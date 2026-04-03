"""Hearth MCP server. Exposes memory/project/system tools via FastMCP."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from hearth import __version__
from hearth.config import HearthConfig, load_config
from hearth.db import HearthDB
from hearth.embeddings import OllamaEmbedder
from hearth.context import ContextAssembler
from hearth.search import hybrid_search

# All logging to stderr — stdout is reserved for MCP stdio transport
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("hearth.server")


def _get_db(ctx: Context) -> HearthDB:
    return ctx.request_context.lifespan_context["db"]


def _get_embedder(ctx: Context) -> OllamaEmbedder:
    return ctx.request_context.lifespan_context["embedder"]


def _get_config(ctx: Context) -> HearthConfig:
    return ctx.request_context.lifespan_context["config"]


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Initialize DB and embedder on startup, clean up on shutdown."""
    config = load_config()
    db = HearthDB(config.db_path)
    db.init_db()
    logger.info("Database initialized at %s", config.db_path)

    embedder = OllamaEmbedder(
        base_url=config.ollama_base_url,
        model=config.embedding.model,
        dimensions=config.embedding.dimensions,
    )
    available = await embedder.check_available()
    if available:
        logger.info("Ollama available with model '%s'", config.embedding.model)
        count = await embedder.process_pending(db)
        if count:
            logger.info("Backfilled %d pending embeddings", count)
    else:
        logger.warning(
            "Ollama not available — server will run with FTS-only search. "
            "Start Ollama and the embedding model to enable semantic search."
        )

    try:
        yield {"db": db, "embedder": embedder, "config": config}
    finally:
        db.close()
        logger.info("Hearth server shut down")


mcp = FastMCP(
    name="hearth",
    instructions=(
        "Hearth is a persistent AI memory system. Use these tools to store, "
        "search, and manage memories that persist across conversations and clients. "
        "Memories can be scoped to projects or be global."
    ),
    lifespan=lifespan,
)


# ── Memory Tools ────────────────────────────────────────────────────


@mcp.tool(
    name="memory_store",
    description=(
        "Store a new memory. Categories: general, learning, pattern, reference, decision. "
        "Set project to scope the memory, or leave empty for global. "
        "Pass session_id to link the memory to an active session."
    ),
)
async def memory_store(
    content: str,
    category: str = "general",
    project: str | None = None,
    tags: list[str] | None = None,
    source: str = "assistant",
    session_id: str | None = None,
    ctx: Context = None,
) -> dict[str, Any]:
    db = _get_db(ctx)
    embedder = _get_embedder(ctx)

    try:
        memory = db.store_memory(content, category, project, tags, source)
    except ValueError as e:
        return {"error": str(e)}

    result = await embedder.embed(content)
    if result:
        db.store_embedding(memory["id"], result.embedding)
        memory["has_embedding"] = True
    else:
        memory["has_embedding"] = False

    if session_id is not None:
        try:
            db.link_memory_to_session(session_id, memory["id"], "created")
            memory["session_id"] = session_id
        except ValueError as e:
            memory["session_link_error"] = str(e)

    return memory


@mcp.tool(
    name="memory_search",
    description="Search memories using hybrid semantic + keyword search. Returns ranked results.",
)
async def memory_search(
    query: str,
    project: str | None = None,
    category: str | None = None,
    limit: int = 10,
    ctx: Context = None,
) -> list[dict[str, Any]]:
    db = _get_db(ctx)
    embedder = _get_embedder(ctx)
    config = _get_config(ctx)

    results = await hybrid_search(
        query, db, embedder,
        project=project, category=category, limit=limit,
        config=config.search,
    )
    return [
        {"memory": r.memory, "score": r.score, "match_type": r.match_type}
        for r in results
    ]


@mcp.tool(
    name="memory_update",
    description="Update an existing memory's content, category, project, or tags.",
)
async def memory_update(
    id: str,
    content: str | None = None,
    category: str | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
    ctx: Context = None,
) -> dict[str, Any]:
    db = _get_db(ctx)
    embedder = _get_embedder(ctx)

    try:
        updated = db.update_memory(id, content, category, project, tags)
    except ValueError as e:
        return {"error": str(e)}

    if updated is None:
        return {"error": f"Memory '{id}' not found"}

    # Re-embed if content changed
    if content is not None:
        try:
            db.delete_embedding(id)
        except Exception:
            pass
        result = await embedder.embed(content)
        if result:
            db.store_embedding(id, result.embedding)
            updated["has_embedding"] = True
        else:
            updated["has_embedding"] = False

    return updated


