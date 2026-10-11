from uuid import uuid4

import pytest
from BackendAPI.app.db.models import (
    CodingChallengeDefinition,
    EvaluationAttempt,
    PlayerProfile,
    PlayerProgression,
    PlayerQuestEvent,
    PlayerQuestProgress,
    PlayerQuestRewardLedger,
    SubmissionRecord,
)
from BackendAPI.app.schemas import (
    ChallengeOut,
    ChallengeSubmissionRequest,
    EvaluationTestResult,
    WorkerEvaluationResponse,
)
from BackendAPI.app.services.quest_events import QuestEventError
from BackendAPI.app.services.submissions import (
    SubmissionError,
    apply_worker_result,
    build_worker_job,
    create_submission,
    get_owned_submission,
)
from pydantic import ValidationError


def _profile(session, subject: str = "submission-player") -> PlayerProfile:
    profile = PlayerProfile(identity_subject=subject, display_name="Learner", locale="en")
    session.add(profile)
    session.flush()
    session.add(PlayerProgression(player_profile_id=profile.id))
    session.commit()
    return profile


def _payload(source: str = "def signal_coordinate(x, y):\n    return (x, y)\n", key=None):
    return ChallengeSubmissionRequest(
        clientSubmissionId=key or uuid4(), challengeVersion=1, source=source
    )


def _passed_worker_result(submission: SubmissionRecord) -> WorkerEvaluationResponse:
    return WorkerEvaluationResponse(
        submissionId=submission.id,
        challengeSlug=submission.challenge_slug,
        challengeVersion=submission.challenge_version,
        evaluatorVersion="python-v1",
        visibleResults=[EvaluationTestResult(passed=True) for _ in range(2)],
        hiddenPassed=2,
        hiddenTotal=2,
    )


def test_submission_creation_is_idempotent_and_ownership_scoped(db_session):
    owner = _profile(db_session)
    other = _profile(db_session, "other-player")
    request = _payload()
    first, replayed = create_submission(db_session, owner, "signal-coordinate", request)
    assert first.status == "queued"
    assert replayed is False
    assert db_session.query(EvaluationAttempt).filter_by(submission_id=first.id).count() == 1

    replay, replayed = create_submission(db_session, owner, "signal-coordinate", request)
    assert replay.id == first.id
    assert replayed is True
    with pytest.raises(SubmissionError, match="different payload"):
        create_submission(
            db_session,
            owner,
            "signal-coordinate",
            _payload("different source", request.clientSubmissionId),
        )
    assert get_owned_submission(db_session, owner.id, first.id).id == first.id
    assert get_owned_submission(db_session, other.id, first.id) is None


def test_submission_validates_version_source_limit_and_rate_limit(db_session):
    owner = _profile(db_session)
    with pytest.raises(SubmissionError) as missing:
        create_submission(
            db_session,
            owner,
            "signal-coordinate",
            ChallengeSubmissionRequest(
                clientSubmissionId=uuid4(), challengeVersion=99, source="pass"
            ),
        )
    assert missing.value.code == "challenge_version_not_found"
    with pytest.raises(SubmissionError) as too_large:
        create_submission(db_session, owner, "signal-coordinate", _payload("x" * 8193))
    assert too_large.value.code == "source_too_large"
    for _ in range(5):
        create_submission(db_session, owner, "signal-coordinate", _payload())
    with pytest.raises(SubmissionError) as limited:
        create_submission(db_session, owner, "signal-coordinate", _payload())
    assert limited.value.status_code == 429
    with pytest.raises(ValidationError):
        ChallengeSubmissionRequest(clientSubmissionId=uuid4(), challengeVersion=1, source=" ")


def test_submission_rejects_published_version_without_evaluator_rules(db_session):
    owner = _profile(db_session)
    challenge = db_session.get(CodingChallengeDefinition, ("signal-coordinate", 1))
    challenge.public_content = {"kind": "legacy"}
    db_session.commit()

    with pytest.raises(SubmissionError) as not_evaluable:
        create_submission(db_session, owner, "signal-coordinate", _payload())
    assert not_evaluable.value.code == "challenge_not_evaluable"
    assert db_session.query(SubmissionRecord).count() == 0


