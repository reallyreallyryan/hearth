"""Thread and tension list/detail routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from hearth.config import VALID_THREAD_STATUSES
from hearth.db import HearthDB
from hearth.web.dependencies import get_db, is_htmx, wants_json

router = APIRouter()


def _get_templates(request: Request):
    return request.app.state.templates


@router.get("/threads", response_model=None)
async def list_threads(
    request: Request,
    project: str | None = None,
    status: str | None = None,
    db: HearthDB = Depends(get_db),
):
    """List threads with linked tensions and optional filters."""
    templates = _get_templates(request)
    from hearth import __version__

    project = project or None
    status = status or None

    threads = db.list_threads(project=project, status=status, limit=50)
    for t in threads:
        t["tensions"] = db.list_tensions(thread_id=t["id"])

    # Free-floating tensions (no parent thread)
    all_tensions = db.list_tensions(project=project)
    free_tensions = [t for t in all_tensions if t.get("thread_id") is None]

    projects = db.list_projects()

    if wants_json(request):
        return JSONResponse({
            "threads": threads,
            "free_tensions": free_tensions,
        })

    context = {
        "threads": threads,
        "free_tensions": free_tensions,
        "projects": projects,
        "statuses": sorted(VALID_THREAD_STATUSES),
        "project": project,
        "status": status,
        "version": __version__,
        "active_page": "threads",
    }

    template = "threads/_list.html" if is_htmx(request) else "threads/list.html"
    return templates.TemplateResponse(request, template, context)


@router.get("/threads/{thread_id}", response_model=None)
async def get_thread_detail(
    request: Request,
    thread_id: str,
    db: HearthDB = Depends(get_db),
):
    """Get thread detail with linked sessions and tensions."""
    templates = _get_templates(request)

    thread = db.get_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    tensions = db.list_tensions(thread_id=thread_id)
    sessions = db.get_thread_sessions(thread_id)

    if wants_json(request):
        return JSONResponse({
            "thread": thread,
            "tensions": tensions,
            "sessions": sessions,
        })

    context = {
        "thread": thread,
        "tensions": tensions,
        "sessions": sessions,
    }

    return templates.TemplateResponse(request, "threads/_detail.html", context)
