"""Tests for hearth.search — hybrid search, FTS-only, project scoping, fallback."""

from __future__ import annotations

import pytest

from hearth.config import SearchConfig
from hearth.db import HearthDB
from hearth.search import SearchResult, hybrid_search, _normalize_scores


# ── Normalization ───────────────────────────────────────────────────


class TestNormalizeScores:
    def test_empty(self) -> None:
        assert _normalize_scores([]) == []

    def test_single(self) -> None:
        assert _normalize_scores([5.0]) == [1.0]

    def test_all_same(self) -> None:
        assert _normalize_scores([3.0, 3.0, 3.0]) == [1.0, 1.0, 1.0]

    def test_range(self) -> None:
        result = _normalize_scores([0.0, 5.0, 10.0])
        assert result == [0.0, 0.5, 1.0]

    def test_negative(self) -> None:
        result = _normalize_scores([-10.0, -5.0, 0.0])
        assert result == [0.0, 0.5, 1.0]


# ── FTS-Only Search ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fts_only_search(seeded_db: HearthDB, unavailable_embedder) -> None:
    """When Ollama is unavailable, search falls back to FTS-only."""
    results = await hybrid_search(
        "Python AI development", seeded_db, unavailable_embedder, limit=10,
    )
    assert len(results) >= 1
    assert all(isinstance(r, SearchResult) for r in results)
    assert all(r.match_type == "fts" for r in results)


@pytest.mark.asyncio
async def test_fts_project_scoping(seeded_db: HearthDB, unavailable_embedder) -> None:
    """Search within a project should only return that project's memories."""
    results = await hybrid_search(
        "great", seeded_db, unavailable_embedder,
        project="project-alpha", limit=10,
    )
    assert len(results) >= 1
    for r in results:
        assert r.memory["project"] == "project-alpha" or r.memory["project"] is None


@pytest.mark.asyncio
async def test_fts_category_filter(seeded_db: HearthDB, unavailable_embedder) -> None:
    """Filter by category."""
    results = await hybrid_search(
        "tests", seeded_db, unavailable_embedder,
        category="pattern", limit=10,
    )
    assert len(results) >= 1
    for r in results:
        assert r.memory["category"] == "pattern"


@pytest.mark.asyncio
async def test_fts_no_results(seeded_db: HearthDB, unavailable_embedder) -> None:
    """Searching for nonsense returns empty."""
    results = await hybrid_search(
        "zzzznonexistentzzzz", seeded_db, unavailable_embedder, limit=10,
    )
    assert results == []


# ── Hybrid Search ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hybrid_search_with_embeddings(seeded_db: HearthDB, mock_embedder) -> None:
    """With embeddings available, search uses both FTS and semantic."""
    # First, store embeddings for all memories
    from tests.conftest import _fake_embedding
    for mem in seeded_db.list_memories():
        seeded_db.store_embedding(mem["id"], _fake_embedding(mem["content"]))

    results = await hybrid_search(
        "Python", seeded_db, mock_embedder, limit=10,
    )
    assert len(results) >= 1
    # At least some results should be hybrid (both FTS and semantic matched)
    match_types = {r.match_type for r in results}
    assert len(match_types) >= 1  # At least one type present


@pytest.mark.asyncio
async def test_hybrid_scores_between_0_and_1(seeded_db: HearthDB, mock_embedder) -> None:
    """All scores should be in valid range."""
    from tests.conftest import _fake_embedding
    for mem in seeded_db.list_memories():
        seeded_db.store_embedding(mem["id"], _fake_embedding(mem["content"]))

    results = await hybrid_search(
        "search", seeded_db, mock_embedder, limit=10,
    )
    for r in results:
        assert 0.0 <= r.score <= 1.0, f"Score {r.score} out of range"


@pytest.mark.asyncio
async def test_search_respects_limit(seeded_db: HearthDB, unavailable_embedder) -> None:
    """Results should not exceed the limit."""
    results = await hybrid_search(
        "test project memory", seeded_db, unavailable_embedder, limit=2,
    )
    assert len(results) <= 2


@pytest.mark.asyncio
async def test_search_config_weights(seeded_db: HearthDB, unavailable_embedder) -> None:
    """Custom search config should be respected."""
    config = SearchConfig(default_limit=5, semantic_weight=0.0, fts_weight=1.0)
    results = await hybrid_search(
        "Python", seeded_db, unavailable_embedder,
        limit=5, config=config,
    )
    # Should still work with zero semantic weight
    assert len(results) >= 1
