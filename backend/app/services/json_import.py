"""JSON import service: validate and import problems/assignments from schema files."""
import json
from pathlib import Path
from typing import Any


def _load_schema(schema_path: str) -> dict:
    return json.loads(Path(schema_path).read_text(encoding="utf-8"))


def _validate_score_tiers(tiers: list[dict]) -> list[str]:
    """Check for overlapping or invalid score tiers. Returns list of error messages."""
    errors = []
    sorted_tiers = sorted(tiers, key=lambda t: t["min_attempts"])

    prev_max = None
    for i, tier in enumerate(sorted_tiers):
        min_att = tier.get("min_attempts")
        max_att = tier.get("max_attempts")

        if max_att is not None and max_att < min_att:
            errors.append(f"Tier {i+1}: max_attempts ({max_att}) < min_attempts ({min_att})")

        if prev_max is not None:
            expected_min = prev_max + 1
            if min_att != expected_min:
                errors.append(
                    f"Tier {i+1}: gap or overlap — expected min_attempts={expected_min}, got {min_att}"
                )

        prev_max = max_att

    return errors


def validate_problem_json(data: dict) -> list[dict]:
    """Validate a problem JSON dict. Returns list of {field, message} violations."""
    violations = []
    required_fields = ["title", "description_md", "time_limit_sec", "memory_limit_mb",
                        "max_points", "allowed_languages", "score_tiers"]

    for f in required_fields:
        if f not in data:
            violations.append({"field": f, "message": f"Required field '{f}' is missing"})

    if "title" in data and not str(data["title"]).strip():
        violations.append({"field": "title", "message": "Title must not be empty"})

    if "time_limit_sec" in data:
        tl = data["time_limit_sec"]
        if not isinstance(tl, (int, float)) or tl < 0.5 or tl > 10.0:
            violations.append({"field": "time_limit_sec", "message": "Must be between 0.5 and 10.0"})

    if "memory_limit_mb" in data:
        ml = data["memory_limit_mb"]
        if not isinstance(ml, int) or ml < 32 or ml > 512:
            violations.append({"field": "memory_limit_mb", "message": "Must be integer between 32 and 512"})

    valid_langs = {"python3", "java17", "cpp17", "c17"}
    if "allowed_languages" in data:
        langs = data["allowed_languages"]
        if not isinstance(langs, list) or len(langs) == 0:
            violations.append({"field": "allowed_languages", "message": "Must provide at least one language"})
        else:
            invalid = [l for l in langs if l not in valid_langs]
            if invalid:
                violations.append({"field": "allowed_languages", "message": f"Invalid languages: {invalid}"})

    if "score_tiers" in data:
        tiers = data["score_tiers"]
        if not isinstance(tiers, list) or len(tiers) == 0:
            violations.append({"field": "score_tiers", "message": "Must provide at least one score tier"})
        else:
            tier_errors = _validate_score_tiers(tiers)
            for err in tier_errors:
                violations.append({"field": "score_tiers", "message": err})

    return violations


async def import_problem_from_json(
    db,
    data: dict,
    problem_set_id,
    created_by,
    display_order: int,
) -> dict:
    """Create Problem + AttemptScoreTier + TestCase records from validated JSON."""
    import uuid
    from pathlib import Path
    from app.models.problem import Problem, AttemptScoreTier, TestCase
    from app.core.config import settings

    problem = Problem(
        problem_set_id=problem_set_id,
        display_order=display_order,
        title=data["title"],
        description_md=data.get("description_md", ""),
        input_description_md=data.get("input_description_md"),
        output_description_md=data.get("output_description_md"),
        time_limit_sec=data["time_limit_sec"],
        memory_limit_mb=data["memory_limit_mb"],
        max_points=data["max_points"],
        allowed_languages=data["allowed_languages"],
        created_by=created_by,
    )
    db.add(problem)
    await db.flush()

    for tier in data.get("score_tiers", []):
        db.add(AttemptScoreTier(
            problem_id=problem.id,
            min_attempts=tier["min_attempts"],
            max_attempts=tier.get("max_attempts"),
            score_ratio=tier["score_ratio"],
        ))

    for i, tc_data in enumerate(data.get("test_cases", []), start=1):
        is_public = tc_data.get("is_sample", False)
        base_key = f"{problem.id}/{i}"
        input_key = f"{base_key}/input.txt"
        output_key = f"{base_key}/expected_output.txt"

        storage_base = Path(settings.testcase_dir)
        (storage_base / str(problem.id) / str(i)).mkdir(parents=True, exist_ok=True)
        (storage_base / input_key).write_text(tc_data["input"], encoding="utf-8")
        (storage_base / output_key).write_text(tc_data["expected_output"], encoding="utf-8")

        db.add(TestCase(
            problem_id=problem.id,
            display_order=i,
            input_storage_key=input_key,
            expected_output_storage_key=output_key,
            is_public=is_public,
        ))

    return {"id": str(problem.id), "title": problem.title}
