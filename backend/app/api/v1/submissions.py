"""Submission endpoints: POST submit, GET result, GET stream (SSE), GET history."""
import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.problem import AttemptScoreTier, Problem, TestCase
from app.models.problem_set import ClassroomAssignment, StudentAssignmentExtension
from app.models.submission import StudentProblemProgress, Submission
from app.schemas.submission import SubmissionAccepted, SubmissionCreate, SubmissionListItem, SubmissionResponse, TestCaseResult

router = APIRouter()


def _get_current_user_id(request: Request) -> uuid.UUID:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uuid.UUID(user_id)


async def _get_effective_due_at(
    db: AsyncSession,
    assignment: ClassroomAssignment,
    student_id: uuid.UUID,
) -> datetime | None:
    """Return student-specific due_at (extension) or assignment-level due_at."""
    if assignment.due_at is None:
        return None
    result = await db.execute(
        select(StudentAssignmentExtension).where(
            StudentAssignmentExtension.assignment_id == assignment.id,
            StudentAssignmentExtension.student_id == student_id,
        )
    )
    ext = result.scalar_one_or_none()
    return ext.extended_due_at if ext else assignment.due_at


@router.post("/problems/{problem_id}/submissions", status_code=202)
async def create_submission(
    problem_id: uuid.UUID,
    body: SubmissionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SubmissionAccepted:
    student_id = _get_current_user_id(request)

    # Load problem and its assignment
    result = await db.execute(
        select(Problem)
        .options(selectinload(Problem.problem_set), selectinload(Problem.score_tiers))
        .where(Problem.id == problem_id)
    )
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    if body.language not in problem.allowed_languages:
        raise HTTPException(status_code=400, detail=f"Language '{body.language}' is not allowed for this problem")

    if not body.code.strip():
        raise HTTPException(status_code=400, detail="Code must not be empty")

    # Get assignment for deadline check
    result = await db.execute(
        select(ClassroomAssignment).where(
            ClassroomAssignment.problem_set_id == problem.problem_set_id
        )
    )
    assignment = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    is_late = False
    if assignment:
        # Check if before open
        if assignment.scheduled_open_at and now < assignment.scheduled_open_at:
            raise HTTPException(status_code=403, detail="Assignment not yet open")

        effective_due = await _get_effective_due_at(db, assignment, student_id)
        if effective_due and now > effective_due:
            if not assignment.allow_late_submission:
                raise HTTPException(status_code=403, detail="Assignment deadline has passed")
            is_late = True

    # Atomically increment attempt_count (SELECT FOR UPDATE)
    from sqlalchemy import text
    prog_result = await db.execute(
        select(StudentProblemProgress)
        .where(
            StudentProblemProgress.student_id == student_id,
            StudentProblemProgress.problem_id == problem_id,
        )
        .with_for_update()
    )
    progress = prog_result.scalar_one_or_none()

    if progress is None:
        progress = StudentProblemProgress(
            student_id=student_id,
            problem_id=problem_id,
            attempt_count=0,
            final_score=0,
        )
        db.add(progress)
        await db.flush()

    # Don't increment attempt_count if already accepted
    if progress.first_accepted_attempt is None:
        progress.attempt_count += 1

    attempt_number = progress.attempt_count

    submission = Submission(
        student_id=student_id,
        problem_id=problem_id,
        code=body.code,
        language=body.language,
        is_late=is_late,
        attempt_number=attempt_number,
        verdict="PENDING",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # Enqueue judge task
    from workers.judge_task import run_judge
    run_judge.delay(str(submission.id))

    return SubmissionAccepted(
        submission_id=submission.id,
        attempt_number=attempt_number,
        status="PENDING",
    )


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SubmissionResponse:
    student_id = _get_current_user_id(request)

    result = await db.execute(
        select(Submission)
        .options(
            selectinload(Submission.problem).selectinload(Problem.test_cases)
        )
        .where(Submission.id == submission_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Authorization: only own submission or teacher
    if str(sub.student_id) != str(student_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Build test case results with public input preview
    tc_results = None
    if sub.test_case_results:
        public_tcs: dict[str, TestCase] = {
            str(tc.id): tc for tc in sub.problem.test_cases if tc.is_public
        }
        tc_results = []
        for r in sub.test_case_results:
            tc_id = r.get("test_case_id")
            tc = public_tcs.get(tc_id)
            tc_results.append(
                TestCaseResult(
                    order=r["order"],
                    verdict=r["verdict"],
                    time_ms=r.get("time_ms"),
                    memory_mb=r.get("memory_mb"),
                    input_preview=_read_preview(tc.input_storage_key) if tc else None,
                    expected_output_preview=_read_preview(tc.expected_output_storage_key) if tc else None,
                )
            )

    return SubmissionResponse(
        id=sub.id,
        verdict=sub.verdict,
        score=float(sub.score) if sub.score is not None else None,
        attempt_number=sub.attempt_number,
        is_late=sub.is_late,
        test_case_results=tc_results,
        judged_at=sub.judged_at,
    )


@router.get("/submissions/{submission_id}/stream")
async def stream_submission_result(
    submission_id: uuid.UUID,
    request: Request,
) -> StreamingResponse:
    _get_current_user_id(request)

    async def event_generator():
        from app.core.database import AsyncSessionFactory
        for _ in range(60):  # poll up to 60 seconds
            async with AsyncSessionFactory() as db:
                result = await db.execute(
                    select(Submission).where(Submission.id == submission_id)
                )
                sub = result.scalar_one_or_none()
                if sub and sub.judged_at is not None:
                    data = (
                        f"event: verdict\n"
                        f"data: {{\"verdict\":\"{sub.verdict}\","
                        f"\"score\":{sub.score if sub.score is not None else 'null'},"
                        f"\"attempt_number\":{sub.attempt_number}}}\n\n"
                    )
                    yield data
                    return
            await asyncio.sleep(1)
        yield "event: timeout\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/submissions/{submission_id}/code")
async def get_submission_code(
    submission_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    student_id = _get_current_user_id(request)
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if str(sub.student_id) != str(student_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"code": sub.code, "language": sub.language}


@router.get("/problems/{problem_id}/my-submissions", response_model=list[SubmissionListItem])
async def get_my_submissions(
    problem_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[SubmissionListItem]:
    student_id = _get_current_user_id(request)
    result = await db.execute(
        select(Submission)
        .where(
            Submission.student_id == student_id,
            Submission.problem_id == problem_id,
        )
        .order_by(Submission.submitted_at.desc())
    )
    subs = result.scalars().all()
    return [
        SubmissionListItem(
            id=s.id,
            submitted_at=s.submitted_at,
            language=s.language,
            verdict=s.verdict,
            attempt_number=s.attempt_number,
            score=float(s.score) if s.score is not None else None,
            is_late=s.is_late,
        )
        for s in subs
    ]


@router.get("/assignments/{assignment_id}/students/{student_id}/history")
async def get_student_history(
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """All submissions grouped by problem for a student in an assignment (teacher access)."""
    _get_current_user_id(request)

    result = await db.execute(
        select(ClassroomAssignment)
        .where(ClassroomAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment or not assignment.problem_set_id:
        raise HTTPException(status_code=404, detail="Assignment not found")

    from app.models.problem import Problem
    problems_result = await db.execute(
        select(Problem)
        .options(selectinload(Problem.problem_set))
        .where(Problem.problem_set_id == assignment.problem_set_id)
        .order_by(Problem.display_order)
    )
    problems = problems_result.scalars().all()

    groups = []
    for problem in problems:
        subs_result = await db.execute(
            select(Submission)
            .where(
                Submission.student_id == student_id,
                Submission.problem_id == problem.id,
            )
            .order_by(Submission.attempt_number)
        )
        subs = subs_result.scalars().all()
        groups.append({
            "problem_id": str(problem.id),
            "problem_title": problem.title,
            "submissions": [
                {
                    "submission_id": str(s.id),
                    "attempt_number": s.attempt_number,
                    "submitted_at": s.submitted_at.isoformat(),
                    "verdict": s.verdict,
                    "score": float(s.score) if s.score is not None else None,
                    "language": s.language,
                    "is_late": s.is_late,
                    "code": s.code,
                }
                for s in subs
            ],
        })

    return {
        "student_id": str(student_id),
        "assignment_id": str(assignment_id),
        "problems": groups,
    }


def _read_preview(storage_key: str, max_bytes: int = 512) -> str | None:
    """Read first max_bytes from a test case file. Returns None on error."""
    from app.core.config import settings
    from pathlib import Path
    try:
        p = Path(settings.testcase_dir) / storage_key
        return p.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except Exception:
        return None
