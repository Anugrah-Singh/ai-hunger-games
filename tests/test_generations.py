from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from ai_hunger_games.database import (
    create_database_engine,
    create_session_factory,
)
from ai_hunger_games.database_setup import initialize_database
from ai_hunger_games.db_models import (
    GameAgentRecord,
    GameFinalAgentRecord,
    GameRecord,
)
from ai_hunger_games.generations import (
    GenerationRunConfig,
    derive_generation_seeds,
    run_generations,
)
from ai_hunger_games.models import (
    Agent,
    Answer,
    AnswerGenerationPolicy,
    ExperimentDefinition,
    Personality,
    PersonalityGenerationPolicy,
    VoteGenerationPolicy,
)
from ai_hunger_games.providers import (
    InsufficientAnswersError,
    SimulatedAnswerProvider,
    SimulatedPersonalityProvider,
    SimulatedVoteProvider,
)
from ai_hunger_games.repositories import (
    ExperimentConfigurationError,
    ExperimentRepository,
    GameRepository,
    GenerationConflictError,
    ProviderConfigurationConflictError,
)

SIMULATED_PROVIDER_NAME = "Simulated providers"


@asynccontextmanager
async def initialized_database(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]]]:
    database_path = tmp_path / "ai_hunger_games.db"
    engine = create_database_engine(f"sqlite+aiosqlite:///{database_path}")

    try:
        await initialize_database(engine)
        session_factory = create_session_factory(engine)

        async with session_factory() as session:
            await ExperimentRepository(session).create_experiment(
                "Test experiment",
                definition=create_test_experiment_definition(),
                provider_name=SIMULATED_PROVIDER_NAME,
            )

        yield engine, session_factory
    finally:
        await engine.dispose()


def create_agents() -> list[Agent]:
    return [
        Agent(
            id="agent_1",
            name="Analyst",
            personality=Personality(
                name="Evidence Analyst",
                description="Tests claims against observable evidence.",
                answer_template="Analyze evidence for {question}",
            ),
        ),
        Agent(
            id="agent_2",
            name="Strategist",
            personality=Personality(
                name="Long-Term Strategist",
                description="Evaluates downstream tradeoffs.",
                answer_template="Plan for the long term in {question}",
            ),
        ),
        Agent(
            id="agent_3",
            name="Mediator",
            personality=Personality(
                name="Empathetic Mediator",
                description="Balances affected perspectives.",
                answer_template="Consider people affected by {question}",
            ),
        ),
    ]


def create_config(
    generation_count: int = 2,
) -> GenerationRunConfig:
    return GenerationRunConfig(
        generation_count=generation_count,
        questions_per_generation=(
            "How should a team make a risky decision?",
            "What makes a policy fair?",
        ),
        candidate_order_seed=11,
        voting_seed=23,
        elimination_seed=37,
        replacement_seed=41,
        answer_policy=AnswerGenerationPolicy(
            timeout_seconds=1.0,
            minimum_successful_answers=2,
            maximum_attempts=1,
            initial_retry_delay_seconds=0.0,
            maximum_retry_delay_seconds=0.0,
        ),
        vote_policy=VoteGenerationPolicy(
            timeout_seconds=1.0,
            maximum_attempts=1,
            initial_retry_delay_seconds=0.0,
            maximum_retry_delay_seconds=0.0,
        ),
        personality_policy=PersonalityGenerationPolicy(
            timeout_seconds=1.0,
            maximum_attempts=1,
            initial_retry_delay_seconds=0.0,
            maximum_retry_delay_seconds=0.0,
        ),
    )


def create_test_experiment_definition() -> ExperimentDefinition:
    config = create_config(generation_count=1)

    return ExperimentDefinition(
        initial_agents=tuple(create_agents()),
        questions_per_generation=config.questions_per_generation,
        candidate_order_seed=config.candidate_order_seed,
        voting_seed=config.voting_seed,
        elimination_seed=config.elimination_seed,
        replacement_seed=config.replacement_seed,
        answer_policy=config.answer_policy,
        vote_policy=config.vote_policy,
        personality_policy=config.personality_policy,
        seed_stride=config.seed_stride,
    )


