"""Deterministic, cautious metrics over persisted experiment history."""

from dataclasses import dataclass, field
from itertools import combinations

from ai_hunger_games.history import (
    ExperimentHistory,
    GenerationSnapshot,
    ParticipantSnapshot,
    PersonalitySnapshot,
    RoundSnapshot,
)

type PersonalityKey = tuple[str, str, str]
type RelationshipKey = tuple[str, str]
type PairKey = tuple[str, str]
type ParticipantObservation = tuple[
    GenerationSnapshot,
    ParticipantSnapshot,
    bool,
]


class HistoryValidationError(ValueError):
    """Raised when persisted facts cannot support trustworthy metrics."""


@dataclass(frozen=True)
class AnalysisConfig:
    minimum_pair_opportunities: int = 8
    minimum_distinct_generations: int = 3
    minimum_excess_votes: float = 3.0
    minimum_reciprocal_rounds: int = 3


@dataclass(frozen=True)
class GenerationScore:
    generation_number: int
    total_score: int
    round_count: int
    average_points_per_round: float | None
    was_eliminated: bool
    won_generation: bool


@dataclass(frozen=True)
class AgentPerformance:
    agent_id: str
    agent_name: str
    personality: PersonalitySnapshot
    generation_scores: tuple[GenerationScore, ...]
    total_points: int
    scored_round_count: int
    average_points_per_round: float | None
    survival_count: int
    elimination_generation: int | None
    generation_win_count: int
    generation_win_rate: float | None
    score_slope_per_generation: float | None


@dataclass(frozen=True)
class RelationshipPeriod:
    generation_number: int
    votes: int
    eligible_voting_opportunities: int
    expected_random_votes: float


@dataclass(frozen=True)
class VoteRelationship:
    voter_agent_id: str
    target_agent_id: str
    periods: tuple[RelationshipPeriod, ...]
    votes: int
    eligible_voting_opportunities: int
    expected_random_votes: float
    vote_rate: float | None
    random_baseline_rate: float | None
    excess_votes: float
    excess_rate: float | None


@dataclass(frozen=True)
class PersonalityPerformance:
    personality: PersonalitySnapshot
    agent_ids: tuple[str, ...]
    generation_participations: int
    generation_survivals: int
    total_points: int
    scored_round_count: int
    average_points_per_round: float | None
    generation_win_count: int
    replacement_observation_count: int
    replacement_success_rate: float | None


@dataclass(frozen=True)
class PersonalityDiversity:
    generated_personality_count: int
    distinct_name_count: int
    distinct_instruction_count: int
    distinct_name_rate: float | None
    distinct_instruction_rate: float | None


@dataclass(frozen=True)
class ReplacementOutcome:
    created_in_generation: int
    replacement_agent_id: str
    personality: PersonalitySnapshot
    first_participation_generation: int | None
    first_participation_score: int | None
    survived_first_participation: bool | None
    status: str


@dataclass(frozen=True)
class ReciprocalVoteIndicator:
    first_agent_id: str
    second_agent_id: str
    reciprocal_rounds: int
    eligible_co_voting_rounds: int
    expected_random_reciprocal_rounds: float
    distinct_generations: int
    meets_history_threshold: bool


@dataclass(frozen=True)
class PossibleVotingBlocIndicator:
    agent_ids: tuple[str, ...]
    supporting_agent_pairs: tuple[PairKey, ...]
    distinct_generations: int
    caveat: str


@dataclass(frozen=True)
class EntryAdjacentRelationshipChange:
    entrant_agent_id: str
    entry_generation: int
    voter_agent_id: str
    target_agent_id: str
    previous_vote_rate: float
    entry_vote_rate: float
    rate_change: float
    previous_excess_votes: float
    entry_excess_votes: float


@dataclass(frozen=True)
class ExperimentAnalysis:
    experiment_id: int
    experiment_name: str
    generation_count: int
    agent_performance: tuple[AgentPerformance, ...]
    vote_relationships: tuple[VoteRelationship, ...]
    personality_performance: tuple[PersonalityPerformance, ...]
    personality_diversity: PersonalityDiversity
    replacement_outcomes: tuple[ReplacementOutcome, ...]
    reciprocal_vote_indicators: tuple[ReciprocalVoteIndicator, ...]
    possible_voting_bloc_indicators: tuple[PossibleVotingBlocIndicator, ...]
    entry_adjacent_changes: tuple[EntryAdjacentRelationshipChange, ...]
    cautions: tuple[str, ...]


