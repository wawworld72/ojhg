import uuid
from datetime import datetime

from pydantic import BaseModel


class SubmissionCreate(BaseModel):
    code: str
    language: str


class TestCaseResult(BaseModel):
    order: int
    verdict: str
    time_ms: int | None = None
    memory_mb: float | None = None
    input_preview: str | None = None
    expected_output_preview: str | None = None


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    verdict: str | None
    score: float | None
    attempt_number: int
    is_late: bool
    test_case_results: list[TestCaseResult] | None = None
    judged_at: datetime | None = None

    model_config = {"from_attributes": True}


class SubmissionListItem(BaseModel):
    id: uuid.UUID
    submitted_at: datetime
    language: str
    verdict: str | None
    attempt_number: int
    score: float | None
    is_late: bool

    model_config = {"from_attributes": True}


class SubmissionAccepted(BaseModel):
    submission_id: uuid.UUID
    attempt_number: int
    status: str = "PENDING"
