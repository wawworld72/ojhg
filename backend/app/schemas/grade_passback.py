import uuid
from datetime import datetime

from pydantic import BaseModel


class GradePassbackRequest(BaseModel):
    student_id: uuid.UUID
    assignment_id: uuid.UUID


class GradePassbackStatus(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    assignment_id: uuid.UUID
    score: float
    status: str
    attempt_count: int
    last_attempted_at: datetime
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PassbackFailureSummary(BaseModel):
    assignment_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    student_email: str
    score: float
    attempt_count: int
    error_message: str | None = None
    last_attempted_at: datetime