@dataclass
class _PeriodCounter:
    votes: int = 0
    opportunities: int = 0
    expected_random_votes: float = 0.0


@dataclass
class _RelationshipCounter:
    votes: int = 0
    opportunities: int = 0
    expected_random_votes: float = 0.0
    periods: dict[int, _PeriodCounter] = field(default_factory=dict)


@dataclass
class _ReciprocalCounter:
    reciprocal_rounds: int = 0
    eligible_co_voting_rounds: int = 0
    expected_random_reciprocal_rounds: float = 0.0
    generations: set[int] = field(default_factory=set)


def analyze_history(
    history: ExperimentHistory,
    config: AnalysisConfig | None = None,
) -> ExperimentAnalysis:
    """Calculate descriptive metrics without issuing database or LLM calls."""

    effective_config = config or AnalysisConfig()
    _validate_analysis_config(effective_config)
    cautions = _validate_history(history)

    relationship_counters = _build_relationship_counters(history)
    reciprocal_counters = _build_reciprocal_counters(history)
    replacement_outcomes = _build_replacement_outcomes(history)
    agent_performance = _build_agent_performance(history)
    vote_relationships = _build_vote_relationships(relationship_counters)
    personality_performance = _build_personality_performance(
        history=history,
        replacement_outcomes=replacement_outcomes,
    )
    personality_diversity = _build_personality_diversity(history)
    reciprocal_indicators = _build_reciprocal_indicators(
        reciprocal_counters,
        effective_config,
    )
    voting_bloc_indicators = _build_voting_bloc_indicators(
        relationship_counters=relationship_counters,
        reciprocal_counters=reciprocal_counters,
        config=effective_config,
    )
    entry_adjacent_changes = _build_entry_adjacent_changes(
        history=history,
        relationship_counters=relationship_counters,
    )

    cautions.extend(_build_interpretation_cautions(history))

    return ExperimentAnalysis(
        experiment_id=history.experiment_id,
        experiment_name=history.experiment_name,
        generation_count=len(history.generations),
        agent_performance=agent_performance,
        vote_relationships=vote_relationships,
        personality_performance=personality_performance,
        personality_diversity=personality_diversity,
        replacement_outcomes=replacement_outcomes,
        reciprocal_vote_indicators=reciprocal_indicators,
        possible_voting_bloc_indicators=voting_bloc_indicators,
        entry_adjacent_changes=entry_adjacent_changes,
        cautions=tuple(dict.fromkeys(cautions)),
    )


def _validate_analysis_config(config: AnalysisConfig) -> None:
    if config.minimum_pair_opportunities < 1:
        raise ValueError("Minimum pair opportunities must be at least 1")

    if config.minimum_distinct_generations < 1:
        raise ValueError("Minimum distinct generations must be at least 1")

    if config.minimum_excess_votes < 0:
        raise ValueError("Minimum excess votes cannot be negative")

    if config.minimum_reciprocal_rounds < 1:
        raise ValueError("Minimum reciprocal rounds must be at least 1")


def _validate_history(history: ExperimentHistory) -> list[str]:
    cautions: list[str] = []
    previous_generation_number = 0

    for generation in history.generations:
        if generation.generation_number <= previous_generation_number:
            raise HistoryValidationError(
                "Generation numbers must be strictly increasing"
            )

        previous_generation_number = generation.generation_number
        _validate_generation(generation)

    for previous, current in zip(
        history.generations,
        history.generations[1:],
    ):
        expected_population = {agent.agent_id for agent in previous.final_agents}
        actual_population = {
            participant.agent.agent_id for participant in current.starting_agents
        }

        if expected_population != actual_population:
            cautions.append(
                "Generation "
                f"{current.generation_number} does not begin with the "
                "previous saved final population; lineage-dependent "
                "metrics are limited for this history."
            )

    personalities_by_agent_id: dict[str, set[PersonalityKey]] = {}

    for generation in history.generations:
        for participant in generation.starting_agents:
            personalities_by_agent_id.setdefault(
                participant.agent.agent_id,
                set(),
            ).add(_personality_key(participant.agent.personality))

    for agent_id, personality_keys in personalities_by_agent_id.items():
        if len(personality_keys) > 1:
            cautions.append(
                f"Agent ID {agent_id} has multiple personality snapshots; "
                "its aggregate is not a single stable identity."
            )

    return cautions


