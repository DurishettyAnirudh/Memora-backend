"""Search service — FTS5 full-text search across tasks."""

import sqlite3

from app.config import settings


class SearchService:
    """SQLite FTS5 search across tasks."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.DB_PATH

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def search_tasks(self, query: str, limit: int = 20) -> list[dict]:
        """FTS5 MATCH query with snippet extraction and rank ordering."""
        if not query or not query.strip():
            return []

        conn = self._get_conn()
        try:
            # Check if FTS table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks_fts'"
            )
            if not cursor.fetchone():
                # Fallback to LIKE search if FTS not available
                return self._fallback_search(conn, query, limit)

            # Use parameterized FTS5 MATCH query
            rows = conn.execute(
                """
                SELECT t.*, snippet(tasks_fts, 0, '<b>', '</b>', '...', 32) AS title_snippet,
                       snippet(tasks_fts, 1, '<b>', '</b>', '...', 64) AS desc_snippet,
                       rank
                FROM tasks_fts
                JOIN tasks t ON t.id = tasks_fts.rowid
                WHERE tasks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()

            return [
                {
                    **dict(row),
                    "title_snippet": row["title_snippet"],
                    "description_snippet": row["desc_snippet"],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def _fallback_search(
        self, conn: sqlite3.Connection, query: str, limit: int
    ) -> list[dict]:
        """LIKE-based fallback when FTS table doesn't exist."""
        search_term = f"%{query}%"
        rows = conn.execute(
            """
            SELECT * FROM tasks
            WHERE title LIKE ? OR description LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (search_term, search_term, limit),
        ).fetchall()

        return [dict(row) for row in rows]

    def rebuild_index(self) -> bool:
        """Rebuild the FTS5 index from the tasks table."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks_fts'"
            )
            if not cursor.fetchone():
                return False

            conn.execute("INSERT INTO tasks_fts(tasks_fts) VALUES('rebuild')")
            conn.commit()
            return True
        finally:
            conn.close()
