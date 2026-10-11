"""Setup helpers for tests that own the isolated PostgreSQL database."""

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def reset_empty_postgres_migration_state(engine: Engine) -> None:
    """Remove only a stale Alembic stamp from an otherwise empty test database."""
    if engine.dialect.name != "postgresql":
        raise ValueError("PostgreSQL integration tests require a PostgreSQL engine")

    tables = set(inspect(engine).get_table_names())
    application_tables = tables - {"alembic_version"}
    if application_tables:
        raise RuntimeError(
            "codequest_test must be empty before PostgreSQL integration tests; "
            f"found {sorted(application_tables)}"
        )

    if "alembic_version" in tables:
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE alembic_version")
