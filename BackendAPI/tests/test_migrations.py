import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TABLES = {
    "achievement_definitions",
    "coding_challenge_definitions",
    "challenge_hidden_test_cases",
    "challenge_hints",
    "player_challenge_hint_unlocks",
    "curriculum_regions",
    "learning_objectives",
    "player_achievement_awards",
    "player_profiles",
    "player_progression",
    "player_quest_progress",
    "player_quest_events",
    "player_quest_reward_ledger",
    "quest_definitions",
    "quest_event_targets",
    "quest_objective_prerequisites",
    "quest_objective_rules",
    "quest_reward_rules",
    "submission_records",
    "evaluation_attempts",
}


def _alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "Database" / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


@pytest.mark.migration
def test_initial_migration_upgrade_and_downgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "migration_test.sqlite3"
    config = _alembic_config(f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    command.check(config)

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES.issubset(tables)
    engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").all() == []
    engine.dispose()


@pytest.mark.postgres
def test_postgres_migration_round_trip_when_configured() -> None:
    database_url = os.getenv("CODEQUEST_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CODEQUEST_TEST_DATABASE_URL is not configured")
    parsed = make_url(database_url)
    if parsed.get_backend_name() != "postgresql" or parsed.database != "codequest_test":
        pytest.fail(
            "PostgreSQL integration tests require an isolated database named codequest_test"
        )

    engine = create_engine(database_url)
    with engine.connect() as connection:
        existing = set(inspect(connection).get_table_names()) - {"alembic_version"}
    engine.dispose()
    if existing:
        pytest.fail(
            f"codequest_test must be empty before running migrations; found {sorted(existing)}"
        )

    config = _alembic_config(database_url)
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    assert EXPECTED_TABLES.issubset(set(inspect(engine).get_table_names()))
    engine.dispose()
    command.downgrade(config, "base")
