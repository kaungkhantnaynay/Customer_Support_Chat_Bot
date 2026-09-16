import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.mark.parametrize("path", ["/admin", "/admin/tickets", "/admin/tickets/1"])
def test_admin_requires_credentials(path):
    client = TestClient(app)
    assert client.get(path).status_code == 401
    assert client.get(path, auth=("admin", "incorrect")).status_code == 401


def test_admin_update_requires_credentials():
    assert TestClient(app).patch("/admin/tickets/1", json={"status": "closed"}).status_code == 401


def test_unconfigured_admin_is_disabled(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "")
    assert TestClient(app).get("/admin").status_code == 503


def test_conversation_access_and_feedback_validation():
    client = TestClient(app)
    first = client.post("/chat", json={"message": "Shipping time?"}).json()
    second = client.post("/chat", json={"message": "Shipping time?"}).json()
    for token in [None, "incorrect", second["conversation_token"]]:
        payload = {"conversation_id": first["conversation_id"], "conversation_token": token}
        assert (
            client.post("/chat", json={**payload, "message": "Track shipping?"}).status_code == 403
        )
        assert client.post("/feedback", json={**payload, "rating": 5}).status_code == 403
    payload = {
        "conversation_id": first["conversation_id"],
        "conversation_token": first["conversation_token"],
        "rating": 5,
    }
    for message_id in [second["message_id"], first["message_id"] - 1, 999999]:
        assert (
            client.post("/feedback", json={**payload, "message_id": message_id}).status_code == 422
        )
    assert (
        client.post("/feedback", json={**payload, "message_id": first["message_id"]}).status_code
        == 200
    )


def test_missing_conversation_cannot_be_continued():
    assert (
        TestClient(app)
        .post(
            "/chat",
            json={
                "message": "Shipping time?",
                "conversation_id": 999999,
                "conversation_token": "invalid",
            },
        )
        .status_code
        == 403
    )
