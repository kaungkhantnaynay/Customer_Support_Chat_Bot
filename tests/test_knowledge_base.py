from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.rag.documents import chunk_documents, load_markdown_documents
from app.rag.retriever import LocalKnowledgeBase

KNOWLEDGE_BASE_DIR = Path("data/knowledge_base")


def test_loads_sample_support_documents() -> None:
    documents = load_markdown_documents(KNOWLEDGE_BASE_DIR)

    assert len(documents) >= 5
    assert {document.id for document in documents} >= {
        "refund_policy",
        "shipping_policy",
        "account_help",
    }


def test_chunks_documents_with_source_metadata() -> None:
    documents = load_markdown_documents(KNOWLEDGE_BASE_DIR)
    chunks = chunk_documents(documents, max_words=50)

    assert chunks
    assert all(chunk.document_id for chunk in chunks)
    assert all(chunk.title for chunk in chunks)
    assert all(chunk.source_path.endswith(".md") for chunk in chunks)
    assert all(chunk.citation for chunk in chunks)


def test_search_returns_relevant_refund_source() -> None:
    knowledge_base = LocalKnowledgeBase.from_directory(KNOWLEDGE_BASE_DIR)

    results = knowledge_base.search("Can I get a refund after being charged twice?")

    assert results
    assert results[0].chunk.document_id == "refund_policy"
    assert "Refund Policy" in results[0].citation


def test_knowledge_search_endpoint_returns_citations() -> None:
    client = TestClient(app)

    response = client.get("/knowledge/search", params={"q": "How long does express shipping take?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "How long does express shipping take?"
    assert payload["results"]
    assert payload["results"][0]["citation"]
