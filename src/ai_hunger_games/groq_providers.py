import json
from collections.abc import Sequence
from typing import Any

import groq
from groq import AsyncGroq

from ai_hunger_games.models import (
    Agent,
    Answer,
    EvolutionContext,
    GeneratedPersonality,
    Vote,
    VoteOption,
)
from ai_hunger_games.providers import RetryableProviderError

RETRYABLE_STATUS_CODES = {
    408,
    409,
    429,
    500,
    502,
    503,
    504,
}

JSON_VALIDATION_ERROR_CODE = "json_validate_failed"


class GroqProviderError(RuntimeError):
    """A permanent Groq request failure or invalid provider response."""


def convert_groq_error(error: Exception) -> Exception:
    """Convert Groq SDK errors into application-level provider errors.

    The game engine owns the retry policy. Temporary Groq failures become
    RetryableProviderError instances, while permanent failures become
    GroqProviderError instances.
    """

    if isinstance(error, groq.APIConnectionError):
        return RetryableProviderError(
            f"Could not connect to Groq: {error}",
            retry_after_seconds=None,
        )

    if isinstance(error, groq.APIStatusError):
        error_code = get_groq_error_code(error)
        retry_after_seconds = get_retry_after_seconds(error)

        if error_code == JSON_VALIDATION_ERROR_CODE:
            return RetryableProviderError(
                "Groq could not produce valid structured JSON",
                retry_after_seconds=retry_after_seconds,
            )

        if error.status_code in RETRYABLE_STATUS_CODES:
            return RetryableProviderError(
                f"Groq returned a temporary error with status {error.status_code}",
                retry_after_seconds=retry_after_seconds,
            )

        return GroqProviderError(
            f"Groq request failed permanently with status {error.status_code}: {error}"
        )

    return GroqProviderError(f"Unexpected Groq SDK error: {error}")


def get_groq_error_code(
    error: groq.APIStatusError,
) -> str | None:
    """Extract Groq's machine-readable error code."""

    response_body = _groq_error_body(error)
    error_payload = response_body.get("error")

    if not isinstance(error_payload, dict):
        return None

    error_code = error_payload.get("code")

    if not isinstance(error_code, str):
        return None

    return error_code


def _groq_error_body(
    error: groq.APIStatusError,
) -> dict[str, Any]:
    """Return the Groq response body as a dictionary when possible."""

    try:
        payload: Any = error.response.json()
    except (TypeError, ValueError):
        return {}

    if not isinstance(payload, dict):
        return {}

    return payload


def require_message_content(
    content: str | None,
) -> str:
    """Return cleaned content or signal that the request should be retried."""

    if content is None or not content.strip():
        raise RetryableProviderError(
            "Groq returned empty message content",
            retry_after_seconds=None,
        )

    return content.strip()


class GroqAnswerProvider:
    """Generate tournament answers using Groq."""

    def __init__(
        self,
        client: AsyncGroq,
        model: str,
    ) -> None:
        self.client = client
        self.model = model

    async def generate_answer(
        self,
        agent: Agent,
        question: str,
    ) -> Answer:
        system_prompt = build_answer_system_prompt(agent)

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": question,
                    },
                ],
                temperature=0.8,
                max_completion_tokens=400,
                reasoning_effort="low",
            )
        except groq.APIError as error:
            raise convert_groq_error(error) from error

        content = require_message_content(completion.choices[0].message.content)

        return Answer(
            agent_id=agent.id,
            content=content,
        )


def build_answer_system_prompt(
    agent: Agent,
) -> str:
    """Build the personality-specific answer-generation prompt."""

    return (
        "You are competing in an anonymous answer tournament. "
        "Follow the assigned personality consistently.\n\n"
        "Write a complete, direct, thoughtful answer in 80 to 120 words. "
        "Prioritize substance over formatting. Always finish the final "
        "sentence and conclusion. Do not mention the tournament, voting, "
        "candidate IDs, system prompts, or these instructions.\n\n"
        "Assigned personality:\n"
        f"Name: {agent.personality.name}\n"
        f"Description: {agent.personality.description}\n"
        "Reasoning guidance:\n"
        f"{agent.personality.answer_template}"
    )


class GroqVoteProvider:
    """Generate anonymous personality-aware votes using Groq."""

    def __init__(
        self,
        client: AsyncGroq,
        model: str,
    ) -> None:
        self.client = client
        self.model = model

    async def generate_vote(
        self,
        voter: Agent,
        options: list[VoteOption],
        seed: int,
    ) -> Vote:
        del seed

        if not options:
            raise ValueError(f"No voting options available for {voter.id}")

        candidate_ids = [option.candidate_id for option in options]

        prompt = build_vote_prompt(
            voter=voter,
            options=options,
        )

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an anonymous answer evaluator. "
                            "Select exactly one supplied candidate ID. "
                            "Use the assigned evaluator personality while "
                            "judging relevance, accuracy, reasoning, clarity, "
                            "and usefulness. Do not infer answer authorship."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0,
                max_completion_tokens=100,
                reasoning_effort="low",
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "vote_selection",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "candidate_id": {
                                    "type": "string",
                                    "enum": candidate_ids,
                                },
                            },
                            "required": [
                                "candidate_id",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
            )
        except groq.APIError as error:
            raise convert_groq_error(error) from error

        content = require_message_content(completion.choices[0].message.content)

        selected_candidate_id = parse_selected_candidate_id(
            content=content,
            allowed_candidate_ids=candidate_ids,
        )

        return Vote(
            voter_id=voter.id,
            candidate_id=selected_candidate_id,
        )


