import hashlib
import json
import math
from dataclasses import asdict

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import KnowledgeVector
from app.rag.documents import DocumentChunk
from app.rag.retriever import RetrievalResult


def snapshot_id(chunks: list[DocumentChunk], model: str) -> str:
    payload = {"model": model, "chunks": [asdict(chunk) for chunk in chunks]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def dense_vector(vector: dict[str, float]) -> list[float]:
    try:
        values = [vector[str(index)] for index in range(len(vector))]
    except KeyError as exc:
        raise ValueError("Expected a dense embedding vector.") from exc
    if not values or not all(math.isfinite(value) for value in values) or not any(values):
        raise ValueError("Embedding must contain finite, nonzero values.")
    return values


class PostgresKnowledgeBase:
    def __init__(self, engine, chunks: list[DocumentChunk], embedding_service, model: str):
        if engine.dialect.name != "postgresql":
            raise ValueError("The pgvector store requires PostgreSQL.")
        if not chunks:
            raise ValueError("Cannot index an empty knowledge base.")
        self.engine = engine
        self.chunks = chunks
        self.embedding_service = embedding_service
        self.model = model
        self.snapshot = snapshot_id(chunks, model)

    def _existing_count(self, session):
        return session.scalar(
            select(func.count())
            .select_from(KnowledgeVector)
            .where(KnowledgeVector.snapshot_id == self.snapshot)
        )

    def is_ready(self) -> bool:
        with Session(self.engine) as session:
            return self._existing_count(session) == len(self.chunks)

    def index(self) -> bool:
        if self.is_ready():
            return False
        # Generate outside the write transaction; insert the entire immutable snapshot atomically.
        vectors = self.embedding_service.embed_many(
            [f"{chunk.title}\n{chunk.text}" for chunk in self.chunks]
        )
        dense = [dense_vector(vector) for vector in vectors]
        if len(dense) != len(self.chunks) or len({len(vector) for vector in dense}) != 1:
            raise ValueError("Embedding batch size or dimensions do not match the chunks.")
        rows = [
            {
                "snapshot_id": self.snapshot,
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "title": chunk.title,
                "source_path": chunk.source_path,
                "content": chunk.text,
                "embedding_model": self.model,
                "dimensions": len(vector),
                "embedding": vector,
            }
            for chunk, vector in zip(self.chunks, dense, strict=True)
        ]
        with self.engine.begin() as connection:
            connection.execute(insert(KnowledgeVector).on_conflict_do_nothing(), rows)
        return True

    def search(self, query: str, limit: int = 3, min_score: float = 0.05):
        if not self.is_ready():
            raise ValueError("Knowledge snapshot is missing. Run scripts/index_knowledge.py.")
        vector = dense_vector(self.embedding_service.embed(query))
        with Session(self.engine) as session:
            dimensions = session.scalars(
                select(KnowledgeVector.dimensions)
                .where(KnowledgeVector.snapshot_id == self.snapshot)
                .distinct()
            ).all()
            if dimensions != [len(vector)]:
                raise ValueError("Query and stored embedding dimensions differ.")
            distance = KnowledgeVector.embedding.cosine_distance(vector)
            rows = session.execute(
                select(KnowledgeVector, (1 - distance).label("score"))
                .where(KnowledgeVector.snapshot_id == self.snapshot, 1 - distance >= min_score)
                .order_by(distance, KnowledgeVector.chunk_id)
                .limit(limit)
            ).all()
            return [
                RetrievalResult(
                    DocumentChunk(
                        row.chunk_id, row.document_id, row.title, row.source_path, row.content
                    ),
                    float(score),
                )
                for row, score in rows
            ]
