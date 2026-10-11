import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from BackendAPI.app.db.models import (
    EvaluationAttempt,
    PlayerProfile,
    PlayerProgression,
    PlayerQuestEvent,
    PlayerQuestProgress,
    PlayerQuestRewardLedger,
    SubmissionRecord,
)
from BackendAPI.app.db.seed import seed_development
from BackendAPI.app.db.session import build_engine
from BackendAPI.app.schemas import (
    ChallengeSubmissionRequest,
    EvaluationTestResult,
    WorkerEvaluationResponse,
)
from BackendAPI.app.services.submissions import apply_worker_result, create_submission
from BackendAPI.tests.postgres_support import reset_empty_postgres_migration_state
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.postgres
def test_postgres_submission_idempotency_and_duplicate_pass_are_serialized():
    database_url = os.getenv("CODEQUEST_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CODEQUEST_TEST_DATABASE_URL is not configured")
    parsed = make_url(database_url)
    if parsed.get_backend_name() != "postgresql" or parsed.database != "codequest_test":
        pytest.fail("PostgreSQL submission tests require the isolated codequest_test database")

    engine = build_engine(database_url)
    reset_empty_postgres_migration_state(engine)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "Database" / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory() as session:
            seed_development(session)
            profile = PlayerProfile(identity_subject="postgres-submission", display_name="Learner")
            session.add(profile)
            session.flush()
            session.add(PlayerProgression(player_profile_id=profile.id))
            session.add(
                PlayerQuestProgress(
                    player_profile_id=profile.id,
                    quest_slug="light-the-signal",
                    quest_version=1,
                    status="in_progress",
                    revision=0,
                    state={"objectiveCounts": {"activate-relay": 1, "reach-platform": 1}},
                )
            )
            profile_id = profile.id
            session.commit()

        client_id = uuid4()
        source = "def signal_coordinate(x, y): return (x, y)"
        request_barrier = Barrier(2)

        def submit_same_key():
            with factory() as session:
                profile = session.get(PlayerProfile, profile_id)
                request_barrier.wait(timeout=10)
                row, replayed = create_submission(
                    session,
                    profile,
                    "signal-coordinate",
                    ChallengeSubmissionRequest(
                        clientSubmissionId=client_id, challengeVersion=1, source=source
                    ),
                )
                return row.id, replayed

        with ThreadPoolExecutor(max_workers=2) as pool:
            submissions = list(pool.map(lambda _index: submit_same_key(), range(2)))
        assert submissions[0][0] == submissions[1][0]
        assert sorted(replayed for _submission_id, replayed in submissions) == [False, True]

        submission_id = submissions[0][0]
        result = WorkerEvaluationResponse(
            submissionId=submission_id,
            challengeSlug="signal-coordinate",
            challengeVersion=1,
            evaluatorVersion="python-v1",
            visibleResults=[EvaluationTestResult(passed=True) for _ in range(2)],
            hiddenPassed=2,
            hiddenTotal=2,
        )
        pass_barrier = Barrier(2)

        def apply_same_pass():
            with factory() as session:
                pass_barrier.wait(timeout=10)
                return apply_worker_result(session, profile_id, submission_id, result).status

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _index: apply_same_pass(), range(2)))
        assert statuses == ["passed", "passed"]

        with factory() as session:
            assert (
                session.scalar(
                    select(PlayerProgression.experience).where(
                        PlayerProgression.player_profile_id == profile_id
                    )
                )
                == 25
            )
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(PlayerQuestRewardLedger)
                    .where(PlayerQuestRewardLedger.player_profile_id == profile_id)
                )
                == 1
            )
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(PlayerQuestEvent)
                    .where(PlayerQuestEvent.player_profile_id == profile_id)
                )
                == 1
            )
            assert (
                session.scalar(
                    select(SubmissionRecord.id).where(SubmissionRecord.id == submission_id)
                )
                == submission_id
            )
            assert (
                session.scalar(
                    select(EvaluationAttempt.id).where(
                        EvaluationAttempt.submission_id == submission_id
                    )
                )
                is not None
            )
    finally:
        command.downgrade(config, "base")
        engine.dispose()
