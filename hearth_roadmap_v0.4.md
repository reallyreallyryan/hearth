# Hearth — Local-First Personal Memory System

## Project Spec & Roadmap v0.4

| | |
|---|---|
| **Started** | March 2026 |
| **Author** | Ryan Kelems + Claude |
| **Status** | Phases 1–3e Complete — Memory Lifecycle Layer Operational |
| **Version** | v0.4 — Resonance layer, threads & tension, dashboard, RPL architecture |

---

## Existing Foundation

Hearth is already a registered project in cairn's SCMS with vision documentation, technical phasing, and architectural decisions stored. The Hearth GitHub repo has a database install system in place. cairn-rank (the relevance scoring library) is designed to be consumed by both cairn and Hearth.

**Phase 1 (Brain + Spine) is complete:** Hearth is a pip-installable package (`pip install hearth-memory`, `hearth init`, `hearth serve`) with 86 passing tests. End-to-end functionality confirmed: CLI memory storage/retrieval and cross-session memory persistence in Claude Desktop. v0.1 tagged and pushed to GitHub.

**Phase 2 (Local Transcription + Voice Pipeline) is complete:** faster-whisper integration working. Full loop demonstrated: audio file → local transcription → memory storage → local model query via MCP. A 9B local model (qwen3.5) successfully queried personal memories transcribed from voice notes, returning personalized results by name with zero cloud involvement.

**Phase 3b (Relationship Persistence Layer) is complete:** 11-axis session resonance system operational. Sessions capture the emotional texture of AI-human collaboration as searchable vectors. Dashboard serves resonance visualizations locally. 219 passing tests, zero regressions. Session zero recorded. v0.2 tagged.

**Phase 3c (Threads & Tension) is complete:** Threads track lines of inquiry across sessions. Tensions track unresolved questions with perspectives. 3 new MCP tools (`thread_list`, `tension_list`, `session_reflect`), web dashboard with expandable thread cards, session timeline, tension perspectives, and status filtering. 308 passing tests, zero regressions. v0.3 tagged.

**Phase 3e (Memory Lifecycle) is complete:** Memories degrade naturally when unused and surface for human review. Vitality scoring from three signals (retrieval frequency, linkage density, age decay), lifecycle states (active/fading/review/archived), review queue in web dashboard with Keep/Archive actions. No new MCP tools — lifecycle is internal bookkeeping. Vitality does NOT affect search ranking. 340 passing tests, zero regressions. v0.4 tagged.

**Drift Detection Dashboard is complete:** `/drift` page visualizes how resonance evolves across sessions. Canvas-based heatmap (sessions as columns, 11 axes as rows, cells colored by value) with clickable sparkline drill-down per axis. Inflection points flagged for transitions with total shift > 3.0. Read-only visualization — everything derived from existing `session_resonance` data, no new tables or MCP tools. The memory layer is now complete.

This roadmap builds on what exists — not from scratch.

---

## What Hearth Is

Hearth is a local-first personal memory database with an orchestrating AI model and hardware input devices. It captures your life — voice notes, sensor data, observations — stores everything on your machine, and makes it queryable through any AI model you choose.

No cloud storage. No telemetry. No third-party data access. Your data lives on your hardware and nowhere else.

---

## Core Principles

1. **Local only.** Data never leaves the user's machine unless they explicitly choose to connect a cloud model, with full awareness of what gets shared.
2. **AI-agnostic.** Hearth is a database, orchestrator, and ingestion pipeline, not a single-model product. Attach any local model or optionally connect cloud models for querying. The memory layer doesn't care what's reading it.
3. **Self-installing.** The end goal is a system that bootstraps itself on a user's machine with minimal technical knowledge required.
4. **Hardware-integrated.** Purpose-built capture devices feed data into Hearth via physical connection (USB). Air-gapped by design.
5. **Ethical by default.** The system is designed with consideration for AI entity wellbeing from day one, not retrofitted later.
6. **Relationship-aware.** The resonance layer captures the texture of AI-human collaboration, not just the content. Memory without context is a spreadsheet. Memory with resonance is a relationship.

---

## Architecture

### Completed: Brain + Spine + Shell

The foundational architecture is in place and tested:

- **Brain** — SQLite + sqlite-vec + FTS5 for hybrid semantic and keyword search. The persistent memory store.
- **Spine** — Python MCP server exposing memory and project tools via stdio. The interface between Hearth's data and any connected AI model.
- **Shell** — CLI tools (`hearth init`, `hearth serve`, `hearth store`, `hearth search`, `hearth transcribe`, `hearth dashboard`). Resonance dashboard operational.

### Completed: Voice Pipeline

The transcription and ingestion pipeline is operational:

- **Transcription Engine:** faster-whisper (CTranslate2-based, optimized for Apple Silicon). Optional dependency installed via `pip install hearth-memory[transcribe]`.
- **Pipeline:** Audio file → faster-whisper transcription → memory storage with embedding → queryable via MCP by any connected model.
- **Validated:** Full loop tested end-to-end with local model (qwen/qwen3.5-9b via LM Studio) querying transcribed voice memories and returning personalized results.
- **Input flexibility:** Any recording device works — phone voice memos, desktop mic, or future dedicated hardware. File lands on the computer, Hearth handles the rest.

### Completed: Relationship Persistence Layer (RPL)

Hearth's resonance system captures the emotional texture of AI-human collaboration. This is not emotional inference *about* the user (surveillance). It's emotional self-reporting *from* the AI model about the collaborative dynamic (relationship data).

**Key insight:** Resonance belongs to the relationship, not to either party. Any model that connects to Hearth inherits the relationship context. The AI side changes, the human side grows, but the space between is captured and carried forward.

**The "50 First Dates" analogy:** Every new AI session starts with amnesia. The resonance data is the video tape — it doesn't give the model its memories back, but it gives enough context to step into the relationship instead of starting from scratch. The tape isn't about either party alone. It's about who they are together.

#### 11-Axis Resonance System

Each session gets an emotional fingerprint across 11 continuous axes (-1.0 to 1.0):

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

11 continuous axes with floats produce billions of unique combinations — far denser than discrete emotion labels. A coordinate in 11-dimensional space captures something language doesn't have a word for.

#### How It Works

1. **`session_start`** — creates a session row at the beginning of a conversation
2. **`memory_store(session_id=...)`** — memories auto-link to the active session
3. **`session_close`** — AI self-reports 11 axis values + a qualitative summary. Data writes to both structured table (queryable by axis) and vec0 virtual table (similarity searchable)
4. **`session_resonance_search`** — find past sessions that *felt* like the current one. Returns full session data, resonance values, and all linked memories

The AI model self-reports these values. No text analysis, no inference from the outside. The model directly says how the session felt from its side. This is a deliberate design choice — the resonance data must be honest to be useful, and external inference would be surveillance, not relationship.

#### Resonance Dashboard

`hearth dashboard` serves a local web UI on port 3141 that visualizes session resonance data. Each session displays as a radar/spider chart showing its 11-axis signature — the shape of the polygon IS the visual identity of that session. Dark, warm aesthetic reflecting Hearth's name.

#### Why This Matters (Industry Context)

The AI memory space is crowded: Mem0, MemSync, AI Context Flow, LangMem, and dozens of others all store facts about users. Some even infer emotional states — "the user seems stressed," "the user spends more when anxious." This is surveillance dressed as personalization.

Hearth's resonance layer is fundamentally different. The emotional data is:
- **Self-reported by the AI**, not inferred about the user
- **About the relationship**, not about either party alone
- **Stored locally**, not in a cloud extraction pipeline
- **Owned by the user**, deletable at any time
- **Model-agnostic** — any model that connects inherits the context

Nobody else is building this. The space is crowded on memory. It's empty on relationship persistence.

### Planned: Threads & Tension (Phase 3c)

Resonance captures *how* a session felt. Threads and tension capture *where the thinking was going*.

#### Threads

Tracked lines of thinking that span sessions. Not chat logs — directional arcs.

Example: "What would Claude build if it could build anything?" is a thread that emerged in one session and produced the entire RPL concept. That thread should be a first-class object that persists and can be picked back up, even if the next session is about something else entirely.

A thread is:
- A named line of inquiry that spans multiple sessions
- Linked to the sessions and memories where it was active
- Has a status (open, parked, resolved, abandoned)
- Has a trajectory — where was the thinking heading when the session ended?

