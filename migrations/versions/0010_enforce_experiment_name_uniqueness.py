"""Repair experiment-name uniqueness in historically stamped SQLite databases.

Revision ID: 0010_enforce_experiment_name_uniqueness
Revises: 0009_snapshot_experiment_definitions
Create Date: 2026-07-18
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_enforce_experiment_name_uniqueness"
down_revision = "0009_snapshot_experiment_definitions"
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "uq_experiments_name"


def upgrade() -> None:
    """Ensure the persisted experiment-name boundary exists exactly once."""

    connection = op.get_bind()

    if _has_name_uniqueness_constraint(connection):
        return

    duplicates = connection.execute(
        sa.text(
            "SELECT name, COUNT(*) AS occurrence_count "
            "FROM experiments "
            "GROUP BY name "
            "HAVING COUNT(*) > 1 "
            "ORDER BY name"
        )
    ).all()

    if duplicates:
        names = ", ".join(f"{name!r} ({count})" for name, count in duplicates)
        raise RuntimeError(
            "Cannot enforce unique experiment names while duplicate "
            f"records exist: {names}."
        )

    if connection.dialect.name == "sqlite":
        # SQLite adds table constraints by rebuilding the table. Alembic's
        # migration environment disables FK enforcement only for that rebuild
        # and validates every relationship before re-enabling it.
        with op.batch_alter_table("experiments", recreate="always") as batch_op:
            batch_op.create_unique_constraint(CONSTRAINT_NAME, ["name"])
        return

    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "experiments",
        ["name"],
    )


def downgrade() -> None:
    """Prevent removal of a data-integrity boundary from experiment history."""

    raise RuntimeError(
        "Downgrading experiment-name uniqueness is intentionally unsupported."
    )


def _has_name_uniqueness_constraint(
    connection: sa.Connection,
) -> bool:
    constraints = sa.inspect(connection).get_unique_constraints("experiments")
    return any(constraint["column_names"] == ["name"] for constraint in constraints)
