from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    message: str
    retryable: bool = False
    correlationId: str
    currentState: dict[str, Any] | None = None


class Page(BaseModel, Generic[T]):
    items: list[T]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)


class OrmSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RegionOut(OrmSchema):
    slug: str
    version: int
    name: str
    summary: str
    sortOrder: int = Field(validation_alias="sort_order")
    unlockRegionSlug: str | None = Field(validation_alias="unlock_region_slug")


class ObjectiveOut(OrmSchema):
    slug: str
    version: int
    regionSlug: str = Field(validation_alias="region_slug")
    regionVersion: int = Field(validation_alias="region_version")
    title: str
    summary: str
    sortOrder: int = Field(validation_alias="sort_order")
    prerequisites: list[str]


class QuestOut(OrmSchema):
    slug: str
    version: int
    regionSlug: str = Field(validation_alias="region_slug")
    regionVersion: int = Field(validation_alias="region_version")
    objectiveSlug: str | None = Field(validation_alias="objective_slug")
    objectiveVersion: int | None = Field(validation_alias="objective_version")
    title: str
    summary: str
    publicContent: dict[str, Any] = Field(validation_alias="public_content")


class ChallengeOut(OrmSchema):
    slug: str
    version: int
    objectiveSlug: str = Field(validation_alias="objective_slug")
    objectiveVersion: int = Field(validation_alias="objective_version")
    title: str
    statement: str
    publicContent: dict[str, Any] = Field(validation_alias="public_content")
    timeLimitMs: int = Field(validation_alias="time_limit_ms")
    outputLimitBytes: int = Field(validation_alias="output_limit_bytes")
    maxSourceBytes: int = Field(validation_alias="max_source_bytes")


class ChallengeSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clientSubmissionId: UUID
    challengeVersion: int = Field(ge=1)
    source: str = Field(min_length=1, max_length=32768)

    @field_validator("source")
    @classmethod
    def validate_source_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 32768:
            raise ValueError("source exceeds the maximum UTF-8 byte length")
        if not value.strip():
            raise ValueError("source cannot be blank")
        return value


class SubmissionResultOut(BaseModel):
    hasResult: bool = False
    scorePercent: int | None = Field(default=None, ge=0, le=100)
    passedTests: int | None = Field(default=None, ge=0)
    totalTests: int | None = Field(default=None, ge=0)
    visibleResults: list[dict[str, str | bool]] = Field(default_factory=list)
    diagnostics: list[dict[str, str]] = Field(default_factory=list)


class SubmissionOut(OrmSchema):
    id: UUID
    challengeSlug: str = Field(validation_alias="challenge_slug")
    challengeVersion: int = Field(validation_alias="challenge_version")
    clientSubmissionId: UUID = Field(validation_alias="client_submission_id")
    status: Literal["queued", "running", "passed", "failed", "timed_out", "internal_error"]
    result: SubmissionResultOut | None = Field(default=None, validation_alias="result_summary")
    createdAt: datetime = Field(validation_alias="created_at")
    completedAt: datetime | None = Field(validation_alias="completed_at")


class ChallengeHintOut(BaseModel):
    challengeSlug: str
    challengeVersion: int
    level: int
    content: str


class EvaluationTestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    diagnosticCode: (
        Literal["syntax_error", "runtime_error", "wrong_answer", "timeout", "output_limit"] | None
    ) = None
    message: str = Field(default="", max_length=240)


class WorkerEvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submissionId: UUID
    challengeSlug: str = Field(min_length=1, max_length=100)
    challengeVersion: int = Field(ge=1)
    evaluatorVersion: str = Field(min_length=1, max_length=40)
    visibleResults: list[EvaluationTestResult] = Field(max_length=100)
    hiddenPassed: int = Field(ge=0, le=100)
    hiddenTotal: int = Field(ge=0, le=100)
    timedOut: bool = False
    infrastructureError: bool = False


class PlayerProfileUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    displayName: str = Field(min_length=1, max_length=50)
    locale: str = Field(
        default="en", min_length=2, max_length=16, pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$"
    )

    @field_validator("displayName")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("displayName cannot be blank")
        return normalized


