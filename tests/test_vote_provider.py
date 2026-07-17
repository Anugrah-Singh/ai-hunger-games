import pytest

from ai_hunger_games.engine import (
    create_candidates,
    create_vote_options,
    generate_votes,
)
from ai_hunger_games.models import (
    Agent,
    Answer,
    Personality,
    Vote,
    VoteOption,
)
from ai_hunger_games.providers import (
    SimulatedVoteProvider,
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


class FirstOptionVoteProvider:
    async def generate_vote(
        self,
        voter: Agent,
        options: list[VoteOption],
        seed: int,
    ) -> Vote:
        del seed

        return Vote(
            voter_id=voter.id,
            candidate_id=options[0].candidate_id,
        )


class RecordingVoteProvider:
    def __init__(self) -> None:
        self.options_by_voter_id: dict[
            str,
            list[VoteOption],
        ] = {}

    async def generate_vote(
        self,
        voter: Agent,
        options: list[VoteOption],
        seed: int,
    ) -> Vote:
        del seed

        self.options_by_voter_id[voter.id] = options

        return Vote(
            voter_id=voter.id,
            candidate_id=options[0].candidate_id,
        )


def test_create_vote_options_excludes_own_answer() -> None:
    agents = create_test_agents()
    answers = create_test_answers()

    candidates = create_candidates(
        answers,
        seed=42,
    )

    voter = agents[0]

    options = create_vote_options(
        voter=voter,
        candidates=candidates,
    )

    candidate_by_id = {
        candidate.id: candidate
        for candidate in candidates
    }

    selected_author_ids = {
        candidate_by_id[option.candidate_id].answer.agent_id
        for option in options
    }

    assert voter.id not in selected_author_ids
    assert len(options) == len(candidates) - 1


def test_vote_options_do_not_expose_author_id() -> None:
    agents = create_test_agents()
    answers = create_test_answers()

    candidates = create_candidates(
        answers,
        seed=42,
    )

    options = create_vote_options(
        voter=agents[0],
        candidates=candidates,
    )

    first_option = options[0]

    assert hasattr(first_option, "candidate_id")
    assert hasattr(first_option, "answer_content")
    assert not hasattr(first_option, "agent_id")
    assert not hasattr(first_option, "author_id")


@pytest.mark.asyncio
async def test_generate_votes_creates_one_vote_per_agent() -> None:
    agents = create_test_agents()

    candidates = create_candidates(
        create_test_answers(),
        seed=42,
    )

    votes = await generate_votes(
        agents=agents,
        candidates=candidates,
        provider=FirstOptionVoteProvider(),
        seed=7,
    )

    assert len(votes) == len(agents)

    assert {
        vote.voter_id
        for vote in votes
    } == {
        agent.id
        for agent in agents
    }


@pytest.mark.asyncio
async def test_generate_votes_never_offers_own_answer() -> None:
    agents = create_test_agents()

    candidates = create_candidates(
        create_test_answers(),
        seed=42,
    )

    provider = RecordingVoteProvider()

    await generate_votes(
        agents=agents,
        candidates=candidates,
        provider=provider,
        seed=7,
    )

    candidates_by_id = {
        candidate.id: candidate
        for candidate in candidates
    }

    for voter in agents:
        options = provider.options_by_voter_id[voter.id]

        option_author_ids = {
            candidates_by_id[
                option.candidate_id
            ].answer.agent_id
            for option in options
        }

        assert voter.id not in option_author_ids


@pytest.mark.asyncio
async def test_simulated_vote_provider_is_reproducible() -> None:
    voter = create_test_agents()[0]

    options = [
        VoteOption(
            candidate_id="candidate_1",
            answer_content="First answer",
        ),
        VoteOption(
            candidate_id="candidate_2",
            answer_content="Second answer",
        ),
    ]

    provider = SimulatedVoteProvider()

    first_vote = await provider.generate_vote(
        voter=voter,
        options=options,
        seed=42,
    )

    second_vote = await provider.generate_vote(
        voter=voter,
        options=options,
        seed=42,
    )

    assert first_vote == second_vote


@pytest.mark.asyncio
async def test_simulated_vote_provider_rejects_empty_options() -> None:
    voter = create_test_agents()[0]
    provider = SimulatedVoteProvider()

    with pytest.raises(
        ValueError,
        match="No voting options available",
    ):
        await provider.generate_vote(
            voter=voter,
            options=[],
            seed=42,
        )