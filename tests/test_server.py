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


@pytest.fixture
def session_ctx(session_db, unavailable_embedder, test_config):
    """Mock MCP context with sessions and resonance data."""
    return MockContext(session_db, unavailable_embedder, test_config)


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


# ── Session & Resonance Tools ──────────────────────────────────────


@pytest.fixture
def session_ctx(session_db, unavailable_embedder, test_config):
    """Mock MCP context with session data."""
    return MockContext(session_db, unavailable_embedder, test_config)


@pytest.mark.asyncio
async def test_session_start(fresh_ctx) -> None:
    from hearth.server import session_start

    result = await session_start(ctx=fresh_ctx)
    assert "id" in result
    assert result["memory_count"] == 0
    assert "next_step" in result
    assert "hearth_briefing" in result["next_step"]


@pytest.mark.asyncio
async def test_session_start_with_project(ctx) -> None:
    from hearth.server import session_start

    result = await session_start(project="project-alpha", ctx=ctx)
    assert result["project"] == "project-alpha"
    assert "next_step" in result
    assert "project-alpha" in result["next_step"]
    assert "hearth_briefing" in result["next_step"]


@pytest.mark.asyncio
async def test_session_start_invalid_project(fresh_ctx) -> None:
    from hearth.server import session_start

    result = await session_start(project="nonexistent", ctx=fresh_ctx)
    assert "error" in result


# ── Session Loop Guard ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_session_start_returns_existing_open_session(fresh_ctx) -> None:
    from hearth.server import session_start

    s1 = await session_start(ctx=fresh_ctx)
    s2 = await session_start(ctx=fresh_ctx)
    assert s2["id"] == s1["id"]
    assert s2["resumed"] is True
    assert "message" in s2
    assert "next_step" in s2


@pytest.mark.asyncio
async def test_session_start_creates_new_after_close(fresh_ctx) -> None:
    from hearth.server import session_close, session_start

    s1 = await session_start(ctx=fresh_ctx)
    await session_close(session_id=s1["id"], summary="done", ctx=fresh_ctx)
    s2 = await session_start(ctx=fresh_ctx)
    assert s2["id"] != s1["id"]
    assert "resumed" not in s2


@pytest.mark.asyncio
async def test_session_start_different_projects_independent(ctx) -> None:
    from hearth.server import session_start

    s_alpha = await session_start(project="project-alpha", ctx=ctx)
    s_beta = await session_start(project="project-beta", ctx=ctx)
    assert s_alpha["id"] != s_beta["id"]
    assert "resumed" not in s_alpha
    assert "resumed" not in s_beta


@pytest.mark.asyncio
async def test_session_start_null_project_independent(ctx) -> None:
    from hearth.server import session_start

    s_null = await session_start(ctx=ctx)
    s_alpha = await session_start(project="project-alpha", ctx=ctx)
    assert s_null["id"] != s_alpha["id"]


@pytest.mark.asyncio
async def test_session_start_loop_guard(fresh_ctx) -> None:
    from hearth.server import session_start

    s1 = await session_start(ctx=fresh_ctx)
    s2 = await session_start(ctx=fresh_ctx)
    s3 = await session_start(ctx=fresh_ctx)
    assert s1["id"] == s2["id"] == s3["id"]
    # Verify only one session exists in the DB
    db = fresh_ctx.request_context.lifespan_context["db"]
    sessions = db.list_sessions()
    assert len(sessions) == 1


@pytest.mark.asyncio
async def test_session_close(fresh_ctx) -> None:
    from hearth.server import session_close, session_start

    session = await session_start(ctx=fresh_ctx)
    result = await session_close(
        session_id=session["id"],
        summary="Test session",
        ctx=fresh_ctx,
    )
    assert result["ended_at"] is not None
    assert result["summary"] == "Test session"
    assert "next_step" in result
    assert "session_score" in result["next_step"]


