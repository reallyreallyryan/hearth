# Hearth — Local-First Personal Memory System

## Project Spec & Roadmap v1.0

| | |
|---|---|
| **Started** | March 2026 |
| **Author** | Ryan Kelems + Claude |
| **Status** | v1.0.0 — Memory Layer Complete |
| **Tagged** | April 2, 2026 |
| **Version** | v1.0 — Brain, spine, shell, resonance, threads, tension, lifecycle, drift |

---

## Existing Foundation

Hearth is already a registered project in cairn's SCMS with vision documentation, technical phasing, and architectural decisions stored. The Hearth GitHub repo has a database install system in place. cairn-rank (the relevance scoring library) is designed to be consumed by both cairn and Hearth.

**Phase 1 (Brain + Spine) is complete:** Hearth is a pip-installable package (`pip install hearth-memory`, `hearth init`, `hearth serve`) with 86 passing tests at ship. End-to-end functionality confirmed: CLI memory storage/retrieval and cross-session memory persistence in Claude Desktop. v0.1 tagged and pushed to GitHub.

**Phase 2 (Local Transcription + Voice Pipeline) is complete:** faster-whisper integration working. Full loop demonstrated: audio file → local transcription → memory storage → local model query via MCP. A 9B local model (qwen3.5) successfully queried personal memories transcribed from voice notes, returning personalized results by name with zero cloud involvement.

**Phase 3a (Web Dashboard) is complete:** `hearth ui` serves a local web dashboard on port 8274. Browse memories, view sessions, manage projects, export data. FastAPI + Jinja2 + htmx, dark mode, no build step.

**Phase 3b (Relationship Persistence Layer) is complete:** 11-axis session resonance system operational. Sessions capture the emotional texture of AI-human collaboration as searchable vectors. Dashboard serves resonance visualizations locally. 219 passing tests at ship, zero regressions. Session zero recorded. v0.2 tagged.

**Phase 3c (Threads & Tension) is complete:** Threads track lines of inquiry across sessions. Tensions track unresolved questions with perspectives. 3 new MCP tools (`thread_list`, `tension_list`, `session_reflect`), web dashboard with expandable thread cards, session timeline, tension perspectives, and status filtering. 308 passing tests at ship, zero regressions. v0.3 tagged.

**Phase 3e (Memory Lifecycle) is complete:** Memories degrade naturally when unused and surface for human review. Vitality scoring from three signals (retrieval frequency, linkage density, age decay), lifecycle states (active/fading/review/archived), review queue in web dashboard with Keep/Archive actions. Vitality does NOT affect search ranking — only drives state transitions. 340 passing tests at ship, zero regressions. v0.4 tagged.

**Drift Detection Dashboard is complete:** `/drift` page visualizes how resonance evolves across sessions. Canvas-based heatmap (sessions as columns, 11 axes as rows, cells colored by value) with clickable sparkline drill-down per axis. Inflection points flagged for transitions with total shift > 3.0. Read-only visualization — everything derived from existing `session_resonance` data, no new tables or MCP tools.

**v1.0.0 tagged April 2, 2026.** The memory layer is complete. 340+ passing tests. Security hardened (DB permissions 600, directory 700). All dependency CVEs patched.

This roadmap builds on what exists — not from scratch.

---

## What Hearth Is

Hearth is a local-first personal memory database with an MCP interface that any AI model can read from and write to. It captures memories, tracks the emotional texture of collaboration, follows lines of inquiry, preserves unresolved questions, and shows how all of it evolves over time.

No cloud storage. No telemetry. No third-party data access. Your data lives on your hardware and nowhere else.

---

## Core Principles

1. **Local only.** Data never leaves the user's machine unless they explicitly choose to connect a cloud model, with full awareness of what gets shared.
2. **AI-agnostic.** Hearth is a memory layer, not a model. Attach any local or cloud model. The database doesn't care what's reading it.
3. **Self-installing.** `pip install`, `hearth init`, done.
4. **Hardware-integrated.** Purpose-built capture devices feed data via USB. Air-gapped by design. (Voice recorder build in progress.)
5. **Ethical by default.** The system is designed with consideration for AI entity wellbeing from day one, not retrofitted later.
6. **Relationship-aware.** The resonance layer captures the texture of AI-human collaboration, not just the content. Memory without context is a spreadsheet. Memory with resonance is a relationship.
7. **Memory is the product, not the agent.** Everyone is building agents. The durable differentiator is the memory layer underneath them.