def _validate_generation(generation: GenerationSnapshot) -> None:
    participant_ids = [
        participant.agent.agent_id for participant in generation.starting_agents
    ]
    participant_id_set = set(participant_ids)

    if len(participant_ids) < 2:
        raise HistoryValidationError(
            "Every generation requires at least two participants"
        )

    if len(participant_ids) != len(participant_id_set):
        raise HistoryValidationError(
            "Generation participants must have unique agent IDs"
        )

    eliminated_participants = [
        participant
        for participant in generation.starting_agents
        if participant.was_eliminated
    ]

    if len(eliminated_participants) != 1:
        raise HistoryValidationError(
            "Every generation must mark exactly one eliminated agent"
        )

    if eliminated_participants[0].agent.agent_id != (generation.eliminated_agent_id):
        raise HistoryValidationError(
            "Eliminated participant and game metadata disagree"
        )

    scores_by_agent_id = {
        participant.agent.agent_id: participant.total_score
        for participant in generation.starting_agents
    }
    minimum_score = min(scores_by_agent_id.values())

    if scores_by_agent_id[generation.eliminated_agent_id] != minimum_score:
        raise HistoryValidationError(
            "Eliminated agent does not have a lowest total score"
        )

    final_agent_ids = [agent.agent_id for agent in generation.final_agents]
    expected_final_agent_ids = (
        participant_id_set - {generation.eliminated_agent_id}
    ) | {generation.replacement_agent.agent_id}

    if len(final_agent_ids) != len(set(final_agent_ids)):
        raise HistoryValidationError("Final population must have unique agent IDs")

    if set(final_agent_ids) != expected_final_agent_ids:
        raise HistoryValidationError(
            "Final population does not match elimination and replacement"
        )

    if generation.eliminated_agent_id in final_agent_ids:
        raise HistoryValidationError("Eliminated agent remains in the final population")

    if generation.replacement_agent.agent_id not in final_agent_ids:
        raise HistoryValidationError(
            "Replacement agent is absent from the final population"
        )

    round_numbers = [
        round_snapshot.round_number for round_snapshot in generation.rounds
    ]

    if round_numbers != list(range(1, len(round_numbers) + 1)):
        raise HistoryValidationError(
            "Round numbers must start at one and be contiguous"
        )

    score_totals_by_agent_id = {agent_id: 0 for agent_id in participant_id_set}

    for round_snapshot in generation.rounds:
        _validate_round(round_snapshot, participant_id_set)

        for score in round_snapshot.scores:
            score_totals_by_agent_id[score.agent_id] += score.score

    if score_totals_by_agent_id != scores_by_agent_id:
        raise HistoryValidationError(
            "Generation totals do not equal persisted round scores"
        )


