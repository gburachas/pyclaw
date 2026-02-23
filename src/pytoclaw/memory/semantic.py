"""Semantic memory with embeddings and vector search."""

from __future__ import annotations

import json
import logging
import math
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


class SemanticMemory:
    """In-process vector store using cosine similarity.

    Stores text chunks with their embeddings for semantic search.
    Uses a simple JSON file for persistence and supports pluggable
    embedding backends (OpenAI, local sentence-transformers).
    """

    def __init__(
        self,
        workspace: str,
        embed_fn: EmbedFunction | None = None,
        dimensions: int = 384,
    ) -> None:
        self._workspace = workspace
        self._store_path = os.path.join(workspace, "memory", "vectors.json")
        self._embed_fn = embed_fn
        self._dimensions = dimensions
        self._entries: list[VectorEntry] = []
        self._load()

    def _load(self) -> None:
        if os.path.isfile(self._store_path):
            try:
                with open(self._store_path) as f:
                    data = json.load(f)
                self._entries = [
                    VectorEntry(
                        text=e["text"],
                        embedding=e["embedding"],
                        metadata=e.get("metadata", {}),
                        timestamp=e.get("timestamp", 0),
                    )
                    for e in data
                ]
            except (json.JSONDecodeError, KeyError):
                logger.warning("Failed to load semantic memory, starting fresh")
                self._entries = []

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        data = [
            {
                "text": e.text,
                "embedding": e.embedding,
                "metadata": e.metadata,
                "timestamp": e.timestamp,
            }
            for e in self._entries
        ]
        tmp = self._store_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, self._store_path)

    async def add(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a text chunk to semantic memory."""
        embedding = await self._get_embedding(text)
        if embedding is None:
            return
        self._entries.append(
            VectorEntry(
                text=text,
                embedding=embedding,
                metadata=metadata or {},
                timestamp=int(time.time()),
            )
        )
        self._save()

    async def search(self, query: str, top_k: int = 5, threshold: float = 0.3) -> list[SearchResult]:
        """Search for semantically similar entries."""
        query_emb = await self._get_embedding(query)
        if query_emb is None:
            return []

        results = []
        for entry in self._entries:
            score = _cosine_similarity(query_emb, entry.embedding)
            if score >= threshold:
                results.append(SearchResult(text=entry.text, score=score, metadata=entry.metadata))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries = []
        self._save()

    async def _get_embedding(self, text: str) -> list[float] | None:
        if self._embed_fn is not None:
            return await self._embed_fn(text)
        # Fallback: simple bag-of-words hash embedding (for testing without API)
        return _hash_embedding(text, self._dimensions)


class VectorEntry:
    __slots__ = ("text", "embedding", "metadata", "timestamp")

    def __init__(self, text: str, embedding: list[float], metadata: dict[str, Any], timestamp: int):
        self.text = text
        self.embedding = embedding
        self.metadata = metadata
        self.timestamp = timestamp


class SearchResult:
    __slots__ = ("text", "score", "metadata")

    def __init__(self, text: str, score: float, metadata: dict[str, Any]):
        self.text = text
        self.score = score
        self.metadata = metadata


# Type alias for embedding functions
from typing import Callable, Coroutine
EmbedFunction = Callable[[str], Coroutine[Any, Any, list[float]]]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _hash_embedding(text: str, dimensions: int) -> list[float]:
    """Simple deterministic hash-based embedding for testing.

    Not suitable for real semantic search — use OpenAI or sentence-transformers
    embeddings for production.
    """
    import hashlib
    words = text.lower().split()
    vec = [0.0] * dimensions
    for word in words:
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = h % dimensions
        vec[idx] += 1.0
    # Normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


async def create_openai_embed_fn(api_key: str, model: str = "text-embedding-3-small") -> EmbedFunction:
    """Create an embedding function using the OpenAI API."""
    import openai
    client = openai.AsyncOpenAI(api_key=api_key)

    async def embed(text: str) -> list[float]:
        response = await client.embeddings.create(input=[text], model=model)
        return response.data[0].embedding

    return embed