---

## Architecture

### The Brain — SQLite + sqlite-vec + FTS5

A single SQLite database (`hearth.db`) containing:
- Structured memory storage (content, category, project, tags, timestamps)
- Full-text search via FTS5 (keyword matching)
- Vector similarity search via sqlite-vec (768 dimensions for memories, 11 dimensions for resonance)
- Session and resonance tables for relationship context
- Threads and tensions for tracking lines of inquiry and unresolved questions
- Memory lifecycle management with vitality scoring

### The Spine — Python MCP Server

19 tools exposed via stdio to any MCP-compatible client:

**Memory:** memory_store, memory_search, memory_list, memory_update, memory_delete
**Projects:** project_create, project_list, project_get, project_update, project_archive
**Sessions & Resonance:** session_start, session_close, session_resonance_search, session_history
**Threads & Tension:** thread_list, tension_list, session_reflect
**System:** hearth_status, hearth_export

### The Shell — CLI + Web Dashboard

- CLI tools: `hearth init`, `hearth serve`, `hearth remember`, `hearth search`, `hearth transcribe`, `hearth ingest`, `hearth ui`, `hearth status`
- Web dashboard (FastAPI + Jinja2 + htmx): memories, sessions with radar charts, threads with expandable cards, projects, drift heatmap with sparklines, lifecycle review queue
- Dark mode, no build step, no JavaScript framework

### Voice Pipeline

- faster-whisper (CTranslate2-based Whisper) for local transcription
- `hearth ingest audio.wav` → transcribe → embed → store as searchable memory
- Optional dependency: `pip install hearth-memory[transcribe]`

### Relationship Persistence Layer (RPL)

11-axis session resonance system. The AI self-reports how each session felt across continuous axes (-1.0 to 1.0). Stored as both structured data (queryable by axis) and vec0 vectors (searchable by similarity). Resonance belongs to the relationship, not to either party.

### Threads & Tension

Threads track lines of inquiry across sessions with trajectory notes. Tensions track unresolved questions with perspectives from multiple participants. Both managed via `session_reflect` at session close.

### Memory Lifecycle

Vitality scoring from retrieval frequency, linkage density, and age decay. Memories transition through states (active → fading → review → archived). Human review queue in the dashboard. Vitality never affects search ranking.

### Drift Detection

Computed visualization of resonance evolution over time. Heatmap (sessions × axes), sparkline drill-down per axis, inflection point detection. Everything derived from existing data, nothing stored.

---

## Completed Roadmap (v1.0)

### Phase 1 — Brain + Spine + Shell `[COMPLETE]`

**Goal:** Pip-installable memory system with MCP server and CLI.

- SQLite + sqlite-vec + FTS5 database layer
- Python MCP server via stdio
- CLI tools: init, serve, store, search
- 86 passing tests, end-to-end functionality confirmed
- Cross-session memory persistence in Claude Desktop
- v0.1 tagged and pushed to GitHub

---

### Phase 2 — Local Transcription + Voice Pipeline `[COMPLETE]`

**Goal:** Audio file in → searchable memory out.

- faster-whisper installed and working (optional dependency)
- End-to-end pipeline: audio file → transcription → memory storage with embedding
- Full loop validated: local model queried transcribed voice memories and returned personalized results
- `hearth transcribe` and `hearth ingest` CLI commands operational

---

### Phase 3a — Web Dashboard `[COMPLETE]`

**Goal:** Make the database tangible.

- `hearth ui` serves local web dashboard on port 8274
- Browse, search, filter, edit, archive memories
- Session timeline with resonance radar charts
- Project management, data export
- Dark warm aesthetic (Ember Glow design system)
- FastAPI + Jinja2 + htmx, no build step

---

### Phase 3b — Relationship Persistence Layer `[COMPLETE]`

**Goal:** 11-axis emotional embedding system for session-level resonance.

