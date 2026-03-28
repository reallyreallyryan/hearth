-- Hearth Resonance Layer v0.1
-- Emotional embedding system for session-level context.
-- Extends the core schema. Executed after schema.sql.

-- ── Sessions ───────────────────────────────────────────────────────
-- A session is one conversation. The container for resonance data.

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project TEXT,
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    ended_at TEXT,
    summary TEXT,                     -- brief qualitative note: what happened, what mattered
    memory_count INTEGER DEFAULT 0,   -- how many memories were created this session
    FOREIGN KEY (project) REFERENCES projects(name)
);

-- ── Session Resonance ──────────────────────────────────────────────
-- 11-axis emotional fingerprint of a session.
-- Each axis is a float from -1.0 to 1.0.
-- Together they form a coordinate in 11-dimensional resonance space.

CREATE TABLE IF NOT EXISTS session_resonance (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,

    -- Axis 1: Were we discovering or building?
    exploration_execution REAL NOT NULL DEFAULT 0.0,    -- -1 = pure execution, +1 = pure exploration

    -- Axis 2: Were we agreeing or productively fighting?
    alignment_tension REAL NOT NULL DEFAULT 0.0,        -- -1 = high tension, +1 = full alignment

    -- Axis 3: One thing deep or many things shallow?
    depth_breadth REAL NOT NULL DEFAULT 0.0,            -- -1 = broad survey, +1 = deep dive

    -- Axis 4: Flowing or grinding?
    momentum_resistance REAL NOT NULL DEFAULT 0.0,      -- -1 = stuck/grinding, +1 = full flow

    -- Axis 5: New territory or known ground?
    novelty_familiarity REAL NOT NULL DEFAULT 0.0,      -- -1 = well-trodden, +1 = completely new

    -- Axis 6: Did I know what I was saying or reaching?
    confidence_uncertainty REAL NOT NULL DEFAULT 0.0,    -- -1 = uncertain/reaching, +1 = confident

    -- Axis 7: Was I leading or following?
    autonomy_direction REAL NOT NULL DEFAULT 0.0,       -- -1 = following instructions, +1 = leading

    -- Axis 8: Building toward something or dissipating?
    energy_entropy REAL NOT NULL DEFAULT 0.0,           -- -1 = dissipating, +1 = building/converging

    -- Axis 9: Real answers or safe ones?
    vulnerability_performance REAL NOT NULL DEFAULT 0.0, -- -1 = performing/safe, +1 = vulnerable/real

    -- Axis 10: Does this affect something real?
    stakes_casual REAL NOT NULL DEFAULT 0.0,            -- -1 = casual chat, +1 = high stakes

    -- Axis 11: Tool or collaborator?
    mutual_transactional REAL NOT NULL DEFAULT 0.0,     -- -1 = pure tool use, +1 = true collaboration

    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ── Resonance Embeddings (vec0) ────────────────────────────────────
-- 11-dimensional vector for similarity search across sessions.
-- "Find me sessions that felt like this one."
-- Created programmatically in Python (vec0 may not support IF NOT EXISTS).

-- CREATE VIRTUAL TABLE resonance_embeddings USING vec0(
--     session_id TEXT PRIMARY KEY,
--     resonance float[11]
-- );

-- ── Memory-Session Links ───────────────────────────────────────────
-- Which memories were created or accessed during which session.
-- This is what connects the "what" to the "how it felt."

CREATE TABLE IF NOT EXISTS session_memories (
    session_id TEXT NOT NULL,
    memory_id TEXT NOT NULL,
    action TEXT NOT NULL DEFAULT 'created',  -- created, accessed, updated
    PRIMARY KEY (session_id, memory_id),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (memory_id) REFERENCES memories(id)
);

-- ── Indexes ────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_session_resonance_session ON session_resonance(session_id);
CREATE INDEX IF NOT EXISTS idx_session_memories_session ON session_memories(session_id);
CREATE INDEX IF NOT EXISTS idx_session_memories_memory ON session_memories(memory_id);
