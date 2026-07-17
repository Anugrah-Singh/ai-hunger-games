from dataclasses import replace
from datetime import datetime, timezone

import pytest

from ai_hunger_games.analysis import (
    AnalysisConfig,
    HistoryValidationError,
    analyze_history,
)
from ai_hunger_games.history import (
    AgentSnapshot,
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


def create_agent(
    agent_id: str,
    personality_name: str,
) -> AgentSnapshot:
    return AgentSnapshot(
        agent_id=agent_id,
        agent_name=personality_name,
        personality=PersonalitySnapshot(
            name=personality_name,
            description=f"{personality_name} description",
            answer_template=(f"Use {personality_name} reasoning for {{question}}"),
        ),
    )


def create_round(
    answers: tuple[AnswerSnapshot, ...],
    votes: tuple[VoteSnapshot, ...],
    scores: tuple[RoundScoreSnapshot, ...],
) -> RoundSnapshot:
    return RoundSnapshot(
        round_id=1,
        round_number=1,
        question="How should a team make a difficult decision?",
        answers=answers,
        votes=votes,
        scores=scores,
    )


def create_history() -> ExperimentHistory:
    analyst = create_agent("agent_1", "Analyst")
    strategist = create_agent("agent_2", "Strategist")
    mediator = create_agent("agent_3", "Mediator")
    designer = create_agent("agent_4", "Constraint Designer")
    storyteller = create_agent("agent_5", "Storyteller")

    first_round = create_round(
        answers=(
            AnswerSnapshot("candidate_1", "agent_1", "A"),
            AnswerSnapshot("candidate_2", "agent_2", "B"),
            AnswerSnapshot("candidate_3", "agent_3", "C"),
        ),
        votes=(
            VoteSnapshot("agent_1", "candidate_2", "agent_2"),
            VoteSnapshot("agent_2", "candidate_1", "agent_1"),
            VoteSnapshot("agent_3", "candidate_1", "agent_1"),
        ),
        scores=(
            RoundScoreSnapshot("agent_1", 2),
            RoundScoreSnapshot("agent_2", 1),
            RoundScoreSnapshot("agent_3", 0),
        ),
    )
    second_round = create_round(
        answers=(
            AnswerSnapshot("candidate_1", "agent_1", "A"),
            AnswerSnapshot("candidate_2", "agent_2", "B"),
            AnswerSnapshot("candidate_3", "agent_4", "D"),
        ),
        votes=(
            VoteSnapshot("agent_1", "candidate_2", "agent_2"),
            VoteSnapshot("agent_2", "candidate_1", "agent_1"),
            VoteSnapshot("agent_4", "candidate_1", "agent_1"),
        ),
        scores=(
            RoundScoreSnapshot("agent_1", 2),
            RoundScoreSnapshot("agent_2", 1),
            RoundScoreSnapshot("agent_4", 0),
        ),
    )
    seeds = RandomizationSnapshot(1, 2, 3, 4)

    return ExperimentHistory(
        experiment_id=7,
        experiment_name="Analysis fixture",
        generations=(
            GenerationSnapshot(
                game_id=1,
                generation_number=1,
                provider_name="Simulated providers",
                created_at=datetime(2026, 7, 17, tzinfo=timezone.utc),
                seeds=seeds,
                starting_agents=(
                    ParticipantSnapshot(analyst, 2, False),
                    ParticipantSnapshot(strategist, 1, False),
                    ParticipantSnapshot(mediator, 0, True),
                ),
                final_agents=(analyst, strategist, designer),
                rounds=(first_round,),
                eliminated_agent_id="agent_3",
                replacement_agent=designer,
            ),
            GenerationSnapshot(
                game_id=2,
                generation_number=2,
                provider_name="Simulated providers",
                created_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
                seeds=seeds,
                starting_agents=(
                    ParticipantSnapshot(analyst, 2, False),
                    ParticipantSnapshot(strategist, 1, False),
                    ParticipantSnapshot(designer, 0, True),
                ),
                final_agents=(analyst, strategist, storyteller),
                rounds=(second_round,),
                eliminated_agent_id="agent_4",
                replacement_agent=storyteller,
            ),
        ),
    )


def test_analyze_history_calculates_scores_relationships_and_replacements() -> None:
    analysis = analyze_history(
        create_history(),
        AnalysisConfig(
            minimum_pair_opportunities=2,
            minimum_distinct_generations=2,
            minimum_excess_votes=1.0,
            minimum_reciprocal_rounds=2,
        ),
    )

    analyst = next(
        performance
        for performance in analysis.agent_performance
        if performance.agent_id == "agent_1"
    )
    analyst_to_strategist = next(
        relationship
        for relationship in analysis.vote_relationships
        if relationship.voter_agent_id == "agent_1"
        and relationship.target_agent_id == "agent_2"
    )
    designer_outcome = next(
        outcome
        for outcome in analysis.replacement_outcomes
        if outcome.replacement_agent_id == "agent_4"
    )
    reciprocal = next(
        indicator
        for indicator in analysis.reciprocal_vote_indicators
        if {
            indicator.first_agent_id,
            indicator.second_agent_id,
        }
        == {"agent_1", "agent_2"}
    )

    assert analysis.generation_count == 2
    assert analyst.total_points == 4
    assert analyst.average_points_per_round == 2.0
    assert analyst.survival_count == 2
    assert analyst.generation_win_rate == 1.0
    assert analyst.score_slope_per_generation == 0.0
    assert analyst_to_strategist.votes == 2
    assert analyst_to_strategist.eligible_voting_opportunities == 2
    assert analyst_to_strategist.expected_random_votes == 1.0
    assert analyst_to_strategist.vote_rate == 1.0
    assert analyst_to_strategist.random_baseline_rate == 0.5
    assert analyst_to_strategist.excess_votes == 1.0
    assert designer_outcome.status == "observed"
    assert designer_outcome.first_participation_score == 0
    assert designer_outcome.survived_first_participation is False
    assert reciprocal.reciprocal_rounds == 2
    assert reciprocal.meets_history_threshold is True
    assert analysis.personality_diversity.generated_personality_count == 2
    assert analysis.personality_diversity.distinct_name_count == 2
    assert analysis.possible_voting_bloc_indicators == ()
    assert any("not proof" in caution for caution in analysis.cautions)


def test_analyze_history_rejects_persisted_self_votes() -> None:
    history = create_history()
    first_generation = history.generations[0]
    first_round = first_generation.rounds[0]
    invalid_round = replace(
        first_round,
        votes=(
            VoteSnapshot("agent_1", "candidate_1", "agent_1"),
            *first_round.votes[1:],
        ),
    )
    invalid_history = replace(
        history,
        generations=(
            replace(first_generation, rounds=(invalid_round,)),
            history.generations[1],
        ),
    )

    with pytest.raises(HistoryValidationError, match="self-vote"):
        analyze_history(invalid_history)


def test_partial_answer_round_uses_the_actual_eligible_baseline() -> None:
    history = create_history()
    first_generation = history.generations[0]
    first_round = first_generation.rounds[0]
    partial_round = replace(
        first_round,
        answers=first_round.answers[:2],
        votes=first_round.votes[:2],
        scores=(
            RoundScoreSnapshot("agent_1", 1),
            RoundScoreSnapshot("agent_2", 1),
            RoundScoreSnapshot("agent_3", 0),
        ),
    )
    partial_generation = replace(
        first_generation,
        starting_agents=(
            ParticipantSnapshot(first_generation.starting_agents[0].agent, 1, False),
            ParticipantSnapshot(first_generation.starting_agents[1].agent, 1, False),
            ParticipantSnapshot(first_generation.starting_agents[2].agent, 0, True),
        ),
        rounds=(partial_round,),
    )
    partial_history = replace(
        history,
        generations=(partial_generation, history.generations[1]),
    )

    analysis = analyze_history(partial_history)
    relationship = next(
        item
        for item in analysis.vote_relationships
        if item.voter_agent_id == "agent_1" and item.target_agent_id == "agent_2"
    )

    assert relationship.periods[0].expected_random_votes == 1.0
    assert any("partial answer" in caution for caution in analysis.cautions)
