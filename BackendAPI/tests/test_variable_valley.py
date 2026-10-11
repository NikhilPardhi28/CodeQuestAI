from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from BackendAPI.app.db.models import (
    CodingChallengeDefinition,
    PlayerProfile,
    PlayerProgression,
    PlayerQuestProgress,
    PlayerQuestRewardLedger,
    SubmissionRecord,
)
from BackendAPI.app.schemas import (
    ChallengeOut,
    ChallengeSubmissionRequest,
    EvaluationTestResult,
    QuestEventRequest,
    WorkerEvaluationResponse,
)
from BackendAPI.app.services.quest_events import QuestEventError, submit_quest_event
from BackendAPI.app.services.submissions import apply_worker_result, create_submission

VALLEY_CHALLENGES = [
    "valley-name-tag",
    "valley-sunplot-area",
    "valley-signal-label",
    "valley-seed-count",
    "valley-beacon-message",
]


def _profile(session) -> PlayerProfile:
    profile = PlayerProfile(
        identity_subject="valley-test-player", display_name="Learner", locale="en"
    )
    session.add(profile)
    session.flush()
    session.add(PlayerProgression(player_profile_id=profile.id))
    session.commit()
    return profile


def _passed_result(submission: SubmissionRecord) -> WorkerEvaluationResponse:
    return WorkerEvaluationResponse(
        submissionId=submission.id,
        challengeSlug=submission.challenge_slug,
        challengeVersion=submission.challenge_version,
        evaluatorVersion="python-v1",
        visibleResults=[EvaluationTestResult(passed=True) for _ in range(2)],
        hiddenPassed=2,
        hiddenTotal=2,
    )


def test_variable_valley_catalog_is_versioned_and_keeps_hidden_cases_private(db_session, client):
    region = client.get("/api/v1/curriculum/regions/variable-valley")
    assert region.status_code == 200
    assert region.json()["version"] == 1
    assert region.json()["name"] == "Variable Valley"

    listed = client.get("/api/v1/challenges")
    valley = [item for item in listed.json()["items"] if item["slug"] in VALLEY_CHALLENGES]
    valley.sort(key=lambda item: item["publicContent"]["sequence"])
    assert [item["slug"] for item in valley] == VALLEY_CHALLENGES
    assert all(item["version"] == 1 for item in valley)
    assert [item["publicContent"]["sequence"] for item in valley] == [1, 2, 3, 4, 5]
    assert [item["publicContent"]["prerequisiteChallengeSlug"] for item in valley] == [
        "",
        *VALLEY_CHALLENGES[:-1],
    ]

    for slug in VALLEY_CHALLENGES:
        response = client.get(f"/api/v1/challenges/{slug}/versions/1")
        assert response.status_code == 200
        assert "visibleTests" in response.json()["publicContent"]
        assert "visibleHints" in response.json()["publicContent"]
        assert "hiddenTests" not in response.json()
        assert "hidden" not in response.json()["publicContent"]
    assert client.get("/api/v1/challenges/valley-name-tag/versions/2").status_code == 404

    definition = db_session.get(CodingChallengeDefinition, (VALLEY_CHALLENGES[0], 1))
    public = ChallengeOut.model_validate(definition).model_dump(by_alias=True)
    assert public["publicContent"]["functionSignature"] == "make_name_tag(name)"


def test_variable_valley_quest_requires_acceptance_and_five_ordered_passes(db_session):
    profile = _profile(db_session)
    accepted = submit_quest_event(
        db_session,
        profile,
        "variables-in-the-valley",
        QuestEventRequest(
            eventId=uuid4(),
            questVersion=1,
            expectedRevision=0,
            eventType="interact",
            targetId="valley-mentor",
            targetVersion=1,
        ),
    )
    assert accepted["status"] == "in_progress"
    assert accepted["revision"] == 1

    # A genuine passed submission for challenge two still cannot skip challenge one.
    later, _ = create_submission(
        db_session,
        profile,
        VALLEY_CHALLENGES[1],
        ChallengeSubmissionRequest(clientSubmissionId=uuid4(), challengeVersion=1, source="pass"),
    )
    later.status = "passed"
    later.created_at = datetime.now(UTC) - timedelta(minutes=2)
    db_session.commit()
    with pytest.raises(QuestEventError) as conflict:
        submit_quest_event(
            db_session,
            profile,
            "variables-in-the-valley",
            QuestEventRequest(
                eventId=uuid4(),
                questVersion=1,
                expectedRevision=1,
                eventType="challenge_passed",
                targetId=VALLEY_CHALLENGES[1],
                targetVersion=1,
                challengeSubmissionId=later.id,
            ),
        )
    assert conflict.value.code == "quest_prerequisite_not_met"

    passed_submissions = []
    for slug in VALLEY_CHALLENGES:
        submission, _ = create_submission(
            db_session,
            profile,
            slug,
            ChallengeSubmissionRequest(
                clientSubmissionId=uuid4(),
                challengeVersion=1,
                source="def solution(value): return value",
            ),
        )
        passed_submissions.append(submission.id)
        apply_worker_result(db_session, profile.id, submission.id, _passed_result(submission))
        submission.created_at = datetime.now(UTC) - timedelta(minutes=2)
        db_session.commit()

    progress = db_session.get(PlayerQuestProgress, (profile.id, "variables-in-the-valley", 1))
    assert progress.status == "completed"
    assert progress.revision == 6
    assert db_session.get(PlayerProgression, profile.id).experience == 50
    assert (
        db_session.query(PlayerQuestRewardLedger)
        .filter_by(player_profile_id=profile.id, quest_slug="variables-in-the-valley")
        .count()
        == 1
    )

    last_submission = db_session.get(SubmissionRecord, passed_submissions[-1])
    apply_worker_result(db_session, profile.id, last_submission.id, _passed_result(last_submission))
    assert db_session.get(PlayerProgression, profile.id).experience == 50
    assert (
        db_session.query(PlayerQuestRewardLedger)
        .filter_by(player_profile_id=profile.id, quest_slug="variables-in-the-valley")
        .count()
        == 1
    )


def test_variable_valley_seed_is_idempotent(db_session):
    from BackendAPI.app.db.seed import seed_development

    counts = seed_development(db_session)
    assert counts["regions"] == 0
    assert counts["challenges"] == 0
    assert (
        db_session.query(CodingChallengeDefinition)
        .filter(CodingChallengeDefinition.slug.in_(VALLEY_CHALLENGES))
        .count()
        == 5
    )
