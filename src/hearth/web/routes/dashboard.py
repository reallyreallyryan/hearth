"""Dashboard route — stats, health, breakdowns."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse

from hearth.db import HearthDB
from hearth.embeddings import OllamaEmbedder
from hearth.web.dependencies import get_db, get_embedder, wants_json

router = APIRouter()


@router.get("/dashboard", response_model=None)
async def dashboard(
    request: Request,
    db: HearthDB = Depends(get_db),
    embedder: OllamaEmbedder = Depends(get_embedder),
):
    """Dashboard with stats, health indicators, and breakdowns."""
    templates = request.app.state.templates
    from hearth import __version__

    stats = db.get_stats()
    ollama_available = await embedder.check_available()

    # Session count
    sessions = db.list_sessions(limit=1000)
    stats["total_sessions"] = len(sessions)

    # Calculate max for bar chart scaling
    by_category = stats.get("by_category", {})
    by_project = stats.get("by_project", {})
    max_cat = max(by_category.values()) if by_category else 1
    max_proj = max(by_project.values()) if by_project else 1

    # DB file size
    config = request.app.state.config
    db_size_mb = 0.0
    if config.db_path.exists():
        db_size_mb = config.db_path.stat().st_size / (1024 * 1024)

    context = {
        "stats": stats,
        "ollama_available": ollama_available,
        "ollama_model": config.embedding.model,
        "db_path": str(config.db_path),
        "db_size_mb": round(db_size_mb, 2),
        "by_category": by_category,
        "by_project": by_project,
        "max_cat": max_cat,
        "max_proj": max_proj,
        "version": __version__,
        "active_page": "dashboard",
    }

    if wants_json(request):
        return JSONResponse({
            "version": __version__,
            "stats": stats,
            "ollama_available": ollama_available,
            "ollama_model": config.embedding.model,
            "db_path": str(config.db_path),
            "db_size_mb": db_size_mb,
        })

    return templates.TemplateResponse(request, "dashboard.html", context)


@router.get("/export/{fmt}", response_model=None)
async def export_memories(
    request: Request,
    fmt: str,
    db: HearthDB = Depends(get_db),
):
    """Export all memories as JSON or CSV file download."""
    if fmt not in ("json", "csv"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Format must be 'json' or 'csv'")

    data = db.export_memories(format=fmt)
    media_type = "application/json" if fmt == "json" else "text/csv"
    filename = f"hearth_memories.{fmt}"

    from fastapi.responses import Response
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
