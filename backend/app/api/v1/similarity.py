"""Similarity analysis endpoints."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.problem_set import ClassroomAssignment
from app.models.similarity import SimilarityReport
from app.schemas.similarity import SimilarityAnalysisRequest

router = APIRouter()


def _get_current_user_id(request: Request) -> uuid.UUID:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uuid.UUID(user_id)


@router.post("/assignments/{assignment_id}/similarity-analysis", status_code=202)
async def start_similarity_analysis(
    assignment_id: uuid.UUID,
    body: SimilarityAnalysisRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)
    now = datetime.now(timezone.utc)

    assignment_result = await db.execute(
        select(ClassroomAssignment).where(ClassroomAssignment.id == assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.due_at and now < assignment.due_at:
        raise HTTPException(status_code=403, detail="Cannot analyze before assignment due date")

    from workers.similarity_task import run_similarity_analysis
    task = run_similarity_analysis.delay(str(assignment_id), body.threshold)

    return {"task_id": task.id, "status": "queued"}


@router.get("/assignments/{assignment_id}/similarity-reports")
async def get_similarity_reports(
    assignment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)

    result = await db.execute(
        select(SimilarityReport)
        .options(
            selectinload(SimilarityReport.student_a),
            selectinload(SimilarityReport.student_b),
            selectinload(SimilarityReport.problem),
        )
        .where(
            SimilarityReport.assignment_id == assignment_id,
            SimilarityReport.is_flagged == True,  # noqa: E712
        )
        .order_by(SimilarityReport.similarity_score.desc())
    )
    reports = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "problem_id": str(r.problem_id),
            "problem_title": r.problem.title,
            "student_a_id": str(r.student_a_id),
            "student_a_name": r.student_a.name,
            "student_b_id": str(r.student_b_id),
            "student_b_name": r.student_b.name,
            "similarity_score": float(r.similarity_score),
            "is_flagged": r.is_flagged,
            "threshold_used": float(r.threshold_used),
            "analyzed_at": r.analyzed_at.isoformat(),
        }
        for r in reports
    ]


@router.get("/similarity-reports/{report_id}/diff")
async def get_similarity_diff(
    report_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _get_current_user_id(request)

    result = await db.execute(
        select(SimilarityReport)
        .options(
            selectinload(SimilarityReport.student_a),
            selectinload(SimilarityReport.student_b),
            selectinload(SimilarityReport.submission_a),
            selectinload(SimilarityReport.submission_b),
        )
        .where(SimilarityReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "report_id": str(report.id),
        "similarity_score": float(report.similarity_score),
        "student_a_id": str(report.student_a_id),
        "student_a_name": report.student_a.name,
        "code_a": report.submission_a.code,
        "language_a": report.submission_a.language,
        "student_b_id": str(report.student_b_id),
        "student_b_name": report.student_b.name,
        "code_b": report.submission_b.code,
        "language_b": report.submission_b.language,
    }