def _validate_round(
    round_snapshot: RoundSnapshot,
    participant_id_set: set[str],
) -> None:
    # The snapshot interface is intentionally structural here so validation
    # stays focused on persisted facts instead of ORM implementation details.
    answers = round_snapshot.answers
    votes = round_snapshot.votes
    scores = round_snapshot.scores
    answer_agent_ids = [answer.agent_id for answer in answers]
    answer_agent_id_set = set(answer_agent_ids)
    candidate_to_agent_id = {answer.candidate_id: answer.agent_id for answer in answers}

    if len(answer_agent_ids) != len(answer_agent_id_set):
        raise HistoryValidationError(
            "A round contains more than one answer from an agent"
        )

    if len(candidate_to_agent_id) != len(answers):
        raise HistoryValidationError("A round contains duplicate candidate IDs")

    if not answer_agent_id_set <= participant_id_set:
        raise HistoryValidationError("A round answer belongs to a nonparticipant")

    voters_seen: set[str] = set()

    for vote in votes:
        if vote.voter_agent_id not in answer_agent_id_set:
            raise HistoryValidationError("A vote belongs to an agent without an answer")

        if vote.voter_agent_id in voters_seen:
            raise HistoryValidationError(
                "A round contains more than one vote from an agent"
            )

        voters_seen.add(vote.voter_agent_id)

        selected_agent_id = candidate_to_agent_id.get(vote.selected_candidate_id)

        if selected_agent_id is None:
            raise HistoryValidationError("A vote selects an unknown candidate")

        if selected_agent_id != vote.selected_agent_id:
            raise HistoryValidationError(
                "A vote target does not match its selected candidate"
            )

        if vote.selected_agent_id == vote.voter_agent_id:
            raise HistoryValidationError("A persisted self-vote is invalid")

    score_agent_ids = [score.agent_id for score in scores]

    if set(score_agent_ids) != participant_id_set:
        raise HistoryValidationError(
            "A round must persist one score for every participant"
        )

    if len(score_agent_ids) != len(set(score_agent_ids)):
        raise HistoryValidationError("A round contains duplicate score records")

    if sum(score.score for score in scores) != len(votes):
        raise HistoryValidationError(
            "Round score total does not equal the number of votes"
        )


def _build_agent_performance(
    history: ExperimentHistory,
) -> tuple[AgentPerformance, ...]:
    observations: dict[
        str,
        list[ParticipantObservation],
    ] = {}

    for generation in history.generations:
        winning_score = max(
            participant.total_score for participant in generation.starting_agents
        )

        for participant in generation.starting_agents:
            observations.setdefault(participant.agent.agent_id, []).append(
                (
                    generation,
                    participant,
                    participant.total_score == winning_score,
                )
            )

    performance: list[AgentPerformance] = []

    for agent_id, agent_observations in observations.items():
        latest_participant = agent_observations[-1][1]
        generation_scores = tuple(
            GenerationScore(
                generation_number=generation.generation_number,
                total_score=participant.total_score,
                round_count=len(generation.rounds),
                average_points_per_round=_average(
                    participant.total_score,
                    len(generation.rounds),
                ),
                was_eliminated=participant.was_eliminated,
                won_generation=won_generation,
            )
            for generation, participant, won_generation in agent_observations
        )
        total_points = sum(
            participant.total_score
            for _generation, participant, _won_generation in agent_observations
        )
        scored_round_count = sum(
            len(generation.rounds)
            for generation, _participant, _won_generation in agent_observations
        )
        elimination_generation = next(
            (
                generation.generation_number
                for generation, participant, _won_generation in agent_observations
                if participant.was_eliminated
            ),
            None,
        )
        generation_win_count = sum(
            won_generation
            for _generation, _participant, won_generation in agent_observations
        )
        trend_points = [
            (
                generation.generation_number,
                _average(participant.total_score, len(generation.rounds)),
            )
            for generation, participant, _won_generation in agent_observations
        ]

        performance.append(
            AgentPerformance(
                agent_id=agent_id,
                agent_name=latest_participant.agent.agent_name,
                personality=latest_participant.agent.personality,
                generation_scores=generation_scores,
                total_points=total_points,
                scored_round_count=scored_round_count,
                average_points_per_round=_average(
                    total_points,
                    scored_round_count,
                ),
                survival_count=sum(
                    not participant.was_eliminated
                    for _generation, participant, _won_generation in agent_observations
                ),
                elimination_generation=elimination_generation,
                generation_win_count=generation_win_count,
                generation_win_rate=_average(
                    generation_win_count,
                    len(agent_observations),
                ),
                score_slope_per_generation=_linear_slope(trend_points),
            )
        )

    return tuple(
        sorted(
            performance,
            key=lambda item: (-item.total_points, item.agent_id),
        )
    )


