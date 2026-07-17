from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DATABASE_DIRECTORY = Path("data")
DATABASE_PATH = DATABASE_DIRECTORY / "ai_hunger_games.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"


def create_database_engine(
    database_url: str = DATABASE_URL,
) -> AsyncEngine:
    if database_url == DATABASE_URL:
        DATABASE_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

    engine = create_async_engine(
        database_url,
        echo=False,
    )

    if engine.url.get_backend_name() == "sqlite":
        _configure_sqlite_transaction_handling(engine)

    return engine


def _configure_sqlite_transaction_handling(
    engine: AsyncEngine,
) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def configure_sqlite_connection(
        dbapi_connection: Any,
        _connection_record: Any,
    ) -> None:
        dbapi_connection.isolation_level = None

        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    @event.listens_for(engine.sync_engine, "begin")
    def begin_sqlite_transaction(
        connection: Connection,
    ) -> None:
        connection.exec_driver_sql("BEGIN")


def set_sqlite_foreign_keys(
    connection: Connection,
    enabled: bool,
) -> None:
    """Change SQLite FK enforcement before a migration opens a transaction."""

    cursor = connection.connection.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys=" + ("ON" if enabled else "OFF"))
    finally:
        cursor.close()


def raise_if_sqlite_foreign_keys_are_invalid(
    connection: Connection,
) -> None:
    """Reject a migration that leaves any SQLite relationship orphaned."""

    cursor = connection.connection.cursor()

    try:
        cursor.execute("PRAGMA foreign_key_check")
        violations = cursor.fetchall()
    finally:
        cursor.close()

    if violations:
        raise RuntimeError(
            "SQLite migration left foreign-key violations: "
            + ", ".join(str(violation) for violation in violations)
        )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


async def create_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
