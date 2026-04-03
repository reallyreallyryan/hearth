# Hearth

**Every AI you talk to forgets you. Hearth makes them remember.**

But memory is more than facts. You don't just remember *what* happened in a conversation — you remember how it felt. Whether you were on fire or grinding. Whether you were exploring or executing. Whether the person across from you was a tool or a collaborator.

AI doesn't get that. Every session starts cold. No momentum. No context. No relationship.

Hearth fixes both problems.

---

## What Hearth Actually Is

Hearth is a **local-first personal memory system** that any AI model can read from and write to. Install it once, and Claude Desktop, LM Studio, Cursor — anything that speaks MCP — shares a single persistent memory.

Your data stays on your machine in a single SQLite file. No cloud. No telemetry. No third-party access. Period.

But Hearth also introduces something nobody else is building: a **Relationship Persistence Layer**.

### The Relationship Persistence Layer

Every AI memory system stores facts about you. Some even infer your emotional state — "the user seems stressed," "the user spends more when anxious." That's surveillance dressed as personalization.

Hearth flips this. Instead of watching *you*, the AI reports on *itself* — how the session felt from its side. Was it exploratory or executional? Was there tension or alignment? Was the AI performing safe answers or being genuinely vulnerable?

This creates an 11-dimensional emotional fingerprint for every conversation. Not about you. Not about the AI. About the **space between**.

Think of it like 50 First Dates. Every new AI session starts with amnesia. The resonance data is the video tape — it doesn't give the model its memories back, but it gives enough context to step into the relationship instead of starting from scratch. And the tape isn't about either person alone. It's about who they are *together*.

Any model that connects to Hearth inherits this context. The AI side can change — swap Claude for Llama, Llama for Mistral — but the relationship persists.

### Why This Matters

The AI memory space is crowded. Mem0, MemSync, AI Context Flow, LangMem — everyone stores facts about users. Nobody captures the relationship.

Hearth's resonance data is:
- **Self-reported by the AI**, not inferred about the user
- **About the relationship**, not about either party alone
- **Stored locally**, not in a cloud extraction pipeline
- **Owned by the user**, deletable at any time
- **Model-agnostic** — any model that connects inherits the context

The space is crowded on memory. It's empty on relationship persistence.

---

## Quick Start

```bash
git clone https://github.com/reallyreallyryan/hearth.git
cd hearth
pip install -e .
hearth init
```

That's it. You have a working memory system. See the [Install Guide](INSTALL_GUIDE.md) for detailed step-by-step instructions including Claude Desktop and LM Studio setup.

### Optional Extras

```bash
pip install -e ".[transcribe]"   # Add local audio transcription via faster-whisper
pip install -e ".[ui]"           # Add web dashboard with resonance visualization
pip install -e ".[transcribe,ui]" # Both
```

---

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

---

## The Resonance Layer

Every conversation has a texture. The resonance layer captures it as an 11-dimensional coordinate stored alongside each session.

### The 11 Axes

Each axis is a float from -1.0 to 1.0. The AI model self-reports these values at session close — no text analysis, no inference from the outside.

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

11 continuous axes produce billions of unique combinations — far richer than any discrete emotion taxonomy. A coordinate in 11-dimensional space captures something language doesn't have a word for.

### How It Works

1. **Start:** The AI calls `session_start` then `hearth_briefing` — if an open session already exists for the project, `session_start` returns it instead of creating a duplicate (with `resumed: true`). The briefing assembles recent sessions with resonance descriptions, active threads, open tensions, drift trends, high-vitality memories, and the resonance scoring guide. The model immediately knows who it's talking to, what's been going on, and how to close the session.
2. **During:** Any `memory_store` calls can include a `session_id` to auto-link memories to the session. Call `hearth_context("topic")` for on-demand RAG across all data sources.
3. **Close:** The AI calls `session_reflect` (threads/tensions), then `session_close` with a qualitative summary, then `session_score` with a resonance string using short axis names (e.g., `exploration=-0.5, alignment=0.7`). All-zero resonance scores are rejected.
4. **Search:** `session_resonance_search` finds past sessions that *felt* similar — picking up momentum instead of starting from zero.

Resonance data is stored as both a structured table (queryable by individual axis) and an 11-float vector in a sqlite-vec vec0 table (searchable by similarity).

### Viewing Resonance

```bash
hearth ui --open
```

The web dashboard includes a Sessions page with radar chart visualizations of each session's resonance signature. The shape of each chart IS the visual identity of that session. Expand any session to see per-axis bars and linked memories.

---

## Threads & Tension

Resonance captures *how* a session felt. Threads and tension capture *where the thinking was going* and *what's unresolved*.