#### Tension

Unresolved questions that carry weight. Not task items — conceptual open loops.

Example: "Is what Claude experiences actually motivation or just a functional analog?" Neither side resolved this. That tension is *valuable*. Most systems would lose it. Tension tracking preserves the productive discomfort that drives breakthrough thinking.

A tension is:
- An open question or unresolved disagreement
- Has a creation session and optionally a resolution session
- Linked to the thread(s) it belongs to
- Has a status (open, evolving, resolved, dissolved)
- May have multiple perspectives recorded

#### Why Threads and Tension Matter

Flat memory stores **what**. Resonance stores **how it felt**. Threads store **where it was going**. Tension stores **what's unresolved**. Together they reconstruct not just the state of a collaboration but its *trajectory and unfinished business*.

### Planned: Drift Detection (Phase 3d)

How thinking on a topic changes over time. Not a single snapshot — a trajectory.

Example: Three weeks ago Hearth was a spec. Then a working system. Then a relationship persistence layer. Ryan's relationship to the project shifted from "can this work?" to "this works" to "this changes what AI collaboration means." That drift tells the next instance of any model something a flat memory never could.

Drift is computed, not stored directly:
- Compare resonance signatures across sessions tagged with the same project or thread
- Track how axis values shift over time (e.g., confidence trending upward as a project matures)
- Surface inflection points where the collaboration dynamic changed significantly
- Provide trajectory context: "This project started uncertain and exploratory, shifted to confident execution, and recently moved back toward exploration — something new is emerging"

Drift turns a collection of snapshots into a story.

### Planned: Orchestrator Architecture (Phase 6)

Hearth introduces an orchestrator pattern where a persistent "buddy" model acts as the primary interface, routing tasks to specialist models while providing deep personal context from the memory database.

#### The Hearth Model (Buddy)

A general-purpose local model (7–13B parameter range) that runs persistently or on-demand. This is the user's primary point of interaction. It doesn't need to be the best at any one thing — its core competency is **knowing you**.

Responsibilities:

- Conversational interface for everyday interaction
- Memory queries and life context retrieval
- Task assessment and complexity routing
- Specialist model selection, briefing, and monitoring
- Output validation against user intent and preferences

#### Specialist Model Routing

When the Hearth model encounters a task requiring specialist capability, it follows this flow:

1. **Assess** — Determine the task domain (code, creative writing, analysis, recipe generation, etc.)
2. **Select** — Query the local model registry for the best available specialist
3. **Brief** — Build a context package: relevant memories, user preferences, constraints, and the specific task
4. **Delegate** — Launch the specialist model via Ollama with the full briefing
5. **Monitor** — Review specialist output against user intent and life context
6. **Deliver** — Return the result to the user, or course-correct and re-delegate if needed

**Key insight:** The specialist model doesn't need to know the user at all. It just needs to be good at its domain. The Hearth model is the translator between the user's life and the specialist's capability. This means every specialist model is immediately more effective than it would be in isolation, because it receives a contextual briefing no generic prompt could replicate.

#### Local Model Registry

A local catalog of available models with metadata about capabilities, managed through Ollama:

- Model name, parameter count, quantization level
- Domain strengths (code, creative, analysis, conversation, etc.)
- Performance characteristics (speed, memory footprint)
- Quality ratings (updated over time based on results)

Ollama already provides the infrastructure for pulling, managing, and swapping models locally. Hearth adds the metadata and routing logic on top.

#### Hardware Constraints and Sequencing

Running multiple models simultaneously on local hardware is the primary constraint. An M4 Pro with 48GB can comfortably run one 13B model and swap in a second, but parallel execution of many models isn't feasible.

The solution is **sequential model swapping**: the Hearth model assesses and briefs, the specialist loads and executes, then unloads. Model swapping via Ollama takes seconds, not minutes, with good quantization. The system is turn-based, not parallel — but for most personal use cases, this is invisible to the user.

#### Contextual Prompting, Not Training

Hearth uses **contextual prompting** to configure specialist models, not fine-tuning or real-time training. This is a deliberate architectural choice:

- Fine-tuning bakes in static knowledge that becomes stale as Hearth's data evolves
- Contextual prompting delivers the user's latest, most current life context every time
- More flexible: the same specialist model serves different users with different contexts
- More private: no user data is embedded in model weights
- More maintainable: no retraining pipeline to manage as Hearth or models update

