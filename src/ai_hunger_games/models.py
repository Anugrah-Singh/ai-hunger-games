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
    description: str = ""


@dataclass(frozen=True)
class GeneratedPersonality:
    name: str
    description: str
    answer_instructions: str


@dataclass
class Agent:
    id: str
    name: str
    personality: Personality


@dataclass(frozen=True)
class AgentFailure:
    agent_id: str
    error_type: str
    message: str
    attempt_count: int = 1
    retry_after_seconds: float | None = None


@dataclass
class Answer:
    agent_id: str
    content: str
    attempt_count: int = 1


@dataclass
class AnswerBatchResult:
    answers: list[Answer]
    failures: list[AgentFailure]

    @property
    def failed_agent_ids(self) -> list[str]:
        return [failure.agent_id for failure in self.failures]


@dataclass(frozen=True)
class AnswerGenerationPolicy:
    timeout_seconds: float
    minimum_successful_answers: int
    maximum_attempts: int
    initial_retry_delay_seconds: float
    maximum_retry_delay_seconds: float
    maximum_concurrent_requests: int | None = None


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
    failures: list[AgentFailure]


@dataclass(frozen=True)
class GameSeeds:
    candidate_order_seed: int
    voting_seed: int
    elimination_seed: int
    replacement_seed: int


@dataclass
class GameResult:
    round_results: list[RoundResult]
    total_scores_by_agent_id: dict[str, int]
    eliminated_agent_id: str
    replacement_agent: Agent
    final_agents: list[Agent]
    seeds: GameSeeds


@dataclass(frozen=True)
class EvolutionContext:
    eliminated_agent_id: str
    eliminated_personality_name: str
    total_scores_by_agent_id: dict[str, int]
    winning_personality_names: list[str]
    existing_personality_names: list[str]
    replacement_seed: int


@dataclass(frozen=True)
class PersonalityGenerationPolicy:
    timeout_seconds: float
    maximum_attempts: int
    initial_retry_delay_seconds: float
    maximum_retry_delay_seconds: float


@dataclass(frozen=True)
class ExperimentDefinition:
    """Immutable inputs that make a newly created experiment reproducible."""

    initial_agents: tuple[Agent, ...]
    questions_per_generation: tuple[str, ...]
    candidate_order_seed: int
    voting_seed: int
    elimination_seed: int
    replacement_seed: int
    answer_policy: AnswerGenerationPolicy
    vote_policy: VoteGenerationPolicy
    personality_policy: PersonalityGenerationPolicy
    seed_stride: int = 1_000_000