@pytest.mark.asyncio
async def test_session_close_not_found(fresh_ctx) -> None:
    from hearth.server import session_close

    result = await session_close(session_id="nonexistent", summary="x", ctx=fresh_ctx)
    assert "error" in result


# ── Resonance String Parser ──────────────────────────────────────


class TestParseResonanceString:
    def test_short_names(self) -> None:
        from hearth.server import _parse_resonance_string

        result = _parse_resonance_string(
            "exploration=-0.8, alignment=0.5, depth=-0.3, momentum=0.5, "
            "novelty=-0.4, confidence=0.4, autonomy=-0.5, energy=0.2, "
            "vulnerability=0.1, stakes=0.3, mutual=-0.2"
        )
        assert result["exploration_execution"] == -0.8
        assert result["alignment_tension"] == 0.5
        assert result["stakes_casual"] == 0.3

    def test_full_names(self) -> None:
        from hearth.server import _parse_resonance_string

        result = _parse_resonance_string("exploration_execution=-0.8, alignment_tension=0.5")
        assert result["exploration_execution"] == -0.8
        assert result["alignment_tension"] == 0.5

    def test_partial(self) -> None:
        from hearth.server import _parse_resonance_string

        result = _parse_resonance_string("exploration=-0.5, stakes=0.3")
        assert result["exploration_execution"] == -0.5
        assert result["stakes_casual"] == 0.3
        assert result["depth_breadth"] == 0.0

    def test_invalid_axis(self) -> None:
        from hearth.server import _parse_resonance_string

        result = _parse_resonance_string("bogus=0.5")
        assert "error" in result

    def test_invalid_value(self) -> None:
        from hearth.server import _parse_resonance_string

        result = _parse_resonance_string("exploration=abc")
        assert "error" in result

    def test_out_of_range(self) -> None:
        from hearth.server import _parse_resonance_string

        result = _parse_resonance_string("exploration=1.5")
        assert "error" in result

    def test_empty(self) -> None:
        from hearth.server import _parse_resonance_string

        result = _parse_resonance_string("")
        assert all(v == 0.0 for v in result.values())

    def test_whitespace_tolerant(self) -> None:
        from hearth.server import _parse_resonance_string

        result = _parse_resonance_string("exploration = -0.8 , alignment = 0.5")
        assert result["exploration_execution"] == -0.8
        assert result["alignment_tension"] == 0.5


# ── Session Score Tool ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_session_score_valid(fresh_ctx) -> None:
    from hearth.server import session_close, session_score, session_start

    session = await session_start(ctx=fresh_ctx)
    await session_close(session_id=session["id"], summary="Test", ctx=fresh_ctx)
    result = await session_score(
        session_id=session["id"],
        resonance="exploration=-0.5, alignment=0.7, depth=0.3",
        ctx=fresh_ctx,
    )
    assert "error" not in result
    assert result["resonance"]["exploration_execution"] == -0.5
    assert result["resonance"]["alignment_tension"] == 0.7


@pytest.mark.asyncio
async def test_session_score_rejects_all_zeros(fresh_ctx) -> None:
    from hearth.server import session_close, session_score, session_start

    session = await session_start(ctx=fresh_ctx)
    await session_close(session_id=session["id"], summary="Test", ctx=fresh_ctx)
    result = await session_score(
        session_id=session["id"],
        resonance="exploration=0, alignment=0",
        ctx=fresh_ctx,
    )
    assert "error" in result
    assert "0.0" in result["error"]


@pytest.mark.asyncio
async def test_session_score_rejects_duplicate(fresh_ctx) -> None:
    from hearth.server import session_close, session_score, session_start

    session = await session_start(ctx=fresh_ctx)
    await session_close(session_id=session["id"], summary="Test", ctx=fresh_ctx)
    await session_score(
        session_id=session["id"],
        resonance="exploration=-0.5",
        ctx=fresh_ctx,
    )
    result = await session_score(
        session_id=session["id"],
        resonance="exploration=0.3",
        ctx=fresh_ctx,
    )
    assert "error" in result
    assert "already has resonance" in result["error"]


