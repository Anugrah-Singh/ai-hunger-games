"""Persist answer retries and partial-answer failure details.

Revision ID: 0007_add_answer_failure_telemetry
Revises: 0006_add_experiment_scoping
Create Date: 2026-07-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_add_answer_failure_telemetry"
down_revision = "0006_add_experiment_scoping"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add durable telemetry without inventing historical failures."""

    op.add_column(
        "answers",
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_table(
        "answer_failures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("round_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False),
        sa.Column("error_type", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column(
            "retry_after_seconds",
            sa.Float(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "round_id",
            "agent_id",
            name="uq_answer_failures_round_agent",
        ),
    )
    op.create_index(
        "ix_answer_failures_round_id",
        "answer_failures",
        ["round_id"],
    )


def downgrade() -> None:
    """Protect accumulated provider telemetry from destructive removal."""

    raise RuntimeError(
        "Downgrading answer failure telemetry is intentionally unsupported "
        "because it would delete historical telemetry."
    )
