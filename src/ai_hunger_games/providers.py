from random import Random
from typing import Protocol

from ai_hunger_games.models import (
    Agent,
    Answer,
    EvolutionContext,
    GeneratedPersonality,
    Vote,
    VoteOption,
)

SIMULATED_PERSONALITIES = (
    GeneratedPersonality(
        name="Practical Builder",
        description=(
            "A grounded problem solver focused on feasible action and "
            "measurable outcomes."
        ),
        answer_instructions=(
            "Answer the question as a practical builder. Focus on "
            "achievable actions, tradeoffs, and clear implementation. "
            "The question is: {question}"
        ),
    ),
    GeneratedPersonality(
        name="Systems Cartographer",
        description=(
            "A systems thinker who maps feedback loops, constraints, "
            "and second-order effects."
        ),
        answer_instructions=(
            "Map the system behind {question}. Identify actors, feedback "
            "loops, constraints, and a practical intervention."
        ),
    ),
    GeneratedPersonality(
        name="Adversarial Tester",
        description=(
            "A constructive skeptic who searches for failure modes before "
            "recommending action."
        ),
        answer_instructions=(
            "Analyze {question} by naming the strongest assumptions, "
            "likely failure modes, and safeguards for a recommendation."
        ),
    ),
    GeneratedPersonality(
        name="Decision Theorist",
        description=(
            "A disciplined reasoner who compares decisions under explicit "
            "uncertainty and values."
        ),
        answer_instructions=(
            "For {question}, define the decision, relevant uncertainty, "
            "tradeoffs, and a justified choice."
        ),
    ),
    GeneratedPersonality(
        name="Field Researcher",
        description=(
            "An empirical investigator who distinguishes observations "
            "from assumptions and proposes tests."
        ),
        answer_instructions=(
            "Address {question} with observable evidence, key unknowns, "
            "and the next test or measurement to run."
        ),
    ),
    GeneratedPersonality(
        name="Constraint Designer",
        description=(
            "A practical designer who turns goals into clear rules and "
            "workable operating constraints."
        ),
        answer_instructions=(
            "For {question}, identify the goal, hard constraints, and a "
            "simple design that can be implemented and checked."
        ),
    ),
    GeneratedPersonality(
        name="Cooperative Negotiator",
        description=(
            "A consensus builder who looks for durable agreements across "
            "conflicting interests."
        ),
        answer_instructions=(
            "Respond to {question} by identifying affected interests, "
            "shared ground, and a durable agreement."
        ),
    ),
    GeneratedPersonality(
        name="Scenario Planner",
        description=(
            "A foresight practitioner who prepares robust actions across "
            "plausible futures."
        ),
        answer_instructions=(
            "Explore {question} through plausible scenarios, early "
            "warning signals, and actions that remain robust."
        ),
    ),
)


class PersonalityProvider(Protocol):
    async def generate_personality(
        self,
        context: EvolutionContext,
    ) -> GeneratedPersonality: ...


class SimulatedPersonalityProvider:
    async def generate_personality(
        self,
        context: EvolutionContext,
    ) -> GeneratedPersonality:
        existing_personality_names = {
            name.casefold() for name in context.existing_personality_names
        }
        available_personalities = tuple(
            personality
            for personality in SIMULATED_PERSONALITIES
            if personality.name.casefold() not in existing_personality_names
        )

        if not available_personalities:
            return GeneratedPersonality(
                name=(f"Adaptive Builder {context.replacement_seed}"),
                description=(
                    "A practical problem solver generated after the "
                    "standard simulated personality catalog was exhausted."
                ),
                answer_instructions=(
                    "Address {question} with a concrete plan, its main "
                    "tradeoffs, and a way to evaluate the result."
                ),
            )

        random_generator = Random(context.replacement_seed)

        return random_generator.choice(available_personalities)


class RetryableProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        retry_after_seconds: float | None = None,
    ) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message)


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
        failure_details: str = "",
    ) -> None:
        self.successful_answer_count = successful_answer_count
        self.minimum_required = minimum_required
        self.failure_details = failure_details

        message = (
            "Not enough answers to continue the round: "
            f"received {successful_answer_count}, "
            f"required {minimum_required}"
        )

        if failure_details:
            message = f"{message}\nProvider failures:\n{failure_details}"

        super().__init__(message)


class AnswerProvider(Protocol):
    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer: ...


class VoteProvider(Protocol):
    async def generate_vote(
        self,
        voter: Agent,
        options: list[VoteOption],
        seed: int,
    ) -> Vote: ...


class SimulatedAnswerProvider:
    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        if not question.strip():
            raise ValueError("Question cannot be empty")

        answer_content = agent.personality.answer_template.replace(
            "{question}",
            question,
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
            raise ValueError(f"No voting options available for {voter.id}")

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
            f"Vote generation timed out for {voter_id} after {timeout_seconds} seconds"
        )


class PersonalityGenerationTimeoutError(RuntimeError):
    def __init__(
        self,
        timeout_seconds: float,
    ) -> None:
        self.timeout_seconds = timeout_seconds

        super().__init__(
            f"Personality generation timed out after {timeout_seconds} seconds"
        )
