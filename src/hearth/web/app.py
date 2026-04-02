"""Hearth Web UI — FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from hearth import __version__
from hearth.config import HearthConfig, load_config
from hearth.db import HearthDB
from hearth.embeddings import OllamaEmbedder

WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


def _timeago(value: str) -> str:
    """Convert ISO timestamp to relative time string."""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "just now"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days < 30:
            return f"{days}d ago"
        months = days // 30
        return f"{months}mo ago"
    except (ValueError, TypeError):
        return value


def _truncate(value: str, length: int = 120) -> str:
    """Truncate string with ellipsis."""
    if len(value) <= length:
        return value
    return value[:length].rstrip() + "..."


def _truncate_id(value: str, length: int = 8) -> str:
    """Show first N chars of an ID."""
    return value[:length] + "..."


def create_app(
    db: HearthDB | None = None,
    embedder: OllamaEmbedder | None = None,
    config: HearthConfig | None = None,
) -> FastAPI:
    """Create the FastAPI application.

    Args:
        db: Optional HearthDB instance (for testing). If None, created from config at startup.
        embedder: Optional OllamaEmbedder instance (for testing).
        config: Optional HearthConfig (for testing).
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if db is not None:
            app.state.db = db
            app.state.embedder = embedder
            app.state.config = config or load_config()
        else:
            cfg = config or load_config()
            app_db = HearthDB(cfg.db_path)
            app_db.init_db()
            app_embedder = OllamaEmbedder(
                base_url=cfg.ollama_base_url,
                model=cfg.embedding.model,
                dimensions=cfg.embedding.dimensions,
            )
            await app_embedder.check_available()
            app.state.db = app_db
            app.state.embedder = app_embedder
            app.state.config = cfg
        try:
            yield
        finally:
            if db is None and hasattr(app.state, "db"):
                app.state.db.close()

    app = FastAPI(title="Hearth", version=__version__, lifespan=lifespan)

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Set up templates
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.filters["timeago"] = _timeago
    templates.env.filters["truncate_content"] = _truncate
    templates.env.filters["truncate_id"] = _truncate_id
    app.state.templates = templates

    # Register route modules
    from hearth.web.routes.memories import router as memories_router
    from hearth.web.routes.dashboard import router as dashboard_router
    from hearth.web.routes.projects import router as projects_router
    from hearth.web.routes.sessions import router as sessions_router
    from hearth.web.routes.threads import router as threads_router
    from hearth.web.routes.lifecycle import router as lifecycle_router
    app.include_router(memories_router)
    app.include_router(dashboard_router)
    app.include_router(projects_router)
    app.include_router(sessions_router)
    app.include_router(threads_router)
    app.include_router(lifecycle_router)

    # Root route — redirect to memories for now
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/memories", status_code=302)

    return app


def run_app(port: int = 8274) -> None:
    """Start the Hearth web UI server."""
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