@mcp.tool(
    name="memory_delete",
    description="Soft-delete (archive) a memory. It won't appear in searches but is not permanently removed.",
)
async def memory_delete(id: str, ctx: Context = None) -> dict[str, Any]:
    db = _get_db(ctx)
    if db.delete_memory(id):
        return {"deleted": True, "id": id}
    return {"error": f"Memory '{id}' not found"}


@mcp.tool(
    name="memory_list",
    description="List memories with optional project/category filters. Returns newest first.",
)
async def memory_list(
    project: str | None = None,
    category: str | None = None,
    limit: int = 10,
    offset: int = 0,
    ctx: Context = None,
) -> list[dict[str, Any]]:
    db = _get_db(ctx)
    return db.list_memories(project=project, category=category, limit=limit, offset=offset)


# ── Project Tools ───────────────────────────────────────────────────


@mcp.tool(
    name="project_create",
    description="Create a new project for scoping memories.",
)
async def project_create(
    name: str, description: str | None = None, ctx: Context = None
) -> dict[str, Any]:
    db = _get_db(ctx)
    try:
        return db.create_project(name, description)
    except ValueError as e:
        return {"error": str(e)}


@mcp.tool(
    name="project_list",
    description="List all active projects.",
)
async def project_list(ctx: Context = None) -> list[dict[str, Any]]:
    db = _get_db(ctx)
    return db.list_projects()


@mcp.tool(
    name="project_get",
    description="Get project details including memory count.",
)
async def project_get(name: str, ctx: Context = None) -> dict[str, Any]:
    db = _get_db(ctx)
    project = db.get_project(name)
    if project is None:
        return {"error": f"Project '{name}' not found"}
    return project


@mcp.tool(
    name="project_update",
    description="Update a project's description or status (active, paused, completed, archived).",
)
async def project_update(
    name: str,
    description: str | None = None,
    status: str | None = None,
    ctx: Context = None,
) -> dict[str, Any]:
    db = _get_db(ctx)
    try:
        updated = db.update_project(name, description=description, status=status)
    except ValueError as e:
        return {"error": str(e)}
    if updated is None:
        return {"error": f"Project '{name}' not found"}
    return updated


@mcp.tool(
    name="project_archive",
    description="Archive a project. Its memories remain but the project is hidden from listings.",
)
async def project_archive(name: str, ctx: Context = None) -> dict[str, Any]:
    db = _get_db(ctx)
    if db.archive_project(name):
        return {"archived": True, "name": name}
    return {"error": f"Project '{name}' not found"}


# ── System Tools ────────────────────────────────────────────────────


@mcp.tool(
    name="hearth_status",
    description="Get Hearth system status: database stats, embedding model status, version info.",
)
async def hearth_status(ctx: Context = None) -> dict[str, Any]:
    db = _get_db(ctx)
    embedder = _get_embedder(ctx)

    stats = db.get_stats()
    available = await embedder.check_available()

    # Backfill pending if Ollama just came online
    if available and stats["pending_embeddings"] > 0:
        count = await embedder.process_pending(db)
        stats = db.get_stats()
        stats["backfilled_embeddings"] = count

    return {
        "version": __version__,
        "database": str(db.db_path),
        "ollama_available": available,
        "embedding_model": embedder.model,
        **stats,
    }


@mcp.tool(
    name="hearth_export",
    description="Export all memories as JSON or CSV.",
)
async def hearth_export(format: str = "json", ctx: Context = None) -> str:
    db = _get_db(ctx)
    try:
        return db.export_memories(format=format)
    except ValueError as e:
        return str(e)


# ── Session & Resonance Tools ──────────────────────────────────────


