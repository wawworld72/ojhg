"""Similarity analysis Celery task."""
import asyncio
import uuid
from datetime import datetime, timezone
from itertools import combinations

from workers.celery_app import celery_app


@celery_app.task(name="workers.similarity_task.run_similarity_analysis", bind=True)
def run_similarity_analysis(self, assignment_id: str, threshold: float = 80.0) -> dict:
    return asyncio.run(_run_similarity_async(assignment_id, threshold))


async def _run_similarity_async(assignment_id_str: str, threshold: float) -> dict:
    from app.core.database import AsyncSessionFactory
    from app.models.problem_set import ClassroomAssignment
    from app.models.problem import Problem
    from app.models.submission import Submission, StudentProblemProgress
    from app.models.similarity import SimilarityReport
    from app.models.course import CourseEnrollment
    from app.services.similarity import compute_jaccard_similarity
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert

    assignment_id = uuid.UUID(assignment_id_str)
    now = datetime.now(timezone.utc)
    total_pairs = 0
    flagged_pairs = 0

    async with AsyncSessionFactory() as db:
        assignment_result = await db.execute(
            select(ClassroomAssignment).where(ClassroomAssignment.id == assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()
        if not assignment or not assignment.problem_set_id:
            return {"error": "assignment not found"}

        students_result = await db.execute(
            select(CourseEnrollment).where(
                CourseEnrollment.course_id == assignment.course_id,
                CourseEnrollment.role == "student",
            )
        )
        student_ids = [e.user_id for e in students_result.scalars().all()]

        problems_result = await db.execute(
            select(Problem).where(Problem.problem_set_id == assignment.problem_set_id)
        )
        problems = problems_result.scalars().all()

        for problem in problems:
            # Get best (accepted or latest) submission per student
            student_subs: dict[uuid.UUID, dict] = {}
            for student_id in student_ids:
                subs_result = await db.execute(
                    select(Submission)
                    .where(
                        Submission.student_id == student_id,
                        Submission.problem_id == problem.id,
                    )
                    .order_by(Submission.attempt_number.desc())
                    .limit(1)
                )
                sub = subs_result.scalar_one_or_none()
                if sub and sub.code:
                    student_subs[student_id] = {
                        "id": sub.id,
                        "code": sub.code,
                        "language": sub.language,
                    }

            student_list = list(student_subs.items())
            for (sid_a, sub_a), (sid_b, sub_b) in combinations(student_list, 2):
                total_pairs += 1
                score = compute_jaccard_similarity(
                    sub_a["code"], sub_a["language"],
                    sub_b["code"], sub_b["language"],
                )
                is_flagged = score >= threshold

                if is_flagged:
                    flagged_pairs += 1

                # Upsert SimilarityReport
                existing = await db.execute(
                    select(SimilarityReport).where(
                        SimilarityReport.assignment_id == assignment_id,
                        SimilarityReport.problem_id == problem.id,
                        SimilarityReport.student_a_id == sid_a,
                        SimilarityReport.student_b_id == sid_b,
                    )
                )
                report = existing.scalar_one_or_none()
                if report:
                    report.similarity_score = score
                    report.is_flagged = is_flagged
                    report.threshold_used = threshold
                    report.analyzed_at = now
                    report.submission_a_id = sub_a["id"]
                    report.submission_b_id = sub_b["id"]
                else:
                    report = SimilarityReport(
                        assignment_id=assignment_id,
                        problem_id=problem.id,
                        student_a_id=sid_a,
                        student_b_id=sid_b,
                        submission_a_id=sub_a["id"],
                        submission_b_id=sub_b["id"],
                        similarity_score=score,
                        is_flagged=is_flagged,
                        threshold_used=threshold,
                        analyzed_at=now,
                    )
                    db.add(report)

        await db.commit()

    return {
        "assignment_id": assignment_id_str,
        "total_pairs_analyzed": total_pairs,
        "flagged_pairs": flagged_pairs,
        "threshold": threshold,
    }
