"""Persist randomization metadata for reproducible game runs.

Revision ID: 0005_add_game_randomization_metadata
Revises: 0004_backfill_final_population_snapshots
Create Date: 2026-07-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_add_game_randomization_metadata"
down_revision = "0004_backfill_final_population_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable metadata without inventing values for legacy rows."""

    for column_name in (
        "candidate_order_seed",
        "voting_seed",
        "elimination_seed",
        "replacement_seed",
    ):
        _add_nullable_integer_column_if_missing(column_name)


def downgrade() -> None:
    """Protect reproducibility metadata from deletion."""

    raise RuntimeError(
        "Downgrading randomization metadata is intentionally unsupported "
        "because it would delete reproducibility information."
    )


def _add_nullable_integer_column_if_missing(
    column_name: str,
) -> None:
    connection = op.get_bind()
    column_names = {
        column["name"] for column in sa.inspect(connection).get_columns("games")
    }

    if column_name not in column_names:
        op.add_column(
            "games",
            sa.Column(column_name, sa.Integer(), nullable=True),
        )
