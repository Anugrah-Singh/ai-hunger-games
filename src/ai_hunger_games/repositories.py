from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_hunger_games.db_models import (
    AnswerRecord,
    GameAgentRecord,
    GameRecord,
    RoundRecord,
    RoundScoreRecord,
    VoteRecord,
)
from ai_hunger_games.engine import (
    convert_candidate_scores_to_agent_scores,
)
from ai_hunger_games.models import (
    Agent,
    GameResult,
)


class GameRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_next_generation_number(self) -> int:
        statement = select(
            func.coalesce(
                func.max(GameRecord.generation_number),
                0,
            )
        )

        result = await self.session.execute(statement)
        current_generation = result.scalar_one()

        return current_generation + 1

    async def save_game(
        self,
        game_result: GameResult,
        original_agents: list[Agent],
        provider_name: str,
    ) -> GameRecord:
        generation_number = (
            await self.get_next_generation_number()
        )

        replacement_personality = (
            game_result.replacement_agent.personality
        )

        game_record = GameRecord(
            generation_number=generation_number,
            provider_name=provider_name,
            eliminated_agent_id=(
                game_result.eliminated_agent_id
            ),
            replacement_agent_id=(
                game_result.replacement_agent.id
            ),
            replacement_personality_name=(
                replacement_personality.name
            ),
            replacement_description=(
                replacement_personality.description
            ),
            replacement_answer_template=(
                replacement_personality.answer_template
            ),
        )

        self.session.add(game_record)

        await self.session.flush()

        self._add_agent_snapshots(
            game_record=game_record,
            game_result=game_result,
            original_agents=original_agents,
        )

        await self._add_rounds(
            game_record=game_record,
            game_result=game_result,
            original_agents=original_agents,
        )

        await self.session.commit()
        await self.session.refresh(game_record)

        return game_record

    def _add_agent_snapshots(
        self,
        game_record: GameRecord,
        game_result: GameResult,
        original_agents: list[Agent],
    ) -> None:
        for agent in original_agents:
            personality = agent.personality

            self.session.add(
                GameAgentRecord(
                    game_id=game_record.id,
                    agent_id=agent.id,
                    agent_name=agent.name,
                    personality_name=personality.name,
                    personality_description=(
                        personality.description
                    ),
                    answer_template=(
                        personality.answer_template
                    ),
                    total_score=(
                        game_result
                        .total_scores_by_agent_id[
                            agent.id
                        ]
                    ),
                    was_eliminated=(
                        agent.id
                        == game_result.eliminated_agent_id
                    ),
                )
            )

    async def _add_rounds(
        self,
        game_record: GameRecord,
        game_result: GameResult,
        original_agents: list[Agent],
    ) -> None:
        agent_ids = {
            agent.id
            for agent in original_agents
        }

        for round_result in game_result.round_results:
            round_record = RoundRecord(
                game_id=game_record.id,
                round_number=round_result.round.number,
                question=round_result.round.question,
            )

            self.session.add(round_record)
            await self.session.flush()

            candidates_by_id = {
                candidate.id: candidate
                for candidate in round_result.candidates
            }

            for candidate in round_result.candidates:
                self.session.add(
                    AnswerRecord(
                        round_id=round_record.id,
                        agent_id=(
                            candidate.answer.agent_id
                        ),
                        candidate_id=candidate.id,
                        content=candidate.answer.content,
                    )
                )

            for vote in round_result.votes:
                selected_candidate = candidates_by_id[
                    vote.candidate_id
                ]

                self.session.add(
                    VoteRecord(
                        round_id=round_record.id,
                        voter_agent_id=vote.voter_id,
                        selected_candidate_id=(
                            vote.candidate_id
                        ),
                        selected_agent_id=(
                            selected_candidate
                            .answer
                            .agent_id
                        ),
                    )
                )

            round_scores = (
                convert_candidate_scores_to_agent_scores(
                    round_result.candidates,
                    round_result.scores_by_candidate_id,
                )
            )

            for agent_id in agent_ids:
                self.session.add(
                    RoundScoreRecord(
                        round_id=round_record.id,
                        agent_id=agent_id,
                        score=round_scores.get(
                            agent_id,
                            0,
                        ),
                    )
                )