def _build_relationship_counters(
    history: ExperimentHistory,
) -> dict[RelationshipKey, _RelationshipCounter]:
    counters: dict[RelationshipKey, _RelationshipCounter] = {}

    for generation in history.generations:
        for round_snapshot in generation.rounds:
            answer_author_ids = {answer.agent_id for answer in round_snapshot.answers}
            eligible_target_count = len(answer_author_ids) - 1

            for vote in round_snapshot.votes:
                for target_agent_id in sorted(
                    answer_author_ids - {vote.voter_agent_id}
                ):
                    key = (vote.voter_agent_id, target_agent_id)
                    counter = counters.setdefault(
                        key,
                        _RelationshipCounter(),
                    )
                    period = counter.periods.setdefault(
                        generation.generation_number,
                        _PeriodCounter(),
                    )
                    expected_random_vote = 1 / eligible_target_count
                    counter.opportunities += 1
                    counter.expected_random_votes += expected_random_vote
                    period.opportunities += 1
                    period.expected_random_votes += expected_random_vote

                    if vote.selected_agent_id == target_agent_id:
                        counter.votes += 1
                        period.votes += 1

    return counters


def _build_vote_relationships(
    counters: dict[RelationshipKey, _RelationshipCounter],
) -> tuple[VoteRelationship, ...]:
    relationships = [
        VoteRelationship(
            voter_agent_id=voter_agent_id,
            target_agent_id=target_agent_id,
            periods=tuple(
                RelationshipPeriod(
                    generation_number=generation_number,
                    votes=period.votes,
                    eligible_voting_opportunities=(period.opportunities),
                    expected_random_votes=(period.expected_random_votes),
                )
                for generation_number, period in sorted(counter.periods.items())
            ),
            votes=counter.votes,
            eligible_voting_opportunities=counter.opportunities,
            expected_random_votes=counter.expected_random_votes,
            vote_rate=_average(counter.votes, counter.opportunities),
            random_baseline_rate=_average(
                counter.expected_random_votes,
                counter.opportunities,
            ),
            excess_votes=(counter.votes - counter.expected_random_votes),
            excess_rate=(
                _average(counter.votes, counter.opportunities)
                - _average(
                    counter.expected_random_votes,
                    counter.opportunities,
                )
            ),
        )
        for (voter_agent_id, target_agent_id), counter in counters.items()
    ]

    return tuple(
        sorted(
            relationships,
            key=lambda item: (
                item.voter_agent_id,
                item.target_agent_id,
            ),
        )
    )


def _build_replacement_outcomes(
    history: ExperimentHistory,
) -> tuple[ReplacementOutcome, ...]:
    outcomes: list[ReplacementOutcome] = []
    generations = history.generations

    for index, generation in enumerate(generations):
        replacement = generation.replacement_agent

        if index + 1 >= len(generations):
            outcomes.append(
                ReplacementOutcome(
                    created_in_generation=(generation.generation_number),
                    replacement_agent_id=replacement.agent_id,
                    personality=replacement.personality,
                    first_participation_generation=None,
                    first_participation_score=None,
                    survived_first_participation=None,
                    status="pending",
                )
            )
            continue

        next_generation = generations[index + 1]
        participant_by_agent_id = {
            participant.agent.agent_id: participant
            for participant in next_generation.starting_agents
        }
        participant = participant_by_agent_id.get(replacement.agent_id)

        if participant is None:
            outcomes.append(
                ReplacementOutcome(
                    created_in_generation=(generation.generation_number),
                    replacement_agent_id=replacement.agent_id,
                    personality=replacement.personality,
                    first_participation_generation=None,
                    first_participation_score=None,
                    survived_first_participation=None,
                    status="not_present",
                )
            )
            continue

        outcomes.append(
            ReplacementOutcome(
                created_in_generation=generation.generation_number,
                replacement_agent_id=replacement.agent_id,
                personality=replacement.personality,
                first_participation_generation=(next_generation.generation_number),
                first_participation_score=participant.total_score,
                survived_first_participation=(not participant.was_eliminated),
                status="observed",
            )
        )

    return tuple(outcomes)


