"""Memory system: episodic, semantic, and working memory management."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from collections import OrderedDict
import hashlib

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("memory")


@dataclass
class EpisodicMemory:
    """Represents a stored interaction."""

    session_id: str
    module: str
    query: str
    response: str
    confidence: float = 0.5
    outcome: Optional[str] = None
    outcome_score: Optional[float] = None
    id: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None


@dataclass
class SemanticMemory:
    """Represents a stored fact or rule."""

    module: str
    category: str
    key: str
    value: str
    confidence: float = 0.5
    source: str = "system"
    tags: list[str] = field(default_factory=list)
    id: Optional[int] = None
    use_count: int = 0


class MemoryManager:
    """
    Manages episodic, semantic, and working memory.

    - Episodic: Full interaction history stored in SQLite
    - Semantic: Knowledge facts/rules stored in SQLite
    - Working: In-memory LRU cache for current session context
    """

    def __init__(self, database: Database) -> None:
        self._db = database
        self._working_memory: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        self._max_working: int = 20

    # === Episodic Memory ===

    async def store_episodic(self, memory: EpisodicMemory) -> int:
        """
        Store an episodic memory.

        Args:
            memory: The episodic memory to store.

        Returns:
            The ID of the stored memory.
        """
        cursor = await self._db.execute(
            """
            INSERT INTO episodic_memory (session_id, module, query, response, confidence, outcome, outcome_score, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory.session_id,
                memory.module,
                memory.query,
                memory.response,
                memory.confidence,
                memory.outcome,
                memory.outcome_score,
                json.dumps(memory.metadata),
            ),
        )
        await self._db.commit()

        # Update working memory
        await self._add_to_working(memory.session_id, {
            "query": memory.query,
            "response": memory.response,
            "timestamp": time.time(),
        })

        logger.debug(f"Stored episodic memory for session {memory.session_id}")
        return cursor.lastrowid or 0

    async def get_episodic(
        self,
        session_id: Optional[str] = None,
        module: Optional[str] = None,
        limit: int = 50,
    ) -> list[EpisodicMemory]:
        """
        Retrieve episodic memories with optional filtering.

        Args:
            session_id: Filter by session.
            module: Filter by module.
            limit: Maximum results.

        Returns:
            List of episodic memories.
        """
        query = "SELECT * FROM episodic_memory WHERE 1=1"
        params: list[Any] = []

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        if module:
            query += " AND module = ?"
            params.append(module)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = await self._db.fetchall(query, tuple(params))
        return [
            EpisodicMemory(
                id=row["id"],
                session_id=row["session_id"],
                module=row["module"],
                query=row["query"],
                response=row["response"],
                confidence=row["confidence"],
                outcome=row["outcome"],
                outcome_score=row["outcome_score"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def update_episodic_outcome(
        self,
        memory_id: int,
        outcome: str,
        score: float,
    ) -> None:
        """Update the outcome of a past interaction."""
        await self._db.execute(
            """
            UPDATE episodic_memory
            SET outcome = ?, outcome_score = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (outcome, score, memory_id),
        )
        await self._db.commit()

    async def delete_episodic(self, memory_id: int) -> bool:
        """Delete an episodic memory by ID."""
        cursor = await self._db.execute(
            "DELETE FROM episodic_memory WHERE id = ?",
            (memory_id,),
        )
        await self._db.commit()
        return (cursor.rowcount or 0) > 0

    async def count_episodic(self) -> int:
        """Get total count of episodic memories."""
        return await self._db.fetchval(
            "SELECT COUNT(*) FROM episodic_memory"
        ) or 0

    # === Semantic Memory ===

    async def store_semantic(self, memory: SemanticMemory) -> int:
        """
        Store or update a semantic memory.

        Args:
            memory: The semantic memory to store.

        Returns:
            The ID of the stored memory.
        """
        tags_json = json.dumps(memory.tags)
        cursor = await self._db.execute(
            """
            INSERT INTO semantic_memory (module, category, key, value, confidence, source, tags, use_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(module, category, key) DO UPDATE SET
                value = excluded.value,
                confidence = excluded.confidence,
                source = excluded.source,
                tags = excluded.tags,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                memory.module,
                memory.category,
                memory.key,
                memory.value,
                memory.confidence,
                memory.source,
                tags_json,
                memory.use_count,
            ),
        )
        await self._db.commit()
        return cursor.lastrowid or 0

    async def get_semantic(
        self,
        module: Optional[str] = None,
        category: Optional[str] = None,
        key: Optional[str] = None,
        limit: int = 50,
    ) -> list[SemanticMemory]:
        """
        Retrieve semantic memories with filtering.

        Args:
            module: Filter by module.
            category: Filter by category.
            key: Filter by key.
            limit: Maximum results.

        Returns:
            List of semantic memories.
        """
        query = "SELECT * FROM semantic_memory WHERE 1=1"
        params: list[Any] = []

        if module:
            query += " AND module = ?"
            params.append(module)

        if category:
            query += " AND category = ?"
            params.append(category)

        if key:
            query += " AND key = ?"
            params.append(key)

        query += " ORDER BY confidence DESC, use_count DESC LIMIT ?"
        params.append(limit)

        rows = await self._db.fetchall(query, tuple(params))
        return [
            SemanticMemory(
                id=row["id"],
                module=row["module"],
                category=row["category"],
                key=row["key"],
                value=row["value"],
                confidence=row["confidence"],
                source=row["source"],
                tags=json.loads(row["tags"]) if row["tags"] else [],
                use_count=row["use_count"],
            )
            for row in rows
        ]

    async def delete_semantic(self, memory_id: int) -> bool:
        """Delete a semantic memory by ID."""
        cursor = await self._db.execute(
            "DELETE FROM semantic_memory WHERE id = ?",
            (memory_id,),
        )
        await self._db.commit()
        return (cursor.rowcount or 0) > 0

    async def increment_use_count(self, memory_id: int) -> None:
        """Increment the use count for a semantic memory."""
        await self._db.execute(
            "UPDATE semantic_memory SET use_count = use_count + 1 WHERE id = ?",
            (memory_id,),
        )
        await self._db.commit()

    # === Working Memory ===

    async def _add_to_working(
        self,
        session_id: str,
        entry: dict[str, Any],
    ) -> None:
        """Add entry to working memory for a session."""
        if session_id not in self._working_memory:
            self._working_memory[session_id] = []

        self._working_memory[session_id].append(entry)

        # Trim to max size
        if len(self._working_memory[session_id]) > self._max_working:
            self._working_memory[session_id] = self._working_memory[session_id][-self._max_working:]

    async def get_working(self, session_id: str) -> list[dict[str, Any]]:
        """
        Get working memory for a session.

        Args:
            session_id: Session identifier.

        Returns:
            List of recent entries for the session.
        """
        return self._working_memory.get(session_id, [])

    async def clear_working(self, session_id: str) -> None:
        """Clear working memory for a session."""
        if session_id in self._working_memory:
            del self._working_memory[session_id]

    async def create_session(self, session_id: str, module: str = "general") -> None:
        """Create a new session entry."""
        await self._db.execute(
            """
            INSERT OR REPLACE INTO sessions (id, module, message_count, started_at, last_active)
            VALUES (?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (session_id, module),
        )
        await self._db.commit()

    async def increment_session_messages(self, session_id: str) -> None:
        """Increment message count for a session."""
        await self._db.execute(
            """
            UPDATE sessions
            SET message_count = message_count + 1, last_active = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (session_id,),
        )
        await self._db.commit()
