import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from ai_hunger_games.database import (
    create_database_engine,
    create_session_factory,
)
from ai_hunger_games.database_setup import (
    ALEMBIC_CONFIG_PATH,
    initialize_database,
)
from ai_hunger_games.db_models import (
    AnswerFailureRecord,
    AnswerRecord,
    Base,
    ExperimentConfigurationRecord,
    ExperimentInitialAgentRecord,
    ExperimentRecord,
    GameAgentRecord,
    GameFinalAgentRecord,
    GameRecord,
    RoundRecord,
    RoundScoreRecord,
    VoteRecord,
)
from ai_hunger_games.engine import (
    convert_candidate_scores_to_agent_scores,
    run_game,
)
from ai_hunger_games.models import (
    Agent,
    Answer,
    AnswerGenerationPolicy,
    ExperimentDefinition,
    GameResult,
    Personality,
    PersonalityGenerationPolicy,
    VoteGenerationPolicy,
)
from ai_hunger_games.providers import (
    RetryableProviderError,
    SimulatedAnswerProvider,
    SimulatedPersonalityProvider,
    SimulatedVoteProvider,
)
from ai_hunger_games.repositories import (
    ExperimentRepository,
    GameRepository,
    GenerationConflictError,
    GenerationPlan,
    ProviderConfigurationConflictError,
)

EXPECTED_APPLICATION_TABLE_NAMES = {
    "answer_failures",
    "answers",
    "experiment_configurations",
    "experiment_initial_agents",
    "experiments",
    "game_agents",
    "game_final_agents",
    "games",
    "round_scores",
    "rounds",
    "votes",
}

ALEMBIC_VERSION_TABLE_NAME = "alembic_version"
EXPECTED_ALEMBIC_REVISION = "0010_enforce_experiment_name_uniqueness"
GENERATION_NUMBER_INDEX_NAME = "uq_games_experiment_generation_number"
SIMULATED_PROVIDER_NAME = "Simulated providers"
TEST_QUESTIONS = (
    "How should a team handle uncertainty?",
    "What makes a difficult decision legitimate?",
)


@asynccontextmanager
async def initialized_database(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]]]:
    database_path = tmp_path / "ai_hunger_games.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    engine = create_database_engine(database_url)

    try:
        await initialize_database(engine)
        session_factory = create_session_factory(engine)

        async with session_factory() as session:
            experiment_repository = ExperimentRepository(session)

            if await experiment_repository.get_latest_experiment() is None:
                await experiment_repository.create_experiment(
                    "Test experiment",
                    definition=create_test_experiment_definition(),
                    provider_name=SIMULATED_PROVIDER_NAME,
                )

        yield engine, session_factory
    finally:
        await engine.dispose()


def create_test_agents() -> list[Agent]:
    return [
        Agent(
            id="agent_1",
            name="Analyst",
            personality=Personality(
                name="Evidence Analyst",
                description="Tests assumptions against evidence.",
                answer_template=("Analyze the evidence for this question: {question}"),
            ),
        ),
        Agent(
            id="agent_2",
            name="Strategist",
            personality=Personality(
                name="Long-Term Strategist",
                description="Weighs tradeoffs over time.",
                answer_template=("Consider the long-term tradeoffs in: {question}"),
            ),
        ),
        Agent(
            id="agent_3",
            name="Mediator",
            personality=Personality(
                name="Empathetic Mediator",
                description="Balances the needs of affected people.",
                answer_template=("Consider the people affected by: {question}"),
            ),
        ),
    ]


def create_answer_policy() -> AnswerGenerationPolicy:
    return AnswerGenerationPolicy(
        timeout_seconds=1.0,
        minimum_successful_answers=2,
        maximum_attempts=1,
        initial_retry_delay_seconds=0.0,
        maximum_retry_delay_seconds=0.0,
    )


def create_vote_policy() -> VoteGenerationPolicy:
    return VoteGenerationPolicy(
        timeout_seconds=1.0,
        maximum_attempts=1,
        initial_retry_delay_seconds=0.0,
        maximum_retry_delay_seconds=0.0,
    )


def create_personality_policy() -> PersonalityGenerationPolicy:
    return PersonalityGenerationPolicy(
        timeout_seconds=1.0,
        maximum_attempts=1,
        initial_retry_delay_seconds=0.0,
        maximum_retry_delay_seconds=0.0,
    )