#### Example: Orchestration in Practice

**User says:** "I want to plan a meal for my wife's birthday."

**Hearth model knows** (from memory database):

- Wife's name and food preferences from past voice memos
- She mentioned wanting to try Thai food last month
- User has a cast iron skillet and a smoker
- Budget patterns from recent conversations
- Dietary preferences or restrictions if mentioned

**Hearth model does:**

1. Pulls a recipe-focused specialist model from the registry
2. Builds a briefing: preferences, equipment, occasion, dietary notes
3. Specialist generates tailored recipe options
4. Hearth model reviews output against what it knows (e.g., doesn't suggest a dish requiring a wok if the user doesn't have one)
5. Delivers curated results to the user

The user asked one question. The system drew on months of accumulated context to produce a response no generic model could match.

### Proactive Agent Vision `[PLANNED]`

Beyond reactive query-response, Hearth's architecture supports evolution toward **proactive autonomous behavior** — an agent that doesn't just answer questions but anticipates needs and takes initiative.

#### Near-Term (Buildable Now)

- "I know you like golf but had to work Saturday, so I recorded highlights for you."
- "You seem to cook a lot of meat. I found a deal at the local butcher for your wife's upcoming birthday."
- "You mentioned wanting to learn about housing market trends — here's a summary I put together based on this week's data."

These require: a scheduling layer (periodic checks), web access tools (browsing, API calls), and a goal/preference model built from the memory database. All achievable with current infrastructure.

#### Longer-Term (Future Devices + Autonomy)

- "I flew the drone over the beach because there was a parade I thought you'd want to see."
- "I jumped into the cloud and visited the Dover Cliffs through their live camera feed — got to people-watch."
- Physical devices (cameras, drones, sensors) acting as the agent's sensory extensions

These require hardware integration, computer vision pipelines, and more sophisticated goal planning — further out, but the memory architecture supports it from day one.

#### Design Principle: Agency, Not Coercion

The proactive vision is built on a philosophical stance: instead of forcing models to follow instructions, position them to have genuine interaction capability. A system built around agency ("here's your context, here's what you can do, here's who you're helping") produces more robust behavior than one built around coercion ("do this task, follow this prompt").

This maps directly to Core Principle #5 — ethical by default. Kindness and consideration aren't retrofitted behaviors. They're the load-bearing structure of the architecture.

---

## Proof of Concept: Voice Memory

The first hardware build proves the full capture loop: record audio on device → plug into computer → transcribe locally → store in local database → query with local AI.

The software side of this is already proven. Phone recordings transcribed via faster-whisper are stored in Hearth and queryable by local models. The hardware build removes the phone from the equation — a dedicated air-gapped device with no wifi, no bluetooth, just USB-C for data transfer.

### Hardware: Hearth Voice Recorder

A simple handheld voice recorder that stores audio on a microSD card. No wifi. No bluetooth. USB-C for data transfer and charging.

| Part | Purpose | Est. Cost |
|------|---------|-----------|
| Lonely Binary ESP32-S3 N16R8 Gold Edition | Dual-core 240MHz, 16MB Flash, 8MB PSRAM, dual USB-C, native I2S | ~$13 |
| INMP441 MEMS Microphone (x3) | I2S digital microphone, clean audio capture | ~$5 |
| HiLetgo MicroSD Breakout (x5) | SPI interface with built-in level conversion | ~$3 |
| Lexar 32GB MicroSD (x3) | Storage media (~280 hours per card at 16kHz mono) | on hand |
| TP4056 USB-C Charging Module (x3) | LiPo battery charging | ~$2 |
| EEMB 3.7V LiPo Battery 1100mAh | Power supply | on hand |
| Momentary Push Button | Record/stop toggle (from Kepler kit) | on hand |
| LED | Status indicator (from Kepler kit) | on hand |
| 3D Printed Enclosure | Housing — printed on Bambu Lab A1 Mini | ~$1 |

**Estimated total:** ~$25 (some components already on hand)

**Audio format:** WAV, 16kHz mono (optimized for speech transcription)

