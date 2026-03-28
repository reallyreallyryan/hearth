# CLAUDE.md — Hearth

## Project Overview

Hearth is a local-first persistent AI memory system. Users download it, install it, and have a personal knowledge base running on their machine that any AI model can read from and write to via MCP.

**Read `HEARTH_PROJECT_BRIEF.md` for the full spec, schema, architecture, and build order.**

## Install with Claude Code

If the user asks to set up, install, or get Hearth running:

```bash
pip install -e ".[transcribe,ui]"
hearth init
```

Optional extras: `[transcribe]` adds faster-whisper for audio transcription, `[ui]` adds the web dashboard. Without them, all memory/MCP features still work.

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

- **Brain:** SQLite database (`hearth.db`) with structured memory storage, FTS5, sqlite-vec for embeddings, and resonance tables for session-level emotional fingerprints
- **Spine:** Python MCP server exposing memory/project/session tools to any MCP client (Claude Desktop, LM Studio, Cursor, etc.)
- **Shell:** CLI tools (`hearth init`, `hearth serve`, `hearth ui`) + web dashboard (FastAPI + htmx) with session timeline and resonance radar charts

The MCP server IS the product. The .db file is the product. Everything else is a front door.

## Build Order

Follow the MCP-first strategy in the project brief:
1. **Phase 1 — Brain + Spine (MVP) (DONE):** `schema.sql` → `db.py` → `search.py` → `embeddings.py` → `hearth_server.py` → `config.py` → tests → package as pip-installable CLI
   - **Phase 1a — Transcription (DONE):** `transcribe.py` — local audio transcription via faster-whisper. `hearth transcribe` CLI command.
   - **Phase 1b — Ingest Pipeline (DONE):** `hearth ingest` — transcribe audio → embed → store as searchable memory. Full loop: voice → database → queryable via MCP.
2. **Phase 3a — Web Dashboard (DONE):** `hearth ui` — local web dashboard for browsing, searching, editing, and managing memories. FastAPI + Jinja2 + htmx. Dark mode. No build step.
3. **Phase 3b — Resonance Layer (DONE):** 11-dimensional emotional embedding system for session-level context. Captures the texture of AI-human collaboration — not just what was discussed, but how it felt. Includes `resonance_schema.sql`, session/resonance CRUD in `db.py`, 4 new MCP tools, vec0 similarity search in resonance space, and web dashboard with radar chart visualization.
4. **Phase 4 — Ecosystem:** Plugins for Claude Desktop, LM Studio, OpenClaw

**Phase 1 is the entire shippable product. A user should be able to `pip install hearth-memory`, run `hearth init && hearth serve`, and have persistent memory working in Claude Desktop and LM Studio within 2 minutes.**

## Tech Decisions (Locked)

- **Database:** SQLite + sqlite-vec + FTS5 (single file, portable)
- **MCP Server:** Python (use `mcp` or `fastmcp` library, whichever is current)
- **Embeddings:** nomic-embed-text via Ollama (768 dimensions for memories, 11 dimensions for resonance)
- **Transcription:** faster-whisper (CTranslate2 backend) — local Whisper inference, no cloud APIs. Optional dependency.
- **Chat Model:** phi3:mini or mistral:7b via Ollama
- **Web UI:** FastAPI + Jinja2 + htmx. Dark mode. No React, no build step, no node_modules. Optional dependency.
- **Config:** YAML (`config.yaml`)
- **Tests:** pytest

## Code Standards

- Every database operation must have a corresponding test
- Search functions must have tests with known data
- Use type hints in all Python code
- Keep dependencies minimal — this runs on user machines
- Core SQL in `schema.sql`, resonance SQL in `resonance_schema.sql`, not scattered across Python files
- Errors should be informative — users will see them during setup

## Architecture Pattern

This mirrors the cairn SCMS (Structured Context Memory System) architecture:
- Memories have: content, category, project, tags, source, timestamps
- Categories: learning, pattern, reference, decision, general
- Projects scope memories — searching within a project excludes other project noise
- Global memories (project=NULL) are available in all contexts
- Soft-delete only (archived flag, never hard delete)
- Hybrid search: semantic similarity (sqlite-vec) + keyword (FTS5) + structured (SQL filters)

### Resonance Layer (v0.2.0)

Sessions wrap conversations with emotional context:
- Sessions have: id, project, started_at, ended_at, summary, memory_count
- Session resonance: 11 float axes from -1.0 to 1.0 (exploration/execution, alignment/tension, depth/breadth, momentum/resistance, novelty/familiarity, confidence/uncertainty, autonomy/direction, energy/entropy, vulnerability/performance, stakes/casual, mutual/transactional)
- Resonance embeddings: 11-dimensional vec0 table for similarity search across sessions
- Session-memory links: which memories were created or accessed during which session
- The AI model self-reports resonance at session close — no text analysis, no inference
- `RESONANCE_AXES` tuple in `config.py` defines axis order (matters for vec0 packing)

## What NOT to Build

- No cloud sync, no external API calls (except Ollama on localhost)
- No background agents or autonomous tasks
- No custom model training
- No mobile support
- No automatic resonance inference from text analysis — the model self-reports
- No resonance on individual memories — it's session-level only
- Web UI is optional (`pip install hearth-memory[ui]`) — the MCP server is the core product
- Keep dependencies minimal — this runs on user machines

## CLI Interface

The package is pip-installable and exposes a CLI:
```
pip install hearth-memory
pip install hearth-memory[transcribe]  # Adds audio transcription support

hearth init              # Creates ~/hearth/hearth.db, config.yaml, pulls embedding model via Ollama
hearth serve             # Starts the MCP server (default: stdio for Claude Desktop/LM Studio)
hearth status            # Shows DB stats, server status, model info
hearth remember "x"      # Quick-store a memory from the command line
hearth search "x"        # Quick-search from the command line
hearth transcribe f.wav  # Transcribe an audio file (print text, no DB storage)
hearth ingest f.wav      # Transcribe + embed + store as searchable memory
hearth ui                # Start the web dashboard (localhost:8274)
```

`hearth transcribe` options: `--model` (tiny/base/small/medium/large-v3/turbo), `--json`, `--segments`

`hearth ingest` options: `--model`, `--project`, `--category`, `--tags`

Package structure should use `pyproject.toml` with a `[project.scripts]` entry point.
