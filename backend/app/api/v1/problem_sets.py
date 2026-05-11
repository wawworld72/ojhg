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
            raise HTTPException(status_code=403, detail="Assignment deadline has passed")
        is_late_access = True

    ps = assignment.problem_set
    problems_out = []
    total_score = 0.0

    for problem in ps.problems:
        prog_result = await db.execute(
            select(StudentProblemProgress).where(
                StudentProblemProgress.student_id == student_id,
                StudentProblemProgress.problem_id == problem.id,
            )
        )
        progress = prog_result.scalar_one_or_none()

        attempt_count = progress.attempt_count if progress else 0
        final_score = float(progress.final_score) if progress else 0.0
        accepted = (progress.first_accepted_attempt is not None) if progress else False

        next_attempt = attempt_count + 1
        current_tier = find_score_tier(next_attempt, problem.score_tiers) if not accepted else None
        next_tier_obj = find_score_tier(next_attempt + 1, problem.score_tiers) if not accepted else None

        problems_out.append({
            "id": str(problem.id),
            "display_order": problem.display_order,
            "title": problem.title,
            "description_md": problem.description_md,
            "input_description_md": problem.input_description_md,
            "output_description_md": problem.output_description_md,
            "time_limit_sec": float(problem.time_limit_sec),
            "memory_limit_mb": problem.memory_limit_mb,
            "max_points": float(problem.max_points),
            "allowed_languages": problem.allowed_languages,
            "score_tiers": [
                {"min_attempts": t.min_attempts, "max_attempts": t.max_attempts, "score_ratio": float(t.score_ratio)}
                for t in problem.score_tiers
            ],
            "my_progress": {
                "attempt_count": attempt_count,
                "final_score": final_score,
                "accepted": accepted,
                "current_tier": {"score_ratio": float(current_tier.score_ratio)} if current_tier else None,
                "next_tier": (
                    {"min_attempts": next_tier_obj.min_attempts, "score_ratio": float(next_tier_obj.score_ratio)}
                    if next_tier_obj else None
                ),
            },
            "public_test_cases": [
                {
                    "order": tc.display_order,
                    "input_preview": _read_preview(tc.input_storage_key),
                    "expected_output_preview": _read_preview(tc.expected_output_storage_key),
                }
                for tc in problem.test_cases if tc.is_public
            ],
        })
        total_score += final_score

    return {
        "problem_set": {
            "id": str(ps.id),
            "name": ps.name,
            "scheduled_open_at": assignment.scheduled_open_at.isoformat() if assignment.scheduled_open_at else None,
            "due_at": effective_due.isoformat() if effective_due else None,
            "allow_late_submission": assignment.allow_late_submission,
        },
        "problems": problems_out,
        "my_total_score": total_score,
        "is_late_access": is_late_access,
    }


# ─── Teacher endpoints ─────────────────────────────────────────────────────────

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


