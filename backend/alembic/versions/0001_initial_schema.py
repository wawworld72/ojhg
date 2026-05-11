"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-11 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums
    op.execute("CREATE TYPE role_enum AS ENUM ('teacher', 'student')")
    op.execute(
        "CREATE TYPE verdict_enum AS ENUM "
        "('PENDING','ACCEPTED','WRONG_ANSWER','TIME_LIMIT_EXCEEDED',"
        "'MEMORY_LIMIT_EXCEEDED','RUNTIME_ERROR','COMPILATION_ERROR')"
    )
    op.execute("CREATE TYPE passback_status_enum AS ENUM ('pending', 'success', 'failed')")
    op.execute(
        "CREATE TYPE publish_status_enum AS ENUM "
        "('pending', 'running', 'completed', 'partial', 'failed')"
    )
    op.execute(
        "CREATE TYPE student_publish_status_enum AS ENUM ('pending', 'success', 'failed')"
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("google_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("profile_picture_url", sa.Text(), nullable=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("classroom_course_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("section", sa.String(255), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("classroom_course_id"),
    )

    op.create_table(
        "course_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Enum("teacher", "student", name="role_enum"), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "user_id", name="uq_enrollment"),
    )

    op.create_table(
        "problem_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "classroom_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("classroom_coursework_id", sa.String(255), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_set_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("max_points", sa.Numeric(10, 2), nullable=True),
        sa.Column("scheduled_open_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allow_late_submission", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["problem_set_id"], ["problem_sets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("classroom_coursework_id"),
        sa.UniqueConstraint("problem_set_id"),
    )

    op.create_table(
        "student_assignment_extensions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extended_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["classroom_assignments.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id", "student_id", name="uq_extension"),
    )

    op.create_table(
        "problems",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description_md", sa.Text(), nullable=False),
        sa.Column("input_description_md", sa.Text(), nullable=True),
        sa.Column("output_description_md", sa.Text(), nullable=True),
        sa.Column("time_limit_sec", sa.Numeric(5, 2), nullable=False, server_default="1.0"),
        sa.Column("memory_limit_mb", sa.Integer(), nullable=False, server_default="256"),
        sa.Column("max_points", sa.Numeric(10, 2), nullable=False),
        sa.Column("allowed_languages", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_set_id"], ["problem_sets.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "attempt_score_tiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("min_attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=True),
        sa.Column("score_ratio", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "test_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("input_storage_key", sa.Text(), nullable=False),
        sa.Column("expected_output_storage_key", sa.Text(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_late", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("verdict", sa.Enum("PENDING","ACCEPTED","WRONG_ANSWER","TIME_LIMIT_EXCEEDED","MEMORY_LIMIT_EXCEEDED","RUNTIME_ERROR","COMPILATION_ERROR", name="verdict_enum"), nullable=True, server_default="PENDING"),
        sa.Column("test_case_results", postgresql.JSONB(), nullable=True),
        sa.Column("score", sa.Numeric(10, 2), nullable=True),
        sa.Column("judged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_submissions_student_problem", "submissions", ["student_id", "problem_id", sa.text("submitted_at DESC")])
    op.create_index("ix_submissions_problem_verdict", "submissions", ["problem_id", "verdict"])

    op.create_table(
        "student_problem_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_accepted_attempt", sa.Integer(), nullable=True),
        sa.Column("final_score", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "problem_id", name="uq_student_problem"),
    )

    op.create_table(
        "grade_passback_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.Enum("pending", "success", "failed", name="passback_status_enum"), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assignment_id"], ["classroom_assignments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_grade_passback_status", "grade_passback_logs", ["status", "last_attempted_at"])

    op.create_table(
        "github_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("github_username", sa.String(255), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("target_repo_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("teacher_id"),
    )

    op.create_table(
        "github_publishes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("initiated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Enum("pending","running","completed","partial","failed", name="publish_status_enum"), nullable=False, server_default="pending"),
        sa.Column("repo_url", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["classroom_assignments.id"]),
        sa.ForeignKeyConstraint(["initiated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "github_publish_student_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("publish_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Enum("pending","success","failed", name="student_publish_status_enum"), nullable=False, server_default="pending"),
        sa.Column("branch_name", sa.String(500), nullable=True),
        sa.Column("branch_url", sa.Text(), nullable=True),
        sa.Column("commits_pushed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["publish_id"], ["github_publishes.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publish_id", "student_id", name="uq_publish_student"),
    )

    op.create_table(
        "similarity_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("similarity_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("threshold_used", sa.Numeric(5, 2), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["classroom_assignments.id"]),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"]),
        sa.ForeignKeyConstraint(["student_a_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["student_b_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["submission_a_id"], ["submissions.id"]),
        sa.ForeignKeyConstraint(["submission_b_id"], ["submissions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id","problem_id","student_a_id","student_b_id", name="uq_similarity_pair"),
    )

    op.create_index("ix_similarity_flagged", "similarity_reports", ["assignment_id", "problem_id", "is_flagged"])
    op.create_index("ix_similarity_score", "similarity_reports", ["assignment_id", "problem_id", sa.text("similarity_score DESC")])


def downgrade() -> None:
    op.drop_table("similarity_reports")
    op.drop_table("github_publish_student_results")
    op.drop_table("github_publishes")
    op.drop_table("github_integrations")
    op.drop_table("grade_passback_logs")
    op.drop_table("student_problem_progress")
    op.drop_table("submissions")
    op.drop_table("test_cases")
    op.drop_table("attempt_score_tiers")
    op.drop_table("problems")
    op.drop_table("student_assignment_extensions")
    op.drop_table("classroom_assignments")
    op.drop_table("problem_sets")
    op.drop_table("course_enrollments")
    op.drop_table("courses")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS student_publish_status_enum")
    op.execute("DROP TYPE IF EXISTS publish_status_enum")
    op.execute("DROP TYPE IF EXISTS passback_status_enum")
    op.execute("DROP TYPE IF EXISTS verdict_enum")
    op.execute("DROP TYPE IF EXISTS role_enum")
