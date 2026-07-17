"""Snapshot runnable experiment inputs and provider identity.

Revision ID: 0009_snapshot_experiment_definitions
Revises: 0008_require_scoped_game_records
Create Date: 2026-07-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_snapshot_experiment_definitions"
down_revision = "0008_require_scoped_game_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add immutable setup snapshots for all newly created experiments."""

    op.add_column(
        "experiments",
        sa.Column(
            "provider_name",
            sa.String(length=200),
            nullable=True,
        ),
    )
    op.create_table(
        "experiment_configurations",
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("questions_json", sa.Text(), nullable=False),
        sa.Column("candidate_order_seed", sa.Integer(), nullable=False),
        sa.Column("voting_seed", sa.Integer(), nullable=False),
        sa.Column("elimination_seed", sa.Integer(), nullable=False),
        sa.Column("replacement_seed", sa.Integer(), nullable=False),
        sa.Column("seed_stride", sa.Integer(), nullable=False),
        sa.Column("answer_timeout_seconds", sa.Float(), nullable=False),
        sa.Column(
            "answer_minimum_successful_answers",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "answer_maximum_attempts",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "answer_initial_retry_delay_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "answer_maximum_retry_delay_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "answer_maximum_concurrent_requests",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column("vote_timeout_seconds", sa.Float(), nullable=False),
        sa.Column("vote_maximum_attempts", sa.Integer(), nullable=False),
        sa.Column(
            "vote_initial_retry_delay_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "vote_maximum_retry_delay_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "personality_timeout_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "personality_maximum_attempts",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "personality_initial_retry_delay_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "personality_maximum_retry_delay_seconds",
            sa.Float(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("experiment_id"),
    )
    op.create_table(
        "experiment_initial_agents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
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
            ["experiment_id"],
            ["experiments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "experiment_id",
            "position",
            name="uq_experiment_initial_agents_position",
        ),
        sa.UniqueConstraint(
            "experiment_id",
            "agent_id",
            name="uq_experiment_initial_agents_agent",
        ),
    )
    op.create_index(
        "ix_experiment_initial_agents_experiment_id",
        "experiment_initial_agents",
        ["experiment_id"],
    )


def downgrade() -> None:
    """Keep experiment setup snapshots durable once they exist."""

    raise RuntimeError(
        "Downgrading experiment setup snapshots is intentionally "
        "unsupported because it would discard reproducibility data."
    )
