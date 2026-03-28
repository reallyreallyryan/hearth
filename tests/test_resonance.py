"""Tests for the resonance layer: sessions, resonance axes, and session-memory links."""

from __future__ import annotations

import pytest

from hearth.config import RESONANCE_AXES
from hearth.db import HearthDB


def _full_axes(**overrides: float) -> dict[str, float]:
    """Return a complete 11-axis dict defaulting to 0.0, with optional overrides."""
    axes = {axis: 0.0 for axis in RESONANCE_AXES}
    axes.update(overrides)
    return axes


# ── Session CRUD ───────────────────────────────────────────────────


class TestCreateSession:
    def test_create_basic(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        assert len(session["id"]) == 32
        assert session["project"] is None
        assert session["started_at"] is not None
        assert session["ended_at"] is None
        assert session["summary"] is None
        assert session["memory_count"] == 0

    def test_create_with_project(self, seeded_db: HearthDB) -> None:
        session = seeded_db.create_session(project="project-alpha")
        assert session["project"] == "project-alpha"

    def test_create_nonexistent_project(self, tmp_db: HearthDB) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            tmp_db.create_session(project="nonexistent")

    def test_id_format(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        assert len(session["id"]) == 32
        int(session["id"], 16)  # Valid hex


class TestGetSession:
    def test_get_existing(self, tmp_db: HearthDB) -> None:
        created = tmp_db.create_session()
        fetched = tmp_db.get_session(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]

    def test_get_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.get_session("nonexistent") is None


class TestCloseSession:
    def test_close_with_summary(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        closed = tmp_db.close_session(session["id"], summary="Great session")
        assert closed is not None
        assert closed["summary"] == "Great session"
        assert closed["ended_at"] is not None

    def test_close_sets_ended_at(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        closed = tmp_db.close_session(session["id"])
        assert closed["ended_at"] is not None

    def test_close_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.close_session("nonexistent") is None

    def test_reclose_updates_summary(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        tmp_db.close_session(session["id"], summary="First")
        reclosed = tmp_db.close_session(session["id"], summary="Second")
        assert reclosed["summary"] == "Second"


class TestListSessions:
    def test_list_all(self, tmp_db: HearthDB) -> None:
        tmp_db.create_session()
        tmp_db.create_session()
        sessions = tmp_db.list_sessions()
        assert len(sessions) == 2

    def test_list_by_project(self, seeded_db: HearthDB) -> None:
        seeded_db.create_session(project="project-alpha")
        seeded_db.create_session(project="project-beta")
        seeded_db.create_session()  # global
        sessions = seeded_db.list_sessions(project="project-alpha")
        assert len(sessions) == 1
        assert all(s["project"] == "project-alpha" for s in sessions)

    def test_list_ordered_newest_first(self, tmp_db: HearthDB) -> None:
        s1 = tmp_db.create_session()
        s2 = tmp_db.create_session()
        sessions = tmp_db.list_sessions()
        assert sessions[0]["id"] == s2["id"]
        assert sessions[1]["id"] == s1["id"]

    def test_list_limit_offset(self, tmp_db: HearthDB) -> None:
        for _ in range(5):
            tmp_db.create_session()
        assert len(tmp_db.list_sessions(limit=2)) == 2
        assert len(tmp_db.list_sessions(limit=2, offset=4)) == 1


# ── Resonance ──────────────────────────────────────────────────────


class TestStoreResonance:
    def test_store_valid(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        axes = _full_axes(exploration_execution=0.9, alignment_tension=-0.5)
        result = tmp_db.store_resonance(session["id"], axes)
        assert result["session_id"] == session["id"]
        assert result["exploration_execution"] == 0.9
        assert result["alignment_tension"] == -0.5
        assert result["created_at"] is not None
        assert len(result["id"]) == 32

    def test_store_missing_axes(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        with pytest.raises(ValueError, match="Missing resonance axes"):
            tmp_db.store_resonance(session["id"], {"exploration_execution": 0.5})

    def test_store_extra_axes(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        axes = _full_axes()
        axes["bogus_axis"] = 0.5
        with pytest.raises(ValueError, match="Unknown resonance axes"):
            tmp_db.store_resonance(session["id"], axes)

    def test_store_out_of_range(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        axes = _full_axes(exploration_execution=1.5)
        with pytest.raises(ValueError, match="must be in"):
            tmp_db.store_resonance(session["id"], axes)

    def test_store_negative_out_of_range(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        axes = _full_axes(depth_breadth=-1.1)
        with pytest.raises(ValueError, match="must be in"):
            tmp_db.store_resonance(session["id"], axes)

    def test_store_nonexistent_session(self, tmp_db: HearthDB) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            tmp_db.store_resonance("nonexistent", _full_axes())


class TestGetResonance:
    def test_get_existing(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        axes = _full_axes(momentum_resistance=0.7)
        tmp_db.store_resonance(session["id"], axes)
        result = tmp_db.get_resonance(session["id"])
        assert result is not None
        assert result["session_id"] == session["id"]
        assert result["momentum_resistance"] == pytest.approx(0.7, abs=1e-5)

    def test_get_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.get_resonance("nonexistent") is None


class TestSearchResonance:
    def test_search_finds_similar(self, tmp_db: HearthDB) -> None:
        # Session A: high exploration
        sa = tmp_db.create_session()
        tmp_db.store_resonance(sa["id"], _full_axes(exploration_execution=0.9))

        # Session B: high execution (opposite)
        sb = tmp_db.create_session()
        tmp_db.store_resonance(sb["id"], _full_axes(exploration_execution=-0.9))

        # Search near high exploration — A should be closer
        results = tmp_db.search_resonance(_full_axes(exploration_execution=0.8))
        assert len(results) == 2
        assert results[0][0] == sa["id"]  # Closer match first
        assert results[0][1] < results[1][1]  # Lower distance

    def test_search_empty(self, tmp_db: HearthDB) -> None:
        results = tmp_db.search_resonance(_full_axes())
        assert results == []

    def test_search_limit(self, tmp_db: HearthDB) -> None:
        for i in range(5):
            s = tmp_db.create_session()
            tmp_db.store_resonance(s["id"], _full_axes(exploration_execution=i * 0.2))
        results = tmp_db.search_resonance(_full_axes(), limit=3)
        assert len(results) == 3

    def test_vec0_populated_on_store(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        axes = _full_axes(novelty_familiarity=0.5, stakes_casual=0.3)
        tmp_db.store_resonance(session["id"], axes)
        results = tmp_db.search_resonance(axes, limit=1)
        assert len(results) == 1
        assert results[0][0] == session["id"]
        assert results[0][1] == pytest.approx(0.0, abs=1e-5)  # Exact match


# ── Session-Memory Links ──────────────────────────────────────────


class TestLinkMemoryToSession:
    def test_link_basic(self, seeded_db: HearthDB) -> None:
        session = seeded_db.create_session()
        memories = seeded_db.list_memories()
        seeded_db.link_memory_to_session(session["id"], memories[0]["id"])
        updated = seeded_db.get_session(session["id"])
        assert updated["memory_count"] == 1

    def test_link_increments_count(self, seeded_db: HearthDB) -> None:
        session = seeded_db.create_session()
        memories = seeded_db.list_memories()
        seeded_db.link_memory_to_session(session["id"], memories[0]["id"])
        seeded_db.link_memory_to_session(session["id"], memories[1]["id"])
        updated = seeded_db.get_session(session["id"])
        assert updated["memory_count"] == 2

    def test_link_duplicate_no_op(self, seeded_db: HearthDB) -> None:
        session = seeded_db.create_session()
        memories = seeded_db.list_memories()
        seeded_db.link_memory_to_session(session["id"], memories[0]["id"])
        seeded_db.link_memory_to_session(session["id"], memories[0]["id"])  # duplicate
        updated = seeded_db.get_session(session["id"])
        assert updated["memory_count"] == 1  # Not double-counted

    def test_link_nonexistent_session(self, seeded_db: HearthDB) -> None:
        memories = seeded_db.list_memories()
        with pytest.raises(ValueError, match="Session"):
            seeded_db.link_memory_to_session("nonexistent", memories[0]["id"])

    def test_link_nonexistent_memory(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        with pytest.raises(ValueError, match="Memory"):
            tmp_db.link_memory_to_session(session["id"], "nonexistent")

    def test_action_types(self, seeded_db: HearthDB) -> None:
        session = seeded_db.create_session()
        memories = seeded_db.list_memories()
        seeded_db.link_memory_to_session(session["id"], memories[0]["id"], action="accessed")
        linked = seeded_db.get_session_memories(session["id"])
        assert linked[0]["action"] == "accessed"


class TestGetSessionMemories:
    def test_get_linked_memories(self, seeded_db: HearthDB) -> None:
        session = seeded_db.create_session()
        memories = seeded_db.list_memories()
        seeded_db.link_memory_to_session(session["id"], memories[0]["id"], "created")
        seeded_db.link_memory_to_session(session["id"], memories[1]["id"], "accessed")
        linked = seeded_db.get_session_memories(session["id"])
        assert len(linked) == 2
        actions = {m["action"] for m in linked}
        assert actions == {"created", "accessed"}

    def test_get_empty(self, tmp_db: HearthDB) -> None:
        session = tmp_db.create_session()
        assert tmp_db.get_session_memories(session["id"]) == []


# ── Integration ────────────────────────────────────────────────────


class TestResonanceIntegration:
    def test_full_flow(self, seeded_db: HearthDB) -> None:
        """Start session → store memories → close with resonance → search → find linked memories."""
        # Start session
        session = seeded_db.create_session(project="project-alpha")

        # Link some memories
        memories = seeded_db.list_memories(project="project-alpha")
        for mem in memories:
            seeded_db.link_memory_to_session(session["id"], mem["id"])

        # Close with resonance
        axes = _full_axes(
            exploration_execution=0.8,
            momentum_resistance=0.9,
            mutual_transactional=0.7,
        )
        seeded_db.close_session(session["id"], summary="Built the resonance layer")
        seeded_db.store_resonance(session["id"], axes)

        # Search resonance space
        results = seeded_db.search_resonance(
            _full_axes(exploration_execution=0.7, momentum_resistance=0.8), limit=5
        )
        assert len(results) >= 1
        found_ids = [r[0] for r in results]
        assert session["id"] in found_ids

        # Get linked memories from found session
        linked = seeded_db.get_session_memories(session["id"])
        assert len(linked) == len(memories)

    def test_session_close_stores_both_tables(self, tmp_db: HearthDB) -> None:
        """Verify store_resonance populates both session_resonance and resonance_embeddings."""
        session = tmp_db.create_session()
        axes = _full_axes(depth_breadth=0.5)
        tmp_db.store_resonance(session["id"], axes)

        # session_resonance row exists
        res = tmp_db.get_resonance(session["id"])
        assert res is not None
        assert res["depth_breadth"] == pytest.approx(0.5, abs=1e-5)

        # resonance_embeddings vec0 row exists (searchable)
        results = tmp_db.search_resonance(axes, limit=1)
        assert len(results) == 1
        assert results[0][0] == session["id"]


class TestInitDBIdempotent:
    def test_double_init_with_resonance(self, tmp_db: HearthDB) -> None:
        """Calling init_db() twice should not error (IF NOT EXISTS + vec0 check)."""
        tmp_db.init_db()  # Second call
        # Verify session operations still work
        session = tmp_db.create_session()
        assert session["id"] is not None
        axes = _full_axes()
        tmp_db.store_resonance(session["id"], axes)
        result = tmp_db.get_resonance(session["id"])
        assert result is not None
