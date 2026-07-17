import asyncio
from time import perf_counter

import pytest

from ai_hunger_games.engine import (
    count_votes,
    create_candidates,
    find_lowest_scoring_agents,
    generate_answers,
    replace_agent,
    run_game,
    run_round,
    select_eliminated_agent,
    validate_agents,
    validate_answer_policy,
)
from ai_hunger_games.models import (
    Agent,
    Answer,
    AnswerGenerationPolicy,
    Personality,
    Round,
    Vote,
)
from ai_hunger_games.providers import (
    InsufficientAnswersError,
    RetryableProviderError,
    SimulatedAnswerProvider,
)


def create_test_agents() -> list[Agent]:
    personality = Personality(
        name="Test Personality",
        answer_template="Test answer for {question}",
    )

    return [
        Agent(
            id="agent_1",
            name="Agent One",
            personality=personality,
        ),
        Agent(
            id="agent_2",
            name="Agent Two",
            personality=personality,
        ),
        Agent(
            id="agent_3",
            name="Agent Three",
            personality=personality,
        ),
    ]


def create_test_answers() -> list[Answer]:
    return [
        Answer(
            agent_id="agent_1",
            content="Answer one",
        ),
        Answer(
            agent_id="agent_2",
            content="Answer two",
        ),
        Answer(
            agent_id="agent_3",
            content="Answer three",
        ),
    ]


def create_test_answer_policy() -> AnswerGenerationPolicy:
    return AnswerGenerationPolicy(
        timeout_seconds=1.0,
        minimum_successful_answers=2,
        maximum_attempts=1,
        initial_retry_delay_seconds=0,
        maximum_retry_delay_seconds=0,
    )


def create_timeout_test_policy() -> AnswerGenerationPolicy:
    return AnswerGenerationPolicy(
        timeout_seconds=0.05,
        minimum_successful_answers=2,
        maximum_attempts=1,
        initial_retry_delay_seconds=0,
        maximum_retry_delay_seconds=0,
    )


def create_retry_test_policy(
    maximum_attempts: int = 3,
) -> AnswerGenerationPolicy:
    return AnswerGenerationPolicy(
        timeout_seconds=1.0,
        minimum_successful_answers=2,
        maximum_attempts=maximum_attempts,
        initial_retry_delay_seconds=0,
        maximum_retry_delay_seconds=0,
    )


class SlowAnswerProvider:
    def __init__(self, delay_seconds: float) -> None:
        self.delay_seconds = delay_seconds

    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        await asyncio.sleep(self.delay_seconds)

        return Answer(
            agent_id=agent.id,
            content=f"{agent.name} answered: {question}",
        )


class ConcurrencyTrackingAnswerProvider:
    def __init__(self) -> None:
        self.active_request_count = 0
        self.maximum_active_request_count = 0

    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        self.active_request_count += 1
        self.maximum_active_request_count = max(
            self.maximum_active_request_count,
            self.active_request_count,
        )

        try:
            await asyncio.sleep(0.02)
        finally:
            self.active_request_count -= 1

        return Answer(
            agent_id=agent.id,
            content=f"{agent.name} answered: {question}",
        )


class CancellingAnswerProvider:
    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        del agent, question
        raise asyncio.CancelledError


class SeedRecordingVoteProvider:
    def __init__(self) -> None:
        self.seeds: list[int] = []

    async def generate_vote(
        self,
        voter: Agent,
        options: list,
        seed: int,
    ) -> Vote:
        self.seeds.append(seed)

        return Vote(
            voter_id=voter.id,
            candidate_id=options[0].candidate_id,
        )


class UnexpectedAnswerProvider:
    def __init__(self) -> None:
        self.was_called = False

    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        del agent, question
        self.was_called = True
        raise AssertionError("The answer provider should not be called")


class PartiallyFailingAnswerProvider:
    def __init__(self, failing_agent_id: str) -> None:
        self.failing_agent_id = failing_agent_id

    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        if agent.id == self.failing_agent_id:
            raise RuntimeError("Simulated provider failure")

        return Answer(
            agent_id=agent.id,
            content=f"{agent.name} answered: {question}",
        )


class MostlyFailingAnswerProvider:
    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        if agent.id != "agent_1":
            raise RuntimeError("Simulated provider failure")

        return Answer(
            agent_id=agent.id,
            content=f"{agent.name} answered: {question}",
        )


