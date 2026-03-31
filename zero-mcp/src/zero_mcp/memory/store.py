"""SQLite-backed vector store with all database tables for zero-mcp."""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

import numpy as np

from ..config.settings import DB_PATH, DEFAULT_MIN_SCORE, DEFAULT_TOP_K
from .embeddings import EmbeddingModel
from .similarity import search_similar

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages the single SQLite database and provides pattern memory CRUD.

    All seven tables defined in DESIGN-SPEC §10.1 are created on first use:
    ``patterns``, ``sessions``, ``steps``, ``mcp_calls``, ``project_files``,
    ``file_exports``, ``file_imports``.

    Args:
        db_path: Path to the SQLite database file.
        embedding_model: Pre-initialised :class:`EmbeddingModel` instance.
            Injected rather than constructed internally to allow test mocking.
    """

    def __init__(
        self,
        db_path: Path | str = DB_PATH,
        embedding_model: EmbeddingModel | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
        )
        # Enable WAL mode for better concurrent read performance.
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

        self._create_tables()

        self.model = embedding_model or EmbeddingModel()

    # ── Table creation ───────────────────────────────────────────────────

    def _create_tables(self) -> None:
        """Create all seven tables and their indices if they do not exist."""
        self.conn.executescript(
            """
            -- Patterns (vector memory)
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                context TEXT NOT NULL,
                approach TEXT NOT NULL,
                outcome TEXT NOT NULL,
                project TEXT,
                embedding BLOB NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                last_matched_at TEXT,
                match_count INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_patterns_project
                ON patterns(project);
            CREATE INDEX IF NOT EXISTS idx_patterns_created
                ON patterns(created_at);

            -- Sessions
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                classification TEXT NOT NULL,
                ai_tool TEXT,
                project TEXT,
                started_at TEXT DEFAULT (datetime('now')),
                ended_at TEXT,
                status TEXT,
                total_input_tokens INTEGER DEFAULT 0,
                total_output_tokens INTEGER DEFAULT 0,
                total_cached_tokens INTEGER DEFAULT 0,
                total_cost_usd REAL DEFAULT 0,
                report_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_project
                ON sessions(project);
            CREATE INDEX IF NOT EXISTS idx_sessions_started
                ON sessions(started_at);

            -- Steps (per-agent token usage within a session)
            CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                agent TEXT NOT NULL,
                model TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cached_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                duration_ms INTEGER,
                accuracy TEXT DEFAULT 'estimated',
                started_at TEXT DEFAULT (datetime('now')),
                ended_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_steps_session
                ON steps(session_id);

            -- MCP call tracking
            CREATE TABLE IF NOT EXISTS mcp_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT REFERENCES sessions(id),
                tool_name TEXT NOT NULL,
                input_bytes INTEGER DEFAULT 0,
                output_bytes INTEGER DEFAULT 0,
                duration_ms INTEGER,
                called_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_mcp_calls_session
                ON mcp_calls(session_id);

            -- Codebase index: files
            CREATE TABLE IF NOT EXISTS project_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_path TEXT NOT NULL,
                file_path TEXT NOT NULL,
                language TEXT,
                role TEXT,
                size_bytes INTEGER DEFAULT 0,
                modified_at TEXT NOT NULL,
                indexed_at TEXT DEFAULT (datetime('now')),
                UNIQUE(project_path, file_path)
            );
            CREATE INDEX IF NOT EXISTS idx_project_files_project
                ON project_files(project_path);
            CREATE INDEX IF NOT EXISTS idx_project_files_lang
                ON project_files(project_path, language);
            CREATE INDEX IF NOT EXISTS idx_project_files_role
                ON project_files(project_path, role);

            -- Codebase index: exported symbols
            CREATE TABLE IF NOT EXISTS file_exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL
                    REFERENCES project_files(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                line_number INTEGER,
                UNIQUE(file_id, name, kind)
            );
            CREATE INDEX IF NOT EXISTS idx_file_exports_file
                ON file_exports(file_id);
            CREATE INDEX IF NOT EXISTS idx_file_exports_name
                ON file_exports(name);

            -- Codebase index: import statements
            CREATE TABLE IF NOT EXISTS file_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL
                    REFERENCES project_files(id) ON DELETE CASCADE,
                import_path TEXT NOT NULL,
                raw_import TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_file_imports_file
                ON file_imports(file_id);
            CREATE INDEX IF NOT EXISTS idx_file_imports_path
                ON file_imports(import_path);
            """
        )
        self.conn.commit()

    # ── Pattern operations ───────────────────────────────────────────────

    def store_pattern(
        self,
        name: str,
        context: str,
        approach: str,
        outcome: str,
        project: str | None = None,
    ) -> int:
        """Store a new pattern with its embedding.  Returns the new row id."""
        text = f"{name} {context} {approach}"
        embedding = self.model.embed(text)
        emb_blob = embedding.tobytes()

        cursor = self.conn.execute(
            "INSERT INTO patterns (name, context, approach, outcome, project, embedding) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, context, approach, outcome, project, emb_blob),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def search_patterns(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        project: str | None = None,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> list[dict]:
        """Semantic search over stored patterns.

        Returns a list of dicts with keys ``id``, ``name``, ``context``,
        ``approach``, ``outcome``, ``score``.
        """
        query_embedding = self.model.embed(query)

        if project:
            rows = self.conn.execute(
                "SELECT id, embedding, name, context, approach, outcome "
                "FROM patterns WHERE project = ? OR project IS NULL",
                (project,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id, embedding, name, context, approach, outcome "
                "FROM patterns"
            ).fetchall()

        # Build lookup dict and stored embeddings list in a single pass.
        metadata_by_id: dict[int, dict] = {}
        stored = []
        for row in rows:
            rid, emb_blob, name, context_val, approach_val, outcome_val = row
            metadata_by_id[rid] = {
                "name": name,
                "context": context_val,
                "approach": approach_val,
                "outcome": outcome_val,
            }
            stored.append((rid, np.frombuffer(emb_blob, dtype=np.float32)))

        matches = search_similar(query_embedding, stored, top_k, min_score)

        results: list[dict] = []
        matched_ids: list[int] = []
        for id_, score in matches:
            meta = metadata_by_id.get(id_)
            if meta:
                matched_ids.append(id_)
                results.append(
                    {
                        "id": id_,
                        "name": meta["name"],
                        "context": meta["context"],
                        "approach": meta["approach"],
                        "outcome": meta["outcome"],
                        "score": round(score, 3),
                    }
                )

        # Batch-update match metadata for all matched patterns.
        for id_ in matched_ids:
            self.conn.execute(
                "UPDATE patterns SET last_matched_at = datetime('now'), "
                "match_count = match_count + 1 WHERE id = ?",
                (id_,),
            )
        self.conn.commit()
        return results

    def prune(
        self,
        max_age_days: int = 90,
    ) -> int:
        """Remove old patterns that have never been matched.

        Returns the number of pruned rows.
        """
        cursor = self.conn.execute(
            "DELETE FROM patterns WHERE "
            "created_at < datetime('now', ? || ' days') AND match_count = 0",
            (f"-{max_age_days}",),
        )
        pruned = cursor.rowcount
        self.conn.commit()
        return pruned

    def get_pattern_count(self) -> int:
        """Return the total number of stored patterns."""
        row = self.conn.execute("SELECT COUNT(*) FROM patterns").fetchone()
        return row[0] if row else 0

    def get_db_size(self) -> int:
        """Return the database file size in bytes, or 0 if not found."""
        try:
            return os.path.getsize(self.db_path)
        except OSError:
            return 0
