"""Project CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from hearth.config import VALID_PROJECT_STATUSES
from hearth.db import HearthDB
from hearth.web.dependencies import get_db, is_htmx, wants_json

router = APIRouter()


def _get_templates(request: Request):
    return request.app.state.templates


@router.get("/projects", response_model=None)
async def list_projects(
    request: Request,
    db: HearthDB = Depends(get_db),
):
    """List all active projects."""
    templates = _get_templates(request)
    from hearth import __version__

    projects = db.list_projects()

    if wants_json(request):
        return JSONResponse({"projects": projects})

    context = {
        "projects": projects,
        "statuses": sorted(VALID_PROJECT_STATUSES),
        "version": __version__,
        "active_page": "projects",
    }

    template = "projects/_table.html" if is_htmx(request) else "projects/list.html"
    return templates.TemplateResponse(request, template, context)


@router.post("/projects", response_model=None)
async def create_project(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: HearthDB = Depends(get_db),
):
    """Create a new project."""
    templates = _get_templates(request)

    try:
        project = db.create_project(
            name=name.strip(),
            description=description.strip() or None,
        )
    except ValueError as e:
        if wants_json(request):
            return JSONResponse({"error": str(e)}, status_code=409)
        raise HTTPException(status_code=409, detail=str(e))

    if wants_json(request):
        return JSONResponse(project, status_code=201)

    # Return updated project list
    projects = db.list_projects()
    from hearth import __version__
    return templates.TemplateResponse(request, "projects/_table.html", {
        "projects": projects,
        "statuses": sorted(VALID_PROJECT_STATUSES),
        "version": __version__,
    })


@router.get("/projects/{name}", response_model=None)
async def get_project(
    request: Request,
    name: str,
    db: HearthDB = Depends(get_db),
):
    """Get project detail with its memories."""
    templates = _get_templates(request)
    project = db.get_project(name)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if wants_json(request):
        return JSONResponse(project)

    memories = db.list_memories(project=name, limit=50)

    return templates.TemplateResponse(request, "projects/_detail.html", {
        "project": project,
        "memories": memories,
        "statuses": sorted(VALID_PROJECT_STATUSES),
    })


@router.put("/projects/{name}", response_model=None)
async def update_project(
    request: Request,
    name: str,
    description: str = Form(None),
    status: str = Form(None),
    db: HearthDB = Depends(get_db),
):
    """Update project description or status."""
    try:
        updated = db.update_project(
            name,
            description=description,
            status=status,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if updated is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if wants_json(request):
        return JSONResponse(updated)

    templates = _get_templates(request)
    memories = db.list_memories(project=name, limit=50)
    return templates.TemplateResponse(request, "projects/_detail.html", {
        "project": updated,
        "memories": memories,
        "statuses": sorted(VALID_PROJECT_STATUSES),
    })


@router.delete("/projects/{name}", response_model=None)
async def archive_project(
    request: Request,
    name: str,
    db: HearthDB = Depends(get_db),
):
    """Archive a project."""
    success = db.archive_project(name)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")

    if wants_json(request):
        return JSONResponse({"archived": True, "name": name})

    return HTMLResponse("", headers={"HX-Trigger": "project-archived"})
