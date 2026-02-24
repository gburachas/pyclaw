"""Tests for semantic memory."""

import pytest

from pyclaw.memory.semantic import SemanticMemory, _cosine_similarity, _hash_embedding


def test_hash_embedding_deterministic():
    e1 = _hash_embedding("hello world", 128)
    e2 = _hash_embedding("hello world", 128)
    assert e1 == e2


def test_hash_embedding_different():
    e1 = _hash_embedding("hello world", 128)
    e2 = _hash_embedding("completely different text", 128)
    assert e1 != e2


def test_cosine_self_similarity():
    vec = [1.0, 2.0, 3.0]
    assert abs(_cosine_similarity(vec, vec) - 1.0) < 0.001


def test_cosine_orthogonal():
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert abs(_cosine_similarity(a, b)) < 0.001


@pytest.mark.asyncio
async def test_add_and_search(tmp_path):
    mem = SemanticMemory(str(tmp_path), dimensions=128)
    await mem.add("Python is a programming language")
    await mem.add("JavaScript runs in browsers")
    await mem.add("Cooking recipes need ingredients")

    results = await mem.search("programming language", top_k=2)
    assert len(results) >= 1
    # The programming-related entry should rank higher than cooking
    texts = [r.text for r in results]
    assert "Python is a programming language" in texts


@pytest.mark.asyncio
async def test_persistence(tmp_path):
    mem1 = SemanticMemory(str(tmp_path), dimensions=64)
    await mem1.add("test entry")
    assert mem1.count() == 1

    mem2 = SemanticMemory(str(tmp_path), dimensions=64)
    assert mem2.count() == 1


@pytest.mark.asyncio
async def test_clear(tmp_path):
    mem = SemanticMemory(str(tmp_path), dimensions=64)
    await mem.add("entry")
    assert mem.count() == 1
    mem.clear()
    assert mem.count() == 0
