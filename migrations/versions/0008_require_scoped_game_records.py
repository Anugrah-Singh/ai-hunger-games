"""Require every persisted game to belong to an experiment.

Revision ID: 0008_require_scoped_game_records
Revises: 0007_add_answer_failure_telemetry
Create Date: 2026-07-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_require_scoped_game_records"
down_revision = "0007_add_answer_failure_telemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make the experiment/generation uniqueness boundary enforceable."""

    connection = op.get_bind()
    unscoped_game_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM games WHERE experiment_id IS NULL")
    ).scalar_one()

    if unscoped_game_count:
        raise RuntimeError(
            "Cannot require experiment-scoped games while "
            f"{unscoped_game_count} game records are unassigned."
        )

    if connection.dialect.name == "sqlite":
        # SQLite changes nullability by recreating the table. Alembic's
        # batch operation preserves the copied rows and existing indexes.
        with op.batch_alter_table("games", recreate="always") as batch_op:
            batch_op.alter_column(
                "experiment_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
        return

    op.alter_column(
        "games",
        "experiment_id",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    """Protect the scoped uniqueness invariant from destructive downgrade."""

    raise RuntimeError(
        "Downgrading required experiment scoping is intentionally "
        "unsupported because it weakens persisted history invariants."
    )
