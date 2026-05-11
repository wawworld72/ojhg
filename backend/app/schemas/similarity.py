import uuid
from datetime import datetime

from pydantic import BaseModel


class SimilarityAnalysisRequest(BaseModel):
    threshold: float = 80.0


class SimilarityPairDetail(BaseModel):
    id: uuid.UUID
    problem_id: uuid.UUID
    problem_title: str
    student_a_id: uuid.UUID
    student_a_name: str
    student_b_id: uuid.UUID
    student_b_name: str
    similarity_score: float
    is_flagged: bool
    threshold_used: float
    analyzed_at: datetime


class SimilarityReportResponse(BaseModel):
    assignment_id: uuid.UUID
    threshold: float
    flagged_pairs: list[SimilarityPairDetail]


class CodeDiffResponse(BaseModel):
    report_id: uuid.UUID
    similarity_score: float
    student_a_id: uuid.UUID
    student_a_name: str
    code_a: str
    language_a: str
    student_b_id: uuid.UUID
    student_b_name: str
    code_b: str
    language_b: str
