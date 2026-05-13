"""Problem set endpoints: student access, teacher management."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.problem import Problem
from app.models.problem_set import ClassroomAssignment, ProblemSet, StudentAssignmentExtension
from app.models.submission import StudentProblemProgress
from app.schemas.problem_set import LinkAssignmentRequest, ProblemOrderRequest, ProblemSetCreate
from app.services.scoring import find_score_tier

router = APIRouter()


def _get_current_user_id(request: Request) -> uuid.UUID:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uuid.UUID(user_id)


def _read_preview(storage_key: str, max_bytes: int = 512) -> str:
    from app.core.config import settings
    from pathlib import Path
    try:
        return (Path(settings.testcase_dir) / storage_key).read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except Exception:
        return ""


# ─── Student endpoint ──────────────────────────────────────────────────────────

@router.get("/assignments/{assignment_id}/problem-set")
async def get_problem_set(
    assignment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    student_id = _get_current_user_id(request)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(ClassroomAssignment)
        .options(
            selectinload(ClassroomAssignment.problem_set)
            .selectinload(ProblemSet.problems)
            .selectinload(Problem.score_tiers),
            selectinload(ClassroomAssignment.problem_set)
            .selectinload(ProblemSet.problems)
            .selectinload(Problem.test_cases),
        )
        .where(ClassroomAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment or not assignment.problem_set:
        raise HTTPException(status_code=404, detail="Assignment or problem set not found")

    if assignment.scheduled_open_at and now < assignment.scheduled_open_at:
        raise HTTPException(
            status_code=403,
            detail=f"Assignment not yet open. Opens at {assignment.scheduled_open_at.isoformat()}",
        )

    ext_result = await db.execute(
        select(StudentAssignmentExtension).where(
            StudentAssignmentExtension.assignment_id == assignment_id,
            StudentAssignmentExtension.student_id == student_id,
        )
    )
    extension = ext_result.scalar_one_or_none()
    effective_due = extension.extended_due_at if extension else assignment.due_at

    is_late_access = False
    if effective_due and now > effective_due:
        if not assignment.allow_late_submission:
            raise HTTPException(status_code=403, detail="Assignment is past due")
        is_late_access = True

    ps = assignment.problem_set
    problems_out = []
    for p in sorted(ps.problems, key=lambda x: x.display_order):
        public_tests = []
        for tc in p.test_cases:
            if tc.is_public:
                public_tests.append({
                    "id": str(tc.id),
                    "display_order": tc.display_order,
                    "input_preview": _read_preview(tc.input_storage_key),
                    "output_preview": _read_preview(tc.expected_output_storage_key),
                })
        problems_out.append({
            "id": str(p.id),
            "display_order": p.display_order,
            "title": p.title,
            "description_md": p.description_md,
            "input_description_md": p.input_description_md,
            "output_description_md": p.output_description_md,
            "time_limit_sec": float(p.time_limit_sec),
            "memory_limit_mb": p.memory_limit_mb,
            "max_points": float(p.max_points),
            "allowed_languages": p.allowed_languages,
            "public_test_cases": public_tests,
            "score_tiers": [
                {"min_attempts": t.min_attempts, "max_attempts": t.max_attempts, "score_ratio": float(t.score_ratio)}
                for t in sorted(p.score_tiers, key=lambda x: x.min_attempts)
            ],
        })

    return {
        "assignment_id": str(assignment_id),
        "problem_set_id": str(ps.id),
        "problem_set_name": ps.name,
        "due_at": effective_due.isoformat() if effective_due else None,
        "is_late_access": is_late_access,
        "problems": problems_out,
    }


# ─── Teacher endpoints ─────────────────────────────────────────────────────────

@router.get("/problem-sets")
async def list_problem_sets(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = _get_current_user_id(request)
    result = await db.execute(
        select(ProblemSet)
        .options(selectinload(ProblemSet.problems))
        .where(ProblemSet.created_by == user_id)
        .order_by(ProblemSet.created_at.desc())
    )
    sets = result.scalars().all()
    return [
        {
            "id": str(ps.id),
            "name": ps.name,
            "course_id": str(ps.course_id),
            "problems": [{"id": str(p.id), "title": p.title} for p in ps.problems],
        }
        for ps in sets
    ]


@router.post("/problem-sets", status_code=201)
async def create_problem_set(
    body: ProblemSetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = _get_current_user_id(request)
    ps = ProblemSet(name=body.name, course_id=body.course_id, created_by=user_id)
    db.add(ps)
    await db.commit()
    await db.refresh(ps)
    return {"id": str(ps.id), "name": ps.name, "course_id": str(ps.course_id), "problems": []}


@router.get("/problem-sets/{set_id}")
async def get_problem_set_detail(
    set_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)
    result = await db.execute(
        select(ProblemSet)
        .options(selectinload(ProblemSet.problems).selectinload(Problem.score_tiers))
        .where(ProblemSet.id == set_id)
    )
    ps = result.scalar_one_or_none()
    if not ps:
        raise HTTPException(status_code=404, detail="Problem set not found")
    return {
        "id": str(ps.id),
        "name": ps.name,
        "course_id": str(ps.course_id),
        "problems": [
            {"id": str(p.id), "title": p.title, "display_order": p.display_order, "max_points": float(p.max_points)}
            for p in ps.problems
        ],
    }
