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
    """Create a TestClient with a seeded database."""
    app = create_app(db=tmp_db, embedder=mock_embedder)
    return TestClient(app)


@pytest.fixture
def seeded_web_client(seeded_db, mock_embedder):
    """Create a TestClient with a seeded database containing memories."""
    app = create_app(db=seeded_db, embedder=mock_embedder)
    return TestClient(app)


# ── Step 1: Scaffold Tests ─────────────────────────────────────


class TestScaffold:
    def test_app_creates_without_error(self, tmp_db, mock_embedder) -> None:
        app = create_app(db=tmp_db, embedder=mock_embedder)
        assert app is not None
        assert app.title == "Hearth"

    def test_root_returns_200(self, web_client) -> None:
        response = web_client.get("/")
        assert response.status_code == 200
        assert "Hearth" in response.text

    def test_root_contains_nav(self, web_client) -> None:
        response = web_client.get("/")
        assert "Dashboard" in response.text
        assert "Memories" in response.text
        assert "Projects" in response.text

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
        response = web_client.get("/")
        from hearth import __version__
        assert __version__ in response.text

    def test_create_app_with_injected_deps(self, tmp_db, mock_embedder) -> None:
        """Verify that create_app accepts injected db/embedder for testing."""
        app = create_app(db=tmp_db, embedder=mock_embedder)
        client = TestClient(app)
        response = client.get("/")
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
