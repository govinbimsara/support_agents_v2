"""Alembic environment (ADR-0014, NFR-REL-04).

- The database URL comes only from ``DATABASE_URL_DIRECT`` (the direct, non-pooled Neon
  endpoint) through ``app.config``. It is never read from a file, never written into the
  Alembic ``Config``, and never printed or logged.
- The ``adk`` schema belongs to ADK's DatabaseSessionService and is ignored completely
  (``app.db.migration_filters``), so autogenerate never touches ADK tables.
- Migrations are written or reviewed by hand; autogenerate output is only a draft.

Alembic docs: https://alembic.sqlalchemy.org/en/latest/tutorial.html (env.py, "Configuration")
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import load_migration_settings, migration_url
from app.db.migration_filters import AUTOGENERATE_OPTIONS

config = context.config

# Interpret alembic.ini for Python logging (logging settings only; no URL in there).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No models yet. When tables are modelled, set this to their MetaData (never ADK's).
target_metadata = None


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting. Needs no URL and no secret."""
    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **AUTOGENERATE_OPTIONS,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the direct endpoint and run migrations."""
    # Built here, in one expression, and handed straight to the engine.
    connectable = create_engine(
        migration_url(load_migration_settings()),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            **AUTOGENERATE_OPTIONS,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
