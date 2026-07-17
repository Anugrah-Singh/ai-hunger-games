"""Create the original game persistence schema.

Revision ID: 0001_create_game_schema
Revises:
Create Date: 2026-07-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_create_game_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the schema used by the first persisted generations."""

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("generation_number", sa.Integer(), nullable=False),
        sa.Column("provider_name", sa.String(length=200), nullable=False),
        sa.Column("eliminated_agent_id", sa.String(length=100), nullable=False),
        sa.Column("replacement_agent_id", sa.String(length=100), nullable=False),
        sa.Column(
            "replacement_personality_name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column("replacement_description", sa.Text(), nullable=False),
        sa.Column(
            "replacement_answer_template",
            sa.Text(),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "game_agents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False),
        sa.Column("agent_name", sa.String(length=200), nullable=False),
        sa.Column(
            "personality_name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column("personality_description", sa.Text(), nullable=False),
        sa.Column("answer_template", sa.Text(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("was_eliminated", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_id",
            "agent_id",
            name="uq_game_agents_game_agent",
        ),
    )
    op.create_index(
        "ix_game_agents_game_id",
        "game_agents",
        ["game_id"],
    )

    op.create_table(
        "rounds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_id",
            "round_number",
            name="uq_rounds_game_round_number",
        ),
    )
    op.create_index("ix_rounds_game_id", "rounds", ["game_id"])

    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("round_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False),
        sa.Column("candidate_id", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "round_id",
            "agent_id",
            name="uq_answers_round_agent",
        ),
        sa.UniqueConstraint(
            "round_id",
            "candidate_id",
            name="uq_answers_round_candidate",
        ),
    )
    op.create_index("ix_answers_round_id", "answers", ["round_id"])

    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("round_id", sa.Integer(), nullable=False),
        sa.Column("voter_agent_id", sa.String(length=100), nullable=False),
        sa.Column(
            "selected_candidate_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "selected_agent_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "round_id",
            "voter_agent_id",
            name="uq_votes_round_voter",
        ),
    )
    op.create_index("ix_votes_round_id", "votes", ["round_id"])

    op.create_table(
        "round_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("round_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "round_id",
            "agent_id",
            name="uq_round_scores_round_agent",
        ),
    )
    op.create_index(
        "ix_round_scores_round_id",
        "round_scores",
        ["round_id"],
    )


def downgrade() -> None:
    """Protect persisted experiment history from a destructive downgrade."""

    raise RuntimeError(
        "Downgrading the initial AI Hunger Games schema is intentionally "
        "unsupported because it would delete persisted experiment history."
    )
