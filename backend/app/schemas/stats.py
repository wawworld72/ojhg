import uuid
from datetime import datetime

from pydantic import BaseModel


class ProblemStatItem(BaseModel):
    problem_id: uuid.UUID
    title: str
    submitted_count: int
    accepted_count: int
    avg_attempts: float
    avg_score: float


class ProblemSetStatsResponse(BaseModel):
    total_students: int
    submitted_students: int
    avg_total_score: float
    problems: list[ProblemStatItem]


class StudentProblemStat(BaseModel):
    problem_id: uuid.UUID
    attempt_count: int
    final_score: float
    accepted: bool


class AssignmentStudentItem(BaseModel):
    student_id: uuid.UUID
    name: str
    email: str
    total_score: float
    problems: list[StudentProblemStat]


class AssignmentStudentListResponse(BaseModel):
    students: list[AssignmentStudentItem]


class AssignmentSummary(BaseModel):
    assignment_id: uuid.UUID
    title: str
    due_at: datetime | None = None
    submitted_count: int
    total_students: int


class CourseDashboardResponse(BaseModel):
    course_id: uuid.UUID
    assignments: list[AssignmentSummary]


class SubmissionHistoryItem(BaseModel):
    submission_id: uuid.UUID
    attempt_number: int
    submitted_at: datetime
    verdict: str | None
    score: float | None
    language: str
    is_late: bool
    code: str | None = None


class ProblemHistoryGroup(BaseModel):
    problem_id: uuid.UUID
    problem_title: str
    submissions: list[SubmissionHistoryItem]


class StudentHistoryResponse(BaseModel):
    student_id: uuid.UUID
    assignment_id: uuid.UUID
    problems: list[ProblemHistoryGroup]