async def count_games(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(GameRecord))

    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_run_generations_persists_and_chains_populations(
    tmp_path: Path,
) -> None:
    agents = create_agents()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)
            results = await run_generations(
                initial_agents=agents,
                config=create_config(),
                answer_provider=SimulatedAnswerProvider(),
                vote_provider=SimulatedVoteProvider(),
                personality_provider=SimulatedPersonalityProvider(),
                repository=repository,
                provider_name="Simulated providers",
            )

            latest_population = await repository.load_latest_population()

            async with session.begin():
                first_final_agents = list(
                    await session.scalars(
                        select(GameFinalAgentRecord)
                        .where(GameFinalAgentRecord.game_id == results[0].game_id)
                        .order_by(GameFinalAgentRecord.position)
                    )
                )
                second_starting_agents = list(
                    await session.scalars(
                        select(GameAgentRecord)
                        .where(GameAgentRecord.game_id == results[1].game_id)
                        .order_by(GameAgentRecord.id)
                    )
                )

    assert [result.generation_number for result in results] == [1, 2]
    assert [record.agent_id for record in second_starting_agents] == [
        record.agent_id for record in first_final_agents
    ]
    assert latest_population is not None
    assert [agent.id for agent in latest_population] == [
        agent.id for agent in results[-1].game_result.final_agents
    ]


@pytest.mark.asyncio
async def test_run_generations_assigns_unique_replacement_ids(
    tmp_path: Path,
) -> None:
    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            results = await run_generations(
                initial_agents=create_agents(),
                config=create_config(),
                answer_provider=SimulatedAnswerProvider(),
                vote_provider=SimulatedVoteProvider(),
                personality_provider=SimulatedPersonalityProvider(),
                repository=GameRepository(session),
                provider_name="Simulated providers",
            )

    assert [result.game_result.replacement_agent.id for result in results] == [
        "agent_4",
        "agent_5",
    ]
    assert "agent_4" in (results[1].game_result.total_scores_by_agent_id)


@pytest.mark.asyncio
async def test_resume_uses_latest_persisted_population(
    tmp_path: Path,
) -> None:
    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as first_session:
            first_results = await run_generations(
                initial_agents=create_agents(),
                config=create_config(generation_count=1),
                answer_provider=SimulatedAnswerProvider(),
                vote_provider=SimulatedVoteProvider(),
                personality_provider=SimulatedPersonalityProvider(),
                repository=GameRepository(first_session),
                provider_name="Simulated providers",
            )

        async with session_factory() as second_session:
            repository = GameRepository(second_session)
            resumed_agents = await repository.load_latest_population()

            assert resumed_agents is not None

            second_results = await run_generations(
                initial_agents=resumed_agents,
                config=create_config(generation_count=1),
                answer_provider=SimulatedAnswerProvider(),
                vote_provider=SimulatedVoteProvider(),
                personality_provider=SimulatedPersonalityProvider(),
                repository=repository,
                provider_name="Simulated providers",
            )

    assert second_results[0].generation_number == 2
    assert [agent.id for agent in resumed_agents] == [
        agent.id for agent in first_results[0].game_result.final_agents
    ]


@pytest.mark.asyncio
async def test_run_generations_rejects_a_stale_starting_population(
    tmp_path: Path,
) -> None:
    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as first_session:
            await run_generations(
                initial_agents=create_agents(),
                config=create_config(generation_count=1),
                answer_provider=SimulatedAnswerProvider(),
                vote_provider=SimulatedVoteProvider(),
                personality_provider=SimulatedPersonalityProvider(),
                repository=GameRepository(first_session),
                provider_name=SIMULATED_PROVIDER_NAME,
            )

        async with session_factory() as second_session:
            repository = GameRepository(second_session)

            with pytest.raises(
                GenerationConflictError,
                match="expected population",
            ):
                await run_generations(
                    initial_agents=create_agents(),
                    config=create_config(generation_count=1),
                    answer_provider=SimulatedAnswerProvider(),
                    vote_provider=SimulatedVoteProvider(),
                    personality_provider=(SimulatedPersonalityProvider()),
                    repository=repository,
                    provider_name=SIMULATED_PROVIDER_NAME,
                )

            assert await count_games(second_session) == 1


