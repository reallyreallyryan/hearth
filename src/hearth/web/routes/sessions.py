"""Session list and detail routes — resonance visualization."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from hearth.config import RESONANCE_AXES
from hearth.db import HearthDB
from hearth.web.dependencies import get_db, is_htmx, wants_json

router = APIRouter()


def _get_templates(request: Request):
    return request.app.state.templates


@router.get("/sessions", response_model=None)
async def list_sessions(
    request: Request,
    project: str | None = None,
    limit: int = 20,
    db: HearthDB = Depends(get_db),
):
    """List sessions with resonance data and radar chart visualization."""
    templates = _get_templates(request)
    from hearth import __version__

    project = project or None

    sessions = db.list_sessions(project=project, limit=limit)
    for s in sessions:
        s["resonance"] = db.get_resonance(s["id"])

    projects = db.list_projects()

    if wants_json(request):
        return JSONResponse({"sessions": sessions})

    context = {
        "sessions": sessions,
        "projects": projects,
        "project": project,
        "resonance_axes": RESONANCE_AXES,
        "version": __version__,
        "active_page": "sessions",
    }

    return templates.TemplateResponse(request, "sessions/list.html", context)


@router.get("/sessions/{session_id}", response_model=None)
async def get_session_detail(
    request: Request,
    session_id: str,
    db: HearthDB = Depends(get_db),
):
    """Get session detail with resonance and linked memories."""
    templates = _get_templates(request)

    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    resonance = db.get_resonance(session_id)
    memories = db.get_session_memories(session_id)

    if wants_json(request):
        return JSONResponse({
            "session": session,
            "resonance": resonance,
            "memories": memories,
        })

    context = {
        "session": session,
        "resonance": resonance,
        "memories": memories,
        "resonance_axes": RESONANCE_AXES,
    }

    return templates.TemplateResponse(request, "sessions/_detail.html", context)
