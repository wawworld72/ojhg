"""Problem management endpoints (teacher)."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.models.problem import AttemptScoreTier, Problem, TestCase
from app.models.problem_set import ProblemSet
from app.schemas.problem import ProblemCreate

router = APIRouter()


def _get_current_user_id(request: Request) -> uuid.UUID:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uuid.UUID(user_id)


@router.post("/problem-sets/{set_id}/problems", status_code=201)
async def create_problem(
    set_id: uuid.UUID,
    body: ProblemCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = _get_current_user_id(request)

    ps_result = await db.execute(select(ProblemSet).where(ProblemSet.id == set_id))
    ps = ps_result.scalar_one_or_none()
    if not ps:
        raise HTTPException(status_code=404, detail="Problem set not found")

    # Determine next display_order
    existing = await db.execute(select(Problem).where(Problem.problem_set_id == set_id))
    display_order = len(existing.scalars().all()) + 1

    problem = Problem(
        problem_set_id=set_id,
        display_order=display_order,
        title=body.title,
        description_md=body.description_md,
        input_description_md=body.input_description_md,
        output_description_md=body.output_description_md,
        time_limit_sec=body.time_limit_sec,
        memory_limit_mb=body.memory_limit_mb,
        max_points=body.max_points,
        allowed_languages=body.allowed_languages,
        created_by=user_id,
    )
    db.add(problem)
    await db.flush()

    for tier in body.score_tiers:
        db.add(AttemptScoreTier(
            problem_id=problem.id,
            min_attempts=tier.min_attempts,
            max_attempts=tier.max_attempts,
            score_ratio=tier.score_ratio,
        ))

    await db.commit()
    await db.refresh(problem)
    return {
        "id": str(problem.id),
        "display_order": problem.display_order,
        "title": problem.title,
        "max_points": float(problem.max_points),
        "allowed_languages": problem.allowed_languages,
    }


@router.put("/problems/{problem_id}")
async def update_problem(
    problem_id: uuid.UUID,
    body: ProblemCreate,
    retroactive_score_update: bool = False,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)
    result = await db.execute(
        select(Problem)
        .options(selectinload(Problem.score_tiers))
        .where(Problem.id == problem_id)
    )
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    problem.title = body.title
    problem.description_md = body.description_md
    problem.input_description_md = body.input_description_md
    problem.output_description_md = body.output_description_md
    problem.time_limit_sec = body.time_limit_sec
    problem.memory_limit_mb = body.memory_limit_mb
    problem.max_points = body.max_points
    problem.allowed_languages = body.allowed_languages

    # Replace score tiers
    for old_tier in problem.score_tiers:
        await db.delete(old_tier)
    for tier in body.score_tiers:
        db.add(AttemptScoreTier(
            problem_id=problem.id,
            min_attempts=tier.min_attempts,
            max_attempts=tier.max_attempts,
            score_ratio=tier.score_ratio,
        ))

    if retroactive_score_update:
        from app.models.submission import StudentProblemProgress
        from app.services.scoring import compute_final_score, find_score_tier

        new_tiers = [
            AttemptScoreTier(
                problem_id=problem.id,
                min_attempts=t.min_attempts,
                max_attempts=t.max_attempts,
                score_ratio=t.score_ratio,
            )
            for t in body.score_tiers
        ]
        prog_result = await db.execute(
            select(StudentProblemProgress).where(
                StudentProblemProgress.problem_id == problem_id,
                StudentProblemProgress.first_accepted_attempt.is_not(None),
            )
        )
        for prog in prog_result.scalars().all():
            tier = find_score_tier(prog.first_accepted_attempt, new_tiers)
            prog.final_score = compute_final_score(float(body.max_points), tier)

    await db.commit()
    return {"id": str(problem.id), "title": problem.title}


@router.post("/problems/import", status_code=201)
async def import_problem(
    problem_set_id: str = Form(...),
    file: UploadFile = File(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Import a single problem from a problem.schema.json file."""
    import json
    from app.services.json_import import validate_problem_json, import_problem_from_json

    user_id = _get_current_user_id(request)
    ps_id = uuid.UUID(problem_set_id)

    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")

    violations = validate_problem_json(data)
    if violations:
        raise HTTPException(status_code=422, detail={"violations": violations})

    ps_result = await db.execute(select(ProblemSet).where(ProblemSet.id == ps_id))
    ps = ps_result.scalar_one_or_none()
    if not ps:
        raise HTTPException(status_code=404, detail="Problem set not found")

    existing = await db.execute(select(Problem).where(Problem.problem_set_id == ps_id))
    display_order = len(existing.scalars().all()) + 1

    result = await import_problem_from_json(db, data, ps_id, user_id, display_order)
    await db.commit()
    return result


@router.post("/problems/{problem_id}/test-cases", status_code=201)
async def upload_test_case(
    problem_id: uuid.UUID,
    input_file: UploadFile = File(...),
    expected_output_file: UploadFile = File(...),
    is_public: bool = Form(False),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)

    result = await db.execute(
        select(Problem).options(selectinload(Problem.test_cases)).where(Problem.id == problem_id)
    )
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    if len(problem.test_cases) >= 100:
        raise HTTPException(status_code=400, detail="Maximum 100 test cases per problem")

    display_order = len(problem.test_cases) + 1
    base_key = f"{problem_id}/{display_order}"
    input_key = f"{base_key}/input.txt"
    output_key = f"{base_key}/expected_output.txt"

    # Store files to local volume
    storage_base = Path(settings.testcase_dir)
    (storage_base / str(problem_id) / str(display_order)).mkdir(parents=True, exist_ok=True)
    (storage_base / input_key).write_bytes(await input_file.read())
    (storage_base / output_key).write_bytes(await expected_output_file.read())

    tc = TestCase(
        problem_id=problem_id,
        display_order=display_order,
        input_storage_key=input_key,
        expected_output_storage_key=output_key,
        is_public=is_public,
    )
    db.add(tc)
    await db.commit()
    await db.refresh(tc)
    return {"id": str(tc.id), "order": tc.display_order, "is_public": tc.is_public}
