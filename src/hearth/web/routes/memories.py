"""Memory list, detail, edit, and archive routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from hearth.config import VALID_CATEGORIES
from hearth.db import HearthDB
from hearth.embeddings import OllamaEmbedder
from hearth.web.dependencies import get_db, get_embedder, is_htmx, wants_json

router = APIRouter()

PER_PAGE = 25


def _get_templates(request: Request):
    return request.app.state.templates


@router.get("/memories", response_model=None)
async def list_memories(
    request: Request,
    project: str | None = None,
    category: str | None = None,
    source: str | None = None,
    page: int = 1,
    q: str | None = None,
    db: HearthDB = Depends(get_db),
    embedder: OllamaEmbedder = Depends(get_embedder),
):
    """List memories with optional filters, or search if q is provided."""
    templates = _get_templates(request)
    from hearth import __version__

    # Normalize empty query to None
    if q is not None and q.strip() == "":
        q = None

    if q:
        # Search mode
        from hearth.search import hybrid_search

        config = request.app.state.config
        results = await hybrid_search(
            q, db, embedder,
            project=project, category=category,
            limit=PER_PAGE, config=config.search,
        )

        if wants_json(request):
            return JSONResponse([
                {"memory": r.memory, "score": r.score, "match_type": r.match_type}
                for r in results
            ])

        context = {
            "search_results": results,
            "query": q,
            "project": project,
            "category": category,
            "source": source,
            "projects": db.list_projects(),
            "categories": sorted(VALID_CATEGORIES),
            "version": __version__,
            "active_page": "memories",
        }

        template = "search/_results.html" if is_htmx(request) else "memories/list.html"
        return templates.TemplateResponse(request, template, context)

    # List mode
    offset = (page - 1) * PER_PAGE
    memories = db.list_memories(
        project=project, category=category, source=source,
        limit=PER_PAGE, offset=offset,
    )
    total = db.count_memories(
        project=project, category=category, source=source,
    )
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)

    if wants_json(request):
        return JSONResponse({
            "memories": memories,
            "total": total,
            "page": page,
            "per_page": PER_PAGE,
            "total_pages": total_pages,
        })

    context = {
        "memories": memories,
        "total": total,
        "page": page,
        "per_page": PER_PAGE,
        "total_pages": total_pages,
        "project": project,
        "category": category,
        "source": source,
        "query": q,
        "projects": db.list_projects(),
        "categories": sorted(VALID_CATEGORIES),
        "version": __version__,
        "active_page": "memories",
    }

    template = "memories/_table.html" if is_htmx(request) else "memories/list.html"
    return templates.TemplateResponse(request, template, context)


@router.get("/memories/{memory_id}", response_model=None)
async def get_memory(
    request: Request,
    memory_id: str,
    db: HearthDB = Depends(get_db),
):
    """Get a single memory detail."""
    templates = _get_templates(request)
    memory = db.get_memory(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    if wants_json(request):
        return JSONResponse(memory)

    return templates.TemplateResponse(request, "memories/_detail.html", {
        "memory": memory,
    })


@router.get("/memories/{memory_id}/edit", response_model=None)
async def edit_memory_form(
    request: Request,
    memory_id: str,
    db: HearthDB = Depends(get_db),
):
    """Return the edit form for a memory."""
    templates = _get_templates(request)
    memory = db.get_memory(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    return templates.TemplateResponse(request, "memories/_edit_form.html", {
        "memory": memory,
        "categories": sorted(VALID_CATEGORIES),
        "projects": db.list_projects(),
    })


@router.put("/memories/{memory_id}", response_model=None)
async def update_memory(
    request: Request,
    memory_id: str,
    content: str = Form(...),
    category: str = Form(...),
    project: str = Form(""),
    tags: str = Form(""),
    db: HearthDB = Depends(get_db),
    embedder: OllamaEmbedder = Depends(get_embedder),
):
    """Update a memory's content and metadata."""
    templates = _get_templates(request)

    # Get existing memory to check if content changed
    existing = db.get_memory(memory_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags.strip() else None
    project_val = project if project.strip() else None

    try:
        updated = db.update_memory(
            memory_id,
            content=content,
            category=category,
            project=project_val,
            tags=tag_list,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Re-embed if content changed
    if content != existing["content"]:
        db.delete_embedding(memory_id)
        embed_result = await embedder.embed(content)
        if embed_result:
            db.store_embedding(memory_id, embed_result.embedding)

    if wants_json(request):
        return JSONResponse(updated)

    return templates.TemplateResponse(request, "memories/_detail.html", {
        "memory": updated,
    })


@router.delete("/memories/{memory_id}")
async def archive_memory(
    request: Request,
    memory_id: str,
    db: HearthDB = Depends(get_db),
):
    """Soft-delete (archive) a memory."""
    success = db.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    if wants_json(request):
        return JSONResponse({"archived": True, "id": memory_id})

    # Return empty response for htmx to remove the row
    return HTMLResponse("", headers={"HX-Trigger": "memory-archived"})