@mcp.tool(
    name="session_start",
    description=(
        "Start or resume a session. If an open session already exists for the "
        "given project, returns it instead of creating a new one (with resumed=True). "
        "Optionally scope to a project. Returns the session ID. After calling this, "
        "ALWAYS call hearth_briefing with the same project to get context about "
        "who you're talking to and how to close the session properly."
    ),
)
async def session_start(
    project: str | None = None,
    ctx: Context = None,
) -> dict[str, Any]:
    db = _get_db(ctx)

    # Guard: check for existing open session
    existing = db.get_open_session(project=project)
    if existing:
        existing["resumed"] = True
        existing["message"] = (
            f"You already have an open session ({existing['id'][:8]}...). "
            "Resuming it instead of starting a new one."
        )
        if project:
            existing["next_step"] = (
                f"Call hearth_briefing(project='{project}') to get context about "
                "who you're talking to, what's been happening, and how to close this session."
            )
        else:
            existing["next_step"] = (
                "Call hearth_briefing() to get context about who you're talking to, "
                "what's been happening, and how to close this session."
            )
        return existing

    # No open session — create a new one
    try:
        session = db.create_session(project=project)
    except ValueError as e:
        return {"error": str(e)}

    if project:
        session["next_step"] = (
            f"Call hearth_briefing(project='{project}') to get context about "
            "who you're talking to, what's been happening, and how to close this session."
        )
    else:
        session["next_step"] = (
            "Call hearth_briefing() to get context about who you're talking to, "
            "what's been happening, and how to close this session."
        )
    return session


@mcp.tool(
    name="session_close",
    description=(
        "Close a session with a summary and 11-axis resonance assessment. "
        "Each axis is a float from -1.0 to 1.0. Call at the end of a conversation. "
        "See the resonance scoring guide from hearth_briefing for axis definitions "
        "and calibration hints. If the briefing has scrolled out of context, call "
        "hearth_context(query='resonance scoring guide') to retrieve it."
    ),
)
async def session_close(
    session_id: str,
    summary: str | None = None,
    exploration_execution: float = 0.0,
    alignment_tension: float = 0.0,
    depth_breadth: float = 0.0,
    momentum_resistance: float = 0.0,
    novelty_familiarity: float = 0.0,
    confidence_uncertainty: float = 0.0,
    autonomy_direction: float = 0.0,
    energy_entropy: float = 0.0,
    vulnerability_performance: float = 0.0,
    stakes_casual: float = 0.0,
    mutual_transactional: float = 0.0,
    ctx: Context = None,
) -> dict[str, Any]:
    db = _get_db(ctx)

    axes = {
        "exploration_execution": exploration_execution,
        "alignment_tension": alignment_tension,
        "depth_breadth": depth_breadth,
        "momentum_resistance": momentum_resistance,
        "novelty_familiarity": novelty_familiarity,
        "confidence_uncertainty": confidence_uncertainty,
        "autonomy_direction": autonomy_direction,
        "energy_entropy": energy_entropy,
        "vulnerability_performance": vulnerability_performance,
        "stakes_casual": stakes_casual,
        "mutual_transactional": mutual_transactional,
    }

    # Reject all-zero resonance (local models skip optional params)
    if all(v == 0.0 for v in axes.values()):
        return {
            "error": "All resonance scores are 0.0. This usually means scores were skipped. "
                     "Please score each axis from -1.0 to 1.0 based on how this session actually felt. "
                     "Use the resonance scoring guide from hearth_briefing for definitions. "
                     "If the guide has scrolled out of context, call hearth_context(query='resonance scoring guide') to retrieve it. "
                     "No axis is inherently good or bad — both poles are valid. Score what happened, not what sounds right.",
            "session_id": session_id,
            "hint": "Even a short session has texture. A quick setup session might be: "
                    "exploration_execution=-0.8 (pure execution), stakes_casual=-0.5 (low stakes), "
                    "mutual_transactional=-0.3 (somewhat transactional). Zeros mean 'I didn't try.'",
        }

    session = db.close_session(session_id, summary=summary)
    if session is None:
        return {"error": f"Session '{session_id}' not found"}

    try:
        resonance = db.store_resonance(session_id, axes)
    except ValueError as e:
        return {"error": str(e)}

    session["resonance"] = resonance

    # Increment session close counter; trigger vitality computation every Nth close
    close_count = db.increment_session_close_count()
    config = _get_config(ctx)
    if close_count % config.vitality.compute_every_n_closes == 0:
        transitions = db.compute_vitality(config.vitality)
        session["vitality_transitions"] = transitions

    return session


