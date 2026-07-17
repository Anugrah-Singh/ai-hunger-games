"""Pydantic contracts for the public HTTP boundary."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Experiment name cannot be empty")

        return normalized_value


class RunGenerationsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generation_count: int = Field(default=1, ge=1, le=1)


class ExperimentResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    provider_name: str | None = None


class PersonalityResponse(BaseModel):
    name: str
    description: str
    answer_template: str


class AgentResponse(BaseModel):
    agent_id: str
    agent_name: str
    personality: PersonalityResponse


class ParticipantResponse(AgentResponse):
    total_score: int
    was_eliminated: bool


class AnswerResponse(BaseModel):
    candidate_id: str
    content: str
    attempt_count: int


class VoteResponse(BaseModel):
    voter_agent_id: str
    selected_candidate_id: str


class AnswerFailureResponse(BaseModel):
    agent_id: str
    error_type: str
    message: str
    attempt_count: int
    retry_after_seconds: float | None


class RoundScoreResponse(BaseModel):
    candidate_id: str
    score: int


class RoundResponse(BaseModel):
    round_id: int
    round_number: int
    question: str
    answers: list[AnswerResponse]
    votes: list[VoteResponse]
    scores: list[RoundScoreResponse]
    failures: list[AnswerFailureResponse]


class GenerationSummaryResponse(BaseModel):
    game_id: int
    generation_number: int
    provider_name: str
    created_at: datetime
    round_count: int
    seeds: dict[str, int | None]
    eliminated_agent_id: str
    replacement_agent: AgentResponse


class GenerationDetailResponse(GenerationSummaryResponse):
    starting_agents: list[ParticipantResponse]
    final_agents: list[AgentResponse]
    rounds: list[RoundResponse]


class ExperimentDetailResponse(ExperimentResponse):
    generation_count: int
    current_population: list[AgentResponse]
    can_run: bool = True
    run_block_reason: str | None = None


class GenerationScoreResponse(BaseModel):
    generation_number: int
    total_score: int
    round_count: int
    average_points_per_round: float | None
    was_eliminated: bool
    won_generation: bool


class AgentPerformanceResponse(BaseModel):
    agent_id: str
    agent_name: str
    personality: PersonalityResponse
    generation_scores: list[GenerationScoreResponse]
    total_points: int
    scored_round_count: int
    average_points_per_round: float | None
    survival_count: int
    elimination_generation: int | None
    generation_win_count: int
    generation_win_rate: float | None
    score_slope_per_generation: float | None


class RelationshipPeriodResponse(BaseModel):
    generation_number: int
    votes: int
    eligible_voting_opportunities: int
    expected_random_votes: float


class VoteRelationshipResponse(BaseModel):
    voter_agent_id: str
    target_agent_id: str
    periods: list[RelationshipPeriodResponse]
    votes: int
    eligible_voting_opportunities: int
    expected_random_votes: float
    vote_rate: float | None
    random_baseline_rate: float | None
    excess_votes: float
    excess_rate: float | None


class PersonalityPerformanceResponse(BaseModel):
    personality: PersonalityResponse
    agent_ids: list[str]
    generation_participations: int
    generation_survivals: int
    total_points: int
    scored_round_count: int
    average_points_per_round: float | None
    generation_win_count: int
    replacement_observation_count: int
    replacement_success_rate: float | None


class PersonalityDiversityResponse(BaseModel):
    generated_personality_count: int
    distinct_name_count: int
    distinct_instruction_count: int
    distinct_name_rate: float | None
    distinct_instruction_rate: float | None


class ReplacementOutcomeResponse(BaseModel):
    created_in_generation: int
    replacement_agent_id: str
    personality: PersonalityResponse
    first_participation_generation: int | None
    first_participation_score: int | None
    survived_first_participation: bool | None
    status: str


class ReciprocalVoteIndicatorResponse(BaseModel):
    first_agent_id: str
    second_agent_id: str
    reciprocal_rounds: int
    eligible_co_voting_rounds: int
    expected_random_reciprocal_rounds: float
    distinct_generations: int
    meets_history_threshold: bool


class PossibleVotingBlocIndicatorResponse(BaseModel):
    agent_ids: list[str]
    supporting_agent_pairs: list[list[str]]
    distinct_generations: int
    caveat: str


class EntryAdjacentRelationshipChangeResponse(BaseModel):
    entrant_agent_id: str
    entry_generation: int
    voter_agent_id: str
    target_agent_id: str
    previous_vote_rate: float
    entry_vote_rate: float
    rate_change: float
    previous_excess_votes: float
    entry_excess_votes: float


class AnalysisResponse(BaseModel):
    experiment_id: int
    experiment_name: str
    generation_count: int
    agent_performance: list[AgentPerformanceResponse]
    vote_relationships: list[VoteRelationshipResponse]
    personality_performance: list[PersonalityPerformanceResponse]
    personality_diversity: PersonalityDiversityResponse
    replacement_outcomes: list[ReplacementOutcomeResponse]
    reciprocal_vote_indicators: list[ReciprocalVoteIndicatorResponse]
    possible_voting_bloc_indicators: list[PossibleVotingBlocIndicatorResponse]
    entry_adjacent_changes: list[EntryAdjacentRelationshipChangeResponse]
    cautions: list[str]