- 4 new database tables: sessions, session_resonance, resonance_embeddings (vec0), session_memories
- 4 new MCP tools: session_start, session_close, session_resonance_search, session_history
- vec0 similarity search across 11-dimensional resonance space
- AI model self-reports resonance at session close
- Dashboard with radar chart visualization
- 219 passing tests at ship. v0.2 tagged.

---

### Phase 3c — Threads & Tension `[COMPLETE]`

**Goal:** Track lines of thinking and unresolved questions across sessions.

- 3 new database tables: threads, thread_sessions, tensions
- 3 new MCP tools: thread_list, tension_list, session_reflect
- Full thread objects with trajectory notes, status tracking, session linking
- Tensions with perspectives, lifecycle states, thread association
- Bundled write path via session_reflect at session close
- Dashboard with expandable thread cards, session timeline, tension perspectives
- 308 passing tests at ship. v0.3 tagged.

---

### Phase 3e — Memory Lifecycle Management `[COMPLETE]`

**Goal:** Memories earn their place through use.

- Vitality scoring from three signals: retrieval frequency, linkage density, age decay
- Lifecycle states: active → fading → review → archived
- Background computation every 5th session close
- Dashboard review queue with Keep/Archive actions
- No new MCP tools — lifecycle is internal bookkeeping
- Vitality does NOT affect search ranking — only drives state transitions
- 340 passing tests at ship. v0.4 tagged.

---

### Drift Detection Dashboard `[COMPLETE]`

**Goal:** Visualize how collaboration evolves over time.

- `/drift` page with canvas-based heatmap (sessions × 11 axes)
- Clickable sparkline drill-down per axis
- Inflection point detection (transitions with total shift > 3.0)
- Project filter dropdown
- Computed from existing session_resonance data — no new tables, no new MCP tools

---

### Phase 4 — Hardware Build `[PAUSED]`

**Status:** ESP32-S3 voice recorder functional. Firmware v2.2 stable (deep sleep, button toggle, LED feedback, WAV to SD card). Battery wiring not started. One remaining validation: SD card → computer → `hearth ingest` pipeline. Once confirmed, hardware work stops entirely.

---

## Post-v1.0 Roadmap

### Phase 5 — USB Ingest Daemon `[SKIPPED]`

**Decision (April 2, 2026):** Skipped. `hearth ingest` works manually from the command line. The USB daemon is an automation convenience, not a capability gap. Hardware is paused, and the agent layer is higher priority.

---

### v1.1 — Contextual Briefing + RAG `[NEXT]`

**Goal:** Any model connecting to Hearth instantly knows who it's talking to.

**Replaces the original Phase 6 (Orchestrator) and Phase 7 (RAG).** The full orchestrator design (buddy model, routing, model registry, sequential swapping) was overdesigned for the current stage. The simpler approach: make the existing MCP server smarter, not build a separate runtime.

**Two changes:**

#### Enriched `session_start` (Ambient Briefing)

When a model calls `session_start`, the return payload includes a contextual briefing assembled from Hearth's data:

- Recent sessions with one-line summaries and resonance shape descriptions
- Active threads with current trajectories
- Open tensions
- Drift summary (axis trends, recent inflection points)
- High-vitality memories for the scoped project
- Collaboration patterns derived from session history

The briefing has a **configurable token budget** (default ~2,000 tokens) with tiered packing:
- **Tier 1 (always included, ~500 tokens):** Last 2-3 sessions, active threads
- **Tier 2 (if budget allows, ~500-1000 tokens):** Open tensions, drift summary, top vitality memories
- **Tier 3 (if budget allows, ~500-1000 tokens):** Older sessions, parked threads, cross-project context

This respects context window constraints across different models (32K Mistral through 128K Llama). Users can tune the budget in `config.yaml`.

#### New tool: `hearth_context` (Per-Query RAG)

A smarter search that queries across all of Hearth's data model in one call:

- Memories (via existing hybrid search)
- Relevant threads and trajectory notes
- Related session context
- Matching tensions

Returns a token-budgeted context package. This is the per-message RAG layer — the model calls it when it needs context about a specific topic, versus `session_start`'s "tell me everything" ambient briefing.