def create_test_experiment_definition() -> ExperimentDefinition:
    return ExperimentDefinition(
        initial_agents=tuple(create_test_agents()),
        questions_per_generation=TEST_QUESTIONS,
        candidate_order_seed=41,
        voting_seed=73,
        elimination_seed=97,
        replacement_seed=101,
        answer_policy=create_answer_policy(),
        vote_policy=create_vote_policy(),
        personality_policy=create_personality_policy(),
        seed_stride=10_000,
    )


class PartiallyRetryingAnswerProvider:
    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        if agent.id == "agent_3":
            raise RetryableProviderError(
                "The simulated provider is temporarily overloaded",
                retry_after_seconds=0.01,
            )

        return Answer(
            agent_id=agent.id,
            content=f"{agent.name} answered: {question}",
        )


async def create_simulated_game_result(
    agents: list[Agent] | None = None,
    *,
    candidate_order_seed: int = 41,
    voting_seed: int = 73,
    elimination_seed: int = 97,
    replacement_seed: int = 101,
    replacement_agent_id: str = "agent_4",
) -> tuple[list[Agent], GameResult]:
    if agents is None:
        agents = create_test_agents()

    game_result = await run_game(
        questions=list(TEST_QUESTIONS),
        agents=agents,
        candidate_order_seed=candidate_order_seed,
        voting_seed=voting_seed,
        elimination_seed=elimination_seed,
        replacement_seed=replacement_seed,
        replacement_agent_id=replacement_agent_id,
        answer_provider=SimulatedAnswerProvider(),
        answer_policy=create_answer_policy(),
        vote_provider=SimulatedVoteProvider(),
        vote_policy=create_vote_policy(),
        personality_provider=SimulatedPersonalityProvider(),
        personality_policy=create_personality_policy(),
    )

    return agents, game_result


async def create_partially_failed_game_result() -> tuple[list[Agent], GameResult]:
    agents = create_test_agents()
    retrying_policy = AnswerGenerationPolicy(
        timeout_seconds=1.0,
        minimum_successful_answers=2,
        maximum_attempts=2,
        initial_retry_delay_seconds=0.0,
        maximum_retry_delay_seconds=0.0,
    )

    game_result = await run_game(
        questions=list(TEST_QUESTIONS),
        agents=agents,
        candidate_order_seed=41,
        voting_seed=73,
        elimination_seed=97,
        replacement_seed=101,
        replacement_agent_id="agent_4",
        answer_provider=PartiallyRetryingAnswerProvider(),
        answer_policy=retrying_policy,
        vote_provider=SimulatedVoteProvider(),
        vote_policy=create_vote_policy(),
        personality_provider=SimulatedPersonalityProvider(),
        personality_policy=create_personality_policy(),
    )

    return agents, game_result


def get_table_names(connection: Connection) -> list[str]:
    return inspect(connection).get_table_names()


def get_index_names(
    connection: Connection,
    table_name: str,
) -> set[str]:
    return {index["name"] for index in inspect(connection).get_indexes(table_name)}


def get_foreign_key_targets(
    connection: Connection,
    table_name: str,
) -> set[str]:
    return {
        foreign_key["referred_table"]
        for foreign_key in inspect(connection).get_foreign_keys(table_name)
    }


def get_columns(
    connection: Connection,
    table_name: str,
) -> dict[str, dict[str, object]]:
    return {
        column["name"]: column for column in inspect(connection).get_columns(table_name)
    }


def upgrade_to_revision(
    connection: Connection,
    database_url: str,
    revision: str,
) -> None:
    config = Config(str(ALEMBIC_CONFIG_PATH))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["connection"] = connection
    command.upgrade(config, revision)