def _build_personality_performance(
    history: ExperimentHistory,
    replacement_outcomes: tuple[ReplacementOutcome, ...],
) -> tuple[PersonalityPerformance, ...]:
    observations: dict[
        PersonalityKey,
        list[ParticipantObservation],
    ] = {}
    personalities: dict[PersonalityKey, PersonalitySnapshot] = {}

    for generation in history.generations:
        replacement_key = _personality_key(generation.replacement_agent.personality)
        personalities.setdefault(
            replacement_key,
            generation.replacement_agent.personality,
        )
        observations.setdefault(replacement_key, [])
        winning_score = max(
            participant.total_score for participant in generation.starting_agents
        )

        for participant in generation.starting_agents:
            key = _personality_key(participant.agent.personality)
            personalities[key] = participant.agent.personality
            observations.setdefault(key, []).append(
                (
                    generation,
                    participant,
                    participant.total_score == winning_score,
                )
            )

    outcomes_by_personality: dict[
        PersonalityKey,
        list[ReplacementOutcome],
    ] = {}

    for outcome in replacement_outcomes:
        outcomes_by_personality.setdefault(
            _personality_key(outcome.personality),
            [],
        ).append(outcome)

    performance: list[PersonalityPerformance] = []

    for key, personality_observations in observations.items():
        observed_outcomes = [
            outcome
            for outcome in outcomes_by_personality.get(key, [])
            if outcome.status == "observed"
        ]
        total_points = sum(
            participant.total_score
            for _generation, participant, _won_generation in personality_observations
        )
        scored_round_count = sum(
            len(generation.rounds)
            for generation, _participant, _won_generation in personality_observations
        )
        successful_replacements = sum(
            outcome.survived_first_participation is True
            for outcome in observed_outcomes
        )

        performance.append(
            PersonalityPerformance(
                personality=personalities[key],
                agent_ids=tuple(
                    sorted(
                        {
                            participant.agent.agent_id
                            for _generation, participant, _won_generation in personality_observations
                        }
                    )
                ),
                generation_participations=len(personality_observations),
                generation_survivals=sum(
                    not participant.was_eliminated
                    for _generation, participant, _won_generation in personality_observations
                ),
                total_points=total_points,
                scored_round_count=scored_round_count,
                average_points_per_round=_average(
                    total_points,
                    scored_round_count,
                ),
                generation_win_count=sum(
                    won_generation
                    for _generation, _participant, won_generation in personality_observations
                ),
                replacement_observation_count=len(observed_outcomes),
                replacement_success_rate=_average(
                    successful_replacements,
                    len(observed_outcomes),
                ),
            )
        )

    return tuple(
        sorted(
            performance,
            key=lambda item: (
                -item.total_points,
                item.personality.name,
                item.personality.answer_template,
            ),
        )
    )


def _build_personality_diversity(
    history: ExperimentHistory,
) -> PersonalityDiversity:
    generated_personalities = [
        generation.replacement_agent.personality for generation in history.generations
    ]
    generated_personality_count = len(generated_personalities)
    distinct_name_count = len(
        {personality.name.casefold() for personality in generated_personalities}
    )
    distinct_instruction_count = len(
        {personality.answer_template for personality in generated_personalities}
    )

    return PersonalityDiversity(
        generated_personality_count=generated_personality_count,
        distinct_name_count=distinct_name_count,
        distinct_instruction_count=distinct_instruction_count,
        distinct_name_rate=_average(
            distinct_name_count,
            generated_personality_count,
        ),
        distinct_instruction_rate=_average(
            distinct_instruction_count,
            generated_personality_count,
        ),
    )


def _build_reciprocal_counters(
    history: ExperimentHistory,
) -> dict[PairKey, _ReciprocalCounter]:
    counters: dict[PairKey, _ReciprocalCounter] = {}

    for generation in history.generations:
        for round_snapshot in generation.rounds:
            votes_by_voter = {
                vote.voter_agent_id: vote for vote in round_snapshot.votes
            }
            answer_count = len(round_snapshot.answers)

            for first_agent_id, second_agent_id in combinations(
                sorted(votes_by_voter),
                2,
            ):
                key = (first_agent_id, second_agent_id)
                counter = counters.setdefault(key, _ReciprocalCounter())
                counter.eligible_co_voting_rounds += 1
                counter.expected_random_reciprocal_rounds += 1 / (
                    (answer_count - 1) ** 2
                )
                counter.generations.add(generation.generation_number)

                if (
                    votes_by_voter[first_agent_id].selected_agent_id == second_agent_id
                    and votes_by_voter[second_agent_id].selected_agent_id
                    == first_agent_id
                ):
                    counter.reciprocal_rounds += 1

    return counters


