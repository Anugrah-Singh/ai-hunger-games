import asyncio
from dataclasses import replace
from random import Random

from ai_hunger_games.models import (
    Agent,
    AgentFailure,
    Answer,
    AnswerBatchResult,
    AnswerGenerationPolicy,
    Candidate,
    EvolutionContext,
    GameResult,
    GameSeeds,
    GeneratedPersonality,
    Personality,
    PersonalityGenerationPolicy,
    Round,
    RoundResult,
    Vote,
    VoteGenerationPolicy,
    VoteOption,
)
from ai_hunger_games.providers import (
    AnswerGenerationTimeoutError,
    AnswerProvider,
    InsufficientAnswersError,
    PersonalityGenerationTimeoutError,
    PersonalityProvider,
    RetryableProviderError,
    SimulatedPersonalityProvider,
    SimulatedVoteProvider,
    VoteGenerationTimeoutError,
    VoteProvider,
)

ROUND_VOTING_SEED_STRIDE = 10_000


class AnswerGenerationExhaustedError(RuntimeError):
    """Retains the final retryable cause and its completed attempt count."""

    def __init__(
        self,
        agent_id: str,
        attempt_count: int,
        cause: Exception,
    ) -> None:
        self.agent_id = agent_id
        self.attempt_count = attempt_count
        self.cause = cause
        super().__init__(str(cause))


def validate_agents(agents: list[Agent]) -> None:
    if not agents:
        raise ValueError("At least one agent is required")

    agent_ids = [agent.id for agent in agents]

    for agent in agents:
        if not agent.id.strip():
            raise ValueError("Agent IDs cannot be empty")

        if not agent.name.strip():
            raise ValueError("Agent names cannot be empty")

        if not agent.personality.name.strip():
            raise ValueError("Personality names cannot be empty")

        if not agent.personality.answer_template.strip():
            raise ValueError("Answer instructions cannot be empty")

        if "{question}" not in agent.personality.answer_template:
            raise ValueError("Answer instructions must contain {question}")

    if len(agent_ids) != len(set(agent_ids)):
        raise ValueError("Agent IDs must be unique")


def validate_answer_policy(
    policy: AnswerGenerationPolicy,
) -> None:
    if policy.timeout_seconds <= 0:
        raise ValueError("Answer timeout must be greater than zero")

    if policy.minimum_successful_answers < 2:
        raise ValueError("At least two successful answers are required")

    if policy.maximum_attempts < 1:
        raise ValueError("Maximum attempts must be at least 1")

    if policy.initial_retry_delay_seconds < 0:
        raise ValueError("Initial retry delay cannot be negative")

    if policy.maximum_retry_delay_seconds < 0:
        raise ValueError("Maximum retry delay cannot be negative")

    if policy.maximum_retry_delay_seconds < policy.initial_retry_delay_seconds:
        raise ValueError(
            "Maximum retry delay cannot be less than the initial retry delay"
        )

    if (
        policy.maximum_concurrent_requests is not None
        and policy.maximum_concurrent_requests < 1
    ):
        raise ValueError("Maximum concurrent answer requests must be at least 1")


def validate_vote_policy(
    policy: VoteGenerationPolicy,
) -> None:
    if policy.timeout_seconds <= 0:
        raise ValueError("Vote timeout must be greater than zero")

    if policy.maximum_attempts < 1:
        raise ValueError("Maximum vote attempts must be at least 1")

    if policy.initial_retry_delay_seconds < 0:
        raise ValueError("Initial vote retry delay cannot be negative")

    if policy.maximum_retry_delay_seconds < 0:
        raise ValueError("Maximum vote retry delay cannot be negative")

    if policy.maximum_retry_delay_seconds < policy.initial_retry_delay_seconds:
        raise ValueError(
            "Maximum vote retry delay cannot be less than the initial vote retry delay"
        )


def validate_answers(
    agents: list[Agent],
    answers: list[Answer],
) -> None:
    agent_ids = {agent.id for agent in agents}

    answering_agent_ids: set[str] = set()

    for answer in answers:
        if answer.agent_id not in agent_ids:
            raise ValueError(f"Unknown answering agent: {answer.agent_id}")

        if not answer.content.strip():
            raise ValueError(f"Answer cannot be empty: {answer.agent_id}")

        if answer.agent_id in answering_agent_ids:
            raise ValueError(f"Agent cannot answer more than once: {answer.agent_id}")

        answering_agent_ids.add(answer.agent_id)


