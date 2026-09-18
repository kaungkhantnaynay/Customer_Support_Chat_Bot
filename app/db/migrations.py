from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, create_engine, inspect

ROOT = Path(__file__).resolve().parents[2]
SUPPORT_TABLES = {
    "conversation_access",
    "conversations",
    "feedback",
    "knowledge_vectors",
    "messages",
    "tickets",
}


def migration_config(connection=None):
    config = Config(str(ROOT / "alembic.ini"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def require_current_schema(engine):
    with engine.connect() as connection:
        current = set(MigrationContext.configure(connection).get_current_heads())
    expected = set(ScriptDirectory.from_config(migration_config()).get_heads())
    if current != expected:
        raise RuntimeError("Database migrations are required. Run scripts/migrate_database.py.")


def migrate(engine, adopt_legacy=False):
    with engine.begin() as connection:
        config = migration_config(connection)
        tables = set(inspect(connection).get_table_names()) - {"alembic_version"}
        support_tables = tables & SUPPORT_TABLES
        current = MigrationContext.configure(connection).get_current_heads()
        if support_tables and not current:
            if not adopt_legacy:
                raise ValueError("Unversioned database: back it up, then use --adopt-legacy.")
            # Construct the frozen baseline in a disposable database, never from evolving models.
            baseline_engine = create_engine("sqlite://")
            try:
                with baseline_engine.begin() as baseline_connection:
                    command.upgrade(migration_config(baseline_connection), "0001")
                    baseline = MetaData()
                    baseline.reflect(baseline_connection)
                    baseline.remove(baseline.tables["alembic_version"])
                context = MigrationContext.configure(connection, opts={"compare_type": True})
                differences = compare_metadata(context, baseline)
                allowed = [
                    item
                    for item in differences
                    if item[0] == "add_table" and item[1].name == "conversation_access"
                ]
                if len(allowed) != len(differences):
                    raise ValueError(
                        "Legacy schema differs from the supported baseline; not adopted."
                    )
                for item in allowed:
                    item[1].create(connection)
                command.stamp(config, "0001")
            finally:
                baseline_engine.dispose()
        command.upgrade(config, "head")
