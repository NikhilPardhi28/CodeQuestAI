from logging.config import fileConfig

from alembic import context
from BackendAPI.app.config import get_settings
from BackendAPI.app.db import models  # noqa: F401
from BackendAPI.app.db.base import Base
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    configured = config.get_main_option("sqlalchemy.url")
    return configured or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url(), poolclass=NullPool, pool_pre_ping=True)
    try:
        with connectable.connect() as connection:
            if connection.dialect.name == "postgresql":
                connection.exec_driver_sql("SET TIME ZONE 'UTC'")
                # SQLAlchemy 2.x autobegins a transaction for SET. Commit it before
                # Alembic starts its migration transaction, or connection close would
                # roll back the nested migration work with the outer transaction.
                connection.commit()
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                render_as_batch=connection.dialect.name == "sqlite",
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