async def generate_answer_once(
    agent: Agent,
    question: str,
    provider: AnswerProvider,
    timeout_seconds: float,
) -> Answer:
    try:
        return await asyncio.wait_for(
            provider.generate_answer(
                agent=agent,
                question=question,
            ),
            timeout=timeout_seconds,
        )
    except TimeoutError as error:
        raise AnswerGenerationTimeoutError(
            agent_id=agent.id,
            timeout_seconds=timeout_seconds,
        ) from error


async def generate_answer_with_retry(
    agent: Agent,
    question: str,
    provider: AnswerProvider,
    policy: AnswerGenerationPolicy,
) -> Answer:
    for attempt_number in range(
        1,
        policy.maximum_attempts + 1,
    ):
        try:
            answer = await generate_answer_once(
                agent=agent,
                question=question,
                provider=provider,
                timeout_seconds=policy.timeout_seconds,
            )
            return replace(answer, attempt_count=attempt_number)
        except (
            AnswerGenerationTimeoutError,
            RetryableProviderError,
        ) as error:
            is_final_attempt = attempt_number == policy.maximum_attempts

            if is_final_attempt:
                raise AnswerGenerationExhaustedError(
                    agent_id=agent.id,
                    attempt_count=attempt_number,
                    cause=error,
                ) from error

            backoff_delay_seconds = min(
                policy.initial_retry_delay_seconds * (2 ** (attempt_number - 1)),
                policy.maximum_retry_delay_seconds,
            )

            provider_retry_delay_seconds = 0.0

            if isinstance(error, RetryableProviderError):
                provider_retry_delay_seconds = error.retry_after_seconds or 0.0

            retry_delay_seconds = max(
                backoff_delay_seconds,
                provider_retry_delay_seconds,
            )

            await asyncio.sleep(retry_delay_seconds)

    raise RuntimeError("Answer retry loop ended unexpectedly")


async def generate_answers(
    agents: list[Agent],
    question: str,
    provider: AnswerProvider,
    policy: AnswerGenerationPolicy,
) -> AnswerBatchResult:
    if not question.strip():
        raise ValueError("Question cannot be empty")

    validate_answer_policy(policy)

    semaphore = (
        asyncio.Semaphore(policy.maximum_concurrent_requests)
        if policy.maximum_concurrent_requests is not None
        else None
    )

    async def generate_for_agent(agent: Agent) -> Answer:
        if semaphore is None:
            return await generate_answer_with_retry(
                agent=agent,
                question=question,
                provider=provider,
                policy=policy,
            )

        async with semaphore:
            return await generate_answer_with_retry(
                agent=agent,
                question=question,
                provider=provider,
                policy=policy,
            )

    answer_tasks = [generate_for_agent(agent) for agent in agents]

    results = await asyncio.gather(
        *answer_tasks,
        return_exceptions=True,
    )

    successful_answers: list[Answer] = []
    failures: list[AgentFailure] = []

    for agent, result in zip(
        agents,
        results,
        strict=True,
    ):
        if isinstance(result, Exception):
            failures.append(_create_agent_failure(agent, result))
            continue

        if isinstance(result, BaseException):
            raise result

        successful_answers.append(result)

    return AnswerBatchResult(
        answers=successful_answers,
        failures=failures,
    )


def _create_agent_failure(
    agent: Agent,
    error: Exception,
) -> AgentFailure:
    failure_cause = error
    attempt_count = 1

    if isinstance(error, AnswerGenerationExhaustedError):
        failure_cause = error.cause
        attempt_count = error.attempt_count

    retry_after_seconds = (
        failure_cause.retry_after_seconds
        if isinstance(failure_cause, RetryableProviderError)
        else None
    )

    return AgentFailure(
        agent_id=agent.id,
        error_type=type(failure_cause).__name__,
        message=str(failure_cause),
        attempt_count=attempt_count,
        retry_after_seconds=retry_after_seconds,
    )


