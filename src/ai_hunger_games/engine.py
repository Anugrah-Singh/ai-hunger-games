import asyncio
from random import Random

from ai_hunger_games.models import (
    Agent,
    Answer,
    AnswerBatchResult,
    AnswerGenerationPolicy,
    Candidate,
    GameResult,
    Personality,
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
    RetryableProviderError,
    SimulatedVoteProvider,
    VoteGenerationTimeoutError,
    VoteProvider,
)


def validate_agents(agents: list[Agent]) -> None:
    if not agents:
        raise ValueError("At least one agent is required")

    agent_ids = [agent.id for agent in agents]

    for agent in agents:
        if not agent.id.strip():
            raise ValueError("Agent IDs cannot be empty")

        if not agent.name.strip():
            raise ValueError("Agent names cannot be empty")

    if len(agent_ids) != len(set(agent_ids)):
        raise ValueError("Agent IDs must be unique")


def validate_answer_policy(
    policy: AnswerGenerationPolicy,
) -> None:
    if policy.timeout_seconds <= 0:
        raise ValueError(
            "Answer timeout must be greater than zero"
        )

    if policy.minimum_successful_answers < 2:
        raise ValueError(
            "At least two successful answers are required"
        )

    if policy.maximum_attempts < 1:
        raise ValueError(
            "Maximum attempts must be at least 1"
        )

    if policy.initial_retry_delay_seconds < 0:
        raise ValueError(
            "Initial retry delay cannot be negative"
        )

    if policy.maximum_retry_delay_seconds < 0:
        raise ValueError(
            "Maximum retry delay cannot be negative"
        )

    if (
        policy.maximum_retry_delay_seconds
        < policy.initial_retry_delay_seconds
    ):
        raise ValueError(
            "Maximum retry delay cannot be less than "
            "the initial retry delay"
        )


def validate_vote_policy(
    policy: VoteGenerationPolicy,
) -> None:
    if policy.timeout_seconds <= 0:
        raise ValueError(
            "Vote timeout must be greater than zero"
        )

    if policy.maximum_attempts < 1:
        raise ValueError(
            "Maximum vote attempts must be at least 1"
        )

    if policy.initial_retry_delay_seconds < 0:
        raise ValueError(
            "Initial vote retry delay cannot be negative"
        )

    if policy.maximum_retry_delay_seconds < 0:
        raise ValueError(
            "Maximum vote retry delay cannot be negative"
        )

    if (
        policy.maximum_retry_delay_seconds
        < policy.initial_retry_delay_seconds
    ):
        raise ValueError(
            "Maximum vote retry delay cannot be less than "
            "the initial vote retry delay"
        )


def validate_answers(
    agents: list[Agent],
    answers: list[Answer],
) -> None:
    agent_ids = {
        agent.id
        for agent in agents
    }

    answering_agent_ids: set[str] = set()

    for answer in answers:
        if answer.agent_id not in agent_ids:
            raise ValueError(
                f"Unknown answering agent: {answer.agent_id}"
            )

        if not answer.content.strip():
            raise ValueError(
                f"Answer cannot be empty: {answer.agent_id}"
            )

        if answer.agent_id in answering_agent_ids:
            raise ValueError(
                "Agent cannot answer more than once: "
                f"{answer.agent_id}"
            )

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
            return await generate_answer_once(
                agent=agent,
                question=question,
                provider=provider,
                timeout_seconds=policy.timeout_seconds,
            )
        except (
            AnswerGenerationTimeoutError,
            RetryableProviderError,
        ):
            is_final_attempt = (
                attempt_number == policy.maximum_attempts
            )

            if is_final_attempt:
                raise

            retry_delay_seconds = min(
                policy.initial_retry_delay_seconds
                * (2 ** (attempt_number - 1)),
                policy.maximum_retry_delay_seconds,
            )

            await asyncio.sleep(retry_delay_seconds)

    raise RuntimeError(
        "Answer retry loop ended unexpectedly"
    )


