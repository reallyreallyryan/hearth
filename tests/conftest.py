"""Shared fixtures for Hearth tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from hearth.config import HearthConfig, SearchConfig
from hearth.db import HearthDB
from hearth.embeddings import EmbeddingResult, OllamaEmbedder


@pytest.fixture
def tmp_db(tmp_path) -> HearthDB:
    """Create a temporary database with full schema."""
    db_path = tmp_path / "test_hearth.db"
    db = HearthDB(db_path)
    db.init_db()
    yield db
    db.close()


@pytest.fixture
def seeded_db(tmp_db) -> HearthDB:
    """Database pre-loaded with sample projects and memories."""
    tmp_db.create_project("project-alpha", "Test project Alpha")
    tmp_db.create_project("project-beta", "Test project Beta")

    tmp_db.store_memory(
        "Python is great for AI development",
        "learning", "project-alpha", ["python", "ai"],
    )
    tmp_db.store_memory(
        "SQLite supports FTS5 for full-text search",
        "reference", "project-alpha", ["sqlite", "fts5"],
    )
    tmp_db.store_memory(
        "Always write tests before shipping",
        "pattern", "project-beta", ["testing"],
    )
    tmp_db.store_memory(
        "Global knowledge accessible everywhere",
        "general", None, ["global"],
    )
    return tmp_db


@pytest.fixture
def session_db(seeded_db) -> HearthDB:
    """Database pre-loaded with sessions and resonance data."""
    from hearth.config import RESONANCE_AXES

    # Session 1: productive coding session on project-alpha
    s1 = seeded_db.create_session(project="project-alpha")
    seeded_db.close_session(s1["id"], summary="Productive coding session")
    axes1 = {axis: 0.0 for axis in RESONANCE_AXES}
    axes1.update({
        "exploration_execution": 0.8,
        "alignment_tension": 0.7,
        "momentum_resistance": 0.9,
        "confidence_uncertainty": 0.6,
        "energy_entropy": 0.5,
        "mutual_transactional": 0.8,
    })
    seeded_db.store_resonance(s1["id"], axes1)

    # Session 2: debugging frustration on project-beta
    s2 = seeded_db.create_session(project="project-beta")
    seeded_db.close_session(s2["id"], summary="Debugging frustration")
    axes2 = {axis: 0.0 for axis in RESONANCE_AXES}
    axes2.update({
        "exploration_execution": -0.5,
        "alignment_tension": -0.3,
        "momentum_resistance": -0.7,
        "confidence_uncertainty": -0.4,
        "stakes_casual": 0.6,
    })
    seeded_db.store_resonance(s2["id"], axes2)

    # Link some memories to session 1
    memories = seeded_db.list_memories(project="project-alpha")
    for mem in memories:
        seeded_db.link_memory_to_session(s1["id"], mem["id"], "created")

    return seeded_db


@pytest.fixture
def test_config(tmp_path) -> HearthConfig:
    """Config pointing to temporary directory."""
    return HearthConfig(db_path=tmp_path / "test_hearth.db")


def _fake_embedding(text: str, dimensions: int = 768) -> list[float]:
    """Generate a deterministic fake embedding from text hash."""
    import hashlib
    h = hashlib.sha256(text.encode()).digest()
    # Extend hash to fill dimensions
    extended = h * (dimensions // len(h) + 1)
    return [b / 255.0 for b in extended[:dimensions]]


@pytest.fixture
def mock_embedder() -> OllamaEmbedder:
    """OllamaEmbedder that returns deterministic fake embeddings."""
    embedder = OllamaEmbedder()
    embedder._available = True

    async def fake_embed(text: str) -> EmbeddingResult:
        return EmbeddingResult(
            embedding=_fake_embedding(text),
            model="nomic-embed-text",
            dimensions=768,
        )

    async def fake_batch(texts: list[str]) -> list[EmbeddingResult]:
        return [
            EmbeddingResult(
                embedding=_fake_embedding(t),
                model="nomic-embed-text",
                dimensions=768,
            )
            for t in texts
        ]

    embedder.embed = fake_embed  # type: ignore[assignment]
    embedder.embed_batch = fake_batch  # type: ignore[assignment]
    return embedder


@pytest.fixture
def unavailable_embedder() -> OllamaEmbedder:
    """OllamaEmbedder that simulates Ollama being offline."""
    embedder = OllamaEmbedder()
    embedder._available = False

    async def returns_none(text: str) -> None:
        return None

    async def returns_nones(texts: list[str]) -> list[None]:
        return [None] * len(texts)

    async def check_returns_false() -> bool:
        return False

    embedder.embed = returns_none  # type: ignore[assignment]
    embedder.embed_batch = returns_nones  # type: ignore[assignment]
    embedder.check_available = check_returns_false  # type: ignore[assignment]
    return embedder
