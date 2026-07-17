import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from ai_hunger_games.database import (
    create_database_engine,
    raise_if_sqlite_foreign_keys_are_invalid,
    set_sqlite_foreign_keys,
)
from ai_hunger_games.db_models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(
        config.config_file_name,
        disable_existing_loggers=False,
    )

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    is_sqlite = connection.dialect.name == "sqlite"

    if is_sqlite:
        # Alembic's SQLite batch mode drops and recreates a table. Its
        # official guidance requires foreign-key enforcement to be disabled
        # while a referenced table is rebuilt; otherwise ON DELETE CASCADE
        # can erase dependent historical rows. The driver cursor runs before
        # SQLAlchemy opens Alembic's migration transaction.
        set_sqlite_foreign_keys(connection, enabled=False)

    try:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()

        if is_sqlite:
            raise_if_sqlite_foreign_keys_are_invalid(connection)
    finally:
        if is_sqlite:
            set_sqlite_foreign_keys(connection, enabled=True)


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = create_database_engine(config.get_main_option("sqlalchemy.url"))

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    connection = config.attributes.get("connection")

    if connection is not None:
        do_run_migrations(connection)
        return

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
