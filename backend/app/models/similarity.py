import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SimilarityReport(Base):
    __tablename__ = "similarity_reports"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "problem_id",
            "student_a_id",
            "student_b_id",
            name="uq_similarity_pair",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classroom_assignments.id"), nullable=False
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False
    )
    student_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    student_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    submission_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id"), nullable=False
    )
    submission_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submissions.id"), nullable=False
    )
    similarity_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    threshold_used: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignment: Mapped["ClassroomAssignment"] = relationship()  # noqa: F821
    problem: Mapped["Problem"] = relationship()  # noqa: F821
    student_a: Mapped["User"] = relationship(foreign_keys=[student_a_id])  # noqa: F821
    student_b: Mapped["User"] = relationship(foreign_keys=[student_b_id])  # noqa: F821
    submission_a: Mapped["Submission"] = relationship(foreign_keys=[submission_a_id])  # noqa: F821
    submission_b: Mapped["Submission"] = relationship(foreign_keys=[submission_b_id])  # noqa: F821