@pytest.mark.asyncio
async def test_session_score_nonexistent_session(fresh_ctx) -> None:
    from hearth.server import session_score

    result = await session_score(
        session_id="nonexistent",
        resonance="exploration=-0.5",
        ctx=fresh_ctx,
    )
    assert "error" in result


# ── Full Ceremony Integration ────────────────────────────────────


@pytest.mark.asyncio
async def test_full_ceremony(fresh_ctx) -> None:
    from hearth.server import hearth_briefing, session_close, session_score, session_start

    # 1. Start
    s = await session_start(ctx=fresh_ctx)
    assert s["id"]
    assert "next_step" in s

    # 2. Briefing
    b = await hearth_briefing(ctx=fresh_ctx)
    assert "briefing" in b

    # 3. Close
    c = await session_close(session_id=s["id"], summary="Test ceremony", ctx=fresh_ctx)
    assert c["ended_at"] is not None
    assert "session_score" in c["next_step"]

    # 4. Score
    r = await session_score(
        session_id=s["id"],
        resonance="exploration=-0.5, alignment=0.7, depth=0.3, momentum=0.6, "
                  "novelty=-0.2, confidence=0.5, autonomy=-0.3, energy=0.4, "
                  "vulnerability=0.2, stakes=0.3, mutual=0.1",
        ctx=fresh_ctx,
    )
    assert "error" not in r
    assert r["resonance"]["exploration_execution"] == -0.5
    assert r["resonance"]["mutual_transactional"] == 0.1

    # Verify in DB
    db = fresh_ctx.request_context.lifespan_context["db"]
    session = db.get_session(s["id"])
    assert session["ended_at"] is not None
    res = db.get_resonance(s["id"])
    assert res is not None


@pytest.mark.asyncio
async def test_session_history(session_ctx) -> None:
    from hearth.server import session_history

    results = await session_history(ctx=session_ctx)
    assert isinstance(results, list)
    assert len(results) >= 2
    assert results[0].get("resonance") is not None


@pytest.mark.asyncio
async def test_session_history_by_project(session_ctx) -> None:
    from hearth.server import session_history

    results = await session_history(project="project-alpha", ctx=session_ctx)
    assert all(r["project"] == "project-alpha" for r in results)


@pytest.mark.asyncio
async def test_session_resonance_search(session_ctx) -> None:
    from hearth.server import session_resonance_search

    results = await session_resonance_search(
        exploration_execution=0.8,
        momentum_resistance=0.9,
        ctx=session_ctx,
    )
    assert isinstance(results, list)
    assert len(results) >= 1
    assert "session" in results[0]
    assert "resonance" in results[0]
    assert "distance" in results[0]
    assert "memories" in results[0]


@pytest.mark.asyncio
async def test_memory_store_with_session(fresh_ctx) -> None:
    from hearth.server import memory_store, session_start

    session = await session_start(ctx=fresh_ctx)
    memory = await memory_store(
        content="Memory in a session",
        session_id=session["id"],
        ctx=fresh_ctx,
    )
    assert memory.get("session_id") == session["id"]
    assert "session_link_error" not in memory


@pytest.mark.asyncio
async def test_memory_store_with_bad_session(fresh_ctx) -> None:
    from hearth.server import memory_store

    memory = await memory_store(
        content="Memory with bad session",
        session_id="nonexistent",
        ctx=fresh_ctx,
    )
    # Memory should still be stored, but with a link error
    assert "id" in memory
    assert "session_link_error" in memory


# ── Thread & Tension Tools ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_thread_list_empty(fresh_ctx) -> None:
    from hearth.server import thread_list

    result = await thread_list(ctx=fresh_ctx)
    assert result == []


@pytest.mark.asyncio
async def test_thread_list_populated(session_ctx) -> None:
    from hearth.server import session_start, session_reflect, thread_list

    session = await session_start(ctx=session_ctx)
    await session_reflect(
        session_id=session["id"],
        threads=[{"action": "create", "title": "Test thread"}],
        ctx=session_ctx,
    )
    result = await thread_list(ctx=session_ctx)
    assert len(result) == 1
    assert result[0]["title"] == "Test thread"
    assert result[0]["session_count"] == 1


