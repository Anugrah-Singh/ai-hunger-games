from random import Random
from typing import Protocol

from ai_hunger_games.models import (
    Agent,
    Answer,
    Vote,
    VoteOption,
)


class RetryableProviderError(RuntimeError):
    """A temporary provider error that may succeed when retried."""


class AnswerGenerationTimeoutError(RuntimeError):
    def __init__(
        self,
        agent_id: str,
        timeout_seconds: float,
    ) -> None:
        self.agent_id = agent_id
        self.timeout_seconds = timeout_seconds

        super().__init__(
            "Answer generation timed out for "
            f"{agent_id} after {timeout_seconds} seconds"
        )


class InsufficientAnswersError(RuntimeError):
    def __init__(
        self,
        successful_answer_count: int,
        minimum_required: int,
    ) -> None:
        self.successful_answer_count = successful_answer_count
        self.minimum_required = minimum_required

        super().__init__(
            "Not enough answers to continue the round: "
            f"received {successful_answer_count}, "
            f"required {minimum_required}"
        )


class AnswerProvider(Protocol):
    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        ...


class VoteProvider(Protocol):
    async def generate_vote(
        self,
        voter: Agent,
        options: list[VoteOption],
        seed: int,
    ) -> Vote:
        ...


class SimulatedAnswerProvider:
    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        if not question.strip():
            raise ValueError("Question cannot be empty")

        answer_content = (
            agent.personality.answer_template.format(
                question=question
            )
        )

        return Answer(
            agent_id=agent.id,
            content=answer_content,
        )


class SimulatedVoteProvider:
    async def generate_vote(
        self,
        voter: Agent,
        options: list[VoteOption],
        seed: int,
    ) -> Vote:
        if not options:
            raise ValueError(
                f"No voting options available for {voter.id}"
            )

        random_generator = Random(seed)
        selected_option = random_generator.choice(options)

        return Vote(
            voter_id=voter.id,
            candidate_id=selected_option.candidate_id,
        )
    

class VoteGenerationTimeoutError(RuntimeError):
    def __init__(
        self,
        voter_id: str,
        timeout_seconds: float,
    ) -> None:
        self.voter_id = voter_id
        self.timeout_seconds = timeout_seconds

        super().__init__(
            "Vote generation timed out for "
            f"{voter_id} after {timeout_seconds} seconds"
        )