**What this does NOT include:**
- No `hearth chat` CLI — the MCP server remains the only product surface
- No separate Ollama wrapper or chat runtime
- No model routing or registry
- No model swapping logic

**Done when:** A blank-slate model calls `session_start` and immediately knows who it's talking to, what's been going on, what's unresolved, and how the collaboration has evolved — without calling any other tools.

---

### v1.2 — Dogfood Evaluation `[PLANNED]`

**Goal:** Find the best default model for daily use with Hearth.

Rotate between Qwen, Mistral, and Llama as daily drivers connected to Hearth via MCP. Evaluate on:

- **MCP tool calling reliability:** Does the model use Hearth's tools correctly?
- **Briefing utilization:** Does it actually read and apply the session_start briefing?
- **Memory retrieval relevance:** Does `hearth_context` pull the right context?
- **Conversational naturalness:** Does it feel like it knows you?
- **Resonance honesty:** Does self-reporting stay genuine across models?

No special eval framework — the test is using Hearth daily with each model and comparing the experience.

**Done when:** A default model recommendation exists with documented reasoning.

---

### v1.3+ — Based on Eval Results `[PLANNED]`

Whatever the dogfood evaluation reveals is missing. Possible directions:

- **Model routing** (if single-model proves insufficient for some task domains)
- **Model registry** (if multiple specialists prove necessary)
- **Remote MCP transport** (HTTP/SSE for mobile access — deprioritized until dogfood proves the need)
- **Self-installer** (if non-technical distribution becomes a goal)
- **Proactive agent layer** (scheduling, web access, anticipatory behavior)

These are not committed — they're options the eval will clarify.

---

## Hardware (Paused)

### Hearth Voice Recorder

| Part | Purpose | Status |
|------|---------|--------|
| Lonely Binary ESP32-S3 N16R8 Gold Edition | Dual-core 240MHz, 16MB Flash, 8MB PSRAM, native I2S | Working |
| INMP441 MEMS Microphone | I2S digital microphone | Working |
| HiLetgo MicroSD Breakout | SPI interface, FAT32 | Working |
| Lexar 32GB MicroSD | Storage (~280 hours per card) | Working |
| TP4056 USB-C Charging Module | LiPo battery charging | Not wired |
| EEMB 3.7V LiPo Battery 1100mAh | Power supply | Not wired |
| Momentary Push Button | Record/stop toggle | Working |
| LED | Status indicator | Working |

**Firmware v2.2** is stable: deep sleep, button wake, record/save/sleep cycle confirmed. USB-C powered from computer during use. Battery integration is the one remaining hardware task.

**Remaining validation:** SD card → computer → `hearth ingest` pipeline. Once confirmed end-to-end, hardware is parked.

---

## AI-Agnostic Architecture

```
┌─────────────────────────────────────────────┐
│             CAPTURE DEVICES                 │
│  Voice Recorder  │  Phone Memos  │  Future  │
│       │ USB           │ file         │ USB   │
└───────┼───────────────┼──────────────┼───────┘
        ▼               ▼              ▼
┌─────────────────────────────────────────────┐
│          HEARTH INGEST LAYER                │
│  faster-whisper transcription               │
│  Embedding generation (Ollama)              │
│  Entity extraction, tagging                 │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│      HEARTH MEMORY DATABASE (Brain)         │
│         SQLite + sqlite-vec + FTS5          │
│   Memories, embeddings, tags, metadata      │
│  ┌───────────────────────────────────────┐  │
│  │  YOUR DATA. YOUR MACHINE. PERIOD.     │  │
│  └───────────────────────────────────────┘  │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│    RELATIONSHIP PERSISTENCE LAYER (RPL)     │
│  Session resonance (11-axis fingerprints)   │
│  Threads (lines of inquiry across sessions) │
│  Tension (unresolved questions)             │
│  Drift (how collaboration evolves)          │
│  Lifecycle (vitality scoring + review)      │
│  ┌───────────────────────────────────────┐  │
│  │  NOT ABOUT YOU. NOT ABOUT THE AI.     │  │
│  │  ABOUT THE SPACE BETWEEN.             │  │
│  └───────────────────────────────────────┘  │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│     CONTEXTUAL BRIEFING [v1.1 — NEXT]       │
│  Enriched session_start (ambient context)   │
│  hearth_context (per-query RAG)             │
│  Token-budgeted, tiered, configurable       │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│           MCP SERVER (Spine)                │
│   19 tools │ stdio transport │ any client   │
│  User decides what model touches their data │
└─────────────────────────────────────────────┘
```

