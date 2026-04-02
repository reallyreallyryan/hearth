"""Lifecycle review queue — memories needing human decision."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from hearth.db import HearthDB
from hearth.web.dependencies import get_db, is_htmx, wants_json

router = APIRouter()


@router.get("/lifecycle", response_model=None)
async def review_queue(
    request: Request,
    db: HearthDB = Depends(get_db),
):
    """Show memories in review state for human decision."""
    templates = request.app.state.templates
    from hearth import __version__

    memories = db.list_review_memories(limit=50)
    review_count = db.count_review_memories()

    # Enrich with linkage count for vitality breakdown display
    for mem in memories:
        links = list(db.conn.execute(
            "SELECT COUNT(*) FROM session_memories WHERE memory_id = ?",
            (mem["id"],),
        ))
        mem["linkage_count"] = links[0][0] if links else 0

    context = {
        "memories": memories,
        "review_count": review_count,
        "version": __version__,
        "active_page": "lifecycle",
    }

    if wants_json(request):
        return JSONResponse({"memories": memories, "review_count": review_count})

    template = "lifecycle/_queue.html" if is_htmx(request) else "lifecycle/review.html"
    return templates.TemplateResponse(request, template, context)


@router.post("/lifecycle/{memory_id}/keep", response_model=None)
async def keep_memory(
    request: Request,
    memory_id: str,
    db: HearthDB = Depends(get_db),
):
    """Human 'keep' action: reset to active with full vitality."""
    memory = db.keep_memory(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    if wants_json(request):
        return JSONResponse(memory)

    return HTMLResponse("", headers={"HX-Trigger": "memory-kept"})


@router.post("/lifecycle/{memory_id}/archive", response_model=None)
async def archive_memory(
    request: Request,
    memory_id: str,
    db: HearthDB = Depends(get_db),
):
    """Human 'archive' action: soft-delete and set lifecycle_state='archived'."""
    success = db.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    if wants_json(request):
        return JSONResponse({"archived": True, "id": memory_id})

    return HTMLResponse("", headers={"HX-Trigger": "memory-archived"})
