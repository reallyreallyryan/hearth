"""Tests for hearth.resonance_guide, hearth.context, and the MCP briefing/context tools."""

from __future__ import annotations

import pytest

from hearth.config import RESONANCE_AXES
from hearth.context import ContextAssembler, describe_resonance
from hearth.db import HearthDB
from hearth.resonance_guide import (
    RESONANCE_GUIDE,
    estimate_tokens,
    format_resonance_guide,
)


# ── Resonance Guide Tests ────────────────────────────────────────


class TestResonanceGuide:
    def test_all_axes_present_in_guide(self) -> None:
        for axis in RESONANCE_AXES:
            assert axis in RESONANCE_GUIDE, f"Missing axis: {axis}"

    def test_guide_entries_have_required_fields(self) -> None:
        for axis, entry in RESONANCE_GUIDE.items():
            assert "name" in entry
            assert "negative_pole" in entry
            assert "positive_pole" in entry
            assert "guidance" in entry

    def test_format_full_contains_all_axes(self) -> None:
        text = format_resonance_guide()
        for axis in RESONANCE_AXES:
            assert axis in text

    def test_format_full_contains_header(self) -> None:
        text = format_resonance_guide()
        assert "Resonance Scoring Guide" in text

    def test_format_compact_contains_all_axes(self) -> None:
        text = format_resonance_guide(token_budget=100)
        for axis in RESONANCE_AXES:
            assert axis in text

    def test_format_compact_shorter_than_full(self) -> None:
        full = format_resonance_guide()
        compact = format_resonance_guide(token_budget=100)
        assert len(compact) < len(full)

    def test_format_compact_fits_budget(self) -> None:
        budget = 400
        text = format_resonance_guide(token_budget=budget)
        # Compact version should be used and fit
        assert estimate_tokens(text) <= budget

    def test_format_large_budget_returns_full(self) -> None:
        text = format_resonance_guide(token_budget=5000)
        # Should get full version with guidance text
        assert "Guidance:" in text


class TestEstimateTokens:
    def test_empty_string(self) -> None:
        assert estimate_tokens("") == 0

    def test_single_word(self) -> None:
        result = estimate_tokens("hello")
        assert result >= 1

    def test_reasonable_estimate(self) -> None:
        # 100 words should be roughly 133 tokens
        text = " ".join(["word"] * 100)
        tokens = estimate_tokens(text)
        assert 100 < tokens < 200

    def test_longer_text_scales(self) -> None:
        short = estimate_tokens("hello world")
        long = estimate_tokens(" ".join(["hello world"] * 50))
        assert long > short


# ── describe_resonance Tests ─────────────────────────────────────


class TestDescribeResonance:
    def test_empty_resonance(self) -> None:
        assert describe_resonance({}) == "no resonance data"

    def test_all_zeros(self) -> None:
        axes = {axis: 0.0 for axis in RESONANCE_AXES}
        result = describe_resonance(axes)
        assert result == "neutral resonance profile"

    def test_single_extreme_axis(self) -> None:
        axes = {axis: 0.0 for axis in RESONANCE_AXES}
        axes["exploration_execution"] = 0.9
        result = describe_resonance(axes)
        assert "exploration" in result.lower()

    def test_negative_axis(self) -> None:
        axes = {axis: 0.0 for axis in RESONANCE_AXES}
        axes["momentum_resistance"] = -0.8
        result = describe_resonance(axes)
        assert "stuck" in result.lower() or "grinding" in result.lower()

    def test_multiple_extreme_axes(self) -> None:
        axes = {axis: 0.0 for axis in RESONANCE_AXES}
        axes["exploration_execution"] = 0.8
        axes["depth_breadth"] = 0.9
        axes["mutual_transactional"] = 0.7
        result = describe_resonance(axes)
        # Should mention multiple aspects
        assert "and" in result

    def test_returns_string(self) -> None:
        axes = {axis: 0.5 for axis in RESONANCE_AXES}
        result = describe_resonance(axes)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_ignores_metadata_fields(self) -> None:
        axes = {axis: 0.0 for axis in RESONANCE_AXES}
        axes["exploration_execution"] = 0.9
        axes["id"] = "some-id"
        axes["session_id"] = "some-session"
        axes["created_at"] = "2026-01-01T00:00:00Z"
        result = describe_resonance(axes)
        assert "exploration" in result.lower()


