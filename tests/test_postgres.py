"""Run against a dedicated disposable database using TEST_POSTGRES_URL."""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.migrations import migrate, require_current_schema
from app.rag.documents import DocumentChunk
from app.rag.postgres import PostgresKnowledgeBase, dense_vector, snapshot_id
from app.rag.retriever import LocalKnowledgeBase
from app.schemas.chat import ChatRequest
from app.services.chat import ChatService
from app.services.engine import AnswerEngine

CHUNKS = [
    DocumentChunk("shipping::1", "shipping", "Shipping", "shipping.md", "Delivery in two days."),
    DocumentChunk("refund::1", "refund", "Refund", "refund.md", "Refund within thirty days."),
]


@pytest.fixture
def postgres():
    url = os.environ.get("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set TEST_POSTGRES_URL to a dedicated disposable PostgreSQL database.")
    engine = create_engine(url, pool_pre_ping=True)
    migrate(engine)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM knowledge_vectors"))
    yield engine
    engine.dispose()


def test_postgres_migrations_and_chat_persistence(postgres):
    require_current_schema(postgres)
    with Session(postgres) as session:
        service = ChatService(
            session, AnswerEngine(LocalKnowledgeBase.from_directory(Path("data/knowledge_base")))
        )
        response = service.answer(ChatRequest(message="I was charged twice."))
        assert response.ticket_id
        assert response.conversation_token


def test_pgvector_index_search_restart_and_content_change(postgres):
    embeddings = Mock()
    embeddings.embed_many.return_value = [{"0": 1.0, "1": 0.0}, {"0": 0.0, "1": 1.0}]
    embeddings.embed.return_value = {"0": 1.0, "1": 0.0}
    store = PostgresKnowledgeBase(postgres, CHUNKS, embeddings, "test-model")
    assert not store.is_ready()
    with pytest.raises(ValueError, match="snapshot is missing"):
        store.search("Delivery?")
    assert store.index()
    assert not store.index()
    assert embeddings.embed_many.call_count == 1
    restarted = PostgresKnowledgeBase(postgres, CHUNKS, embeddings, "test-model")
    results = restarted.search("When will the parcel arrive?", min_score=0.5)
    assert [result.chunk.document_id for result in results] == ["shipping"]
    assert results[0].score == pytest.approx(1.0)
    assert len(restarted.search("All", limit=1, min_score=0)) == 1
    assert restarted.search("Nothing", min_score=1.1) == []
    changed = [DocumentChunk("shipping::1", "shipping", "Shipping", "shipping.md", "Three days.")]
    new_store = PostgresKnowledgeBase(postgres, changed, embeddings, "test-model")
    assert not new_store.is_ready()
    assert restarted.is_ready()
    assert not PostgresKnowledgeBase(postgres, CHUNKS, embeddings, "other-model").is_ready()
    embeddings.embed.return_value = {"0": 1.0}
    with pytest.raises(ValueError, match="dimensions"):
        restarted.search("Wrong dimensions")


def test_invalid_embedding_batch_does_not_partially_index(postgres):
    embeddings = Mock()
    embeddings.embed_many.return_value = [{"0": 1.0}]
    store = PostgresKnowledgeBase(postgres, CHUNKS, embeddings, "invalid-model")
    with pytest.raises(ValueError, match="batch size"):
        store.index()
    assert not store.is_ready()


def test_snapshot_id_changes_with_model_or_content():
    assert snapshot_id(CHUNKS, "a") != snapshot_id(CHUNKS, "b")
    assert snapshot_id(CHUNKS, "a") != snapshot_id(CHUNKS[:1], "a")


@pytest.mark.parametrize("vector", [{}, {"word": 1.0}, {"0": float("nan")}, {"0": 0.0}])
def test_dense_vectors_reject_invalid_input(vector):
    with pytest.raises(ValueError):
        dense_vector(vector)
