"""Backfill final-population snapshots for historical generations.

Revision ID: 0004_backfill_final_population_snapshots
Revises: 0003_enforce_unique_game_generation
Create Date: 2026-07-17
"""

from collections.abc import Mapping

import sqlalchemy as sa
from alembic import op

revision = "0004_backfill_final_population_snapshots"
down_revision = "0003_enforce_unique_game_generation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Reconstruct snapshots from immutable legacy game records."""

    connection = op.get_bind()
    games = connection.execute(
        sa.text(
            "SELECT "
            "id, "
            "eliminated_agent_id, "
            "replacement_agent_id, "
            "replacement_personality_name, "
            "replacement_description, "
            "replacement_answer_template "
            "FROM games "
            "ORDER BY id"
        )
    ).mappings()

    for game in games:
        starting_agents = list(
            connection.execute(
                sa.text(
                    "SELECT "
                    "agent_id, "
                    "agent_name, "
                    "personality_name, "
                    "personality_description, "
                    "answer_template "
                    "FROM game_agents "
                    "WHERE game_id = :game_id "
                    "ORDER BY id"
                ),
                {"game_id": game["id"]},
            ).mappings()
        )

        existing_snapshot_count = connection.execute(
            sa.text("SELECT COUNT(*) FROM game_final_agents WHERE game_id = :game_id"),
            {"game_id": game["id"]},
        ).scalar_one()

        if existing_snapshot_count:
            _validate_existing_snapshot(
                connection=connection,
                game=game,
                starting_agents=starting_agents,
            )
            continue

        position = 1
        eliminated_agent_found = False

        for agent in starting_agents:
            if agent["agent_id"] == game["eliminated_agent_id"]:
                eliminated_agent_found = True
                continue

            _insert_snapshot(
                connection=connection,
                game_id=game["id"],
                position=position,
                agent_id=agent["agent_id"],
                agent_name=agent["agent_name"],
                personality_name=agent["personality_name"],
                personality_description=(agent["personality_description"]),
                answer_template=agent["answer_template"],
            )
            position += 1

        if not eliminated_agent_found:
            raise RuntimeError(
                "Cannot reconstruct the final population for game "
                f"{game['id']} because its eliminated agent is missing "
                "from game_agents."
            )

        _insert_snapshot(
            connection=connection,
            game_id=game["id"],
            position=position,
            agent_id=game["replacement_agent_id"],
            agent_name=game["replacement_personality_name"],
            personality_name=game["replacement_personality_name"],
            personality_description=game["replacement_description"],
            answer_template=game["replacement_answer_template"],
        )


def _validate_existing_snapshot(
    connection: sa.Connection,
    game: Mapping[str, object],
    starting_agents: list[Mapping[str, object]],
) -> None:
    """Fail instead of treating a partial prior snapshot as authoritative."""

    expected_rows: list[dict[str, object]] = []
    eliminated_agent_found = False

    for agent in starting_agents:
        if agent["agent_id"] == game["eliminated_agent_id"]:
            eliminated_agent_found = True
            continue

        expected_rows.append(
            {
                "agent_id": agent["agent_id"],
                "agent_name": agent["agent_name"],
                "personality_name": agent["personality_name"],
                "personality_description": agent["personality_description"],
                "answer_template": agent["answer_template"],
            }
        )

    if not eliminated_agent_found:
        raise RuntimeError(
            "Cannot validate the final population for game "
            f"{game['id']} because its eliminated agent is missing "
            "from game_agents."
        )

    expected_rows.append(
        {
            "agent_id": game["replacement_agent_id"],
            "agent_name": game["replacement_personality_name"],
            "personality_name": game["replacement_personality_name"],
            "personality_description": game["replacement_description"],
            "answer_template": game["replacement_answer_template"],
        }
    )
    actual_rows = list(
        connection.execute(
            sa.text(
                "SELECT "
                "position, "
                "agent_id, "
                "agent_name, "
                "personality_name, "
                "personality_description, "
                "answer_template "
                "FROM game_final_agents "
                "WHERE game_id = :game_id "
                "ORDER BY position"
            ),
            {"game_id": game["id"]},
        ).mappings()
    )

    if len(actual_rows) != len(expected_rows):
        raise RuntimeError(
            "Final-population snapshot for game "
            f"{game['id']} is incomplete: expected "
            f"{len(expected_rows)} rows, found {len(actual_rows)}."
        )

    fields = (
        "agent_id",
        "agent_name",
        "personality_name",
        "personality_description",
        "answer_template",
    )

    for position, (actual, expected) in enumerate(
        zip(actual_rows, expected_rows),
        start=1,
    ):
        if actual["position"] != position or any(
            actual[field] != expected[field] for field in fields
        ):
            raise RuntimeError(
                "Final-population snapshot for game "
                f"{game['id']} disagrees with its immutable game records."
            )


def downgrade() -> None:
    """Protect reconstructed historical snapshots from deletion."""

    raise RuntimeError(
        "Downgrading final-population backfill is intentionally "
        "unsupported because it would delete historical snapshots."
    )


def _insert_snapshot(
    connection: sa.Connection,
    game_id: int,
    position: int,
    agent_id: str,
    agent_name: str,
    personality_name: str,
    personality_description: str,
    answer_template: str,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO game_final_agents ("
            "game_id, "
            "position, "
            "agent_id, "
            "agent_name, "
            "personality_name, "
            "personality_description, "
            "answer_template"
            ") VALUES ("
            ":game_id, "
            ":position, "
            ":agent_id, "
            ":agent_name, "
            ":personality_name, "
            ":personality_description, "
            ":answer_template"
            ")"
        ),
        {
            "game_id": game_id,
            "position": position,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "personality_name": personality_name,
            "personality_description": personality_description,
            "answer_template": answer_template,
        },
    )