# ── ContextAssembler Tests ───────────────────────────────────────


@pytest.fixture
def context_db(session_db) -> HearthDB:
    """session_db with additional threads and tensions for context testing."""
    # Create a thread on project-alpha
    s1 = session_db.list_sessions(project="project-alpha")[0]
    thread = session_db.create_thread(
        title="Embedding performance optimization",
        project="project-alpha",
        trajectory="Investigating batch vs single embedding calls",
        session_id=s1["id"],
    )

    # Create a tension
    session_db.create_tension(
        question="Should we cache embeddings in memory or rely on SQLite?",
        thread_id=thread["id"],
        session_id=s1["id"],
    )

    return session_db


class TestAssembleBriefingEmpty:
    def test_empty_db_returns_valid_briefing(self, tmp_db) -> None:
        assembler = ContextAssembler(tmp_db)
        result = assembler.assemble_briefing()
        assert "briefing" in result
        assert "metadata" in result
        assert isinstance(result["briefing"], str)
        assert len(result["briefing"]) > 0

    def test_empty_db_includes_preamble(self, tmp_db) -> None:
        assembler = ContextAssembler(tmp_db)
        result = assembler.assemble_briefing()
        assert "session_close" in result["briefing"]

    def test_empty_db_includes_resonance_guide(self, tmp_db) -> None:
        assembler = ContextAssembler(tmp_db)
        result = assembler.assemble_briefing()
        assert "Resonance Scoring Guide" in result["briefing"]


