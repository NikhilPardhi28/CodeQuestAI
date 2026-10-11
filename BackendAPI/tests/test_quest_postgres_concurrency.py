import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from BackendAPI.app.db.models import PlayerProfile, PlayerProgression
from BackendAPI.app.db.seed import seed_development
from BackendAPI.app.db.session import build_engine
from BackendAPI.app.schemas import QuestEventRequest
from BackendAPI.app.services.quest_events import QuestEventError, submit_quest_event
from BackendAPI.tests.postgres_support import (
    assert_empty_postgres_application_schema,
    assert_postgres_migration_applied,
    report_postgres_migration_state,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]


def _config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "Database" / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


@pytest.mark.postgres
def test_postgres_serializes_concurrent_quest_revisions():
    database_url = os.getenv("CODEQUEST_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CODEQUEST_TEST_DATABASE_URL is not configured")
    if (
        make_url(database_url).get_backend_name() != "postgresql"
        or make_url(database_url).database != "codequest_test"
    ):
        pytest.fail("PostgreSQL concurrency tests require the isolated codequest_test database")

    engine = build_engine(database_url)
    config = _config(database_url)
    before_migration = report_postgres_migration_state(
        stage="before_upgrade", engine=engine, config=config, test_database_url=database_url
    )
    assert_empty_postgres_application_schema(before_migration)
    command.upgrade(config, "head")
    engine.dispose()
    engine = build_engine(database_url)
    after_migration = report_postgres_migration_state(
        stage="after_upgrade", engine=engine, config=config, test_database_url=database_url
    )
    assert_postgres_migration_applied(after_migration)
    try:
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        with factory() as session:
            seed_development(session)
            profile = PlayerProfile(
                identity_subject="postgres-concurrency", display_name="Concurrency"
            )
            session.add(profile)
            session.flush()
            session.add(PlayerProgression(player_profile_id=profile.id))
            profile_id = profile.id
            session.commit()

        barrier = Barrier(2)

        def submit(event_id):
            with factory() as session:
                profile = session.get(PlayerProfile, profile_id)
                payload = QuestEventRequest(
                    eventId=event_id,
                    questVersion=1,
                    expectedRevision=0,
                    eventType="interact",
                    targetId="relay-switch",
                    targetVersion=1,
                )
                barrier.wait(timeout=10)
                try:
                    return submit_quest_event(session, profile, "light-the-signal", payload)
                except QuestEventError as error:
                    return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(submit, [uuid4(), uuid4()]))
        assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1
        assert sum(outcome == "quest_revision_conflict" for outcome in outcomes) == 1
    finally:
        command.downgrade(config, "base")
        engine.dispose()