@mcp.tool(
    name="session_resonance_search",
    description=(
        "Find sessions with similar resonance signatures. "
        "Returns sessions ranked by proximity in resonance space, "
        "including their summaries and linked memories."
    ),
)
async def session_resonance_search(
    exploration_execution: float = 0.0,
    alignment_tension: float = 0.0,
    depth_breadth: float = 0.0,
    momentum_resistance: float = 0.0,
    novelty_familiarity: float = 0.0,
    confidence_uncertainty: float = 0.0,
    autonomy_direction: float = 0.0,
    energy_entropy: float = 0.0,
    vulnerability_performance: float = 0.0,
    stakes_casual: float = 0.0,
    mutual_transactional: float = 0.0,
    limit: int = 5,
    ctx: Context = None,
) -> list[dict[str, Any]]:
    db = _get_db(ctx)

    axes = {
        "exploration_execution": exploration_execution,
        "alignment_tension": alignment_tension,
        "depth_breadth": depth_breadth,
        "momentum_resistance": momentum_resistance,
        "novelty_familiarity": novelty_familiarity,
        "confidence_uncertainty": confidence_uncertainty,
        "autonomy_direction": autonomy_direction,
        "energy_entropy": energy_entropy,
        "vulnerability_performance": vulnerability_performance,
        "stakes_casual": stakes_casual,
        "mutual_transactional": mutual_transactional,
    }

    try:
        results = db.search_resonance(axes, limit=limit)
    except ValueError as e:
        return [{"error": str(e)}]

    enriched = []
    for session_id, distance in results:
        session = db.get_session(session_id)
        if session is None:
            continue
        resonance = db.get_resonance(session_id)
        memories = db.get_session_memories(session_id)
        enriched.append({
            "session": session,
            "resonance": resonance,
            "distance": distance,
            "memories": memories,
        })
    return enriched


@mcp.tool(
    name="session_history",
    description="List recent sessions with their resonance data and summaries. Optionally filter by project.",
)
async def session_history(
    project: str | None = None,
    limit: int = 10,
    ctx: Context = None,
) -> list[dict[str, Any]]:
    db = _get_db(ctx)
    sessions = db.list_sessions(project=project, limit=limit)
    for session in sessions:
        session["resonance"] = db.get_resonance(session["id"])
    return sessions


# ── Thread & Tension Tools ─────────────────────────────────────────


@mcp.tool(
    name="thread_list",
    description=(
        "List active threads, optionally filtered by project or status. "
        "Use at session start to see what lines of inquiry are open. "
        "Each thread includes its current trajectory, session count, and tension count."
    ),
)
async def thread_list(
    project: str | None = None,
    status: str | None = None,
    limit: int = 20,
    ctx: Context = None,
) -> list[dict[str, Any]]:
    db = _get_db(ctx)
    try:
        return db.list_threads(project=project, status=status, limit=limit)
    except ValueError as e:
        return [{"error": str(e)}]


@mcp.tool(
    name="tension_list",
    description=(
        "List open tensions (unresolved questions or disagreements). "
        "Optionally filter by thread, project, or status. "
        "Use at session start to see what's unresolved."
    ),
)
async def tension_list(
    thread_id: str | None = None,
    project: str | None = None,
    status: str | None = None,
    limit: int = 20,
    ctx: Context = None,
) -> list[dict[str, Any]]:
    db = _get_db(ctx)
    try:
        return db.list_tensions(
            thread_id=thread_id, project=project, status=status, limit=limit,
        )
    except ValueError as e:
        return [{"error": str(e)}]