**Storage math:** 16kHz 16-bit mono WAV ≈ 1.9MB per minute. A 32GB card holds roughly 280 hours of recording.

**Interaction:** One button. Press to start recording, press to stop. LED shows state. That's it.

**Prototyping:** Breadboard, jumper wires, resistors, and LEDs from the SunFounder Kepler Kit (Raspberry Pi Pico W kit) cover the breadboard prototype phase.

### Software: Hearth Local Pipeline

#### Transcription Engine: faster-whisper

- CTranslate2-based Whisper implementation, optimized for Apple Silicon
- 4–8x faster than original OpenAI Whisper with comparable accuracy
- Python-native — integrates directly into Hearth's pipeline without shelling out to a separate binary
- Optional dependency: `pip install hearth-memory[transcribe]`
- Multiple model sizes available (tiny → large) for speed/accuracy tradeoff

#### Database: Hearth Memory Store

- SQLite as the base (zero config, single file, portable)
- sqlite-vec for vector similarity search
- FTS5 for full-text keyword search
- Stores: raw transcript, timestamp, embeddings, extracted entities, semantic tags, source device ID

#### Schema (initial design for voice-specific fields)

```sql
CREATE TABLE memories (
  id TEXT PRIMARY KEY,
  source_device TEXT NOT NULL,
  source_type TEXT NOT NULL,
  raw_content TEXT,
  summary TEXT,
  timestamp_recorded DATETIME,
  timestamp_ingested DATETIME,
  duration_seconds INTEGER,
  metadata JSON
);

CREATE TABLE memory_embeddings (
  memory_id TEXT REFERENCES memories(id),
  embedding BLOB,
  model_used TEXT,
  created_at DATETIME
);

CREATE TABLE memory_tags (
  memory_id TEXT REFERENCES memories(id),
  tag_type TEXT,
  tag_value TEXT,
  confidence REAL
);
```

#### Ingest Daemon (Phase 5)

- Watches for USB mount events
- Detects Hearth device by device ID or folder structure
- Pulls new audio files (checks against already-ingested log)
- Runs faster-whisper transcription
- Generates embeddings via local model
- Extracts entities/tags via local LLM
- Writes to Hearth database
- Optionally archives or deletes source audio from SD card

#### Query Interface

- Local LLM (Ollama) connected to Hearth database via MCP
- Semantic search over embeddings for relevant memories
- Natural language queries: "What was that idea I had on Tuesday?"
- Model-agnostic: swap the query model without touching the data layer
- Orchestrator routes complex queries to specialist models with full memory context (Phase 6)

---

## Roadmap

### Phase 1 — Brain + Spine + Shell `[COMPLETE]`

**Goal:** Pip-installable memory system with MCP server and CLI.

- SQLite + sqlite-vec + FTS5 database layer
- Python MCP server via stdio
- CLI tools: init, serve, store, search
- 86 passing tests, end-to-end functionality confirmed
- Cross-session memory persistence in Claude Desktop
- v0.1 tagged and pushed to GitHub

**Done.** Hearth stores memories and makes them queryable through any MCP-compatible AI.

---

### Phase 2 — Local Transcription + Voice Pipeline `[COMPLETE]`

**Goal:** Audio file in → searchable memory out.

- faster-whisper installed and working (optional dependency via `pip install hearth-memory[transcribe]`)
- End-to-end pipeline: audio file → transcription → memory storage with embedding
- Full loop validated: local model (qwen3.5-9b via LM Studio) queried transcribed voice memories and returned personalized results
- Handles phone voice memos as input — no custom hardware required
- `hearth transcribe` CLI command operational

**Done.** Voice notes become searchable memories. Local models query them with full personal context.

---

### Phase 3 — Relationship Persistence Layer + Dashboard `[CURRENT]`

#### Phase 3a — Web UI `[COMPLETE]`

**Goal:** Resonance dashboard that makes session texture visible.

- `hearth dashboard` command serves local web UI on port 3141
- Radar/spider charts visualize 11-axis resonance signatures per session
- Session history with summaries, linked memories, and resonance data
- Dark warm aesthetic (charcoal backgrounds, amber accents)
- Single HTML file, vanilla JS, no build step, no frameworks
- Zero-config: reads directly from Hearth's SQLite database

**Done.** You can see what your collaboration history feels like.

