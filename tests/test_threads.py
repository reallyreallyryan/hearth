"""Tests for thread CRUD operations in HearthDB."""

from __future__ import annotations

import pytest

from hearth.db import HearthDB


# ── Create Thread ──────────────────────────────────────────────────


class TestCreateThread:
    def test_create_basic(self, tmp_db: HearthDB) -> None:
        thread = tmp_db.create_thread(title="Test thread")
        assert thread["id"]
        assert thread["title"] == "Test thread"
        assert thread["status"] == "open"
        assert thread["project"] is None
        assert thread["trajectory"] is None
        assert thread["created_session_id"] is None
        assert thread["created_at"]
        assert thread["updated_at"]

    def test_create_with_project(self, seeded_db: HearthDB) -> None:
        thread = seeded_db.create_thread(
            title="Project thread",
            project="project-alpha",
        )
        assert thread["project"] == "project-alpha"

    def test_create_with_all_fields(self, session_db: HearthDB) -> None:
        sessions = session_db.list_sessions()
        sid = sessions[0]["id"]
        thread = session_db.create_thread(
            title="Full thread",
            project="project-alpha",
            session_id=sid,
            trajectory="Exploring something",
        )
        assert thread["project"] == "project-alpha"
        assert thread["created_session_id"] == sid
        assert thread["trajectory"] == "Exploring something"

    def test_create_with_session_auto_links(self, session_db: HearthDB) -> None:
        sessions = session_db.list_sessions()
        sid = sessions[0]["id"]
        thread = session_db.create_thread(title="Auto-link", session_id=sid)
        linked = session_db.get_thread_sessions(thread["id"])
        assert len(linked) == 1
        assert linked[0]["id"] == sid

    def test_create_invalid_project(self, tmp_db: HearthDB) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            tmp_db.create_thread(title="Bad", project="nonexistent")

    def test_create_invalid_session(self, seeded_db: HearthDB) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            seeded_db.create_thread(title="Bad", session_id="nonexistent")


# ── Get Thread ─────────────────────────────────────────────────────


class TestGetThread:
    def test_get_existing(self, tmp_db: HearthDB) -> None:
        created = tmp_db.create_thread(title="Findable")
        found = tmp_db.get_thread(created["id"])
        assert found is not None
        assert found["title"] == "Findable"

    def test_get_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.get_thread("nonexistent") is None


# ── Update Thread ──────────────────────────────────────────────────


class TestUpdateThread:
    def test_update_title(self, tmp_db: HearthDB) -> None:
        thread = tmp_db.create_thread(title="Old title")
        updated = tmp_db.update_thread(thread["id"], title="New title")
        assert updated is not None
        assert updated["title"] == "New title"

    def test_update_status(self, tmp_db: HearthDB) -> None:
        thread = tmp_db.create_thread(title="Status test")
        updated = tmp_db.update_thread(thread["id"], status="parked")
        assert updated["status"] == "parked"

    def test_update_trajectory(self, tmp_db: HearthDB) -> None:
        thread = tmp_db.create_thread(title="Trajectory test")
        updated = tmp_db.update_thread(thread["id"], trajectory="New direction")
        assert updated["trajectory"] == "New direction"

    def test_update_bumps_updated_at(self, tmp_db: HearthDB) -> None:
        thread = tmp_db.create_thread(title="Timestamp test")
        updated = tmp_db.update_thread(thread["id"], title="Changed")
        assert updated["updated_at"] >= thread["updated_at"]

    def test_update_invalid_status(self, tmp_db: HearthDB) -> None:
        thread = tmp_db.create_thread(title="Bad status")
        with pytest.raises(ValueError, match="Invalid thread status"):
            tmp_db.update_thread(thread["id"], status="invalid")

    def test_update_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.update_thread("nonexistent", title="Nope") is None

    def test_update_no_changes(self, tmp_db: HearthDB) -> None:
        thread = tmp_db.create_thread(title="No-op")
        result = tmp_db.update_thread(thread["id"])
        assert result is not None
        assert result["title"] == "No-op"


# ── List Threads ───────────────────────────────────────────────────