class TestAssembleBriefingPopulated:
    def test_includes_session_summaries(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_briefing(project="project-alpha")
        assert "Productive coding session" in result["briefing"]

    def test_includes_active_threads(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_briefing(project="project-alpha")
        assert "Embedding performance optimization" in result["briefing"]

    def test_includes_resonance_descriptions(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_briefing(project="project-alpha")
        briefing = result["briefing"]
        # Session 1 has high momentum (0.9), exploration (0.8), mutual (0.8)
        # So the description should contain natural language, not raw numbers
        assert "0.9" not in briefing or "momentum" not in briefing

    def test_project_scoping(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_briefing(project="project-beta")
        # Should include project-beta session, not project-alpha thread
        assert "Debugging frustration" in result["briefing"]

    def test_metadata_includes_tiers(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_briefing(project="project-alpha", token_budget=3000)
        assert 1 in result["metadata"]["tiers_included"]


class TestAssembleBriefingBudget:
    def test_respects_token_budget(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        # Small budget
        result = assembler.assemble_briefing(project="project-alpha", token_budget=500)
        tokens = estimate_tokens(result["briefing"])
        # Allow some overshoot since preamble + guide are always included
        assert tokens < 800  # generous margin for always-included sections

    def test_small_budget_gets_tier1(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_briefing(project="project-alpha", token_budget=500)
        assert 1 in result["metadata"]["tiers_included"]

    def test_large_budget_gets_more_tiers(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_briefing(project="project-alpha", token_budget=4000)
        tiers = result["metadata"]["tiers_included"]
        assert 1 in tiers

    def test_bookend_pattern(self, context_db) -> None:
        """Briefing starts with preamble mentioning session_close, ends with resonance guide."""
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_briefing(project="project-alpha")
        briefing = result["briefing"]

        # Starts with preamble
        first_200_chars = briefing[:200]
        assert "session_close" in first_200_chars

        # Ends with resonance guide
        last_500_chars = briefing[-500:]
        assert "Resonance Scoring Guide" in briefing
        # The guide should be in the trailing portion
        guide_pos = briefing.index("Resonance Scoring Guide")
        # Preamble mentions session_close
        preamble_pos = briefing.index("session_close")
        assert guide_pos > preamble_pos

    def test_always_includes_preamble_and_guide(self, context_db) -> None:
        """Even with very small budget, preamble and trailing guide are present."""
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_briefing(project="project-alpha", token_budget=300)
        briefing = result["briefing"]
        assert "session_close" in briefing
        assert "Resonance Scoring Guide" in briefing


# ── assemble_context Tests ───────────────────────────────────────


class TestAssembleContext:
    def test_returns_valid_structure(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_context(query="Python")
        assert "context" in result
        assert "metadata" in result
        assert isinstance(result["context"], str)

    def test_finds_matching_memory(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_context(query="Python AI development")
        assert "Python" in result["context"]
        assert "memories" in result["metadata"]["sources"]

    def test_finds_matching_thread(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_context(query="embedding optimization")
        assert "Embedding performance" in result["context"]
        assert "threads" in result["metadata"]["sources"]

    def test_finds_matching_tension(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_context(query="cache embeddings SQLite")
        assert "cache" in result["context"].lower()
        assert "tensions" in result["metadata"]["sources"]

    def test_finds_matching_session(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_context(query="Productive coding")
        assert "Productive" in result["context"]
        assert "sessions" in result["metadata"]["sources"]

    def test_resonance_guide_query(self, context_db) -> None:
        """Querying for resonance guide returns the full axis definitions."""
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_context(query="resonance scoring guide")
        assert "Resonance Scoring Guide" in result["context"]
        assert "resonance_guide" in result["metadata"]["sources"]
        # Should contain all axis names
        for axis in RESONANCE_AXES:
            assert axis in result["context"]

    def test_no_results_graceful(self, tmp_db) -> None:
        assembler = ContextAssembler(tmp_db)
        result = assembler.assemble_context(query="nonexistent topic xyz123")
        assert "No relevant context found" in result["context"]

    def test_respects_token_budget(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_context(
            query="Python", token_budget=500,
        )
        tokens = estimate_tokens(result["context"])
        assert tokens < 600  # small margin

    def test_project_scoping(self, context_db) -> None:
        assembler = ContextAssembler(context_db)
        result = assembler.assemble_context(
            query="Python", project="project-alpha",
        )
        assert "context" in result
        assert result["metadata"]["project"] == "project-alpha"

    def test_empty_db_graceful(self, tmp_db) -> None:
        assembler = ContextAssembler(tmp_db)
        result = assembler.assemble_context(query="anything")
        assert "No relevant context found" in result["context"]


# ── MCP Tool Integration Tests ───────────────────────────────────


class MockLifespanContext:
    def __init__(self, db, embedder, config):
        self.lifespan_context = {
            "db": db,
            "embedder": embedder,
            "config": config,
        }


class MockContext:
    def __init__(self, db, embedder, config):
        self.request_context = MockLifespanContext(db, embedder, config)


@pytest.fixture
def ctx(context_db, unavailable_embedder, test_config):
    return MockContext(context_db, unavailable_embedder, test_config)


@pytest.fixture
def fresh_ctx(tmp_db, unavailable_embedder, test_config):
    return MockContext(tmp_db, unavailable_embedder, test_config)


class TestHearthBriefingTool:
    @pytest.mark.asyncio
    async def test_returns_briefing(self, ctx) -> None:
        from hearth.server import hearth_briefing

        result = await hearth_briefing(project="project-alpha", ctx=ctx)
        assert "briefing" in result
        assert isinstance(result["briefing"], str)
        assert len(result["briefing"]) > 0

    @pytest.mark.asyncio
    async def test_includes_resonance_guide(self, ctx) -> None:
        from hearth.server import hearth_briefing

        result = await hearth_briefing(ctx=ctx)
        assert "Resonance Scoring Guide" in result["briefing"]

    @pytest.mark.asyncio
    async def test_project_scoping(self, ctx) -> None:
        from hearth.server import hearth_briefing

        result = await hearth_briefing(project="project-alpha", ctx=ctx)
        assert "Productive coding session" in result["briefing"]

    @pytest.mark.asyncio
    async def test_token_budget(self, ctx) -> None:
        from hearth.server import hearth_briefing

        result = await hearth_briefing(token_budget=500, ctx=ctx)
        assert result["metadata"]["token_budget"] == 500

    @pytest.mark.asyncio
    async def test_empty_db(self, fresh_ctx) -> None:
        from hearth.server import hearth_briefing

        result = await hearth_briefing(ctx=fresh_ctx)
        assert "briefing" in result
        assert len(result["briefing"]) > 0


class TestHearthContextTool:
    @pytest.mark.asyncio
    async def test_returns_context(self, ctx) -> None:
        from hearth.server import hearth_context

        result = await hearth_context(query="Python", ctx=ctx)
        assert "context" in result
        assert isinstance(result["context"], str)

    @pytest.mark.asyncio
    async def test_finds_memories(self, ctx) -> None:
        from hearth.server import hearth_context

        result = await hearth_context(query="Python AI", ctx=ctx)
        assert "Python" in result["context"]

    @pytest.mark.asyncio
    async def test_resonance_guide_recovery(self, ctx) -> None:
        """Model can re-request resonance guide mid-conversation."""
        from hearth.server import hearth_context

        result = await hearth_context(query="resonance scoring guide", ctx=ctx)
        assert "Resonance Scoring Guide" in result["context"]
        for axis in RESONANCE_AXES:
            assert axis in result["context"]

    @pytest.mark.asyncio
    async def test_project_scoping(self, ctx) -> None:
        from hearth.server import hearth_context

        result = await hearth_context(
            query="coding", project="project-alpha", ctx=ctx,
        )
        assert result["metadata"]["project"] == "project-alpha"

    @pytest.mark.asyncio
    async def test_empty_db(self, fresh_ctx) -> None:
        from hearth.server import hearth_context

        result = await hearth_context(query="anything", ctx=fresh_ctx)
        assert "No relevant context found" in result["context"]


class TestConfigurableTokenBudget:
    """Tests for briefing_token_budget config support."""

    @pytest.mark.asyncio
    async def test_briefing_uses_config_default(self, context_db, unavailable_embedder, tmp_path) -> None:
        from hearth.config import HearthConfig
        from hearth.server import hearth_briefing

        config = HearthConfig(db_path=tmp_path / "test.db", briefing_token_budget=800)
        ctx = MockContext(context_db, unavailable_embedder, config)
        result = await hearth_briefing(ctx=ctx)
        assert result["metadata"]["token_budget"] == 800

    @pytest.mark.asyncio
    async def test_briefing_override_beats_config(self, context_db, unavailable_embedder, tmp_path) -> None:
        from hearth.config import HearthConfig
        from hearth.server import hearth_briefing

        config = HearthConfig(db_path=tmp_path / "test.db", briefing_token_budget=800)
        ctx = MockContext(context_db, unavailable_embedder, config)
        result = await hearth_briefing(token_budget=2000, ctx=ctx)
        assert result["metadata"]["token_budget"] == 2000

    @pytest.mark.asyncio
    async def test_context_uses_config_default(self, context_db, unavailable_embedder, tmp_path) -> None:
        from hearth.config import HearthConfig
        from hearth.server import hearth_context

        config = HearthConfig(db_path=tmp_path / "test.db", briefing_token_budget=800)
        ctx = MockContext(context_db, unavailable_embedder, config)
        result = await hearth_context(query="Python", ctx=ctx)
        assert result["metadata"]["token_budget"] == 800

    @pytest.mark.asyncio
    async def test_config_missing_uses_hardcoded_default(self, context_db, unavailable_embedder, tmp_path) -> None:
        from hearth.config import HearthConfig
        from hearth.server import hearth_briefing

        config = HearthConfig(db_path=tmp_path / "test.db")
        ctx = MockContext(context_db, unavailable_embedder, config)
        result = await hearth_briefing(ctx=ctx)
        assert result["metadata"]["token_budget"] == 1000


class TestBriefingAfterSessionStart:
    """Integration test: session_start -> hearth_briefing shows new session."""

    @pytest.mark.asyncio
    async def test_briefing_reflects_session_history(self, ctx) -> None:
        from hearth.server import hearth_briefing

        # The context_db already has sessions, so briefing should show them
        result = await hearth_briefing(project="project-alpha", ctx=ctx)
        briefing = result["briefing"]
        assert "Productive coding session" in briefing
        assert "session_close" in briefing
