"""Persist asynchronous generation-run status.

Revision ID: 0011_add_generation_runs
Revises: 0010_enforce_experiment_name_uniqueness
Create Date: 2026-07-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_add_generation_runs"
down_revision = "0010_enforce_experiment_name_uniqueness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create durable records for background generation execution."""

    op.create_table(
        "generation_runs",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "experiment_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "generation_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "game_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_generation_runs_status",
        ),
    )

    op.create_index(
        "ix_generation_runs_experiment_id",
        "generation_runs",
        ["experiment_id"],
    )

    op.create_index(
        "ix_generation_runs_status",
        "generation_runs",
        ["status"],
    )

    op.create_index(
        "ix_generation_runs_game_id",
        "generation_runs",
        ["game_id"],
    )

    op.create_index(
        "uq_generation_runs_active_experiment",
        "generation_runs",
        ["experiment_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('queued', 'running')"),
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    """Protect persisted run history from destructive downgrade."""

    raise RuntimeError(
        "Downgrading generation-run persistence is intentionally "
        "unsupported because it would delete execution history."
    )