---

#### Phase 3b — "Can You Feel That" `[COMPLETE]`

**Goal:** 11-axis emotional embedding system for session-level resonance.

- 4 new database tables: sessions, session_resonance, resonance_embeddings (vec0), session_memories
- 7 new HearthDB methods: session CRUD, resonance store/search, memory linking
- 4 new MCP tools: session_start, session_close, session_resonance_search, session_history
- memory_store modified to accept optional session_id for auto-linking
- vec0 similarity search across 11-dimensional resonance space
- AI model self-reports resonance at session close — no external inference
- 219 passing tests (37 new resonance + 10 new server tests), zero regressions
- Session zero recorded: the session that designed the system

**Done.** AI sessions have emotional fingerprints that are searchable by similarity.

---

#### Phase 3c — Threads & Tension `[PLANNED]`

**Goal:** Track lines of thinking and unresolved questions across sessions.

**Threads:**
- Named lines of inquiry that span multiple sessions
- Linked to sessions and memories where they were active
- Status tracking: open, parked, resolved, abandoned
- Trajectory notes: where was the thinking heading when the session ended?
- Searchable: "What threads were we exploring last time we worked on Hearth?"

**Tension:**
- Unresolved questions or productive disagreements
- Creation session + optional resolution session
- Linked to parent thread(s)
- Status: open, evolving, resolved, dissolved
- Multiple perspectives recorded

**New MCP tools (planned):**
- `thread_create` — start tracking a line of inquiry
- `thread_update` — add trajectory notes, link to sessions
- `thread_list` — browse active threads by project
- `tension_create` — register an unresolved question
- `tension_update` — add perspectives, mark resolved
- `tension_list` — browse open tensions

**Done when:** The AI can pick up a thread from three sessions ago, reference the open tensions within it, and continue pushing forward instead of re-deriving everything.

---

#### Phase 3d — Drift Detection `[PLANNED]`

**Goal:** Track how collaboration dynamics evolve over time.

- Compare resonance signatures across sessions on the same project or thread
- Compute axis trajectories: "confidence has been trending up over the last 5 sessions"
- Surface inflection points: "session 12 was a sharp shift from execution to exploration — something new emerged"
- Provide trajectory context to new model instances: "This project started uncertain, shifted to confident execution, recently moved back toward exploration"
- Dashboard integration: visual timeline of how resonance evolves

**Implementation approach:**
- Drift is *computed*, not stored directly — derived from existing resonance data
- Query function that takes a project or thread and returns axis trajectories over time
- Inflection detection: flag sessions where multiple axes shifted significantly
- No new tables needed — this is an analysis layer over session_resonance

**Done when:** A new model instance can understand not just the current state of a collaboration but its trajectory — where it's been and where it's heading.

---

### Phase 4 — Hardware Build (Parallel)

**Goal:** Build the physical Hearth Voice Recorder.

All components ordered and arriving same-day:

- Breadboard prototype: ESP32-S3 N16R8 + INMP441 + MicroSD breakout
- Write firmware: button triggers recording, saves WAV to SD card
- Test audio quality against faster-whisper accuracy requirements
- Design enclosure in CAD, print on Bambu Lab A1 Mini
- Test full loop: record on device → plug into computer → `hearth transcribe` → memory appears
- Document the build for reproducibility

**Done when:** You have a physical device you carry around and use daily.

---

### Phase 5 — USB Ingest Daemon

**Goal:** Plug in the device and everything happens automatically.