class TemporarilyFailingAnswerProvider:
    def __init__(
        self,
        failures_before_success: int,
    ) -> None:
        self.failures_before_success = failures_before_success
        self.attempts_by_agent_id: dict[str, int] = {}

    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        attempt_count = self.attempts_by_agent_id.get(agent.id, 0) + 1

        self.attempts_by_agent_id[agent.id] = attempt_count

        if attempt_count <= self.failures_before_success:
            raise RetryableProviderError("Simulated temporary provider failure")

        return Answer(
            agent_id=agent.id,
            content=f"{agent.name} answered: {question}",
        )


class PermanentFailureAnswerProvider:
    def __init__(self) -> None:
        self.attempts_by_agent_id: dict[str, int] = {}

    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        current_attempts = self.attempts_by_agent_id.get(
            agent.id,
            0,
        )

        self.attempts_by_agent_id[agent.id] = current_attempts + 1

        raise ValueError("Simulated permanent failure")


class RetryAfterFailureAnswerProvider:
    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        del agent, question
        raise RetryableProviderError(
            "The provider asked the caller to retry later",
            retry_after_seconds=7.5,
        )


def test_validate_agents_accepts_valid_agents() -> None:
    agents = create_test_agents()

    validate_agents(agents)


def test_validate_agents_rejects_duplicate_ids() -> None:
    agents = create_test_agents()

    agents[1] = Agent(
        id="agent_1",
        name="Duplicate Agent",
        personality=agents[1].personality,
    )

    with pytest.raises(
        ValueError,
        match="Agent IDs must be unique",
    ):
        validate_agents(agents)


def test_validate_agents_rejects_template_without_question_placeholder() -> None:
    agents = create_test_agents()
    agents[0].personality = Personality(
        name="Incomplete Personality",
        answer_template="Give a generic answer.",
    )

    with pytest.raises(
        ValueError,
        match="must contain \\{question\\}",
    ):
        validate_agents(agents)


def test_validate_answer_policy_accepts_valid_policy() -> None:
    policy = create_test_answer_policy()

    validate_answer_policy(policy)


def test_validate_answer_policy_rejects_non_positive_timeout() -> None:
    policy = AnswerGenerationPolicy(
        timeout_seconds=0,
        minimum_successful_answers=2,
        maximum_attempts=1,
        initial_retry_delay_seconds=0,
        maximum_retry_delay_seconds=0,
    )

    with pytest.raises(
        ValueError,
        match="Answer timeout must be greater than zero",
    ):
        validate_answer_policy(policy)


def test_validate_answer_policy_rejects_too_few_answers() -> None:
    policy = AnswerGenerationPolicy(
        timeout_seconds=1.0,
        minimum_successful_answers=1,
        maximum_attempts=1,
        initial_retry_delay_seconds=0,
        maximum_retry_delay_seconds=0,
    )

    with pytest.raises(
        ValueError,
        match="At least two successful answers are required",
    ):
        validate_answer_policy(policy)


def test_validate_answer_policy_rejects_zero_attempts() -> None:
    policy = AnswerGenerationPolicy(
        timeout_seconds=1.0,
        minimum_successful_answers=2,
        maximum_attempts=0,
        initial_retry_delay_seconds=0,
        maximum_retry_delay_seconds=0,
    )

    with pytest.raises(
        ValueError,
        match="Maximum attempts must be at least 1",
    ):
        validate_answer_policy(policy)


def test_validate_answer_policy_rejects_negative_initial_delay() -> None:
    policy = AnswerGenerationPolicy(
        timeout_seconds=1.0,
        minimum_successful_answers=2,
        maximum_attempts=1,
        initial_retry_delay_seconds=-1,
        maximum_retry_delay_seconds=0,
    )

    with pytest.raises(
        ValueError,
        match="Initial retry delay cannot be negative",
    ):
        validate_answer_policy(policy)


def test_validate_answer_policy_rejects_invalid_delay_range() -> None:
    policy = AnswerGenerationPolicy(
        timeout_seconds=1.0,
        minimum_successful_answers=2,
        maximum_attempts=3,
        initial_retry_delay_seconds=2.0,
        maximum_retry_delay_seconds=1.0,
    )

    with pytest.raises(
        ValueError,
        match=("Maximum retry delay cannot be less than the initial retry delay"),
    ):
        validate_answer_policy(policy)


def test_create_candidates_is_reproducible() -> None:
    answers = create_test_answers()

    first_candidates = create_candidates(
        answers,
        seed=42,
    )

    second_candidates = create_candidates(
        answers,
        seed=42,
    )

    first_author_order = [candidate.answer.agent_id for candidate in first_candidates]

    second_author_order = [candidate.answer.agent_id for candidate in second_candidates]

    assert first_author_order == second_author_order


