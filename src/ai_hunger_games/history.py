"""Immutable read models shared by persistence and deterministic analysis."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PersonalitySnapshot:
    name: str
    description: str
    answer_template: str


@dataclass(frozen=True)
class AgentSnapshot:
    agent_id: str
    agent_name: str
    personality: PersonalitySnapshot


@dataclass(frozen=True)
class ParticipantSnapshot:
    agent: AgentSnapshot
    total_score: int
    was_eliminated: bool


@dataclass(frozen=True)
class AnswerSnapshot:
    candidate_id: str
    agent_id: str
    content: str
    attempt_count: int = 1


@dataclass(frozen=True)
class AnswerFailureSnapshot:
    agent_id: str
    error_type: str
    message: str
    attempt_count: int
    retry_after_seconds: float | None


@dataclass(frozen=True)
class VoteSnapshot:
    voter_agent_id: str
    selected_candidate_id: str
    selected_agent_id: str


@dataclass(frozen=True)
class RoundScoreSnapshot:
    agent_id: str
    score: int


@dataclass(frozen=True)
class RoundSnapshot:
    round_id: int
    round_number: int
    question: str
    answers: tuple[AnswerSnapshot, ...]
    votes: tuple[VoteSnapshot, ...]
    scores: tuple[RoundScoreSnapshot, ...]
    failures: tuple[AnswerFailureSnapshot, ...] = ()


@dataclass(frozen=True)
class RandomizationSnapshot:
    candidate_order_seed: int | None
    voting_seed: int | None
    elimination_seed: int | None
    replacement_seed: int | None


@dataclass(frozen=True)
class GenerationSnapshot:
    game_id: int
    generation_number: int
    provider_name: str
    created_at: datetime
    seeds: RandomizationSnapshot
    starting_agents: tuple[ParticipantSnapshot, ...]
    final_agents: tuple[AgentSnapshot, ...]
    rounds: tuple[RoundSnapshot, ...]
    eliminated_agent_id: str
    replacement_agent: AgentSnapshot


@dataclass(frozen=True)
class ExperimentHistory:
    experiment_id: int
    experiment_name: str
    generations: tuple[GenerationSnapshot, ...]
