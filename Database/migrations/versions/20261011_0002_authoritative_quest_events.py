"""Add server-authoritative quest rules, events, revisions, and reward ledger.

Revision ID: 20261011_0002
Revises: 20261011_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261011_0002"
down_revision: str | None = "20261011_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("player_quest_progress") as batch_op:
        batch_op.add_column(sa.Column("revision", sa.Integer(), server_default="0", nullable=False))
        batch_op.create_check_constraint("ck_quest_progress_revision_nonnegative", "revision >= 0")

    op.create_table(
        "quest_event_targets",
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(120), nullable=False),
        sa.Column("target_version", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('interact', 'checkpoint', 'challenge_passed', "
            "'prerequisite_completed')",
            name="ck_quest_event_target_type",
        ),
        sa.CheckConstraint("target_version > 0", name="ck_quest_event_target_version_positive"),
        sa.PrimaryKeyConstraint(
            "event_type", "target_id", "target_version", name="pk_quest_event_targets"
        ),
    )
    op.create_table(
        "quest_objective_rules",
        sa.Column("quest_slug", sa.String(100), nullable=False),
        sa.Column("quest_version", sa.Integer(), nullable=False),
        sa.Column("objective_id", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(120), nullable=False),
        sa.Column("target_version", sa.Integer(), nullable=False),
        sa.Column("required_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("required_count > 0", name="ck_quest_objective_required_positive"),
        sa.CheckConstraint(
            "event_type = 'challenge_passed' OR required_count = 1",
            name="ck_quest_objective_repeat_requires_challenge",
        ),
        sa.ForeignKeyConstraint(
            ["quest_slug", "quest_version"],
            ["quest_definitions.slug", "quest_definitions.version"],
            name="fk_quest_objective_rule_definition",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_type", "target_id", "target_version"],
            [
                "quest_event_targets.event_type",
                "quest_event_targets.target_id",
                "quest_event_targets.target_version",
            ],
            name="fk_quest_objective_rule_target",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "quest_slug", "quest_version", "objective_id", name="pk_quest_objective_rules"
        ),
    )
    op.create_index(
        "ix_quest_objective_rule_target",
        "quest_objective_rules",
        ["event_type", "target_id", "target_version"],
    )
    op.create_table(
        "quest_objective_prerequisites",
        sa.Column("quest_slug", sa.String(100), nullable=False),
        sa.Column("quest_version", sa.Integer(), nullable=False),
        sa.Column("objective_id", sa.String(100), nullable=False),
        sa.Column("prerequisite_objective_id", sa.String(100), nullable=False),
        sa.CheckConstraint(
            "objective_id <> prerequisite_objective_id",
            name="ck_quest_objective_not_self_prerequisite",
        ),
        sa.ForeignKeyConstraint(
            ["quest_slug", "quest_version", "objective_id"],
            [
                "quest_objective_rules.quest_slug",
                "quest_objective_rules.quest_version",
                "quest_objective_rules.objective_id",
            ],
            name="fk_quest_objective_prerequisite_objective",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["quest_slug", "quest_version", "prerequisite_objective_id"],
            [
                "quest_objective_rules.quest_slug",
                "quest_objective_rules.quest_version",
                "quest_objective_rules.objective_id",
            ],
            name="fk_quest_objective_prerequisite_required",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "quest_slug",
            "quest_version",
            "objective_id",
            "prerequisite_objective_id",
            name="pk_quest_objective_prerequisites",
        ),
    )
    op.create_table(
        "quest_reward_rules",
        sa.Column("quest_slug", sa.String(100), nullable=False),
        sa.Column("quest_version", sa.Integer(), nullable=False),
        sa.Column("reward_id", sa.String(100), nullable=False),
        sa.Column("reward_type", sa.String(24), nullable=False),
        sa.Column("experience_points", sa.Integer(), nullable=False),
        sa.CheckConstraint("reward_type = 'experience'", name="ck_quest_reward_type_supported"),
        sa.CheckConstraint("experience_points > 0", name="ck_quest_reward_experience_positive"),
        sa.ForeignKeyConstraint(
            ["quest_slug", "quest_version"],
            ["quest_definitions.slug", "quest_definitions.version"],
            name="fk_quest_reward_rule_definition",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "quest_slug", "quest_version", "reward_id", name="pk_quest_reward_rules"
        ),
    )
    op.create_table(
        "player_quest_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("player_profile_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("quest_slug", sa.String(100), nullable=False),
        sa.Column("quest_version", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(120), nullable=False),
        sa.Column("target_version", sa.Integer(), nullable=False),
        sa.Column("evidence_submission_id", sa.Uuid(), nullable=True),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("length(payload_hash) = 64", name="ck_quest_event_payload_hash_length"),
        sa.ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_quest_event_player",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["quest_slug", "quest_version"],
            ["quest_definitions.slug", "quest_definitions.version"],
            name="fk_quest_event_definition",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_type", "target_id", "target_version"],
            [
                "quest_event_targets.event_type",
                "quest_event_targets.target_id",
                "quest_event_targets.target_version",
            ],
            name="fk_quest_event_target",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_submission_id"],
            ["submission_records.id"],
            name="fk_quest_event_submission",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_player_quest_events"),
        sa.UniqueConstraint(
            "player_profile_id", "event_id", name="uq_player_quest_event_idempotency"
        ),
    )
    op.create_index(
        "ix_player_quest_events_quest_created",
        "player_quest_events",
        ["player_profile_id", "quest_slug", "quest_version", "created_at"],
    )
    op.create_index(
        "uq_player_quest_submission_evidence",
        "player_quest_events",
        ["player_profile_id", "quest_slug", "quest_version", "evidence_submission_id"],
        unique=True,
        postgresql_where=sa.text("evidence_submission_id IS NOT NULL"),
        sqlite_where=sa.text("evidence_submission_id IS NOT NULL"),
    )
    op.create_table(
        "player_quest_reward_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("player_profile_id", sa.Uuid(), nullable=False),
        sa.Column("quest_slug", sa.String(100), nullable=False),
        sa.Column("quest_version", sa.Integer(), nullable=False),
        sa.Column("reward_id", sa.String(100), nullable=False),
        sa.Column("experience_points", sa.Integer(), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "experience_points > 0", name="ck_quest_reward_ledger_experience_positive"
        ),
        sa.ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_quest_reward_player",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["quest_slug", "quest_version", "reward_id"],
            [
                "quest_reward_rules.quest_slug",
                "quest_reward_rules.quest_version",
                "quest_reward_rules.reward_id",
            ],
            name="fk_quest_reward_ledger_rule",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_player_quest_reward_ledger"),
        sa.UniqueConstraint(
            "player_profile_id",
            "quest_slug",
            "quest_version",
            "reward_id",
            name="uq_player_quest_reward_once",
        ),
    )
    op.create_index(
        "ix_player_quest_rewards_player_date",
        "player_quest_reward_ledger",
        ["player_profile_id", "granted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_player_quest_rewards_player_date", table_name="player_quest_reward_ledger")
    op.drop_table("player_quest_reward_ledger")
    op.drop_index("uq_player_quest_submission_evidence", table_name="player_quest_events")
    op.drop_index("ix_player_quest_events_quest_created", table_name="player_quest_events")
    op.drop_table("player_quest_events")
    op.drop_table("quest_reward_rules")
    op.drop_table("quest_objective_prerequisites")
    op.drop_index("ix_quest_objective_rule_target", table_name="quest_objective_rules")
    op.drop_table("quest_objective_rules")
    op.drop_table("quest_event_targets")
    with op.batch_alter_table("player_quest_progress") as batch_op:
        batch_op.drop_constraint("ck_quest_progress_revision_nonnegative", type_="check")
        batch_op.drop_column("revision")
