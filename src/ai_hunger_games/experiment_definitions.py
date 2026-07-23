"""Factories and conversions for durable experiment inputs."""

from enum import StrEnum

from ai_hunger_games.generations import GenerationRunConfig
from ai_hunger_games.models import (
    Agent,
    AnswerGenerationPolicy,
    ExperimentDefinition,
    Personality,
)
from ai_hunger_games.sample_data import (
    AGENTS,
    ANSWER_POLICY,
    CANDIDATE_ORDER_SEED,
    ELIMINATION_SEED,
    PERSONALITY_POLICY,
    QUESTIONS,
    REPLACEMENT_SEED,
    VOTE_POLICY,
    VOTING_SEED,
)


class ExperimentPreset(StrEnum):
    QUICK_DEMO = "quick_demo"
    FULL_TOURNAMENT = "full_tournament"


DEFAULT_EXPERIMENT_PRESET = ExperimentPreset.QUICK_DEMO

QUICK_DEMO_AGENT_COUNT = 4
QUICK_DEMO_ROUND_COUNT = 3


def build_experiment_definition(
    preset: ExperimentPreset,
) -> ExperimentDefinition:
    """Build an immutable experiment definition for the selected preset."""

    match preset:
        case ExperimentPreset.QUICK_DEMO:
            return _build_quick_demo_definition()
        case ExperimentPreset.FULL_TOURNAMENT:
            return _build_full_tournament_definition()


def build_default_experiment_definition() -> ExperimentDefinition:
    """Build the recruiter-friendly default experiment definition."""

    return build_experiment_definition(DEFAULT_EXPERIMENT_PRESET)


def build_generation_run_config(
    definition: ExperimentDefinition,
    generation_count: int,
) -> GenerationRunConfig:
    return GenerationRunConfig(
        generation_count=generation_count,
        questions_per_generation=definition.questions_per_generation,
        candidate_order_seed=definition.candidate_order_seed,
        voting_seed=definition.voting_seed,
        elimination_seed=definition.elimination_seed,
        replacement_seed=definition.replacement_seed,
        answer_policy=definition.answer_policy,
        vote_policy=definition.vote_policy,
        personality_policy=definition.personality_policy,
        seed_stride=definition.seed_stride,
    )


def _build_quick_demo_definition() -> ExperimentDefinition:
    initial_agents = tuple(
        _copy_agent(agent) for agent in AGENTS[:QUICK_DEMO_AGENT_COUNT]
    )

    questions = tuple(QUESTIONS[:QUICK_DEMO_ROUND_COUNT])

    answer_policy = AnswerGenerationPolicy(
        timeout_seconds=ANSWER_POLICY.timeout_seconds,
        minimum_successful_answers=QUICK_DEMO_AGENT_COUNT,
        maximum_attempts=ANSWER_POLICY.maximum_attempts,
        initial_retry_delay_seconds=(ANSWER_POLICY.initial_retry_delay_seconds),
        maximum_retry_delay_seconds=(ANSWER_POLICY.maximum_retry_delay_seconds),
        maximum_concurrent_requests=(ANSWER_POLICY.maximum_concurrent_requests),
    )

    return ExperimentDefinition(
        initial_agents=initial_agents,
        questions_per_generation=questions,
        candidate_order_seed=CANDIDATE_ORDER_SEED,
        voting_seed=VOTING_SEED,
        elimination_seed=ELIMINATION_SEED,
        replacement_seed=REPLACEMENT_SEED,
        answer_policy=answer_policy,
        vote_policy=VOTE_POLICY,
        personality_policy=PERSONALITY_POLICY,
    )


def _build_full_tournament_definition() -> ExperimentDefinition:
    return ExperimentDefinition(
        initial_agents=tuple(_copy_agent(agent) for agent in AGENTS),
        questions_per_generation=tuple(QUESTIONS),
        candidate_order_seed=CANDIDATE_ORDER_SEED,
        voting_seed=VOTING_SEED,
        elimination_seed=ELIMINATION_SEED,
        replacement_seed=REPLACEMENT_SEED,
        answer_policy=ANSWER_POLICY,
        vote_policy=VOTE_POLICY,
        personality_policy=PERSONALITY_POLICY,
    )


def _copy_agent(agent: Agent) -> Agent:
    return Agent(
        id=agent.id,
        name=agent.name,
        personality=Personality(
            name=agent.personality.name,
            description=agent.personality.description,
            answer_template=agent.personality.answer_template,
        ),
    )
