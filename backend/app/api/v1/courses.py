"""Course and assignment endpoints (teacher & student)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.course import Course, CourseEnrollment
from app.models.problem_set import ClassroomAssignment

router = APIRouter()


def _get_current_user_id(request: Request) -> uuid.UUID:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uuid.UUID(user_id)


@router.get("/courses")
async def list_courses(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = _get_current_user_id(request)
    result = await db.execute(
        select(CourseEnrollment)
        .options(selectinload(CourseEnrollment.course))
        .where(CourseEnrollment.user_id == user_id)
    )
    enrollments = result.scalars().all()
    return [
        {
            "id": str(e.course.id),
            "classroom_course_id": e.course.classroom_course_id,
            "name": e.course.name,
            "role": e.role,
        }
        for e in enrollments
    ]


@router.post("/courses/sync")
async def sync_courses(request: Request, db: AsyncSession = Depends(get_db)):
    """Re-sync Google Classroom courses and enrollments for the current user."""
    from app.models.user import User
    from app.core.security import decrypt_token
    from app.core.config import settings

    user_id = _get_current_user_id(request)

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.encrypted_refresh_token:
        raise HTTPException(status_code=403, detail="No stored credentials")

    try:
        from google.oauth2.credentials import Credentials
        from app.services.classroom_api import ClassroomAPIClient

        creds = Credentials(
            token=None,
            refresh_token=decrypt_token(user.encrypted_refresh_token),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        client = ClassroomAPIClient(creds)

        import asyncio
        from datetime import datetime, timezone
        from app.models.course import CourseEnrollment

        now = datetime.now(timezone.utc)
        teacher_courses, student_courses = await asyncio.gather(
            client.list_courses(teacher_id="me"),
            client.list_courses(student_id="me"),
        )
        courses_by_role = [(c, "teacher") for c in teacher_courses] + [(c, "student") for c in student_courses]

        for c, role in courses_by_role:
            classroom_id = c["id"]
            result = await db.execute(
                select(Course).where(Course.classroom_course_id == classroom_id)
            )
            course = result.scalar_one_or_none()
            if course is None:
                course = Course(
                    classroom_course_id=classroom_id,
                    name=c.get("name", ""),
                    section=c.get("section"),
                    synced_at=now,
                )
                db.add(course)
                await db.flush()
            else:
                course.name = c.get("name", "")
                course.section = c.get("section")
                course.synced_at = now

            enroll_result = await db.execute(
                select(CourseEnrollment).where(
                    CourseEnrollment.course_id == course.id,
                    CourseEnrollment.user_id == user_id,
                )
            )
            enrollment = enroll_result.scalar_one_or_none()
            if enrollment is None:
                db.add(CourseEnrollment(
                    course_id=course.id,
                    user_id=user_id,
                    role=role,
                    synced_at=now,
                ))
            else:
                enrollment.role = role
                enrollment.synced_at = now

        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Classroom sync failed: {e}")

    result = await db.execute(
        select(CourseEnrollment)
        .options(selectinload(CourseEnrollment.course))
        .where(CourseEnrollment.user_id == user_id)
    )
    enrollments = result.scalars().all()
    return [
        {
            "id": str(e.course.id),
            "classroom_course_id": e.course.classroom_course_id,
            "name": e.course.name,
            "role": e.role,
        }
        for e in enrollments
    ]


@router.get("/courses/{course_id}/assignments")
async def list_assignments(
    course_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)
    result = await db.execute(
        select(ClassroomAssignment).where(ClassroomAssignment.course_id == course_id)
    )
    assignments = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "title": a.title,
            "scheduled_open_at": a.scheduled_open_at.isoformat() if a.scheduled_open_at else None,
            "due_at": a.due_at.isoformat() if a.due_at else None,
            "max_points": float(a.max_points) if a.max_points else None,
            "problem_set_id": str(a.problem_set_id) if a.problem_set_id else None,
            "is_linked": a.problem_set_id is not None,
        }
        for a in assignments
    ]


@router.post("/courses/{course_id}/assignments/{assignment_id}/sync")
async def sync_assignment(
    course_id: uuid.UUID,
    assignment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """On-demand sync of assignment schedule from Google Classroom (teacher only)."""
    from app.models.user import User
    from app.core.security import decrypt_token

    user_id = _get_current_user_id(request)

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.encrypted_refresh_token:
        raise HTTPException(status_code=403, detail="Teacher account or token required")

    result = await db.execute(
        select(ClassroomAssignment)
        .options(selectinload(ClassroomAssignment.course))
        .where(ClassroomAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    try:
        from google.oauth2.credentials import Credentials
        from app.services.classroom_api import ClassroomAPIClient

        creds = Credentials(
            token=None,
            refresh_token=decrypt_token(user.encrypted_refresh_token),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=__import__("app.core.config", fromlist=["settings"]).settings.google_client_id,
            client_secret=__import__("app.core.config", fromlist=["settings"]).settings.google_client_secret,
        )
        client = ClassroomAPIClient(creds)
        cw = await client.get_coursework(
            assignment.course.classroom_course_id,
            assignment.classroom_coursework_id,
        )
        if "dueDate" in cw and "dueTime" in cw:
            d = cw["dueDate"]
            t = cw["dueTime"]
            assignment.due_at = datetime(
                d["year"], d["month"], d["day"],
                t.get("hours", 0), t.get("minutes", 0), 0,
                tzinfo=timezone.utc,
            )
        if "maxPoints" in cw:
            assignment.max_points = cw["maxPoints"]
        assignment.synced_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Classroom sync failed: {e}")

    return {
        "id": str(assignment.id),
        "title": assignment.title,
        "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
        "max_points": float(assignment.max_points) if assignment.max_points else None,
        "synced_at": assignment.synced_at.isoformat() if assignment.synced_at else None,
    }


@router.get("/courses/{course_id}/dashboard")
async def course_dashboard(
    course_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)
    from app.models.submission import Submission, StudentProblemProgress
    from app.models.problem import Problem

    result = await db.execute(
        select(ClassroomAssignment)
        .where(ClassroomAssignment.course_id == course_id)
    )
    assignments = result.scalars().all()

    students_result = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.role == "student",
        )
    )
    total_students = len(students_result.scalars().all())

    out = []
    for a in assignments:
        submitted_count = 0
        if a.problem_set_id:
            problems_result = await db.execute(
                select(Problem).where(Problem.problem_set_id == a.problem_set_id)
            )
            problems = problems_result.scalars().all()
            if problems:
                problem_ids = [p.id for p in problems]
                subs_result = await db.execute(
                    select(StudentProblemProgress.student_id)
                    .where(StudentProblemProgress.problem_id.in_(problem_ids))
                    .distinct()
                )
                submitted_count = len(subs_result.scalars().all())

        out.append({
            "assignment_id": str(a.id),
            "title": a.title,
            "due_at": a.due_at.isoformat() if a.due_at else None,
            "submitted_count": submitted_count,
            "total_students": total_students,
        })
    return out