def test_count_votes_calculates_candidate_scores() -> None:
    agents = create_test_agents()
    answers = create_test_answers()

    candidates = create_candidates(
        answers,
        seed=1,
    )

    candidate_id_by_author_id = {
        candidate.answer.agent_id: candidate.id for candidate in candidates
    }

    votes = [
        Vote(
            voter_id="agent_1",
            candidate_id=candidate_id_by_author_id["agent_2"],
        ),
        Vote(
            voter_id="agent_2",
            candidate_id=candidate_id_by_author_id["agent_3"],
        ),
        Vote(
            voter_id="agent_3",
            candidate_id=candidate_id_by_author_id["agent_2"],
        ),
    ]

    scores = count_votes(
        agents,
        candidates,
        votes,
    )

    agent_1_candidate_id = candidate_id_by_author_id["agent_1"]
    agent_2_candidate_id = candidate_id_by_author_id["agent_2"]
    agent_3_candidate_id = candidate_id_by_author_id["agent_3"]

    assert scores[agent_1_candidate_id] == 0
    assert scores[agent_2_candidate_id] == 2
    assert scores[agent_3_candidate_id] == 1


def test_count_votes_rejects_self_vote() -> None:
    agents = create_test_agents()
    answers = create_test_answers()

    candidates = create_candidates(
        answers,
        seed=1,
    )

    candidate_id_by_author_id = {
        candidate.answer.agent_id: candidate.id for candidate in candidates
    }

    self_vote = Vote(
        voter_id="agent_1",
        candidate_id=candidate_id_by_author_id["agent_1"],
    )

    with pytest.raises(
        ValueError,
        match="Agent cannot vote for its own answer",
    ):
        count_votes(
            agents,
            candidates,
            [self_vote],
        )


def test_count_votes_rejects_duplicate_voter() -> None:
    agents = create_test_agents()
    answers = create_test_answers()

    candidates = create_candidates(
        answers,
        seed=1,
    )

    candidate_id_by_author_id = {
        candidate.answer.agent_id: candidate.id for candidate in candidates
    }

    votes = [
        Vote(
            voter_id="agent_1",
            candidate_id=candidate_id_by_author_id["agent_2"],
        ),
        Vote(
            voter_id="agent_1",
            candidate_id=candidate_id_by_author_id["agent_3"],
        ),
    ]

    with pytest.raises(
        ValueError,
        match="Agent cannot vote more than once",
    ):
        count_votes(
            agents,
            candidates,
            votes,
        )


def test_find_lowest_scoring_agents_returns_all_ties() -> None:
    scores = {
        "agent_1": 5,
        "agent_2": 2,
        "agent_3": 2,
    }

    lowest_scoring_agent_ids = find_lowest_scoring_agents(scores)

    assert lowest_scoring_agent_ids == [
        "agent_2",
        "agent_3",
    ]


def test_select_eliminated_agent_is_reproducible() -> None:
    scores = {
        "agent_1": 5,
        "agent_2": 2,
        "agent_3": 2,
    }

    first_selection = select_eliminated_agent(
        scores,
        seed=99,
    )

    second_selection = select_eliminated_agent(
        scores,
        seed=99,
    )

    assert first_selection == second_selection

    assert first_selection in {
        "agent_2",
        "agent_3",
    }


def test_replace_agent_preserves_population_size() -> None:
    agents = create_test_agents()

    replacement_agent = Agent(
        id="agent_4",
        name="Replacement",
        personality=Personality(
            name="Replacement Personality",
            answer_template=("Replacement answer for {question}"),
        ),
    )

    updated_agents = replace_agent(
        agents,
        eliminated_agent_id="agent_2",
        replacement_agent=replacement_agent,
    )

    updated_agent_ids = {agent.id for agent in updated_agents}

    assert len(updated_agents) == len(agents)
    assert "agent_2" not in updated_agent_ids
    assert "agent_4" in updated_agent_ids


@pytest.mark.asyncio
async def test_run_game_completes_full_game_cycle() -> None:
    agents = create_test_agents()
    answer_provider = SimulatedAnswerProvider()

    questions = [
        "Question one?",
        "Question two?",
        "Question three?",
    ]

    game_result = await run_game(
        questions=questions,
        agents=agents,
        candidate_order_seed=42,
        voting_seed=7,
        elimination_seed=99,
        replacement_seed=123,
        replacement_agent_id="agent_4",
        answer_provider=answer_provider,
        answer_policy=create_test_answer_policy(),
    )

    assert len(game_result.round_results) == len(questions)

    assert set(game_result.total_scores_by_agent_id) == {
        "agent_1",
        "agent_2",
        "agent_3",
    }

    assert game_result.eliminated_agent_id in {
        "agent_1",
        "agent_2",
        "agent_3",
    }

    assert game_result.replacement_agent.id == "agent_4"

    final_agent_ids = {agent.id for agent in game_result.final_agents}

    assert len(game_result.final_agents) == len(agents)
    assert game_result.eliminated_agent_id not in final_agent_ids
    assert "agent_4" in final_agent_ids


