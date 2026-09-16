import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import APITimeoutError, OpenAI
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.main import app
from app.rag.documents import DocumentChunk
from app.rag.embeddings import OpenAIEmbeddingService
from app.rag.retriever import LocalKnowledgeBase, RetrievalResult
from app.services.engine import AnswerEngine, _semantic_index, get_answer_engine
from app.services.generation import GeneratedAnswer, OpenAIAnswerGenerator

CHUNK = DocumentChunk(
    "shipping::chunk-1",
    "shipping",
    "Shipping",
    "shipping.md",
    "Express shipping takes 1 to 2 business days.",
)
CASES = [
    json.loads(line)
    for line in Path("data/evaluation/generation_cases.jsonl").read_text().splitlines()
]


def install_engine(monkeypatch, generated=None, results=None):
    generator = Mock()
    generator.generate.return_value = generated or GeneratedAnswer(
        answer="Express shipping takes 1 to 2 business days.",
        source_ids=[CHUNK.id],
        insufficient_context=False,
    )
    knowledge = Mock()
    knowledge.search.return_value = [RetrievalResult(CHUNK, 0.8)] if results is None else results
    engine = AnswerEngine(knowledge, generator, 0.35, 0.65)
    monkeypatch.setattr("app.services.chat.get_answer_engine", lambda: engine)
    return engine


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_generated_answers_are_validated_before_persisting(monkeypatch, case):
    generated = GeneratedAnswer.model_validate(case)
    install_engine(monkeypatch, generated)
    client = TestClient(app)
    response = client.post("/chat", json={"message": case["question"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["needs_escalation"] is not case["accepted"]
    if case["accepted"]:
        assert payload["citations"] == [CHUNK.citation]
        assert case["answer"] in payload["answer"]
    else:
        assert payload["ticket_id"]
        assert payload["citations"] == []
        assert payload["confidence"] == "low"
        assert case["answer"] not in payload["answer"]


def test_no_context_skips_generation(monkeypatch):
    engine = install_engine(monkeypatch, results=[])
    payload = TestClient(app).post("/chat", json={"message": "Repair a piano?"}).json()
    engine.generator.generate.assert_not_called()
    assert payload["ticket_id"]
    assert payload["citations"] == []


@pytest.mark.parametrize("stage", ["retrieval", "generation"])
def test_provider_timeout_escalates_and_keeps_conversation_usable(monkeypatch, stage):
    engine = install_engine(monkeypatch)
    method = engine.knowledge_base.search if stage == "retrieval" else engine.generator.generate
    method.side_effect = APITimeoutError(request=httpx.Request("POST", "https://example.test"))
    client = TestClient(app)
    payload = client.post("/chat", json={"message": "Express shipping?"}).json()
    assert payload["ticket_id"]
    assert payload["confidence"] == "low"
    assert payload["citations"] == []
    method.side_effect = None
    response = client.post(
        "/chat",
        json={
            "message": "Express shipping?",
            "conversation_id": payload["conversation_id"],
            "conversation_token": payload["conversation_token"],
        },
    )
    assert response.status_code == 200
    assert response.json()["conversation_id"] == payload["conversation_id"]


def test_history_is_bounded_and_only_from_authorized_conversation(monkeypatch):
    engine = install_engine(monkeypatch)
    client = TestClient(app)
    client.post("/chat", json={"message": "Other customer's private question"})
    first = client.post("/chat", json={"message": "Express shipping?"}).json()
    followup = {
        "conversation_id": first["conversation_id"],
        "conversation_token": first["conversation_token"],
        "message": "Can I track it?",
    }
    client.post("/chat", json=followup)
    question, _, history = engine.generator.generate.call_args.args
    assert question == "Can I track it?"
    assert len(history) == 2
    assert history[0]["content"] == "Express shipping?"
    assert "Other customer's" not in json.dumps(history)
    assert engine.knowledge_base.search.call_args.args[0] == "Express shipping?\nCan I track it?"
    monkeypatch.setattr(settings, "history_message_limit", 1)
    client.post("/chat", json=followup)
    assert len(engine.generator.generate.call_args.args[2]) == 1


def test_generation_cannot_disable_billing_escalation(monkeypatch):
    install_engine(monkeypatch)
    result = TestClient(app).post("/chat", json={"message": "I was charged twice"}).json()
    assert result["needs_escalation"]
    assert "Billing" in result["escalation_reason"]


def test_embedding_batch_order_normalization_and_semantic_search():
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        # Semantically equivalent query and source intentionally share no keywords.
        return httpx.Response(
            200,
            json={
                "object": "list",
                "model": "text-embedding-3-small",
                "data": [
                    {
                        "object": "embedding",
                        "index": index,
                        "embedding": [3.0, 4.0] if "unrelated" not in text else [4.0, -3.0],
                    }
                    for index, text in reversed(list(enumerate(body["input"])))
                ],
                "usage": {"prompt_tokens": 1, "total_tokens": 1},
            },
        )

    client = OpenAI(
        api_key="test", http_client=httpx.Client(transport=httpx.MockTransport(respond))
    )
    service = OpenAIEmbeddingService(client, "text-embedding-3-small")
    unrelated = DocumentChunk("other", "other", "Other", "other.md", "unrelated")
    knowledge = LocalKnowledgeBase([CHUNK, unrelated], service)
    results = knowledge.search("When does my parcel arrive?", min_score=0.35)
    assert [result.chunk.id for result in results] == [CHUNK.id]
    assert results[0].score == pytest.approx(1)
    assert len(requests) == 2  # one document batch, then one query
    assert len(requests[0]["input"]) == 2
    client.close()


def test_responses_sdk_parses_structured_output_and_disables_storage():
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 1,
                "model": "gpt-5.4-mini",
                "status": "completed",
                "parallel_tool_calls": False,
                "tool_choice": "auto",
                "tools": [],
                "output": [
                    {
                        "id": "msg_test",
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "answer": "One to two business days.",
                                        "source_ids": [CHUNK.id],
                                        "insufficient_context": False,
                                    }
                                ),
                                "annotations": [],
                            }
                        ],
                    }
                ],
            },
        )

    client = OpenAI(
        api_key="test", http_client=httpx.Client(transport=httpx.MockTransport(respond))
    )
    answer = OpenAIAnswerGenerator(client, "gpt-5.4-mini").generate(
        "Express shipping?", [RetrievalResult(CHUNK, 0.8)], []
    )
    assert answer.source_ids == [CHUNK.id]
    assert requests[0]["store"] is False
    assert requests[0]["text"]["format"]["type"] == "json_schema"
    assert json.loads(requests[0]["input"])["sources"][0]["id"] == CHUNK.id
    client.close()


