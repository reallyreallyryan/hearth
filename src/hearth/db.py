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

from hearth.config import VALID_CATEGORIES, VALID_PROJECT_STATUSES, VALID_SOURCES

logger = logging.getLogger("hearth.db")

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


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
        """Execute schema.sql and create vec0 table if needed."""
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

    def list_memories(
        self,
        project: str | None = None,
        category: str | None = None,
        limit: int = 10,
        offset: int = 0,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """List memories with optional filters."""
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

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
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