def test_public_definition_excludes_private_tests_and_worker_job_uses_exact_version(db_session):
    owner = _profile(db_session)
    request = _payload()
    submission, _ = create_submission(db_session, owner, "signal-coordinate", request)
    job = build_worker_job(db_session, submission)
    public = ChallengeOut.model_validate(
        db_session.get(CodingChallengeDefinition, ("signal-coordinate", 1))
    ).model_dump(by_alias=True)
    assert "hiddenTests" not in public
    assert len(job["definition"]["hiddenTests"]) == 2
    assert job["challengeVersion"] == 1


def test_worker_result_computes_score_and_reward_once_with_quest_integration(db_session):
    owner = _profile(db_session)
    progress = PlayerQuestProgress(
        player_profile_id=owner.id,
        quest_slug="light-the-signal",
        quest_version=1,
        status="in_progress",
        revision=0,
        state={"objectiveCounts": {"activate-relay": 1, "reach-platform": 1}},
    )
    db_session.add(progress)
    db_session.commit()

    submission, _ = create_submission(db_session, owner, "signal-coordinate", _payload())
    result = _passed_worker_result(submission)
    evaluated = apply_worker_result(db_session, owner.id, submission.id, result)
    assert evaluated.status == "passed"
    assert evaluated.result_summary["scorePercent"] == 100
    assert db_session.get(PlayerProgression, owner.id).experience == 25
    assert (
        db_session.query(PlayerQuestEvent)
        .filter_by(player_profile_id=owner.id, evidence_submission_id=submission.id)
        .count()
        == 1
    )
    assert (
        db_session.query(PlayerQuestRewardLedger).filter_by(player_profile_id=owner.id).count() == 1
    )

    duplicate = apply_worker_result(db_session, owner.id, submission.id, result)
    assert duplicate.status == "passed"
    assert db_session.get(PlayerProgression, owner.id).experience == 25
    assert (
        db_session.query(PlayerQuestRewardLedger).filter_by(player_profile_id=owner.id).count() == 1
    )


def test_malformed_worker_and_timeout_never_grant_rewards(db_session):
    owner = _profile(db_session)
    submission, _ = create_submission(db_session, owner, "signal-coordinate", _payload())
    malformed = WorkerEvaluationResponse(
        submissionId=uuid4(),
        challengeSlug="signal-coordinate",
        challengeVersion=1,
        evaluatorVersion="python-v1",
        visibleResults=[EvaluationTestResult(passed=True) for _ in range(2)],
        hiddenPassed=2,
        hiddenTotal=2,
    )
    result = apply_worker_result(db_session, owner.id, submission.id, malformed)
    assert result.status == "internal_error"
    assert db_session.get(PlayerProgression, owner.id).experience == 0
    assert db_session.query(PlayerQuestRewardLedger).count() == 0

    second, _ = create_submission(db_session, owner, "signal-coordinate", _payload())
    timeout = WorkerEvaluationResponse(
        submissionId=second.id,
        challengeSlug="signal-coordinate",
        challengeVersion=1,
        evaluatorVersion="python-v1",
        visibleResults=[],
        hiddenPassed=0,
        hiddenTotal=2,
        timedOut=True,
    )
    timed_out = apply_worker_result(db_session, owner.id, second.id, timeout)
    assert timed_out.status == "timed_out"
    assert db_session.get(PlayerProgression, owner.id).experience == 0
    assert db_session.query(PlayerQuestRewardLedger).count() == 0


def test_quest_reward_failure_rolls_back_pass_result(db_session, monkeypatch):
    owner = _profile(db_session)
    db_session.add(
        PlayerQuestProgress(
            player_profile_id=owner.id,
            quest_slug="light-the-signal",
            quest_version=1,
            status="in_progress",
            revision=0,
            state={"objectiveCounts": {"activate-relay": 1, "reach-platform": 1}},
        )
    )
    db_session.commit()
    submission, _ = create_submission(db_session, owner, "signal-coordinate", _payload())

    def fail_quest_event(*_args, **_kwargs):
        raise QuestEventError(500, "transaction_failed", "forced transaction failure")

    monkeypatch.setattr("BackendAPI.app.services.submissions.submit_quest_event", fail_quest_event)
    with pytest.raises(QuestEventError):
        apply_worker_result(db_session, owner.id, submission.id, _passed_worker_result(submission))

    persisted = db_session.get(SubmissionRecord, submission.id)
    assert persisted.status == "queued"
    assert db_session.get(PlayerProgression, owner.id).experience == 0
    assert db_session.query(PlayerQuestRewardLedger).count() == 0
