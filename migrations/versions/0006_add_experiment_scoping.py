"""Scope generations to durable experiment records.

Revision ID: 0006_add_experiment_scoping
Revises: 0005_add_game_randomization_metadata
Create Date: 2026-07-17
"""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0006_add_experiment_scoping"
down_revision = "0005_add_game_randomization_metadata"
branch_labels = None
depends_on = None


LEGACY_EXPERIMENT_NAME = "Imported legacy history"
OLD_GENERATION_INDEX_NAME = "uq_games_generation_number"
EXPERIMENT_GENERATION_INDEX_NAME = "uq_games_experiment_generation_number"
EXPERIMENT_ID_INDEX_NAME = "ix_games_experiment_id"


def upgrade() -> None:
    """Create experiments and assign all existing games to one import."""

    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_experiments_name"),
    )

    _add_experiment_id_column()
    op.create_index(
        EXPERIMENT_ID_INDEX_NAME,
        "games",
        ["experiment_id"],
    )

    _assign_existing_games_to_legacy_experiment()
    _replace_global_generation_index()


def downgrade() -> None:
    """Protect experiment history from destructive downgrade."""

    raise RuntimeError(
        "Downgrading experiment scoping is intentionally unsupported "
        "because it would merge or delete experiment history."
    )


def _assign_existing_games_to_legacy_experiment() -> None:
    connection = op.get_bind()
    game_count = connection.execute(sa.text("SELECT COUNT(*) FROM games")).scalar_one()

    if not game_count:
        return

    connection.execute(
        sa.text(
            "INSERT INTO experiments (name, created_at) VALUES (:name, :created_at)"
        ),
        {
            "name": LEGACY_EXPERIMENT_NAME,
            # Raw SQL text bypasses SQLAlchemy's SQLite DateTime binder.
            # Store an explicit ISO-8601 value instead of relying on
            # Python's deprecated sqlite3 datetime adapter.
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    experiment_id = connection.execute(
        sa.text("SELECT id FROM experiments WHERE name = :name"),
        {"name": LEGACY_EXPERIMENT_NAME},
    ).scalar_one_or_none()

    if experiment_id is None:
        raise RuntimeError(
            "Could not create the experiment used to import legacy games."
        )

    connection.execute(
        sa.text(
            "UPDATE games "
            "SET experiment_id = :experiment_id "
            "WHERE experiment_id IS NULL"
        ),
        {"experiment_id": experiment_id},
    )

    unassigned_game_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM games WHERE experiment_id IS NULL")
    ).scalar_one()

    if unassigned_game_count:
        raise RuntimeError("Could not assign every legacy game to an experiment.")


def _add_experiment_id_column() -> None:
    connection = op.get_bind()

    if connection.dialect.name == "sqlite":
        # SQLite supports an inline REFERENCES clause in ADD COLUMN, but it
        # cannot add the same foreign key later as a separate constraint.
        op.execute(
            "ALTER TABLE games "
            "ADD COLUMN experiment_id INTEGER "
            "REFERENCES experiments(id)"
        )
        return

    op.add_column(
        "games",
        sa.Column(
            "experiment_id",
            sa.Integer(),
            sa.ForeignKey("experiments.id"),
            nullable=True,
        ),
    )


def _replace_global_generation_index() -> None:
    connection = op.get_bind()
    index_names = {
        index["name"] for index in sa.inspect(connection).get_indexes("games")
    }

    op.create_index(
        EXPERIMENT_GENERATION_INDEX_NAME,
        "games",
        ["experiment_id", "generation_number"],
        unique=True,
    )

    if OLD_GENERATION_INDEX_NAME in index_names:
        op.drop_index(OLD_GENERATION_INDEX_NAME, table_name="games")