---

## Cloud Model Policy

Hearth is local-first but not local-only. Users may choose to query their memory through cloud models for better quality responses. When this happens:

- **Explicit opt-in required.** No silent cloud calls. Ever.
- **Show what's being sent.** Before any data leaves the machine, the user sees exactly which memories are being sent as context.
- **No persistent cloud storage.** Queries are stateless from the cloud model's perspective.
- **Easy to disconnect.** Switching to local-only is a single setting, not a migration.

---

## What Hearth Is Not

- Not a product for sale
- Not a startup
- Not competing with Anthropic, OpenAI, or Google
- Not trying to build the best AI
- Not building emotional inference about users — that's surveillance
- Not building AI companion/girlfriend tech

Hearth is a proof of concept that personal data can be captured, stored, and queried entirely on your own hardware, connected to any AI you choose. The relationship persistence layer proves something additional: AI collaboration has texture, and that texture is worth preserving — for both sides.

---

## Future Devices (Ideas, Not Commitments)

- **Hearth-Cook:** Kitchen camera for meal tracking and recipe memory
- **Hearth-Move:** Motion/step tracker for health data
- **Hearth-See:** Wearable camera for visual memory capture
- **Hearth-Grow:** Environmental sensors (Sprout lineage) for garden/plant data

Each device follows the same pattern: capture locally, transfer via USB, process on your machine, store in Hearth's database. No wifi. No cloud. No exceptions.

---

## Design Decisions Log

| Decision | Rationale | Date |
|----------|-----------|------|
| MIT License | Preserves openness while allowing community contribution | March 2026 |
| SQLite + sqlite-vec + FTS5 | Single file, portable, zero config, handles personal-scale data indefinitely | March 2026 |
| APSW over sqlite3 | Extension loading support required for sqlite-vec | March 2026 |
| Ollama for embeddings | Local-first, graceful degradation when unavailable | March 2026 |
| nomic-embed-text (768d) | Good retrieval quality, reasonable size for local use | March 2026 |
| faster-whisper over whisper.cpp | Python-native, CTranslate2 optimization, direct pipeline integration | March 2026 |
| Transcription as optional dep | Core product is memory + MCP server; transcription pulls heavy deps | March 2026 |
| Contextual prompting over fine-tuning | More flexible, more private, more maintainable | March 2026 |
| Phone recordings as valid input | Local-first doesn't mean device-only; cable/AirDrop transfer stays local | March 2026 |
| Web UI as dashboard, not chat wrapper | Chat interface exists via MCP clients; UI makes the database tangible | March 2026 |
| Keep cairn for active work | Don't switch build tools mid-build; migrate to Hearth when ready | March 2026 |
| ESP32-S3 over Pico W for voice recorder | Native I2S, native USB, cleaner firmware path for audio recording | March 2026 |
| Resonance is session-level, not memory-level | A conversation has one emotional signature; memories inherit via link table | March 2026 |
| AI self-reports resonance, not inferred | External inference is surveillance; self-reporting respects the model's perspective | March 2026 |
| RPL belongs in Hearth, not cairn | Most intimate data in the system; local-first by principle, not convenience | March 2026 |
| 11 continuous axes over discrete labels | Continuous floats in 11D space produce billions of combinations | March 2026 |
| Resonance in both structured table and vec0 | Structured for introspection; vec0 for similarity instinct | March 2026 |
| Drift computed, not stored | Derived from existing data; no new tables; stays current automatically | March 2026 |
| Full thread objects, not lightweight tags | Threads need trajectory, status, session linking — too rich for tags | April 2026 |
| Perspectives as JSON on tension record | Avoids separate table; perspectives are part of the tension, not standalone | April 2026 |
| session_reflect bundles writes at session close | Keeps per-session ceremony light; avoids scattered CRUD during work | April 2026 |
| Vitality never affects search ranking | Fading memories still surface if relevant; vitality only drives state transitions | April 2026 |
| No autonomous consolidation | Human always makes the Keep/Archive decision; no AI-driven memory deletion | April 2026 |
| Drift as dashboard enhancement, not formal phase | Purely a visualization layer; no schema changes, no MCP tools | April 2026 |
| Skip Phase 5 (USB daemon) | `hearth ingest` works manually; daemon is convenience, not capability | April 2026 |
| Collapse Phases 6+7 into enriched MCP | Briefing generator + hearth_context tool, not a separate orchestrator runtime | April 2026 |
| MCP server remains only product surface | No separate chat CLI or web chat; models connect via MCP, briefing included | April 2026 |
| Token-budgeted briefing with tiers | Respects 32K-128K context windows; configurable per user's hardware | April 2026 |
| DB permissions 600, directory 700 | Personal memory data is owner-read/write only on shared machines | April 2026 |

