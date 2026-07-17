import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_hunger_games.db_models import (
    AnswerFailureRecord,
    AnswerRecord,
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
    validate_agents,
    validate_answer_policy,
    validate_personality_policy,
    validate_vote_policy,
)
from ai_hunger_games.history import (
    AgentSnapshot,
    AnswerFailureSnapshot,
    AnswerSnapshot,
    ExperimentHistory,
    GenerationSnapshot,
    ParticipantSnapshot,
    PersonalitySnapshot,
    RandomizationSnapshot,
    RoundScoreSnapshot,
    RoundSnapshot,
    VoteSnapshot,
)
from ai_hunger_games.models import (
    Agent,
    AnswerGenerationPolicy,
    ExperimentDefinition,
    GameResult,
    Personality,
    PersonalityGenerationPolicy,
    VoteGenerationPolicy,
)

if TYPE_CHECKING:
    from ai_hunger_games.generations import GenerationRunConfig


class ExperimentConfigurationError(RuntimeError):
    """Raised when an experiment lacks a trustworthy runnable definition."""


class ProviderConfigurationConflictError(
    ExperimentConfigurationError,
):
    """Raised when a run tries to mix provider histories."""


class ExperimentRepository:
    """Persist and discover independent experiment histories."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create_experiment(
        self,
        name: str,
        definition: ExperimentDefinition | None = None,
        provider_name: str | None = None,
    ) -> ExperimentRecord:
        normalized_name = name.strip()

        if not normalized_name:
            raise ValueError("Experiment name cannot be empty")

        if definition is None and provider_name is not None:
            raise ValueError("A provider name requires an experiment definition")

        if definition is not None:
            _validate_experiment_definition(definition)

            if provider_name is None or not provider_name.strip():
                raise ValueError("Runnable experiments require a provider name")

        async with self.session.begin():
            experiment = ExperimentRecord(
                name=normalized_name,
                provider_name=(
                    provider_name.strip() if provider_name is not None else None
                ),
            )
            self.session.add(experiment)
            await self.session.flush()

            if definition is not None:
                _add_experiment_definition_records(
                    self.session,
                    experiment,
                    definition,
                )

        return experiment

    async def get_experiment(
        self,
        experiment_id: int,
    ) -> ExperimentRecord | None:
        if experiment_id < 1:
            raise ValueError("Experiment ID must be at least 1")

        async with self.session.begin():
            return await self.session.get(
                ExperimentRecord,
                experiment_id,
            )

    async def get_latest_experiment(
        self,
    ) -> ExperimentRecord | None:
        async with self.session.begin():
            return await self.session.scalar(
                select(ExperimentRecord)
                .order_by(
                    ExperimentRecord.created_at.desc(),
                    ExperimentRecord.id.desc(),
                )
                .limit(1)
            )

    async def get_experiment_for_game(
        self,
        game_id: int,
    ) -> ExperimentRecord | None:
        if game_id < 1:
            raise ValueError("Game ID must be at least 1")

        async with self.session.begin():
            return await self.session.scalar(
                select(ExperimentRecord)
                .join(GameRecord)
                .where(GameRecord.id == game_id)
            )

    async def list_experiments(
        self,
    ) -> list[ExperimentRecord]:
        async with self.session.begin():
            return list(
                await self.session.scalars(
                    select(ExperimentRecord).order_by(
                        ExperimentRecord.created_at.desc(),
                        ExperimentRecord.id.desc(),
                    )
                )
            )

    async def load_initial_population(
        self,
        experiment_id: int,
    ) -> list[Agent] | None:
        """Load the immutable baseline stored when an experiment was created."""

        if experiment_id < 1:
            raise ValueError("Experiment ID must be at least 1")

        async with self.session.begin():
            experiment = await self.session.get(
                ExperimentRecord,
                experiment_id,
            )

            if experiment is None:
                raise ValueError(f"Experiment {experiment_id} does not exist")

            records = await _load_initial_agent_records(
                self.session,
                experiment_id,
            )

            if not records:
                return None

            _validate_initial_agent_positions(records)

            return [_create_agent_from_record(record) for record in records]

    async def load_experiment_definition(
        self,
        experiment_id: int,
    ) -> ExperimentDefinition | None:
        """Load the frozen inputs required to run an experiment again.

        Imported histories predate configuration snapshots and deliberately
        return ``None``. They remain analyzable, but cannot be resumed with
        mutable source-code defaults.
        """

        if experiment_id < 1:
            raise ValueError("Experiment ID must be at least 1")

        async with self.session.begin():
            experiment = await self.session.get(
                ExperimentRecord,
                experiment_id,
            )

            if experiment is None:
                raise ValueError(f"Experiment {experiment_id} does not exist")

            return await _load_experiment_definition(
                self.session,
                experiment_id,
            )


def _validate_experiment_definition(
    definition: ExperimentDefinition,
) -> None:
    if len(definition.initial_agents) < 2:
        raise ValueError("Experiment definitions require at least two initial agents")

    agent_ids = [agent.id for agent in definition.initial_agents]

    if len(agent_ids) != len(set(agent_ids)):
        raise ValueError("Experiment definition agent IDs must be unique")

    if not definition.questions_per_generation:
        raise ValueError("Experiment definitions require at least one question")

    if any(not question.strip() for question in definition.questions_per_generation):
        raise ValueError("Experiment definition questions cannot be empty")

    if definition.seed_stride < 1:
        raise ValueError("Experiment definition seed stride must be at least 1")

    agents = list(definition.initial_agents)
    validate_agents(agents)
    validate_answer_policy(definition.answer_policy)
    validate_vote_policy(definition.vote_policy)
    validate_personality_policy(definition.personality_policy)

    if definition.answer_policy.minimum_successful_answers > len(agents):
        raise ValueError(
            "Minimum successful answers cannot exceed the baseline population size"
        )


def _add_experiment_definition_records(
    session: AsyncSession,
    experiment: ExperimentRecord,
    definition: ExperimentDefinition,
) -> None:
    answer_policy = definition.answer_policy
    vote_policy = definition.vote_policy
    personality_policy = definition.personality_policy

    session.add(
        ExperimentConfigurationRecord(
            experiment_id=experiment.id,
            questions_json=json.dumps(
                definition.questions_per_generation,
                separators=(",", ":"),
            ),
            candidate_order_seed=definition.candidate_order_seed,
            voting_seed=definition.voting_seed,
            elimination_seed=definition.elimination_seed,
            replacement_seed=definition.replacement_seed,
            seed_stride=definition.seed_stride,
            answer_timeout_seconds=answer_policy.timeout_seconds,
            answer_minimum_successful_answers=(
                answer_policy.minimum_successful_answers
            ),
            answer_maximum_attempts=answer_policy.maximum_attempts,
            answer_initial_retry_delay_seconds=(
                answer_policy.initial_retry_delay_seconds
            ),
            answer_maximum_retry_delay_seconds=(
                answer_policy.maximum_retry_delay_seconds
            ),
            answer_maximum_concurrent_requests=(
                answer_policy.maximum_concurrent_requests
            ),
            vote_timeout_seconds=vote_policy.timeout_seconds,
            vote_maximum_attempts=vote_policy.maximum_attempts,
            vote_initial_retry_delay_seconds=(vote_policy.initial_retry_delay_seconds),
            vote_maximum_retry_delay_seconds=(vote_policy.maximum_retry_delay_seconds),
            personality_timeout_seconds=personality_policy.timeout_seconds,
            personality_maximum_attempts=(personality_policy.maximum_attempts),
            personality_initial_retry_delay_seconds=(
                personality_policy.initial_retry_delay_seconds
            ),
            personality_maximum_retry_delay_seconds=(
                personality_policy.maximum_retry_delay_seconds
            ),
        )
    )

    for position, agent in enumerate(
        definition.initial_agents,
        start=1,
    ):
        personality = agent.personality
        session.add(
            ExperimentInitialAgentRecord(
                experiment_id=experiment.id,
                position=position,
                agent_id=agent.id,
                agent_name=agent.name,
                personality_name=personality.name,
                personality_description=personality.description,
                answer_template=personality.answer_template,
            )
        )


async def _load_initial_agent_records(
    session: AsyncSession,
    experiment_id: int,
) -> list[ExperimentInitialAgentRecord]:
    return list(
        await session.scalars(
            select(ExperimentInitialAgentRecord)
            .where(ExperimentInitialAgentRecord.experiment_id == experiment_id)
            .order_by(ExperimentInitialAgentRecord.position)
        )
    )


def _validate_initial_agent_positions(
    records: list[ExperimentInitialAgentRecord],
) -> None:
    expected_positions = list(range(1, len(records) + 1))
    actual_positions = [record.position for record in records]

    if actual_positions != expected_positions:
        raise ExperimentConfigurationError(
            "Experiment baseline population positions must start at one "
            "and be contiguous."
        )


async def _load_experiment_definition(
    session: AsyncSession,
    experiment_id: int,
) -> ExperimentDefinition | None:
    configuration = await session.get(
        ExperimentConfigurationRecord,
        experiment_id,
    )
    initial_agent_records = await _load_initial_agent_records(
        session,
        experiment_id,
    )

    if configuration is None:
        if initial_agent_records:
            raise ExperimentConfigurationError(
                "Experiment has baseline agents but no configuration "
                "snapshot. It cannot be run safely."
            )

        return None

    if not initial_agent_records:
        raise ExperimentConfigurationError(
            "Experiment has a configuration snapshot but no baseline "
            "population. It cannot be run safely."
        )

    _validate_initial_agent_positions(initial_agent_records)

    try:
        parsed_questions = json.loads(configuration.questions_json)
    except json.JSONDecodeError as error:
        raise ExperimentConfigurationError(
            "Experiment configuration contains invalid question JSON."
        ) from error

    if not isinstance(parsed_questions, list) or not all(
        isinstance(question, str) for question in parsed_questions
    ):
        raise ExperimentConfigurationError(
            "Experiment configuration questions must be a JSON array of strings."
        )

    definition = ExperimentDefinition(
        initial_agents=tuple(
            _create_agent_from_record(record) for record in initial_agent_records
        ),
        questions_per_generation=tuple(parsed_questions),
        candidate_order_seed=configuration.candidate_order_seed,
        voting_seed=configuration.voting_seed,
        elimination_seed=configuration.elimination_seed,
        replacement_seed=configuration.replacement_seed,
        answer_policy=AnswerGenerationPolicy(
            timeout_seconds=configuration.answer_timeout_seconds,
            minimum_successful_answers=(
                configuration.answer_minimum_successful_answers
            ),
            maximum_attempts=configuration.answer_maximum_attempts,
            initial_retry_delay_seconds=(
                configuration.answer_initial_retry_delay_seconds
            ),
            maximum_retry_delay_seconds=(
                configuration.answer_maximum_retry_delay_seconds
            ),
            maximum_concurrent_requests=(
                configuration.answer_maximum_concurrent_requests
            ),
        ),
        vote_policy=VoteGenerationPolicy(
            timeout_seconds=configuration.vote_timeout_seconds,
            maximum_attempts=configuration.vote_maximum_attempts,
            initial_retry_delay_seconds=(
                configuration.vote_initial_retry_delay_seconds
            ),
            maximum_retry_delay_seconds=(
                configuration.vote_maximum_retry_delay_seconds
            ),
        ),
        personality_policy=PersonalityGenerationPolicy(
            timeout_seconds=configuration.personality_timeout_seconds,
            maximum_attempts=(configuration.personality_maximum_attempts),
            initial_retry_delay_seconds=(
                configuration.personality_initial_retry_delay_seconds
            ),
            maximum_retry_delay_seconds=(
                configuration.personality_maximum_retry_delay_seconds
            ),
        ),
        seed_stride=configuration.seed_stride,
    )

    try:
        _validate_experiment_definition(definition)
    except ValueError as error:
        raise ExperimentConfigurationError(
            f"Experiment configuration is invalid: {error}"
        ) from error

    return definition


def _create_agent_from_record(
    record: ExperimentInitialAgentRecord,
) -> Agent:
    return Agent(
        id=record.agent_id,
        name=record.agent_name,
        personality=Personality(
            name=record.personality_name,
            description=record.personality_description,
            answer_template=record.answer_template,
        ),
    )


@dataclass(frozen=True)
class GenerationPlan:
    experiment_id: int
    generation_number: int
    replacement_agent_id: str


class GenerationConflictError(RuntimeError):
    """Raised when another runner has advanced an experiment first."""


class GameRepository:
    def __init__(
        self,
        session: AsyncSession,
        experiment_id: int | None = None,
    ) -> None:
        self.session = session
        self.experiment_id = experiment_id

    async def get_next_generation_number(self) -> int:
        async with self.session.begin():
            experiment_id = await self._resolve_experiment_id()
            return await self._get_next_generation_number(experiment_id)

    async def validate_generation_configuration(
        self,
        config: "GenerationRunConfig",
        provider_name: str,
        current_agents: list[Agent],
    ) -> None:
        """Ensure a caller cannot run mutable inputs against saved history."""

        normalized_provider_name = provider_name.strip()

        if not normalized_provider_name:
            raise ValueError("Provider name cannot be empty")

        async with self.session.begin():
            experiment_id = await self._resolve_experiment_id()
            definition = await self._validate_runnable_experiment(
                experiment_id=experiment_id,
                provider_name=normalized_provider_name,
            )
            self._validate_generation_config_matches_definition(
                config=config,
                definition=definition,
            )
            expected_population = await self._load_expected_population(
                experiment_id,
                definition=definition,
            )
            self._validate_population_matches(
                expected_population=expected_population,
                supplied_population=current_agents,
                context="The requested run",
            )

    async def _get_next_generation_number(
        self,
        experiment_id: int,
    ) -> int:
        statement = select(
            func.coalesce(
                func.max(GameRecord.generation_number),
                0,
            )
        ).where(GameRecord.experiment_id == experiment_id)

        result = await self.session.execute(statement)
        current_generation = result.scalar_one()

        return current_generation + 1

    async def _validate_runnable_experiment(
        self,
        experiment_id: int,
        provider_name: str,
    ) -> ExperimentDefinition:
        experiment = await self.session.get(
            ExperimentRecord,
            experiment_id,
        )

        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} does not exist")

        if experiment.provider_name is None:
            raise ExperimentConfigurationError(
                "This imported experiment has no saved provider and "
                "configuration snapshot. Create a new experiment to run "
                "additional generations."
            )

        if experiment.provider_name != provider_name:
            raise ProviderConfigurationConflictError(
                "This experiment is pinned to "
                f"'{experiment.provider_name}', not '{provider_name}'. "
                "Create a separate experiment before changing providers."
            )

        definition = await _load_experiment_definition(
            self.session,
            experiment_id,
        )

        if definition is None:
            raise ExperimentConfigurationError(
                "This experiment has no saved configuration snapshot. "
                "Create a new experiment to run additional generations."
            )

        return definition

    @staticmethod
    def _validate_generation_config_matches_definition(
        config: "GenerationRunConfig",
        definition: ExperimentDefinition,
    ) -> None:
        mismatched_fields: list[str] = []

        if config.questions_per_generation != definition.questions_per_generation:
            mismatched_fields.append("questions")

        for field_name in (
            "candidate_order_seed",
            "voting_seed",
            "elimination_seed",
            "replacement_seed",
            "seed_stride",
            "answer_policy",
            "vote_policy",
            "personality_policy",
        ):
            if getattr(config, field_name) != getattr(
                definition,
                field_name,
            ):
                mismatched_fields.append(field_name)

        if mismatched_fields:
            raise ExperimentConfigurationError(
                "The requested generation configuration differs from the "
                "immutable experiment snapshot: " + ", ".join(mismatched_fields) + "."
            )

    @staticmethod
    def _validate_population_matches(
        expected_population: list[Agent],
        supplied_population: list[Agent],
        context: str,
    ) -> None:
        if expected_population == supplied_population:
            return

        expected_ids = [agent.id for agent in expected_population]
        supplied_ids = [agent.id for agent in supplied_population]
        raise GenerationConflictError(
            f"{context} does not match the experiment's expected "
            "population. Expected ordered agent IDs "
            f"{expected_ids}; received {supplied_ids}."
        )

    @staticmethod
    def _validate_game_result_population(
        game_result: GameResult,
        original_agents: list[Agent],
    ) -> None:
        original_agent_ids = {agent.id for agent in original_agents}

        if game_result.eliminated_agent_id not in original_agent_ids:
            raise ValueError(
                "Game result eliminates an agent outside its starting population."
            )

        if game_result.replacement_agent.id in original_agent_ids:
            raise ValueError(
                "Game result replacement ID is already in its starting population."
            )

        expected_final_agents = [
            agent
            for agent in original_agents
            if agent.id != game_result.eliminated_agent_id
        ]
        expected_final_agents.append(game_result.replacement_agent)

        if expected_final_agents != game_result.final_agents:
            raise ValueError(
                "Game result final population does not match its "
                "elimination and replacement."
            )

        if set(game_result.total_scores_by_agent_id) != original_agent_ids:
            raise ValueError(
                "Game result scores must contain exactly the starting agent IDs."
            )

    @staticmethod
    def _validate_game_result_configuration(
        game_result: GameResult,
        definition: ExperimentDefinition,
        generation_number: int,
    ) -> None:
        seed_offset = (generation_number - 1) * definition.seed_stride
        expected_seeds = (
            definition.candidate_order_seed + seed_offset,
            definition.voting_seed + seed_offset,
            definition.elimination_seed + seed_offset,
            definition.replacement_seed + seed_offset,
        )
        actual_seeds = (
            game_result.seeds.candidate_order_seed,
            game_result.seeds.voting_seed,
            game_result.seeds.elimination_seed,
            game_result.seeds.replacement_seed,
        )

        if actual_seeds != expected_seeds:
            raise ExperimentConfigurationError(
                "Game result seeds do not match the immutable experiment "
                "configuration for this generation."
            )

        expected_questions = definition.questions_per_generation
        actual_questions = tuple(
            round_result.round.question for round_result in game_result.round_results
        )
        actual_numbers = tuple(
            round_result.round.number for round_result in game_result.round_results
        )

        if actual_questions != expected_questions or actual_numbers != tuple(
            range(1, len(expected_questions) + 1)
        ):
            raise ExperimentConfigurationError(
                "Game result rounds do not match the immutable experiment question set."
            )

    async def save_game(
        self,
        game_result: GameResult,
        original_agents: list[Agent],
        provider_name: str,
        plan: GenerationPlan | None = None,
    ) -> GameRecord:
        normalized_provider_name = provider_name.strip()

        if not normalized_provider_name:
            raise ValueError("Provider name cannot be empty")

        async with self.session.begin():
            experiment_id = await self._resolve_experiment_id()
            definition = await self._validate_runnable_experiment(
                experiment_id=experiment_id,
                provider_name=normalized_provider_name,
            )
            expected_population = await self._load_expected_population(
                experiment_id,
                definition=definition,
            )
            self._validate_population_matches(
                expected_population=expected_population,
                supplied_population=original_agents,
                context="The game being saved",
            )
            self._validate_game_result_population(
                game_result=game_result,
                original_agents=original_agents,
            )
            generation_number = await self._get_next_generation_number(experiment_id)
            self._validate_game_result_configuration(
                game_result=game_result,
                definition=definition,
                generation_number=generation_number,
            )

            if plan is not None:
                expected_replacement_agent_id = (
                    await self._get_next_replacement_agent_id(
                        original_agents,
                        experiment_id,
                    )
                )
                self._validate_generation_plan(
                    plan=plan,
                    experiment_id=experiment_id,
                    generation_number=generation_number,
                    expected_replacement_agent_id=(expected_replacement_agent_id),
                    replacement_agent_id=(game_result.replacement_agent.id),
                )

            replacement_personality = game_result.replacement_agent.personality

            game_record = GameRecord(
                experiment_id=experiment_id,
                generation_number=generation_number,
                provider_name=normalized_provider_name,
                candidate_order_seed=(game_result.seeds.candidate_order_seed),
                voting_seed=game_result.seeds.voting_seed,
                elimination_seed=game_result.seeds.elimination_seed,
                replacement_seed=game_result.seeds.replacement_seed,
                eliminated_agent_id=(game_result.eliminated_agent_id),
                replacement_agent_id=(game_result.replacement_agent.id),
                replacement_personality_name=(replacement_personality.name),
                replacement_description=(replacement_personality.description),
                replacement_answer_template=(replacement_personality.answer_template),
            )

            self.session.add(game_record)

            await self.session.flush()

            self._add_agent_snapshots(
                game_record=game_record,
                game_result=game_result,
                original_agents=original_agents,
            )

            await self._add_rounds(
                game_record=game_record,
                game_result=game_result,
                original_agents=original_agents,
            )

            self._add_final_agent_snapshots(
                game_record=game_record,
                final_agents=game_result.final_agents,
            )

        return game_record

    async def load_latest_population(
        self,
    ) -> list[Agent] | None:
        async with self.session.begin():
            experiment_id = await self._resolve_experiment_id()
            latest_game = await self.session.scalar(
                select(GameRecord)
                .where(GameRecord.experiment_id == experiment_id)
                .order_by(
                    GameRecord.generation_number.desc(),
                    GameRecord.id.desc(),
                )
                .limit(1)
            )

            if latest_game is None:
                return None

            final_agent_records = list(
                await self.session.scalars(
                    select(GameFinalAgentRecord)
                    .where(GameFinalAgentRecord.game_id == latest_game.id)
                    .order_by(GameFinalAgentRecord.position)
                )
            )

            if final_agent_records:
                return await self._validated_final_population(
                    latest_game=latest_game,
                    final_agent_records=final_agent_records,
                )

            return await self._reconstruct_legacy_population(latest_game)

    async def load_experiment_history(
        self,
    ) -> ExperimentHistory:
        """Load an experiment into immutable snapshots without ORM laziness."""

        async with self.session.begin():
            experiment_id = await self._resolve_experiment_id()
            experiment = await self.session.get(
                ExperimentRecord,
                experiment_id,
            )

            if experiment is None:
                raise ValueError(f"Experiment {experiment_id} does not exist")

            games = list(
                await self.session.scalars(
                    select(GameRecord)
                    .where(GameRecord.experiment_id == experiment_id)
                    .order_by(
                        GameRecord.generation_number,
                        GameRecord.id,
                    )
                )
            )

            if not games:
                return ExperimentHistory(
                    experiment_id=experiment.id,
                    experiment_name=experiment.name,
                    generations=(),
                )

            game_ids = [game.id for game in games]
            starting_agents_by_game = {game_id: [] for game_id in game_ids}
            final_agents_by_game = {game_id: [] for game_id in game_ids}
            rounds_by_game = {game_id: [] for game_id in game_ids}

            starting_agent_records = list(
                await self.session.scalars(
                    select(GameAgentRecord)
                    .where(GameAgentRecord.game_id.in_(game_ids))
                    .order_by(
                        GameAgentRecord.game_id,
                        GameAgentRecord.id,
                    )
                )
            )
            final_agent_records = list(
                await self.session.scalars(
                    select(GameFinalAgentRecord)
                    .where(GameFinalAgentRecord.game_id.in_(game_ids))
                    .order_by(
                        GameFinalAgentRecord.game_id,
                        GameFinalAgentRecord.position,
                    )
                )
            )
            round_records = list(
                await self.session.scalars(
                    select(RoundRecord)
                    .where(RoundRecord.game_id.in_(game_ids))
                    .order_by(
                        RoundRecord.game_id,
                        RoundRecord.round_number,
                    )
                )
            )

            for record in starting_agent_records:
                starting_agents_by_game[record.game_id].append(record)

            for record in final_agent_records:
                final_agents_by_game[record.game_id].append(record)

            for record in round_records:
                rounds_by_game[record.game_id].append(record)

            rounds_by_id = {record.id: record for record in round_records}
            answers_by_round = {round_id: [] for round_id in rounds_by_id}
            votes_by_round = {round_id: [] for round_id in rounds_by_id}
            scores_by_round = {round_id: [] for round_id in rounds_by_id}
            failures_by_round = {round_id: [] for round_id in rounds_by_id}

            if rounds_by_id:
                round_ids = list(rounds_by_id)
                answer_records = list(
                    await self.session.scalars(
                        select(AnswerRecord)
                        .where(AnswerRecord.round_id.in_(round_ids))
                        .order_by(AnswerRecord.round_id, AnswerRecord.id)
                    )
                )
                vote_records = list(
                    await self.session.scalars(
                        select(VoteRecord)
                        .where(VoteRecord.round_id.in_(round_ids))
                        .order_by(VoteRecord.round_id, VoteRecord.id)
                    )
                )
                score_records = list(
                    await self.session.scalars(
                        select(RoundScoreRecord)
                        .where(RoundScoreRecord.round_id.in_(round_ids))
                        .order_by(
                            RoundScoreRecord.round_id,
                            RoundScoreRecord.agent_id,
                        )
                    )
                )
                failure_records = list(
                    await self.session.scalars(
                        select(AnswerFailureRecord)
                        .where(AnswerFailureRecord.round_id.in_(round_ids))
                        .order_by(
                            AnswerFailureRecord.round_id,
                            AnswerFailureRecord.id,
                        )
                    )
                )

                for record in answer_records:
                    answers_by_round[record.round_id].append(record)

                for record in vote_records:
                    votes_by_round[record.round_id].append(record)

                for record in score_records:
                    scores_by_round[record.round_id].append(record)

                for record in failure_records:
                    failures_by_round[record.round_id].append(record)

            generations = tuple(
                self._create_generation_snapshot(
                    game=game,
                    starting_agent_records=(starting_agents_by_game[game.id]),
                    final_agent_records=final_agents_by_game[game.id],
                    round_records=rounds_by_game[game.id],
                    answers_by_round=answers_by_round,
                    votes_by_round=votes_by_round,
                    scores_by_round=scores_by_round,
                    failures_by_round=failures_by_round,
                )
                for game in games
            )

            return ExperimentHistory(
                experiment_id=experiment.id,
                experiment_name=experiment.name,
                generations=generations,
            )

    async def get_next_replacement_agent_id(
        self,
        current_agents: list[Agent],
    ) -> str:
        async with self.session.begin():
            experiment_id = await self._resolve_experiment_id()
            return await self._get_next_replacement_agent_id(
                current_agents,
                experiment_id,
            )

    async def get_next_generation_plan(
        self,
        current_agents: list[Agent],
    ) -> GenerationPlan:
        async with self.session.begin():
            experiment_id = await self._resolve_experiment_id()
            expected_population = await self._load_expected_population(experiment_id)
            self._validate_population_matches(
                expected_population=expected_population,
                supplied_population=current_agents,
                context="The requested generation",
            )
            generation_number = await self._get_next_generation_number(experiment_id)
            replacement_agent_id = await self._get_next_replacement_agent_id(
                current_agents,
                experiment_id,
            )

        return GenerationPlan(
            experiment_id=experiment_id,
            generation_number=generation_number,
            replacement_agent_id=replacement_agent_id,
        )

    async def _get_next_replacement_agent_id(
        self,
        current_agents: list[Agent],
        experiment_id: int,
    ) -> str:
        used_agent_ids = {agent.id for agent in current_agents}

        used_agent_ids.update(
            await self.session.scalars(
                select(GameAgentRecord.agent_id)
                .join(GameRecord)
                .where(GameRecord.experiment_id == experiment_id)
            )
        )

        used_agent_ids.update(
            await self.session.scalars(
                select(GameRecord.replacement_agent_id).where(
                    GameRecord.experiment_id == experiment_id
                )
            )
        )

        highest_agent_number = 0

        for agent_id in used_agent_ids:
            match = re.fullmatch(r"agent_(\d+)", agent_id)

            if match is not None:
                highest_agent_number = max(
                    highest_agent_number,
                    int(match.group(1)),
                )

        return f"agent_{highest_agent_number + 1}"

    async def _resolve_experiment_id(self) -> int:
        if self.experiment_id is not None:
            experiment = await self.session.get(
                ExperimentRecord,
                self.experiment_id,
            )

            if experiment is None:
                raise ValueError(f"Experiment {self.experiment_id} does not exist")

            return self.experiment_id

        experiment_ids = list(
            await self.session.scalars(
                select(ExperimentRecord.id).order_by(ExperimentRecord.id).limit(2)
            )
        )

        if len(experiment_ids) == 1:
            return experiment_ids[0]

        raise ValueError(
            "GameRepository requires an explicit experiment ID when "
            "the database does not contain exactly one experiment"
        )

    async def _load_expected_population(
        self,
        experiment_id: int,
        definition: ExperimentDefinition | None = None,
    ) -> list[Agent]:
        latest_game = await self.session.scalar(
            select(GameRecord)
            .where(GameRecord.experiment_id == experiment_id)
            .order_by(
                GameRecord.generation_number.desc(),
                GameRecord.id.desc(),
            )
            .limit(1)
        )

        if latest_game is None:
            effective_definition = definition or await _load_experiment_definition(
                self.session,
                experiment_id,
            )

            if effective_definition is None:
                raise ExperimentConfigurationError(
                    "This experiment has no baseline population snapshot. "
                    "Create a new experiment to run generations."
                )

            return list(effective_definition.initial_agents)

        final_agent_records = list(
            await self.session.scalars(
                select(GameFinalAgentRecord)
                .where(GameFinalAgentRecord.game_id == latest_game.id)
                .order_by(GameFinalAgentRecord.position)
            )
        )

        if not final_agent_records:
            raise GenerationConflictError(
                "The latest saved generation has no final-population "
                "snapshot, so it cannot be resumed safely."
            )

        return await self._validated_final_population(
            latest_game=latest_game,
            final_agent_records=final_agent_records,
        )

    async def _validated_final_population(
        self,
        latest_game: GameRecord,
        final_agent_records: list[GameFinalAgentRecord],
    ) -> list[Agent]:
        starting_agent_records = list(
            await self.session.scalars(
                select(GameAgentRecord)
                .where(GameAgentRecord.game_id == latest_game.id)
                .order_by(GameAgentRecord.id)
            )
        )

        if not starting_agent_records:
            raise GenerationConflictError(
                "The latest saved generation has no starting-population "
                "snapshot, so its final population cannot be verified."
            )

        expected_final_agents = [
            self._create_agent(
                agent_id=record.agent_id,
                agent_name=record.agent_name,
                personality_name=record.personality_name,
                personality_description=(record.personality_description),
                answer_template=record.answer_template,
            )
            for record in starting_agent_records
            if record.agent_id != latest_game.eliminated_agent_id
        ]

        if len(expected_final_agents) != len(starting_agent_records) - 1:
            raise GenerationConflictError(
                "The latest saved generation cannot be verified because "
                "its eliminated agent is missing from the starting "
                "snapshot."
            )

        expected_final_agents.append(
            self._create_agent(
                agent_id=latest_game.replacement_agent_id,
                agent_name=latest_game.replacement_personality_name,
                personality_name=latest_game.replacement_personality_name,
                personality_description=(latest_game.replacement_description),
                answer_template=(latest_game.replacement_answer_template),
            )
        )

        expected_positions = list(range(1, len(expected_final_agents) + 1))
        actual_positions = [record.position for record in final_agent_records]

        if actual_positions != expected_positions:
            raise GenerationConflictError(
                "The latest saved generation has an incomplete or "
                "out-of-order final-population snapshot."
            )

        actual_final_agents = [
            self._create_agent(
                agent_id=record.agent_id,
                agent_name=record.agent_name,
                personality_name=record.personality_name,
                personality_description=(record.personality_description),
                answer_template=record.answer_template,
            )
            for record in final_agent_records
        ]

        if actual_final_agents != expected_final_agents:
            raise GenerationConflictError(
                "The latest saved generation has a final-population "
                "snapshot that disagrees with its immutable game records."
            )

        return actual_final_agents

    @staticmethod
    def _validate_generation_plan(
        plan: GenerationPlan,
        experiment_id: int,
        generation_number: int,
        expected_replacement_agent_id: str,
        replacement_agent_id: str,
    ) -> None:
        if plan.experiment_id != experiment_id:
            raise GenerationConflictError(
                "Generation plan belongs to a different experiment"
            )

        if plan.generation_number != generation_number:
            raise GenerationConflictError(
                "Generation plan is stale because this experiment has already advanced"
            )

        if plan.replacement_agent_id != replacement_agent_id:
            raise GenerationConflictError(
                "Game result replacement agent does not match its generation plan"
            )

        if plan.replacement_agent_id != expected_replacement_agent_id:
            raise GenerationConflictError("Generation plan replacement agent is stale")

    def _add_agent_snapshots(
        self,
        game_record: GameRecord,
        game_result: GameResult,
        original_agents: list[Agent],
    ) -> None:
        for agent in original_agents:
            personality = agent.personality

            self.session.add(
                GameAgentRecord(
                    game_id=game_record.id,
                    agent_id=agent.id,
                    agent_name=agent.name,
                    personality_name=personality.name,
                    personality_description=(personality.description),
                    answer_template=(personality.answer_template),
                    total_score=(game_result.total_scores_by_agent_id[agent.id]),
                    was_eliminated=(agent.id == game_result.eliminated_agent_id),
                )
            )

    @staticmethod
    def _create_generation_snapshot(
        game: GameRecord,
        starting_agent_records: list[GameAgentRecord],
        final_agent_records: list[GameFinalAgentRecord],
        round_records: list[RoundRecord],
        answers_by_round: dict[int, list[AnswerRecord]],
        votes_by_round: dict[int, list[VoteRecord]],
        scores_by_round: dict[int, list[RoundScoreRecord]],
        failures_by_round: dict[int, list[AnswerFailureRecord]],
    ) -> GenerationSnapshot:
        starting_agents = tuple(
            ParticipantSnapshot(
                agent=GameRepository._create_agent_snapshot(
                    agent_id=record.agent_id,
                    agent_name=record.agent_name,
                    personality_name=record.personality_name,
                    personality_description=(record.personality_description),
                    answer_template=record.answer_template,
                ),
                total_score=record.total_score,
                was_eliminated=record.was_eliminated,
            )
            for record in starting_agent_records
        )
        final_agents = tuple(
            GameRepository._create_agent_snapshot(
                agent_id=record.agent_id,
                agent_name=record.agent_name,
                personality_name=record.personality_name,
                personality_description=(record.personality_description),
                answer_template=record.answer_template,
            )
            for record in final_agent_records
        )
        rounds = tuple(
            RoundSnapshot(
                round_id=record.id,
                round_number=record.round_number,
                question=record.question,
                answers=tuple(
                    AnswerSnapshot(
                        candidate_id=answer.candidate_id,
                        agent_id=answer.agent_id,
                        content=answer.content,
                        attempt_count=answer.attempt_count,
                    )
                    for answer in answers_by_round[record.id]
                ),
                votes=tuple(
                    VoteSnapshot(
                        voter_agent_id=vote.voter_agent_id,
                        selected_candidate_id=(vote.selected_candidate_id),
                        selected_agent_id=vote.selected_agent_id,
                    )
                    for vote in votes_by_round[record.id]
                ),
                scores=tuple(
                    RoundScoreSnapshot(
                        agent_id=score.agent_id,
                        score=score.score,
                    )
                    for score in scores_by_round[record.id]
                ),
                failures=tuple(
                    AnswerFailureSnapshot(
                        agent_id=failure.agent_id,
                        error_type=failure.error_type,
                        message=failure.message,
                        attempt_count=failure.attempt_count,
                        retry_after_seconds=(failure.retry_after_seconds),
                    )
                    for failure in failures_by_round[record.id]
                ),
            )
            for record in round_records
        )

        return GenerationSnapshot(
            game_id=game.id,
            generation_number=game.generation_number,
            provider_name=game.provider_name,
            created_at=game.created_at,
            seeds=RandomizationSnapshot(
                candidate_order_seed=game.candidate_order_seed,
                voting_seed=game.voting_seed,
                elimination_seed=game.elimination_seed,
                replacement_seed=game.replacement_seed,
            ),
            starting_agents=starting_agents,
            final_agents=final_agents,
            rounds=rounds,
            eliminated_agent_id=game.eliminated_agent_id,
            replacement_agent=(
                GameRepository._create_agent_snapshot(
                    agent_id=game.replacement_agent_id,
                    agent_name=(game.replacement_personality_name),
                    personality_name=(game.replacement_personality_name),
                    personality_description=(game.replacement_description),
                    answer_template=(game.replacement_answer_template),
                )
            ),
        )

    @staticmethod
    def _create_agent_snapshot(
        agent_id: str,
        agent_name: str,
        personality_name: str,
        personality_description: str,
        answer_template: str,
    ) -> AgentSnapshot:
        return AgentSnapshot(
            agent_id=agent_id,
            agent_name=agent_name,
            personality=PersonalitySnapshot(
                name=personality_name,
                description=personality_description,
                answer_template=answer_template,
            ),
        )

    def _add_final_agent_snapshots(
        self,
        game_record: GameRecord,
        final_agents: list[Agent],
    ) -> None:
        for position, agent in enumerate(
            final_agents,
            start=1,
        ):
            personality = agent.personality

            self.session.add(
                GameFinalAgentRecord(
                    game_id=game_record.id,
                    position=position,
                    agent_id=agent.id,
                    agent_name=agent.name,
                    personality_name=personality.name,
                    personality_description=(personality.description),
                    answer_template=personality.answer_template,
                )
            )

    async def _reconstruct_legacy_population(
        self,
        latest_game: GameRecord,
    ) -> list[Agent]:
        starting_agent_records = list(
            await self.session.scalars(
                select(GameAgentRecord)
                .where(GameAgentRecord.game_id == latest_game.id)
                .order_by(GameAgentRecord.id)
            )
        )

        if not starting_agent_records:
            raise GenerationConflictError(
                "Cannot reconstruct the latest legacy population because "
                "its starting-population snapshot is missing."
            )

        surviving_agents = [
            self._create_agent(
                agent_id=record.agent_id,
                agent_name=record.agent_name,
                personality_name=record.personality_name,
                personality_description=(record.personality_description),
                answer_template=record.answer_template,
            )
            for record in starting_agent_records
            if record.agent_id != latest_game.eliminated_agent_id
        ]

        if len(surviving_agents) != len(starting_agent_records) - 1:
            raise GenerationConflictError(
                "Cannot reconstruct the latest legacy population because "
                "its eliminated agent is missing from the starting "
                "snapshot."
            )

        replacement_agent = self._create_agent(
            agent_id=latest_game.replacement_agent_id,
            agent_name=latest_game.replacement_personality_name,
            personality_name=(latest_game.replacement_personality_name),
            personality_description=(latest_game.replacement_description),
            answer_template=(latest_game.replacement_answer_template),
        )

        return [*surviving_agents, replacement_agent]

    @staticmethod
    def _create_agent(
        agent_id: str,
        agent_name: str,
        personality_name: str,
        personality_description: str,
        answer_template: str,
    ) -> Agent:
        return Agent(
            id=agent_id,
            name=agent_name,
            personality=Personality(
                name=personality_name,
                description=personality_description,
                answer_template=answer_template,
            ),
        )

    async def _add_rounds(
        self,
        game_record: GameRecord,
        game_result: GameResult,
        original_agents: list[Agent],
    ) -> None:
        agent_ids = {agent.id for agent in original_agents}

        for round_result in game_result.round_results:
            round_record = RoundRecord(
                game_id=game_record.id,
                round_number=round_result.round.number,
                question=round_result.round.question,
            )

            self.session.add(round_record)
            await self.session.flush()

            candidates_by_id = {
                candidate.id: candidate for candidate in round_result.candidates
            }

            for candidate in round_result.candidates:
                self.session.add(
                    AnswerRecord(
                        round_id=round_record.id,
                        agent_id=(candidate.answer.agent_id),
                        candidate_id=candidate.id,
                        content=candidate.answer.content,
                        attempt_count=(candidate.answer.attempt_count),
                    )
                )

            for failure in round_result.failures:
                self.session.add(
                    AnswerFailureRecord(
                        round_id=round_record.id,
                        agent_id=failure.agent_id,
                        error_type=failure.error_type,
                        message=failure.message,
                        attempt_count=failure.attempt_count,
                        retry_after_seconds=(failure.retry_after_seconds),
                    )
                )

            for vote in round_result.votes:
                selected_candidate = candidates_by_id[vote.candidate_id]

                self.session.add(
                    VoteRecord(
                        round_id=round_record.id,
                        voter_agent_id=vote.voter_id,
                        selected_candidate_id=(vote.candidate_id),
                        selected_agent_id=(selected_candidate.answer.agent_id),
                    )
                )

            round_scores = convert_candidate_scores_to_agent_scores(
                round_result.candidates,
                round_result.scores_by_candidate_id,
            )

            for agent_id in agent_ids:
                self.session.add(
                    RoundScoreRecord(
                        round_id=round_record.id,
                        agent_id=agent_id,
                        score=round_scores.get(
                            agent_id,
                            0,
                        ),
                    )
                )
