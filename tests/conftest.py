import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.models import Base
from app.db.session import get_session
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database_and_admin(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "test-admin-password")
    monkeypatch.setattr(settings, "ai_mode", "offline")
    monkeypatch.setattr(settings, "vector_store", "local")
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    yield
    app.dependency_overrides.pop(get_session, None)
    engine.dispose()