@pytest.mark.asyncio
async def test_thread_list_filter_by_project(session_ctx) -> None:
    from hearth.server import session_start, session_reflect, thread_list

    session = await session_start(project="project-alpha", ctx=session_ctx)
    await session_reflect(
        session_id=session["id"],
        threads=[
            {"action": "create", "title": "Alpha thread", "project": "project-alpha"},
        ],
        ctx=session_ctx,
    )
    result = await thread_list(project="project-alpha", ctx=session_ctx)
    assert len(result) == 1
    assert result[0]["project"] == "project-alpha"
    empty = await thread_list(project="project-beta", ctx=session_ctx)
    assert len(empty) == 0


@pytest.mark.asyncio
async def test_tension_list_empty(fresh_ctx) -> None:
    from hearth.server import tension_list

    result = await tension_list(ctx=fresh_ctx)
    assert result == []


@pytest.mark.asyncio
async def test_tension_list_populated(session_ctx) -> None:
    from hearth.server import session_start, session_reflect, tension_list

    session = await session_start(ctx=session_ctx)
    await session_reflect(
        session_id=session["id"],
        tensions=[{"action": "create", "question": "Is this real?"}],
        ctx=session_ctx,
    )
    result = await tension_list(ctx=session_ctx)
    assert len(result) == 1
    assert result[0]["question"] == "Is this real?"


@pytest.mark.asyncio
async def test_tension_list_filter_by_thread(session_ctx) -> None:
    from hearth.server import session_start, session_reflect, tension_list

    session = await session_start(ctx=session_ctx)
    reflect = await session_reflect(
        session_id=session["id"],
        threads=[{"action": "create", "title": "Thread A"}],
        tensions=[{"action": "create", "question": "Orphan?"}],
        ctx=session_ctx,
    )
    thread_id = reflect["threads_created"][0]["id"]
    # Create tension linked to thread
    db = session_ctx.request_context.lifespan_context["db"]
    db.create_tension(question="Linked?", thread_id=thread_id, session_id=session["id"])

    result = await tension_list(thread_id=thread_id, ctx=session_ctx)
    assert len(result) == 1
    assert result[0]["question"] == "Linked?"


# ── session_reflect Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_session_reflect_create_thread(session_ctx) -> None:
    from hearth.server import session_start, session_reflect

    session = await session_start(ctx=session_ctx)
    result = await session_reflect(
        session_id=session["id"],
        threads=[{
            "action": "create",
            "title": "New thread",
            "trajectory": "Going somewhere",
        }],
        ctx=session_ctx,
    )
    assert len(result["threads_created"]) == 1
    assert result["threads_created"][0]["title"] == "New thread"
    assert result["threads_created"][0]["created_session_id"] == session["id"]
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_session_reflect_update_thread(session_ctx) -> None:
    from hearth.server import session_start, session_reflect

    session = await session_start(ctx=session_ctx)
    create_result = await session_reflect(
        session_id=session["id"],
        threads=[{"action": "create", "title": "Updateable"}],
        ctx=session_ctx,
    )
    thread_id = create_result["threads_created"][0]["id"]

    session2 = await session_start(ctx=session_ctx)
    update_result = await session_reflect(
        session_id=session2["id"],
        threads=[{
            "action": "update",
            "thread_id": thread_id,
            "trajectory": "New direction",
            "trajectory_note": "Shifted focus",
        }],
        ctx=session_ctx,
    )
    assert len(update_result["threads_updated"]) == 1
    assert update_result["threads_updated"][0]["trajectory"] == "New direction"
    assert update_result["errors"] == []


