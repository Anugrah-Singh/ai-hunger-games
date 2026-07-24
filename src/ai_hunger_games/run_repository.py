"""Persistence operations for asynchronous generation runs."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_hunger_games.db_models import GenerationRunRecord

ACTIVE_RUN_STATUSES = (
    "queued",
    "running",
)


class ActiveGenerationRunError(RuntimeError):
    """Raised when an experiment already has an active run."""


class GenerationRunNotFoundError(LookupError):
    """Raised when a requested generation run does not exist."""


class GenerationRunRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create_queued_run(
        self,
        *,
        experiment_id: int,
        generation_number: int,
    ) -> GenerationRunRecord:
        active_run = await self.get_active_run(experiment_id)

        if active_run is not None:
            raise ActiveGenerationRunError(
                "This experiment already has a generation in progress."
            )

        run = GenerationRunRecord(
            experiment_id=experiment_id,
            status="queued",
            generation_number=generation_number,
            game_id=None,
            error_message=None,
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
        )

        self.session.add(run)

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(run)

        return run

    async def get_run(
        self,
        run_id: int,
    ) -> GenerationRunRecord | None:
        return await self.session.get(
            GenerationRunRecord,
            run_id,
        )

    async def require_run(
        self,
        run_id: int,
    ) -> GenerationRunRecord:
        run = await self.get_run(run_id)

        if run is None:
            raise GenerationRunNotFoundError(f"Generation run {run_id} does not exist.")

        return run

    async def get_active_run(
        self,
        experiment_id: int,
    ) -> GenerationRunRecord | None:
        result = await self.session.execute(
            select(GenerationRunRecord)
            .where(
                GenerationRunRecord.experiment_id == experiment_id,
                GenerationRunRecord.status.in_(ACTIVE_RUN_STATUSES),
            )
            .order_by(GenerationRunRecord.id.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def mark_running(
        self,
        run_id: int,
    ) -> GenerationRunRecord:
        run = await self.require_run(run_id)

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        run.error_message = None

        await self.session.commit()
        await self.session.refresh(run)

        return run

    async def mark_completed(
        self,
        run_id: int,
        *,
        game_id: int,
    ) -> GenerationRunRecord:
        run = await self.require_run(run_id)

        run.status = "completed"
        run.game_id = game_id
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = None

        await self.session.commit()
        await self.session.refresh(run)

        return run

    async def mark_failed(
        self,
        run_id: int,
        *,
        error_message: str,
    ) -> GenerationRunRecord:
        run = await self.require_run(run_id)

        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = error_message[:1000]

        await self.session.commit()
        await self.session.refresh(run)

        return run