def create_candidates(
    answers: list[Answer],
    seed: int,
) -> list[Candidate]:
    shuffled_answers = answers.copy()

    random_generator = Random(seed)
    random_generator.shuffle(shuffled_answers)

    candidates: list[Candidate] = []

    for position, answer in enumerate(
        shuffled_answers,
        start=1,
    ):
        candidates.append(
            Candidate(
                id=f"candidate_{position}",
                answer=answer,
            )
        )

    return candidates


def create_vote_options(
    voter: Agent,
    candidates: list[Candidate],
) -> list[VoteOption]:
    options: list[VoteOption] = []

    for candidate in candidates:
        is_voters_own_answer = candidate.answer.agent_id == voter.id

        if is_voters_own_answer:
            continue

        options.append(
            VoteOption(
                candidate_id=candidate.id,
                answer_content=candidate.answer.content,
            )
        )

    return options


async def generate_vote_once(
    voter: Agent,
    options: list[VoteOption],
    provider: VoteProvider,
    seed: int,
    timeout_seconds: float,
) -> Vote:
    try:
        return await asyncio.wait_for(
            provider.generate_vote(
                voter=voter,
                options=options,
                seed=seed,
            ),
            timeout=timeout_seconds,
        )
    except TimeoutError as error:
        raise VoteGenerationTimeoutError(
            voter_id=voter.id,
            timeout_seconds=timeout_seconds,
        ) from error


async def generate_vote_with_retry(
    voter: Agent,
    options: list[VoteOption],
    provider: VoteProvider,
    seed: int,
    policy: VoteGenerationPolicy,
) -> Vote:
    for attempt_number in range(
        1,
        policy.maximum_attempts + 1,
    ):
        try:
            return await generate_vote_once(
                voter=voter,
                options=options,
                provider=provider,
                seed=seed,
                timeout_seconds=policy.timeout_seconds,
            )
        except (
            RetryableProviderError,
            VoteGenerationTimeoutError,
        ) as error:
            is_final_attempt = attempt_number == policy.maximum_attempts

            if is_final_attempt:
                raise

            backoff_delay_seconds = min(
                policy.initial_retry_delay_seconds * (2 ** (attempt_number - 1)),
                policy.maximum_retry_delay_seconds,
            )

            provider_retry_delay = 0.0

            if isinstance(error, RetryableProviderError):
                provider_retry_delay = error.retry_after_seconds or 0.0

            retry_delay_seconds = max(
                backoff_delay_seconds,
                provider_retry_delay,
            )

            await asyncio.sleep(retry_delay_seconds)

    raise RuntimeError("Vote retry loop ended unexpectedly")


async def generate_votes(
    agents: list[Agent],
    candidates: list[Candidate],
    provider: VoteProvider,
    seed: int,
    policy: VoteGenerationPolicy,
) -> list[Vote]:
    if len(agents) < 2:
        raise ValueError("At least two agents are required for voting")

    validate_vote_policy(policy)

    votes: list[Vote] = []

    for voter_position, voter in enumerate(
        agents,
        start=1,
    ):
        options = create_vote_options(
            voter=voter,
            candidates=candidates,
        )

        if not options:
            raise ValueError(f"No voting options available for {voter.id}")

        voter_seed = seed + voter_position

        vote = await generate_vote_with_retry(
            voter=voter,
            options=options,
            provider=provider,
            seed=voter_seed,
            policy=policy,
        )

        votes.append(vote)

    return votes


def count_votes(
    agents: list[Agent],
    candidates: list[Candidate],
    votes: list[Vote],
) -> dict[str, int]:
    validate_agents(agents)

    agent_ids = {agent.id for agent in agents}

    scores_by_candidate_id: dict[str, int] = {
        candidate.id: 0 for candidate in candidates
    }

    candidates_by_id = {candidate.id: candidate for candidate in candidates}

    candidate_id_by_author_id = {
        candidate.answer.agent_id: candidate.id for candidate in candidates
    }

    voters_seen: set[str] = set()

    for vote in votes:
        if vote.voter_id not in agent_ids:
            raise ValueError(f"Unknown voter: {vote.voter_id}")

        if vote.candidate_id not in candidates_by_id:
            raise ValueError(f"Unknown candidate: {vote.candidate_id}")

        voter_candidate_id = candidate_id_by_author_id[vote.voter_id]

        if vote.candidate_id == voter_candidate_id:
            raise ValueError(f"Agent cannot vote for its own answer: {vote.voter_id}")

        if vote.voter_id in voters_seen:
            raise ValueError(f"Agent cannot vote more than once: {vote.voter_id}")

        voters_seen.add(vote.voter_id)
        scores_by_candidate_id[vote.candidate_id] += 1

    return scores_by_candidate_id


