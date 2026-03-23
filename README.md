# Hearth

**Every AI you talk to forgets you. Hearth makes them remember.**

Hearth is a local-first persistent AI memory system. Install it once, and every AI tool you use — Claude Desktop, LM Studio, Cursor — can store and recall memories across conversations. Your data stays on your machine in a single SQLite file.

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
hearth init --no-models        # Set up without Ollama (cloud-only, keyword search only)
hearth serve                   # Start the MCP server (stdio transport)
hearth status                  # Show memory count, embedding status, Ollama availability
hearth remember "some fact"    # Store a memory from the command line
hearth search "query"          # Search your memories
```

Options for `remember`: `-c category` (general, learning, pattern, reference, decision), `-p project`, `-t "tag1,tag2"`

Options for `search`: `-p project`, `-c category`, `-n limit`

## MCP Tools

When connected, Hearth exposes 12 tools to any MCP client:

| Tool | What it does |
|------|-------------|
| `memory_store` | Save a new memory with category, project, and tags |
| `memory_search` | Hybrid semantic + keyword search across memories |
| `memory_list` | List memories with filters (project, category) |
| `memory_update` | Update a memory's content or metadata |
| `memory_delete` | Soft-delete (archive) a memory |
| `project_create` | Create a new project for scoping memories |
| `project_list` | List all active projects |
| `project_get` | Get project details and memory count |
| `project_update` | Update project description or status |
| `project_archive` | Archive a project |
| `hearth_status` | Database stats, embedding model status, version |
| `hearth_export` | Export all memories as JSON or CSV |

## Your Data

Everything lives in `~/hearth/`:

```
~/hearth/
  hearth.db        <- Your memories (the important file)
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

### With a GUI

[DB Browser for SQLite](https://sqlitebrowser.org) is a free app that lets you browse, search, and edit your `hearth.db` visually. Just open `~/hearth/hearth.db`.

## How It Works

Hearth has two layers:

**The Brain** — a single SQLite database (`hearth.db`) with:
- Structured memory storage (content, category, project, tags, timestamps)
- Full-text search via FTS5 (keyword matching)
- Vector similarity search via sqlite-vec (semantic meaning)
- Hybrid search that combines both, weighted and normalized

**The Spine** — a Python MCP server that exposes the Brain to any MCP-compatible client. It runs over stdio (Claude Desktop spawns it as a subprocess) and handles all read/write operations.

Embeddings are generated locally via Ollama using the `nomic-embed-text` model (768 dimensions). If Ollama isn't available, the server still works — search falls back to keyword-only mode, and embeddings are backfilled when Ollama comes online.

## Requirements

- Python 3.11+
- Ollama (optional — for semantic search)
- ~300MB disk space for the embedding model

## Credits

Built with:
- [Ollama](https://ollama.ai) — local model inference
- [nomic-embed-text](https://ollama.com/library/nomic-embed-text) — embedding model
- [sqlite-vec](https://github.com/asg017/sqlite-vec) — vector similarity search for SQLite
- [APSW](https://github.com/rogerbinns/apsw) — Python SQLite wrapper with extension support
- [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) — Model Context Protocol server framework
- [Click](https://click.palletsprojects.com/) — CLI framework

## License

MIT
