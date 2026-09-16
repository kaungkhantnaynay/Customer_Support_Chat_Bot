import math
import re
from collections import Counter
from typing import Protocol

from openai import OpenAI

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "for",
    "from",
    "get",
    "have",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "should",
    "that",
    "the",
    "their",
    "then",
    "they",
    "to",
    "was",
    "what",
    "when",
    "with",
    "you",
    "your",
}


class EmbeddingService(Protocol):
    def embed(self, text: str) -> dict[str, float]:
        """Convert text into a vector representation."""


class KeywordEmbeddingService:
    """Small local embedding substitute for Phase 2 development and tests."""

    def embed(self, text: str) -> dict[str, float]:
        tokens = [token for token in TOKEN_PATTERN.findall(text.lower()) if token not in STOP_WORDS]
        counts = Counter(tokens)
        length = math.sqrt(sum(value * value for value in counts.values()))

        if length == 0:
            return {}

        return {token: count / length for token, count in counts.items()}


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0

    shared_tokens = left.keys() & right.keys()
    return sum(left[token] * right[token] for token in shared_tokens)


class OpenAIEmbeddingService:
    """Adapt dense, normalized vectors to the existing cosine-search interface."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def embed(self, text: str) -> dict[str, float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[dict[str, float]]:
        vectors = []
        for start in range(0, len(texts), 64):
            batch = texts[start : start + 64]
            response = self.client.embeddings.create(
                model=self.model, input=batch, encoding_format="float"
            )
            entries = sorted(response.data, key=lambda item: item.index)
            if [entry.index for entry in entries] != list(range(len(batch))):
                raise ValueError("Incomplete embedding response.")
            for entry in entries:
                values = entry.embedding
                length = math.sqrt(sum(value * value for value in values))
                if not values or not math.isfinite(length) or length == 0:
                    raise ValueError("Invalid embedding vector.")
                vectors.append({str(index): value / length for index, value in enumerate(values)})
        if vectors and any(len(vector) != len(vectors[0]) for vector in vectors):
            raise ValueError("Inconsistent embedding dimensions.")
        return vectors
