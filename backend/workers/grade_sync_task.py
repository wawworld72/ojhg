"""Grade passback and Classroom schedule sync Celery tasks."""
import asyncio
import uuid
from datetime import datetime, timezone

from workers.celery_app import celery_app


@celery_app.task(name="workers.grade_sync_task.sync_classroom_schedules")
def sync_classroom_schedules() -> None:
    asyncio.run(_sync_schedules_async())


async def _sync_schedules_async() -> None:
    from app.core.database import AsyncSessionFactory
    from app.core.security import decrypt_token
    from app.models.problem_set import ClassroomAssignment
    from app.models.user import User
    from sqlalchemy import select
    from google.oauth2.credentials import Credentials
    from app.services.classroom_api import ClassroomAPIClient
    from app.core.config import settings

    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(ClassroomAssignment)
            .where(ClassroomAssignment.problem_set_id.is_not(None))
        )
        assignments = result.scalars().all()

        for assignment in assignments:
            try:
                from app.models.course import CourseEnrollment
                teacher_result = await db.execute(
                    select(User)
                    .join(CourseEnrollment, CourseEnrollment.user_id == User.id)
                    .where(
                        CourseEnrollment.course_id == assignment.course_id,
                        CourseEnrollment.role == "teacher",
                    )
                    .limit(1)
                )
                teacher = teacher_result.scalar_one_or_none()
                if not teacher or not teacher.encrypted_refresh_token:
                    continue

                creds = Credentials(
                    token=None,
                    refresh_token=decrypt_token(teacher.encrypted_refresh_token),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=settings.google_client_id,
                    client_secret=settings.google_client_secret,
                )
                client = ClassroomAPIClient(creds)

                from app.models.course import Course
                course_result = await db.execute(
                    select(Course).where(Course.id == assignment.course_id)
                )
                course = course_result.scalar_one_or_none()
                if not course:
                    continue

                cw = await client.get_coursework(
                    course.classroom_course_id,
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

            except Exception:
                pass

        await db.commit()


@celery_app.task(name="workers.grade_sync_task.finalize_due_assignments")
def finalize_due_assignments() -> None:
    asyncio.run(_finalize_due_async())


async def _finalize_due_async() -> None:
    from app.core.database import AsyncSessionFactory
    from app.models.problem_set import ClassroomAssignment
    from sqlalchemy import select

    now = datetime.now(timezone.utc)

    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(ClassroomAssignment).where(
                ClassroomAssignment.problem_set_id.is_not(None),
                ClassroomAssignment.due_at <= now,
            )
        )
        due_assignments = result.scalars().all()

        for assignment in due_assignments:
            from app.models.course import CourseEnrollment
            students_result = await db.execute(
                select(CourseEnrollment).where(
                    CourseEnrollment.course_id == assignment.course_id,
                    CourseEnrollment.role == "student",
                )
            )
            for enrollment in students_result.scalars().all():
                passback_grade.delay(str(enrollment.user_id), str(assignment.id))


@celery_app.task(name="workers.grade_sync_task.passback_grade", bind=True, max_retries=3, default_retry_delay=60)
def passback_grade(self, student_id: str, assignment_id: str) -> dict:
    try:
        return asyncio.run(_passback_grade_async(student_id, assignment_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _passback_grade_async(student_id_str: str, assignment_id_str: str) -> dict:
    from app.core.database import AsyncSessionFactory
    from app.core.security import decrypt_token
    from app.models.grade_passback import GradePassbackLog
    from app.models.problem_set import ClassroomAssignment
    from app.models.user import User
    from app.models.course import CourseEnrollment
    from sqlalchemy import select
    from app.core.config import settings
    from google.oauth2.credentials import Credentials
    from app.services.grade_passback import passback_grade_for_student

    student_id = uuid.UUID(student_id_str)
    assignment_id = uuid.UUID(assignment_id_str)

    async with AsyncSessionFactory() as db:
        assignment_result = await db.execute(
            select(ClassroomAssignment).where(ClassroomAssignment.id == assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()
        if not assignment:
            return {"error": "assignment not found"}

        teacher_result = await db.execute(
            select(User)
            .join(CourseEnrollment, CourseEnrollment.user_id == User.id)
            .where(
                CourseEnrollment.course_id == assignment.course_id,
                CourseEnrollment.role == "teacher",
            )
            .limit(1)
        )
        teacher = teacher_result.scalar_one_or_none()
        if not teacher or not teacher.encrypted_refresh_token:
            log_result = await db.execute(
                select(GradePassbackLog).where(
                    GradePassbackLog.student_id == student_id,
                    GradePassbackLog.assignment_id == assignment_id,
                )
            )
            log = log_result.scalar_one_or_none()
            if log is None:
                log = GradePassbackLog(
                    student_id=student_id,
                    assignment_id=assignment_id,
                    score=0,
                    status="failed",
                    error_message="No teacher token available",
                )
                db.add(log)
            else:
                log.status = "failed"
                log.error_message = "No teacher token available"
            await db.commit()
            return {"error": "no teacher token"}

        creds = Credentials(
            token=None,
            refresh_token=decrypt_token(teacher.encrypted_refresh_token),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        return await passback_grade_for_student(db, student_id, assignment_id, creds)
