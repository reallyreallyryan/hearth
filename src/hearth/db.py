"""Database operations for Hearth. All CRUD, embedding storage, and FTS helpers."""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import apsw
import sqlite_vec

from hearth.config import (
    RESONANCE_AXES,
    VALID_CATEGORIES,
    VALID_PROJECT_STATUSES,
    VALID_SOURCES,
    VALID_TENSION_STATUSES,
    VALID_THREAD_STATUSES,
)

logger = logging.getLogger("hearth.db")

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
RESONANCE_SCHEMA_PATH = Path(__file__).parent / "resonance_schema.sql"
THREADS_SCHEMA_PATH = Path(__file__).parent / "threads_schema.sql"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _new_id() -> str:
    return secrets.token_hex(16)


class HearthDB:
    """Manages the Hearth SQLite database via APSW."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: apsw.Connection | None = None

    @property
    def conn(self) -> apsw.Connection:
        if self._conn is None:
            self._conn = self._connect()
        return self._conn

    def _connect(self) -> apsw.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = apsw.Connection(str(self.db_path))
        conn.enableloadextension(True)
        conn.loadextension(sqlite_vec.loadable_path())
        conn.enableloadextension(False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_db(self) -> None:
        """Execute schema.sql, resonance_schema.sql, and create vec0 tables if needed."""
        schema_sql = SCHEMA_PATH.read_text()
        cursor = self.conn.cursor()
        cursor.execute(schema_sql)

        # vec0 may not support IF NOT EXISTS — check first
        existing = list(
            self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_embeddings'"
            )
        )
        if not existing:
            self.conn.execute(
                "CREATE VIRTUAL TABLE memory_embeddings USING vec0("
                "memory_id TEXT PRIMARY KEY, "
                "embedding float[768]"
                ")"
            )

        # Load resonance schema (sessions, session_resonance, session_memories)
        resonance_sql = RESONANCE_SCHEMA_PATH.read_text()
        cursor.execute(resonance_sql)

        # Create resonance_embeddings vec0 table if needed
        existing_res = list(
            self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='resonance_embeddings'"
            )
        )
        if not existing_res:
            self.conn.execute(
                "CREATE VIRTUAL TABLE resonance_embeddings USING vec0("
                "session_id TEXT PRIMARY KEY, "
                "resonance float[11]"
                ")"
            )

        # Load threads & tension schema
        threads_sql = THREADS_SCHEMA_PATH.read_text()
        cursor.execute(threads_sql)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ── Helpers ──────────────────────────────────────────────────────

    def _row_to_dict(self, cursor: apsw.Cursor, row: tuple[Any, ...]) -> dict[str, Any]:
        desc = cursor.getdescription()
        d = {col[0]: val for col, val in zip(desc, row)}
        if "tags" in d and d["tags"] is not None:
            try:
                d["tags"] = json.loads(d["tags"])
            except (json.JSONDecodeError, TypeError):
                d["tags"] = []
        if "perspectives" in d and d["perspectives"] is not None:
            try:
                d["perspectives"] = json.loads(d["perspectives"])
            except (json.JSONDecodeError, TypeError):
                d["perspectives"] = []
        if "archived" in d:
            d["archived"] = bool(d["archived"])
        return d

    def _validate_category(self, category: str) -> None:
        if category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}"
            )

    def _validate_source(self, source: str) -> None:
        if source not in VALID_SOURCES:
            raise ValueError(
                f"Invalid source '{source}'. Must be one of: {', '.join(sorted(VALID_SOURCES))}"
            )

    def _validate_project_exists(self, project: str) -> None:
        row = list(self.conn.execute(
            "SELECT 1 FROM projects WHERE name = ? AND status != 'archived'", (project,)
        ))
        if not row:
            raise ValueError(f"Project '{project}' does not exist or is archived")

    def _validate_project_status(self, status: str) -> None:
        if status not in VALID_PROJECT_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_PROJECT_STATUSES))}"
            )

    def _validate_resonance_axes(self, axes: dict[str, float]) -> None:
        missing = set(RESONANCE_AXES) - set(axes.keys())
        if missing:
            raise ValueError(f"Missing resonance axes: {', '.join(sorted(missing))}")
        extra = set(axes.keys()) - set(RESONANCE_AXES)
        if extra:
            raise ValueError(f"Unknown resonance axes: {', '.join(sorted(extra))}")
        for axis, value in axes.items():
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Resonance axis '{axis}' must be a number, got {type(value).__name__}"
                )
            if value < -1.0 or value > 1.0:
                raise ValueError(
                    f"Resonance axis '{axis}' must be in [-1, 1], got {value}"
                )

    def _validate_session_exists(self, session_id: str) -> None:
        row = list(self.conn.execute(
            "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
        ))
        if not row:
            raise ValueError(f"Session '{session_id}' does not exist")

    def _validate_thread_status(self, status: str) -> None:
        if status not in VALID_THREAD_STATUSES:
            raise ValueError(
                f"Invalid thread status '{status}'. "
                f"Must be one of: {', '.join(sorted(VALID_THREAD_STATUSES))}"
            )

    def _validate_thread_exists(self, thread_id: str) -> None:
        row = list(self.conn.execute(
            "SELECT 1 FROM threads WHERE id = ?", (thread_id,)
        ))
        if not row:
            raise ValueError(f"Thread '{thread_id}' does not exist")

    def _validate_tension_status(self, status: str) -> None:
        if status not in VALID_TENSION_STATUSES:
            raise ValueError(
                f"Invalid tension status '{status}'. "
                f"Must be one of: {', '.join(sorted(VALID_TENSION_STATUSES))}"
            )

    def _validate_tension_exists(self, tension_id: str) -> None:
        row = list(self.conn.execute(
            "SELECT 1 FROM tensions WHERE id = ?", (tension_id,)
        ))
        if not row:
            raise ValueError(f"Tension '{tension_id}' does not exist")

    # ── Memory CRUD ─────────────────────────────────────────────────

    def store_memory(
        self,
        content: str,
        category: str = "general",
        project: str | None = None,
        tags: list[str] | None = None,
        source: str = "user",
    ) -> dict[str, Any]:
        """Store a new memory. Returns the created memory as a dict."""
        self._validate_category(category)
        self._validate_source(source)
        if project is not None:
            self._validate_project_exists(project)

        memory_id = _new_id()
        now = _now()
        tags_json = json.dumps(tags) if tags else None

        self.conn.execute(
            "INSERT INTO memories (id, content, category, project, tags, source, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (memory_id, content, category, project, tags_json, source, now, now),
        )

        return {
            "id": memory_id,
            "content": content,
            "category": category,
            "project": project,
            "tags": tags or [],
            "source": source,
            "created_at": now,
            "updated_at": now,
            "archived": False,
        }

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Get a single memory by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = next(cursor, None)
        if row is None:
            return None
        return self._row_to_dict(cursor, row)

    def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        category: str | None = None,
        project: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Update fields on an existing memory. Returns updated memory or None."""
        existing = self.get_memory(memory_id)
        if existing is None:
            return None

        if category is not None:
            self._validate_category(category)
        if project is not None:
            self._validate_project_exists(project)

        updates: list[str] = []
        params: list[Any] = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if project is not None:
            updates.append("project = ?")
            params.append(project)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))

        if not updates:
            return existing

        updates.append("updated_at = ?")
        params.append(_now())
        params.append(memory_id)

        self.conn.execute(
            f"UPDATE memories SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )

        return self.get_memory(memory_id)

    def delete_memory(self, memory_id: str) -> bool:
        """Soft-delete a memory by setting archived=1. Returns True if found."""
        existing = self.get_memory(memory_id)
        if existing is None:
            return False
        self.conn.execute(
            "UPDATE memories SET archived = 1, updated_at = ? WHERE id = ?",
            (_now(), memory_id),
        )
        return True

    def _build_memory_filters(
        self,
        project: str | None = None,
        category: str | None = None,
        source: str | None = None,
        include_archived: bool = False,
    ) -> tuple[str, list[Any]]:
        """Build WHERE clause and params for memory queries."""
        conditions: list[str] = []
        params: list[Any] = []

        if not include_archived:
            conditions.append("archived = 0")
        if project is not None:
            conditions.append("project = ?")
            params.append(project)
        if category is not None:
            conditions.append("category = ?")
            params.append(category)
        if source is not None:
            conditions.append("source = ?")
            params.append(source)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return where, params

    def list_memories(
        self,
        project: str | None = None,
        category: str | None = None,
        source: str | None = None,
        limit: int = 10,
        offset: int = 0,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """List memories with optional filters."""
        where, params = self._build_memory_filters(
            project=project, category=category, source=source,
            include_archived=include_archived,
        )
        params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT * FROM memories {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            tuple(params),
        )

        results = []
        for row in cursor:
            results.append(self._row_to_dict(cursor, row))
        return results

    def count_memories(
        self,
        project: str | None = None,
        category: str | None = None,
        source: str | None = None,
        include_archived: bool = False,
    ) -> int:
        """Count memories matching filters. Used for pagination."""
        where, params = self._build_memory_filters(
            project=project, category=category, source=source,
            include_archived=include_archived,
        )
        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT COUNT(*) FROM memories {where}",
            tuple(params),
        )
        return next(cursor)[0]

    # ── Project CRUD ────────────────────────────────────────────────

    def create_project(self, name: str, description: str | None = None) -> dict[str, Any]:
        """Create a new project. Raises ValueError if name already exists."""
        existing = list(self.conn.execute(
            "SELECT 1 FROM projects WHERE name = ?", (name,)
        ))
        if existing:
            raise ValueError(f"Project '{name}' already exists")

        project_id = _new_id()
        now = _now()

        self.conn.execute(
            "INSERT INTO projects (id, name, description, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'active', ?, ?)",
            (project_id, name, description, now, now),
        )

        return {
            "id": project_id,
            "name": name,
            "description": description,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }

    def get_project(self, name: str) -> dict[str, Any] | None:
        """Get project by name, including recent memory count."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE name = ?", (name,))
        row = next(cursor, None)
        if row is None:
            return None
        project = self._row_to_dict(cursor, row)

        # Add memory count
        count_row = next(self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE project = ? AND archived = 0", (name,)
        ))
        project["memory_count"] = count_row[0]
        return project

    def list_projects(self, include_archived: bool = False) -> list[dict[str, Any]]:
        """List all projects."""
        if include_archived:
            sql = "SELECT * FROM projects ORDER BY created_at DESC"
            params: tuple[Any, ...] = ()
        else:
            sql = "SELECT * FROM projects WHERE status != 'archived' ORDER BY created_at DESC"
            params = ()

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return [self._row_to_dict(cursor, row) for row in cursor]

    def update_project(
        self,
        name: str,
        description: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any] | None:
        """Update project fields. Returns updated project or None."""
        existing = self.get_project(name)
        if existing is None:
            return None

        if status is not None:
            self._validate_project_status(status)

        updates: list[str] = []
        params: list[Any] = []

        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if not updates:
            return existing

        updates.append("updated_at = ?")
        params.append(_now())
        params.append(name)

        self.conn.execute(
            f"UPDATE projects SET {', '.join(updates)} WHERE name = ?",
            tuple(params),
        )

        return self.get_project(name)

    def archive_project(self, name: str) -> bool:
        """Archive a project. Returns True if found."""
        result = self.update_project(name, status="archived")
        return result is not None

    # ── Session CRUD ───────────────────────────────────────────────

    def create_session(self, project: str | None = None) -> dict[str, Any]:
        """Start a new session. Returns the created session as a dict."""
        if project is not None:
            self._validate_project_exists(project)

        session_id = _new_id()
        now = _now()
        self.conn.execute(
            "INSERT INTO sessions (id, project, started_at) VALUES (?, ?, ?)",
            (session_id, project, now),
        )
        return {
            "id": session_id,
            "project": project,
            "started_at": now,
            "ended_at": None,
            "summary": None,
            "memory_count": 0,
        }

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a single session by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = next(cursor, None)
        if row is None:
            return None
        return self._row_to_dict(cursor, row)

    def close_session(
        self,
        session_id: str,
        summary: str | None = None,
        ended_at: str | None = None,
    ) -> dict[str, Any] | None:
        """Close a session with an optional summary. Returns updated session or None."""
        existing = self.get_session(session_id)
        if existing is None:
            return None
        if ended_at is None:
            ended_at = _now()
        self.conn.execute(
            "UPDATE sessions SET ended_at = ?, summary = ? WHERE id = ?",
            (ended_at, summary, session_id),
        )
        return self.get_session(session_id)

    def list_sessions(
        self,
        project: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List sessions, optionally filtered by project. Newest first."""
        conditions: list[str] = []
        params: list[Any] = []
        if project is not None:
            conditions.append("project = ?")
            params.append(project)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])
        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT * FROM sessions {where} ORDER BY started_at DESC LIMIT ? OFFSET ?",
            tuple(params),
        )
        return [self._row_to_dict(cursor, row) for row in cursor]

    # ── Resonance Operations ───────────────────────────────────────

    def store_resonance(self, session_id: str, axes: dict[str, float]) -> dict[str, Any]:
        """Store the 11-axis resonance for a session and its vec0 embedding."""
        import struct

        self._validate_session_exists(session_id)
        self._validate_resonance_axes(axes)

        resonance_id = _new_id()
        now = _now()
        columns = ", ".join(RESONANCE_AXES)
        placeholders = ", ".join(["?"] * len(RESONANCE_AXES))
        values = [float(axes[axis]) for axis in RESONANCE_AXES]

        self.conn.execute(
            f"INSERT INTO session_resonance (id, session_id, {columns}, created_at) "
            f"VALUES (?, ?, {placeholders}, ?)",
            (resonance_id, session_id, *values, now),
        )

        # Store vec0 embedding (11 floats in RESONANCE_AXES order)
        blob = struct.pack("11f", *values)
        self.conn.execute(
            "INSERT INTO resonance_embeddings (session_id, resonance) VALUES (?, ?)",
            (session_id, blob),
        )

        result: dict[str, Any] = {"id": resonance_id, "session_id": session_id, "created_at": now}
        result.update(axes)
        return result

    def get_resonance(self, session_id: str) -> dict[str, Any] | None:
        """Get resonance data for a session."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM session_resonance WHERE session_id = ?", (session_id,)
        )
        row = next(cursor, None)
        if row is None:
            return None
        return self._row_to_dict(cursor, row)

    def search_resonance(
        self, axes: dict[str, float], limit: int = 5
    ) -> list[tuple[str, float]]:
        """Vector similarity search in resonance space. Returns (session_id, distance) pairs."""
        import struct

        self._validate_resonance_axes(axes)
        values = [float(axes[axis]) for axis in RESONANCE_AXES]
        blob = struct.pack("11f", *values)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT session_id, distance FROM resonance_embeddings "
            "WHERE resonance MATCH ? AND k = ?",
            (blob, limit),
        )
        return [(row[0], row[1]) for row in cursor]

    # ── Session-Memory Links ───────────────────────────────────────

    def link_memory_to_session(
        self, session_id: str, memory_id: str, action: str = "created"
    ) -> None:
        """Link a memory to a session. No-op if already linked."""
        self._validate_session_exists(session_id)
        if self.get_memory(memory_id) is None:
            raise ValueError(f"Memory '{memory_id}' does not exist")

        try:
            self.conn.execute(
                "INSERT INTO session_memories (session_id, memory_id, action) "
                "VALUES (?, ?, ?)",
                (session_id, memory_id, action),
            )
            self.conn.execute(
                "UPDATE sessions SET memory_count = memory_count + 1 WHERE id = ?",
                (session_id,),
            )
        except apsw.ConstraintError:
            pass  # Already linked, no-op

    def get_session_memories(self, session_id: str) -> list[dict[str, Any]]:
        """Return all memories linked to a session, with their action type."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT m.*, sm.action "
            "FROM session_memories sm "
            "JOIN memories m ON sm.memory_id = m.id "
            "WHERE sm.session_id = ? "
            "ORDER BY m.created_at ASC",
            (session_id,),
        )
        return [self._row_to_dict(cursor, row) for row in cursor]

    # ── Thread CRUD ─────────────────────────────────────────────────

    def create_thread(
        self,
        title: str,
        project: str | None = None,
        session_id: str | None = None,
        trajectory: str | None = None,
    ) -> dict[str, Any]:
        """Create a new thread (line of inquiry). Returns the created thread."""
        if project is not None:
            self._validate_project_exists(project)
        if session_id is not None:
            self._validate_session_exists(session_id)

        thread_id = _new_id()
        now = _now()
        self.conn.execute(
            "INSERT INTO threads (id, title, project, status, trajectory, "
            "created_session_id, created_at, updated_at) "
            "VALUES (?, ?, ?, 'open', ?, ?, ?, ?)",
            (thread_id, title, project, trajectory, session_id, now, now),
        )

        # Auto-link the creating session
        if session_id is not None:
            self.conn.execute(
                "INSERT OR IGNORE INTO thread_sessions "
                "(thread_id, session_id, created_at) VALUES (?, ?, ?)",
                (thread_id, session_id, now),
            )

        return {
            "id": thread_id,
            "title": title,
            "project": project,
            "status": "open",
            "trajectory": trajectory,
            "created_session_id": session_id,
            "created_at": now,
            "updated_at": now,
        }

    def get_thread(self, thread_id: str) -> dict[str, Any] | None:
        """Get a single thread by ID. Returns None if not found."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM threads WHERE id = ?", (thread_id,))
        row = next(cursor, None)
        if row is None:
            return None
        return self._row_to_dict(cursor, row)

    def update_thread(
        self,
        thread_id: str,
        title: str | None = None,
        status: str | None = None,
        trajectory: str | None = None,
    ) -> dict[str, Any] | None:
        """Update thread fields. Returns updated thread or None if not found."""
        existing = self.get_thread(thread_id)
        if existing is None:
            return None

        if status is not None:
            self._validate_thread_status(status)

        updates: list[str] = []
        params: list[Any] = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if trajectory is not None:
            updates.append("trajectory = ?")
            params.append(trajectory)

        if not updates:
            return existing

        updates.append("updated_at = ?")
        params.append(_now())
        params.append(thread_id)

        self.conn.execute(
            f"UPDATE threads SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        return self.get_thread(thread_id)

    def list_threads(
        self,
        project: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List threads with session_count and tension_count."""
        conditions: list[str] = []
        params: list[Any] = []

        if project is not None:
            conditions.append("t.project = ?")
            params.append(project)
        if status is not None:
            self._validate_thread_status(status)
            conditions.append("t.status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT t.*, "
            f"(SELECT COUNT(*) FROM thread_sessions ts "
            f"WHERE ts.thread_id = t.id) AS session_count, "
            f"(SELECT COUNT(*) FROM tensions tn "
            f"WHERE tn.thread_id = t.id) AS tension_count "
            f"FROM threads t {where} "
            f"ORDER BY t.updated_at DESC LIMIT ?",
            tuple(params),
        )
        return [self._row_to_dict(cursor, row) for row in cursor]

    def link_thread_session(
        self,
        thread_id: str,
        session_id: str,
        trajectory_note: str | None = None,
    ) -> None:
        """Link a thread to a session (upsert). Updates thread's updated_at."""
        self._validate_thread_exists(thread_id)
        self._validate_session_exists(session_id)

        now = _now()
        self.conn.execute(
            "INSERT INTO thread_sessions (thread_id, session_id, trajectory_note, created_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(thread_id, session_id) "
            "DO UPDATE SET trajectory_note = excluded.trajectory_note",
            (thread_id, session_id, trajectory_note, now),
        )
        self.conn.execute(
            "UPDATE threads SET updated_at = ? WHERE id = ?",
            (now, thread_id),
        )

    def get_thread_sessions(self, thread_id: str) -> list[dict[str, Any]]:
        """Get all sessions linked to a thread, with trajectory notes."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT s.*, ts.trajectory_note "
            "FROM thread_sessions ts "
            "JOIN sessions s ON ts.session_id = s.id "
            "WHERE ts.thread_id = ? "
            "ORDER BY s.started_at ASC",
            (thread_id,),
        )
        return [self._row_to_dict(cursor, row) for row in cursor]

    # ── Tension CRUD ────────────────────────────────────────────────

    def create_tension(
        self,
        question: str,
        thread_id: str | None = None,
        session_id: str | None = None,
        perspectives: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new tension (unresolved question). Returns the created tension."""
        if thread_id is not None:
            self._validate_thread_exists(thread_id)
        if session_id is not None:
            self._validate_session_exists(session_id)

        tension_id = _new_id()
        now = _now()
        perspectives_json = json.dumps(perspectives) if perspectives else "[]"

        self.conn.execute(
            "INSERT INTO tensions (id, question, status, thread_id, "
            "created_session_id, perspectives, created_at, updated_at) "
            "VALUES (?, ?, 'open', ?, ?, ?, ?, ?)",
            (tension_id, question, thread_id, session_id, perspectives_json, now, now),
        )

        return {
            "id": tension_id,
            "question": question,
            "status": "open",
            "thread_id": thread_id,
            "created_session_id": session_id,
            "resolved_session_id": None,
            "resolution": None,
            "perspectives": perspectives or [],
            "created_at": now,
            "updated_at": now,
        }

    def get_tension(self, tension_id: str) -> dict[str, Any] | None:
        """Get a single tension by ID. Perspectives auto-deserialized."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tensions WHERE id = ?", (tension_id,))
        row = next(cursor, None)
        if row is None:
            return None
        return self._row_to_dict(cursor, row)

    def update_tension(
        self,
        tension_id: str,
        status: str | None = None,
        resolution: str | None = None,
        resolved_session_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Update tension fields. Returns updated tension or None if not found."""
        existing = self.get_tension(tension_id)
        if existing is None:
            return None

        if status is not None:
            self._validate_tension_status(status)
        if resolved_session_id is not None:
            self._validate_session_exists(resolved_session_id)

        updates: list[str] = []
        params: list[Any] = []

        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if resolution is not None:
            updates.append("resolution = ?")
            params.append(resolution)
        if resolved_session_id is not None:
            updates.append("resolved_session_id = ?")
            params.append(resolved_session_id)

        if not updates:
            return existing

        updates.append("updated_at = ?")
        params.append(_now())
        params.append(tension_id)

        self.conn.execute(
            f"UPDATE tensions SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        return self.get_tension(tension_id)

    def add_tension_perspective(
        self,
        tension_id: str,
        perspective: str,
        source: str = "assistant",
        session_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Append a perspective to a tension's JSON array.
        Auto-transitions status to 'evolving' if currently 'open'."""
        existing = self.get_tension(tension_id)
        if existing is None:
            return None

        current = existing.get("perspectives") or []
        entry = {"perspective": perspective, "source": source}
        if session_id is not None:
            entry["session_id"] = session_id
        current.append(entry)

        now = _now()
        new_status = existing["status"]
        if new_status == "open":
            new_status = "evolving"

        self.conn.execute(
            "UPDATE tensions SET perspectives = ?, status = ?, updated_at = ? "
            "WHERE id = ?",
            (json.dumps(current), new_status, now, tension_id),
        )
        return self.get_tension(tension_id)

    def list_tensions(
        self,
        thread_id: str | None = None,
        status: str | None = None,
        project: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List tensions with optional filters. Project filter matches via thread or session."""
        conditions: list[str] = []
        params: list[Any] = []

        if project is not None:
            conditions.append(
                "(EXISTS (SELECT 1 FROM threads th "
                "WHERE th.id = tn.thread_id AND th.project = ?) "
                "OR EXISTS (SELECT 1 FROM sessions s "
                "WHERE s.id = tn.created_session_id AND s.project = ?))"
            )
            params.extend([project, project])
        if status is not None:
            self._validate_tension_status(status)
            conditions.append("tn.status = ?")
            params.append(status)
        if thread_id is not None:
            conditions.append("tn.thread_id = ?")
            params.append(thread_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT tn.* FROM tensions tn {where} "
            f"ORDER BY tn.updated_at DESC LIMIT ?",
            tuple(params),
        )
        return [self._row_to_dict(cursor, row) for row in cursor]

    # ── Embedding Operations ────────────────────────────────────────

    def store_embedding(self, memory_id: str, embedding: list[float]) -> None:
        """Store an embedding vector for a memory."""
        import struct

        blob = struct.pack(f"{len(embedding)}f", *embedding)
        self.conn.execute(
            "INSERT INTO memory_embeddings (memory_id, embedding) VALUES (?, ?)",
            (memory_id, blob),
        )

    def delete_embedding(self, memory_id: str) -> None:
        """Delete the embedding for a memory."""
        self.conn.execute(
            "DELETE FROM memory_embeddings WHERE memory_id = ?", (memory_id,)
        )

    def get_pending_embeddings(self) -> list[dict[str, Any]]:
        """Return memories that have no embedding yet."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT m.id, m.content FROM memories m "
            "LEFT JOIN memory_embeddings me ON m.id = me.memory_id "
            "WHERE me.memory_id IS NULL AND m.archived = 0"
        )
        return [{"id": row[0], "content": row[1]} for row in cursor]

    # ── FTS Search ──────────────────────────────────────────────────

    def fts_search(
        self,
        query: str,
        project: str | None = None,
        category: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Full-text search using FTS5. Returns memories with BM25 rank scores."""
        # Sanitize query for FTS5
        sanitized = _sanitize_fts_query(query)
        if not sanitized:
            return []

        conditions = ["memories_fts MATCH ?", "m.archived = 0"]
        params: list[Any] = [sanitized]

        if project is not None:
            conditions.append("m.project = ?")
            params.append(project)
        if category is not None:
            conditions.append("m.category = ?")
            params.append(category)

        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT m.*, rank AS fts_rank "
            "FROM memories_fts f "
            "JOIN memories m ON f.rowid = m.rowid "
            f"WHERE {' AND '.join(conditions)} "
            "ORDER BY rank "
            "LIMIT ?",
            tuple(params),
        )

        results = []
        for row in cursor:
            d = self._row_to_dict(cursor, row)
            d["fts_rank"] = d.pop("fts_rank", 0.0)
            results.append(d)
        return results

    def vec_search(
        self,
        embedding: list[float],
        limit: int = 10,
    ) -> list[tuple[str, float]]:
        """Vector similarity search. Returns (memory_id, distance) pairs."""
        import struct

        blob = struct.pack(f"{len(embedding)}f", *embedding)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT memory_id, distance FROM memory_embeddings "
            "WHERE embedding MATCH ? AND k = ?",
            (blob, limit),
        )
        return [(row[0], row[1]) for row in cursor]

    # ── Stats & Export ──────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Return database statistics."""
        total = next(self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE archived = 0"
        ))[0]
        archived = next(self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE archived = 1"
        ))[0]
        embeddings = next(self.conn.execute(
            "SELECT COUNT(*) FROM memory_embeddings"
        ))[0]
        projects = next(self.conn.execute(
            "SELECT COUNT(*) FROM projects WHERE status != 'archived'"
        ))[0]

        by_category: dict[str, int] = {}
        for row in self.conn.execute(
            "SELECT category, COUNT(*) FROM memories WHERE archived = 0 GROUP BY category"
        ):
            by_category[row[0]] = row[1]

        by_project: dict[str, int] = {}
        for row in self.conn.execute(
            "SELECT COALESCE(project, '(global)'), COUNT(*) FROM memories "
            "WHERE archived = 0 GROUP BY project"
        ):
            by_project[row[0]] = row[1]

        return {
            "total_memories": total,
            "archived_memories": archived,
            "total_embeddings": embeddings,
            "pending_embeddings": total - embeddings,
            "active_projects": projects,
            "by_category": by_category,
            "by_project": by_project,
        }

    def export_memories(self, format: str = "json") -> str:
        """Export all non-archived memories."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM memories WHERE archived = 0 ORDER BY created_at DESC"
        )
        memories = [self._row_to_dict(cursor, row) for row in cursor]

        if format == "json":
            return json.dumps(memories, indent=2)
        elif format == "csv":
            if not memories:
                return "id,content,category,project,tags,source,created_at,updated_at\n"
            import csv
            import io

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=memories[0].keys())
            writer.writeheader()
            for m in memories:
                row = dict(m)
                if isinstance(row.get("tags"), list):
                    row["tags"] = json.dumps(row["tags"])
                writer.writerow(row)
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")


def _sanitize_fts_query(query: str) -> str:
    """Sanitize a user query for FTS5 MATCH syntax.

    Wraps each word in double quotes to avoid FTS5 syntax errors from
    special characters like *, -, etc.
    """
    words = query.split()
    if not words:
        return ""
    return " ".join(f'"{w}"' for w in words)