def find_winners(
    scores_by_id: dict[str, int],
) -> list[str]:
    if not scores_by_id:
        raise ValueError("Cannot find a winner without scores")

    highest_score = max(scores_by_id.values())

    return [
        item_id for item_id, score in scores_by_id.items() if score == highest_score
    ]


def find_lowest_scoring_agents(
    scores_by_agent_id: dict[str, int],
) -> list[str]:
    if not scores_by_agent_id:
        raise ValueError("Cannot find elimination candidates without scores")

    lowest_score = min(scores_by_agent_id.values())

    return [
        agent_id
        for agent_id, score in scores_by_agent_id.items()
        if score == lowest_score
    ]


def select_eliminated_agent(
    scores_by_agent_id: dict[str, int],
    seed: int,
) -> str:
    lowest_scoring_agent_ids = find_lowest_scoring_agents(scores_by_agent_id)

    if len(lowest_scoring_agent_ids) == 1:
        return lowest_scoring_agent_ids[0]

    random_generator = Random(seed)

    return random_generator.choice(lowest_scoring_agent_ids)


def validate_personality_policy(
    policy: PersonalityGenerationPolicy,
) -> None:
    if policy.timeout_seconds <= 0:
        raise ValueError("Personality timeout must be greater than zero")

    if policy.maximum_attempts < 1:
        raise ValueError("Maximum personality attempts must be at least 1")

    if policy.initial_retry_delay_seconds < 0:
        raise ValueError("Initial personality retry delay cannot be negative")

    if policy.maximum_retry_delay_seconds < 0:
        raise ValueError("Maximum personality retry delay cannot be negative")

    if policy.maximum_retry_delay_seconds < policy.initial_retry_delay_seconds:
        raise ValueError(
            "Maximum personality retry delay cannot be less "
            "than the initial retry delay"
        )


async def generate_personality_once(
    context: EvolutionContext,
    provider: PersonalityProvider,
    timeout_seconds: float,
) -> GeneratedPersonality:
    try:
        return await asyncio.wait_for(
            provider.generate_personality(context),
            timeout=timeout_seconds,
        )
    except TimeoutError as error:
        raise PersonalityGenerationTimeoutError(
            timeout_seconds=timeout_seconds,
        ) from error


async def generate_personality_with_retry(
    context: EvolutionContext,
    provider: PersonalityProvider,
    policy: PersonalityGenerationPolicy,
) -> GeneratedPersonality:
    validate_personality_policy(policy)

    for attempt_number in range(
        1,
        policy.maximum_attempts + 1,
    ):
        try:
            return await generate_personality_once(
                context=context,
                provider=provider,
                timeout_seconds=policy.timeout_seconds,
            )
        except (
            RetryableProviderError,
            PersonalityGenerationTimeoutError,
        ) as error:
            is_final_attempt = attempt_number == policy.maximum_attempts

            if is_final_attempt:
                raise

            backoff_delay_seconds = min(
                policy.initial_retry_delay_seconds * (2 ** (attempt_number - 1)),
                policy.maximum_retry_delay_seconds,
            )

            provider_retry_delay_seconds = 0.0

            if isinstance(error, RetryableProviderError):
                provider_retry_delay_seconds = error.retry_after_seconds or 0.0

            retry_delay_seconds = max(
                backoff_delay_seconds,
                provider_retry_delay_seconds,
            )

            await asyncio.sleep(retry_delay_seconds)

    raise RuntimeError("Personality retry loop ended unexpectedly")


async def generate_replacement_agent(
    agent_id: str,
    context: EvolutionContext,
    provider: PersonalityProvider,
    policy: PersonalityGenerationPolicy,
) -> Agent:
    generated_personality = await generate_personality_with_retry(
        context=context,
        provider=provider,
        policy=policy,
    )

    existing_personality_names = {
        name.casefold() for name in context.existing_personality_names
    }

    if generated_personality.name.casefold() in (existing_personality_names):
        raise ValueError(
            "Generated replacement personality name already exists: "
            f"{generated_personality.name}"
        )

    personality = Personality(
        name=generated_personality.name,
        description=generated_personality.description,
        answer_template=(generated_personality.answer_instructions),
    )

    return Agent(
        id=agent_id,
        name=generated_personality.name,
        personality=personality,
    )


