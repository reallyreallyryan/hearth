# Hearth

**Every AI you talk to forgets you. Hearth makes them remember.**

Hearth is a local-first persistent AI memory system. Install it once, and every AI tool you use — Claude Desktop, LM Studio, Cursor — can store and recall memories across conversations. Your data stays on your machine in a single SQLite file.

**v0.2.0 "Can You Feel That"** adds the resonance layer — an 11-dimensional emotional embedding system that captures the *texture* of each conversation, not just what was discussed, but how it felt. AI models can now carry forward collaborative momentum across sessions instead of starting cold every time.

## Quick Start

```bash
git clone https://github.com/reallyreallyryan/hearth.git
cd hearth
pip install -e .
hearth init
```

That's it. You now have a working memory system. See the [Install Guide](INSTALL_GUIDE.md) for detailed step-by-step instructions.

## Connect to Claude Desktop

1. Find your hearth path:
   ```
   which hearth
   ```

2. Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "hearth": {
         "command": "/full/path/to/hearth",
         "args": ["serve"]
       }
     }
   }
   ```
   Replace `/full/path/to/hearth` with the output from `which hearth`.

3. Quit and reopen Claude Desktop (Cmd+Q, then relaunch).

`hearth init` prints the exact config with the full path filled in — just copy and paste it.

## Connect to LM Studio

Add to `~/.lmstudio/mcp.json`:

```json
{
  "mcpServers": {
    "hearth": {
      "command": "/full/path/to/hearth",
      "args": ["serve"]
    }
  }
}
```

## CLI Commands

```
hearth init                    # Set up ~/hearth/ — database, config, pull embedding model
hearth init --no-models        # Set up without Ollama (keyword search only)
hearth serve                   # Start the MCP server (stdio transport)
hearth status                  # Show memory count, embedding status, Ollama availability
hearth remember "some fact"    # Store a memory from the command line
hearth search "query"          # Search your memories
hearth transcribe audio.wav    # Transcribe audio locally (print text, no storage)
hearth ingest audio.wav        # Transcribe + embed + store as searchable memory
hearth ui                      # Start web dashboard (localhost:8274)
hearth ui --port 9000          # Custom port
hearth ui --open               # Start and open browser
```

Options for `remember`: `-c category` (general, learning, pattern, reference, decision), `-p project`, `-t "tag1,tag2"`

Options for `search`: `-p project`, `-c category`, `-n limit`

Options for `transcribe`: `-m model` (tiny/base/small/medium/large-v3/turbo), `--json`, `--segments`

Options for `ingest`: `-m model`, `-p project`, `-c category`, `-t "tag1,tag2"`

## MCP Tools

When connected, Hearth exposes 16 tools to any MCP client:

### Memory Tools

| Tool | What it does |
|------|-------------|
| `memory_store` | Save a new memory with category, project, tags, and optional session link |
| `memory_search` | Hybrid semantic + keyword search across memories |
| `memory_list` | List memories with filters (project, category) |
| `memory_update` | Update a memory's content or metadata |
| `memory_delete` | Soft-delete (archive) a memory |

### Project Tools

| Tool | What it does |
|------|-------------|
| `project_create` | Create a new project for scoping memories |
| `project_list` | List all active projects |
| `project_get` | Get project details and memory count |
| `project_update` | Update project description or status |
| `project_archive` | Archive a project |

### Session & Resonance Tools (v0.2.0)

| Tool | What it does |
|------|-------------|
| `session_start` | Start a new session, optionally scoped to a project |
| `session_close` | Close a session with a summary and 11-axis resonance assessment |
| `session_resonance_search` | Find past sessions with similar emotional texture |
| `session_history` | List recent sessions with their resonance data |

### System Tools

| Tool | What it does |
|------|-------------|
| `hearth_status` | Database stats, embedding model status, version |
| `hearth_export` | Export all memories as JSON or CSV |

## The Resonance Layer

Every conversation has a texture — was it exploratory or executional? Were you in flow or grinding? Was the AI leading or following? The resonance layer captures this as an 11-dimensional coordinate stored alongside each session.

### The 11 Axes

Each axis is a float from -1.0 to 1.0. The AI model self-reports these values at session close.

| Axis | -1 means | +1 means |
|------|----------|----------|
| exploration_execution | Pure execution | Pure exploration |
| alignment_tension | High tension/disagreement | Full alignment |
| depth_breadth | Broad survey | Deep dive |
| momentum_resistance | Stuck/grinding | Full flow |
| novelty_familiarity | Well-trodden ground | Completely new territory |
| confidence_uncertainty | Uncertain/reaching | Confident |
| autonomy_direction | Following instructions | Leading |
| energy_entropy | Dissipating/winding down | Building/converging |
| vulnerability_performance | Performing safe answers | Vulnerable/real |
| stakes_casual | Casual chat | High stakes |
| mutual_transactional | Pure tool use | True collaboration |

### How It Works

1. **Start:** The AI calls `session_start` at the beginning of a conversation
2. **During:** Any `memory_store` calls can include a `session_id` to auto-link memories to the session
3. **Close:** The AI calls `session_close` with a qualitative summary and its self-assessment of all 11 axes
4. **Search:** Next conversation, `session_resonance_search` finds past sessions that *felt* similar — picking up momentum instead of starting from zero

Resonance data is stored as an 11-float vector in a sqlite-vec vec0 table, enabling fast similarity search across sessions.

### Viewing Resonance

The web dashboard (`hearth ui`) includes a Sessions page with:
- Session timeline with radar chart visualizations of each session's resonance signature
- Expandable session detail with per-axis bar visualization and linked memories
- Project filtering

## Your Data

Everything lives in `~/hearth/`:

```
~/hearth/
  hearth.db        <- Your memories and sessions (the important file)
  config.yaml      <- Settings (embedding model, search weights)
  hearth.db-shm    <- SQLite temp file (normal, can be ignored)
  hearth.db-wal    <- SQLite write-ahead log (normal, can be ignored)
