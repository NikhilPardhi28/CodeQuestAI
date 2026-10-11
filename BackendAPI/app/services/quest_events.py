from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from BackendAPI.app.db.models import (
    CodingChallengeDefinition,
    PlayerProfile,
    PlayerProgression,
    PlayerQuestEvent,
    PlayerQuestProgress,
    PlayerQuestRewardLedger,
    QuestDefinition,
    QuestEventTarget,
    QuestObjectivePrerequisite,
    QuestObjectiveRule,
    QuestRewardRule,
    SubmissionRecord,
)
from BackendAPI.app.schemas import QuestEventRequest


class QuestEventError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        current_state: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.current_state = current_state


def _insert_ignore_conflict(
    session: Session, model, values: dict[str, Any], index_elements: list[str]
):
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        statement = (
            pg_insert(model).values(**values).on_conflict_do_nothing(index_elements=index_elements)
        )
    elif dialect == "sqlite":
        statement = (
            sqlite_insert(model)
            .values(**values)
            .on_conflict_do_nothing(index_elements=index_elements)
        )
    else:
        raise RuntimeError(
            f"Quest event persistence is unsupported for database dialect {dialect}."
        )
    session.execute(statement)


def _canonical_hash(quest_slug: str, payload: QuestEventRequest) -> str:
    canonical = {
        "questSlug": quest_slug,
        **payload.model_dump(mode="json", by_alias=True, exclude_none=True),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _progress_counts(row: PlayerQuestProgress) -> dict[str, int]:
    state = row.state if isinstance(row.state, dict) else {}
    raw = state.get("objectiveCounts", {})
    if not isinstance(raw, dict):
        return {}
    return {str(key): max(0, int(value)) for key, value in raw.items() if isinstance(value, int)}


def _objective_progress(
    session: Session, quest_slug: str, quest_version: int, counts: dict[str, int]
):
    rules = session.scalars(
        select(QuestObjectiveRule)
        .where(
            QuestObjectiveRule.quest_slug == quest_slug,
            QuestObjectiveRule.quest_version == quest_version,
        )
        .order_by(QuestObjectiveRule.objective_id)
    ).all()
    return [
        {
            "objectiveId": rule.objective_id,
            "completedCount": min(counts.get(rule.objective_id, 0), rule.required_count),
            "requiredCount": rule.required_count,
            "completed": counts.get(rule.objective_id, 0) >= rule.required_count,
        }
        for rule in rules
    ]


def _snapshot(session: Session, row: PlayerQuestProgress) -> dict[str, Any]:
    return {
        "questSlug": row.quest_slug,
        "questVersion": row.quest_version,
        "status": row.status,
        "revision": row.revision,
        "objectiveProgress": _objective_progress(
            session, row.quest_slug, row.quest_version, _progress_counts(row)
        ),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def _validate_definition(session: Session, quest: QuestDefinition) -> list[QuestObjectiveRule]:
    rules = session.scalars(
        select(QuestObjectiveRule)
        .where(
            QuestObjectiveRule.quest_slug == quest.slug,
            QuestObjectiveRule.quest_version == quest.version,
        )
        .order_by(QuestObjectiveRule.objective_id)
    ).all()
    if not rules:
        raise QuestEventError(
            409, "quest_definition_invalid", "The quest has no server objective rules."
        )
    rule_ids = {rule.objective_id for rule in rules}
    prerequisites: dict[str, set[str]] = {rule.objective_id: set() for rule in rules}
    edges = session.scalars(
        select(QuestObjectivePrerequisite).where(
            QuestObjectivePrerequisite.quest_slug == quest.slug,
            QuestObjectivePrerequisite.quest_version == quest.version,
        )
    ).all()
    for edge in edges:
        if edge.objective_id not in rule_ids or edge.prerequisite_objective_id not in rule_ids:
            raise QuestEventError(
                409, "quest_definition_invalid", "The quest has an invalid objective prerequisite."
            )
        prerequisites[edge.objective_id].add(edge.prerequisite_objective_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(objective_id: str) -> None:
        if objective_id in visiting:
            raise QuestEventError(
                409, "quest_definition_invalid", "The quest objective graph contains a cycle."
            )
        if objective_id in visited:
            return
        visiting.add(objective_id)
        for required_id in prerequisites[objective_id]:
            visit(required_id)
        visiting.remove(objective_id)
        visited.add(objective_id)

    for objective_id in rule_ids:
        visit(objective_id)

    for rule in rules:
        target = session.get(
            QuestEventTarget, (rule.event_type, rule.target_id, rule.target_version)
        )
        if target is None or not target.is_enabled:
            raise QuestEventError(
                409, "quest_definition_invalid", "The quest contains an unregistered target."
            )
        if rule.event_type == "challenge_passed":
            challenge = session.get(
                CodingChallengeDefinition, (rule.target_id, rule.target_version)
            )
            if challenge is None or not challenge.is_published:
                raise QuestEventError(
                    409,
                    "quest_definition_invalid",
                    "The quest references an unsupported challenge version.",
                )
        if rule.event_type == "prerequisite_completed":
            prerequisite_quest = session.get(QuestDefinition, (rule.target_id, rule.target_version))
            if prerequisite_quest is None or not prerequisite_quest.is_published:
                raise QuestEventError(
                    409,
                    "quest_definition_invalid",
                    "The quest references an unsupported prerequisite quest version.",
                )
    rewards = session.scalars(
        select(QuestRewardRule).where(
            QuestRewardRule.quest_slug == quest.slug,
            QuestRewardRule.quest_version == quest.version,
        )
    ).all()
    if rewards and not any(rule.event_type == "challenge_passed" for rule in rules):
        raise QuestEventError(
            409, "quest_definition_invalid", "XP rewards require a trusted challenge objective."
        )
    return rules


def _build_response(
    session: Session,
    row: PlayerQuestProgress,
    rewards: list[dict[str, Any]],
    progression: PlayerProgression,
) -> dict[str, Any]:
    return {
        "questSlug": row.quest_slug,
        "questVersion": row.quest_version,
        "status": row.status,
        "revision": row.revision,
        "objectiveProgress": _objective_progress(
            session, row.quest_slug, row.quest_version, _progress_counts(row)
        ),
        "newlyGrantedRewards": rewards,
        "progression": {
            "experience": progression.experience,
            "level": progression.level,
            "revision": progression.revision,
            "updatedAt": progression.updated_at.isoformat() if progression.updated_at else None,
        },
        "replayed": False,
    }


def _ensure_quest_progress(session: Session, profile_id: uuid.UUID, quest: QuestDefinition) -> None:
    values = {
        "player_profile_id": profile_id,
        "quest_slug": quest.slug,
        "quest_version": quest.version,
        "status": "available",
        "revision": 0,
        "state": {"objectiveCounts": {}},
    }
    _insert_ignore_conflict(
        session,
        PlayerQuestProgress,
        values,
        ["player_profile_id", "quest_slug", "quest_version"],
    )
    session.flush()


def submit_quest_event(
    session: Session,
    profile: PlayerProfile,
    quest_slug: str,
    payload: QuestEventRequest,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    payload_hash = _canonical_hash(quest_slug, payload)
    savepoint = None if commit else session.begin_nested()
    try:
        prior = session.scalar(
            select(PlayerQuestEvent).where(
                PlayerQuestEvent.player_profile_id == profile.id,
                PlayerQuestEvent.event_id == payload.eventId,
            )
        )
        if prior is not None:
            if prior.payload_hash != payload_hash:
                raise QuestEventError(
                    409,
                    "idempotency_key_reused",
                    "This event ID was already used with a different payload.",
                )
            session.commit()
            response = dict(prior.response or {})
            response["replayed"] = True
            return response

        quest = session.get(QuestDefinition, (quest_slug, payload.questVersion))
        if quest is None or not quest.is_published:
            raise QuestEventError(
                404, "quest_version_not_found", "The published quest version was not found."
            )
        rules = _validate_definition(session, quest)
        target = session.get(
            QuestEventTarget, (payload.eventType, payload.targetId, payload.targetVersion)
        )
        if target is None or not target.is_enabled:
            raise QuestEventError(
                409, "quest_target_not_registered", "The event target is not registered."
            )

        evidence_submission_id = payload.challengeSubmissionId
        if payload.eventType == "challenge_passed":
            if evidence_submission_id is None:
                raise QuestEventError(
                    422,
                    "challenge_evidence_required",
                    "A challenge submission reference is required.",
                )
            submission = session.scalar(
                select(SubmissionRecord)
                .where(SubmissionRecord.id == evidence_submission_id)
                .with_for_update()
            )
            if (
                submission is None
                or submission.player_profile_id != profile.id
                or submission.status != "passed"
                or submission.challenge_slug != payload.targetId
                or submission.challenge_version != payload.targetVersion
            ):
                raise QuestEventError(
                    409,
                    "challenge_evidence_invalid",
                    "No passed submission matches this profile and challenge version.",
                )
        elif evidence_submission_id is not None:
            raise QuestEventError(
                422,
                "challenge_evidence_not_allowed",
                "Submission evidence is only valid for challenge_passed.",
            )

        event_values = {
            "id": uuid.uuid4(),
            "player_profile_id": profile.id,
            "event_id": payload.eventId,
            "payload_hash": payload_hash,
            "quest_slug": quest.slug,
            "quest_version": quest.version,
            "event_type": payload.eventType,
            "target_id": payload.targetId,
            "target_version": payload.targetVersion,
            "evidence_submission_id": evidence_submission_id,
        }
        _insert_ignore_conflict(
            session,
            PlayerQuestEvent,
            event_values,
            ["player_profile_id", "event_id"],
        )
        session.flush()
        event_record = session.scalar(
            select(PlayerQuestEvent).where(
                PlayerQuestEvent.player_profile_id == profile.id,
                PlayerQuestEvent.event_id == payload.eventId,
            )
        )
        if event_record.payload_hash != payload_hash:
            raise QuestEventError(
                409,
                "idempotency_key_reused",
                "This event ID was already used with a different payload.",
            )
        if event_record.response is not None:
            session.commit()
            response = dict(event_record.response)
            response["replayed"] = True
            return response

        _ensure_quest_progress(session, profile.id, quest)
        row = session.scalar(
            select(PlayerQuestProgress)
            .where(
                PlayerQuestProgress.player_profile_id == profile.id,
                PlayerQuestProgress.quest_slug == quest.slug,
                PlayerQuestProgress.quest_version == quest.version,
            )
            .with_for_update()
        )
        if row.revision != payload.expectedRevision:
            raise QuestEventError(
                409,
                "quest_revision_conflict",
                "Quest progress changed since the supplied revision.",
                _snapshot(session, row),
            )
        if row.status == "completed" or row.status == "abandoned" or row.status == "locked":
            raise QuestEventError(
                409,
                "quest_transition_invalid",
                "This quest cannot accept events in its current state.",
                _snapshot(session, row),
            )

        counts = _progress_counts(row)
        matching_rules = [
            rule
            for rule in rules
            if rule.event_type == payload.eventType
            and rule.target_id == payload.targetId
            and rule.target_version == payload.targetVersion
        ]
        if not matching_rules:
            raise QuestEventError(
                409,
                "quest_event_not_allowed",
                "This event is not allowed by the published quest rules.",
            )
        if payload.eventType == "prerequisite_completed":
            prerequisite_progress = session.get(
                PlayerQuestProgress,
                (profile.id, payload.targetId, payload.targetVersion),
            )
            if prerequisite_progress is None or prerequisite_progress.status != "completed":
                raise QuestEventError(
                    409, "quest_prerequisite_not_met", "The prerequisite quest is not completed."
                )
        edges = session.scalars(
            select(QuestObjectivePrerequisite).where(
                QuestObjectivePrerequisite.quest_slug == quest.slug,
                QuestObjectivePrerequisite.quest_version == quest.version,
            )
        ).all()
        prereqs_by_objective: dict[str, set[str]] = {}
        for edge in edges:
            prereqs_by_objective.setdefault(edge.objective_id, set()).add(
                edge.prerequisite_objective_id
            )
        eligible = [
            rule
            for rule in matching_rules
            if counts.get(rule.objective_id, 0) < rule.required_count
            if all(
                counts.get(required_id, 0)
                >= next(item.required_count for item in rules if item.objective_id == required_id)
                for required_id in prereqs_by_objective.get(rule.objective_id, set())
            )
        ]
        if not eligible:
            if all(
                counts.get(rule.objective_id, 0) >= rule.required_count for rule in matching_rules
            ):
                raise QuestEventError(
                    409,
                    "quest_objective_already_completed",
                    "All objectives for this event have already been completed.",
                )
            raise QuestEventError(
                409,
                "quest_prerequisite_not_met",
                "Complete the required objective before submitting this event.",
            )

        existing_event = (
            session.scalar(
                select(PlayerQuestEvent.id).where(
                    PlayerQuestEvent.player_profile_id == profile.id,
                    PlayerQuestEvent.quest_slug == quest.slug,
                    PlayerQuestEvent.quest_version == quest.version,
                    PlayerQuestEvent.id != event_record.id,
                    PlayerQuestEvent.evidence_submission_id == evidence_submission_id,
                )
            )
            if evidence_submission_id is not None
            else None
        )
        if existing_event is not None:
            raise QuestEventError(
                409,
                "challenge_evidence_already_used",
                "This passed submission has already advanced this quest.",
            )

        for rule in eligible:
            counts[rule.objective_id] = min(
                rule.required_count, counts.get(rule.objective_id, 0) + 1
            )
        row.state = {"objectiveCounts": counts}
        was_completed = row.status == "completed"
        row.status = "in_progress"
        if all(counts.get(rule.objective_id, 0) >= rule.required_count for rule in rules):
            row.status = "completed"
        row.revision += 1
        row.updated_at = datetime.now(UTC)

        granted: list[dict[str, Any]] = []
        progression = session.scalar(
            select(PlayerProgression)
            .where(PlayerProgression.player_profile_id == profile.id)
            .with_for_update()
        )
        if progression is None:
            raise QuestEventError(
                409, "player_progression_not_found", "Player progression is not initialized."
            )
        if row.status == "completed" and not was_completed:
            reward_rules = session.scalars(
                select(QuestRewardRule).where(
                    QuestRewardRule.quest_slug == quest.slug,
                    QuestRewardRule.quest_version == quest.version,
                )
            ).all()
            for reward in reward_rules:
                ledger = PlayerQuestRewardLedger(
                    player_profile_id=profile.id,
                    quest_slug=quest.slug,
                    quest_version=quest.version,
                    reward_id=reward.reward_id,
                    experience_points=reward.experience_points,
                )
                session.add(ledger)
                progression.experience += reward.experience_points
                progression.revision += 1
                progression.updated_at = datetime.now(UTC)
                granted.append(
                    {
                        "rewardId": reward.reward_id,
                        "rewardType": reward.reward_type,
                        "experiencePoints": reward.experience_points,
                    }
                )

        response = _build_response(session, row, granted, progression)
        event_record.response = response
        if commit:
            session.commit()
        else:
            session.flush()
            savepoint.commit()
        return response
    except QuestEventError:
        if commit:
            session.rollback()
        elif savepoint is not None:
            savepoint.rollback()
        raise
    except IntegrityError as exc:
        if commit:
            session.rollback()
        elif savepoint is not None:
            savepoint.rollback()
        raise QuestEventError(
            409,
            "quest_event_conflict",
            "The event conflicts with an existing quest or reward record.",
        ) from exc
    except Exception:
        if commit:
            session.rollback()
        elif savepoint is not None:
            savepoint.rollback()
        raise


def get_quest_definition(session: Session, slug: str, version: int) -> dict[str, Any] | None:
    quest = session.get(QuestDefinition, (slug, version))
    if quest is None or not quest.is_published:
        return None
    rules = _validate_definition(session, quest)
    edges = session.scalars(
        select(QuestObjectivePrerequisite).where(
            QuestObjectivePrerequisite.quest_slug == slug,
            QuestObjectivePrerequisite.quest_version == version,
        )
    ).all()
    prerequisites_by_objective: dict[str, list[str]] = {}
    for edge in edges:
        prerequisites_by_objective.setdefault(edge.objective_id, []).append(
            edge.prerequisite_objective_id
        )
    rewards = session.scalars(
        select(QuestRewardRule).where(
            QuestRewardRule.quest_slug == slug,
            QuestRewardRule.quest_version == version,
        )
    ).all()
    return {
        "slug": quest.slug,
        "version": quest.version,
        "title": quest.title,
        "summary": quest.summary,
        "objectiveRules": [
            {
                "objectiveId": rule.objective_id,
                "eventType": rule.event_type,
                "targetId": rule.target_id,
                "targetVersion": rule.target_version,
                "requiredCount": rule.required_count,
                "prerequisiteObjectiveIds": sorted(
                    prerequisites_by_objective.get(rule.objective_id, [])
                ),
            }
            for rule in rules
        ],
        "prerequisiteQuestIds": sorted(
            rule.target_id for rule in rules if rule.event_type == "prerequisite_completed"
        ),
        "rewards": [
            {
                "rewardId": reward.reward_id,
                "rewardType": reward.reward_type,
                "experiencePoints": reward.experience_points,
            }
            for reward in rewards
        ],
    }


def list_profile_quest_progress(session: Session, profile_id: uuid.UUID, limit: int, offset: int):
    statement = (
        select(PlayerQuestProgress)
        .where(PlayerQuestProgress.player_profile_id == profile_id)
        .order_by(PlayerQuestProgress.updated_at.desc(), PlayerQuestProgress.quest_slug)
    )
    rows = session.scalars(statement.offset(offset).limit(limit)).all()
    total = (
        session.scalar(
            select(func.count())
            .select_from(PlayerQuestProgress)
            .where(PlayerQuestProgress.player_profile_id == profile_id)
        )
        or 0
    )
    return [
        {
            "questSlug": row.quest_slug,
            "questVersion": row.quest_version,
            "status": row.status,
            "revision": row.revision,
            "objectiveProgress": _objective_progress(
                session, row.quest_slug, row.quest_version, _progress_counts(row)
            ),
            "createdAt": row.created_at,
            "updatedAt": row.updated_at,
        }
        for row in rows
    ], total
