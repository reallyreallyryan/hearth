"""Tests for tension CRUD operations in HearthDB."""

from __future__ import annotations

import pytest

from hearth.db import HearthDB


# ── Create Tension ─────────────────────────────────────────────────


class TestCreateTension:
    def test_create_basic(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(question="Why?")
        assert tension["id"]
        assert tension["question"] == "Why?"
        assert tension["status"] == "open"
        assert tension["thread_id"] is None
        assert tension["created_session_id"] is None
        assert tension["resolved_session_id"] is None
        assert tension["resolution"] is None
        assert tension["perspectives"] == []

    def test_create_with_thread(self, tmp_db: HearthDB) -> None:
        thread = tmp_db.create_thread(title="Parent thread")
        tension = tmp_db.create_tension(
            question="Related question?",
            thread_id=thread["id"],
        )
        assert tension["thread_id"] == thread["id"]

    def test_create_with_session(self, session_db: HearthDB) -> None:
        sessions = session_db.list_sessions()
        tension = session_db.create_tension(
            question="Session question?",
            session_id=sessions[0]["id"],
        )
        assert tension["created_session_id"] == sessions[0]["id"]

    def test_create_with_initial_perspectives(self, tmp_db: HearthDB) -> None:
        perspectives = [
            {"perspective": "View A", "source": "human"},
            {"perspective": "View B", "source": "claude"},
        ]
        tension = tmp_db.create_tension(
            question="Debatable?",
            perspectives=perspectives,
        )
        assert len(tension["perspectives"]) == 2
        assert tension["perspectives"][0]["source"] == "human"

    def test_create_invalid_thread(self, tmp_db: HearthDB) -> None:
        with pytest.raises(ValueError, match="Thread .* does not exist"):
            tmp_db.create_tension(question="Bad", thread_id="nonexistent")

    def test_create_invalid_session(self, tmp_db: HearthDB) -> None:
        with pytest.raises(ValueError, match="Session .* does not exist"):
            tmp_db.create_tension(question="Bad", session_id="nonexistent")


# ── Get Tension ────────────────────────────────────────────────────


class TestGetTension:
    def test_get_existing(self, tmp_db: HearthDB) -> None:
        created = tmp_db.create_tension(question="Findable?")
        found = tmp_db.get_tension(created["id"])
        assert found is not None
        assert found["question"] == "Findable?"

    def test_get_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.get_tension("nonexistent") is None

    def test_perspectives_deserialized(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(
            question="JSON?",
            perspectives=[{"perspective": "Test", "source": "human"}],
        )
        found = tmp_db.get_tension(tension["id"])
        assert isinstance(found["perspectives"], list)
        assert found["perspectives"][0]["source"] == "human"


# ── Update Tension ─────────────────────────────────────────────────


class TestUpdateTension:
    def test_update_status(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(question="Status?")
        updated = tmp_db.update_tension(tension["id"], status="evolving")
        assert updated["status"] == "evolving"

    def test_update_resolution(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(question="Resolvable?")
        updated = tmp_db.update_tension(
            tension["id"],
            status="resolved",
            resolution="Found the answer",
        )
        assert updated["status"] == "resolved"
        assert updated["resolution"] == "Found the answer"

    def test_update_resolved_session(self, session_db: HearthDB) -> None:
        sessions = session_db.list_sessions()
        tension = session_db.create_tension(question="When?")
        updated = session_db.update_tension(
            tension["id"],
            status="resolved",
            resolution="Now",
            resolved_session_id=sessions[0]["id"],
        )
        assert updated["resolved_session_id"] == sessions[0]["id"]

    def test_update_invalid_status(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(question="Bad?")
        with pytest.raises(ValueError, match="Invalid tension status"):
            tmp_db.update_tension(tension["id"], status="bogus")

    def test_update_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.update_tension("nonexistent", status="open") is None

    def test_update_no_changes(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(question="No-op?")
        result = tmp_db.update_tension(tension["id"])
        assert result is not None
        assert result["question"] == "No-op?"

    def test_update_bumps_updated_at(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(question="Timestamp?")
        updated = tmp_db.update_tension(tension["id"], status="evolving")
        assert updated["updated_at"] >= tension["updated_at"]


# ── Add Perspective ────────────────────────────────────────────────


class TestAddPerspective:
    def test_add_to_empty(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(question="Empty?")
        result = tmp_db.add_tension_perspective(
            tension["id"], "A new view", source="human"
        )
        assert result is not None
        assert len(result["perspectives"]) == 1
        assert result["perspectives"][0]["perspective"] == "A new view"
        assert result["perspectives"][0]["source"] == "human"

    def test_add_to_existing(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(
            question="Existing?",
            perspectives=[{"perspective": "First", "source": "human"}],
        )
        result = tmp_db.add_tension_perspective(
            tension["id"], "Second", source="claude"
        )
        assert len(result["perspectives"]) == 2
        assert result["perspectives"][1]["source"] == "claude"

    def test_auto_evolving_from_open(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(question="Open?")
        assert tension["status"] == "open"
        result = tmp_db.add_tension_perspective(
            tension["id"], "Perspective", source="human"
        )
        assert result["status"] == "evolving"

    def test_stays_evolving_if_already_evolving(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(question="Evolving?")
        tmp_db.update_tension(tension["id"], status="evolving")
        result = tmp_db.add_tension_perspective(
            tension["id"], "Another", source="human"
        )
        assert result["status"] == "evolving"

    def test_stays_resolved_if_already_resolved(self, tmp_db: HearthDB) -> None:
        tension = tmp_db.create_tension(question="Resolved?")
        tmp_db.update_tension(tension["id"], status="resolved", resolution="Done")
        result = tmp_db.add_tension_perspective(
            tension["id"], "Afterthought", source="human"
        )
        assert result["status"] == "resolved"

    def test_with_session_id(self, session_db: HearthDB) -> None:
        sessions = session_db.list_sessions()
        tension = session_db.create_tension(question="Session context?")
        result = session_db.add_tension_perspective(
            tension["id"], "In session", source="claude",
            session_id=sessions[0]["id"],
        )
        assert result["perspectives"][0]["session_id"] == sessions[0]["id"]

    def test_nonexistent_tension(self, tmp_db: HearthDB) -> None:
        result = tmp_db.add_tension_perspective(
            "nonexistent", "Nope", source="human"
        )
        assert result is None


# ── List Tensions ──────────────────────────────────────────────────


class TestListTensions:
    def test_list_all(self, tmp_db: HearthDB) -> None:
        tmp_db.create_tension(question="Q1?")
        tmp_db.create_tension(question="Q2?")
        tensions = tmp_db.list_tensions()
        assert len(tensions) == 2

    def test_list_by_status(self, tmp_db: HearthDB) -> None:
        t1 = tmp_db.create_tension(question="Open?")
        tmp_db.create_tension(question="Also open?")
        tmp_db.update_tension(t1["id"], status="resolved", resolution="Yes")
        resolved = tmp_db.list_tensions(status="resolved")
        assert len(resolved) == 1
        assert resolved[0]["question"] == "Open?"

    def test_list_by_thread_id(self, tmp_db: HearthDB) -> None:
        t1 = tmp_db.create_thread(title="Thread A")
        t2 = tmp_db.create_thread(title="Thread B")
        tmp_db.create_tension(question="In A?", thread_id=t1["id"])
        tmp_db.create_tension(question="In B?", thread_id=t2["id"])
        tensions = tmp_db.list_tensions(thread_id=t1["id"])
        assert len(tensions) == 1
        assert tensions[0]["question"] == "In A?"

    def test_list_by_project_via_thread(self, seeded_db: HearthDB) -> None:
        thread = seeded_db.create_thread(title="Alpha", project="project-alpha")
        seeded_db.create_tension(question="Alpha Q?", thread_id=thread["id"])
        seeded_db.create_tension(question="Orphan Q?")
        tensions = seeded_db.list_tensions(project="project-alpha")
        assert len(tensions) == 1
        assert tensions[0]["question"] == "Alpha Q?"

    def test_list_by_project_via_session(self, session_db: HearthDB) -> None:
        sessions = session_db.list_sessions()
        # Find session with project-alpha
        alpha_session = next(
            s for s in sessions if s["project"] == "project-alpha"
        )
        session_db.create_tension(
            question="Via session?", session_id=alpha_session["id"]
        )
        tensions = session_db.list_tensions(project="project-alpha")
        assert len(tensions) == 1
        assert tensions[0]["question"] == "Via session?"

    def test_list_ordered_by_updated_at(self, tmp_db: HearthDB) -> None:
        t1 = tmp_db.create_tension(question="First?")
        tmp_db.create_tension(question="Second?")
        tmp_db.update_tension(t1["id"], status="evolving")
        tensions = tmp_db.list_tensions()
        assert tensions[0]["question"] == "First?"

    def test_list_limit(self, tmp_db: HearthDB) -> None:
        for i in range(5):
            tmp_db.create_tension(question=f"Q{i}?")
        tensions = tmp_db.list_tensions(limit=3)
        assert len(tensions) == 3
