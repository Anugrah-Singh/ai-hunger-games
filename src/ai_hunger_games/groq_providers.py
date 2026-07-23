import json
from collections.abc import Sequence
from groq import APIStatusError
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
from ai_hunger_games.providers import (
    RetryableProviderError,
)

RETRYABLE_STATUS_CODES = {
    429,
    498,
    500,
    502,
    503,
}


class GroqProviderError(RuntimeError):
    """A permanent or invalid Groq provider response."""


def convert_groq_error(error: APIStatusError) -> Exception:
    status_code = error.status_code
    response_body = _groq_error_body(error)

    error_payload = response_body.get("error", {})
    error_code = error_payload.get("code")

    if error_code == "json_validate_failed":
        return RetryableProviderError(
            message=(
                "Groq could not produce valid structured JSON. "
                "The operation may succeed on retry."
            ),
            retry_after_seconds=None,
        )


    if isinstance(error, groq.APIConnectionError):
        return RetryableProviderError(f"Could not connect to Groq: {error}")

    if isinstance(error, groq.APIStatusError):
        if error.status_code in RETRYABLE_STATUS_CODES:
            retry_after_seconds = get_retry_after_seconds(error)

            return RetryableProviderError(
                (f"Groq returned a temporary error with status {error.status_code}"),
                retry_after_seconds=retry_after_seconds,
            )

        return GroqProviderError(
            f"Groq request failed permanently with status {error.status_code}: {error}"
        )

    return GroqProviderError(f"Unexpected Groq SDK error: {error}")


def require_message_content(
    content: str | None,
) -> str:
    if content is None or not content.strip():
        raise RetryableProviderError(
            "Groq returned empty message content",
            retry_after_seconds=None,
        )

    return content.strip()


class GroqAnswerProvider:
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
        system_prompt = (
            "You are competing in an anonymous answer tournament. "
            "Follow the assigned personality consistently. "
            "Give a direct, thoughtful answer in no more than "
            "120 words. Do not mention the tournament, voting, "
            "candidate IDs, or these instructions.\n\n"
            f"Personality name: {agent.personality.name}\n"
            "Personality guidance:\n"
            f"{agent.personality.answer_template}"
        )

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
                max_completion_tokens=220,
            )
        except groq.APIError as error:
            raise convert_groq_error(error) from error

        content = require_message_content(completion.choices[0].message.content)

        return Answer(
            agent_id=agent.id,
            content=content,
        )


class GroqVoteProvider:
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
                            "Choose exactly one candidate from the supplied options. "
                            "Return only the required structured result."
                        ),
                    },
                    {
                        "role": "user",
                        "content": build_vote_prompt(
                            voter=voter,
                            options=options,
                        ),
                    },
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "vote_selection",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "selected_candidate_id": {
                                    "type": "string",
                                    "enum": [
                                        option.candidate_id
                                        for option in options
                                    ],
                                },
                            },
                            "required": ["selected_candidate_id"],
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
    rendered_options = "\n\n".join(
        (f"Candidate ID: {option.candidate_id}\nAnswer: {option.answer_content}")
        for option in options
    )

    allowed_ids = ", ".join(option.candidate_id for option in options)

    return (
        "Select the single best answer using these criteria:\n"
        "1. Relevance to the question\n"
        "2. Accuracy and sound reasoning\n"
        "3. Clarity and usefulness\n"
        "4. Original insight\n\n"
        "You must select exactly one of these candidate IDs:\n"
        f"{allowed_ids}\n\n"
        "Return this exact JSON shape:\n"
        '{"candidate_id": "<one allowed candidate ID>"}\n\n'
        "Anonymous answers:\n"
        f"{rendered_options}\n\n"
        "Your evaluator perspective may affect judgment, but do not "
        "invent candidate IDs.\n"
        f"Evaluator personality: {voter.personality.name}\n"
        "Evaluator guidance:\n"
        f"{voter.personality.description}\n"
        "Evaluator reasoning approach:\n"
        f"{voter.personality.answer_template}"
    )


def parse_selected_candidate_id(
    content: str,
    allowed_candidate_ids: Sequence[str],
) -> str:
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
    leaderboard = "\n".join(
        (
            f"- {agent_id}: {score}"
            for agent_id, score in context.total_scores_by_agent_id.items()
        )
    )

    winning_personalities = ", ".join(context.winning_personality_names)
    existing_personalities = ", ".join(context.existing_personality_names)

    return (
        "Create one new personality to replace an eliminated "
        "agent.\n\n"
        "The replacement should be clearly distinct from the "
        "existing successful personalities while borrowing "
        "useful strategic traits from the tournament results.\n\n"
        "Eliminated personality:\n"
        f"{context.eliminated_personality_name}\n\n"
        "Winning or high-performing personalities:\n"
        f"{winning_personalities}\n\n"
        "Existing personality names:\n"
        f"{existing_personalities}\n\n"
        "Leaderboard:\n"
        f"{leaderboard}\n\n"
        "Return exactly this JSON shape:\n"
        "{\n"
        '  "name": "short personality name",\n'
        '  "description": "one sentence description",\n'
        '  "answer_instructions": '
        '"instructions containing the literal placeholder '
        '{question}"\n'
        "}\n\n"
        "Rules:\n"
        "- The name must be unique, concise, and must not match any "
        "existing name case-insensitively.\n"
        "- The personality must have a distinct reasoning style.\n"
        "- answer_instructions must contain {question}.\n"
        "- Do not copy the eliminated personality.\n"
        "- Return only JSON."
    )


def parse_generated_personality(
    content: str,
) -> GeneratedPersonality:
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


class GroqPersonalityProvider:
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
                            "You design distinct AI agent "
                            "personalities for an evolutionary "
                            "answer tournament. Return only a "
                            "valid JSON object."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.9,
                seed=context.replacement_seed,
                max_completion_tokens=220,
                response_format={
                    "type": "json_object",
                },
            )
        except groq.APIError as error:
            raise convert_groq_error(error) from error

        content = require_message_content(completion.choices[0].message.content)

        return parse_generated_personality(content)


def get_retry_after_seconds(
    error: groq.APIStatusError,
) -> float | None:
    retry_after = error.response.headers.get("retry-after")

    if retry_after is None:
        return None

    try:
        return float(retry_after)
    except ValueError:
        return None


def _groq_error_body(error: APIStatusError) -> dict[str, Any]:
    try:
        payload = error.response.json()
    except Exception:
        return {}

    return payload if isinstance(payload, dict) else {}