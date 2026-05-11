import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class ScoreTierResponse(BaseModel):
    min_attempts: int
    max_attempts: int | None
    score_ratio: float

    model_config = {"from_attributes": True}


class ScoreTierCreate(BaseModel):
    min_attempts: int
    max_attempts: int | None
    score_ratio: float


class MyProgressResponse(BaseModel):
    attempt_count: int
    final_score: float | None
    accepted: bool
    current_tier: ScoreTierResponse | None = None
    next_tier: dict | None = None


class PublicTestCaseResponse(BaseModel):
    order: int
    input_preview: str
    expected_output_preview: str


class ProblemResponse(BaseModel):
    id: uuid.UUID
    display_order: int
    title: str
    description_md: str
    input_description_md: str | None
    output_description_md: str | None
    time_limit_sec: float
    memory_limit_mb: int
    max_points: float
    allowed_languages: list[str]
    score_tiers: list[ScoreTierResponse]
    my_progress: MyProgressResponse | None = None
    public_test_cases: list[PublicTestCaseResponse] | None = None

    model_config = {"from_attributes": True}


class ProblemCreate(BaseModel):
    title: str
    description_md: str
    input_description_md: str | None = None
    output_description_md: str | None = None
    time_limit_sec: float = 1.0
    memory_limit_mb: int = 256
    max_points: float
    allowed_languages: list[str]
    score_tiers: list[ScoreTierCreate]

    @field_validator("time_limit_sec")
    @classmethod
    def validate_time_limit(cls, v: float) -> float:
        if not (0.5 <= v <= 10.0):
            raise ValueError("time_limit_sec must be between 0.5 and 10.0")
        return v

    @field_validator("memory_limit_mb")
    @classmethod
    def validate_memory_limit(cls, v: int) -> int:
        if not (32 <= v <= 512):
            raise ValueError("memory_limit_mb must be between 32 and 512")
        return v

    @field_validator("max_points")
    @classmethod
    def validate_max_points(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("max_points must be greater than 0")
        return v

    @field_validator("allowed_languages")
    @classmethod
    def validate_languages(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("allowed_languages must not be empty")
        return v

    @field_validator("score_tiers")
    @classmethod
    def validate_score_tiers(cls, tiers: list[ScoreTierCreate]) -> list[ScoreTierCreate]:
        sorted_tiers = sorted(tiers, key=lambda t: t.min_attempts)
        for i, tier in enumerate(sorted_tiers):
            if tier.max_attempts is not None and tier.max_attempts <= tier.min_attempts:
                raise ValueError("max_attempts must be greater than min_attempts")
            if i > 0:
                prev = sorted_tiers[i - 1]
                prev_max = prev.max_attempts if prev.max_attempts is not None else float("inf")
                if tier.min_attempts <= prev_max:
                    raise ValueError("Score tiers must not overlap")
        null_max_count = sum(1 for t in tiers if t.max_attempts is None)
        if null_max_count > 1:
            raise ValueError("Only one tier may have max_attempts=null (unlimited)")
        return tiers


class ProblemSetDetailResponse(BaseModel):
    problem_set: dict
    problems: list[ProblemResponse]
    my_total_score: float
    is_late_access: bool