```

The `-shm` and `-wal` files are standard SQLite housekeeping from WAL mode. They merge back into `hearth.db` automatically.

**Backup:** Copy `hearth.db` when no process has it open. To move to a new machine, copy the entire `~/hearth/` folder.

## Viewing Your Memories

### From the command line

```bash
# Search
hearth search "what did I learn about Python"

# List recent memories
hearth status

# Raw SQL query
sqlite3 ~/hearth/hearth.db "SELECT content, category, project FROM memories WHERE archived = 0 ORDER BY created_at DESC LIMIT 10;"

# Count by project
sqlite3 ~/hearth/hearth.db "SELECT COALESCE(project, '(global)'), COUNT(*) FROM memories WHERE archived = 0 GROUP BY project;"

# Export everything
sqlite3 ~/hearth/hearth.db -json "SELECT * FROM memories WHERE archived = 0;"
```

### With the Web Dashboard

```bash
hearth ui --open
```

Opens a local web dashboard at `localhost:8274` where you can:
- **Memories** — browse, search, filter, edit, and archive memories
- **Sessions** — view session timeline with resonance radar charts, expand for detail and linked memories
- **Dashboard** — stats cards, memory/session counts, Ollama status
- **Projects** — create and manage projects to organize memories
- **Export** — download all memories as JSON or CSV

Dark mode by default. Install with `pip install hearth-memory[ui]`.

### With DB Browser

[DB Browser for SQLite](https://sqlitebrowser.org) is a free app that lets you browse and edit your `hearth.db` visually. Just open `~/hearth/hearth.db`.

## How It Works

Hearth has three layers:

**The Brain** — a single SQLite database (`hearth.db`) with:
- Structured memory storage (content, category, project, tags, timestamps)
- Full-text search via FTS5 (keyword matching)
- Vector similarity search via sqlite-vec (semantic meaning, 768 dimensions)
- Hybrid search that combines both, weighted and normalized
- Session and resonance tables for emotional context tracking
- 11-dimensional resonance embeddings via sqlite-vec for session similarity search

**The Spine** — a Python MCP server that exposes the Brain to any MCP-compatible client. It runs over stdio (Claude Desktop spawns it as a subprocess) and handles all read/write operations. Includes memory, project, session, and resonance tools.

**The Shell** — a local web dashboard (`hearth ui`) built with FastAPI, Jinja2, and htmx. Browse memories, view session timelines with resonance radar charts, manage projects. Dark mode, no build step, no JavaScript framework. Runs alongside the MCP server — both read/write the same `hearth.db`.

Embeddings are generated locally via Ollama using the `nomic-embed-text` model (768 dimensions). If Ollama isn't available, the server still works — search falls back to keyword-only mode, and embeddings are backfilled when Ollama comes online.

**Audio Transcription** — Hearth can transcribe audio files locally using faster-whisper (a CTranslate2-based Whisper implementation). `hearth ingest audio.wav` transcribes the audio, generates an embedding, and stores it as a searchable memory. No cloud APIs — everything runs on your machine.

## Requirements

- Python 3.11+
- Ollama (optional — for semantic search)
- ~300MB disk space for the embedding model
- faster-whisper (optional — for audio transcription, install with `pip install hearth-memory[transcribe]`)
- FastAPI + Jinja2 (optional — for web dashboard, install with `pip install hearth-memory[ui]`)

## Credits

Built with:
- [Ollama](https://ollama.ai) — local model inference
- [nomic-embed-text](https://ollama.com/library/nomic-embed-text) — embedding model
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — local audio transcription (CTranslate2)
- [FastAPI](https://fastapi.tiangolo.com) — web dashboard backend
- [htmx](https://htmx.org) — lightweight dynamic UI interactions
- [sqlite-vec](https://github.com/asg017/sqlite-vec) — vector similarity search for SQLite
- [APSW](https://github.com/rogerbinns/apsw) — Python SQLite wrapper with extension support
- [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) — Model Context Protocol server framework
- [Click](https://click.palletsprojects.com/) — CLI framework

## License

MIT