class PlayerProfileOut(OrmSchema):
    id: UUID
    displayName: str = Field(validation_alias="display_name")
    locale: str
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime = Field(validation_alias="updated_at")


class QuestProgressOut(OrmSchema):
    questSlug: str = Field(validation_alias="quest_slug")
    questVersion: int = Field(validation_alias="quest_version")
    status: Literal["locked", "available", "in_progress", "completed", "abandoned"]
    state: dict[str, Any]
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime = Field(validation_alias="updated_at")


QuestEventType = Literal["interact", "checkpoint", "challenge_passed", "prerequisite_completed"]


class QuestEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventId: UUID
    questVersion: int = Field(ge=1)
    expectedRevision: int = Field(ge=0)
    eventType: QuestEventType
    targetId: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")
    targetVersion: int = Field(default=1, ge=1)
    challengeSubmissionId: UUID | None = None

    @field_validator("challengeSubmissionId", mode="before")
    @classmethod
    def empty_submission_is_absent(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def submission_evidence_only_for_challenges(self):
        if self.eventType == "challenge_passed" and self.challengeSubmissionId is None:
            raise ValueError("challengeSubmissionId is required for challenge_passed")
        if self.eventType != "challenge_passed" and self.challengeSubmissionId is not None:
            raise ValueError("challengeSubmissionId is only valid for challenge_passed")
        return self


class QuestObjectiveRuleOut(BaseModel):
    objectiveId: str
    eventType: QuestEventType
    targetId: str
    targetVersion: int
    requiredCount: int
    prerequisiteObjectiveIds: list[str]


class QuestRewardRuleOut(BaseModel):
    rewardId: str
    rewardType: Literal["experience"]
    experiencePoints: int


class QuestDefinitionV2Out(BaseModel):
    slug: str
    version: int
    title: str
    summary: str
    objectiveRules: list[QuestObjectiveRuleOut]
    prerequisiteQuestIds: list[str]
    rewards: list[QuestRewardRuleOut]


class QuestObjectiveProgressOut(BaseModel):
    objectiveId: str
    completedCount: int
    requiredCount: int
    completed: bool


class QuestProgressV2Out(BaseModel):
    questSlug: str
    questVersion: int
    status: Literal["locked", "available", "in_progress", "completed", "abandoned"]
    revision: int
    objectiveProgress: list[QuestObjectiveProgressOut]
    createdAt: datetime
    updatedAt: datetime


class QuestEventRewardOut(BaseModel):
    rewardId: str
    rewardType: Literal["experience"]
    experiencePoints: int


class QuestEventResult(BaseModel):
    questSlug: str
    questVersion: int
    status: Literal["locked", "available", "in_progress", "completed", "abandoned"]
    revision: int
    objectiveProgress: list[QuestObjectiveProgressOut]
    newlyGrantedRewards: list[QuestEventRewardOut]
    progression: ProgressionOut
    replayed: bool = False


class ProgressionOut(OrmSchema):
    experience: int
    level: int
    revision: int
    updatedAt: datetime = Field(validation_alias="updated_at")


class AchievementAwardOut(OrmSchema):
    achievementSlug: str = Field(validation_alias="achievement_slug")
    achievementVersion: int = Field(validation_alias="achievement_version")
    awardedAt: datetime = Field(validation_alias="awarded_at")
    source: str


class SubmissionMetadataOut(OrmSchema):
    id: UUID
    challengeSlug: str = Field(validation_alias="challenge_slug")
    challengeVersion: int = Field(validation_alias="challenge_version")
    clientSubmissionId: UUID = Field(validation_alias="client_submission_id")
    status: Literal[
        "received", "queued", "running", "passed", "failed", "timed_out", "internal_error"
    ]
    sourceDigest: str | None = Field(validation_alias="source_digest")
    createdAt: datetime = Field(validation_alias="created_at")
    completedAt: datetime | None = Field(validation_alias="completed_at")


class HealthOut(BaseModel):
    status: str


class ReadinessOut(BaseModel):
    status: str
    checks: dict[str, str]
