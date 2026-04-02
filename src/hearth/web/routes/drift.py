"""Drift visualization — how resonance evolves across sessions."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from hearth.config import RESONANCE_AXES
from hearth.db import HearthDB
from hearth.web.dependencies import get_db, wants_json

router = APIRouter()


def _session_label(session: dict) -> str:
    """Generate a short label for a session column header."""
    summary = session.get("summary") or ""
    date_str = ""
    started = session.get("started_at", "")
    if started:
        try:
            dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            date_str = dt.strftime("%b %-d")
        except (ValueError, TypeError):
            date_str = started[:10]

    if summary:
        short = summary[:15].rstrip()
        if len(summary) > 15:
            short += "..."
        return f"{short} ({date_str})" if date_str else short

    return date_str or session.get("id", "")[:8]


def _compute_inflections(
    sessions: list[dict],
) -> list[dict]:
    """Compute inflection points between consecutive sessions.

    An inflection is flagged when the total absolute shift across all 11
    axes exceeds 3.0 between two consecutive sessions.
    """
    inflections = []
    for i in range(1, len(sessions)):
        prev_res = sessions[i - 1]["resonance"]
        curr_res = sessions[i]["resonance"]

        deltas = []
        for axis in RESONANCE_AXES:
            delta = curr_res.get(axis, 0.0) - prev_res.get(axis, 0.0)
            deltas.append({"axis": axis, "delta": round(delta, 3)})

        total_shift = sum(abs(d["delta"]) for d in deltas)

        if total_shift > 3.0:
            top_axes = sorted(deltas, key=lambda d: abs(d["delta"]), reverse=True)[:3]
            inflections.append({
                "from_idx": i - 1,
                "to_idx": i,
                "from_label": sessions[i - 1]["label"],
                "to_label": sessions[i]["label"],
                "total_shift": round(total_shift, 2),
                "top_axes": top_axes,
            })

    return sorted(inflections, key=lambda x: x["total_shift"], reverse=True)


@router.get("/drift", response_model=None)
async def drift_view(
    request: Request,
    project: str | None = None,
    db: HearthDB = Depends(get_db),
):
    """Resonance drift visualization — how collaboration evolves over time."""
    templates = request.app.state.templates
    from hearth import __version__

    project = project or None

    # Fetch sessions and attach resonance data
    raw_sessions = db.list_sessions(project=project, limit=100)
    sessions = []
    for s in raw_sessions:
        resonance = db.get_resonance(s["id"])
        if resonance is None:
            continue
        sessions.append({
            "id": s["id"],
            "label": _session_label(s),
            "date": s["started_at"][:10] if s.get("started_at") else "",
            "project": s.get("project"),
            "summary": s.get("summary"),
            "resonance": {
                axis: resonance.get(axis, 0.0) for axis in RESONANCE_AXES
            },
        })

    # Sort chronologically (oldest first — x-axis of heatmap)
    sessions.reverse()

    # Compute inflection points
    inflections = _compute_inflections(sessions) if len(sessions) >= 2 else []

    projects = db.list_projects()

    if wants_json(request):
        return JSONResponse({"sessions": sessions, "inflections": inflections})

    context = {
        "sessions_json": sessions,
        "inflections_json": inflections,
        "inflections": inflections,
        "session_count": len(sessions),
        "projects": projects,
        "project": project,
        "version": __version__,
        "active_page": "drift",
    }

    return templates.TemplateResponse(request, "drift/view.html", context)
