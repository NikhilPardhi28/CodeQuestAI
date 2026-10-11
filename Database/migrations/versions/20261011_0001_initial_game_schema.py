"""Create initial player, curriculum, quest, challenge, and award schema.

Revision ID: 20261011_0001
Revises:
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261011_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "player_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("identity_subject", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=50), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
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
        sa.PrimaryKeyConstraint("id", name="pk_player_profiles"),
        sa.UniqueConstraint("identity_subject", name="uq_player_profiles_identity_subject"),
    )
    op.create_table(
        "curriculum_regions",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("unlock_region_slug", sa.String(length=80), nullable=True),
        sa.Column("unlock_region_version", sa.Integer(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_region_sort_nonnegative"),
        sa.CheckConstraint("version > 0", name="ck_region_version_positive"),
        sa.ForeignKeyConstraint(
            ["unlock_region_slug", "unlock_region_version"],
            ["curriculum_regions.slug", "curriculum_regions.version"],
            name="fk_region_unlock_region_version",
        ),
        sa.PrimaryKeyConstraint("slug", "version", name="pk_curriculum_regions"),
    )
    op.create_index(
        "ix_regions_published_order", "curriculum_regions", ["is_published", "sort_order"]
    )

    op.create_table(
        "learning_objectives",
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("region_slug", sa.String(length=80), nullable=False),
        sa.Column("region_version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("prerequisites", sa.JSON(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("sort_order >= 0", name="ck_objective_sort_nonnegative"),
        sa.CheckConstraint("version > 0", name="ck_objective_version_positive"),
        sa.ForeignKeyConstraint(
            ["region_slug", "region_version"],
            ["curriculum_regions.slug", "curriculum_regions.version"],
            name="fk_objective_region_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("slug", "version", name="pk_learning_objectives"),
    )
    op.create_index(
        "ix_objectives_region_order",
        "learning_objectives",
        ["region_slug", "region_version", "sort_order"],
    )

    op.create_table(
        "quest_definitions",
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("region_slug", sa.String(length=80), nullable=False),
        sa.Column("region_version", sa.Integer(), nullable=False),
        sa.Column("objective_slug", sa.String(length=100), nullable=True),
        sa.Column("objective_version", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("public_content", sa.JSON(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(objective_slug IS NULL AND objective_version IS NULL) OR "
            "(objective_slug IS NOT NULL AND objective_version IS NOT NULL)",
            name="ck_quest_objective_version_pair",
        ),
        sa.CheckConstraint("version > 0", name="ck_quest_version_positive"),
        sa.ForeignKeyConstraint(
            ["objective_slug", "objective_version"],
            ["learning_objectives.slug", "learning_objectives.version"],
            name="fk_quest_objective_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["region_slug", "region_version"],
            ["curriculum_regions.slug", "curriculum_regions.version"],
            name="fk_quest_region_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("slug", "version", name="pk_quest_definitions"),
    )
    op.create_index(
        "ix_quests_region_published", "quest_definitions", ["region_slug", "is_published"]
    )

    op.create_table(
        "coding_challenge_definitions",
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("objective_slug", sa.String(length=100), nullable=False),
        sa.Column("objective_version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("statement", sa.String(length=4000), nullable=False),
        sa.Column("public_content", sa.JSON(), nullable=False),
        sa.Column("content_digest", sa.String(length=64), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(content_digest) = 64", name="ck_challenge_content_digest_length"
        ),
        sa.CheckConstraint("version > 0", name="ck_challenge_version_positive"),
        sa.ForeignKeyConstraint(
            ["objective_slug", "objective_version"],
            ["learning_objectives.slug", "learning_objectives.version"],
            name="fk_challenge_objective_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("slug", "version", name="pk_coding_challenge_definitions"),
    )
    op.create_index(
        "ix_challenges_objective_published",
        "coding_challenge_definitions",
        ["objective_slug", "is_published"],
    )

    op.create_table(
        "achievement_definitions",
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("version > 0", name="ck_achievement_version_positive"),
        sa.PrimaryKeyConstraint("slug", "version", name="pk_achievement_definitions"),
    )

    op.create_table(
        "player_quest_progress",
        sa.Column("player_profile_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("quest_slug", sa.String(length=100), nullable=False),
        sa.Column("quest_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
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
            "status IN ('locked', 'available', 'in_progress', 'completed', 'abandoned')",
            name="ck_quest_progress_status",
        ),
        sa.ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_quest_progress_player",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["quest_slug", "quest_version"],
            ["quest_definitions.slug", "quest_definitions.version"],
            name="fk_quest_progress_definition",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "player_profile_id", "quest_slug", "quest_version", name="pk_player_quest_progress"
        ),
    )
    op.create_index(
        "ix_quest_progress_player_updated",
        "player_quest_progress",
        ["player_profile_id", "updated_at"],
    )

    op.create_table(
        "submission_records",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("player_profile_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("challenge_slug", sa.String(length=100), nullable=False),
        sa.Column("challenge_version", sa.Integer(), nullable=False),
        sa.Column("client_submission_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source_digest", sa.String(length=64), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source_digest IS NULL OR length(source_digest) = 64",
            name="ck_submission_digest_length",
        ),
        sa.CheckConstraint(
            "status IN ('received', 'queued', 'running', 'passed', 'failed', 'error')",
            name="ck_submission_status",
        ),
        sa.ForeignKeyConstraint(
            ["challenge_slug", "challenge_version"],
            ["coding_challenge_definitions.slug", "coding_challenge_definitions.version"],
            name="fk_submission_challenge_definition",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_submission_player",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_submission_records"),
        sa.UniqueConstraint(
            "player_profile_id", "client_submission_id", name="uq_submission_client_id_per_player"
        ),
    )
    op.create_index(
        "ix_submissions_challenge_created", "submission_records", ["challenge_slug", "created_at"]
    )
    op.create_index(
        "ix_submissions_player_created", "submission_records", ["player_profile_id", "created_at"]
    )

    op.create_table(
        "player_progression",
        sa.Column("player_profile_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("experience", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("experience >= 0", name="ck_progression_experience_nonnegative"),
        sa.CheckConstraint("level >= 1", name="ck_progression_level_positive"),
        sa.CheckConstraint("revision >= 0", name="ck_progression_revision_nonnegative"),
        sa.ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_progression_player",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("player_profile_id", name="pk_player_progression"),
    )

    op.create_table(
        "player_achievement_awards",
        sa.Column("player_profile_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("achievement_slug", sa.String(length=100), nullable=False),
        sa.Column("achievement_version", sa.Integer(), nullable=False),
        sa.Column(
            "awarded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(
            ["achievement_slug", "achievement_version"],
            ["achievement_definitions.slug", "achievement_definitions.version"],
            name="fk_achievement_award_definition",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_achievement_award_player",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "player_profile_id",
            "achievement_slug",
            "achievement_version",
            name="pk_player_achievement_awards",
        ),
    )
    op.create_index(
        "ix_achievement_awards_player_date",
        "player_achievement_awards",
        ["player_profile_id", "awarded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_achievement_awards_player_date", table_name="player_achievement_awards")
    op.drop_table("player_achievement_awards")
    op.drop_table("player_progression")
    op.drop_index("ix_submissions_player_created", table_name="submission_records")
    op.drop_index("ix_submissions_challenge_created", table_name="submission_records")
    op.drop_table("submission_records")
    op.drop_index("ix_quest_progress_player_updated", table_name="player_quest_progress")
    op.drop_table("player_quest_progress")
    op.drop_table("achievement_definitions")
    op.drop_index("ix_challenges_objective_published", table_name="coding_challenge_definitions")
    op.drop_table("coding_challenge_definitions")
    op.drop_index("ix_quests_region_published", table_name="quest_definitions")
    op.drop_table("quest_definitions")
    op.drop_index("ix_objectives_region_order", table_name="learning_objectives")
    op.drop_table("learning_objectives")
    op.drop_index("ix_regions_published_order", table_name="curriculum_regions")
    op.drop_table("curriculum_regions")
    op.drop_table("player_profiles")
