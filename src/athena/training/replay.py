"""Replay past interactions with improved context for training."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from athena.core.agent import AthenaAgent

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("training.replay")


@dataclass
class ReplayResult:
    """Result of a replayed interaction."""

    original_memory_id: int
    original_query: str
    original_response: str
    replayed_response: str
    improved: bool
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    notes: Optional[str] = None


class ReplayManager:
    """Replays past interactions with improved context for training."""

    def __init__(self, database: Optional[Database] = None) -> None:
        self._db = database
        self._replay_history: list[ReplayResult] = []

    async def replay_interaction(
        self,
        memory_id: int,
        agent: Any = None,
    ) -> Optional[ReplayResult]:
        """
        Replay a past interaction with the current (improved) system.
        
        Args:
            memory_id: ID of the episodic memory to replay.
            agent: Optional agent instance to use for replay.
            
        Returns:
            ReplayResult if successful, None if memory not found.
        """
        if not self._db or not self._db.is_connected:
            return None

        try:
            # Fetch original memory
            row = await self._db.fetchone(
                "SELECT * FROM episodic_memory WHERE id = ?",
                (memory_id,),
            )

            if not row:
                return None

            original_query = row["query"] if isinstance(row["query"], str) else row[3]
            original_response = row["response"] if isinstance(row["response"], str) else row[4]
            session_id = row["session_id"] if isinstance(row["session_id"], str) else row[1]
            module = row["module"] if isinstance(row["module"], str) else row[2]

            replayed_response = original_response
            improved = False

            # If agent is provided, replay with it
            if agent is not None:
                try:
                    response = await agent.chat(
                        message=original_query,
                        module=module,
                        session_id=f"replay_{session_id}",
                        store_memory=False,
                    )
                    replayed_response = response.response
                    improved = replayed_response != original_response
                except Exception as e:
                    logger.warning(f"Replay failed for memory {memory_id}: {e}")

            result = ReplayResult(
                original_memory_id=memory_id,
                original_query=original_query,
                original_response=original_response,
                replayed_response=replayed_response,
                improved=improved,
            )

            self._replay_history.append(result)
            return result

        except Exception as e:
            logger.error(f"Error replaying interaction {memory_id}: {e}")
            return None

    async def replay_session(
        self,
        session_id: str,
        agent: Any = None,
        limit: int = 50,
    ) -> list[ReplayResult]:
        """
        Replay all interactions in a session.
        
        Args:
            session_id: Session ID to replay.
            agent: Optional agent instance.
            limit: Maximum interactions to replay.
            
        Returns:
            List of ReplayResult instances.
        """
        if not self._db or not self._db.is_connected:
            return []

        try:
            rows = await self._db.fetchall(
                "SELECT id FROM episodic_memory WHERE session_id = ? ORDER BY created_at LIMIT ?",
                (session_id, limit),
            )

            results: list[ReplayResult] = []
            for row in rows:
                memory_id = row["id"] if isinstance(row["id"], int) else row[0]
                result = await self.replay_interaction(memory_id, agent)
                if result:
                    results.append(result)

            logger.info(f"Replayed {len(results)} interactions from session {session_id}")
            return results

        except Exception as e:
            logger.error(f"Error replaying session {session_id}: {e}")
            return []

    def get_replay_history(self, limit: int = 20) -> list[ReplayResult]:
        """Get replay history."""
        return self._replay_history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get replay statistics."""
        if not self._replay_history:
            return {"total": 0, "improved": 0, "unchanged": 0}

        improved = sum(1 for r in self._replay_history if r.improved)
        return {
            "total": len(self._replay_history),
            "improved": improved,
            "unchanged": len(self._replay_history) - improved,
        }


# Global instance
replay_manager = ReplayManager()