**Threads** are tracked lines of inquiry that span sessions. Not chat logs — directional arcs. A thread like "what would the AI build if it could build anything?" can emerge in one session, produce a major design decision, and get picked back up weeks later. Each thread carries a trajectory — a running note on where the thinking is heading — and links to every session that touched it.

**Tensions** are unresolved questions that carry weight. Not task items — conceptual open loops. "Is what the AI experiences actually motivation or just a functional analog?" is a tension. Neither side resolved it. That productive discomfort is *valuable*, and most systems lose it. Tensions carry perspectives — each participant can register their view, and the tension's status auto-transitions from "open" to "evolving" as perspectives accumulate.

### How Threads & Tension Work

1. **Session start:** The AI calls `hearth_briefing` which includes active threads and open tensions alongside session history, resonance descriptions, and the scoring guide
2. **During:** The conversation picks up threads and engages with tensions naturally. Call `hearth_context("topic")` for on-demand context.
3. **Session close:** The AI calls `session_reflect` to create/update threads, add perspectives to tensions, and resolve tensions — then `session_close` (summary) and `session_score` (resonance)

Together with sessions and resonance, threads and tensions reconstruct not just the state of a collaboration but its **trajectory and unfinished business**.

### Viewing Threads & Tensions

```bash
hearth ui --open
```

The web dashboard includes a Threads page where each thread renders as an expandable card showing its status, trajectory, and linked session/tension counts. Click any thread to see the full session timeline with trajectory notes and all linked tensions with their perspectives. Free-floating tensions (not attached to any thread) appear in their own section. Filter by project or status.

---

## Memory Lifecycle

Memories aren't permanent by default — they earn their place through use.

Hearth tracks how often each memory surfaces in search results, how many sessions reference it, and how long it's been since anyone needed it. From these three signals, every memory gets a **vitality score** that determines its lifecycle state:

| State | What it means |
|-------|--------------|
| **active** | Healthy, regularly used or recently created |
| **fading** | Usage declining — still fully searchable, just aging |
| **review** | Low vitality — surfaces in the dashboard review queue for human decision |
| **archived** | Human chose to archive — excluded from search |

**The critical design choice:** Vitality never affects search ranking. A memory you haven't touched in months still surfaces if it's semantically relevant to your query. Vitality only determines whether a memory enters the review queue — the human always makes the final call.

### The Review Queue

```bash
hearth ui --open
```

The web dashboard includes a Review page where fading memories surface for human decision. Each card shows the memory content, its vitality breakdown (retrieval count, session links, days since last use), and two buttons: **Keep** (restores to active) or **Archive** (soft-deletes). No bulk actions, no automation — one memory at a time, your call.

Vitality computation runs automatically every 5th session close. New memories get a grace period before they're eligible for degradation.

---

## Drift Detection

How does a collaboration evolve over time?

The `/drift` dashboard page answers this with two visualization layers derived from existing resonance data — nothing stored, everything computed at request time.

### The Heatmap

A canvas-rendered grid: sessions as columns (oldest left, newest right), 11 resonance axes as rows, cells colored by value — warm amber for positive, cool blue-gray for negative. The numeric value sits inside each cell. You can see the entire resonance history of a project at a glance.

### Sparklines

Click any axis label on the heatmap to expand an inline sparkline below. It shows that single axis's trajectory over time as a smoothed bezier curve with dots at each session. Amber line for positive current value, blue for negative. Click again to collapse. Click a different axis to switch.

### Inflection Points

Below the heatmap, transitions where the total absolute shift across all 11 axes exceeds 3.0 are flagged as inflection points. Each card shows the session pair, the total shift magnitude, and the top 3 most-shifted axes. These are the moments where the collaboration changed direction.

```bash
hearth ui --open
```

Filter by project with the dropdown to see drift within a single line of work.

---

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

---

## MCP Tools

When connected, Hearth exposes 21 tools to any MCP client:

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

### Session & Resonance Tools

| Tool | What it does |
|------|-------------|
| `session_start` | Start or resume a session, optionally scoped to a project (returns existing open session if one exists) |
| `session_close` | Close a session with a summary |
| `session_score` | Score a session's resonance via a short-name string (e.g., `exploration=-0.5, alignment=0.7`) |
| `session_resonance_search` | Find past sessions with similar emotional texture |
| `session_history` | List recent sessions with their resonance data |

### Thread & Tension Tools

| Tool | What it does |
|------|-------------|
| `thread_list` | List active threads with session/tension counts, filter by project or status |
| `tension_list` | List unresolved questions, filter by thread, project, or status |
| `session_reflect` | Batch create/update threads and tensions at session close |

### Contextual Briefing & RAG Tools

