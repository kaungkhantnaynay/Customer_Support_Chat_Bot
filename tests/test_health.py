from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_session
from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_checks_database() -> None:
    executed = False

    def track_execute(statement):
        nonlocal executed
        executed = str(statement) == str(text("SELECT 1"))

    class SessionStub:
        execute = staticmethod(track_execute)

    app.dependency_overrides[get_session] = lambda: SessionStub()
    try:
        assert TestClient(app).get("/health").status_code == 200
        assert executed
    finally:
        app.dependency_overrides.pop(get_session, None)
