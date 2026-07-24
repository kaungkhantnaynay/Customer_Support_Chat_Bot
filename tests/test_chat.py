from fastapi.testclient import TestClient

from app.main import app


def test_chat_endpoint_returns_grounded_answer_with_citations() -> None:
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={"message": "Can I get a refund if I was charged twice?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] >= 1
    assert payload["message_id"] >= 1
    assert "Refund Policy" in payload["answer"]
    assert payload["citations"]
    assert any("Refund Policy" in citation for citation in payload["citations"])
    assert payload["confidence"] in {"high", "medium"}
    assert payload["needs_escalation"] is False


def test_chat_endpoint_refuses_when_context_is_missing() -> None:
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={"message": "Do you repair xylophones in zanzibar?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "do not have enough information" in payload["answer"]
    assert payload["citations"] == []
    assert payload["confidence"] == "low"
    assert payload["needs_escalation"] is True
    assert payload["escalation_reason"]


def test_chat_endpoint_can_continue_existing_conversation() -> None:
    client = TestClient(app)

    first_response = client.post(
        "/chat",
        json={"message": "How long does express shipping take?"},
    )
    conversation_id = first_response.json()["conversation_id"]

    second_response = client.post(
        "/chat",
        json={
            "conversation_id": conversation_id,
            "message": "Can I track the package too?",
        },
    )

    assert second_response.status_code == 200
    assert second_response.json()["conversation_id"] == conversation_id


def test_feedback_endpoint_records_customer_feedback() -> None:
    client = TestClient(app)

    chat_response = client.post(
        "/chat",
        json={"message": "How do I reset my password?"},
    )
    chat_payload = chat_response.json()

    response = client.post(
        "/feedback",
        json={
            "conversation_id": chat_payload["conversation_id"],
            "message_id": chat_payload["message_id"],
            "rating": 5,
            "comment": "Helpful answer.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["feedback_id"] >= 1
    assert payload["status"] == "recorded"


def test_chat_endpoint_validates_short_messages() -> None:
    client = TestClient(app)

    response = client.post("/chat", json={"message": "?"})

    assert response.status_code == 422
