from dataclasses import dataclass
from pathlib import Path

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
        self._chunk_vectors = {
            chunk.id: self.embedding_service.embed(f"{chunk.title}\n{chunk.text}")
            for chunk in chunks
        }

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
        query_vector = self.embedding_service.embed(query)
        scored_results = [
            RetrievalResult(
                chunk=chunk,
                score=cosine_similarity(query_vector, self._chunk_vectors[chunk.id]),
            )
            for chunk in self.chunks
        ]

        matching_results = [result for result in scored_results if result.score >= min_score]
        return sorted(matching_results, key=lambda result: result.score, reverse=True)[:limit]