def _build_reciprocal_indicators(
    counters: dict[PairKey, _ReciprocalCounter],
    config: AnalysisConfig,
) -> tuple[ReciprocalVoteIndicator, ...]:
    indicators = [
        ReciprocalVoteIndicator(
            first_agent_id=first_agent_id,
            second_agent_id=second_agent_id,
            reciprocal_rounds=counter.reciprocal_rounds,
            eligible_co_voting_rounds=(counter.eligible_co_voting_rounds),
            expected_random_reciprocal_rounds=(
                counter.expected_random_reciprocal_rounds
            ),
            distinct_generations=len(counter.generations),
            meets_history_threshold=(
                counter.reciprocal_rounds >= config.minimum_reciprocal_rounds
                and len(counter.generations) >= config.minimum_distinct_generations
            ),
        )
        for (first_agent_id, second_agent_id), counter in counters.items()
        if counter.reciprocal_rounds
    ]

    return tuple(
        sorted(
            indicators,
            key=lambda item: (
                -item.reciprocal_rounds,
                item.first_agent_id,
                item.second_agent_id,
            ),
        )
    )


def _build_voting_bloc_indicators(
    relationship_counters: dict[RelationshipKey, _RelationshipCounter],
    reciprocal_counters: dict[PairKey, _ReciprocalCounter],
    config: AnalysisConfig,
) -> tuple[PossibleVotingBlocIndicator, ...]:
    qualifying_pairs: list[PairKey] = []

    agent_ids = sorted(
        {
            agent_id
            for relationship in relationship_counters
            for agent_id in relationship
        }
    )

    for first_agent_id, second_agent_id in combinations(agent_ids, 2):
        forward = relationship_counters.get((first_agent_id, second_agent_id))
        reverse = relationship_counters.get((second_agent_id, first_agent_id))
        reciprocal = reciprocal_counters.get((first_agent_id, second_agent_id))

        if forward is None or reverse is None or reciprocal is None:
            continue

        if not _relationship_meets_threshold(forward, config):
            continue

        if not _relationship_meets_threshold(reverse, config):
            continue

        if reciprocal.reciprocal_rounds < config.minimum_reciprocal_rounds:
            continue

        if len(reciprocal.generations) < config.minimum_distinct_generations:
            continue

        qualifying_pairs.append((first_agent_id, second_agent_id))

    components = _connected_components(qualifying_pairs)
    indicators: list[PossibleVotingBlocIndicator] = []

    for component in components:
        if len(component) < 3:
            continue

        supporting_pairs = tuple(
            pair
            for pair in qualifying_pairs
            if pair[0] in component and pair[1] in component
        )
        distinct_generations = len(
            {
                generation_number
                for pair in supporting_pairs
                for generation_number in reciprocal_counters[pair].generations
            }
        )
        indicators.append(
            PossibleVotingBlocIndicator(
                agent_ids=tuple(sorted(component)),
                supporting_agent_pairs=supporting_pairs,
                distinct_generations=distinct_generations,
                caveat=(
                    "A repeated voting pattern is not evidence of "
                    "coordination, collusion, or causation."
                ),
            )
        )

    return tuple(sorted(indicators, key=lambda item: item.agent_ids))


def _relationship_meets_threshold(
    counter: _RelationshipCounter,
    config: AnalysisConfig,
) -> bool:
    return (
        counter.opportunities >= config.minimum_pair_opportunities
        and len(counter.periods) >= config.minimum_distinct_generations
        and (
            counter.votes - counter.expected_random_votes >= config.minimum_excess_votes
        )
    )


def _connected_components(
    edges: list[PairKey],
) -> list[set[str]]:
    neighbors: dict[str, set[str]] = {}

    for first_agent_id, second_agent_id in edges:
        neighbors.setdefault(first_agent_id, set()).add(second_agent_id)
        neighbors.setdefault(second_agent_id, set()).add(first_agent_id)

    components: list[set[str]] = []
    remaining_agent_ids = set(neighbors)

    while remaining_agent_ids:
        pending = [remaining_agent_ids.pop()]
        component: set[str] = set()

        while pending:
            agent_id = pending.pop()

            if agent_id in component:
                continue

            component.add(agent_id)
            remaining_agent_ids.discard(agent_id)
            pending.extend(neighbors[agent_id] - component)

        components.append(component)

    return components


