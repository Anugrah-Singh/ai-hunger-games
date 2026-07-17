import asyncio

from groq import AsyncGroq

from ai_hunger_games.engine import (
    convert_candidate_scores_to_agent_scores,
    run_game,
)
from ai_hunger_games.groq_providers import (
    GroqAnswerProvider,
    GroqPersonalityProvider,
    GroqVoteProvider,
)
from ai_hunger_games.providers import (
    AnswerProvider,
    PersonalityProvider,
    SimulatedAnswerProvider,
    SimulatedPersonalityProvider,
    SimulatedVoteProvider,
    VoteProvider,
)
from ai_hunger_games.sample_data import (
    AGENTS,
    ANSWER_POLICY,
    CANDIDATE_ORDER_SEED,
    ELIMINATION_SEED,
    QUESTIONS,
    REPLACEMENT_AGENT_ID,
    REPLACEMENT_SEED,
    VOTING_SEED,
    VOTE_POLICY,
)
from ai_hunger_games.settings import (
    Settings,
    load_settings,
    require_groq_api_key,
)


def create_providers(
    settings: Settings,
) -> tuple[
    AnswerProvider,
    VoteProvider,
    PersonalityProvider,
    AsyncGroq | None,
]:
    if not settings.use_real_llm:
        return (
            SimulatedAnswerProvider(),
            SimulatedVoteProvider(),
            SimulatedPersonalityProvider(),
            None,
        )

    api_key = require_groq_api_key(settings)

    client = AsyncGroq(
        api_key=api_key,
        max_retries=0,
    )

    return (
        GroqAnswerProvider(
            client=client,
            model=settings.groq_model,
        ),
        GroqVoteProvider(
            client=client,
            model=settings.groq_model,
        ),
        GroqPersonalityProvider(
            client=client,
            model=settings.groq_model,
        ),
        client,
    )


async def main() -> None:
    settings = load_settings()

    (
        answer_provider,
        vote_provider,
        personality_provider,
        groq_client,
    ) = create_providers(settings)

    try:
        await run_and_print_game(
            answer_provider=answer_provider,
            vote_provider=vote_provider,
            personality_provider=personality_provider,
            settings=settings,
        )
    finally:
        if groq_client is not None:
            await groq_client.close()


async def run_and_print_game(
    answer_provider: AnswerProvider,
    vote_provider: VoteProvider,
    personality_provider: PersonalityProvider,
    settings: Settings,
) -> None:
    agents_by_id = {
        agent.id: agent
        for agent in AGENTS
    }

    provider_name = (
        f"Groq ({settings.groq_model})"
        if settings.use_real_llm
        else "Simulated providers"
    )

    print(f"Provider: {provider_name}")
    print()

    game_result = await run_game(
        questions=QUESTIONS,
        agents=AGENTS,
        candidate_order_seed=CANDIDATE_ORDER_SEED,
        voting_seed=VOTING_SEED,
        elimination_seed=ELIMINATION_SEED,
        replacement_seed=REPLACEMENT_SEED,
        replacement_agent_id=REPLACEMENT_AGENT_ID,
        answer_provider=answer_provider,
        answer_policy=ANSWER_POLICY,
        vote_provider=vote_provider,
        vote_policy=VOTE_POLICY,
        personality_provider=personality_provider,
    )

    for round_result in game_result.round_results:
        candidates_by_id = {
            candidate.id: candidate
            for candidate in round_result.candidates
        }

        print(f"Round {round_result.round.number}")
        print(f"Question: {round_result.round.question}")
        print()

        if round_result.failed_agent_ids:
            print("Failed agents:")

            for agent_id in round_result.failed_agent_ids:
                print(f"- {agents_by_id[agent_id].name}")

            print()

        print("Anonymous answers:")

        for candidate in round_result.candidates:
            print(
                f"\n{candidate.id}:\n"
                f"{candidate.answer.content}"
            )

        print()
        print("Votes:")

        for vote in round_result.votes:
            voter = agents_by_id[vote.voter_id]

            selected_candidate = candidates_by_id[
                vote.candidate_id
            ]

            selected_agent = agents_by_id[
                selected_candidate.answer.agent_id
            ]

            print(
                f"- {voter.name} voted for "
                f"{vote.candidate_id} "
                f"({selected_agent.name})"
            )

        round_scores = (
            convert_candidate_scores_to_agent_scores(
                round_result.candidates,
                round_result.scores_by_candidate_id,
            )
        )

        print()
        print("Round scores:")

        for agent in AGENTS:
            print(
                f"- {agent.name}: "
                f"{round_scores.get(agent.id, 0)}"
            )

        print()
        print("-" * 40)
        print()

    print("Final leaderboard:")

    for agent in AGENTS:
        score = game_result.total_scores_by_agent_id[
            agent.id
        ]

        print(f"- {agent.name}: {score}")

    eliminated_agent = agents_by_id[
        game_result.eliminated_agent_id
    ]

    replacement_personality = (
        game_result.replacement_agent.personality
    )

    print()
    print(f"Eliminated agent: {eliminated_agent.name}")

    print(
        "Replacement agent: "
        f"{game_result.replacement_agent.name}"
    )

    print(
        "Replacement description: "
        f"{replacement_personality.description}"
    )

    print(
        "Replacement answer instructions: "
        f"{replacement_personality.answer_template}"
    )

    print()
    print("Agents entering the next game:")

    for agent in game_result.final_agents:
        print(
            f"- {agent.name} "
            f"({agent.id})"
        )


if __name__ == "__main__":
    asyncio.run(main())