def create_evolution_context(
    agents: list[Agent],
    total_scores_by_agent_id: dict[str, int],
    eliminated_agent_id: str,
    replacement_seed: int,
) -> EvolutionContext:
    agents_by_id = {agent.id: agent for agent in agents}

    eliminated_agent = agents_by_id[eliminated_agent_id]

    highest_score = max(total_scores_by_agent_id.values())

    winning_personality_names = [
        agents_by_id[agent_id].personality.name
        for agent_id, score in total_scores_by_agent_id.items()
        if score == highest_score
    ]

    return EvolutionContext(
        eliminated_agent_id=eliminated_agent_id,
        eliminated_personality_name=(eliminated_agent.personality.name),
        total_scores_by_agent_id=dict(total_scores_by_agent_id),
        winning_personality_names=(winning_personality_names),
        existing_personality_names=[agent.personality.name for agent in agents],
        replacement_seed=replacement_seed,
    )


def replace_agent(
    agents: list[Agent],
    eliminated_agent_id: str,
    replacement_agent: Agent,
) -> list[Agent]:
    existing_agent_ids = {agent.id for agent in agents}

    if eliminated_agent_id not in existing_agent_ids:
        raise ValueError(f"Cannot replace unknown agent: {eliminated_agent_id}")

    if replacement_agent.id in existing_agent_ids:
        raise ValueError(f"Replacement agent ID already exists: {replacement_agent.id}")

    remaining_agents = [agent for agent in agents if agent.id != eliminated_agent_id]

    return [
        *remaining_agents,
        replacement_agent,
    ]


def convert_candidate_scores_to_agent_scores(
    candidates: list[Candidate],
    scores_by_candidate_id: dict[str, int],
) -> dict[str, int]:
    scores_by_agent_id: dict[str, int] = {}

    for candidate in candidates:
        agent_id = candidate.answer.agent_id
        candidate_score = scores_by_candidate_id[candidate.id]

        scores_by_agent_id[agent_id] = candidate_score

    return scores_by_agent_id


def add_round_scores(
    total_scores_by_agent_id: dict[str, int],
    round_scores_by_agent_id: dict[str, int],
) -> None:
    for agent_id, round_score in round_scores_by_agent_id.items():
        total_scores_by_agent_id[agent_id] += round_score


async def run_round(
    round_config: Round,
    agents: list[Agent],
    candidate_order_seed: int,
    voting_seed: int,
    answer_provider: AnswerProvider,
    answer_policy: AnswerGenerationPolicy,
    vote_provider: VoteProvider | None = None,
    vote_policy: VoteGenerationPolicy | None = None,
) -> RoundResult:
    validate_agents(agents)
    validate_answer_policy(answer_policy)

    answer_batch = await generate_answers(
        agents=agents,
        question=round_config.question,
        provider=answer_provider,
        policy=answer_policy,
    )

    if len(answer_batch.answers) < answer_policy.minimum_successful_answers:
        failure_details = "\n".join(
            (f"- {failure.agent_id}: {failure.error_type}: {failure.message}")
            for failure in answer_batch.failures
        )

        raise InsufficientAnswersError(
            successful_answer_count=len(answer_batch.answers),
            minimum_required=(answer_policy.minimum_successful_answers),
            failure_details=failure_details,
        )

    validate_answers(
        agents,
        answer_batch.answers,
    )

    successful_agent_ids = {answer.agent_id for answer in answer_batch.answers}

    participating_agents = [
        agent for agent in agents if agent.id in successful_agent_ids
    ]

    candidates = create_candidates(
        answer_batch.answers,
        seed=candidate_order_seed,
    )

    effective_vote_provider = vote_provider or SimulatedVoteProvider()

    effective_vote_policy = vote_policy or VoteGenerationPolicy(
        timeout_seconds=10.0,
        maximum_attempts=3,
        initial_retry_delay_seconds=2.0,
        maximum_retry_delay_seconds=10.0,
    )

    votes = await generate_votes(
        agents=participating_agents,
        candidates=candidates,
        provider=effective_vote_provider,
        seed=voting_seed,
        policy=effective_vote_policy,
    )

    scores_by_candidate_id = count_votes(
        participating_agents,
        candidates,
        votes,
    )

    winning_candidate_ids = find_winners(scores_by_candidate_id)

    return RoundResult(
        round=round_config,
        answers=answer_batch.answers,
        failed_agent_ids=answer_batch.failed_agent_ids,
        candidates=candidates,
        votes=votes,
        scores_by_candidate_id=scores_by_candidate_id,
        winning_candidate_ids=winning_candidate_ids,
        failures=answer_batch.failures,
    )


