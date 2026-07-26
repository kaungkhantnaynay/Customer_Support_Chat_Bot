from fastapi.testclient import TestClient

from app.main import app


def test_chat_endpoint_returns_grounded_answer_without_ticket_for_routine_question() -> None:
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={"message": "How long does express shipping take?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] >= 1
    assert payload["message_id"] >= 1
    assert payload["ticket_id"] is None
    assert "Shipping Policy" in payload["answer"]
    assert payload["citations"]
    assert any("Shipping Policy" in citation for citation in payload["citations"])
    assert payload["confidence"] in {"high", "medium"}
    assert payload["needs_escalation"] is False


def test_chat_endpoint_creates_ticket_for_duplicate_billing() -> None:
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={"message": "Can I get a refund if I was charged twice?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "Refund Policy" in payload["answer"]
    assert payload["ticket_id"] >= 1
    assert payload["needs_escalation"] is True
    assert payload["escalation_reason"] == "Billing or refund issue requires human review."

    ticket_response = client.get(f"/admin/tickets/{payload['ticket_id']}")

    assert ticket_response.status_code == 200
    ticket = ticket_response.json()
    assert ticket["priority"] == "high"
    assert ticket["assigned_team"] == "billing"
    assert ticket["status"] == "open"
    assert ticket["conversation_id"] == payload["conversation_id"]


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
    assert payload["ticket_id"] >= 1
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


def test_admin_can_list_and_update_tickets() -> None:
    client = TestClient(app)

    chat_response = client.post(
        "/chat",
        json={"message": "I am angry that my payment was charged twice."},
    )
    ticket_id = chat_response.json()["ticket_id"]

    list_response = client.get("/admin/tickets", params={"status": "open"})

    assert list_response.status_code == 200
    tickets = list_response.json()["tickets"]
    assert any(ticket["id"] == ticket_id for ticket in tickets)

    update_response = client.patch(
        f"/admin/tickets/{ticket_id}",
        json={"status": "in_progress", "assigned_team": "billing_specialists"},
    )

    assert update_response.status_code == 200
    updated_ticket = update_response.json()
    assert updated_ticket["status"] == "in_progress"
    assert updated_ticket["assigned_team"] == "billing_specialists"


def test_admin_ticket_detail_returns_404_for_missing_ticket() -> None:
    client = TestClient(app)

    response = client.get("/admin/tickets/999999")

    assert response.status_code == 404