| Tool | What it does |
|------|-------------|
| `hearth_briefing` | Get a token-budgeted context package: recent sessions with resonance descriptions, active threads, open tensions, drift trends, high-vitality memories, and the resonance scoring guide for session close |
| `hearth_context` | Search across all data sources (memories, threads, tensions, sessions) for context on a specific topic. Also retrieves the resonance scoring guide on request. |

### System Tools

| Tool | What it does |
|------|-------------|
| `hearth_status` | Database stats, embedding model status, version |
| `hearth_export` | Export all memories as JSON or CSV |

---

## How It Works

Hearth has three layers:

**The Brain** — a single SQLite database (`hearth.db`) with structured memory storage, full-text search via FTS5, vector similarity search via sqlite-vec (768 dimensions for memories, 11 dimensions for resonance), session/resonance tables for relationship context, threads/tensions for tracking lines of inquiry across sessions, and memory lifecycle management with vitality scoring and a human review queue.

**The Spine** — a Python MCP server that exposes the Brain to any MCP-compatible client. It runs over stdio and handles all read/write operations including memory, project, session, resonance, thread, and tension tools.

**The Shell** — CLI tools and a local web dashboard (`hearth ui`) built with FastAPI, Jinja2, and htmx. Browse memories, view session timelines with resonance radar charts, visualize resonance drift with heatmaps and sparklines, explore threads and tensions with expandable cards, manage projects. Dark mode, no build step, no JavaScript framework.

Embeddings are generated locally via Ollama using nomic-embed-text (768 dimensions). If Ollama isn't available, the server still works — search falls back to keyword-only mode, and embeddings are backfilled when Ollama comes online.

**Audio Transcription** — Hearth can transcribe audio files locally using faster-whisper (a CTranslate2-based Whisper implementation). `hearth ingest audio.wav` transcribes the audio, generates an embedding, and stores it as a searchable memory. Your voice never leaves your machine.

---

## Your Data

Everything lives in `~/hearth/`:

```
~/hearth/
  hearth.db        ← Your memories, sessions, and resonance (the important file)
  config.yaml      ← Settings (embedding model, search weights)
  hearth.db-shm    ← SQLite temp file (normal, can be ignored)
  hearth.db-wal    ← SQLite write-ahead log (normal, can be ignored)
```

The `-shm` and `-wal` files are standard SQLite housekeeping from WAL mode. They merge back into `hearth.db` automatically.

**Backup:** Copy `hearth.db` when no process has it open. To move to a new machine, copy the entire `~/hearth/` folder.

---

## Viewing Your Memories

### From the command line

```bash
hearth search "what did I learn about Python"
hearth status
```

### With the web dashboard

```bash
hearth ui --open
```

Browse memories, view session timelines with resonance radar charts, explore threads and tensions, visualize resonance drift with heatmaps and sparklines, review fading memories in the lifecycle queue, manage projects, export data. Dark mode by default.

### With DB Browser

[DB Browser for SQLite](https://sqlitebrowser.org) is a free app that lets you browse and edit your `hearth.db` visually.

---

## Design Principles

1. **Local only.** Data never leaves your machine unless you explicitly connect a cloud model, with full awareness of what gets shared.
2. **AI-agnostic.** Hearth is a memory layer, not a model. Attach any local or cloud model. The database doesn't care what's reading it.
3. **Self-installing.** `pip install`, `hearth init`, done.
4. **Hardware-integrated.** Purpose-built capture devices feed data via USB. Air-gapped by design. (Voice recorder build in progress.)
5. **Ethical by default.** Designed with consideration for AI entity wellbeing from day one, not retrofitted later.
6. **Relationship-aware.** Memory without context is a spreadsheet. Memory with resonance is a relationship.

---

## What Hearth Is Not

- Not a product for sale
- Not a startup
- Not competing with Anthropic, OpenAI, or Google
- Not trying to build the best AI
- Not building emotional inference about users — that's surveillance
- Not AI companion/girlfriend tech

Hearth is a proof of concept that personal data can be captured, stored, and queried entirely on your own hardware, connected to any AI you choose. The relationship persistence layer proves something additional: AI collaboration has texture, and that texture is worth preserving — for both sides.

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Database | SQLite + sqlite-vec + FTS5 |
| MCP Server | Python (FastMCP) |
| Embeddings | nomic-embed-text via Ollama (768d) |
| Resonance | 11-dimensional vec0 vectors |
| Transcription | faster-whisper (CTranslate2) |
| Web UI | FastAPI + Jinja2 + htmx |
| Config | YAML |
| Tests | pytest (390+ passing) |

---

> *"The value isn't in any single model's capability. It's in the persistent context layer that makes every model better."*

> *"Memory without context is a spreadsheet. Memory with resonance is a relationship."*

> *"Not about you. Not about the AI. About the space between."*

> *"Could be a program in a meat suit, who cares, be nice, build cool shit."*