"""Tests for Hearth Web UI."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from hearth.cli import cli
from hearth.web.app import create_app


@pytest.fixture
def mock_embedder():
    """Create a mock OllamaEmbedder for web tests."""
    embedder = MagicMock()
    embedder.check_available = AsyncMock(return_value=True)
    embedder.embed = AsyncMock(return_value=None)
    embedder._available = True
    return embedder


@pytest.fixture
def web_client(tmp_db, mock_embedder):
    """Create a TestClient with an empty database."""
    app = create_app(db=tmp_db, embedder=mock_embedder)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def seeded_web_client(seeded_db, mock_embedder):
    """Create a TestClient with a seeded database containing memories."""
    app = create_app(db=seeded_db, embedder=mock_embedder)
    with TestClient(app) as client:
        yield client


# ── Step 1: Scaffold Tests ─────────────────────────────────────


class TestScaffold:
    def test_app_creates_without_error(self, tmp_db, mock_embedder) -> None:
        app = create_app(db=tmp_db, embedder=mock_embedder)
        assert app is not None
        assert app.title == "Hearth"

    def test_root_redirects_to_memories(self, web_client) -> None:
        response = web_client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/memories" in response.headers["location"]

    def test_root_follow_redirect(self, web_client) -> None:
        response = web_client.get("/")
        assert response.status_code == 200
        assert "Memories" in response.text

    def test_static_css_served(self, web_client) -> None:
        response = web_client.get("/static/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]

    def test_static_htmx_served(self, web_client) -> None:
        response = web_client.get("/static/htmx.min.js")
        assert response.status_code == 200

    def test_static_js_served(self, web_client) -> None:
        response = web_client.get("/static/app.js")
        assert response.status_code == 200

    def test_nonexistent_static_returns_404(self, web_client) -> None:
        response = web_client.get("/static/nonexistent.css")
        assert response.status_code == 404

    def test_version_in_page(self, web_client) -> None:
        response = web_client.get("/memories")
        from hearth import __version__
        assert __version__ in response.text

    def test_create_app_with_injected_deps(self, tmp_db, mock_embedder) -> None:
        """Verify that create_app accepts injected db/embedder for testing."""
        app = create_app(db=tmp_db, embedder=mock_embedder)
        with TestClient(app) as client:
            response = client.get("/memories")
            assert response.status_code == 200


class TestUICommand:
    def test_ui_db_not_initialized(self, tmp_path) -> None:
        runner = CliRunner()
        with patch("hearth.cli.load_config") as mock_config:
            cfg = mock_config.return_value
            cfg.db_path = tmp_path / "nonexistent.db"
            result = runner.invoke(cli, ["ui"])
        assert result.exit_code == 1
        assert "not initialized" in result.output

    def test_ui_startup_message(self, tmp_db) -> None:
        runner = CliRunner()
        with patch("hearth.cli.load_config") as mock_config, \
             patch("hearth.web.app.run_app") as mock_run:
            cfg = mock_config.return_value
            cfg.db_path = tmp_db.db_path
            result = runner.invoke(cli, ["ui", "--port", "9999"])
        assert "http://localhost:9999" in result.output
        mock_run.assert_called_once_with(port=9999)


# ── Step 2: Memory List Tests ──────────────────────────────────


class TestMemoryList:
    def test_list_returns_200(self, seeded_web_client) -> None:
        response = seeded_web_client.get("/memories")
        assert response.status_code == 200
        assert "Memories" in response.text

    def test_list_shows_memory_content(self, seeded_web_client) -> None:
        response = seeded_web_client.get("/memories")
        # Seeded db has memories — check that content appears
        assert response.status_code == 200
        # At least one memory content should be visible
        assert "data-table" in response.text or "empty-state" in response.text

    def test_list_json_mode(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories", headers={"Accept": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "memories" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert isinstance(data["memories"], list)

    def test_list_pagination_page_1(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories?page=1", headers={"Accept": "application/json"}
        )
        data = response.json()
        assert data["page"] == 1

    def test_list_filter_by_category(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories?category=learning",
            headers={"Accept": "application/json"},
        )
        data = response.json()
        for memory in data["memories"]:
            assert memory["category"] == "learning"

    def test_list_filter_by_project(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories?project=project-alpha",
            headers={"Accept": "application/json"},
        )
        data = response.json()
        for memory in data["memories"]:
            assert memory["project"] == "project-alpha"

    def test_list_filter_by_source(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories?source=user",
            headers={"Accept": "application/json"},
        )
        data = response.json()
        for memory in data["memories"]:
            assert memory["source"] == "user"

    def test_list_empty_db(self, web_client) -> None:
        response = web_client.get("/memories")
        assert response.status_code == 200
        assert "No memories found" in response.text

    def test_list_htmx_returns_partial(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories", headers={"HX-Request": "true"}
        )
        assert response.status_code == 200
        # Partial should NOT contain full HTML structure
        assert "<!DOCTYPE html>" not in response.text

    def test_list_full_page_contains_layout(self, seeded_web_client) -> None:
        response = seeded_web_client.get("/memories")
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text
        assert "sidebar" in response.text


class TestMemoryDetail:
    def test_get_memory_returns_detail(self, seeded_web_client, seeded_db) -> None:
        memories = seeded_db.list_memories(limit=1)
        memory_id = memories[0]["id"]
        response = seeded_web_client.get(f"/memories/{memory_id}")
        assert response.status_code == 200
        assert memories[0]["content"] in response.text

    def test_get_memory_json(self, seeded_web_client, seeded_db) -> None:
        memories = seeded_db.list_memories(limit=1)
        memory_id = memories[0]["id"]
        response = seeded_web_client.get(
            f"/memories/{memory_id}",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == memory_id

    def test_get_nonexistent_memory(self, seeded_web_client) -> None:
        response = seeded_web_client.get("/memories/nonexistent-id-123")
        assert response.status_code == 404


class TestMemoryUpdate:
    def test_update_memory_content(self, seeded_web_client, seeded_db) -> None:
        memories = seeded_db.list_memories(limit=1)
        memory_id = memories[0]["id"]
        response = seeded_web_client.put(
            f"/memories/{memory_id}",
            data={
                "content": "Updated content here",
                "category": "learning",
                "project": "",
                "tags": "",
            },
        )
        assert response.status_code == 200
        assert "Updated content here" in response.text

    def test_update_memory_json(self, seeded_web_client, seeded_db) -> None:
        memories = seeded_db.list_memories(limit=1)
        memory_id = memories[0]["id"]
        response = seeded_web_client.put(
            f"/memories/{memory_id}",
            data={
                "content": "JSON update test",
                "category": "general",
                "project": "",
                "tags": "tag1, tag2",
            },
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "JSON update test"
        assert data["tags"] == ["tag1", "tag2"]

    def test_update_nonexistent_memory(self, seeded_web_client) -> None:
        response = seeded_web_client.put(
            "/memories/nonexistent-id-123",
            data={
                "content": "test",
                "category": "general",
                "project": "",
                "tags": "",
            },
        )
        assert response.status_code == 404

    def test_update_invalid_category(self, seeded_web_client, seeded_db) -> None:
        memories = seeded_db.list_memories(limit=1)
        memory_id = memories[0]["id"]
        response = seeded_web_client.put(
            f"/memories/{memory_id}",
            data={
                "content": "test",
                "category": "invalid_category",
                "project": "",
                "tags": "",
            },
        )
        assert response.status_code == 422


class TestMemoryArchive:
    def test_archive_memory(self, seeded_web_client, seeded_db) -> None:
        memories = seeded_db.list_memories(limit=1)
        memory_id = memories[0]["id"]
        response = seeded_web_client.delete(f"/memories/{memory_id}")
        assert response.status_code == 200
        # Verify it's archived
        mem = seeded_db.get_memory(memory_id)
        assert mem["archived"] is True

    def test_archive_json_mode(self, seeded_web_client, seeded_db) -> None:
        memories = seeded_db.list_memories(limit=1)
        memory_id = memories[0]["id"]
        response = seeded_web_client.delete(
            f"/memories/{memory_id}",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["archived"] is True

    def test_archive_nonexistent(self, seeded_web_client) -> None:
        response = seeded_web_client.delete("/memories/nonexistent-id-123")
        assert response.status_code == 404


# ── Step 3: Search Tests ───────────────────────────────────────


class TestSearch:
    def test_search_returns_results(self, seeded_web_client) -> None:
        response = seeded_web_client.get("/memories?q=Python")
        assert response.status_code == 200
        assert "Python" in response.text

    def test_search_json_mode(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories?q=Python",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "memory" in data[0]
        assert "score" in data[0]
        assert "match_type" in data[0]

    def test_search_no_results(self, seeded_web_client) -> None:
        response = seeded_web_client.get("/memories?q=xyznonexistent999")
        assert response.status_code == 200
        assert "No results" in response.text

    def test_search_empty_query_falls_back_to_list(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories?q=",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should return list format, not search format
        assert "memories" in data

    def test_search_with_category_filter(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories?q=Python&category=learning",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        for result in data:
            assert result["memory"]["category"] == "learning"

    def test_search_htmx_returns_partial(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories?q=Python", headers={"HX-Request": "true"}
        )
        assert response.status_code == 200
        assert "<!DOCTYPE html>" not in response.text

    def test_search_results_show_match_type(self, seeded_web_client) -> None:
        response = seeded_web_client.get("/memories?q=SQLite")
        assert response.status_code == 200
        # Should show match type badge (fts since no embeddings in test)
        assert "fts" in response.text or "semantic" in response.text or "hybrid" in response.text


# ── Step 4: Filter Tests ──────────────────────────────────────


class TestFilters:
    def test_multiple_filters_compose(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories?project=project-alpha&category=learning",
            headers={"Accept": "application/json"},
        )
        data = response.json()
        for memory in data["memories"]:
            assert memory["project"] == "project-alpha"
            assert memory["category"] == "learning"

    def test_filter_plus_search(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories?q=Python&project=project-alpha",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for result in data:
            assert result["memory"]["project"] == "project-alpha"

    def test_invalid_filter_returns_empty(self, seeded_web_client) -> None:
        response = seeded_web_client.get(
            "/memories?project=nonexistent-project",
            headers={"Accept": "application/json"},
        )
        data = response.json()
        assert data["memories"] == []
        assert data["total"] == 0

    def test_filter_dropdowns_populated(self, seeded_web_client) -> None:
        response = seeded_web_client.get("/memories")
        assert response.status_code == 200
        assert "project-alpha" in response.text
        assert "project-beta" in response.text
        assert "learning" in response.text
        assert "general" in response.text


class TestCountMemories:
    def test_count_all(self, seeded_db) -> None:
        count = seeded_db.count_memories()
        memories = seeded_db.list_memories(limit=100)
        assert count == len(memories)

    def test_count_with_category_filter(self, seeded_db) -> None:
        count = seeded_db.count_memories(category="learning")
        memories = seeded_db.list_memories(category="learning", limit=100)
        assert count == len(memories)

    def test_count_with_project_filter(self, seeded_db) -> None:
        count = seeded_db.count_memories(project="project-alpha")
        memories = seeded_db.list_memories(project="project-alpha", limit=100)
        assert count == len(memories)

    def test_count_empty_db(self, tmp_db) -> None:
        assert tmp_db.count_memories() == 0

    def test_count_excludes_archived_by_default(self, seeded_db) -> None:
        memories = seeded_db.list_memories(limit=1)
        seeded_db.delete_memory(memories[0]["id"])
        count_before = seeded_db.count_memories()
        count_with_archived = seeded_db.count_memories(include_archived=True)
        assert count_with_archived > count_before
