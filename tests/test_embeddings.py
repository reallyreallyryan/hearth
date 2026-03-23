"""Tests for hearth.embeddings — Ollama client, availability, batch processing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hearth.db import HearthDB
from hearth.embeddings import EmbeddingResult, OllamaEmbedder


# ── Availability Check ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_available_success() -> None:
    """check_available returns True when model is found."""
    embedder = OllamaEmbedder(model="nomic-embed-text")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "models": [
            {"name": "nomic-embed-text:latest"},
            {"name": "llama3:latest"},
        ]
    }

    with patch("hearth.embeddings.httpx.AsyncClient") as mock_client_cls:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client_instance

        result = await embedder.check_available()
        assert result is True
        assert embedder._available is True


@pytest.mark.asyncio
async def test_check_available_model_missing() -> None:
    """check_available returns False when model is not found."""
    embedder = OllamaEmbedder(model="nomic-embed-text")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "models": [{"name": "llama3:latest"}]
    }

    with patch("hearth.embeddings.httpx.AsyncClient") as mock_client_cls:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client_instance

        result = await embedder.check_available()
        assert result is False
        assert embedder._available is False


@pytest.mark.asyncio
async def test_check_available_connection_error() -> None:
    """check_available returns False on connection error."""
    import httpx

    embedder = OllamaEmbedder()

    with patch("hearth.embeddings.httpx.AsyncClient") as mock_client_cls:
        client_instance = AsyncMock()
        client_instance.get.side_effect = httpx.ConnectError("refused")
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client_instance

        result = await embedder.check_available()
        assert result is False
        assert embedder._available is False


# ── Embed ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_embed_success() -> None:
    """embed returns EmbeddingResult on success."""
    embedder = OllamaEmbedder()
    embedder._available = True

    fake_vec = [0.1] * 768
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "embeddings": [fake_vec],
        "model": "nomic-embed-text",
    }

    with patch("hearth.embeddings.httpx.AsyncClient") as mock_client_cls:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client_instance

        result = await embedder.embed("Hello world")
        assert result is not None
        assert len(result.embedding) == 768
        assert result.model == "nomic-embed-text"


@pytest.mark.asyncio
async def test_embed_returns_none_when_unavailable() -> None:
    """embed returns None immediately when _available is False."""
    embedder = OllamaEmbedder()
    embedder._available = False
    result = await embedder.embed("Hello")
    assert result is None


# ── Process Pending ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_process_pending(tmp_db: HearthDB) -> None:
    """process_pending embeds all memories missing embeddings."""
    tmp_db.store_memory("First memory")
    tmp_db.store_memory("Second memory")

    assert len(tmp_db.get_pending_embeddings()) == 2

    embedder = OllamaEmbedder()
    embedder._available = True

    fake_vec = [0.1] * 768
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "embeddings": [fake_vec, fake_vec],
        "model": "nomic-embed-text",
    }

    with patch("hearth.embeddings.httpx.AsyncClient") as mock_client_cls:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client_instance

        count = await embedder.process_pending(tmp_db)
        assert count == 2
        assert len(tmp_db.get_pending_embeddings()) == 0


@pytest.mark.asyncio
async def test_process_pending_no_pending(tmp_db: HearthDB) -> None:
    """process_pending returns 0 when nothing is pending."""
    embedder = OllamaEmbedder()
    embedder._available = True
    count = await embedder.process_pending(tmp_db)
    assert count == 0