@pytest.mark.asyncio
async def test_run_game_rejects_existing_replacement_id_before_requests() -> None:
    provider = UnexpectedAnswerProvider()

    with pytest.raises(
        ValueError,
        match="Replacement agent ID already exists",
    ):
        await run_game(
            questions=["Question one?"],
            agents=create_test_agents(),
            candidate_order_seed=42,
            voting_seed=7,
            elimination_seed=99,
            replacement_seed=123,
            replacement_agent_id="agent_1",
            answer_provider=provider,
            answer_policy=create_test_answer_policy(),
        )

    assert not provider.was_called


@pytest.mark.asyncio
async def test_run_game_derives_unique_vote_seeds_per_round_and_voter() -> None:
    vote_provider = SeedRecordingVoteProvider()

    await run_game(
        questions=["Question one?", "Question two?"],
        agents=create_test_agents(),
        candidate_order_seed=42,
        voting_seed=7,
        elimination_seed=99,
        replacement_seed=123,
        replacement_agent_id="agent_4",
        answer_provider=SimulatedAnswerProvider(),
        answer_policy=create_test_answer_policy(),
        vote_provider=vote_provider,
    )

    assert len(vote_provider.seeds) == 6
    assert len(set(vote_provider.seeds)) == 6


@pytest.mark.asyncio
async def test_generate_answers_runs_concurrently() -> None:
    agents = create_test_agents()

    provider = SlowAnswerProvider(
        delay_seconds=0.1,
    )

    started_at = perf_counter()

    answer_batch = await generate_answers(
        agents=agents,
        question="What makes a good team?",
        provider=provider,
        policy=create_test_answer_policy(),
    )

    elapsed_seconds = perf_counter() - started_at

    assert len(answer_batch.answers) == len(agents)
    assert answer_batch.failed_agent_ids == []
    assert elapsed_seconds < 0.25


@pytest.mark.asyncio
async def test_generate_answers_respects_concurrency_limit() -> None:
    provider = ConcurrencyTrackingAnswerProvider()
    policy = AnswerGenerationPolicy(
        timeout_seconds=1.0,
        minimum_successful_answers=2,
        maximum_attempts=1,
        initial_retry_delay_seconds=0,
        maximum_retry_delay_seconds=0,
        maximum_concurrent_requests=2,
    )

    answer_batch = await generate_answers(
        agents=create_test_agents(),
        question="What makes a good team?",
        provider=provider,
        policy=policy,
    )

    assert len(answer_batch.answers) == 3
    assert provider.maximum_active_request_count == 2


@pytest.mark.asyncio
async def test_generate_answers_propagates_cancellation() -> None:
    with pytest.raises(asyncio.CancelledError):
        await generate_answers(
            agents=create_test_agents(),
            question="What makes a good team?",
            provider=CancellingAnswerProvider(),
            policy=create_test_answer_policy(),
        )


@pytest.mark.asyncio
async def test_simulated_answers_replace_only_question_placeholder() -> None:
    agent = Agent(
        id="agent_1",
        name="Literal Template Tester",
        personality=Personality(
            name="Literal Template Tester",
            answer_template=("Keep {other_braces} literal while answering {question}"),
        ),
    )

    answer = await SimulatedAnswerProvider().generate_answer(
        agent=agent,
        question="this question",
    )

    assert answer.content == (
        "Keep {other_braces} literal while answering this question"
    )


@pytest.mark.asyncio
async def test_generate_answers_records_timeouts() -> None:
    agents = create_test_agents()

    provider = SlowAnswerProvider(
        delay_seconds=0.2,
    )

    answer_batch = await generate_answers(
        agents=agents,
        question="What makes a good team?",
        provider=provider,
        policy=create_timeout_test_policy(),
    )

    assert answer_batch.answers == []

    assert set(answer_batch.failed_agent_ids) == {
        "agent_1",
        "agent_2",
        "agent_3",
    }
    assert {failure.error_type for failure in answer_batch.failures} == {
        "AnswerGenerationTimeoutError"
    }
    assert {failure.attempt_count for failure in answer_batch.failures} == {1}
    assert all(failure.retry_after_seconds is None for failure in answer_batch.failures)


