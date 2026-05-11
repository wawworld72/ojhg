import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problem_sets.id"), nullable=False
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description_md: Mapped[str] = mapped_column(Text, nullable=False)
    input_description_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_description_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_limit_sec: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=1.0)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=256)
    max_points: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    allowed_languages: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    problem_set: Mapped["ProblemSet"] = relationship(back_populates="problems")  # noqa: F821
    creator: Mapped["User"] = relationship()  # noqa: F821
    score_tiers: Mapped[list["AttemptScoreTier"]] = relationship(
        back_populates="problem", cascade="all, delete-orphan", order_by="AttemptScoreTier.min_attempts"
    )
    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="problem", cascade="all, delete-orphan", order_by="TestCase.display_order"
    )
    submissions: Mapped[list["Submission"]] = relationship(back_populates="problem")  # noqa: F821
    progress_records: Mapped[list["StudentProblemProgress"]] = relationship(back_populates="problem")  # noqa: F821


class AttemptScoreTier(Base):
    __tablename__ = "attempt_score_tiers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False
    )
    min_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_ratio: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    problem: Mapped["Problem"] = relationship(back_populates="score_tiers")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    input_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    problem: Mapped["Problem"] = relationship(back_populates="test_cases")
