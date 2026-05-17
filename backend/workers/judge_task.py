"""Judge Celery task — orchestrates sandbox execution and result persistence."""
import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure /app is in Python path for judge module import
if '/app' not in sys.path:
    sys.path.insert(0, '/app')

from workers.celery_app import celery_app


@celery_app.task(name="workers.judge_task.run_judge", bind=True, max_retries=0)
def run_judge(self, submission_id: str) -> dict:
    return asyncio.run(_run_judge_async(submission_id))


async def _run_judge_async(submission_id_str: str) -> dict:
    from app.core.config import settings
    from app.core.database import AsyncSessionFactory
    from app.models.problem import Problem, TestCase
    from app.models.submission import StudentProblemProgress, Submission
    from app.services.scoring import compute_final_score, find_score_tier
    from judge.compare import compare_outputs
    from judge.sandbox import run_in_sandbox
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    submission_id = uuid.UUID(submission_id_str)

    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(Submission)
            .options(
                selectinload(Submission.problem)
                .selectinload(Problem.test_cases),
                selectinload(Submission.problem)
                .selectinload(Problem.score_tiers),
            )
            .where(Submission.id == submission_id)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return {"error": "submission not found"}

        problem = sub.problem
        test_cases: list[TestCase] = sorted(problem.test_cases, key=lambda tc: tc.display_order)

        tc_results = []
        overall_verdict = "ACCEPTED"
        compilation_error = None

        for tc in test_cases:
            input_data = _read_file(settings.testcase_dir, tc.input_storage_key)
            expected_output = _read_file(settings.testcase_dir, tc.expected_output_storage_key)

            sandbox_result = run_in_sandbox(
                language=sub.language,
                code=sub.code,
                input_data=input_data,
                time_limit_sec=float(problem.time_limit_sec),
                memory_limit_mb=problem.memory_limit_mb,
            )

            if sandbox_result.verdict == "COMPILATION_ERROR":
                overall_verdict = "COMPILATION_ERROR"
                compilation_error = sandbox_result.compilation_error
                tc_results.append({
                    "test_case_id": str(tc.id),
                    "order": tc.display_order,
                    "verdict": "COMPILATION_ERROR",
                    "time_ms": 0,
                    "memory_mb": 0,
                })
                break  # Stop on CE

            if sandbox_result.verdict == "RUN_OK":
                tc_verdict = compare_outputs(sandbox_result.stdout, expected_output)
            elif sandbox_result.verdict == "TIME_LIMIT_EXCEEDED":
                tc_verdict = "TIME_LIMIT_EXCEEDED"
            elif sandbox_result.verdict == "MEMORY_LIMIT_EXCEEDED":
                tc_verdict = "MEMORY_LIMIT_EXCEEDED"
            else:
                tc_verdict = "RUNTIME_ERROR"

            tc_results.append({
                "test_case_id": str(tc.id),
                "order": tc.display_order,
                "verdict": tc_verdict,
                "time_ms": sandbox_result.time_ms,
                "memory_mb": sandbox_result.memory_mb,
            })

            # Aggregate: first non-AC verdict wins (priority order per sandbox.md)
            if tc_verdict != "ACCEPTED" and overall_verdict == "ACCEPTED":
                overall_verdict = tc_verdict

        # Compute score if first Accepted
        score = None
        if overall_verdict == "ACCEPTED":
            # Load progress with lock
            prog_result = await db.execute(
                select(StudentProblemProgress)
                .where(
                    StudentProblemProgress.student_id == sub.student_id,
                    StudentProblemProgress.problem_id == sub.problem_id,
                )
                .with_for_update()
            )
            progress = prog_result.scalar_one_or_none()

            if progress and progress.first_accepted_attempt is None:
                tier = find_score_tier(progress.attempt_count, problem.score_tiers)
                final_score = compute_final_score(float(problem.max_points), tier)
                progress.first_accepted_attempt = progress.attempt_count
                progress.final_score = final_score
                progress.accepted_at = datetime.now(timezone.utc)
                score = final_score

                # Enqueue grade passback
                from workers.grade_sync_task import passback_grade
                from app.models.problem_set import ClassroomAssignment
                assign_result = await db.execute(
                    select(ClassroomAssignment).where(
                        ClassroomAssignment.problem_set_id == problem.problem_set_id
                    )
                )
                assignment = assign_result.scalar_one_or_none()
                if assignment:
                    passback_grade.delay(str(sub.student_id), str(assignment.id))
            elif progress and progress.first_accepted_attempt is not None:
                score = float(progress.final_score)

        # Persist submission result
        sub.verdict = overall_verdict
        sub.test_case_results = tc_results
        sub.score = score
        sub.judged_at = datetime.now(timezone.utc)

        await db.commit()

    return {"submission_id": submission_id_str, "verdict": overall_verdict}


def _read_file(base_dir: str, key: str) -> str:
    try:
        return (Path(base_dir) / key).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


