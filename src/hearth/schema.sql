-- Hearth v0.1 Schema
-- All DDL lives here. Executed by db.init_db().

-- Core memories table
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    project TEXT,
    tags TEXT,
    source TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    archived INTEGER NOT NULL DEFAULT 0
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Full-text search index
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    category,
    project,
    tags,
    content='memories',
    content_rowid='rowid'
);

-- FTS5 sync triggers
CREATE TRIGGER IF NOT EXISTS memories_fts_insert AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, category, project, tags)
    VALUES (NEW.rowid, NEW.content, COALESCE(NEW.category, ''), COALESCE(NEW.project, ''), COALESCE(NEW.tags, ''));
END;

CREATE TRIGGER IF NOT EXISTS memories_fts_update AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, category, project, tags)
    VALUES ('delete', OLD.rowid, OLD.content, COALESCE(OLD.category, ''), COALESCE(OLD.project, ''), COALESCE(OLD.tags, ''));
    INSERT INTO memories_fts(rowid, content, category, project, tags)
    VALUES (NEW.rowid, NEW.content, COALESCE(NEW.category, ''), COALESCE(NEW.project, ''), COALESCE(NEW.tags, ''));
END;

CREATE TRIGGER IF NOT EXISTS memories_fts_delete AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, category, project, tags)
    VALUES ('delete', OLD.rowid, OLD.content, COALESCE(OLD.category, ''), COALESCE(OLD.project, ''), COALESCE(OLD.tags, ''));
END;

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
