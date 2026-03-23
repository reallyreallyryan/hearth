"""Tests for hearth.server — MCP tool round-trips."""

from __future__ import annotations

import pytest

from hearth.db import HearthDB
from hearth.embeddings import OllamaEmbedder


# These tests call the tool functions directly (bypassing MCP transport)
# by constructing a mock context.

class MockLifespanContext:
    def __init__(self, db: HearthDB, embedder: OllamaEmbedder, config):
        self.lifespan_context = {
            "db": db,
            "embedder": embedder,
            "config": config,
        }


class MockContext:
    def __init__(self, db: HearthDB, embedder: OllamaEmbedder, config):
        self.request_context = MockLifespanContext(db, embedder, config)


@pytest.fixture
def ctx(seeded_db, unavailable_embedder, test_config):
    """Mock MCP context with seeded DB and unavailable embedder."""
    return MockContext(seeded_db, unavailable_embedder, test_config)


@pytest.fixture
def fresh_ctx(tmp_db, unavailable_embedder, test_config):
    """Mock MCP context with empty DB."""
    return MockContext(tmp_db, unavailable_embedder, test_config)


# ── Memory Tools ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_memory_store(fresh_ctx) -> None:
    from hearth.server import memory_store

    result = await memory_store(
        content="Test memory from MCP",
        category="learning",
        source="assistant",
        ctx=fresh_ctx,
    )
    assert "id" in result
    assert result["content"] == "Test memory from MCP"
    assert result["has_embedding"] is False  # Ollama unavailable


@pytest.mark.asyncio
async def test_memory_store_invalid_category(fresh_ctx) -> None:
    from hearth.server import memory_store

    result = await memory_store(content="Test", category="invalid", ctx=fresh_ctx)
    assert "error" in result


@pytest.mark.asyncio
async def test_memory_search(ctx) -> None:
    from hearth.server import memory_search

    results = await memory_search(query="Python", ctx=ctx)
    assert isinstance(results, list)
    assert len(results) >= 1
    assert "memory" in results[0]
    assert "score" in results[0]


@pytest.mark.asyncio
async def test_memory_update(ctx) -> None:
    from hearth.server import memory_store, memory_update

    stored = await memory_store(content="Original", ctx=ctx)
    updated = await memory_update(id=stored["id"], content="Modified", ctx=ctx)
    assert updated["content"] == "Modified"


@pytest.mark.asyncio
async def test_memory_update_not_found(ctx) -> None:
    from hearth.server import memory_update

    result = await memory_update(id="nonexistent", content="x", ctx=ctx)
    assert "error" in result


@pytest.mark.asyncio
async def test_memory_delete(ctx) -> None:
    from hearth.server import memory_store, memory_delete

    stored = await memory_store(content="To delete", ctx=ctx)
    result = await memory_delete(id=stored["id"], ctx=ctx)
    assert result["deleted"] is True


@pytest.mark.asyncio
async def test_memory_delete_not_found(ctx) -> None:
    from hearth.server import memory_delete

    result = await memory_delete(id="nonexistent", ctx=ctx)
    assert "error" in result


@pytest.mark.asyncio
async def test_memory_list(ctx) -> None:
    from hearth.server import memory_list

    results = await memory_list(ctx=ctx)
    assert isinstance(results, list)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_memory_list_by_project(ctx) -> None:
    from hearth.server import memory_list

    results = await memory_list(project="project-alpha", ctx=ctx)
    assert all(r["project"] == "project-alpha" for r in results)


# ── Project Tools ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_project_create(fresh_ctx) -> None:
    from hearth.server import project_create

    result = await project_create(name="test-project", description="A test", ctx=fresh_ctx)
    assert result["name"] == "test-project"
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_project_create_duplicate(ctx) -> None:
    from hearth.server import project_create

    result = await project_create(name="project-alpha", ctx=ctx)
    assert "error" in result


@pytest.mark.asyncio
async def test_project_list(ctx) -> None:
    from hearth.server import project_list

    results = await project_list(ctx=ctx)
    assert len(results) >= 2


@pytest.mark.asyncio
async def test_project_get(ctx) -> None:
    from hearth.server import project_get

    result = await project_get(name="project-alpha", ctx=ctx)
    assert result["name"] == "project-alpha"
    assert "memory_count" in result


@pytest.mark.asyncio
async def test_project_get_not_found(ctx) -> None:
    from hearth.server import project_get

    result = await project_get(name="nonexistent", ctx=ctx)
    assert "error" in result


@pytest.mark.asyncio
async def test_project_update(ctx) -> None:
    from hearth.server import project_update

    result = await project_update(name="project-alpha", description="Updated", ctx=ctx)
    assert result["description"] == "Updated"


@pytest.mark.asyncio
async def test_project_archive(ctx) -> None:
    from hearth.server import project_archive

    result = await project_archive(name="project-beta", ctx=ctx)
    assert result["archived"] is True


# ── System Tools ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hearth_status(ctx) -> None:
    from hearth.server import hearth_status

    result = await hearth_status(ctx=ctx)
    assert "version" in result
    assert "total_memories" in result
    assert result["ollama_available"] is False


@pytest.mark.asyncio
async def test_hearth_export_json(ctx) -> None:
    from hearth.server import hearth_export
    import json

    result = await hearth_export(format="json", ctx=ctx)
    parsed = json.loads(result)
    assert isinstance(parsed, list)


@pytest.mark.asyncio
async def test_hearth_export_csv(ctx) -> None:
    from hearth.server import hearth_export

    result = await hearth_export(format="csv", ctx=ctx)
    assert "content" in result  # CSV header
