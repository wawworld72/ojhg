import uuid
from datetime import datetime

from pydantic import BaseModel


class CourseResponse(BaseModel):
    id: uuid.UUID
    classroom_course_id: str
    name: str
    role: str


class AssignmentResponse(BaseModel):
    id: uuid.UUID
    title: str
    scheduled_open_at: datetime | None
    due_at: datetime | None
    max_points: float | None
    problem_set_id: uuid.UUID | None
    is_linked: bool
