from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from BackendAPI.app.db.base import Base


class PlayerProfile(Base):
    __tablename__ = "player_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identity_subject: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CurriculumRegion(Base):
    __tablename__ = "curriculum_regions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["unlock_region_slug", "unlock_region_version"],
            ["curriculum_regions.slug", "curriculum_regions.version"],
            name="fk_region_unlock_region_version",
        ),
        CheckConstraint("version > 0", name="ck_region_version_positive"),
        CheckConstraint("sort_order >= 0", name="ck_region_sort_nonnegative"),
        Index("ix_regions_published_order", "is_published", "sort_order"),
    )

    slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    unlock_region_slug: Mapped[str | None] = mapped_column(String(80), nullable=True)
    unlock_region_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LearningObjective(Base):
    __tablename__ = "learning_objectives"
    __table_args__ = (
        ForeignKeyConstraint(
            ["region_slug", "region_version"],
            ["curriculum_regions.slug", "curriculum_regions.version"],
            name="fk_objective_region_version",
            ondelete="RESTRICT",
        ),
        CheckConstraint("version > 0", name="ck_objective_version_positive"),
        CheckConstraint("sort_order >= 0", name="ck_objective_sort_nonnegative"),
        Index("ix_objectives_region_order", "region_slug", "region_version", "sort_order"),
    )

    slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    region_version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    prerequisites: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class QuestDefinition(Base):
    __tablename__ = "quest_definitions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["region_slug", "region_version"],
            ["curriculum_regions.slug", "curriculum_regions.version"],
            name="fk_quest_region_version",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["objective_slug", "objective_version"],
            ["learning_objectives.slug", "learning_objectives.version"],
            name="fk_quest_objective_version",
            ondelete="RESTRICT",
        ),
        CheckConstraint("version > 0", name="ck_quest_version_positive"),
        CheckConstraint(
            "(objective_slug IS NULL AND objective_version IS NULL) OR "
            "(objective_slug IS NOT NULL AND objective_version IS NOT NULL)",
            name="ck_quest_objective_version_pair",
        ),
        Index("ix_quests_region_published", "region_slug", "is_published"),
    )

    slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    region_version: Mapped[int] = mapped_column(Integer, nullable=False)
    objective_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    objective_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    public_content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class QuestEventTarget(Base):
    __tablename__ = "quest_event_targets"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('interact', 'checkpoint', 'challenge_passed', "
            "'prerequisite_completed')",
            name="ck_quest_event_target_type",
        ),
        CheckConstraint("target_version > 0", name="ck_quest_event_target_version_positive"),
    )

    event_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    target_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    target_version: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class QuestObjectiveRule(Base):
    __tablename__ = "quest_objective_rules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["quest_slug", "quest_version"],
            ["quest_definitions.slug", "quest_definitions.version"],
            name="fk_quest_objective_rule_definition",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["event_type", "target_id", "target_version"],
            [
                "quest_event_targets.event_type",
                "quest_event_targets.target_id",
                "quest_event_targets.target_version",
            ],
            name="fk_quest_objective_rule_target",
            ondelete="RESTRICT",
        ),
        CheckConstraint("required_count > 0", name="ck_quest_objective_required_positive"),
        CheckConstraint(
            "event_type = 'challenge_passed' OR required_count = 1",
            name="ck_quest_objective_repeat_requires_challenge",
        ),
        Index("ix_quest_objective_rule_target", "event_type", "target_id", "target_version"),
    )

    quest_slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    quest_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    objective_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(120), nullable=False)
    target_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    required_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class QuestObjectivePrerequisite(Base):
    __tablename__ = "quest_objective_prerequisites"
    __table_args__ = (
        ForeignKeyConstraint(
            ["quest_slug", "quest_version", "objective_id"],
            [
                "quest_objective_rules.quest_slug",
                "quest_objective_rules.quest_version",
                "quest_objective_rules.objective_id",
            ],
            name="fk_quest_objective_prerequisite_objective",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["quest_slug", "quest_version", "prerequisite_objective_id"],
            [
                "quest_objective_rules.quest_slug",
                "quest_objective_rules.quest_version",
                "quest_objective_rules.objective_id",
            ],
            name="fk_quest_objective_prerequisite_required",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "objective_id <> prerequisite_objective_id",
            name="ck_quest_objective_not_self_prerequisite",
        ),
    )

    quest_slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    quest_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    objective_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    prerequisite_objective_id: Mapped[str] = mapped_column(String(100), primary_key=True)


class QuestRewardRule(Base):
    __tablename__ = "quest_reward_rules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["quest_slug", "quest_version"],
            ["quest_definitions.slug", "quest_definitions.version"],
            name="fk_quest_reward_rule_definition",
            ondelete="RESTRICT",
        ),
        CheckConstraint("reward_type = 'experience'", name="ck_quest_reward_type_supported"),
        CheckConstraint("experience_points > 0", name="ck_quest_reward_experience_positive"),
    )

    quest_slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    quest_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    reward_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    reward_type: Mapped[str] = mapped_column(String(24), nullable=False, default="experience")
    experience_points: Mapped[int] = mapped_column(Integer, nullable=False)