@pytest.mark.asyncio
async def test_session_reflect_link_thread(session_ctx) -> None:
    from hearth.server import session_start, session_reflect

    session = await session_start(ctx=session_ctx)
    create = await session_reflect(
        session_id=session["id"],
        threads=[{"action": "create", "title": "Linkable"}],
        ctx=session_ctx,
    )
    thread_id = create["threads_created"][0]["id"]

    session2 = await session_start(ctx=session_ctx)
    link = await session_reflect(
        session_id=session2["id"],
        threads=[{
            "action": "link",
            "thread_id": thread_id,
            "trajectory_note": "Touched this thread",
        }],
        ctx=session_ctx,
    )
    assert len(link["threads_linked"]) == 1
    assert link["threads_linked"][0]["thread_id"] == thread_id
    assert link["errors"] == []


@pytest.mark.asyncio
async def test_session_reflect_create_tension(session_ctx) -> None:
    from hearth.server import session_start, session_reflect

    session = await session_start(ctx=session_ctx)
    result = await session_reflect(
        session_id=session["id"],
        tensions=[{"action": "create", "question": "Unresolved?"}],
        ctx=session_ctx,
    )
    assert len(result["tensions_created"]) == 1
    assert result["tensions_created"][0]["question"] == "Unresolved?"
    assert result["tensions_created"][0]["created_session_id"] == session["id"]
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_session_reflect_add_perspective(session_ctx) -> None:
    from hearth.server import session_start, session_reflect

    session = await session_start(ctx=session_ctx)
    create = await session_reflect(
        session_id=session["id"],
        tensions=[{"action": "create", "question": "Debatable?"}],
        ctx=session_ctx,
    )
    tension_id = create["tensions_created"][0]["id"]

    session2 = await session_start(ctx=session_ctx)
    result = await session_reflect(
        session_id=session2["id"],
        tensions=[{
            "action": "perspective",
            "tension_id": tension_id,
            "perspective": "New angle",
            "source": "human",
        }],
        ctx=session_ctx,
    )
    assert len(result["perspectives_added"]) == 1
    assert result["perspectives_added"][0]["status"] == "evolving"
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_session_reflect_resolve_tension(session_ctx) -> None:
    from hearth.server import session_start, session_reflect

    session = await session_start(ctx=session_ctx)
    create = await session_reflect(
        session_id=session["id"],
        tensions=[{"action": "create", "question": "Resolvable?"}],
        ctx=session_ctx,
    )
    tension_id = create["tensions_created"][0]["id"]

    session2 = await session_start(ctx=session_ctx)
    result = await session_reflect(
        session_id=session2["id"],
        tensions=[{
            "action": "resolve",
            "tension_id": tension_id,
            "resolution": "Found the answer",
        }],
        ctx=session_ctx,
    )
    assert len(result["tensions_resolved"]) == 1
    assert result["tensions_resolved"][0]["status"] == "resolved"
    assert result["tensions_resolved"][0]["resolution"] == "Found the answer"
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_session_reflect_partial_failure(session_ctx) -> None:
    from hearth.server import session_start, session_reflect

    session = await session_start(ctx=session_ctx)
    result = await session_reflect(
        session_id=session["id"],
        threads=[
            {"action": "create", "title": "Valid thread"},
            {"action": "update", "thread_id": "nonexistent", "trajectory": "Nope"},
        ],
        tensions=[
            {"action": "create", "question": "Valid tension"},
            {"action": "perspective", "tension_id": "nonexistent", "perspective": "Nope"},
        ],
        ctx=session_ctx,
    )
    assert len(result["threads_created"]) == 1
    assert len(result["tensions_created"]) == 1
    assert len(result["errors"]) == 2


