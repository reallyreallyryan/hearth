"""FastAPI dependency injection for Hearth web UI."""

from __future__ import annotations

from fastapi import Request

from hearth.config import HearthConfig
from hearth.db import HearthDB
from hearth.embeddings import OllamaEmbedder


def get_db(request: Request) -> HearthDB:
    """Get the shared HearthDB instance."""
    return request.app.state.db


def get_embedder(request: Request) -> OllamaEmbedder:
    """Get the shared OllamaEmbedder instance."""
    return request.app.state.embedder


def get_config(request: Request) -> HearthConfig:
    """Get the loaded HearthConfig."""
    return request.app.state.config


def is_htmx(request: Request) -> bool:
    """Check if this is an htmx partial request."""
    return request.headers.get("hx-request") == "true"


def wants_json(request: Request) -> bool:
    """Check if the client wants JSON instead of HTML."""
    accept = request.headers.get("accept", "")
    return "application/json" in accept