@router.put("/problem-sets/{set_id}/link")
async def link_assignment(
    set_id: uuid.UUID,
    body: LinkAssignmentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)

    # Check 1:1 uniqueness
    existing = await db.execute(
        select(ClassroomAssignment).where(ClassroomAssignment.problem_set_id == set_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Problem set is already linked to an assignment")

    assignment_result = await db.execute(
        select(ClassroomAssignment).where(ClassroomAssignment.id == body.assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.problem_set_id is not None:
        raise HTTPException(status_code=409, detail="Assignment is already linked to a problem set")

    assignment.problem_set_id = set_id
    assignment.synced_at = datetime.now(timezone.utc)
    await db.commit()
    return {"problem_set_id": str(set_id), "assignment_id": str(assignment.id)}


@router.patch("/problem-sets/{set_id}/problems/order")
async def reorder_problems(
    set_id: uuid.UUID,
    body: ProblemOrderRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)
    result = await db.execute(
        select(Problem).where(Problem.problem_set_id == set_id)
    )
    problems = {str(p.id): p for p in result.scalars().all()}

    for order, pid in enumerate(body.problem_ids, start=1):
        p = problems.get(str(pid))
        if not p:
            raise HTTPException(status_code=404, detail=f"Problem {pid} not found in this set")
        p.display_order = order

    await db.commit()
    return {"ok": True}


@router.get("/assignments/{assignment_id}/students")
async def list_assignment_students(
    assignment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)
    from app.models.user import User
    from app.models.course import CourseEnrollment
    from sqlalchemy import and_

    assignment_result = await db.execute(
        select(ClassroomAssignment).where(ClassroomAssignment.id == assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    result = await db.execute(
        select(CourseEnrollment)
        .options(selectinload(CourseEnrollment.user))
        .where(
            CourseEnrollment.course_id == assignment.course_id,
            CourseEnrollment.role == "student",
        )
    )
    enrollments = result.scalars().all()

    students_out = []
    for e in enrollments:
        problems_result = await db.execute(
            select(Problem)
            .options(selectinload(Problem.problem_set))
            .where(Problem.problem_set_id == assignment.problem_set_id)
        )
        problems = problems_result.scalars().all()

        problem_stats = []
        total_score = 0.0
        for p in problems:
            prog = await db.execute(
                select(StudentProblemProgress).where(
                    StudentProblemProgress.student_id == e.user_id,
                    StudentProblemProgress.problem_id == p.id,
                )
            )
            prog_rec = prog.scalar_one_or_none()
            score = float(prog_rec.final_score) if prog_rec else 0.0
            total_score += score
            problem_stats.append({
                "problem_id": str(p.id),
                "attempt_count": prog_rec.attempt_count if prog_rec else 0,
                "final_score": score,
                "accepted": (prog_rec.first_accepted_attempt is not None) if prog_rec else False,
            })

        students_out.append({
            "student_id": str(e.user_id),
            "name": e.user.name,
            "email": e.user.email,
            "total_score": total_score,
            "problems": problem_stats,
        })

    return students_out


@router.post("/problem-sets/import", status_code=201)
async def import_problem_set(
    course_id: str = Form(...),
    file: UploadFile = File(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Import an assignment from an assignment.schema.json file, creating ProblemSet + Problems."""
    import json
    from app.services.json_import import validate_problem_json, import_problem_from_json

    user_id = _get_current_user_id(request)
    c_id = uuid.UUID(course_id)

    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")

    assignment_name = data.get("name")
    if not assignment_name:
        raise HTTPException(status_code=422, detail="Assignment 'name' is required")

    problems_data = data.get("problems", [])
    if not problems_data:
        raise HTTPException(status_code=422, detail="Assignment must include at least one problem")

    # Validate all problems first
    all_violations = []
    for i, prob in enumerate(problems_data):
        prob_data = prob.get("inline") or prob
        violations = validate_problem_json(prob_data)
        for v in violations:
            all_violations.append({"problem_index": i, "field": v["field"], "message": v["message"]})

    if all_violations:
        raise HTTPException(status_code=422, detail={"violations": all_violations})

    ps = ProblemSet(name=assignment_name, course_id=c_id, created_by=user_id)
    db.add(ps)
    await db.flush()

    created_problems = []
    for order, prob in enumerate(problems_data, start=1):
        prob_data = prob.get("inline") or prob
        result = await import_problem_from_json(db, prob_data, ps.id, user_id, order)
        created_problems.append(result)

    await db.commit()
    return {
        "problem_set_id": str(ps.id),
        "name": ps.name,
        "problems_created": len(created_problems),
        "problems": created_problems,
    }


@router.get("/assignments/{assignment_id}/passback-failures")
async def get_passback_failures(
    assignment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Return list of failed grade passback attempts for teacher dashboard."""
    _get_current_user_id(request)
    from app.services.grade_passback import get_passback_failures as _get_failures
    return await _get_failures(db, assignment_id)


@router.get("/problem-sets/{set_id}/stats")
async def get_problem_set_stats(
    set_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)
    from app.models.submission import Submission
    from sqlalchemy import func

    result = await db.execute(select(Problem).where(Problem.problem_set_id == set_id))
    problems = result.scalars().all()

    problem_stats = []
    for p in problems:
        subs = await db.execute(
            select(Submission).where(Submission.problem_id == p.id)
        )
        all_subs = subs.scalars().all()
        unique_students = {str(s.student_id) for s in all_subs}
        accepted = [s for s in all_subs if s.verdict == "ACCEPTED"]
        avg_attempts = (
            sum(s.attempt_number for s in all_subs) / len(all_subs) if all_subs else 0
        )
        avg_score = (
            sum(float(s.score or 0) for s in accepted) / len(accepted) if accepted else 0
        )
        problem_stats.append({
            "problem_id": str(p.id),
            "title": p.title,
            "submitted_count": len(unique_students),
            "accepted_count": len({str(s.student_id) for s in accepted}),
            "avg_attempts": round(avg_attempts, 2),
            "avg_score": round(avg_score, 2),
        })

    return {
        "total_students": 0,
        "submitted_students": 0,
        "avg_total_score": 0,
        "problems": problem_stats,
    }