async def run_game(
    questions: list[str],
    agents: list[Agent],
    candidate_order_seed: int,
    voting_seed: int,
    elimination_seed: int,
    replacement_seed: int,
    replacement_agent_id: str,
    answer_provider: AnswerProvider,
    answer_policy: AnswerGenerationPolicy,
    vote_provider: VoteProvider | None = None,
    vote_policy: VoteGenerationPolicy | None = None,
    personality_provider: PersonalityProvider | None = None,
    personality_policy: PersonalityGenerationPolicy | None = None,
) -> GameResult:
    if not questions:
        raise ValueError("At least one question is required")

    validate_agents(agents)

    if not replacement_agent_id.strip():
        raise ValueError("Replacement agent ID cannot be empty")

    if replacement_agent_id in {agent.id for agent in agents}:
        raise ValueError(f"Replacement agent ID already exists: {replacement_agent_id}")

    validate_answer_policy(answer_policy)

    if answer_policy.minimum_successful_answers > len(agents):
        raise ValueError("Minimum successful answers cannot exceed the population size")

    if vote_policy is not None:
        validate_vote_policy(vote_policy)

    total_scores_by_agent_id = {agent.id: 0 for agent in agents}

    round_results: list[RoundResult] = []

    for round_number, question in enumerate(
        questions,
        start=1,
    ):
        round_result = await run_round(
            round_config=Round(
                number=round_number,
                question=question,
            ),
            agents=agents,
            candidate_order_seed=(candidate_order_seed + round_number),
            voting_seed=(voting_seed + round_number * ROUND_VOTING_SEED_STRIDE),
            answer_provider=answer_provider,
            answer_policy=answer_policy,
            vote_provider=vote_provider,
            vote_policy=vote_policy,
        )

        round_scores_by_agent_id = convert_candidate_scores_to_agent_scores(
            round_result.candidates,
            round_result.scores_by_candidate_id,
        )

        add_round_scores(
            total_scores_by_agent_id,
            round_scores_by_agent_id,
        )

        round_results.append(round_result)

    eliminated_agent_id = select_eliminated_agent(
        total_scores_by_agent_id,
        seed=elimination_seed,
    )

    evolution_context = create_evolution_context(
        agents=agents,
        total_scores_by_agent_id=total_scores_by_agent_id,
        eliminated_agent_id=eliminated_agent_id,
        replacement_seed=replacement_seed,
    )

    effective_personality_provider = (
        personality_provider or SimulatedPersonalityProvider()
    )

    effective_personality_policy = personality_policy or PersonalityGenerationPolicy(
        timeout_seconds=30.0,
        maximum_attempts=4,
        initial_retry_delay_seconds=3.0,
        maximum_retry_delay_seconds=20.0,
    )

    replacement_agent = await generate_replacement_agent(
        agent_id=replacement_agent_id,
        context=evolution_context,
        provider=effective_personality_provider,
        policy=effective_personality_policy,
    )

    final_agents = replace_agent(
        agents,
        eliminated_agent_id=eliminated_agent_id,
        replacement_agent=replacement_agent,
    )

    return GameResult(
        round_results=round_results,
        total_scores_by_agent_id=total_scores_by_agent_id,
        eliminated_agent_id=eliminated_agent_id,
        replacement_agent=replacement_agent,
        final_agents=final_agents,
        seeds=GameSeeds(
            candidate_order_seed=candidate_order_seed,
            voting_seed=voting_seed,
            elimination_seed=elimination_seed,
            replacement_seed=replacement_seed,
        ),
    )
