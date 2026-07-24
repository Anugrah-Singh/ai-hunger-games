"""FastAPI application for running and inspecting AI Hunger Games."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    status,
)
from fastapi import Path as ApiPath
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from ai_hunger_games.analysis import analyze_history
from ai_hunger_games.api_schemas import (
    AgentResponse,
    AnalysisResponse,
    AnswerFailureResponse,
    AnswerResponse,
    CreateExperimentRequest,
    ExperimentDetailResponse,
    ExperimentResponse,
    GenerationDetailResponse,
    GenerationRunResponse,
    GenerationSummaryResponse,
    ParticipantResponse,
    PersonalityResponse,
    RoundResponse,
    RoundScoreResponse,
    RunGenerationsRequest,
    VoteResponse,
)
from ai_hunger_games.database import (
    DATABASE_URL,
    create_database_engine,
    create_session_factory,
)
from ai_hunger_games.database_setup import initialize_database
from ai_hunger_games.db_models import (
    ExperimentRecord,
    GenerationRunRecord,
)
from ai_hunger_games.experiment_definitions import (
    build_experiment_definition,
    build_generation_run_config,
)
from ai_hunger_games.generations import run_generations
from ai_hunger_games.history import (
    AgentSnapshot,
    ExperimentHistory,
    GenerationSnapshot,
    PersonalitySnapshot,
    RoundSnapshot,
)
from ai_hunger_games.main import (
    create_providers,
    provider_name_for_settings,
)
from ai_hunger_games.models import (
    Agent,
    ExperimentDefinition,
)
from ai_hunger_games.repositories import (
    ExperimentConfigurationError,
    ExperimentRepository,
    GameRepository,
    GenerationConflictError,
    ProviderConfigurationConflictError,
)
from ai_hunger_games.run_repository import (
    ActiveGenerationRunError,
    GenerationRunNotFoundError,
    GenerationRunRepository,
)
from ai_hunger_games.settings import Settings, load_settings

WEB_DIRECTORY = Path(__file__).with_name("web")
logger = logging.getLogger(__name__)


class ExperimentRunCoordinator:
    """Serialize synchronous runs within one process and experiment."""

    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = {}

    async def try_acquire(
        self,
        experiment_id: int,
    ) -> asyncio.Lock | None:
        lock = self._locks.setdefault(
            experiment_id,
            asyncio.Lock(),
        )

        if lock.locked():
            return None

        await lock.acquire()

        return lock


async def get_session(
    request: Request,
) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = (
        request.app.state.session_factory
    )

    async with session_factory() as session:
        yield session


SessionDependency = Annotated[
    AsyncSession,
    Depends(get_session),
]
ExperimentId = Annotated[
    int,
    ApiPath(ge=1),
]
GameId = Annotated[
    int,
    ApiPath(ge=1),
]
RunId = Annotated[
    int,
    ApiPath(ge=1),
]


def create_app(
    database_url: str = DATABASE_URL,
    settings: Settings | None = None,
) -> FastAPI:
    configured_settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(
        app: FastAPI,
    ) -> AsyncIterator[None]:
        database_engine: AsyncEngine = create_database_engine(database_url)

        await initialize_database(database_engine)

        app.state.session_factory = create_session_factory(database_engine)
        app.state.settings = configured_settings
        app.state.run_coordinator = ExperimentRunCoordinator()

        try:
            yield
        finally:
            await database_engine.dispose()

    app = FastAPI(
        title="AI Hunger Games API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.mount(
        "/static",
        StaticFiles(directory=WEB_DIRECTORY),
        name="static",
    )

    @app.get(
        "/",
        include_in_schema=False,
    )
    async def dashboard() -> FileResponse:
        return FileResponse(WEB_DIRECTORY / "index.html")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/experiments",
        response_model=ExperimentResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_experiment(
        payload: CreateExperimentRequest,
        request: Request,
        session: SessionDependency,
    ) -> ExperimentResponse:
        settings_for_experiment: Settings = request.app.state.settings

        try:
            experiment = await ExperimentRepository(session).create_experiment(
                name=payload.name,
                definition=build_experiment_definition(payload.preset),
                provider_name=provider_name_for_settings(settings_for_experiment),
            )
        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("An experiment with this name already exists."),
            ) from error

        return _experiment_response(experiment)

    @app.get(
        "/experiments",
        response_model=list[ExperimentResponse],
    )
    async def list_experiments(
        session: SessionDependency,
    ) -> list[ExperimentResponse]:
        experiments = await ExperimentRepository(session).list_experiments()

        return [_experiment_response(experiment) for experiment in experiments]

    @app.get(
        "/experiments/{experiment_id}",
        response_model=ExperimentDetailResponse,
    )
    async def get_experiment(
        experiment_id: ExperimentId,
        request: Request,
        session: SessionDependency,
    ) -> ExperimentDetailResponse:
        experiment = await _get_experiment_or_404(
            session,
            experiment_id,
        )

        experiment_repository = ExperimentRepository(session)

        repository = GameRepository(
            session,
            experiment.id,
        )

        history = await repository.load_experiment_history()

        definition: ExperimentDefinition | None = None
        run_block_reason: str | None = None

        try:
            definition = await experiment_repository.load_experiment_definition(
                experiment.id
            )
        except ExperimentConfigurationError as error:
            run_block_reason = str(error)

        if history.generations:
            try:
                latest_population = await repository.load_latest_population()
            except GenerationConflictError as error:
                latest_population = None

                if run_block_reason is None:
                    run_block_reason = str(error)

            current_population = (
                [_configured_agent_response(agent) for agent in latest_population]
                if latest_population is not None
                else []
            )
        elif definition is not None:
            current_population = [
                _configured_agent_response(agent) for agent in definition.initial_agents
            ]
        else:
            current_population = []

        if run_block_reason is None and experiment.provider_name is None:
            run_block_reason = (
                "This imported experiment has no saved "
                "provider and configuration snapshot. "
                "Create a new experiment to run additional "
                "generations."
            )

        if run_block_reason is None and definition is None:
            run_block_reason = (
                "This experiment has no saved configuration "
                "snapshot. Create a new experiment to run "
                "additional generations."
            )

        configured_provider_name = provider_name_for_settings(
            request.app.state.settings
        )

        if (
            run_block_reason is None
            and experiment.provider_name != configured_provider_name
        ):
            run_block_reason = (
                "This server is configured for "
                f"'{configured_provider_name}', while this "
                "experiment is pinned to "
                f"'{experiment.provider_name}'."
            )

        return ExperimentDetailResponse(
            **_experiment_response(experiment).model_dump(),
            generation_count=len(history.generations),
            current_population=current_population,
            can_run=run_block_reason is None,
            run_block_reason=run_block_reason,
        )

    @app.post(
        "/experiments/{experiment_id}/generations",
        response_model=list[GenerationSummaryResponse],
    )
    async def run_experiment_generations(
        experiment_id: ExperimentId,
        payload: RunGenerationsRequest,
        request: Request,
        session: SessionDependency,
    ) -> list[GenerationSummaryResponse]:
        del payload

        experiment = await _get_experiment_or_404(
            session,
            experiment_id,
        )

        coordinator: ExperimentRunCoordinator = request.app.state.run_coordinator

        lock = await coordinator.try_acquire(experiment.id)

        if lock is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("This experiment already has a generation in progress."),
            )

        try:
            repository = GameRepository(
                session,
                experiment.id,
            )

            settings_for_run: Settings = request.app.state.settings

            provider_name = provider_name_for_settings(settings_for_run)

            definition = await ExperimentRepository(session).load_experiment_definition(
                experiment.id
            )

            if definition is None:
                raise ExperimentConfigurationError(
                    "This experiment has no saved "
                    "configuration snapshot. Create a new "
                    "experiment to run additional "
                    "generations."
                )

            starting_agents = await repository.load_latest_population()

            if starting_agents is None:
                starting_agents = list(definition.initial_agents)

            groq_client = None

            try:
                (
                    answer_provider,
                    vote_provider,
                    personality_provider,
                    groq_client,
                ) = create_providers(settings_for_run)

                results = await run_generations(
                    initial_agents=starting_agents,
                    config=build_generation_run_config(
                        definition,
                        1,
                    ),
                    answer_provider=answer_provider,
                    vote_provider=vote_provider,
                    personality_provider=(personality_provider),
                    repository=repository,
                    provider_name=provider_name,
                )
            finally:
                if groq_client is not None:
                    await groq_client.close()

        except (
            GenerationConflictError,
            ProviderConfigurationConflictError,
            ExperimentConfigurationError,
        ) as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        except ValueError as error:
            raise HTTPException(
                status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
                detail=str(error),
            ) from error

        except Exception as error:
            logger.exception(
                "Generation run failed for experiment %s",
                experiment.id,
            )

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=("Generation did not complete; no generation was saved."),
            ) from error

        finally:
            lock.release()

        history = await repository.load_experiment_history()

        generations_by_game_id = {
            generation.game_id: generation for generation in history.generations
        }

        return [
            _generation_summary_response(generations_by_game_id[result.game_id])
            for result in results
        ]

    @app.post(
        "/experiments/{experiment_id}/runs",
        response_model=GenerationRunResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def start_generation_run(
        experiment_id: ExperimentId,
        payload: RunGenerationsRequest,
        background_tasks: BackgroundTasks,
        request: Request,
        session: SessionDependency,
    ) -> GenerationRunResponse:
        del payload

        experiment = await _get_experiment_or_404(
            session,
            experiment_id,
        )

        experiment_repository = ExperimentRepository(session)

        try:
            definition = await experiment_repository.load_experiment_definition(
                experiment.id
            )
        except ExperimentConfigurationError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        if definition is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("This experiment has no saved configuration snapshot."),
            )

        configured_provider_name = provider_name_for_settings(
            request.app.state.settings
        )

        if experiment.provider_name != configured_provider_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This server is configured for "
                    f"'{configured_provider_name}', while "
                    "this experiment is pinned to "
                    f"'{experiment.provider_name}'."
                ),
            )

        repository = GameRepository(
            session,
            experiment.id,
        )

        starting_agents = await _starting_agents_for_run(
            repository=repository,
            definition=definition,
        )

        try:
            generation_plan = await repository.get_next_generation_plan(starting_agents)
        except (
            GenerationConflictError,
            ProviderConfigurationConflictError,
            ExperimentConfigurationError,
        ) as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        try:
            run = await GenerationRunRepository(session).create_queued_run(
                experiment_id=experiment.id,
                generation_number=(generation_plan.generation_number),
            )
        except ActiveGenerationRunError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("This experiment already has a generation in progress."),
            ) from error

        background_tasks.add_task(
            _execute_generation_run,
            run_id=run.id,
            experiment_id=experiment.id,
            session_factory=(request.app.state.session_factory),
            settings=request.app.state.settings,
        )

        return _generation_run_response(run)

    @app.get(
        "/runs/{run_id}",
        response_model=GenerationRunResponse,
    )
    async def get_generation_run(
        run_id: RunId,
        session: SessionDependency,
    ) -> GenerationRunResponse:
        try:
            run = await GenerationRunRepository(session).require_run(run_id)
        except GenerationRunNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error

        return _generation_run_response(run)

    @app.get(
        "/experiments/{experiment_id}/runs/active",
        response_model=GenerationRunResponse | None,
    )
    async def get_active_generation_run(
        experiment_id: ExperimentId,
        session: SessionDependency,
    ) -> GenerationRunResponse | None:
        await _get_experiment_or_404(
            session,
            experiment_id,
        )

        run = await GenerationRunRepository(session).get_active_run(experiment_id)

        if run is None:
            return None

        return _generation_run_response(run)

    @app.get(
        "/experiments/{experiment_id}/generations",
        response_model=list[GenerationSummaryResponse],
    )
    async def list_generations(
        experiment_id: ExperimentId,
        session: SessionDependency,
    ) -> list[GenerationSummaryResponse]:
        history = await _get_history_or_404(
            session,
            experiment_id,
        )

        return [
            _generation_summary_response(generation)
            for generation in history.generations
        ]

    @app.get(
        "/experiments/{experiment_id}/analysis",
        response_model=AnalysisResponse,
    )
    async def get_experiment_analysis(
        experiment_id: ExperimentId,
        session: SessionDependency,
    ) -> AnalysisResponse:
        history = await _get_history_or_404(
            session,
            experiment_id,
        )

        return AnalysisResponse.model_validate(asdict(analyze_history(history)))

    @app.get(
        "/generations/{game_id}",
        response_model=GenerationDetailResponse,
    )
    async def get_generation(
        game_id: GameId,
        session: SessionDependency,
    ) -> GenerationDetailResponse:
        generation = await _get_generation_or_404(
            session,
            game_id,
        )

        return _generation_detail_response(generation)

    @app.get(
        "/generations/{game_id}/rounds",
        response_model=list[RoundResponse],
    )
    async def get_generation_rounds(
        game_id: GameId,
        session: SessionDependency,
    ) -> list[RoundResponse]:
        generation = await _get_generation_or_404(
            session,
            game_id,
        )

        return [_round_response(round_snapshot) for round_snapshot in generation.rounds]

    @app.get(
        "/generations/{game_id}/votes",
        response_model=list[VoteResponse],
    )
    async def get_generation_votes(
        game_id: GameId,
        session: SessionDependency,
    ) -> list[VoteResponse]:
        generation = await _get_generation_or_404(
            session,
            game_id,
        )

        return [
            VoteResponse(
                voter_agent_id=(vote.voter_agent_id),
                selected_candidate_id=(vote.selected_candidate_id),
            )
            for round_snapshot in generation.rounds
            for vote in round_snapshot.votes
        ]

    return app


async def _execute_generation_run(
    *,
    run_id: int,
    experiment_id: int,
    session_factory: (async_sessionmaker[AsyncSession]),
    settings: Settings,
) -> None:
    """Execute one generation independently of the request session."""

    async with session_factory() as session:
        run_repository = GenerationRunRepository(session)

        try:
            await run_repository.mark_running(run_id)

            experiment = await session.get(
                ExperimentRecord,
                experiment_id,
            )

            if experiment is None:
                raise RuntimeError("The experiment no longer exists.")

            definition = await ExperimentRepository(session).load_experiment_definition(
                experiment_id
            )

            if definition is None:
                raise ExperimentConfigurationError(
                    "This experiment has no saved configuration snapshot."
                )

            configured_provider_name = provider_name_for_settings(settings)

            if experiment.provider_name != configured_provider_name:
                raise ProviderConfigurationConflictError(
                    "This server is configured for "
                    f"'{configured_provider_name}', while "
                    "this experiment is pinned to "
                    f"'{experiment.provider_name}'."
                )

            repository = GameRepository(
                session,
                experiment_id,
            )

            starting_agents = await _starting_agents_for_run(
                repository=repository,
                definition=definition,
            )

            groq_client = None

            try:
                (
                    answer_provider,
                    vote_provider,
                    personality_provider,
                    groq_client,
                ) = create_providers(settings)

                results = await run_generations(
                    initial_agents=(starting_agents),
                    config=(
                        build_generation_run_config(
                            definition,
                            1,
                        )
                    ),
                    answer_provider=(answer_provider),
                    vote_provider=vote_provider,
                    personality_provider=(personality_provider),
                    repository=repository,
                    provider_name=(configured_provider_name),
                )
            finally:
                if groq_client is not None:
                    await groq_client.close()

            if len(results) != 1:
                raise RuntimeError(
                    "The background generation did not return exactly one result."
                )

            await run_repository.mark_completed(
                run_id,
                game_id=results[0].game_id,
            )

        except Exception:
            logger.exception(
                "Background generation run %s failed for experiment %s",
                run_id,
                experiment_id,
            )

            await session.rollback()

            try:
                await run_repository.mark_failed(
                    run_id,
                    error_message=(
                        "Generation did not complete; no generation was saved."
                    ),
                )
            except Exception:
                logger.exception(
                    "Could not mark generation run %s as failed",
                    run_id,
                )


async def _starting_agents_for_run(
    *,
    repository: GameRepository,
    definition: ExperimentDefinition,
) -> list[Agent]:
    starting_agents = await repository.load_latest_population()

    if starting_agents is not None:
        return starting_agents

    return list(definition.initial_agents)


async def _get_experiment_or_404(
    session: AsyncSession,
    experiment_id: int,
) -> ExperimentRecord:
    experiment = await ExperimentRepository(session).get_experiment(experiment_id)

    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Experiment {experiment_id} was not found."),
        )

    return experiment


async def _get_history_or_404(
    session: AsyncSession,
    experiment_id: int,
) -> ExperimentHistory:
    experiment = await _get_experiment_or_404(
        session,
        experiment_id,
    )

    return await GameRepository(
        session,
        experiment.id,
    ).load_experiment_history()


async def _get_generation_or_404(
    session: AsyncSession,
    game_id: int,
) -> GenerationSnapshot:
    experiment = await ExperimentRepository(session).get_experiment_for_game(game_id)

    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Generation {game_id} was not found."),
        )

    history = await GameRepository(
        session,
        experiment.id,
    ).load_experiment_history()

    for generation in history.generations:
        if generation.game_id == game_id:
            return generation

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=(f"Generation {game_id} was not found."),
    )


def _experiment_response(
    experiment: ExperimentRecord,
) -> ExperimentResponse:
    return ExperimentResponse(
        id=experiment.id,
        name=experiment.name,
        created_at=experiment.created_at,
        provider_name=experiment.provider_name,
    )


def _generation_run_response(
    run: GenerationRunRecord,
) -> GenerationRunResponse:
    return GenerationRunResponse(
        id=run.id,
        experiment_id=run.experiment_id,
        status=run.status,
        generation_number=(run.generation_number),
        game_id=run.game_id,
        error_message=run.error_message,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


def _personality_response(
    personality: PersonalitySnapshot,
) -> PersonalityResponse:
    return PersonalityResponse(
        name=personality.name,
        description=personality.description,
        answer_template=(personality.answer_template),
    )


def _agent_response(
    agent: AgentSnapshot,
) -> AgentResponse:
    return AgentResponse(
        agent_id=agent.agent_id,
        agent_name=agent.agent_name,
        personality=_personality_response(agent.personality),
    )


def _configured_agent_response(
    agent: Agent,
) -> AgentResponse:
    return AgentResponse(
        agent_id=agent.id,
        agent_name=agent.name,
        personality=PersonalityResponse(
            name=agent.personality.name,
            description=(agent.personality.description),
            answer_template=(agent.personality.answer_template),
        ),
    )


def _generation_summary_response(
    generation: GenerationSnapshot,
) -> GenerationSummaryResponse:
    return GenerationSummaryResponse(
        game_id=generation.game_id,
        generation_number=(generation.generation_number),
        provider_name=(generation.provider_name),
        created_at=generation.created_at,
        round_count=len(generation.rounds),
        seeds=asdict(generation.seeds),
        eliminated_agent_id=(generation.eliminated_agent_id),
        replacement_agent=_agent_response(generation.replacement_agent),
    )


def _generation_detail_response(
    generation: GenerationSnapshot,
) -> GenerationDetailResponse:
    return GenerationDetailResponse(
        **_generation_summary_response(generation).model_dump(),
        starting_agents=[
            ParticipantResponse(
                **_agent_response(participant.agent).model_dump(),
                total_score=(participant.total_score),
                was_eliminated=(participant.was_eliminated),
            )
            for participant in generation.starting_agents
        ],
        final_agents=[_agent_response(agent) for agent in generation.final_agents],
        rounds=[
            _round_response(round_snapshot) for round_snapshot in generation.rounds
        ],
    )


def _round_response(
    round_snapshot: RoundSnapshot,
) -> RoundResponse:
    candidate_id_by_agent_id = {
        answer.agent_id: answer.candidate_id for answer in round_snapshot.answers
    }

    return RoundResponse(
        round_id=round_snapshot.round_id,
        round_number=(round_snapshot.round_number),
        question=round_snapshot.question,
        answers=[
            AnswerResponse(
                candidate_id=(answer.candidate_id),
                content=answer.content,
                attempt_count=(answer.attempt_count),
            )
            for answer in round_snapshot.answers
        ],
        votes=[
            VoteResponse(
                voter_agent_id=(vote.voter_agent_id),
                selected_candidate_id=(vote.selected_candidate_id),
            )
            for vote in round_snapshot.votes
        ],
        scores=[
            RoundScoreResponse(
                candidate_id=(candidate_id_by_agent_id[score.agent_id]),
                score=score.score,
            )
            for score in round_snapshot.scores
            if score.agent_id in candidate_id_by_agent_id
        ],
        failures=[
            AnswerFailureResponse(
                agent_id=failure.agent_id,
                error_type=failure.error_type,
                message=failure.message,
                attempt_count=(failure.attempt_count),
                retry_after_seconds=(failure.retry_after_seconds),
            )
            for failure in round_snapshot.failures
        ],
    )


app = create_app()
