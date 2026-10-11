import uuid

import pytest
from BackendAPI.app.db.models import (
    CurriculumRegion,
    PlayerProfile,
    PlayerQuestProgress,
    SubmissionRecord,
)
from BackendAPI.app.db.seed import seed_development
from BackendAPI.app.services import catalog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError


def test_development_seed_is_idempotent(db_session) -> None:
    first = seed_development(db_session)
    second = seed_development(db_session)
    assert first == {
        "regions": 0,
        "objectives": 0,
        "quests": 0,
        "challenges": 0,
        "achievements": 0,
        "questRules": 0,
    }
    assert second == first
    assert db_session.scalar(select(func.count()).select_from(CurriculumRegion)) == 4


def test_public_catalog_queries_return_latest_published_rows(db_session) -> None:
    regions, total = catalog.list_regions(db_session, limit=2, offset=0)
    assert total == 4
    assert [region.slug for region in regions] == ["variable-valley", "variable-vale"]
    assert catalog.get_quest(db_session, "light-the-signal").version == 2
    assert catalog.get_challenge(db_session, "signal-coordinate").version == 2


def test_profile_identity_subject_is_unique(db_session) -> None:
    profile = PlayerProfile(identity_subject="same-subject", display_name="First", locale="en")
    db_session.add(profile)
    db_session.commit()

    db_session.add(
        PlayerProfile(identity_subject="same-subject", display_name="Second", locale="en")
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_foreign_key_and_status_constraints_are_enforced(db_session) -> None:
    invalid_progress = PlayerQuestProgress(
        player_profile_id=uuid.uuid4(),
        quest_slug="missing-quest",
        quest_version=1,
        status="completed",
        state={},
    )
    db_session.add(invalid_progress)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    profile = PlayerProfile(identity_subject="constraint-subject", display_name="Test", locale="en")
    db_session.add(profile)
    db_session.commit()
    invalid_status = PlayerQuestProgress(
        player_profile_id=profile.id,
        quest_slug="light-the-signal",
        quest_version=1,
        status="trusted_client_says_complete",
        state={},
    )
    db_session.add(invalid_status)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_submission_idempotency_key_is_unique_per_player(db_session) -> None:
    profile = PlayerProfile(identity_subject="submission-subject", display_name="Test", locale="en")
    db_session.add(profile)
    db_session.commit()
    client_submission_id = uuid.uuid4()
    row = SubmissionRecord(
        player_profile_id=profile.id,
        challenge_slug="signal-coordinate",
        challenge_version=1,
        client_submission_id=client_submission_id,
        status="queued",
    )
    db_session.add(row)
    db_session.commit()

    duplicate = SubmissionRecord(
        player_profile_id=profile.id,
        challenge_slug="signal-coordinate",
        challenge_version=1,
        client_submission_id=client_submission_id,
        status="received",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
