"""Memory service — read/update/delete from Memori fact tables."""

import sqlite3

from app.config import settings


class MemoryService:
    """Manages memory facts stored by Memori in the shared SQLite database."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.DB_PATH

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_all_facts(self) -> list[dict]:
        """Read all facts from memori_entity_fact, grouped by type."""
        conn = self._get_conn()
        try:
            # Check if the table exists first
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memori_entity_fact'"
            )
            if not cursor.fetchone():
                return []

            rows = conn.execute(
                "SELECT * FROM memori_entity_fact ORDER BY created_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_facts_grouped(self) -> dict[str, list[dict]]:
        """Get facts grouped by their type/category."""
        facts = self.get_all_facts()
        groups: dict[str, list[dict]] = {}

        for fact in facts:
            fact_type = fact.get("type", "general")
            if fact_type not in groups:
                groups[fact_type] = []
            groups[fact_type].append(fact)

        return groups

    def update_fact(self, fact_id: int, content: str) -> dict | None:
        """Update a single memory fact's content."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memori_entity_fact'"
            )
            if not cursor.fetchone():
                return None

            conn.execute(
                "UPDATE memori_entity_fact SET content = ? WHERE id = ?",
                (content, fact_id),
            )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM memori_entity_fact WHERE id = ?", (fact_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_fact(self, fact_id: int) -> bool:
        """Delete a single memory fact."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memori_entity_fact'"
            )
            if not cursor.fetchone():
                return False

            result = conn.execute(
                "DELETE FROM memori_entity_fact WHERE id = ?", (fact_id,)
            )
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()

    def wipe_all(self, confirmation: str) -> bool:
        """Delete all rows from Memori tables. Requires explicit confirmation."""
        if confirmation != "DELETE_ALL":
            return False

        conn = self._get_conn()
        try:
            memori_tables = [
                "memori_entity_fact",
                "memori_knowledge_graph",
                "memori_conversation_message",
                "memori_process_attribute",
            ]

            for table in memori_tables:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                if cursor.fetchone():
                    conn.execute(f"DELETE FROM {table}")  # Table name from hardcoded list

            conn.commit()
            return True
        finally:
            conn.close()
