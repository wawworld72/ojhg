"""Grade passback service: calculate scores and send to Google Classroom."""
import uuid
from datetime import datetime, timezone


async def calculate_student_total_score(db, student_id: uuid.UUID, assignment_id: uuid.UUID) -> float:
    from app.models.problem import Problem
    from app.models.problem_set import ClassroomAssignment
    from app.models.submission import StudentProblemProgress
    from sqlalchemy import select

    assignment_result = await db.execute(
        select(ClassroomAssignment).where(ClassroomAssignment.id == assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    if not assignment or not assignment.problem_set_id:
        return 0.0

    problems_result = await db.execute(
        select(Problem).where(Problem.problem_set_id == assignment.problem_set_id)
    )
    problems = problems_result.scalars().all()

    total_score = 0.0
    for problem in problems:
        prog_result = await db.execute(
            select(StudentProblemProgress).where(
                StudentProblemProgress.student_id == student_id,
                StudentProblemProgress.problem_id == problem.id,
            )
        )
        prog = prog_result.scalar_one_or_none()
        total_score += float(prog.final_score) if prog else 0.0

    return total_score


async def passback_grade_for_student(
    db,
    student_id: uuid.UUID,
    assignment_id: uuid.UUID,
    creds,
) -> dict:
    """Send grade to Classroom. Returns dict with status and score."""
    from app.models.grade_passback import GradePassbackLog
    from app.models.problem_set import ClassroomAssignment
    from app.models.course import Course
    from app.models.user import User
    from app.services.classroom_api import ClassroomAPIClient
    from sqlalchemy import select

    total_score = await calculate_student_total_score(db, student_id, assignment_id)

    log_result = await db.execute(
        select(GradePassbackLog).where(
            GradePassbackLog.student_id == student_id,
            GradePassbackLog.assignment_id == assignment_id,
        )
    )
    log = log_result.scalar_one_or_none()

    if log and log.status == "success" and float(log.score) == total_score:
        return {"status": "skipped_no_change", "score": total_score}

    if log is None:
        log = GradePassbackLog(
            student_id=student_id,
            assignment_id=assignment_id,
            score=total_score,
        )
        db.add(log)
    else:
        log.score = total_score
        log.attempt_count += 1
        log.last_attempted_at = datetime.now(timezone.utc)

    await db.flush()

    assignment_result = await db.execute(
        select(ClassroomAssignment).where(ClassroomAssignment.id == assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    if not assignment:
        log.status = "failed"
        log.error_message = "Assignment not found"
        await db.commit()
        return {"status": "failed", "error": "assignment not found"}

    course_result = await db.execute(
        select(Course).where(Course.id == assignment.course_id)
    )
    course = course_result.scalar_one_or_none()

    student_result = await db.execute(select(User).where(User.id == student_id))
    student = student_result.scalar_one_or_none()

    try:
        client = ClassroomAPIClient(creds)
        submissions = await client.list_student_submissions(
            course.classroom_course_id,
            assignment.classroom_coursework_id,
        )
        classroom_sub_id = None
        for csub in submissions:
            if csub.get("userId") == student.google_id:
                classroom_sub_id = csub["id"]
                break

        if classroom_sub_id:
            await client.patch_grade(
                course.classroom_course_id,
                assignment.classroom_coursework_id,
                classroom_sub_id,
                total_score,
            )
            log.status = "success"
        else:
            log.status = "failed"
            log.error_message = "Student Classroom submission not found"

    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)[:500]
        await db.commit()
        raise

    await db.commit()
    return {"status": log.status, "score": total_score}


async def get_passback_failures(db, assignment_id: uuid.UUID) -> list[dict]:
    """Return failed passback logs for an assignment."""
    from app.models.grade_passback import GradePassbackLog
    from app.models.user import User
    from sqlalchemy import select

    result = await db.execute(
        select(GradePassbackLog, User)
        .join(User, User.id == GradePassbackLog.student_id)
        .where(
            GradePassbackLog.assignment_id == assignment_id,
            GradePassbackLog.status == "failed",
        )
    )
    rows = result.all()
    return [
        {
            "assignment_id": str(assignment_id),
            "student_id": str(log.student_id),
            "student_name": user.name,
            "student_email": user.email,
            "score": float(log.score),
            "attempt_count": log.attempt_count,
            "error_message": log.error_message,
            "last_attempted_at": log.last_attempted_at.isoformat(),
        }
        for log, user in rows
    ]
