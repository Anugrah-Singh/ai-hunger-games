import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import AsyncEngine

from ai_hunger_games.database import (
    raise_if_sqlite_foreign_keys_are_invalid,
    set_sqlite_foreign_keys,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"
LEGACY_BASELINE_REVISION = "0001_create_game_schema"
LEGACY_FINAL_POPULATION_REVISION = "0002_add_final_population_snapshot"
LEGACY_GENERATION_INDEX_REVISION = "0003_enforce_unique_game_generation"
LEGACY_RANDOMIZATION_REVISION = "0005_add_game_randomization_metadata"
LEGACY_GENERATION_INDEX_NAME = "uq_games_generation_number"
LEGACY_TABLE_COLUMNS = {
    "games": {
        "id",
        "generation_number",
        "provider_name",
        "eliminated_agent_id",
        "replacement_agent_id",
        "replacement_personality_name",
        "replacement_description",
        "replacement_answer_template",
        "created_at",
    },
    "game_agents": {
        "id",
        "game_id",
        "agent_id",
        "agent_name",
        "personality_name",
        "personality_description",
        "answer_template",
        "total_score",
        "was_eliminated",
    },
    "rounds": {
        "id",
        "game_id",
        "round_number",
        "question",
    },
    "answers": {
        "id",
        "round_id",
        "agent_id",
        "candidate_id",
        "content",
    },
    "votes": {
        "id",
        "round_id",
        "voter_agent_id",
        "selected_candidate_id",
        "selected_agent_id",
    },
    "round_scores": {
        "id",
        "round_id",
        "agent_id",
        "score",
    },
}
LEGACY_OPTIONAL_TABLE_COLUMNS = {
    "games": {
        "candidate_order_seed",
        "voting_seed",
        "elimination_seed",
        "replacement_seed",
    },
}
LEGACY_FINAL_AGENT_COLUMNS = {
    "id",
    "game_id",
    "position",
    "agent_id",
    "agent_name",
    "personality_name",
    "personality_description",
    "answer_template",
}
SQLITE_INTERNAL_TABLE_NAMES = {"sqlite_sequence"}


async def initialize_database(
    engine: AsyncEngine,
) -> None:
    # Alembic owns the migration transaction. Keeping an outer transaction
    # open would prevent SQLite from changing foreign-key enforcement around
    # a batch table rebuild.
    async with engine.connect() as connection:
        await connection.run_sync(
            _upgrade_database,
            str(engine.url),
        )


def _upgrade_database(
    connection: Connection,
    database_url: str,
) -> None:
    config = Config(str(ALEMBIC_CONFIG_PATH))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["connection"] = connection

    is_sqlite = connection.dialect.name == "sqlite"

    if is_sqlite:
        # Alembic documents that a SQLite batch migration cannot safely drop
        # a referenced table while FK enforcement is enabled. The driver
        # cursor runs before Alembic starts its transaction, unlike a normal
        # SQLAlchemy execute which would implicitly begin one first.
        set_sqlite_foreign_keys(connection, enabled=False)

    try:
        legacy_revision = _detect_unversioned_legacy_sqlite_revision(database_url)

        if legacy_revision is not None:
            command.stamp(config, legacy_revision)

        command.upgrade(config, "head")

        if connection.in_transaction():
            connection.commit()

        if is_sqlite:
            raise_if_sqlite_foreign_keys_are_invalid(connection)
    except Exception:
        if connection.in_transaction():
            connection.rollback()
        raise
    finally:
        if is_sqlite:
            set_sqlite_foreign_keys(connection, enabled=True)


def _detect_unversioned_legacy_sqlite_revision(
    database_url: str,
) -> str | None:
    database_url_parts = make_url(database_url)

    if database_url_parts.get_backend_name() != "sqlite":
        return None

    database_name = database_url_parts.database

    if database_name in (None, ":memory:"):
        return None

    database_path = Path(database_name)

    if not database_path.exists():
        return None

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        if "alembic_version" in table_names:
            return None

        allowed_table_names = {
            *LEGACY_TABLE_COLUMNS,
            "game_final_agents",
            *SQLITE_INTERNAL_TABLE_NAMES,
        }
        unexpected_table_names = table_names - allowed_table_names

        if unexpected_table_names:
            unexpected_tables = ", ".join(sorted(unexpected_table_names))
            raise RuntimeError(
                "Found an unversioned AI Hunger Games schema with "
                "unexpected tables. Refusing to stamp it because its "
                f"history is ambiguous: {unexpected_tables}."
            )

        legacy_table_names = set(LEGACY_TABLE_COLUMNS)
        found_legacy_table_names = legacy_table_names & table_names

        if not found_legacy_table_names:
            return None

        missing_table_names = legacy_table_names - found_legacy_table_names

        if missing_table_names:
            missing_tables = ", ".join(sorted(missing_table_names))
            raise RuntimeError(
                "Found an unversioned partial AI Hunger Games schema. "
                "Refusing to stamp it because these expected tables are "
                f"missing: {missing_tables}."
            )

        _validate_legacy_table_columns(connection)

        return _legacy_revision_for_schema(
            connection,
            table_names,
        )


def _legacy_revision_for_schema(
    connection: sqlite3.Connection,
    table_names: set[str],
) -> str:
    game_column_names = {
        row[1] for row in connection.execute("PRAGMA table_info(games)")
    }
    randomization_column_names = LEGACY_OPTIONAL_TABLE_COLUMNS["games"]
    found_randomization_columns = game_column_names & randomization_column_names

    if (
        found_randomization_columns
        and found_randomization_columns != randomization_column_names
    ):
        missing_columns = ", ".join(
            sorted(randomization_column_names - found_randomization_columns)
        )
        raise RuntimeError(
            "Found an unversioned partial randomization migration. "
            f"Missing columns: {missing_columns}."
        )

    index_names = {row[1] for row in connection.execute("PRAGMA index_list(games)")}
    has_final_population_table = "game_final_agents" in table_names
    has_generation_index = LEGACY_GENERATION_INDEX_NAME in index_names

    if not has_final_population_table:
        if found_randomization_columns or has_generation_index:
            raise RuntimeError(
                "Found an unversioned schema with migration artifacts "
                "that require game_final_agents. Refusing to infer a "
                "safe Alembic revision."
            )

        return LEGACY_BASELINE_REVISION

    if found_randomization_columns:
        if not has_generation_index:
            raise RuntimeError(
                "Found unversioned randomization columns without the "
                "required game generation index."
            )

        return LEGACY_RANDOMIZATION_REVISION

    if has_generation_index:
        # Revision 0004 changed data only. Stamping 0003 lets its
        # idempotent backfill run before later schema migrations.
        return LEGACY_GENERATION_INDEX_REVISION

    return LEGACY_FINAL_POPULATION_REVISION


def _validate_legacy_table_columns(
    connection: sqlite3.Connection,
) -> None:
    for table_name, expected_column_names in LEGACY_TABLE_COLUMNS.items():
        actual_column_names = {
            row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")
        }
        missing_column_names = expected_column_names - actual_column_names

        if missing_column_names:
            missing_columns = ", ".join(sorted(missing_column_names))
            raise RuntimeError(
                f"Cannot stamp legacy table '{table_name}' because "
                f"these columns are missing: {missing_columns}."
            )

        optional_column_names = LEGACY_OPTIONAL_TABLE_COLUMNS.get(
            table_name,
            set(),
        )
        unexpected_column_names = actual_column_names - (
            expected_column_names | optional_column_names
        )

        if unexpected_column_names:
            unexpected_columns = ", ".join(sorted(unexpected_column_names))
            raise RuntimeError(
                f"Cannot stamp legacy table '{table_name}' because "
                f"these columns are not recognized: {unexpected_columns}."
            )

    table_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }

    if "game_final_agents" not in table_names:
        return

    final_agent_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(game_final_agents)")
    }
    missing_final_agent_columns = LEGACY_FINAL_AGENT_COLUMNS - final_agent_columns
    unexpected_final_agent_columns = final_agent_columns - LEGACY_FINAL_AGENT_COLUMNS

    if missing_final_agent_columns or unexpected_final_agent_columns:
        details: list[str] = []

        if missing_final_agent_columns:
            details.append("missing " + ", ".join(sorted(missing_final_agent_columns)))

        if unexpected_final_agent_columns:
            details.append(
                "unrecognized " + ", ".join(sorted(unexpected_final_agent_columns))
            )

        raise RuntimeError(
            "Cannot stamp legacy table 'game_final_agents' because it "
            + "; ".join(details)
            + "."
        )
