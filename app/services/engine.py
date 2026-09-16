from dataclasses import dataclass
from functools import lru_cache
from threading import Lock

from openai import OpenAI

from app.core.config import settings
from app.rag.documents import DocumentChunk, chunk_documents, load_markdown_documents
from app.rag.embeddings import OpenAIEmbeddingService
from app.rag.retriever import KnowledgeBase, LocalKnowledgeBase
from app.services.generation import AnswerGenerator, OpenAIAnswerGenerator


@dataclass(frozen=True)
class AnswerEngine:
    knowledge_base: KnowledgeBase
    generator: AnswerGenerator | None = None
    min_score: float = 0.12
    high_score: float = 0.25


_index_lock = Lock()


@lru_cache(maxsize=2)
def _client(api_key: str, timeout: float) -> OpenAI:
    return OpenAI(api_key=api_key, timeout=timeout, max_retries=0)


@lru_cache(maxsize=2)
def _semantic_index(
    chunks: tuple[DocumentChunk, ...], client: OpenAI, model: str
) -> LocalKnowledgeBase:
    return LocalKnowledgeBase(list(chunks), OpenAIEmbeddingService(client, model))


def get_answer_engine() -> AnswerEngine:
    if settings.ai_mode == "offline":
        return AnswerEngine(LocalKnowledgeBase.from_directory(settings.knowledge_base_dir))
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required in OpenAI mode.")
    client = _client(settings.openai_api_key, settings.openai_timeout_seconds)
    chunks = tuple(chunk_documents(load_markdown_documents(settings.knowledge_base_dir)))
    # Serialize cache fills so concurrent first requests do not duplicate embedding charges.
    # Contents are part of the key, so editing a document rebuilds the index.
    if settings.vector_store == "pgvector":
        from app.db.session import engine
        from app.rag.postgres import PostgresKnowledgeBase

        knowledge_base = PostgresKnowledgeBase(
            engine,
            list(chunks),
            OpenAIEmbeddingService(client, settings.openai_embedding_model),
            settings.openai_embedding_model,
        )
    else:
        with _index_lock:
            knowledge_base = _semantic_index(chunks, client, settings.openai_embedding_model)
    return AnswerEngine(
        knowledge_base,
        OpenAIAnswerGenerator(client, settings.openai_chat_model),
        settings.semantic_min_score,
        settings.semantic_high_score,
    )
