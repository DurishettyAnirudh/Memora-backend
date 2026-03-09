"""Entity resolver — resolves named references using Memori stored facts."""

from dataclasses import dataclass

from app.ai.client import get_memori


@dataclass
class ResolvedEntity:
    name: str
    resolved_to: str
    entity_type: str  # person, place, thing, event
    confidence: float


class EntityResolver:
    """Resolves ambiguous entity mentions using Memori's stored facts."""

    def resolve(self, entity_mention: str) -> ResolvedEntity | None:
        """
        Try to resolve an entity mention using stored Memori facts.
        e.g., "the mansion" → "uncle's property at 123 Oak Lane"
        """
        mem = get_memori()
        if mem is None:
            return None

        try:
            # Use Memori's recall to search for matching facts
            # This searches across all entity facts
            facts = self._search_facts(entity_mention)

            if not facts:
                return None

            # Return the best match
            best = facts[0]
            return ResolvedEntity(
                name=entity_mention,
                resolved_to=best.get("content", ""),
                entity_type=best.get("type", "thing"),
                confidence=best.get("confidence", 0.7),
            )
        except Exception:
            return None

    def resolve_many(self, mentions: list[str]) -> dict[str, ResolvedEntity | None]:
        """Resolve multiple entity mentions."""
        return {mention: self.resolve(mention) for mention in mentions}

    def _search_facts(self, query: str) -> list[dict]:
        """Search Memori entity facts for a query string."""
        import sqlite3
        from app.config import settings

        conn = sqlite3.connect(settings.DB_PATH)
        conn.row_factory = sqlite3.Row

        try:
            # Check if table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memori_entity_fact'"
            )
            if not cursor.fetchone():
                return []

            search_term = f"%{query}%"
            rows = conn.execute(
                "SELECT * FROM memori_entity_fact WHERE content LIKE ? LIMIT 5",
                (search_term,),
            ).fetchall()

            return [dict(r) for r in rows]
        finally:
            conn.close()
