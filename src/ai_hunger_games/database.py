from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


DATABASE_DIRECTORY = Path("data")
DATABASE_PATH = DATABASE_DIRECTORY / "ai_hunger_games.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"


def create_database_engine() -> AsyncEngine:
    DATABASE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    return create_async_engine(
        DATABASE_URL,
        echo=False,
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