async def count_records(
    session: AsyncSession,
    record_type: type[Base],
) -> int:
    statement = select(func.count()).select_from(record_type)
    result = await session.execute(statement)

    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_initialize_database_creates_expected_schema(
    tmp_path: Path,
) -> None:
    async with initialized_database(
        tmp_path,
    ) as (engine, _session_factory):
        async with engine.connect() as connection:
            table_names = await connection.run_sync(get_table_names)
            foreign_keys_enabled = await connection.scalar(text("PRAGMA foreign_keys"))
            game_index_names = await connection.run_sync(
                get_index_names,
                "games",
            )
            game_foreign_key_targets = await connection.run_sync(
                get_foreign_key_targets,
                "games",
            )
            game_columns = await connection.run_sync(
                get_columns,
                "games",
            )
            answer_columns = await connection.run_sync(
                get_columns,
                "answers",
            )
            failure_foreign_key_targets = await connection.run_sync(
                get_foreign_key_targets,
                "answer_failures",
            )

    assert set(table_names) == {
        *EXPECTED_APPLICATION_TABLE_NAMES,
        ALEMBIC_VERSION_TABLE_NAME,
    }
    assert foreign_keys_enabled == 1
    assert GENERATION_NUMBER_INDEX_NAME in game_index_names
    assert "experiments" in game_foreign_key_targets
    assert game_columns["experiment_id"]["nullable"] is False
    assert answer_columns["attempt_count"]["nullable"] is False
    assert "rounds" in failure_foreign_key_targets

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            migration_revision = await session.scalar(
                text("SELECT version_num FROM alembic_version")
            )

    assert migration_revision == EXPECTED_ALEMBIC_REVISION


