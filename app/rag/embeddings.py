import math
import re
from collections import Counter
from typing import Protocol

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a",
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