@pytest.mark.asyncio
async def test_run_generations_rejects_mutable_configuration_drift(
    tmp_path: Path,
) -> None:
    mismatched_config = replace(
        create_config(generation_count=1),
        candidate_order_seed=12,
    )

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            with pytest.raises(
                ExperimentConfigurationError,
                match="differs from the immutable experiment snapshot",
            ):
                await run_generations(
                    initial_agents=create_agents(),
                    config=mismatched_config,
                    answer_provider=SimulatedAnswerProvider(),
                    vote_provider=SimulatedVoteProvider(),
                    personality_provider=(SimulatedPersonalityProvider()),
                    repository=GameRepository(session),
                    provider_name=SIMULATED_PROVIDER_NAME,
                )

            assert await count_games(session) == 0


@pytest.mark.asyncio
async def test_run_generations_rejects_a_provider_change(
    tmp_path: Path,
) -> None:
    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            with pytest.raises(
                ProviderConfigurationConflictError,
                match="pinned",
            ):
                await run_generations(
                    initial_agents=create_agents(),
                    config=create_config(generation_count=1),
                    answer_provider=SimulatedAnswerProvider(),
                    vote_provider=SimulatedVoteProvider(),
                    personality_provider=(SimulatedPersonalityProvider()),
                    repository=GameRepository(session),
                    provider_name="Groq llama-3.1-8b-instant",
                )

            assert await count_games(session) == 0


@pytest.mark.asyncio
async def test_partial_final_population_snapshot_cannot_be_loaded_or_resumed(
    tmp_path: Path,
) -> None:
    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)
            results = await run_generations(
                initial_agents=create_agents(),
                config=create_config(generation_count=1),
                answer_provider=SimulatedAnswerProvider(),
                vote_provider=SimulatedVoteProvider(),
                personality_provider=SimulatedPersonalityProvider(),
                repository=repository,
                provider_name=SIMULATED_PROVIDER_NAME,
            )

            async with session.begin():
                await session.execute(
                    delete(GameFinalAgentRecord)
                    .where(GameFinalAgentRecord.game_id == results[0].game_id)
                    .where(GameFinalAgentRecord.position == 2)
                )

            with pytest.raises(
                GenerationConflictError,
                match="incomplete or out-of-order",
            ):
                await repository.load_latest_population()

            with pytest.raises(
                GenerationConflictError,
                match="incomplete or out-of-order",
            ):
                await run_generations(
                    initial_agents=(results[0].game_result.final_agents),
                    config=create_config(generation_count=1),
                    answer_provider=SimulatedAnswerProvider(),
                    vote_provider=SimulatedVoteProvider(),
                    personality_provider=(SimulatedPersonalityProvider()),
                    repository=repository,
                    provider_name=SIMULATED_PROVIDER_NAME,
                )


def test_generation_seed_derivation_is_stable_and_distinct() -> None:
    config = create_config()

    first_generation_seeds = derive_generation_seeds(
        config,
        generation_number=1,
    )
    same_first_generation_seeds = derive_generation_seeds(
        config,
        generation_number=1,
    )
    second_generation_seeds = derive_generation_seeds(
        config,
        generation_number=2,
    )

    assert first_generation_seeds == same_first_generation_seeds
    assert first_generation_seeds != second_generation_seeds


class FailingSecondGenerationAnswerProvider:
    def __init__(self) -> None:
        self.call_count = 0

    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        del question
        self.call_count += 1

        if self.call_count > 6:
            raise RuntimeError("Intentional provider failure")

        return Answer(
            agent_id=agent.id,
            content=f"Answer from {agent.id}",
        )


@pytest.mark.asyncio
async def test_failed_generation_is_not_persisted(
    tmp_path: Path,
) -> None:
    config = create_config(generation_count=2)

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)

            with pytest.raises(InsufficientAnswersError):
                await run_generations(
                    initial_agents=create_agents(),
                    config=config,
                    answer_provider=(FailingSecondGenerationAnswerProvider()),
                    vote_provider=SimulatedVoteProvider(),
                    personality_provider=SimulatedPersonalityProvider(),
                    repository=repository,
                    provider_name="Simulated providers",
                )

            assert await count_games(session) == 1