@mcp.tool(
    name="session_reflect",
    description=(
        "Reflect on threads and tensions at session close. "
        "Create new threads, update existing ones with trajectory notes, "
        "create new tensions, add perspectives to existing tensions, "
        "and resolve tensions. Call this alongside session_close."
    ),
)
async def session_reflect(
    session_id: str,
    threads: list[dict[str, Any]] | None = None,
    tensions: list[dict[str, Any]] | None = None,
    ctx: Context = None,
) -> dict[str, Any]:
    db = _get_db(ctx)

    # Validate the session exists
    try:
        db._validate_session_exists(session_id)
    except ValueError as e:
        return {"error": str(e)}

    results: dict[str, Any] = {
        "session_id": session_id,
        "threads_created": [],
        "threads_updated": [],
        "threads_linked": [],
        "tensions_created": [],
        "perspectives_added": [],
        "tensions_resolved": [],
        "errors": [],
    }

    for i, ta in enumerate(threads or []):
        try:
            action = ta.get("action")
            if action == "create":
                thread = db.create_thread(
                    title=ta["title"],
                    project=ta.get("project"),
                    trajectory=ta.get("trajectory"),
                    session_id=session_id,
                )
                results["threads_created"].append(thread)
            elif action == "update":
                thread = db.update_thread(
                    thread_id=ta["thread_id"],
                    title=ta.get("title"),
                    status=ta.get("status"),
                    trajectory=ta.get("trajectory"),
                )
                if thread is None:
                    results["errors"].append(
                        {"index": i, "type": "thread",
                         "error": f"Thread '{ta['thread_id']}' not found"}
                    )
                else:
                    db.link_thread_session(
                        ta["thread_id"], session_id,
                        trajectory_note=ta.get("trajectory_note"),
                    )
                    results["threads_updated"].append(thread)
            elif action == "link":
                db.link_thread_session(
                    thread_id=ta["thread_id"],
                    session_id=session_id,
                    trajectory_note=ta.get("trajectory_note"),
                )
                results["threads_linked"].append(
                    {"thread_id": ta["thread_id"], "session_id": session_id}
                )
            else:
                results["errors"].append(
                    {"index": i, "type": "thread",
                     "error": f"Unknown thread action '{action}'"}
                )
        except (ValueError, KeyError) as e:
            results["errors"].append(
                {"index": i, "type": "thread", "error": str(e)}
            )

    for i, ta in enumerate(tensions or []):
        try:
            action = ta.get("action")
            if action == "create":
                tension = db.create_tension(
                    question=ta["question"],
                    thread_id=ta.get("thread_id"),
                    session_id=session_id,
                )
                results["tensions_created"].append(tension)
            elif action == "perspective":
                tension = db.add_tension_perspective(
                    tension_id=ta["tension_id"],
                    perspective=ta["perspective"],
                    source=ta.get("source", "assistant"),
                    session_id=session_id,
                )
                if tension is None:
                    results["errors"].append(
                        {"index": i, "type": "tension",
                         "error": f"Tension '{ta['tension_id']}' not found"}
                    )
                else:
                    results["perspectives_added"].append(tension)
            elif action == "resolve":
                tension = db.update_tension(
                    tension_id=ta["tension_id"],
                    status=ta.get("status", "resolved"),
                    resolution=ta.get("resolution"),
                    resolved_session_id=session_id,
                )
                if tension is None:
                    results["errors"].append(
                        {"index": i, "type": "tension",
                         "error": f"Tension '{ta['tension_id']}' not found"}
                    )
                else:
                    results["tensions_resolved"].append(tension)
            else:
                results["errors"].append(
                    {"index": i, "type": "tension",
                     "error": f"Unknown tension action '{action}'"}
                )
        except (ValueError, KeyError) as e:
            results["errors"].append(
                {"index": i, "type": "tension", "error": str(e)}
            )

    return results


# ── Contextual Briefing & RAG Tools ──────────────────────────────


@mcp.tool(
    name="hearth_briefing",
    description=(
        "Get a contextual briefing assembled from Hearth's data. "
        "Call this after session_start to understand who you're talking to, "
        "what's been happening, what's unresolved, and how to close the session. "
        "Includes recent sessions with resonance descriptions, active threads, "
        "open tensions, drift trends, high-vitality memories, and the resonance "
        "scoring guide for session_close."
    ),
)
async def hearth_briefing(
    project: str | None = None,
    token_budget: int | None = None,
    ctx: Context = None,
) -> dict[str, Any]:
    db = _get_db(ctx)
    if token_budget is None:
        config = _get_config(ctx)
        token_budget = config.briefing_token_budget
    assembler = ContextAssembler(db)
    return assembler.assemble_briefing(project=project, token_budget=token_budget)


@mcp.tool(
    name="hearth_context",
    description=(
        "Search across all of Hearth's data for context on a specific topic. "
        "Unlike hearth_briefing (which gives ambient context), this tool "
        "answers a specific question by searching memories, threads, "
        "tensions, and session history."
    ),
)
async def hearth_context(
    query: str,
    project: str | None = None,
    token_budget: int | None = None,
    ctx: Context = None,
) -> dict[str, Any]:
    db = _get_db(ctx)
    if token_budget is None:
        config = _get_config(ctx)
        token_budget = config.briefing_token_budget
    assembler = ContextAssembler(db)
    return assembler.assemble_context(
        query=query, project=project, token_budget=token_budget,
    )


def run_server() -> None:
    """Entry point for `hearth serve`. Runs MCP server over stdio."""
    mcp.run(transport="stdio")