@pytest.mark.asyncio
async def test_run_round_continues_after_one_failure() -> None:
    agents = create_test_agents()

    provider = PartiallyFailingAnswerProvider(
        failing_agent_id="agent_3",
    )

    round_result = await run_round(
        round_config=Round(
            number=1,
            question="What makes a good team?",
        ),
        agents=agents,
        candidate_order_seed=42,
        voting_seed=7,
        answer_provider=provider,
        answer_policy=create_test_answer_policy(),
    )

    assert len(round_result.answers) == 2
    assert round_result.failed_agent_ids == ["agent_3"]
    assert len(round_result.candidates) == 2
    assert len(round_result.votes) == 2

    participating_agent_ids = {answer.agent_id for answer in round_result.answers}

    assert participating_agent_ids == {
        "agent_1",
        "agent_2",
    }

    assert all(answer.agent_id != "agent_3" for answer in round_result.answers)

    assert all(vote.voter_id != "agent_3" for vote in round_result.votes)
    assert len(round_result.failures) == 1
    assert round_result.failures[0].agent_id == "agent_3"
    assert round_result.failures[0].error_type == "RuntimeError"
    assert round_result.failures[0].attempt_count == 1


@pytest.mark.asyncio
async def test_run_round_fails_below_answer_threshold() -> None:
    agents = create_test_agents()
    provider = MostlyFailingAnswerProvider()

    with pytest.raises(
        InsufficientAnswersError,
        match="Not enough answers to continue the round",
    ):
        await run_round(
            round_config=Round(
                number=1,
                question="What makes a good team?",
            ),
            agents=agents,
            candidate_order_seed=42,
            voting_seed=7,
            answer_provider=provider,
            answer_policy=create_test_answer_policy(),
        )


@pytest.mark.asyncio
async def test_generate_answers_retries_temporary_failures() -> None:
    agents = create_test_agents()

    provider = TemporarilyFailingAnswerProvider(
        failures_before_success=2,
    )

    answer_batch = await generate_answers(
        agents=agents,
        question="What makes a good team?",
        provider=provider,
        policy=create_retry_test_policy(maximum_attempts=3),
    )

    assert len(answer_batch.answers) == len(agents)
    assert answer_batch.failed_agent_ids == []

    assert provider.attempts_by_agent_id == {
        "agent_1": 3,
        "agent_2": 3,
        "agent_3": 3,
    }
    assert {answer.attempt_count for answer in answer_batch.answers} == {3}


@pytest.mark.asyncio
async def test_generate_answers_records_exhausted_retries() -> None:
    agents = create_test_agents()

    provider = TemporarilyFailingAnswerProvider(
        failures_before_success=5,
    )

    answer_batch = await generate_answers(
        agents=agents,
        question="What makes a good team?",
        provider=provider,
        policy=create_retry_test_policy(maximum_attempts=3),
    )

    assert answer_batch.answers == []

    assert set(answer_batch.failed_agent_ids) == {
        "agent_1",
        "agent_2",
        "agent_3",
    }

    assert provider.attempts_by_agent_id == {
        "agent_1": 3,
        "agent_2": 3,
        "agent_3": 3,
    }
    assert {failure.error_type for failure in answer_batch.failures} == {
        "RetryableProviderError"
    }
    assert {failure.attempt_count for failure in answer_batch.failures} == {3}
    assert all(failure.retry_after_seconds is None for failure in answer_batch.failures)


@pytest.mark.asyncio
async def test_generate_answers_preserves_provider_retry_after_on_failure() -> None:
    answer_batch = await generate_answers(
        agents=create_test_agents(),
        question="What makes a good team?",
        provider=RetryAfterFailureAnswerProvider(),
        policy=create_retry_test_policy(maximum_attempts=1),
    )

    assert answer_batch.answers == []
    assert {failure.retry_after_seconds for failure in answer_batch.failures} == {7.5}
    assert {failure.attempt_count for failure in answer_batch.failures} == {1}


@pytest.mark.asyncio
async def test_generate_answers_does_not_retry_permanent_errors() -> None:
    agents = create_test_agents()
    provider = PermanentFailureAnswerProvider()

    answer_batch = await generate_answers(
        agents=agents,
        question="What makes a good team?",
        provider=provider,
        policy=create_retry_test_policy(maximum_attempts=3),
    )

    assert answer_batch.answers == []

    assert set(answer_batch.failed_agent_ids) == {
        "agent_1",
        "agent_2",
        "agent_3",
    }

    assert provider.attempts_by_agent_id == {
        "agent_1": 1,
        "agent_2": 1,
        "agent_3": 1,
    }