@celery_app.task(name="workers.judge_task.publish_to_github", bind=True, max_retries=2, default_retry_delay=30)
def publish_to_github(self, publish_id: str) -> dict:
    try:
        return asyncio.run(_publish_to_github_async(publish_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _publish_to_github_async(publish_id_str: str) -> dict:
    import asyncio as _asyncio
    from app.core.database import AsyncSessionFactory
    from app.core.security import decrypt_token
    from app.models.github import GitHubIntegration, GitHubPublish, GitHubPublishStudentResult
    from app.models.problem_set import ClassroomAssignment
    from app.models.problem import Problem
    from app.models.submission import Submission
    from app.models.course import CourseEnrollment
    from app.models.user import User
    from app.services.github_publish import (
        ensure_github_repo,
        push_student_submissions,
        _slugify,
    )
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    publish_id = uuid.UUID(publish_id_str)

    async with AsyncSessionFactory() as db:
        pub_result = await db.execute(
            select(GitHubPublish).where(GitHubPublish.id == publish_id)
        )
        publish = pub_result.scalar_one_or_none()
        if not publish:
            return {"error": "publish record not found"}

        publish.status = "running"
        publish.started_at = datetime.now(timezone.utc)
        await db.flush()

        assignment_result = await db.execute(
            select(ClassroomAssignment).where(ClassroomAssignment.id == publish.assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()
        if not assignment:
            publish.status = "failed"
            await db.commit()
            return {"error": "assignment not found"}

        integration_result = await db.execute(
            select(GitHubIntegration).where(GitHubIntegration.teacher_id == publish.initiated_by)
        )
        integration = integration_result.scalar_one_or_none()
        if not integration:
            publish.status = "failed"
            await db.commit()
            return {"error": "no GitHub integration"}

        access_token = decrypt_token(integration.encrypted_access_token)
        clone_url_with_token = (
            f"https://{integration.github_username}:{access_token}@github.com/"
            f"{integration.github_username}/{integration.target_repo_name}.git"
        )

        try:
            repo_url = await ensure_github_repo(
                integration.github_username, access_token, integration.target_repo_name
            )
            publish.repo_url = repo_url
            await db.flush()
        except Exception as exc:
            publish.status = "failed"
            await db.commit()
            raise

        students_result = await db.execute(
            select(CourseEnrollment)
            .options(selectinload(CourseEnrollment.user))
            .where(
                CourseEnrollment.course_id == assignment.course_id,
                CourseEnrollment.role == "student",
            )
        )
        students = students_result.scalars().all()

        problems_result = await db.execute(
            select(Problem).where(Problem.problem_set_id == assignment.problem_set_id)
        )
        problems = problems_result.scalars().all()

        assignment_slug = _slugify(assignment.title or str(assignment.id))
        total = len(students)
        success_count = 0
        fail_count = 0

        for enrollment in students:
            student = enrollment.user
            student_slug = _slugify(student.name or student.email or str(student.id))

            for problem in problems:
                problem_slug = _slugify(problem.title or str(problem.id))

                subs_result = await db.execute(
                    select(Submission)
                    .where(
                        Submission.student_id == student.id,
                        Submission.problem_id == problem.id,
                    )
                    .order_by(Submission.attempt_number)
                )
                subs = subs_result.scalars().all()
                if not subs:
                    continue

                submissions_data = [
                    {
                        "attempt_number": s.attempt_number,
                        "verdict": s.verdict or "PENDING",
                        "score": float(s.score) if s.score is not None else 0.0,
                        "language": s.language,
                        "code": s.code,
                        "submitted_at": s.submitted_at.isoformat(),
                    }
                    for s in subs
                ]

                # Check for existing student result record
                sr_result = await db.execute(
                    select(GitHubPublishStudentResult).where(
                        GitHubPublishStudentResult.publish_id == publish_id,
                        GitHubPublishStudentResult.student_id == student.id,
                    )
                )
                sr = sr_result.scalar_one_or_none()
                if sr is None:
                    sr = GitHubPublishStudentResult(
                        publish_id=publish_id,
                        student_id=student.id,
                        status="pending",
                    )
                    db.add(sr)
                    await db.flush()

                try:
                    result_data = await push_student_submissions(
                        student.id,
                        assignment_slug,
                        problem_slug,
                        student_slug,
                        submissions_data,
                        clone_url_with_token,
                        repo_url.rstrip(".git"),
                    )
                    sr.status = "success"
                    sr.branch_name = result_data["branch_name"]
                    sr.branch_url = result_data["branch_url"]
                    sr.commits_pushed = result_data["commits_pushed"]
                    success_count += 1
                except Exception as exc:
                    sr.status = "failed"
                    sr.error_message = str(exc)[:500]
                    fail_count += 1

                await db.flush()

        if fail_count == 0:
            publish.status = "completed"
        elif success_count == 0:
            publish.status = "failed"
        else:
            publish.status = "partial"

        publish.completed_at = datetime.now(timezone.utc)
        await db.commit()

    return {"publish_id": publish_id_str, "status": publish.status}