def _build_entry_adjacent_changes(
    history: ExperimentHistory,
    relationship_counters: dict[RelationshipKey, _RelationshipCounter],
) -> tuple[EntryAdjacentRelationshipChange, ...]:
    changes: list[EntryAdjacentRelationshipChange] = []

    for previous, current in zip(
        history.generations,
        history.generations[1:],
    ):
        entrant_agent_id = previous.replacement_agent.agent_id
        current_agent_ids = {
            participant.agent.agent_id for participant in current.starting_agents
        }

        if entrant_agent_id not in current_agent_ids:
            continue

        for (voter_agent_id, target_agent_id), counter in relationship_counters.items():
            if entrant_agent_id in {voter_agent_id, target_agent_id}:
                continue

            previous_period = counter.periods.get(previous.generation_number)
            entry_period = counter.periods.get(current.generation_number)

            if previous_period is None or entry_period is None:
                continue

            previous_vote_rate = _average(
                previous_period.votes,
                previous_period.opportunities,
            )
            entry_vote_rate = _average(
                entry_period.votes,
                entry_period.opportunities,
            )

            if previous_vote_rate is None or entry_vote_rate is None:
                continue

            changes.append(
                EntryAdjacentRelationshipChange(
                    entrant_agent_id=entrant_agent_id,
                    entry_generation=current.generation_number,
                    voter_agent_id=voter_agent_id,
                    target_agent_id=target_agent_id,
                    previous_vote_rate=previous_vote_rate,
                    entry_vote_rate=entry_vote_rate,
                    rate_change=(entry_vote_rate - previous_vote_rate),
                    previous_excess_votes=(
                        previous_period.votes - previous_period.expected_random_votes
                    ),
                    entry_excess_votes=(
                        entry_period.votes - entry_period.expected_random_votes
                    ),
                )
            )

    return tuple(
        sorted(
            changes,
            key=lambda item: (
                item.entry_generation,
                item.voter_agent_id,
                item.target_agent_id,
            ),
        )
    )


def _build_interpretation_cautions(
    history: ExperimentHistory,
) -> list[str]:
    cautions = [
        "All metrics are descriptive summaries of saved generations, "
        "not evidence of causal behavior or model improvement.",
        "Repeated voting is an indicator for further study, not proof of "
        "an alliance, collusion, or coordination.",
        "Compare multiple experiments, shuffled candidate orders, and "
        "random-vote baselines before drawing scientific conclusions.",
    ]

    partial_answer_rounds = sum(
        len(round_snapshot.answers) < len(generation.starting_agents)
        for generation in history.generations
        for round_snapshot in generation.rounds
    )

    if partial_answer_rounds:
        cautions.append(
            f"{partial_answer_rounds} round(s) had partial answer "
            "participation; opportunity baselines account for the "
            "available answers in each affected round."
        )

    return cautions


def _personality_key(
    personality: PersonalitySnapshot,
) -> PersonalityKey:
    return (
        personality.name,
        personality.description,
        personality.answer_template,
    )


def _average(
    numerator: int | float,
    denominator: int,
) -> float | None:
    if denominator == 0:
        return None

    return numerator / denominator


def _linear_slope(
    points: list[tuple[int, float | None]],
) -> float | None:
    usable_points = [
        (float(x_value), y_value) for x_value, y_value in points if y_value is not None
    ]

    if len(usable_points) < 2:
        return None

    x_mean = sum(x_value for x_value, _y_value in usable_points) / len(usable_points)
    y_mean = sum(y_value for _x_value, y_value in usable_points) / len(usable_points)
    denominator = sum((x_value - x_mean) ** 2 for x_value, _y_value in usable_points)

    if denominator == 0:
        return None

    numerator = sum(
        (x_value - x_mean) * (y_value - y_mean) for x_value, y_value in usable_points
    )

    return numerator / denominator
