import pytest

from ai_hunger_games.groq_providers import (
    GroqProviderError,
    build_vote_prompt,
    parse_selected_candidate_id,
)
from ai_hunger_games.models import (
    Agent,
    Personality,
    VoteOption,
)


def create_test_voter() -> Agent:
    return Agent(
        id="agent_1",
        name="Agent One",
        personality=Personality(
            name="Analytical Judge",
            description="Prioritizes evidence and explicit tradeoffs.",
            answer_template="Answer {question}",
        ),
    )


def test_parse_selected_candidate_id_accepts_valid_json() -> None:
    candidate_id = parse_selected_candidate_id(
        content='{"candidate_id": "candidate_2"}',
        allowed_candidate_ids=[
            "candidate_1",
            "candidate_2",
        ],
    )

    assert candidate_id == "candidate_2"


def test_parse_selected_candidate_id_rejects_invalid_json() -> None:
    with pytest.raises(
        GroqProviderError,
        match="invalid voting JSON",
    ):
        parse_selected_candidate_id(
            content="candidate_1",
            allowed_candidate_ids=[
                "candidate_1",
            ],
        )


def test_parse_selected_candidate_id_rejects_unknown_id() -> None:
    with pytest.raises(
        GroqProviderError,
        match="unknown candidate",
    ):
        parse_selected_candidate_id(
            content='{"candidate_id": "candidate_99"}',
            allowed_candidate_ids=[
                "candidate_1",
                "candidate_2",
            ],
        )


def test_json_validation_failure_is_retryable():
    error = make_groq_status_error(
        status_code=400,
        payload={
            "error": {
                "code": "json_validate_failed",
                "message": "Failed to validate JSON.",
            }
        },
    )

    converted = convert_groq_error(error)

    assert isinstance(converted, RetryableProviderError)


def test_vote_prompt_contains_only_anonymous_options() -> None:
    voter = create_test_voter()

    prompt = build_vote_prompt(
        voter=voter,
        options=[
            VoteOption(
                candidate_id="candidate_1",
                answer_content="First anonymous answer",
            ),
            VoteOption(
                candidate_id="candidate_2",
                answer_content="Second anonymous answer",
            ),
        ],
    )

    assert "candidate_1" in prompt
    assert "candidate_2" in prompt
    assert "First anonymous answer" in prompt
    assert "Second anonymous answer" in prompt
    assert "Prioritizes evidence and explicit tradeoffs." in prompt
    assert "Answer {question}" in prompt

    assert "agent_1" not in prompt


def test_json_validation_failure_is_retryable():
    error = make_groq_status_error(
        status_code=400,
        payload={
            "error": {
                "code": "json_validate_failed",
                "message": "Failed to validate JSON.",
            }
        },
    )

    converted = convert_groq_error(error)

    assert isinstance(converted, RetryableProviderError)



async def test_empty_answer_response_is_retryable():
    client = fake_client_returning_content("")

    provider = GroqAnswerProvider(
        client=client,
        model="openai/gpt-oss-20b",
    )

    with pytest.raises(RetryableProviderError):
        await provider.generate_answer(
            agent=sample_agent(),
            question="What makes a system reliable?",
        )


assert request["response_format"]["type"] == "json_schema"
assert request["response_format"]["json_schema"]["strict"] is True
assert request["response_format"]["json_schema"]["schema"][
    "properties"
]["selected_candidate_id"]["enum"] == [
    "candidate_1",
    "candidate_2",
]