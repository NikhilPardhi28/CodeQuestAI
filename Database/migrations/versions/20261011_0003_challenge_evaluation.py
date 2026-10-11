"""Add versioned challenge evaluation content and durable submission attempts.

Revision ID: 20261011_0003
Revises: 20261011_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261011_0003"
down_revision: str | None = "20261011_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("coding_challenge_definitions") as batch_op:
        batch_op.add_column(sa.Column("time_limit_ms", sa.Integer(), server_default="5000", nullable=False))
        batch_op.add_column(sa.Column("output_limit_bytes", sa.Integer(), server_default="65536", nullable=False))
        batch_op.add_column(sa.Column("max_source_bytes", sa.Integer(), server_default="32768", nullable=False))
        batch_op.add_column(sa.Column("passing_score", sa.Integer(), server_default="70", nullable=False))
        batch_op.add_column(sa.Column("evaluator_version", sa.String(40), server_default="python-v1", nullable=False))
        batch_op.create_check_constraint("ck_challenge_time_limit", "time_limit_ms BETWEEN 100 AND 5000")
        batch_op.create_check_constraint("ck_challenge_output_limit", "output_limit_bytes BETWEEN 1024 AND 65536")
        batch_op.create_check_constraint("ck_challenge_source_limit", "max_source_bytes BETWEEN 1 AND 65536")
        batch_op.create_check_constraint("ck_challenge_passing_score", "passing_score BETWEEN 1 AND 100")

    with op.batch_alter_table("submission_records") as batch_op:
        batch_op.add_column(sa.Column("source_code", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("request_hash", sa.String(64), nullable=True))
        batch_op.drop_constraint("ck_submission_status", type_="check")
        batch_op.execute("UPDATE submission_records SET status = 'queued' WHERE status = 'received'")
        batch_op.execute("UPDATE submission_records SET status = 'internal_error' WHERE status = 'error'")
        batch_op.create_check_constraint(
            "ck_submission_status",
            "status IN ('queued', 'running', 'passed', 'failed', 'timed_out', 'internal_error')",
        )
        batch_op.create_check_constraint(
            "ck_submission_request_hash_length", "request_hash IS NULL OR length(request_hash) = 64"
        )
        batch_op.create_check_constraint(
            "ck_submission_source_length", "source_code IS NULL OR length(source_code) <= 32768"
        )
        batch_op.create_index(
            "ix_submission_queue_status_created", ["status", "created_at"]
        )

    op.create_table(
        "challenge_hidden_test_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("challenge_slug", sa.String(100), nullable=False),
        sa.Column("challenge_version", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("test_definition", sa.JSON(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_hidden_test_position_nonnegative"),
        sa.ForeignKeyConstraint(
            ["challenge_slug", "challenge_version"],
            ["coding_challenge_definitions.slug", "coding_challenge_definitions.version"],
            name="fk_hidden_test_challenge_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_challenge_hidden_test_cases"),
        sa.UniqueConstraint("challenge_slug", "challenge_version", "position", name="uq_hidden_test_position"),
    )
    op.create_index("ix_hidden_tests_challenge", "challenge_hidden_test_cases", ["challenge_slug", "challenge_version"])

    op.create_table(
        "challenge_hints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("challenge_slug", sa.String(100), nullable=False),
        sa.Column("challenge_version", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(1000), nullable=False),
        sa.CheckConstraint("level > 0", name="ck_challenge_hint_level_positive"),
        sa.ForeignKeyConstraint(
            ["challenge_slug", "challenge_version"],
            ["coding_challenge_definitions.slug", "coding_challenge_definitions.version"],
            name="fk_challenge_hint_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_challenge_hints"),
        sa.UniqueConstraint("challenge_slug", "challenge_version", "level", name="uq_challenge_hint_level"),
    )
    op.create_table(
        "player_challenge_hint_unlocks",
        sa.Column("player_profile_id", sa.Uuid(), nullable=False),
        sa.Column("challenge_slug", sa.String(100), nullable=False),
        sa.Column("challenge_version", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_profile_id"], ["player_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["challenge_slug", "challenge_version", "level"],
            ["challenge_hints.challenge_slug", "challenge_hints.challenge_version", "challenge_hints.level"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("player_profile_id", "challenge_slug", "challenge_version", "level", name="pk_player_challenge_hint_unlocks"),
    )
    op.create_index("ix_player_challenge_hints", "player_challenge_hint_unlocks", ["player_profile_id", "challenge_slug", "challenge_version"])

    op.create_table(
        "evaluation_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("worker_version", sa.String(40), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempt_number > 0", name="ck_evaluation_attempt_number_positive"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'passed', 'failed', 'timed_out', 'internal_error')",
            name="ck_evaluation_attempt_status",
        ),
        sa.ForeignKeyConstraint(["submission_id"], ["submission_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_evaluation_attempts"),
        sa.UniqueConstraint("submission_id", "attempt_number", name="uq_evaluation_attempt_number"),
        sa.UniqueConstraint(
            "submission_id", name="uq_evaluation_attempt_single_per_submission"
        ),
    )
    op.create_index("ix_evaluation_attempts_status_created", "evaluation_attempts", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_attempts_status_created", table_name="evaluation_attempts")
    op.drop_table("evaluation_attempts")
    op.drop_index("ix_player_challenge_hints", table_name="player_challenge_hint_unlocks")
    op.drop_table("player_challenge_hint_unlocks")
    op.drop_table("challenge_hints")
    op.drop_index("ix_hidden_tests_challenge", table_name="challenge_hidden_test_cases")
    op.drop_table("challenge_hidden_test_cases")
    with op.batch_alter_table("submission_records") as batch_op:
        batch_op.drop_index("ix_submission_queue_status_created")
        batch_op.drop_constraint("ck_submission_source_length", type_="check")
        batch_op.drop_constraint("ck_submission_request_hash_length", type_="check")
        batch_op.drop_constraint("ck_submission_status", type_="check")
        batch_op.execute(
            "UPDATE submission_records SET status = 'error' "
            "WHERE status IN ('timed_out', 'internal_error')"
        )
        batch_op.create_check_constraint(
            "ck_submission_status",
            "status IN ('received', 'queued', 'running', 'passed', 'failed', 'error')",
        )
        batch_op.drop_column("request_hash")
        batch_op.drop_column("source_code")
    with op.batch_alter_table("coding_challenge_definitions") as batch_op:
        batch_op.drop_constraint("ck_challenge_passing_score", type_="check")
        batch_op.drop_constraint("ck_challenge_source_limit", type_="check")
        batch_op.drop_constraint("ck_challenge_output_limit", type_="check")
        batch_op.drop_constraint("ck_challenge_time_limit", type_="check")
        batch_op.drop_column("evaluator_version")
        batch_op.drop_column("passing_score")
        batch_op.drop_column("max_source_bytes")
        batch_op.drop_column("output_limit_bytes")
        batch_op.drop_column("time_limit_ms")