@pytest.mark.asyncio
async def test_initialize_database_upgrades_legacy_schema_without_losing_games(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy_0005.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    engine = create_database_engine(database_url)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                upgrade_to_revision,
                database_url,
                "0005_add_game_randomization_metadata",
            )
            await connection.execute(
                text(
                    "INSERT INTO games ("
                    "generation_number, provider_name, "
                    "eliminated_agent_id, replacement_agent_id, "
                    "replacement_personality_name, "
                    "replacement_description, "
                    "replacement_answer_template, created_at, "
                    "candidate_order_seed, voting_seed, "
                    "elimination_seed, replacement_seed"
                    ") VALUES ("
                    "1, 'Simulated providers', 'agent_1', 'agent_4', "
                    "'Practical Builder', 'Legacy replacement', "
                    "'Answer {question}', '2026-01-01T00:00:00+00:00', "
                    "41, 73, 97, 101"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO game_final_agents ("
                    "game_id, position, agent_id, agent_name, "
                    "personality_name, personality_description, "
                    "answer_template"
                    ") VALUES ("
                    "1, 1, 'agent_4', 'Practical Builder', "
                    "'Practical Builder', 'Legacy replacement', "
                    "'Answer {question}'"
                    ")"
                )
            )
            await connection.execute(text("DROP TABLE alembic_version"))
    finally:
        await engine.dispose()

    engine = create_database_engine(database_url)
    try:
        await initialize_database(engine)
        session_factory = create_session_factory(engine)

        async with session_factory() as session:
            game_count = await count_records(session, GameRecord)
            recreated_final_snapshot_count = await count_records(
                session,
                GameFinalAgentRecord,
            )
            imported_experiment = await session.scalar(
                select(ExperimentRecord).where(
                    ExperimentRecord.name == "Imported legacy history"
                )
            )
            assert imported_experiment is not None
            assigned_game_count = await session.scalar(
                select(func.count())
                .select_from(GameRecord)
                .where(GameRecord.experiment_id == imported_experiment.id)
            )
            migration_revision = await session.scalar(
                text("SELECT version_num FROM alembic_version")
            )

        async with engine.connect() as connection:
            game_index_names = await connection.run_sync(
                get_index_names,
                "games",
            )
    finally:
        await engine.dispose()

    assert game_count == 1
    assert recreated_final_snapshot_count == 1
    assert assigned_game_count == 1
    assert migration_revision == EXPECTED_ALEMBIC_REVISION
    assert GENERATION_NUMBER_INDEX_NAME in game_index_names


@pytest.mark.asyncio
async def test_alembic_command_upgrade_preserves_referenced_sqlite_rows(
    tmp_path: Path,
) -> None:
    """Exercise Alembic's standalone CLI path, not application startup."""

    database_path = tmp_path / "alembic_command_0006.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    engine = create_database_engine(database_url)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                upgrade_to_revision,
                database_url,
                "0006_add_experiment_scoping",
            )
            await connection.execute(
                text(
                    "INSERT INTO experiments (name, created_at) "
                    "VALUES ('CLI migration probe', "
                    "'2026-01-01T00:00:00+00:00')"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO games ("
                    "generation_number, experiment_id, provider_name, "
                    "eliminated_agent_id, replacement_agent_id, "
                    "replacement_personality_name, "
                    "replacement_description, "
                    "replacement_answer_template, created_at"
                    ") VALUES ("
                    "1, 1, 'Simulated providers', 'agent_1', "
                    "'agent_2', 'Replacement', 'Probe replacement', "
                    "'Answer {question}', '2026-01-01T00:00:00+00:00'"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO game_agents ("
                    "game_id, agent_id, agent_name, personality_name, "
                    "personality_description, answer_template, "
                    "total_score, was_eliminated"
                    ") VALUES ("
                    "1, 'agent_1', 'Probe', 'Probe personality', "
                    "'Probe description', 'Answer {question}', 0, 1"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO game_final_agents ("
                    "game_id, position, agent_id, agent_name, "
                    "personality_name, personality_description, "
                    "answer_template"
                    ") VALUES ("
                    "1, 1, 'agent_2', 'Replacement', 'Replacement', "
                    "'Probe replacement', 'Answer {question}'"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO rounds (game_id, round_number, question) "
                    "VALUES (1, 1, 'Probe question')"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO answers ("
                    "round_id, agent_id, candidate_id, content"
                    ") VALUES (1, 'agent_1', 'candidate_1', 'Probe answer')"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO votes ("
                    "round_id, voter_agent_id, selected_candidate_id, "
                    "selected_agent_id"
                    ") VALUES ("
                    "1, 'agent_1', 'candidate_1', 'agent_1'"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO round_scores (round_id, agent_id, score) "
                    "VALUES (1, 'agent_1', 1)"
                )
            )
    finally:
        await engine.dispose()

    config = Config(str(ALEMBIC_CONFIG_PATH))
    config.set_main_option("sqlalchemy.url", database_url)
    await asyncio.to_thread(command.upgrade, config, "head")

    engine = create_database_engine(database_url)
    try:
        session_factory = create_session_factory(engine)
        async with session_factory() as session:
            assert await count_records(session, GameRecord) == 1
            assert await count_records(session, GameAgentRecord) == 1
            assert await count_records(session, GameFinalAgentRecord) == 1
            assert await count_records(session, RoundRecord) == 1
            assert await count_records(session, AnswerRecord) == 1
            assert await count_records(session, VoteRecord) == 1
            assert await count_records(session, RoundScoreRecord) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_alembic_repairs_missing_experiment_name_constraint(
    tmp_path: Path,
) -> None:
    """Repair a historically stamped database without losing child games."""

    database_path = tmp_path / "missing_experiment_name_constraint.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    engine = create_database_engine(database_url)

    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE experiments ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "name VARCHAR(200) NOT NULL, "
                    "created_at DATETIME NOT NULL, "
                    "provider_name VARCHAR(200)"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE games ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "experiment_id INTEGER NOT NULL, "
                    "FOREIGN KEY(experiment_id) REFERENCES experiments(id) "
                    "ON DELETE CASCADE"
                    ")"
                )
            )
            await connection.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
            )
            await connection.execute(
                text(
                    "INSERT INTO experiments (id, name, created_at) VALUES "
                    "(1, 'Constraint repair probe', "
                    "'2026-01-01T00:00:00+00:00')"
                )
            )
            await connection.execute(
                text("INSERT INTO games (id, experiment_id) VALUES (1, 1)")
            )
            await connection.execute(
                text(
                    "INSERT INTO alembic_version (version_num) VALUES "
                    "('0009_snapshot_experiment_definitions')"
                )
            )
    finally:
        await engine.dispose()

    config = Config(str(ALEMBIC_CONFIG_PATH))
    config.set_main_option("sqlalchemy.url", database_url)
    await asyncio.to_thread(command.upgrade, config, "head")

    engine = create_database_engine(database_url)
    try:
        async with engine.begin() as connection:
            game_count = await connection.scalar(text("SELECT COUNT(*) FROM games"))
            foreign_key_violations = (
                await connection.execute(text("PRAGMA foreign_key_check"))
            ).all()

            assert game_count == 1
            assert foreign_key_violations == []

            with pytest.raises(IntegrityError):
                await connection.execute(
                    text(
                        "INSERT INTO experiments (id, name, created_at) "
                        "VALUES (2, 'Constraint repair probe', "
                        "'2026-01-02T00:00:00+00:00')"
                    )
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_initialize_database_rejects_partial_legacy_final_population(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy_0003_partial_snapshot.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    engine = create_database_engine(database_url)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                upgrade_to_revision,
                database_url,
                "0003_enforce_unique_game_generation",
            )
            await connection.execute(
                text(
                    "INSERT INTO games ("
                    "generation_number, provider_name, "
                    "eliminated_agent_id, replacement_agent_id, "
                    "replacement_personality_name, "
                    "replacement_description, "
                    "replacement_answer_template, created_at"
                    ") VALUES ("
                    "1, 'Simulated providers', 'agent_1', 'agent_4', "
                    "'Practical Builder', 'Legacy replacement', "
                    "'Answer {question}', '2026-01-01T00:00:00+00:00'"
                    ")"
                )
            )
            for agent_id, agent_name, personality_name in (
                ("agent_1", "Analyst", "Evidence Analyst"),
                ("agent_2", "Strategist", "Long-Term Strategist"),
                ("agent_3", "Mediator", "Empathetic Mediator"),
            ):
                await connection.execute(
                    text(
                        "INSERT INTO game_agents ("
                        "game_id, agent_id, agent_name, personality_name, "
                        "personality_description, answer_template, "
                        "total_score, was_eliminated"
                        ") VALUES ("
                        "1, :agent_id, :agent_name, :personality_name, "
                        "'Legacy agent', 'Answer {question}', 0, 0"
                        ")"
                    ),
                    {
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "personality_name": personality_name,
                    },
                )
            await connection.execute(
                text(
                    "INSERT INTO game_final_agents ("
                    "game_id, position, agent_id, agent_name, "
                    "personality_name, personality_description, "
                    "answer_template"
                    ") VALUES ("
                    "1, 1, 'agent_2', 'Strategist', "
                    "'Long-Term Strategist', 'Legacy agent', "
                    "'Answer {question}'"
                    ")"
                )
            )
            await connection.execute(text("DROP TABLE alembic_version"))
    finally:
        await engine.dispose()

    engine = create_database_engine(database_url)
    try:
        with pytest.raises(
            RuntimeError,
            match="Final-population snapshot for game 1 is incomplete",
        ):
            await initialize_database(engine)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_save_game_persists_complete_simulated_game(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            saved_game = await GameRepository(session).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            assert saved_game.id == 1
            assert saved_game.experiment_id == 1
            assert await count_records(session, GameRecord) == 1
            assert await count_records(session, GameAgentRecord) == len(agents)
            assert await count_records(session, RoundRecord) == len(
                game_result.round_results
            )

            assert saved_game.candidate_order_seed == (
                game_result.seeds.candidate_order_seed
            )
            assert saved_game.voting_seed == game_result.seeds.voting_seed
            assert saved_game.elimination_seed == (game_result.seeds.elimination_seed)
            assert saved_game.replacement_seed == (game_result.seeds.replacement_seed)


@pytest.mark.asyncio
async def test_experiment_definition_is_durably_snapshotted(
    tmp_path: Path,
) -> None:
    expected_definition = create_test_experiment_definition()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = ExperimentRepository(session)
            experiment = await repository.get_latest_experiment()

            assert experiment is not None

            loaded_definition = await repository.load_experiment_definition(
                experiment.id
            )
            baseline_population = await repository.load_initial_population(
                experiment.id
            )

        async with session_factory() as session:
            configuration_count = await count_records(
                session,
                ExperimentConfigurationRecord,
            )
            initial_agent_count = await count_records(
                session,
                ExperimentInitialAgentRecord,
            )

    assert experiment.provider_name == SIMULATED_PROVIDER_NAME
    assert loaded_definition == expected_definition
    assert baseline_population == list(expected_definition.initial_agents)
    assert configuration_count == 1
    assert initial_agent_count == len(expected_definition.initial_agents)


@pytest.mark.asyncio
async def test_load_experiment_history_returns_detached_snapshots(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)
            saved_game = await repository.save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )
            history = await repository.load_experiment_history()

    generation = history.generations[0]

    assert history.experiment_name == "Test experiment"
    assert generation.game_id == saved_game.id
    assert generation.generation_number == 1
    assert len(generation.starting_agents) == len(agents)
    assert len(generation.final_agents) == len(game_result.final_agents)
    assert len(generation.rounds) == len(game_result.round_results)
    assert len(generation.rounds[0].answers) == len(
        game_result.round_results[0].answers
    )
    assert len(generation.rounds[0].votes) == len(game_result.round_results[0].votes)


@pytest.mark.asyncio
async def test_experiments_scope_generation_numbers(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            experiment_repository = ExperimentRepository(session)
            first_experiment = await experiment_repository.get_latest_experiment()
            second_experiment = await experiment_repository.create_experiment(
                "Second experiment",
                definition=create_test_experiment_definition(),
                provider_name=SIMULATED_PROVIDER_NAME,
            )

            assert first_experiment is not None

            first_game = await GameRepository(
                session,
                first_experiment.id,
            ).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )
            second_game = await GameRepository(
                session,
                second_experiment.id,
            ).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )
            first_generation_number = first_game.generation_number
            second_generation_number = second_game.generation_number
            first_experiment_id = first_game.experiment_id
            second_experiment_id = second_game.experiment_id

            with pytest.raises(ValueError, match="explicit experiment ID"):
                await GameRepository(session).get_next_generation_number()

    assert first_generation_number == 1
    assert second_generation_number == 1
    assert first_experiment_id != second_experiment_id


@pytest.mark.asyncio
async def test_save_game_assigns_first_generation_number(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            saved_game = await GameRepository(session).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

    assert saved_game.generation_number == 1


@pytest.mark.asyncio
async def test_reading_next_generation_number_does_not_block_save(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)

            next_generation_number = await repository.get_next_generation_number()
            saved_game = await repository.save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

    assert next_generation_number == 1
    assert saved_game.generation_number == 1


@pytest.mark.asyncio
async def test_save_game_increments_generation_number(
    tmp_path: Path,
) -> None:
    agents, first_game_result = await create_simulated_game_result()
    second_agents = first_game_result.final_agents
    _, second_game_result = await create_simulated_game_result(
        agents=second_agents,
        candidate_order_seed=10_041,
        voting_seed=10_073,
        elimination_seed=10_097,
        replacement_seed=10_101,
        replacement_agent_id="agent_5",
    )

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)

            first_game = await repository.save_game(
                game_result=first_game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )
            second_game = await repository.save_game(
                game_result=second_game_result,
                original_agents=second_agents,
                provider_name="Simulated providers",
            )

    assert first_game.generation_number == 1
    assert second_game.generation_number == 2


@pytest.mark.asyncio
async def test_save_game_rejects_a_provider_change_within_an_experiment(
    tmp_path: Path,
) -> None:
    agents, first_game_result = await create_simulated_game_result()
    current_agents = first_game_result.final_agents
    _, second_game_result = await create_simulated_game_result(
        agents=current_agents,
        candidate_order_seed=10_041,
        voting_seed=10_073,
        elimination_seed=10_097,
        replacement_seed=10_101,
        replacement_agent_id="agent_5",
    )

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)
            await repository.save_game(
                game_result=first_game_result,
                original_agents=agents,
                provider_name=SIMULATED_PROVIDER_NAME,
            )

            with pytest.raises(
                ProviderConfigurationConflictError,
                match="pinned",
            ):
                await repository.save_game(
                    game_result=second_game_result,
                    original_agents=current_agents,
                    provider_name="Groq llama-3.1-8b-instant",
                )

            assert await count_records(session, GameRecord) == 1


@pytest.mark.asyncio
async def test_save_game_persists_all_participating_agents(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            saved_game = await GameRepository(session).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            records = list(
                await session.scalars(
                    select(GameAgentRecord).where(
                        GameAgentRecord.game_id == saved_game.id
                    )
                )
            )

    assert {record.agent_id for record in records} == {agent.id for agent in agents}


@pytest.mark.asyncio
async def test_save_game_persists_final_population_snapshot(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            saved_game = await GameRepository(session).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            records = list(
                await session.scalars(
                    select(GameFinalAgentRecord)
                    .where(GameFinalAgentRecord.game_id == saved_game.id)
                    .order_by(GameFinalAgentRecord.position)
                )
            )

    assert [record.position for record in records] == [1, 2, 3]
    assert [record.agent_id for record in records] == [
        agent.id for agent in game_result.final_agents
    ]
    assert [record.answer_template for record in records] == [
        agent.personality.answer_template for agent in game_result.final_agents
    ]


@pytest.mark.asyncio
async def test_load_latest_population_returns_none_without_games(
    tmp_path: Path,
) -> None:
    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            population = await GameRepository(session).load_latest_population()

    assert population is None


@pytest.mark.asyncio
async def test_load_latest_population_uses_final_population_snapshot(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)
            await repository.save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            population = await repository.load_latest_population()

    assert population is not None
    assert [agent.id for agent in population] == [
        agent.id for agent in game_result.final_agents
    ]
    assert [agent.personality.name for agent in population] == [
        agent.personality.name for agent in game_result.final_agents
    ]


@pytest.mark.asyncio
async def test_load_latest_population_reconstructs_legacy_game(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)
            saved_game = await repository.save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            async with session.begin():
                await session.execute(
                    delete(GameFinalAgentRecord).where(
                        GameFinalAgentRecord.game_id == saved_game.id
                    )
                )

            population = await repository.load_latest_population()

    assert population is not None
    assert [agent.id for agent in population] == [
        agent.id for agent in game_result.final_agents
    ]


@pytest.mark.asyncio
async def test_next_replacement_agent_id_uses_historical_agents(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)
            await repository.save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            replacement_agent_id = await repository.get_next_replacement_agent_id(
                game_result.final_agents
            )

    assert replacement_agent_id == "agent_5"


@pytest.mark.asyncio
async def test_next_generation_plan_is_consistent_with_history(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)
            await repository.save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            generation_plan = await repository.get_next_generation_plan(
                game_result.final_agents
            )

    assert generation_plan.generation_number == 2
    assert generation_plan.replacement_agent_id == "agent_5"


@pytest.mark.asyncio
async def test_stale_generation_plan_does_not_persist_another_game(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)
            plan = await repository.get_next_generation_plan(agents)

            await repository.save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
                plan=plan,
            )

            current_agents = game_result.final_agents
            _, next_game_result = await create_simulated_game_result(
                agents=current_agents,
                candidate_order_seed=10_041,
                voting_seed=10_073,
                elimination_seed=10_097,
                replacement_seed=10_101,
                replacement_agent_id="agent_5",
            )
            stale_plan = GenerationPlan(
                experiment_id=plan.experiment_id,
                generation_number=plan.generation_number,
                replacement_agent_id="agent_5",
            )

            with pytest.raises(
                GenerationConflictError,
                match="stale",
            ):
                await repository.save_game(
                    game_result=next_game_result,
                    original_agents=current_agents,
                    provider_name="Simulated providers",
                    plan=stale_plan,
                )

            assert await count_records(session, GameRecord) == 1


@pytest.mark.asyncio
async def test_save_game_marks_eliminated_agent(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            saved_game = await GameRepository(session).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            records = list(
                await session.scalars(
                    select(GameAgentRecord).where(
                        GameAgentRecord.game_id == saved_game.id
                    )
                )
            )

    eliminated_records = [record for record in records if record.was_eliminated]

    assert len(eliminated_records) == 1
    assert eliminated_records[0].agent_id == (game_result.eliminated_agent_id)


@pytest.mark.asyncio
async def test_save_game_persists_every_round(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            saved_game = await GameRepository(session).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            records = list(
                await session.scalars(
                    select(RoundRecord)
                    .where(RoundRecord.game_id == saved_game.id)
                    .order_by(RoundRecord.round_number)
                )
            )

    assert [record.round_number for record in records] == [
        round_result.round.number for round_result in game_result.round_results
    ]
    assert [record.question for record in records] == [
        round_result.round.question for round_result in game_result.round_results
    ]


@pytest.mark.asyncio
async def test_save_game_persists_one_answer_per_successful_agent(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            saved_game = await GameRepository(session).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            round_records = list(
                await session.scalars(
                    select(RoundRecord)
                    .where(RoundRecord.game_id == saved_game.id)
                    .order_by(RoundRecord.round_number)
                )
            )

            stored_agent_ids_by_round = {
                round_record.round_number: {
                    answer.agent_id
                    for answer in await session.scalars(
                        select(AnswerRecord).where(
                            AnswerRecord.round_id == round_record.id
                        )
                    )
                }
                for round_record in round_records
            }

    expected_agent_ids_by_round = {
        round_result.round.number: {answer.agent_id for answer in round_result.answers}
        for round_result in game_result.round_results
    }

    assert stored_agent_ids_by_round == expected_agent_ids_by_round


@pytest.mark.asyncio
async def test_save_game_persists_answer_retry_and_failure_telemetry(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_partially_failed_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            saved_game = await GameRepository(session).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name=SIMULATED_PROVIDER_NAME,
            )
            history = await GameRepository(session).load_experiment_history()
            round_records = list(
                await session.scalars(
                    select(RoundRecord)
                    .where(RoundRecord.game_id == saved_game.id)
                    .order_by(RoundRecord.round_number)
                )
            )
            answers_by_round = {
                round_record.round_number: list(
                    await session.scalars(
                        select(AnswerRecord)
                        .where(AnswerRecord.round_id == round_record.id)
                        .order_by(AnswerRecord.agent_id)
                    )
                )
                for round_record in round_records
            }
            failures_by_round = {
                round_record.round_number: list(
                    await session.scalars(
                        select(AnswerFailureRecord).where(
                            AnswerFailureRecord.round_id == round_record.id
                        )
                    )
                )
                for round_record in round_records
            }

    assert {
        round_number: {answer.agent_id: answer.attempt_count for answer in answers}
        for round_number, answers in answers_by_round.items()
    } == {
        1: {"agent_1": 1, "agent_2": 1},
        2: {"agent_1": 1, "agent_2": 1},
    }
    assert {
        round_number: [
            (
                failure.agent_id,
                failure.error_type,
                failure.attempt_count,
                failure.retry_after_seconds,
            )
            for failure in failures
        ]
        for round_number, failures in failures_by_round.items()
    } == {
        1: [("agent_3", "RetryableProviderError", 2, 0.01)],
        2: [("agent_3", "RetryableProviderError", 2, 0.01)],
    }
    assert [
        failure.retry_after_seconds
        for failure in history.generations[0].rounds[0].failures
    ] == [0.01]


@pytest.mark.asyncio
async def test_save_game_persists_one_vote_per_participating_voter(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            saved_game = await GameRepository(session).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            round_records = list(
                await session.scalars(
                    select(RoundRecord)
                    .where(RoundRecord.game_id == saved_game.id)
                    .order_by(RoundRecord.round_number)
                )
            )

            stored_voter_ids_by_round = {
                round_record.round_number: {
                    vote.voter_agent_id
                    for vote in await session.scalars(
                        select(VoteRecord).where(VoteRecord.round_id == round_record.id)
                    )
                }
                for round_record in round_records
            }

    expected_voter_ids_by_round = {
        round_result.round.number: {vote.voter_id for vote in round_result.votes}
        for round_result in game_result.round_results
    }

    assert stored_voter_ids_by_round == expected_voter_ids_by_round


@pytest.mark.asyncio
async def test_save_game_persists_round_scores(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            saved_game = await GameRepository(session).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

            round_records = list(
                await session.scalars(
                    select(RoundRecord)
                    .where(RoundRecord.game_id == saved_game.id)
                    .order_by(RoundRecord.round_number)
                )
            )

            stored_scores_by_round = {
                round_record.round_number: {
                    score.agent_id: score.score
                    for score in await session.scalars(
                        select(RoundScoreRecord).where(
                            RoundScoreRecord.round_id == round_record.id
                        )
                    )
                }
                for round_record in round_records
            }

    expected_scores_by_round = {
        round_result.round.number: (
            convert_candidate_scores_to_agent_scores(
                round_result.candidates,
                round_result.scores_by_candidate_id,
            )
        )
        for round_result in game_result.round_results
    }

    assert stored_scores_by_round == expected_scores_by_round


@pytest.mark.asyncio
async def test_save_game_persists_replacement_personality_fields(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            saved_game = await GameRepository(session).save_game(
                game_result=game_result,
                original_agents=agents,
                provider_name="Simulated providers",
            )

    replacement = game_result.replacement_agent

    assert saved_game.replacement_agent_id == replacement.id
    assert saved_game.replacement_personality_name == (replacement.personality.name)
    assert saved_game.replacement_description == (replacement.personality.description)
    assert saved_game.replacement_answer_template == (
        replacement.personality.answer_template
    )


@pytest.mark.asyncio
async def test_save_game_rolls_back_on_constraint_failure(
    tmp_path: Path,
) -> None:
    agents, game_result = await create_simulated_game_result()
    first_round = game_result.round_results[0]
    first_round.candidates[1].answer.agent_id = first_round.candidates[
        0
    ].answer.agent_id

    async with initialized_database(
        tmp_path,
    ) as (_engine, session_factory):
        async with session_factory() as session:
            repository = GameRepository(session)

            with pytest.raises(IntegrityError):
                await repository.save_game(
                    game_result=game_result,
                    original_agents=agents,
                    provider_name="Simulated providers",
                )

            assert await count_records(session, GameRecord) == 0
            assert await count_records(session, GameAgentRecord) == 0
            assert await count_records(session, RoundRecord) == 0
            assert await count_records(session, AnswerRecord) == 0
            assert await count_records(session, AnswerFailureRecord) == 0
            assert await count_records(session, VoteRecord) == 0
            assert await count_records(session, RoundScoreRecord) == 0