@pytest.mark.parametrize("status,parsed", [("incomplete", None), ("completed", None)])
def test_incomplete_or_refused_provider_response_is_rejected(status, parsed):
    client = Mock()
    client.responses.parse.return_value = SimpleNamespace(status=status, output_parsed=parsed)
    with pytest.raises(ValueError):
        OpenAIAnswerGenerator(client, "test").generate("Question", [], [])


def test_semantic_index_is_cached_and_invalidated_by_content(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ai_mode", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "test")
    monkeypatch.setattr(settings, "knowledge_base_dir", tmp_path)
    document = tmp_path / "shipping.md"
    document.write_text("# Shipping\n\nShips in two days.")
    client = Mock()
    client.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(index=0, embedding=[1.0, 0.0])]
    )
    monkeypatch.setattr("app.services.engine._client", lambda *args: client)
    _semantic_index.cache_clear()
    try:
        first = get_answer_engine()
        assert first.knowledge_base is get_answer_engine().knowledge_base
        assert client.embeddings.create.call_count == 1
        document.write_text("# Shipping\n\nShips in three days.")
        assert first.knowledge_base is not get_answer_engine().knowledge_base
        assert client.embeddings.create.call_count == 2
    finally:
        _semantic_index.cache_clear()


def test_openai_mode_requires_key_and_ordered_thresholds():
    with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
        Settings(_env_file=None, ai_mode="openai", openai_api_key="")
    with pytest.raises(ValidationError, match="Semantic high score"):
        Settings(_env_file=None, semantic_min_score=0.8, semantic_high_score=0.2)


def test_evaluations_stay_offline_when_openai_is_enabled(monkeypatch):
    from app.evaluation.runner import run_evaluation

    monkeypatch.setattr(settings, "ai_mode", "openai")
    monkeypatch.setattr("app.services.engine._client", Mock(side_effect=AssertionError("Network")))
    assert run_evaluation().passed


@pytest.mark.parametrize(
    "data",
    [
        [],
        [SimpleNamespace(index=1, embedding=[1.0])],
        [SimpleNamespace(index=0, embedding=[])],
        [SimpleNamespace(index=0, embedding=[0.0, 0.0])],
        [SimpleNamespace(index=0, embedding=[float("nan")])],
    ],
)
def test_invalid_embeddings_are_rejected(data):
    client = Mock()
    client.embeddings.create.return_value = SimpleNamespace(data=data)
    with pytest.raises(ValueError):
        OpenAIEmbeddingService(client, "test").embed("Question")


def test_empty_generated_answer_is_not_delivered(monkeypatch):
    install_engine(
        monkeypatch,
        GeneratedAnswer(answer="   ", source_ids=[CHUNK.id], insufficient_context=False),
    )
    result = TestClient(app).post("/chat", json={"message": "Express shipping?"}).json()
    assert result["ticket_id"]
    assert result["citations"] == []


def test_knowledge_endpoint_uses_configured_engine_and_handles_outage(monkeypatch):
    engine = install_engine(monkeypatch)
    monkeypatch.setattr("app.api.routes.get_answer_engine", lambda: engine)
    client = TestClient(app)
    assert client.get("/knowledge/search?q=parcel").json()["results"][0]["title"] == "Shipping"
    engine.knowledge_base.search.assert_called_with("parcel", limit=3, min_score=0.35)
    engine.knowledge_base.search.side_effect = ValueError("private provider detail")
    response = client.get("/knowledge/search?q=parcel")
    assert response.status_code == 503
    assert "private provider detail" not in response.text
