"""Enforce one persisted record for each game generation.

Revision ID: 0003_enforce_unique_game_generation
Revises: 0002_add_final_population_snapshot
Create Date: 2026-07-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_enforce_unique_game_generation"
down_revision = "0002_add_final_population_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create a unique index after verifying legacy data is valid."""

    duplicate_generation_numbers = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT generation_number "
                "FROM games "
                "GROUP BY generation_number "
                "HAVING COUNT(*) > 1"
            )
        )
        .scalars()
        .all()
    )

    if duplicate_generation_numbers:
        generations = ", ".join(
            str(generation_number) for generation_number in duplicate_generation_numbers
        )
        raise RuntimeError(
            "Cannot enforce unique game generations because duplicate "
            f"generation numbers exist: {generations}."
        )

    op.create_index(
        "uq_games_generation_number",
        "games",
        ["generation_number"],
        unique=True,
    )


def downgrade() -> None:
    """Remove the generation-number uniqueness guarantee."""

    op.drop_index(
        "uq_games_generation_number",
        table_name="games",
    )