async def generate_answers(
    agents: list[Agent],
    question: str,
    provider: AnswerProvider,
    policy: AnswerGenerationPolicy,
) -> AnswerBatchResult:
    if not question.strip():
        raise ValueError("Question cannot be empty")

    validate_answer_policy(policy)

    answer_tasks = [
        generate_answer_with_retry(
            agent=agent,
            question=question,
            provider=provider,
            policy=policy,
        )
        for agent in agents
    ]

    results = await asyncio.gather(
        *answer_tasks,
        return_exceptions=True,
    )

    successful_answers: list[Answer] = []
    failed_agent_ids: list[str] = []

    for agent, result in zip(
        agents,
        results,
        strict=True,
    ):
        if isinstance(result, BaseException):
            failed_agent_ids.append(agent.id)
            continue

        successful_answers.append(result)

    return AnswerBatchResult(
        answers=successful_answers,
        failed_agent_ids=failed_agent_ids,
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
        is_voters_own_answer = (
            candidate.answer.agent_id == voter.id
        )

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
        ):
            is_final_attempt = (
                attempt_number == policy.maximum_attempts
            )

            if is_final_attempt:
                raise

            retry_delay_seconds = min(
                policy.initial_retry_delay_seconds
                * (2 ** (attempt_number - 1)),
                policy.maximum_retry_delay_seconds,
            )

            await asyncio.sleep(retry_delay_seconds)

    raise RuntimeError(
        "Vote retry loop ended unexpectedly"
    )


async def generate_votes(
    agents: list[Agent],
    candidates: list[Candidate],
    provider: VoteProvider,
    seed: int,
    policy: VoteGenerationPolicy,
) -> list[Vote]:
    if len(agents) < 2:
        raise ValueError(
            "At least two agents are required for voting"
        )

    validate_vote_policy(policy)

    vote_tasks = []

    for voter_position, voter in enumerate(
        agents,
        start=1,
    ):
        options = create_vote_options(
            voter=voter,
            candidates=candidates,
        )

        if not options:
            raise ValueError(
                f"No voting options available for {voter.id}"
            )

        voter_seed = seed + voter_position

        vote_tasks.append(
            generate_vote_with_retry(
                voter=voter,
                options=options,
                provider=provider,
                seed=voter_seed,
                policy=policy,
            )
        )

    return list(await asyncio.gather(*vote_tasks))


def count_votes(
    agents: list[Agent],
    candidates: list[Candidate],
    votes: list[Vote],
) -> dict[str, int]:
    validate_agents(agents)

    agent_ids = {
        agent.id
        for agent in agents
    }

    scores_by_candidate_id: dict[str, int] = {
        candidate.id: 0
        for candidate in candidates
    }

    candidates_by_id = {
        candidate.id: candidate
        for candidate in candidates
    }

    candidate_id_by_author_id = {
        candidate.answer.agent_id: candidate.id
        for candidate in candidates
    }

    voters_seen: set[str] = set()

    for vote in votes:
        if vote.voter_id not in agent_ids:
            raise ValueError(
                f"Unknown voter: {vote.voter_id}"
            )

        if vote.candidate_id not in candidates_by_id:
            raise ValueError(
                f"Unknown candidate: {vote.candidate_id}"
            )

        voter_candidate_id = candidate_id_by_author_id[
            vote.voter_id
        ]

        if vote.candidate_id == voter_candidate_id:
            raise ValueError(
                "Agent cannot vote for its own answer: "
                f"{vote.voter_id}"
            )

        if vote.voter_id in voters_seen:
            raise ValueError(
                "Agent cannot vote more than once: "
                f"{vote.voter_id}"
            )

        voters_seen.add(vote.voter_id)
        scores_by_candidate_id[vote.candidate_id] += 1

    return scores_by_candidate_id


def find_winners(
    scores_by_id: dict[str, int],
) -> list[str]:
    if not scores_by_id:
        raise ValueError(
            "Cannot find a winner without scores"
        )

    highest_score = max(scores_by_id.values())

    return [
        item_id
        for item_id, score in scores_by_id.items()
        if score == highest_score
    ]


def find_lowest_scoring_agents(
    scores_by_agent_id: dict[str, int],
) -> list[str]:
    if not scores_by_agent_id:
        raise ValueError(
            "Cannot find elimination candidates without scores"
        )

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
    lowest_scoring_agent_ids = (
        find_lowest_scoring_agents(scores_by_agent_id)
    )

    if len(lowest_scoring_agent_ids) == 1:
        return lowest_scoring_agent_ids[0]

    random_generator = Random(seed)

    return random_generator.choice(
        lowest_scoring_agent_ids
    )


