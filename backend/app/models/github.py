import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

PublishStatusEnum = Enum(
    "pending", "running", "completed", "partial", "failed", name="publish_status_enum"
)
StudentPublishStatusEnum = Enum("pending", "success", "failed", name="student_publish_status_enum")


class GitHubIntegration(Base):
    __tablename__ = "github_integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    github_username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    target_repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    teacher: Mapped["User"] = relationship(back_populates="github_integration")  # noqa: F821


class GitHubPublish(Base):
    __tablename__ = "github_publishes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classroom_assignments.id"), nullable=False
    )
    initiated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(PublishStatusEnum, nullable=False, default="pending")
    repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignment: Mapped["ClassroomAssignment"] = relationship()  # noqa: F821
    initiator: Mapped["User"] = relationship()  # noqa: F821
    student_results: Mapped[list["GitHubPublishStudentResult"]] = relationship(
        back_populates="publish"
    )


class GitHubPublishStudentResult(Base):
    __tablename__ = "github_publish_student_results"
    __table_args__ = (UniqueConstraint("publish_id", "student_id", name="uq_publish_student"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publish_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("github_publishes.id"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(StudentPublishStatusEnum, nullable=False, default="pending")
    branch_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    branch_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    commits_pushed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    publish: Mapped["GitHubPublish"] = relationship(back_populates="student_results")
    student: Mapped["User"] = relationship()  # noqa: F821