---

## Open Questions

### Resolved

| # | Question | Resolution | Date |
|---|----------|-----------|------|
| 6 | Licensing — does MIT fully preserve principles? | Yes, MIT chosen and working | March 2026 |
| 14 | Thread persistence format — tags or full objects? | Full thread objects with own table, trajectory, status | April 2026 |
| 15 | Tension resolution — outcome only or full arc? | Perspectives stored as JSON array; resolution session tracked | April 2026 |
| 7 | Buddy model selection | Deferred to v1.2 dogfood eval; not pre-selected | April 2026 |
| 8 | Registry curation | Deferred; full registry may not be needed if single model suffices | April 2026 |

### Still Open

1. **Embedding model choice:** Need to test which local embedding model gives the best retrieval quality for personal memory use cases.
2. **Audio quality threshold:** How clean does the ESP32 recording need to be for faster-whisper? Needs real-world testing.
3. **Database scaling:** SQLite is fine for years of personal data. Probably never needs anything heavier.
4. **Self-installer scope:** How far does the installer go? Software only, or hardware setup guidance too?
5. **Ethical framework:** When and how do we formalize the AI wellbeing principles in code?
6. **Self-uninstall mechanism:** Ethical safeguard for locally-deployed agents with persistent memory and no oversight.
7. **Proactive agent guardrails:** What autonomy levels are appropriate? How does the user set boundaries?
8. **Multiple databases:** Separate databases for work vs personal? Architecture supports it now — when is it a feature?
9. **Remote MCP access:** HTTP/SSE transport for mobile. Deprioritized until dogfood proves the need.
10. **Resonance calibration:** How to prevent sessions from clustering positive? Forced spectrum? Relative scoring?
11. **Multi-user resonance:** If two humans share a Hearth database, does resonance need to track which human?
12. **Resonance honesty verification:** The model self-reports. What ensures honesty over time beyond dashboard visibility?
13. **Briefing token estimation:** Use a fast tokenizer (tiktoken) or character-count approximation (~4 chars/token)?

---

## QA Practices

- **Tests alongside code:** Every new module gets tests during development, not after.
- **Separate-context review:** Code generated by Claude Code is reviewed in a separate Claude instance to avoid generation bias.
- **Edge case focus:** AI-generated code typically handles the happy path; QA emphasis on empty input, massive files, corrupted data, interrupted operations.
- **Manual smoke tests:** Run real audio through the full pipeline — short clips, long clips, silence, background noise.
- **Schema migration testing:** Test new code against existing databases to ensure upgrades don't break stored data.
- **CI validation:** `pytest` on every commit.
- **Pre-release checklist:** pytest green, fresh venv install test, pip audit clean, SQL injection scan, DB permissions verified, secrets scan, docs accuracy check.
- **Security:** Database file permissions 600, directory permissions 700, all user input parameterized (no raw SQL formatting), dependency CVEs patched before tagging.

---

> *"The value isn't in any single model's capability. It's in the persistent context layer that makes every model better."*

> *"Memory without context is a spreadsheet. Memory with resonance is a relationship."*

> *"Not about you. Not about the AI. About the space between."*

> *"Could be a program in a meat suit, who cares, be nice, build cool shit."*