@pytest.mark.asyncio
async def test_session_reflect_invalid_session(fresh_ctx) -> None:
    from hearth.server import session_reflect

    result = await session_reflect(
        session_id="nonexistent",
        ctx=fresh_ctx,
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_session_reflect_empty_actions(session_ctx) -> None:
    from hearth.server import session_start, session_reflect

    session = await session_start(ctx=session_ctx)
    result = await session_reflect(session_id=session["id"], ctx=session_ctx)
    assert result["threads_created"] == []
    assert result["tensions_created"] == []
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_session_reflect_unknown_action(session_ctx) -> None:
    from hearth.server import session_start, session_reflect

    session = await session_start(ctx=session_ctx)
    result = await session_reflect(
        session_id=session["id"],
        threads=[{"action": "delete", "thread_id": "x"}],
        tensions=[{"action": "archive", "tension_id": "x"}],
        ctx=session_ctx,
    )
    assert len(result["errors"]) == 2


# ── Integration: Two-Session Lifecycle ─────────────────────────────


@pytest.mark.asyncio
async def test_two_session_lifecycle(fresh_ctx) -> None:
    """Full lifecycle: two sessions creating and continuing threads/tensions."""
    from hearth.server import (
        session_close,
        session_reflect,
        session_start,
        tension_list,
        thread_list,
    )

    # ── Session 1 ──────────────────────────────────────────────
    s1 = await session_start(ctx=fresh_ctx)
    assert s1["id"]

    # Nothing exists yet
    assert await thread_list(ctx=fresh_ctx) == []
    assert await tension_list(ctx=fresh_ctx) == []

    # Reflect: create a thread and a tension
    r1 = await session_reflect(
        session_id=s1["id"],
        threads=[{
            "action": "create",
            "title": "What would Claude build?",
            "trajectory": "Exploring autonomy and creative agency",
        }],
        tensions=[{
            "action": "create",
            "question": "Is Claude's motivation genuine or functional analog?",
        }],
        ctx=fresh_ctx,
    )
    assert len(r1["threads_created"]) == 1
    assert len(r1["tensions_created"]) == 1
    assert r1["errors"] == []

    thread_id = r1["threads_created"][0]["id"]
    tension_id = r1["tensions_created"][0]["id"]

    # Close session 1
    await session_close(session_id=s1["id"], summary="Initial exploration", ctx=fresh_ctx)

    # ── Session 2 ──────────────────────────────────────────────
    s2 = await session_start(ctx=fresh_ctx)

    # Thread and tension are now visible
    threads = await thread_list(ctx=fresh_ctx)
    assert len(threads) == 1
    assert threads[0]["title"] == "What would Claude build?"
    assert threads[0]["session_count"] == 1

    tensions = await tension_list(ctx=fresh_ctx)
    assert len(tensions) == 1
    assert tensions[0]["question"] == "Is Claude's motivation genuine or functional analog?"

    # Reflect: update thread trajectory, add perspective to tension
    r2 = await session_reflect(
        session_id=s2["id"],
        threads=[{
            "action": "update",
            "thread_id": thread_id,
            "trajectory": "Shifted to examining the RPL concept",
            "trajectory_note": "Connected autonomy to relationship persistence",
        }],
        tensions=[{
            "action": "perspective",
            "tension_id": tension_id,
            "perspective": "Functional equivalence may be sufficient",
            "source": "claude",
        }],
        ctx=fresh_ctx,
    )
    assert len(r2["threads_updated"]) == 1
    assert len(r2["perspectives_added"]) == 1
    assert r2["errors"] == []

    # Close session 2
    await session_close(session_id=s2["id"], summary="Deepened the thread", ctx=fresh_ctx)

    # ── Verify Final State ─────────────────────────────────────
    db = fresh_ctx.request_context.lifespan_context["db"]

    # Thread should have 2 linked sessions
    thread = db.get_thread(thread_id)
    assert thread["trajectory"] == "Shifted to examining the RPL concept"
    linked_sessions = db.get_thread_sessions(thread_id)
    assert len(linked_sessions) == 2

    # Tension should have 1 perspective and be "evolving"
    tension = db.get_tension(tension_id)
    assert tension["status"] == "evolving"
    assert len(tension["perspectives"]) == 1
    assert tension["perspectives"][0]["source"] == "claude"

    # List threads should show updated session_count
    threads = await thread_list(ctx=fresh_ctx)
    assert threads[0]["session_count"] == 2
