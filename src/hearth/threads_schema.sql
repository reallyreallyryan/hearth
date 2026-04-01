-- Hearth Threads & Tension Layer v0.1
-- Tracks lines of thinking and unresolved questions across sessions.
-- Extends the core + resonance schemas.

-- ── Threads ────────────────────────────────────────────────────────
-- A thread is a named line of inquiry that spans multiple sessions.
-- Not a chat log — a directional arc.

CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,                -- human-readable name for the line of inquiry
    project TEXT,                       -- optional project scope
    status TEXT NOT NULL DEFAULT 'open', -- open, parked, resolved, abandoned
    trajectory TEXT,                    -- where was the thinking heading? updated each session
    created_session_id TEXT,            -- session where this thread first emerged
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (project) REFERENCES projects(name),
    FOREIGN KEY (created_session_id) REFERENCES sessions(id)
);

-- ── Thread-Session Links ───────────────────────────────────────────
-- Which sessions touched which threads, and what happened on that thread.

CREATE TABLE IF NOT EXISTS thread_sessions (
    thread_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    trajectory_note TEXT,              -- what happened on this thread during this session
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (thread_id, session_id),
    FOREIGN KEY (thread_id) REFERENCES threads(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ── Tensions ───────────────────────────────────────────────────────
-- An unresolved question or productive disagreement.
-- Linked to a thread (optional) and to the sessions where it was created/resolved.

CREATE TABLE IF NOT EXISTS tensions (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,             -- the unresolved question or disagreement
    status TEXT NOT NULL DEFAULT 'open', -- open, evolving, resolved, dissolved
    thread_id TEXT,                     -- parent thread (nullable — tensions can be free-floating)
    created_session_id TEXT,            -- session where this tension emerged
    resolved_session_id TEXT,           -- session where this tension was resolved (nullable)
    resolution TEXT,                    -- how it resolved (nullable, filled on resolution)
    perspectives TEXT DEFAULT '[]',     -- JSON array of perspective objects
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (thread_id) REFERENCES threads(id),
    FOREIGN KEY (created_session_id) REFERENCES sessions(id),
    FOREIGN KEY (resolved_session_id) REFERENCES sessions(id)
);

-- ── Indexes ────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_threads_project ON threads(project);
CREATE INDEX IF NOT EXISTS idx_threads_status ON threads(status);
CREATE INDEX IF NOT EXISTS idx_threads_created_session ON threads(created_session_id);
CREATE INDEX IF NOT EXISTS idx_thread_sessions_thread ON thread_sessions(thread_id);
CREATE INDEX IF NOT EXISTS idx_thread_sessions_session ON thread_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_tensions_thread ON tensions(thread_id);
CREATE INDEX IF NOT EXISTS idx_tensions_status ON tensions(status);
CREATE INDEX IF NOT EXISTS idx_tensions_created_session ON tensions(created_session_id);
