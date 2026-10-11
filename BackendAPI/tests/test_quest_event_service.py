from uuid import uuid4

import pytest
from BackendAPI.app.db.models import (
    PlayerProfile,
    PlayerProgression,
    PlayerQuestEvent,
    PlayerQuestProgress,
    PlayerQuestRewardLedger,
    QuestObjectivePrerequisite,
    SubmissionRecord,
)
from BackendAPI.app.schemas import QuestEventRequest
from BackendAPI.app.services import quest_events
from BackendAPI.app.services.quest_events import QuestEventError
from pydantic import ValidationError


def _profile(db_session, subject="service-player"):
    profile = PlayerProfile(identity_subject=subject, display_name=subject)
    db_session.add(profile)
    db_session.flush()
    db_session.add(PlayerProgression(player_profile_id=profile.id))
    db_session.commit()
    return profile


def _payload(event_type, target_id, revision, event_id=None, submission_id=None, quest_version=1):
    return QuestEventRequest(
        eventId=event_id or uuid4(),
        questVersion=quest_version,
        expectedRevision=revision,
        eventType=event_type,
        targetId=target_id,
        targetVersion=1,
        challengeSubmissionId=submission_id,
    )


def test_service_idempotency_revision_ownership_and_server_reward(db_session):
    profile = _profile(db_session)
    interaction = _payload("interact", "relay-switch", 0)
    first = quest_events.submit_quest_event(db_session, profile, "light-the-signal", interaction)
    assert first["revision"] == 1
    replay = quest_events.submit_quest_event(db_session, profile, "light-the-signal", interaction)
    assert replay["replayed"] is True

    with pytest.raises(QuestEventError, match="different payload") as conflict:
        quest_events.submit_quest_event(
            db_session,
            profile,
            "light-the-signal",
            _payload("interact", "signal-platform", 0, event_id=interaction.eventId),
        )
    assert conflict.value.code == "idempotency_key_reused"

    with pytest.raises(QuestEventError) as stale:
        quest_events.submit_quest_event(
            db_session, profile, "light-the-signal", _payload("checkpoint", "signal-platform", 0)
        )
    assert stale.value.code == "quest_revision_conflict"
    assert stale.value.current_state["revision"] == 1

    db_session.add(
        SubmissionRecord(
            player_profile_id=profile.id,
            challenge_slug="signal-coordinate",
            challenge_version=1,
            client_submission_id=uuid4(),
            status="passed",
        )
    )
    db_session.commit()
    submission = db_session.query(SubmissionRecord).filter_by(player_profile_id=profile.id).one()
    progress = db_session.get(PlayerQuestProgress, (profile.id, "light-the-signal", 1))
    progress.revision = 2
    progress.state = {"objectiveCounts": {"activate-relay": 1, "reach-platform": 1}}
    progress.status = "in_progress"
    db_session.commit()
    foreign_profile = _profile(db_session, "foreign-player")
    foreign_submission = SubmissionRecord(
        player_profile_id=foreign_profile.id,
        challenge_slug="signal-coordinate",
        challenge_version=1,
        client_submission_id=uuid4(),
        status="passed",
    )
    db_session.add(foreign_submission)
    db_session.commit()
    with pytest.raises(QuestEventError) as foreign_evidence:
        quest_events.submit_quest_event(
            db_session,
            profile,
            "light-the-signal",
            _payload(
                "challenge_passed", "signal-coordinate", 2, submission_id=foreign_submission.id
            ),
        )
    assert foreign_evidence.value.code == "challenge_evidence_invalid"
    challenge = _payload("challenge_passed", "signal-coordinate", 2, submission_id=submission.id)
    result = quest_events.submit_quest_event(db_session, profile, "light-the-signal", challenge)
    assert result["status"] == "completed"
    assert result["progression"]["experience"] == 25
    assert (
        db_session.query(PlayerQuestRewardLedger).filter_by(player_profile_id=profile.id).count()
        == 1
    )


def test_service_prerequisite_invalid_version_and_transaction_rollback(db_session, monkeypatch):
    profile = _profile(db_session)
    with pytest.raises(QuestEventError) as prerequisite:
        quest_events.submit_quest_event(
            db_session,
            profile,
            "light-the-signal",
            _payload("checkpoint", "signal-platform", 0),
        )
    assert prerequisite.value.code == "quest_prerequisite_not_met"
    with pytest.raises(QuestEventError) as missing:
        quest_events.submit_quest_event(
            db_session,
            profile,
            "light-the-signal",
            _payload("interact", "relay-switch", 0, quest_version=999),
        )
    assert missing.value.code == "quest_version_not_found"

    original = quest_events._build_response
    monkeypatch.setattr(
        quest_events,
        "_build_response",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("forced response failure")),
    )
    with pytest.raises(RuntimeError, match="forced response failure"):
        quest_events.submit_quest_event(
            db_session, profile, "light-the-signal", _payload("interact", "relay-switch", 0)
        )
    monkeypatch.setattr(quest_events, "_build_response", original)
    assert db_session.query(PlayerQuestEvent).filter_by(player_profile_id=profile.id).count() == 0
    assert (
        db_session.query(PlayerQuestProgress).filter_by(player_profile_id=profile.id).count() == 0
    )


def test_malformed_objective_prerequisite_graph_is_rejected(db_session):
    profile = _profile(db_session)
    db_session.add_all(
        [
            QuestObjectivePrerequisite(
                quest_slug="light-the-signal",
                quest_version=1,
                objective_id="activate-relay",
                prerequisite_objective_id="reach-platform",
            ),
        ]
    )
    db_session.commit()
    with pytest.raises(QuestEventError) as invalid:
        quest_events.submit_quest_event(
            db_session, profile, "light-the-signal", _payload("interact", "relay-switch", 0)
        )
    assert invalid.value.code == "quest_definition_invalid"


def test_unregistered_targets_and_unknown_event_types_are_rejected(db_session):
    profile = _profile(db_session)
    with pytest.raises(QuestEventError) as target:
        quest_events.submit_quest_event(
            db_session,
            profile,
            "light-the-signal",
            _payload("interact", "unregistered-target", 0),
        )
    assert target.value.code == "quest_target_not_registered"
    with pytest.raises(ValidationError):
        QuestEventRequest(
            eventId=uuid4(),
            questVersion=1,
            expectedRevision=0,
            eventType="unknown",
            targetId="relay-switch",
        )
