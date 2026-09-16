from fastapi.testclient import TestClient

from app.main import app


def test_root_serves_chat_workspace() -> None:
    client = TestClient(app)
    client.auth = ("admin", "test-admin-password")

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Grounded Support Console" in response.text


def test_admin_serves_ticket_workspace() -> None:
    client = TestClient(app)
    client.auth = ("admin", "test-admin-password")

    response = client.get("/admin")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Escalation Queue" in response.text


def test_static_assets_are_available() -> None:
    client = TestClient(app)
    client.auth = ("admin", "test-admin-password")

    response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    assert "Customer Support AI" not in response.text