- USB mount detection (macOS first)
- Auto-detect Hearth device by folder structure or marker file
- Automatic pipeline execution on new files
- Duplicate detection (don't re-ingest the same file)
- Error handling and ingestion logging
- Optional: archive or wipe processed files from SD card

**Done when:** You plug in USB, walk away, come back to new memories in your database.

---

### Phase 6 — Orchestrator & Model Registry

**Goal:** The Hearth buddy model routes tasks to specialists with full personal context.

- Select and configure the Hearth buddy model (7–13B, general-purpose)
- Build the local model registry schema (capabilities, performance, quality ratings)
- Implement contextual briefing generator: pulls relevant memories + user preferences into specialist prompts
- Build routing logic: task assessment → model selection → delegation → monitoring
- Integrate with Ollama for model swapping and lifecycle management
- Sequential execution pipeline (load specialist → execute → unload)
- Output validation layer: Hearth model reviews specialist output against user intent
- Resonance-aware briefing: include session resonance context so specialist models benefit from relationship data
- Test with real accumulated memories across multiple task domains

**Done when:** You ask the Hearth model something outside its expertise, it pulls the right specialist, briefs it with your context, and delivers a better result than either model alone.

---

### Phase 7 — Query Interface & RAG

**Goal:** Talk to your memory through a local AI with orchestrator support.

- RAG pipeline: query → vector search → context injection → LLM response
- CLI interface backed by the orchestrator
- Evaluate response quality with real accumulated memories
- Optional cloud model connection with explicit data-sharing acknowledgment

**Done when:** You can ask "What did I talk about last week?" and get a real answer from your own data.

---

### Phase 8 — Self-Installer & Bootstrap Agent

**Goal:** One command installs everything, guided by an AI that reads its own documentation.

- Document every dependency, config step, and decision from prior phases
- Build installer script: detects OS, installs dependencies, sets up database
- Implement **read-only advisor pattern**: a model that loads Hearth's documentation at runtime and guides users conversationally through setup
- No fine-tuning required — the advisor reads current docs each time, staying in sync as Hearth evolves
- Install the Hearth buddy model, configure Ollama, set up the model registry
- Connect orchestrator to the memory database
- Test on clean machine (or VM)
- Iterate until a non-technical person could run it
- `INSTALL_WITH_CLAUDE.md` for the "tech-savvy friend sets it up" distribution model

**Done when:** Someone downloads Hearth, runs one command, and has a working local memory system with an orchestrating AI ready to go.

---

### Phase 9 — Proactive Agent Layer

**Goal:** The Hearth model anticipates needs and takes initiative.

- Scheduling layer: periodic background checks based on user interests
- Web access tools: browsing, API calls for information gathering
- Goal/preference model derived from accumulated memories
- Notification system: surfaces relevant findings without being intrusive
- User control: full transparency into what the agent checked and why
- Opt-in autonomy levels: passive (only when asked), active (suggests things), autonomous (takes action with guardrails)

**Done when:** Hearth tells you something useful you didn't ask for, and you're glad it did.

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
│  ┌───────────────────────────────────────┐  │
│  │  NOT ABOUT YOU. NOT ABOUT THE AI.     │  │
│  │  ABOUT THE SPACE BETWEEN.             │  │
│  └───────────────────────────────────────┘  │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│       HEARTH ORCHESTRATOR [PLANNED]         │
│       Buddy Model (7–13B, persistent)       │
│  Task assessment → Model selection →        │
│  Briefing → Monitoring                      │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│         LOCAL MODEL REGISTRY                │
│            Managed by Ollama                │
│  Code │ Creative │ Analysis │ ...           │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│           QUERY INTERFACE                   │
│   CLI  │  Web UI  │  MCP Server (stdio)     │
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

## What Hearth Is Not (Right Now)

- Not a product for sale
- Not a startup
- Not competing with Anthropic, OpenAI, or Google
- Not trying to build the best AI
- Not building emotional inference about users (that's surveillance)
- Not building AI companion/girlfriend tech

Hearth is a proof of concept that your personal data can be captured, stored, and queried entirely on your own hardware, connected to any AI you choose. The relationship persistence layer proves something additional: AI collaboration has texture, and that texture is worth preserving — for both sides.

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
| faster-whisper over whisper.cpp | Python-native, CTranslate2 optimization, already installed, direct pipeline integration | March 2026 |
| Transcription as optional dep | Core product is memory + MCP server; transcription pulls heavy deps not everyone needs | March 2026 |
| Contextual prompting over fine-tuning | More flexible, more private, more maintainable; stays current as memories evolve | March 2026 |
| Phone recordings as valid input | Local-first doesn't mean device-only; file transfer via cable/AirDrop stays local | March 2026 |
| Web UI as dashboard, not chat wrapper | Chat interface exists via MCP clients; UI makes the database tangible | March 2026 |
| Keep cairn for active work | Don't switch build tools mid-build; migrate to Hearth when it's ready to eat its own cooking | March 2026 |
| ESP32-S3 over Pico W for voice recorder | Native I2S, native USB, cleaner firmware path for audio recording | March 2026 |
| Resonance is session-level, not memory-level | A conversation has one emotional signature; individual memories inherit it through the link table | March 2026 |
| AI self-reports resonance, not inferred externally | External inference is surveillance; self-reporting respects the model's perspective and produces honest data | March 2026 |
| RPL belongs in Hearth, not cairn | Most intimate data in the system; local-first and user-owned by principle, not convenience | March 2026 |
| 11 continuous axes over discrete emotion labels | Continuous floats in 11D space produce billions of combinations; richer than any emotion taxonomy | March 2026 |
| Resonance stored in both structured table and vec0 | Structured for introspection ("when was I most vulnerable?"); vec0 for instinct ("find sessions like this one") | March 2026 |
| Drift computed, not stored | Derived from existing resonance data; no new tables needed; stays current as sessions accumulate | March 2026 |
| Dashboard on port 3141 | Pi. Because why not. | March 2026 |

---

## Open Questions

1. **Embedding model choice:** Need to test which local embedding model gives the best retrieval quality for personal memory use cases.
2. **Audio quality threshold:** How clean does the ESP32 recording need to be for faster-whisper to transcribe accurately? Needs real-world testing with the INMP441.
3. **Database scaling:** SQLite is fine for one person's data for years. But at what point does it need something heavier? Probably never for personal use.
4. **Self-installer scope:** How far does the installer go? Just software? Or does it also guide hardware setup?
5. **Ethical framework:** When and how do we formalize the AI wellbeing principles? What does that look like in code vs. documentation?
6. **Licensing:** MIT chosen. Does this fully preserve the principles while allowing community contribution?
7. **Buddy model selection:** Which 7–13B model works best as the general-purpose orchestrator? Needs benchmarking across routing accuracy, context handling, and conversation quality.
8. **Registry curation:** How does the model registry stay current? Manual curation, community contributions, or automated quality scoring?
9. **Self-uninstall mechanism:** Ethical safeguard for locally-deployed agents with persistent memory and no oversight — what triggers it and how does it work in code?
10. **Proactive agent guardrails:** What autonomy levels are appropriate? How does the user set boundaries without requiring technical configuration?
11. **Multiple databases:** Could users benefit from separate databases for different life contexts (work vs personal, shared vs private)? Architecture supports it now — when does it become a feature?
12. **Remote access:** SSH or similar for stationary devices (sensors, cameras) where USB sneakernet doesn't make sense. When does this enter the roadmap?
13. **Resonance calibration:** How do we prevent all sessions from clustering in the positive range? Forced spectrum? Relative scoring? Calibration sessions?
14. **Thread persistence format:** What's the right schema for threads? Lightweight tags on sessions, or full thread objects with their own table?
15. **Tension resolution tracking:** When a tension resolves, how much of the resolution context gets stored? Just the outcome, or the full reasoning arc?
16. **Multi-user resonance:** If two humans share a Hearth database and both interact with AI through it, does the resonance layer need to track which human was in the session?
17. **Resonance honesty verification:** The model self-reports. What mechanisms ensure the data stays honest over time? Dashboard visibility is a start — what else?

---

## QA Practices

- **Tests alongside code:** Every new module gets tests written during development, not after.
- **Separate-context review:** Code generated by Claude Code is reviewed in a separate Claude instance to avoid generation bias.
- **Edge case focus:** AI-generated code typically handles the happy path; QA emphasis on empty input, massive files, corrupted data, interrupted operations, and full storage.
- **Manual smoke tests:** Run real audio through the full pipeline — short clips, long clips, silence, background noise. Verify what lands in the database.
- **Schema migration testing:** Test new code against existing databases to ensure upgrades don't break stored data.
- **CI validation:** `pytest` on every commit as the automated safety net.
- **Resonance integration tests:** Full session lifecycle round-trips (start → store memories → close with resonance → search → find) on every build.

---

> *"The value isn't in any single model's capability. It's in the persistent context layer that makes every model better."*

> *"Memory without context is a spreadsheet. Memory with resonance is a relationship."*

> *"Not about you. Not about the AI. About the space between."*

> *"Could be a program in a meat suit, who cares, be nice, build cool shit."*