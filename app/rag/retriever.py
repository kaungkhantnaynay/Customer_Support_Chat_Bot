from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.rag.documents import DocumentChunk, chunk_documents, load_markdown_documents
from app.rag.embeddings import EmbeddingService, KeywordEmbeddingService, cosine_similarity


@dataclass(frozen=True)
class RetrievalResult:
    chunk: DocumentChunk
    score: float

    @property
    def citation(self) -> str:
        return self.chunk.citation


class LocalKnowledgeBase:
    def __init__(
        self,
        chunks: list[DocumentChunk],
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.embedding_service = embedding_service or KeywordEmbeddingService()
        self.chunks = chunks
        texts = [f"{chunk.title}\n{chunk.text}" for chunk in chunks]
        embed_many = getattr(self.embedding_service, "embed_many", None)
        vectors = (
            embed_many(texts)
            if embed_many
            else [self.embedding_service.embed(text) for text in texts]
        )
        self._chunk_vectors = dict(zip((chunk.id for chunk in chunks), vectors, strict=True))

    @classmethod
    def from_directory(
        cls,
        directory: Path,
        embedding_service: EmbeddingService | None = None,
        max_words: int = 90,
    ) -> "LocalKnowledgeBase":
        documents = load_markdown_documents(directory)
        chunks = chunk_documents(documents, max_words=max_words)
        return cls(chunks=chunks, embedding_service=embedding_service)

    def search(self, query: str, limit: int = 3, min_score: float = 0.05) -> list[RetrievalResult]:
        if not self.chunks:
            return []
        query_vector = self.embedding_service.embed(query)
        if hasattr(self.embedding_service, "embed_many") and any(
            len(vector) != len(query_vector) for vector in self._chunk_vectors.values()
        ):
            raise ValueError("Query and index embedding dimensions differ.")
        scored_results = [
            RetrievalResult(
                chunk=chunk,
                score=cosine_similarity(query_vector, self._chunk_vectors[chunk.id]),
            )
            for chunk in self.chunks
        ]

        matching_results = [result for result in scored_results if result.score >= min_score]
        return sorted(matching_results, key=lambda result: result.score, reverse=True)[:limit]


class KnowledgeBase(Protocol):
    def search(
        self, query: str, limit: int = 3, min_score: float = 0.05
    ) -> list[RetrievalResult]: ...
