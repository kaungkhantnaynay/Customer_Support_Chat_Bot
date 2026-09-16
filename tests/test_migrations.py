import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.db.migrations import migrate, migration_config, require_current_schema
from app.db.models import Base, Conversation
from app.db.urls import sync_database_url


@pytest.fixture
def database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    yield engine
    engine.dispose()


def test_migrations_create_schema_and_match_models(database):
    migrate(database)
    require_current_schema(database)
    with database.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    with Session(database) as session:
        conversation = Conversation()
        session.add(conversation)
        session.commit()
        assert conversation.created_at is not None
    migrate(database)


def legacy_schema(database):
    with database.begin() as connection:
        command.upgrade(migration_config(connection), "0001")
        connection.execute(text("DROP TABLE alembic_version"))
    with Session(database) as session:
        session.add(Conversation(id=100))
        session.commit()


def test_legacy_adoption_preserves_rows_and_requires_explicit_option(database):
    legacy_schema(database)
    with pytest.raises(ValueError, match="adopt-legacy"):
        migrate(database)
    migrate(database, adopt_legacy=True)
    require_current_schema(database)
    with Session(database) as session:
        assert session.get(Conversation, 100) is not None


def test_legacy_adoption_supports_missing_access_table(database):
    legacy_schema(database)
    with database.begin() as connection:
        connection.execute(text("DROP TABLE conversation_access"))
    migrate(database, adopt_legacy=True)
    assert "conversation_access" in inspect(database).get_table_names()


def test_legacy_adoption_rejects_unknown_schema_without_stamping(database):
    legacy_schema(database)
    with database.begin() as connection:
        connection.execute(text("ALTER TABLE conversations ADD COLUMN surprise TEXT"))
    with pytest.raises(ValueError, match="differs"):
        migrate(database, adopt_legacy=True)
    with database.connect() as connection:
        assert not MigrationContext.configure(connection).get_current_heads()
        assert connection.scalar(text("SELECT COUNT(*) FROM conversations")) == 1


def test_downgrade_to_baseline_preserves_support_data(database):
    migrate(database)
    with Session(database) as session:
        session.add(Conversation(id=100))
        session.commit()
    with database.begin() as connection:
        command.downgrade(migration_config(connection), "0001")
    assert "knowledge_vectors" not in inspect(database).get_table_names()
    with Session(database) as session:
        assert session.get(Conversation, 100)
    with pytest.raises(RuntimeError, match="migrations"):
        require_current_schema(database)
    migrate(database)


@pytest.mark.parametrize(
    "url,driver",
    [
        ("sqlite+aiosqlite:///data/test.db", "sqlite"),
        ("postgres://user:password@localhost/database", "postgresql+psycopg"),
        ("postgresql://user:p%25word@localhost/database", "postgresql+psycopg"),
    ],
)
def test_database_url_normalization(url, driver):
    assert sync_database_url(url).drivername == driver


def test_url_keeps_encoded_password():
    assert sync_database_url("postgresql://user:p%25word@localhost/db").password == "p%word"
