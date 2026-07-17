from dataclasses import dataclass

from ai_hunger_games.engine import (
    run_game,
    validate_agents,
    validate_answer_policy,
    validate_personality_policy,
    validate_vote_policy,
)
from ai_hunger_games.models import (
    Agent,
    AnswerGenerationPolicy,
    GameResult,
    GameSeeds,
    PersonalityGenerationPolicy,
    VoteGenerationPolicy,
)
from ai_hunger_games.providers import (
    AnswerProvider,
    PersonalityProvider,
    VoteProvider,
)
from ai_hunger_games.repositories import GameRepository


@dataclass(frozen=True)
class GenerationRunConfig:
    generation_count: int
    questions_per_generation: tuple[str, ...]
    candidate_order_seed: int
    voting_seed: int
    elimination_seed: int
    replacement_seed: int
    answer_policy: AnswerGenerationPolicy
    vote_policy: VoteGenerationPolicy
    personality_policy: PersonalityGenerationPolicy
    seed_stride: int = 1_000_000


@dataclass(frozen=True)
class PersistedGenerationResult:
    game_id: int
    generation_number: int
    starting_agents: tuple[Agent, ...]
    game_result: GameResult


def validate_generation_run_config(
    config: GenerationRunConfig,
    initial_agents: list[Agent],
    provider_name: str,
) -> None:
    if config.generation_count < 1:
        raise ValueError("Generation count must be at least 1")

    if not config.questions_per_generation:
        raise ValueError("At least one question is required")

    if any(not question.strip() for question in config.questions_per_generation):
        raise ValueError("Generation questions cannot be empty")

    if config.seed_stride < 1:
        raise ValueError("Generation seed stride must be at least 1")

    if not provider_name.strip():
        raise ValueError("Provider name cannot be empty")

    validate_agents(initial_agents)
    validate_answer_policy(config.answer_policy)
    validate_vote_policy(config.vote_policy)
    validate_personality_policy(config.personality_policy)

    if config.answer_policy.minimum_successful_answers > len(initial_agents):
        raise ValueError("Minimum successful answers cannot exceed the population size")


def derive_generation_seeds(
    config: GenerationRunConfig,
    generation_number: int,
) -> GameSeeds:
    if generation_number < 1:
        raise ValueError("Generation number must be at least 1")

    offset = (generation_number - 1) * config.seed_stride

    return GameSeeds(
        candidate_order_seed=config.candidate_order_seed + offset,
        voting_seed=config.voting_seed + offset,
        elimination_seed=config.elimination_seed + offset,
        replacement_seed=config.replacement_seed + offset,
    )


async def run_generations(
    initial_agents: list[Agent],
    config: GenerationRunConfig,
    answer_provider: AnswerProvider,
    vote_provider: VoteProvider,
    personality_provider: PersonalityProvider,
    repository: GameRepository,
    *,
    provider_name: str,
) -> list[PersistedGenerationResult]:
    """Run and commit complete generations one at a time.

    LLM calls intentionally run outside database transactions. Each finished
    game is saved atomically before its final population becomes the input to
    the next game.
    """

    validate_generation_run_config(
        config=config,
        initial_agents=initial_agents,
        provider_name=provider_name,
    )
    await repository.validate_generation_configuration(
        config=config,
        provider_name=provider_name,
        current_agents=initial_agents,
    )

    current_agents = list(initial_agents)
    persisted_results: list[PersistedGenerationResult] = []

    for _ in range(config.generation_count):
        starting_agents = tuple(current_agents)
        generation_plan = await repository.get_next_generation_plan(current_agents)
        seeds = derive_generation_seeds(
            config=config,
            generation_number=generation_plan.generation_number,
        )

        game_result = await run_game(
            questions=list(config.questions_per_generation),
            agents=current_agents,
            candidate_order_seed=seeds.candidate_order_seed,
            voting_seed=seeds.voting_seed,
            elimination_seed=seeds.elimination_seed,
            replacement_seed=seeds.replacement_seed,
            replacement_agent_id=(generation_plan.replacement_agent_id),
            answer_provider=answer_provider,
            answer_policy=config.answer_policy,
            vote_provider=vote_provider,
            vote_policy=config.vote_policy,
            personality_provider=personality_provider,
            personality_policy=config.personality_policy,
        )

        saved_game = await repository.save_game(
            game_result=game_result,
            original_agents=current_agents,
            provider_name=provider_name,
            plan=generation_plan,
        )

        persisted_results.append(
            PersistedGenerationResult(
                game_id=saved_game.id,
                generation_number=saved_game.generation_number,
                starting_agents=starting_agents,
                game_result=game_result,
            )
        )
        current_agents = game_result.final_agents

    return persisted_results