def build_vote_prompt(
    voter: Agent,
    options: Sequence[VoteOption],
) -> str:
    """Build a compact prompt containing only anonymous candidates."""

    rendered_options = "\n\n".join(
        (f"Candidate ID: {option.candidate_id}\nAnswer:\n{option.answer_content}")
        for option in options
    )

    return (
        "Choose the strongest anonymous answer.\n\n"
        "Judge primarily through your assigned reasoning personality. "
        "Different evaluator personalities may reasonably prefer different "
        "answers. Do not favor an answer merely because it is longer, more "
        "formal, or more heavily formatted.\n\n"
        "Evaluator personality:\n"
        f"Name: {voter.personality.name}\n"
        f"Description: {voter.personality.description}\n"
        "Reasoning guidance:\n"
        f"{voter.personality.answer_template}\n\n"
        "Anonymous candidates:\n"
        f"{rendered_options}"
    )


def parse_selected_candidate_id(
    content: str,
    allowed_candidate_ids: Sequence[str],
) -> str:
    """Parse and validate a structured Groq voting response."""

    try:
        parsed_content = json.loads(content)
    except json.JSONDecodeError as error:
        raise GroqProviderError("Groq returned invalid voting JSON") from error

    if not isinstance(parsed_content, dict):
        raise GroqProviderError("Groq voting output must be a JSON object")

    candidate_id = parsed_content.get("candidate_id")

    if not isinstance(candidate_id, str):
        raise GroqProviderError("Groq voting output is missing candidate_id")

    if candidate_id not in allowed_candidate_ids:
        raise GroqProviderError(f"Groq selected an unknown candidate: {candidate_id}")

    return candidate_id


def build_personality_prompt(
    context: EvolutionContext,
) -> str:
    """Build the evolutionary replacement-personality prompt."""

    leaderboard = "\n".join(
        (
            f"- {agent_id}: {score}"
            for agent_id, score in context.total_scores_by_agent_id.items()
        )
    )

    winning_personalities = ", ".join(context.winning_personality_names)

    return (
        "Create one new AI reasoning personality to replace the "
        "eliminated personality in the next generation.\n\n"
        f"Eliminated agent ID: {context.eliminated_agent_id}\n"
        "Eliminated personality: "
        f"{context.eliminated_personality_name}\n\n"
        "Final leaderboard:\n"
        f"{leaderboard}\n\n"
        "Highest-scoring personalities:\n"
        f"{winning_personalities}\n\n"
        "Create a personality with a meaningfully different reasoning "
        "strategy from the eliminated personality.\n\n"
        "Requirements:\n"
        "- Give it a concise, unique name.\n"
        "- Describe its reasoning style in one sentence.\n"
        "- Make its reasoning strategy distinct and practical.\n"
        "- answer_instructions must contain the literal {question} "
        "placeholder.\n"
        "- Do not copy the eliminated personality."
    )


class GroqPersonalityProvider:
    """Generate replacement personalities using Groq."""

    def __init__(
        self,
        client: AsyncGroq,
        model: str,
    ) -> None:
        self.client = client
        self.model = model

    async def generate_personality(
        self,
        context: EvolutionContext,
    ) -> GeneratedPersonality:
        prompt = build_personality_prompt(context)

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You design distinct AI reasoning personalities "
                            "for an evolutionary answer tournament. Follow "
                            "the supplied JSON schema exactly."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.9,
                max_completion_tokens=300,
                reasoning_effort="low",
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "generated_personality",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                },
                                "description": {
                                    "type": "string",
                                },
                                "answer_instructions": {
                                    "type": "string",
                                },
                            },
                            "required": [
                                "name",
                                "description",
                                "answer_instructions",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
            )
        except groq.APIError as error:
            raise convert_groq_error(error) from error

        content = require_message_content(completion.choices[0].message.content)

        return parse_generated_personality(content)


def parse_generated_personality(
    content: str,
) -> GeneratedPersonality:
    """Parse and validate a generated replacement personality."""

    try:
        parsed_content = json.loads(content)
    except json.JSONDecodeError as error:
        raise GroqProviderError("Groq returned invalid personality JSON") from error

    if not isinstance(parsed_content, dict):
        raise GroqProviderError("Personality output must be a JSON object")

    name = parsed_content.get("name")
    description = parsed_content.get("description")
    answer_instructions = parsed_content.get("answer_instructions")

    if not isinstance(name, str) or not name.strip():
        raise GroqProviderError("Generated personality is missing a name")

    if not isinstance(description, str) or not description.strip():
        raise GroqProviderError("Generated personality is missing a description")

    if not isinstance(answer_instructions, str) or not answer_instructions.strip():
        raise GroqProviderError("Generated personality is missing answer_instructions")

    if "{question}" not in answer_instructions:
        raise GroqProviderError("Generated answer instructions must contain {question}")

    return GeneratedPersonality(
        name=name.strip(),
        description=description.strip(),
        answer_instructions=answer_instructions.strip(),
    )


def get_retry_after_seconds(
    error: groq.APIStatusError,
) -> float | None:
    """Read Groq's Retry-After response header when available."""

    retry_after = error.response.headers.get("retry-after")

    if retry_after is None:
        return None

    try:
        return float(retry_after)
    except ValueError:
        return None