class PlayerQuestProgress(Base):
    __tablename__ = "player_quest_progress"
    __table_args__ = (
        ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_quest_progress_player",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["quest_slug", "quest_version"],
            ["quest_definitions.slug", "quest_definitions.version"],
            name="fk_quest_progress_definition",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('locked', 'available', 'in_progress', 'completed', 'abandoned')",
            name="ck_quest_progress_status",
        ),
        Index("ix_quest_progress_player_updated", "player_profile_id", "updated_at"),
        CheckConstraint("revision >= 0", name="ck_quest_progress_revision_nonnegative"),
    )

    player_profile_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    quest_slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    quest_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="available")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlayerQuestEvent(Base):
    __tablename__ = "player_quest_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_quest_event_player",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["quest_slug", "quest_version"],
            ["quest_definitions.slug", "quest_definitions.version"],
            name="fk_quest_event_definition",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["event_type", "target_id", "target_version"],
            [
                "quest_event_targets.event_type",
                "quest_event_targets.target_id",
                "quest_event_targets.target_version",
            ],
            name="fk_quest_event_target",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["evidence_submission_id"],
            ["submission_records.id"],
            name="fk_quest_event_submission",
            ondelete="SET NULL",
        ),
        UniqueConstraint("player_profile_id", "event_id", name="uq_player_quest_event_idempotency"),
        CheckConstraint("length(payload_hash) = 64", name="ck_quest_event_payload_hash_length"),
        Index(
            "ix_player_quest_events_quest_created",
            "player_profile_id",
            "quest_slug",
            "quest_version",
            "created_at",
        ),
        Index(
            "uq_player_quest_submission_evidence",
            "player_profile_id",
            "quest_slug",
            "quest_version",
            "evidence_submission_id",
            unique=True,
            postgresql_where=text("evidence_submission_id IS NOT NULL"),
            sqlite_where=text("evidence_submission_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_profile_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    quest_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    quest_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(120), nullable=False)
    target_version: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    response: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PlayerQuestRewardLedger(Base):
    __tablename__ = "player_quest_reward_ledger"
    __table_args__ = (
        ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_quest_reward_player",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["quest_slug", "quest_version", "reward_id"],
            [
                "quest_reward_rules.quest_slug",
                "quest_reward_rules.quest_version",
                "quest_reward_rules.reward_id",
            ],
            name="fk_quest_reward_ledger_rule",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "player_profile_id",
            "quest_slug",
            "quest_version",
            "reward_id",
            name="uq_player_quest_reward_once",
        ),
        CheckConstraint("experience_points > 0", name="ck_quest_reward_ledger_experience_positive"),
        Index("ix_player_quest_rewards_player_date", "player_profile_id", "granted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_profile_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    quest_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    quest_version: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_id: Mapped[str] = mapped_column(String(100), nullable=False)
    experience_points: Mapped[int] = mapped_column(Integer, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CodingChallengeDefinition(Base):
    __tablename__ = "coding_challenge_definitions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["objective_slug", "objective_version"],
            ["learning_objectives.slug", "learning_objectives.version"],
            name="fk_challenge_objective_version",
            ondelete="RESTRICT",
        ),
        CheckConstraint("version > 0", name="ck_challenge_version_positive"),
        CheckConstraint("length(content_digest) = 64", name="ck_challenge_content_digest_length"),
        Index("ix_challenges_objective_published", "objective_slug", "is_published"),
    )

    slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    objective_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    objective_version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    statement: Mapped[str] = mapped_column(String(4000), nullable=False)
    public_content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    content_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SubmissionRecord(Base):
    __tablename__ = "submission_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_submission_player",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["challenge_slug", "challenge_version"],
            ["coding_challenge_definitions.slug", "coding_challenge_definitions.version"],
            name="fk_submission_challenge_definition",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "player_profile_id", "client_submission_id", name="uq_submission_client_id_per_player"
        ),
        CheckConstraint(
            "status IN ('received', 'queued', 'running', 'passed', 'failed', 'error')",
            name="ck_submission_status",
        ),
        CheckConstraint(
            "source_digest IS NULL OR length(source_digest) = 64",
            name="ck_submission_digest_length",
        ),
        Index("ix_submissions_player_created", "player_profile_id", "created_at"),
        Index("ix_submissions_challenge_created", "challenge_slug", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_profile_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    challenge_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    challenge_version: Mapped[int] = mapped_column(Integer, nullable=False)
    client_submission_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    source_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlayerProgression(Base):
    __tablename__ = "player_progression"
    __table_args__ = (
        ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_progression_player",
            ondelete="CASCADE",
        ),
        CheckConstraint("experience >= 0", name="ck_progression_experience_nonnegative"),
        CheckConstraint("level >= 1", name="ck_progression_level_positive"),
        CheckConstraint("revision >= 0", name="ck_progression_revision_nonnegative"),
    )

    player_profile_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AchievementDefinition(Base):
    __tablename__ = "achievement_definitions"
    __table_args__ = (CheckConstraint("version > 0", name="ck_achievement_version_positive"),)

    slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    criteria: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PlayerAchievementAward(Base):
    __tablename__ = "player_achievement_awards"
    __table_args__ = (
        ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.id"],
            name="fk_achievement_award_player",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["achievement_slug", "achievement_version"],
            ["achievement_definitions.slug", "achievement_definitions.version"],
            name="fk_achievement_award_definition",
            ondelete="RESTRICT",
        ),
        Index("ix_achievement_awards_player_date", "player_profile_id", "awarded_at"),
    )

    player_profile_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    achievement_slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    achievement_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