class TestListThreads:
    def test_list_all(self, tmp_db: HearthDB) -> None:
        tmp_db.create_thread(title="Thread A")
        tmp_db.create_thread(title="Thread B")
        threads = tmp_db.list_threads()
        assert len(threads) == 2

    def test_list_by_project(self, seeded_db: HearthDB) -> None:
        seeded_db.create_thread(title="Alpha thread", project="project-alpha")
        seeded_db.create_thread(title="Beta thread", project="project-beta")
        alpha = seeded_db.list_threads(project="project-alpha")
        assert len(alpha) == 1
        assert alpha[0]["title"] == "Alpha thread"

    def test_list_by_status(self, tmp_db: HearthDB) -> None:
        t1 = tmp_db.create_thread(title="Open")
        tmp_db.create_thread(title="Also open")
        tmp_db.update_thread(t1["id"], status="parked")
        parked = tmp_db.list_threads(status="parked")
        assert len(parked) == 1
        assert parked[0]["title"] == "Open"

    def test_list_includes_session_count(self, session_db: HearthDB) -> None:
        sessions = session_db.list_sessions()
        thread = session_db.create_thread(
            title="Linked", session_id=sessions[0]["id"]
        )
        session_db.link_thread_session(thread["id"], sessions[1]["id"])
        threads = session_db.list_threads()
        assert threads[0]["session_count"] == 2

    def test_list_includes_tension_count(self, tmp_db: HearthDB) -> None:
        thread = tmp_db.create_thread(title="Has tensions")
        tmp_db.create_tension(question="Q1?", thread_id=thread["id"])
        tmp_db.create_tension(question="Q2?", thread_id=thread["id"])
        threads = tmp_db.list_threads()
        assert threads[0]["tension_count"] == 2

    def test_list_ordered_by_updated_at(self, tmp_db: HearthDB) -> None:
        t1 = tmp_db.create_thread(title="First")
        tmp_db.create_thread(title="Second")
        # Update first thread so it becomes most recently updated
        tmp_db.update_thread(t1["id"], title="First updated")
        threads = tmp_db.list_threads()
        assert threads[0]["title"] == "First updated"

    def test_list_limit(self, tmp_db: HearthDB) -> None:
        for i in range(5):
            tmp_db.create_thread(title=f"Thread {i}")
        threads = tmp_db.list_threads(limit=3)
        assert len(threads) == 3


# ── Link Thread Session ────────────────────────────────────────────


class TestLinkThreadSession:
    def test_link_basic(self, session_db: HearthDB) -> None:
        thread = session_db.create_thread(title="Linkable")
        sessions = session_db.list_sessions()
        session_db.link_thread_session(thread["id"], sessions[0]["id"])
        linked = session_db.get_thread_sessions(thread["id"])
        assert len(linked) == 1

    def test_link_with_trajectory_note(self, session_db: HearthDB) -> None:
        thread = session_db.create_thread(title="Noted")
        sessions = session_db.list_sessions()
        session_db.link_thread_session(
            thread["id"], sessions[0]["id"],
            trajectory_note="Made progress here",
        )
        linked = session_db.get_thread_sessions(thread["id"])
        assert linked[0]["trajectory_note"] == "Made progress here"

    def test_link_upsert_updates_note(self, session_db: HearthDB) -> None:
        thread = session_db.create_thread(title="Upsert")
        sessions = session_db.list_sessions()
        sid = sessions[0]["id"]
        session_db.link_thread_session(thread["id"], sid, trajectory_note="V1")
        session_db.link_thread_session(thread["id"], sid, trajectory_note="V2")
        linked = session_db.get_thread_sessions(thread["id"])
        assert len(linked) == 1
        assert linked[0]["trajectory_note"] == "V2"

    def test_link_updates_thread_updated_at(self, session_db: HearthDB) -> None:
        thread = session_db.create_thread(title="Timestamp")
        sessions = session_db.list_sessions()
        session_db.link_thread_session(thread["id"], sessions[0]["id"])
        updated = session_db.get_thread(thread["id"])
        assert updated["updated_at"] >= thread["updated_at"]

    def test_link_nonexistent_thread(self, session_db: HearthDB) -> None:
        sessions = session_db.list_sessions()
        with pytest.raises(ValueError, match="Thread .* does not exist"):
            session_db.link_thread_session("nonexistent", sessions[0]["id"])

    def test_link_nonexistent_session(self, tmp_db: HearthDB) -> None:
        thread = tmp_db.create_thread(title="No session")
        with pytest.raises(ValueError, match="Session .* does not exist"):
            tmp_db.link_thread_session(thread["id"], "nonexistent")


# ── Get Thread Sessions ───────────────────────────────────────────


class TestGetThreadSessions:
    def test_get_linked_sessions(self, session_db: HearthDB) -> None:
        sessions = session_db.list_sessions()
        thread = session_db.create_thread(title="Multi-session")
        session_db.link_thread_session(thread["id"], sessions[0]["id"], "Note A")
        session_db.link_thread_session(thread["id"], sessions[1]["id"], "Note B")
        linked = session_db.get_thread_sessions(thread["id"])
        assert len(linked) == 2
        # Each linked session should have summary and trajectory_note
        assert all("summary" in s for s in linked)
        assert all("trajectory_note" in s for s in linked)

    def test_get_empty(self, tmp_db: HearthDB) -> None:
        thread = tmp_db.create_thread(title="Lonely")
        linked = tmp_db.get_thread_sessions(thread["id"])
        assert linked == []

    def test_ordered_by_started_at(self, session_db: HearthDB) -> None:
        sessions = session_db.list_sessions()
        thread = session_db.create_thread(title="Ordered")
        # Link both sessions (list_sessions returns newest first)
        session_db.link_thread_session(thread["id"], sessions[0]["id"])
        session_db.link_thread_session(thread["id"], sessions[1]["id"])
        linked = session_db.get_thread_sessions(thread["id"])
        assert linked[0]["started_at"] <= linked[1]["started_at"]
