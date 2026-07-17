"""Persist the population entering the next generation.

Revision ID: 0002_add_final_population_snapshot
Revises: 0001_create_game_schema
Create Date: 2026-07-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_add_final_population_snapshot"
down_revision = "0001_create_game_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store an immutable final-population snapshot for each game."""

    op.create_table(
        "game_final_agents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False),
        sa.Column("agent_name", sa.String(length=200), nullable=False),
        sa.Column(
            "personality_name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column("personality_description", sa.Text(), nullable=False),
        sa.Column("answer_template", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_id",
            "position",
            name="uq_game_final_agents_game_position",
        ),
        sa.UniqueConstraint(
            "game_id",
            "agent_id",
            name="uq_game_final_agents_game_agent",
        ),
    )
    op.create_index(
        "ix_game_final_agents_game_id",
        "game_final_agents",
        ["game_id"],
    )


def downgrade() -> None:
    """Remove final-population snapshots when explicitly requested."""

    op.drop_index(
        "ix_game_final_agents_game_id",
        table_name="game_final_agents",
    )
    op.drop_table("game_final_agents")
