from dataclasses import dataclass


@dataclass
class Vote:
    voter_id: str
    candidate_id: str


@dataclass(frozen=True)
class VoteOption:
    candidate_id: str
    answer_content: str


@dataclass
class Personality:
    name: str
    answer_template: str


@dataclass
class Agent:
    id: str
    name: str
    personality: Personality


@dataclass
class Answer:
    agent_id: str
    content: str


@dataclass
class AnswerBatchResult:
    answers: list[Answer]
    failed_agent_ids: list[str]


@dataclass(frozen=True)
class AnswerGenerationPolicy:
    timeout_seconds: float
    minimum_successful_answers: int
    maximum_attempts: int
    initial_retry_delay_seconds: float
    maximum_retry_delay_seconds: float


@dataclass(frozen=True)
class VoteGenerationPolicy:
    timeout_seconds: float
    maximum_attempts: int
    initial_retry_delay_seconds: float
    maximum_retry_delay_seconds: float


@dataclass
class Candidate:
    id: str
    answer: Answer


@dataclass
class Round:
    number: int
    question: str


@dataclass
class RoundResult:
    round: Round
    answers: list[Answer]
    failed_agent_ids: list[str]
    candidates: list[Candidate]
    votes: list[Vote]
    scores_by_candidate_id: dict[str, int]
    winning_candidate_ids: list[str]


@dataclass
class GameResult:
    round_results: list[RoundResult]
    total_scores_by_agent_id: dict[str, int]
    eliminated_agent_id: str
    replacement_agent: Agent
    final_agents: list[Agent]