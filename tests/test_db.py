"""Tests for hearth.db — CRUD operations, triggers, validation, export."""

from __future__ import annotations

import json

import pytest

from hearth.db import HearthDB


# ── Memory CRUD ─────────────────────────────────────────────────────


class TestStoreMemory:
    def test_store_basic(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test content")
        assert mem["content"] == "Test content"
        assert mem["category"] == "general"
        assert mem["project"] is None
        assert mem["tags"] == []
        assert mem["source"] == "user"
        assert mem["archived"] is False
        assert len(mem["id"]) == 32  # hex(16 bytes)

    def test_store_with_all_fields(self, tmp_db: HearthDB) -> None:
        tmp_db.create_project("proj", "desc")
        mem = tmp_db.store_memory(
            "Full memory",
            category="learning",
            project="proj",
            tags=["tag1", "tag2"],
            source="assistant",
        )
        assert mem["category"] == "learning"
        assert mem["project"] == "proj"
        assert mem["tags"] == ["tag1", "tag2"]
        assert mem["source"] == "assistant"

    def test_store_invalid_category(self, tmp_db: HearthDB) -> None:
        with pytest.raises(ValueError, match="Invalid category"):
            tmp_db.store_memory("test", category="invalid")

    def test_store_invalid_source(self, tmp_db: HearthDB) -> None:
        with pytest.raises(ValueError, match="Invalid source"):
            tmp_db.store_memory("test", source="invalid")

    def test_store_nonexistent_project(self, tmp_db: HearthDB) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            tmp_db.store_memory("test", project="nonexistent")


class TestGetMemory:
    def test_get_existing(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test")
        fetched = tmp_db.get_memory(mem["id"])
        assert fetched is not None
        assert fetched["content"] == "Test"

    def test_get_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.get_memory("nonexistent") is None

    def test_tags_deserialized(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test", tags=["a", "b"])
        fetched = tmp_db.get_memory(mem["id"])
        assert fetched["tags"] == ["a", "b"]


class TestUpdateMemory:
    def test_update_content(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Original")
        updated = tmp_db.update_memory(mem["id"], content="Updated")
        assert updated["content"] == "Updated"
        assert updated["updated_at"] != mem["updated_at"]

    def test_update_category(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test")
        updated = tmp_db.update_memory(mem["id"], category="learning")
        assert updated["category"] == "learning"

    def test_update_tags(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test", tags=["old"])
        updated = tmp_db.update_memory(mem["id"], tags=["new1", "new2"])
        assert updated["tags"] == ["new1", "new2"]

    def test_update_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.update_memory("nonexistent", content="x") is None

    def test_update_invalid_category(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test")
        with pytest.raises(ValueError, match="Invalid category"):
            tmp_db.update_memory(mem["id"], category="bad")

    def test_update_no_changes(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test")
        result = tmp_db.update_memory(mem["id"])
        assert result["content"] == "Test"


class TestDeleteMemory:
    def test_soft_delete(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test")
        assert tmp_db.delete_memory(mem["id"]) is True
        fetched = tmp_db.get_memory(mem["id"])
        assert fetched["archived"] is True

    def test_delete_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.delete_memory("nonexistent") is False

    def test_deleted_excluded_from_list(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test")
        tmp_db.delete_memory(mem["id"])
        memories = tmp_db.list_memories()
        assert all(m["id"] != mem["id"] for m in memories)


class TestListMemories:
    def test_list_all(self, seeded_db: HearthDB) -> None:
        memories = seeded_db.list_memories()
        assert len(memories) == 4

    def test_list_by_project(self, seeded_db: HearthDB) -> None:
        memories = seeded_db.list_memories(project="project-alpha")
        assert len(memories) == 2
        assert all(m["project"] == "project-alpha" for m in memories)

    def test_list_by_category(self, seeded_db: HearthDB) -> None:
        memories = seeded_db.list_memories(category="learning")
        assert len(memories) == 1
        assert memories[0]["category"] == "learning"

    def test_list_limit(self, seeded_db: HearthDB) -> None:
        memories = seeded_db.list_memories(limit=2)
        assert len(memories) == 2

    def test_list_offset(self, seeded_db: HearthDB) -> None:
        all_mems = seeded_db.list_memories()
        offset_mems = seeded_db.list_memories(offset=2)
        assert len(offset_mems) == len(all_mems) - 2

    def test_list_include_archived(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test")
        tmp_db.delete_memory(mem["id"])
        assert len(tmp_db.list_memories()) == 0
        assert len(tmp_db.list_memories(include_archived=True)) == 1

    def test_list_ordered_newest_first(self, seeded_db: HearthDB) -> None:
        memories = seeded_db.list_memories()
        dates = [m["created_at"] for m in memories]
        assert dates == sorted(dates, reverse=True)


# ── Project CRUD ────────────────────────────────────────────────────


class TestCreateProject:
    def test_create_basic(self, tmp_db: HearthDB) -> None:
        proj = tmp_db.create_project("my-project", "A description")
        assert proj["name"] == "my-project"
        assert proj["description"] == "A description"
        assert proj["status"] == "active"

    def test_create_duplicate(self, tmp_db: HearthDB) -> None:
        tmp_db.create_project("dupe")
        with pytest.raises(ValueError, match="already exists"):
            tmp_db.create_project("dupe")


class TestGetProject:
    def test_get_with_memory_count(self, seeded_db: HearthDB) -> None:
        proj = seeded_db.get_project("project-alpha")
        assert proj is not None
        assert proj["memory_count"] == 2

    def test_get_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.get_project("nonexistent") is None


class TestListProjects:
    def test_list_active(self, seeded_db: HearthDB) -> None:
        projects = seeded_db.list_projects()
        assert len(projects) == 2

    def test_list_excludes_archived(self, seeded_db: HearthDB) -> None:
        seeded_db.archive_project("project-beta")
        projects = seeded_db.list_projects()
        assert len(projects) == 1
        assert projects[0]["name"] == "project-alpha"


class TestUpdateProject:
    def test_update_description(self, seeded_db: HearthDB) -> None:
        updated = seeded_db.update_project("project-alpha", description="New desc")
        assert updated["description"] == "New desc"

    def test_update_status(self, seeded_db: HearthDB) -> None:
        updated = seeded_db.update_project("project-alpha", status="paused")
        assert updated["status"] == "paused"

    def test_update_invalid_status(self, seeded_db: HearthDB) -> None:
        with pytest.raises(ValueError, match="Invalid status"):
            seeded_db.update_project("project-alpha", status="invalid")

    def test_update_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.update_project("nonexistent", description="x") is None


class TestArchiveProject:
    def test_archive(self, seeded_db: HearthDB) -> None:
        assert seeded_db.archive_project("project-alpha") is True
        proj = seeded_db.get_project("project-alpha")
        assert proj["status"] == "archived"

    def test_archive_nonexistent(self, tmp_db: HearthDB) -> None:
        assert tmp_db.archive_project("nonexistent") is False


# ── FTS5 Triggers ───────────────────────────────────────────────────


class TestFTSTriggers:
    def test_insert_triggers_fts(self, tmp_db: HearthDB) -> None:
        tmp_db.store_memory("Full text search works great")
        results = tmp_db.fts_search("search")
        assert len(results) >= 1
        assert "search" in results[0]["content"].lower()

    def test_update_triggers_fts(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Original content here")
        tmp_db.update_memory(mem["id"], content="Completely different text")
        # Old content should not match
        assert len(tmp_db.fts_search("Original")) == 0
        # New content should match
        assert len(tmp_db.fts_search("different")) >= 1

    def test_fts_project_filter(self, seeded_db: HearthDB) -> None:
        results = seeded_db.fts_search("great", project="project-alpha")
        assert len(results) >= 1
        assert all(r["project"] == "project-alpha" for r in results)


# ── Embeddings ──────────────────────────────────────────────────────


class TestEmbeddingStorage:
    def test_store_and_search(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test embedding")
        fake_vec = [0.1] * 768
        tmp_db.store_embedding(mem["id"], fake_vec)

        results = tmp_db.vec_search(fake_vec, limit=5)
        assert len(results) >= 1
        assert results[0][0] == mem["id"]
        assert results[0][1] < 0.01  # near-zero distance for identical vector

    def test_delete_embedding(self, tmp_db: HearthDB) -> None:
        mem = tmp_db.store_memory("Test")
        tmp_db.store_embedding(mem["id"], [0.1] * 768)
        tmp_db.delete_embedding(mem["id"])
        results = tmp_db.vec_search([0.1] * 768, limit=5)
        assert all(r[0] != mem["id"] for r in results)

    def test_pending_embeddings(self, tmp_db: HearthDB) -> None:
        mem1 = tmp_db.store_memory("Has embedding")
        mem2 = tmp_db.store_memory("No embedding")
        tmp_db.store_embedding(mem1["id"], [0.1] * 768)
        pending = tmp_db.get_pending_embeddings()
        assert len(pending) == 1
        assert pending[0]["id"] == mem2["id"]


# ── Stats & Export ──────────────────────────────────────────────────


class TestStats:
    def test_stats(self, seeded_db: HearthDB) -> None:
        stats = seeded_db.get_stats()
        assert stats["total_memories"] == 4
        assert stats["archived_memories"] == 0
        assert stats["active_projects"] == 2
        assert "learning" in stats["by_category"]


class TestExport:
    def test_export_json(self, seeded_db: HearthDB) -> None:
        data = seeded_db.export_memories("json")
        parsed = json.loads(data)
        assert len(parsed) == 4

    def test_export_csv(self, seeded_db: HearthDB) -> None:
        data = seeded_db.export_memories("csv")
        lines = data.strip().split("\n")
        assert len(lines) == 5  # header + 4 rows

    def test_export_invalid_format(self, seeded_db: HearthDB) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            seeded_db.export_memories("xml")


# ── Idempotent Init ─────────────────────────────────────────────────


class TestInitDB:
    def test_double_init(self, tmp_db: HearthDB) -> None:
        """Calling init_db twice should not error."""
        tmp_db.init_db()
        tmp_db.store_memory("Still works")
        assert len(tmp_db.list_memories()) >= 1
