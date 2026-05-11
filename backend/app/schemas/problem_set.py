import uuid
from datetime import datetime

from pydantic import BaseModel


class ProblemSetCreate(BaseModel):
    name: str
    course_id: uuid.UUID


class ProblemSetResponse(BaseModel):
    id: uuid.UUID
    name: str
    course_id: uuid.UUID
    problems: list = []

    model_config = {"from_attributes": True}


class LinkAssignmentRequest(BaseModel):
    assignment_id: uuid.UUID


class ProblemOrderRequest(BaseModel):
    problem_ids: list[uuid.UUID]
