import argparse
import asyncio

from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from ai_hunger_games.database import (
    create_database_engine,
    create_session_factory,
)
from ai_hunger_games.database_setup import initialize_database
from ai_hunger_games.db_models import ExperimentRecord
from ai_hunger_games.experiment_definitions import (
    build_default_experiment_definition,
    build_generation_run_config,
)
from ai_hunger_games.generations import run_generations
from ai_hunger_games.groq_providers import (
    GroqAnswerProvider,
    GroqPersonalityProvider,
    GroqVoteProvider,
)
from ai_hunger_games.models import Agent, ExperimentDefinition
from ai_hunger_games.providers import (
    AnswerProvider,
    PersonalityProvider,
    SimulatedAnswerProvider,
    SimulatedPersonalityProvider,
    SimulatedVoteProvider,
    VoteProvider,
)
from ai_hunger_games.repositories import (
    ExperimentConfigurationError,
    ExperimentRepository,
    GameRepository,
    ProviderConfigurationConflictError,
)
from ai_hunger_games.settings import (
    Settings,
    load_settings,
    require_groq_api_key,
)
from ai_hunger_games.terminal import render_generation_result


def create_providers(
    settings: Settings,
) -> tuple[
    AnswerProvider,
    VoteProvider,
    PersonalityProvider,
    AsyncGroq | None,
]:
    if not settings.use_real_llm:
        return (
            SimulatedAnswerProvider(),
            SimulatedVoteProvider(),
            SimulatedPersonalityProvider(),
            None,
        )

    api_key = require_groq_api_key(settings)
    client = AsyncGroq(
        api_key=api_key,
        max_retries=0,
    )

    return (
        GroqAnswerProvider(
            client=client,
            model=settings.groq_model,
        ),
        GroqVoteProvider(
            client=client,
            model=settings.groq_model,
        ),
        GroqPersonalityProvider(
            client=client,
            model=settings.groq_model,
        ),
        client,
    )


def provider_name_for_settings(settings: Settings) -> str:
    if settings.use_real_llm:
        return f"Groq ({settings.groq_model})"

    return "Simulated providers"


async def main(
    generation_count: int = 1,
    *,
    new_experiment_name: str | None = None,
    experiment_id: int | None = None,
    list_experiments: bool = False,
) -> None:
    settings = load_settings()
    provider_name = provider_name_for_settings(settings)
    database_engine = create_database_engine()
    groq_client: AsyncGroq | None = None

    try:
        await initialize_database(database_engine)

        async with create_session_factory(database_engine)() as session:
            experiment_repository = ExperimentRepository(session)

            if list_experiments:
                await _print_experiments(experiment_repository)
                return

            experiment, definition, starting_agents = await _resolve_experiment(
                experiment_repository=experiment_repository,
                session=session,
                new_experiment_name=new_experiment_name,
                experiment_id=experiment_id,
                provider_name=provider_name,
            )
            repository = GameRepository(
                session,
                experiment.id,
            )

            print(f"Provider: {provider_name}")
            print(f"Experiment: {experiment.name} (ID: {experiment.id})")
            print()

            (
                answer_provider,
                vote_provider,
                personality_provider,
                groq_client,
            ) = create_providers(settings)

            results = await run_generations(
                initial_agents=starting_agents,
                config=build_generation_run_config(
                    definition,
                    generation_count,
                ),
                answer_provider=answer_provider,
                vote_provider=vote_provider,
                personality_provider=personality_provider,
                repository=repository,
                provider_name=provider_name,
            )

        for index, result in enumerate(results):
            if index:
                print()

            print(render_generation_result(result))
    finally:
        await database_engine.dispose()

        if groq_client is not None:
            await groq_client.close()


async def _resolve_experiment(
    experiment_repository: ExperimentRepository,
    session: AsyncSession,
    new_experiment_name: str | None,
    experiment_id: int | None,
    provider_name: str,
) -> tuple[ExperimentRecord, ExperimentDefinition, list[Agent]]:
    if new_experiment_name is not None:
        definition = build_default_experiment_definition()
        experiment = await experiment_repository.create_experiment(
            name=new_experiment_name,
            definition=definition,
            provider_name=provider_name,
        )
        return experiment, definition, list(definition.initial_agents)

    if experiment_id is not None:
        experiment = await experiment_repository.get_experiment(experiment_id)

        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} does not exist")
    else:
        experiment = await experiment_repository.get_latest_experiment()

        if experiment is None:
            definition = build_default_experiment_definition()
            experiment = await experiment_repository.create_experiment(
                name="Default experiment",
                definition=definition,
                provider_name=provider_name,
            )
            return experiment, definition, list(definition.initial_agents)

    if experiment.provider_name is None:
        raise ExperimentConfigurationError(
            "This imported experiment has no frozen run configuration. "
            "Start a new experiment before running generations."
        )

    if experiment.provider_name != provider_name:
        raise ProviderConfigurationConflictError(
            "This experiment is pinned to "
            f"'{experiment.provider_name}', not '{provider_name}'. "
            "Start a new experiment before changing providers."
        )

    definition = await experiment_repository.load_experiment_definition(experiment.id)

    if definition is None:
        raise ExperimentConfigurationError(
            "This experiment has no frozen run configuration. Start a "
            "new experiment before running generations."
        )

    repository = GameRepository(session, experiment.id)
    saved_population = await repository.load_latest_population()

    return (
        experiment,
        definition,
        saved_population or list(definition.initial_agents),
    )


async def _print_experiments(
    experiment_repository: ExperimentRepository,
) -> None:
    experiments = await experiment_repository.list_experiments()

    if not experiments:
        print("No experiments have been created.")
        return

    for experiment in experiments:
        print(
            f"{experiment.id}: {experiment.name} ({experiment.created_at.isoformat()})"
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run AI Hunger Games generations.",
    )
    parser.add_argument(
        "--generations",
        type=positive_integer,
        default=1,
        help="Number of completed generations to run.",
    )
    experiment_group = parser.add_mutually_exclusive_group()
    experiment_group.add_argument(
        "--new-experiment",
        type=nonempty_string,
        help="Create a new experiment from the eight-agent baseline.",
    )
    experiment_group.add_argument(
        "--experiment-id",
        type=positive_integer,
        help="Resume a specific saved experiment.",
    )
    parser.add_argument(
        "--list-experiments",
        action="store_true",
        help="List saved experiments without running a generation.",
    )

    return parser.parse_args()


def positive_integer(value: str) -> int:
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error

    if parsed_value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")

    return parsed_value


def nonempty_string(value: str) -> str:
    normalized_value = value.strip()

    if not normalized_value:
        raise argparse.ArgumentTypeError("cannot be empty")

    return normalized_value


if __name__ == "__main__":
    arguments = parse_arguments()
    asyncio.run(
        main(
            arguments.generations,
            new_experiment_name=arguments.new_experiment,
            experiment_id=arguments.experiment_id,
            list_experiments=arguments.list_experiments,
        )
    )
