from sqlalchemy.ext.asyncio import AsyncEngine

from ai_hunger_games.db_models import Base


async def initialize_database(
    engine: AsyncEngine,
) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )