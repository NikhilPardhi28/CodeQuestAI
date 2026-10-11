"""Diagnostics and guards for tests that own the isolated PostgreSQL database."""

import json

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine, make_url


def _safe_target(url: str) -> dict[str, str | int | None]:
    parsed = make_url(url)
    return {
        "driver": parsed.drivername,
        "host": parsed.host,
        "port": parsed.port,
        "database": parsed.database,
    }


def report_postgres_migration_state(
    *, stage: str, engine: Engine, config: Config, test_database_url: str
) -> dict[str, object]:
    """Log credential-free migration state and verify the engine/config target agrees."""
    configured_url = config.get_main_option("sqlalchemy.url")
    configured_target = make_url(configured_url)
    test_target = make_url(test_database_url)
    engine_target = make_url(engine.url)
    alembic_matches_test_url = configured_target == test_target
    engine_matches_test_url = engine_target == test_target
    expected_head = ScriptDirectory.from_config(config).get_current_head()

    with engine.connect() as connection:
        database, schema = connection.execute(
            text("SELECT current_database(), current_schema()")
        ).one()
        current_revision = MigrationContext.configure(connection).get_current_revision()
        tables = sorted(inspect(connection).get_table_names())

    state: dict[str, object] = {
        "stage": stage,
        "engineTarget": _safe_target(engine.url.render_as_string(hide_password=True)),
        "alembicTarget": _safe_target(configured_url),
        "testEnvironmentTarget": _safe_target(test_database_url),
        "engineMatchesTestUrl": engine_matches_test_url,
        "alembicMatchesTestUrl": alembic_matches_test_url,
        "migrationScriptLocation": config.get_main_option("script_location"),
        "database": database,
        "schema": schema,
        "alembicCurrent": current_revision,
        "alembicHead": expected_head,
        "curriculumRegionsExists": "curriculum_regions" in tables,
        "tableNames": tables,
    }
    print("POSTGRES_MIGRATION_DIAGNOSTIC " + json.dumps(state, sort_keys=True), flush=True)

    if not engine_matches_test_url or not alembic_matches_test_url:
        raise AssertionError(
            "PostgreSQL engine and Alembic URLs must match CODEQUEST_TEST_DATABASE_URL"
        )
    return state


def assert_empty_postgres_application_schema(state: dict[str, object]) -> None:
    tables = set(state["tableNames"])
    application_tables = tables - {"alembic_version"}
    if application_tables:
        raise AssertionError(
            "codequest_test must be empty before PostgreSQL integration tests; "
            f"found {sorted(application_tables)}"
        )


def assert_postgres_migration_applied(state: dict[str, object]) -> None:
    if state["alembicCurrent"] != state["alembicHead"]:
        raise AssertionError(
            "PostgreSQL migration did not reach Alembic head: "
            f"current={state['alembicCurrent']!r}, head={state['alembicHead']!r}"
        )
    if not state["curriculumRegionsExists"]:
        raise AssertionError(
            "PostgreSQL migration reports Alembic head but curriculum_regions is absent "
            f"in database={state['database']!r}, schema={state['schema']!r}"
        )
