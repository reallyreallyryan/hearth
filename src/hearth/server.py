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
        "Set project to scope the memory, or leave empty for global."
    ),
)
async def memory_store(
    content: str,
    category: str = "general",
    project: str | None = None,
    tags: list[str] | None = None,
    source: str = "assistant",
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


def run_server() -> None:
    """Entry point for `hearth serve`. Runs MCP server over stdio."""
    mcp.run(transport="stdio")
