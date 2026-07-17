"""Factories and conversions for durable experiment inputs."""

from ai_hunger_games.generations import GenerationRunConfig
from ai_hunger_games.models import Agent, ExperimentDefinition, Personality
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


def build_default_experiment_definition() -> ExperimentDefinition:
    """Copy the current sample inputs into a snapshot-ready definition."""

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