def generate_replacement_personality(
    seed: int,
) -> Personality:
    personality_styles = [
        (
            "Practical Builder",
            "A practical answer to '{question}' is that "
            "strong decisions should be useful, achievable, "
            "and supported by clear action.",
        ),
        (
            "Curious Explorer",
            "A curious answer to '{question}' begins by "
            "questioning assumptions, considering alternatives, "
            "and remaining open to unexpected evidence.",
        ),
        (
            "Empathetic Mediator",
            "An empathetic answer to '{question}' considers "
            "how the decision affects different people and "
            "searches for a fair, cooperative outcome.",
        ),
        (
            "Bold Challenger",
            "A bold answer to '{question}' is that progress "
            "often requires challenging comfortable beliefs "
            "and taking carefully considered risks.",
        ),
    ]

    random_generator = Random(seed)

    personality_name, answer_template = (
        random_generator.choice(personality_styles)
    )

    return Personality(
        name=personality_name,
        answer_template=answer_template,
    )


def generate_replacement_agent(
    agent_id: str,
    seed: int,
) -> Agent:
    personality = generate_replacement_personality(seed)

    return Agent(
        id=agent_id,
        name=personality.name,
        personality=personality,
    )


def replace_agent(
    agents: list[Agent],
    eliminated_agent_id: str,
    replacement_agent: Agent,
) -> list[Agent]:
    existing_agent_ids = {
        agent.id
        for agent in agents
    }

    if eliminated_agent_id not in existing_agent_ids:
        raise ValueError(
            "Cannot replace unknown agent: "
            f"{eliminated_agent_id}"
        )

    if replacement_agent.id in existing_agent_ids:
        raise ValueError(
            "Replacement agent ID already exists: "
            f"{replacement_agent.id}"
        )

    remaining_agents = [
        agent
        for agent in agents
        if agent.id != eliminated_agent_id
    ]

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
        candidate_score = scores_by_candidate_id[
            candidate.id
        ]

        scores_by_agent_id[agent_id] = candidate_score

    return scores_by_agent_id


def add_round_scores(
    total_scores_by_agent_id: dict[str, int],
    round_scores_by_agent_id: dict[str, int],
) -> None:
    for agent_id, round_score in (
        round_scores_by_agent_id.items()
    ):
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

    if (
        len(answer_batch.answers)
        < answer_policy.minimum_successful_answers
    ):
        raise InsufficientAnswersError(
            successful_answer_count=len(
                answer_batch.answers
            ),
            minimum_required=(
                answer_policy.minimum_successful_answers
            ),
        )

    validate_answers(
        agents,
        answer_batch.answers,
    )

    successful_agent_ids = {
        answer.agent_id
        for answer in answer_batch.answers
    }

    participating_agents = [
        agent
        for agent in agents
        if agent.id in successful_agent_ids
    ]

    candidates = create_candidates(
        answer_batch.answers,
        seed=candidate_order_seed,
    )

    effective_vote_provider = (
        vote_provider or SimulatedVoteProvider()
    )

    effective_vote_policy = (
        vote_policy
        or VoteGenerationPolicy(
            timeout_seconds=10.0,
            maximum_attempts=3,
            initial_retry_delay_seconds=2.0,
            maximum_retry_delay_seconds=10.0,
        )
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

    winning_candidate_ids = find_winners(
        scores_by_candidate_id
    )

    return RoundResult(
        round=round_config,
        answers=answer_batch.answers,
        failed_agent_ids=answer_batch.failed_agent_ids,
        candidates=candidates,
        votes=votes,
        scores_by_candidate_id=scores_by_candidate_id,
        winning_candidate_ids=winning_candidate_ids,
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
) -> GameResult:
    if not questions:
        raise ValueError(
            "At least one question is required"
        )

    validate_agents(agents)
    validate_answer_policy(answer_policy)

    if vote_policy is not None:
        validate_vote_policy(vote_policy)

    total_scores_by_agent_id = {
        agent.id: 0
        for agent in agents
    }

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
            candidate_order_seed=(
                candidate_order_seed + round_number
            ),
            voting_seed=voting_seed + round_number,
            answer_provider=answer_provider,
            answer_policy=answer_policy,
            vote_provider=vote_provider,
            vote_policy=vote_policy,
        )

        round_scores_by_agent_id = (
            convert_candidate_scores_to_agent_scores(
                round_result.candidates,
                round_result.scores_by_candidate_id,
            )
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

    replacement_agent = generate_replacement_agent(
        agent_id=replacement_agent_id,
        seed=replacement_seed,
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
    )