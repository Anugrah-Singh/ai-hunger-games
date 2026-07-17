from ai_hunger_games.engine import (
    convert_candidate_scores_to_agent_scores,
)
from ai_hunger_games.generations import PersistedGenerationResult
from ai_hunger_games.models import Agent


def render_generation_result(
    result: PersistedGenerationResult,
) -> str:
    """Render a completed generation after all votes have been recorded."""

    game_result = result.game_result
    agents_by_id = {agent.id: agent for agent in result.starting_agents}
    lines = [
        f"Saved generation: {result.generation_number}",
        f"Database game ID: {result.game_id}",
        "",
    ]

    for round_result in game_result.round_results:
        candidates_by_id = {
            candidate.id: candidate for candidate in round_result.candidates
        }

        lines.extend(
            [
                f"Round {round_result.round.number}",
                f"Question: {round_result.round.question}",
                "",
            ]
        )

        if round_result.failed_agent_ids:
            lines.append("Failed agents:")
            lines.extend(
                f"- {_agent_name(agent_id, agents_by_id)}"
                for agent_id in round_result.failed_agent_ids
            )
            lines.append("")

        lines.append("Anonymous answers:")

        for candidate in round_result.candidates:
            lines.extend(
                [
                    f"{candidate.id}:",
                    candidate.answer.content,
                    "",
                ]
            )

        lines.append("Votes:")

        for vote in round_result.votes:
            selected_candidate = candidates_by_id[vote.candidate_id]
            lines.append(
                "- "
                f"{_agent_name(vote.voter_id, agents_by_id)} voted for "
                f"{vote.candidate_id} "
                "("
                f"{_agent_name(selected_candidate.answer.agent_id, agents_by_id)}"
                ")"
            )

        round_scores = convert_candidate_scores_to_agent_scores(
            round_result.candidates,
            round_result.scores_by_candidate_id,
        )
        lines.extend(["", "Round scores:"])
        lines.extend(
            f"- {agent.name}: {round_scores.get(agent.id, 0)}"
            for agent in result.starting_agents
        )
        lines.extend(["", "-" * 40, ""])

    lines.append("Final leaderboard:")
    lines.extend(
        f"- {agent.name}: {game_result.total_scores_by_agent_id[agent.id]}"
        for agent in result.starting_agents
    )

    eliminated_agent = agents_by_id[game_result.eliminated_agent_id]
    replacement_personality = game_result.replacement_agent.personality
    lines.extend(
        [
            "",
            f"Eliminated agent: {eliminated_agent.name}",
            f"Replacement agent: {game_result.replacement_agent.name}",
            f"Replacement description: {replacement_personality.description}",
            "Replacement answer instructions: "
            f"{replacement_personality.answer_template}",
            "",
            "Agents entering the next game:",
        ]
    )
    lines.extend(f"- {agent.name} ({agent.id})" for agent in game_result.final_agents)

    return "\n".join(lines)


def _agent_name(
    agent_id: str,
    agents_by_id: dict[str, Agent],
) -> str:
    agent = agents_by_id.get(agent_id)

    if agent is None:
        return agent_id

    return agent.name
