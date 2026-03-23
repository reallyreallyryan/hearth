# CLAUDE.md — Hearth

## Project Overview

Hearth is a local-first persistent AI memory system. Users download it, install it, and have a personal knowledge base running on their machine that any AI model can read from and write to via MCP.

**Read `HEARTH_PROJECT_BRIEF.md` for the full spec, schema, architecture, and build order.**

## Install with Claude Code

If the user asks to set up, install, or get Hearth running:

```bash
pip install -e .
hearth init
```

`hearth init` will:
1. Create `~/hearth/` with the database and config
2. Check for Ollama and pull `nomic-embed-text` if available
3. Print the Claude Desktop config snippet with the **full path** to the hearth binary

Tell the user to:
1. Copy the printed config into `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Quit Claude Desktop fully (Cmd+Q) and reopen it
3. Verify Hearth tools appear in Settings > Connectors > hearth

If the user doesn't want Ollama: `hearth init --no-models`

For detailed instructions, see `INSTALL_GUIDE.md`.

## Quick Context

- **Brain:** SQLite database (`hearth.db`) with structured memory storage, FTS5, and sqlite-vec for embeddings
- **Spine:** Python MCP server exposing memory/project tools to any MCP client (Claude Desktop, LM Studio, Cursor, etc.)
- **Shell:** CLI tools (`hearth init`, `hearth serve`) + web UI (Phase 2)

The MCP server IS the product. The .db file is the product. Everything else is a front door.

## Build Order

Follow the MCP-first strategy in the project brief:
1. **Phase 1 — Brain + Spine (MVP):** `schema.sql` → `db.py` → `search.py` → `embeddings.py` → `hearth_server.py` → `config.py` → tests → package as pip-installable CLI
2. **Phase 2 — Shell:** `install.sh` → Web UI → setup wizard → local chat  
3. **Phase 3 — Ecosystem:** Plugins for Claude Desktop, LM Studio, OpenClaw

**Phase 1 is the entire shippable product. A user should be able to `pip install hearth-memory`, run `hearth init && hearth serve`, and have persistent memory working in Claude Desktop and LM Studio within 2 minutes.**

**Do not build UI before Phase 1 is complete, tested, and working end-to-end with real MCP clients.**

## Tech Decisions (Locked)

- **Database:** SQLite + sqlite-vec + FTS5 (single file, portable)
- **MCP Server:** Python (use `mcp` or `fastmcp` library, whichever is current)
- **Embeddings:** nomic-embed-text via Ollama (768 dimensions)
- **Chat Model:** phi3:mini or mistral:7b via Ollama
- **Web UI:** Lightweight — vanilla HTML/JS/CSS or minimal React. No heavy frameworks.
- **Config:** YAML (`config.yaml`)
- **Tests:** pytest

## Code Standards

- Every database operation must have a corresponding test
- Search functions must have tests with known data
- Use type hints in all Python code
- Keep dependencies minimal — this runs on user machines
- All SQL in `schema.sql`, not scattered across Python files
- Errors should be informative — users will see them during setup

## Architecture Pattern

This mirrors the cairn SCMS (Structured Context Memory System) architecture:
- Memories have: content, category, project, tags, source, timestamps
- Categories: learning, pattern, reference, decision, general
- Projects scope memories — searching within a project excludes other project noise
- Global memories (project=NULL) are available in all contexts
- Soft-delete only (archived flag, never hard delete)
- Hybrid search: semantic similarity (sqlite-vec) + keyword (FTS5) + structured (SQL filters)

## What NOT to Build

- No cloud sync, no external API calls (except Ollama on localhost)
- No background agents or autonomous tasks
- No custom model training
- No mobile support
- No web UI in Phase 1 — the MCP server is the product
- Keep dependencies minimal — this runs on user machines

## CLI Interface (Phase 1 deliverable)

The package should be pip-installable and expose a CLI:
```
pip install hearth-memory
hearth init          # Creates ~/hearth/hearth.db, config.yaml, pulls embedding model via Ollama
hearth serve         # Starts the MCP server (default: stdio for Claude Desktop/LM Studio)
hearth status        # Shows DB stats, server status, model info
hearth remember "x"  # Quick-store a memory from the command line (nice to have)
hearth search "x"    # Quick-search from the command line (nice to have)
```

Package structure should use `pyproject.toml` with a `[project.scripts]` entry point.