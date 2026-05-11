import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProblemSet(Base):
    __tablename__ = "problem_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    course: Mapped["Course"] = relationship(back_populates="problem_sets")  # noqa: F821
    creator: Mapped["User"] = relationship()  # noqa: F821
    problems: Mapped[list["Problem"]] = relationship(  # noqa: F821
        back_populates="problem_set", order_by="Problem.display_order"
    )
    classroom_assignment: Mapped["ClassroomAssignment | None"] = relationship(
        back_populates="problem_set"
    )


class ClassroomAssignment(Base):
    __tablename__ = "classroom_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classroom_coursework_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False
    )
    problem_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problem_sets.id"), unique=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    max_points: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    scheduled_open_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    allow_late_submission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    course: Mapped["Course"] = relationship(back_populates="assignments")  # noqa: F821
    problem_set: Mapped["ProblemSet | None"] = relationship(back_populates="classroom_assignment")
    extensions: Mapped[list["StudentAssignmentExtension"]] = relationship(
        back_populates="assignment"
    )


class StudentAssignmentExtension(Base):
    __tablename__ = "student_assignment_extensions"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", name="uq_extension"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classroom_assignments.id"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    extended_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignment: Mapped["ClassroomAssignment"] = relationship(back_populates="extensions")
    student: Mapped["User"] = relationship()  # noqa: F821
