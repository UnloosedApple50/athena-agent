"""Feedback collection and management for agent training."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("training.feedback")


@dataclass
class FeedbackEntry:
    """User feedback on a response."""

    id: str
    memory_id: int
    rating: int  # 1-5 or -1 (down) / 1 (up)
    correction: Optional[str] = None
    comment: Optional[str] = None
    category: str = "general"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: Optional[str] = None
    module: str = "general"
    original_query: Optional[str] = None
    original_response: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "memory_id": self.memory_id,
            "rating": self.rating,
            "correction": self.correction,
            "comment": self.comment,
            "category": self.category,
            "session_id": self.session_id,
            "module": self.module,
            "original_query": self.original_query,
            "original_response": self.original_response,
            "created_at": self.created_at,
        }


class FeedbackManager:
    """Collects and manages user feedback for agent improvement."""

    def __init__(self, database: Optional[Database] = None) -> None:
        self._db = database
        self._feedback: dict[str, FeedbackEntry] = {}
        self._count: int = 0
        self._positive_count: int = 0
        self._negative_count: int = 0

    async def submit_feedback(
        self,
        memory_id: int,
        rating: int,
        correction: Optional[str] = None,
        comment: Optional[str] = None,
        category: str = "general",
        session_id: Optional[str] = None,
        module: str = "general",
        original_query: Optional[str] = None,
        original_response: Optional[str] = None,
    ) -> FeedbackEntry:
        """
        Submit feedback on a response.
        
        Args:
            memory_id: ID of the episodic memory being rated.
            rating: Rating (1-5) or thumbs (-1/1).
            correction: Optional corrected response text.
            comment: Optional comment.
            category: Feedback category.
            session_id: Session ID.
            module: Module context.
            original_query: Original user query.
            original_response: Original agent response.
            
        Returns:
            FeedbackEntry instance.
        """
        feedback_id = f"fb_{uuid.uuid4().hex[:12]}"

        # Normalize rating to 1-5 scale
        normalized_rating = max(1, min(5, rating))

        entry = FeedbackEntry(
            id=feedback_id,
            memory_id=memory_id,
            rating=normalized_rating,
            correction=correction,
            comment=comment,
            category=category,
            session_id=session_id,
            module=module,
            original_query=original_query,
            original_response=original_response,
        )

        self._feedback[feedback_id] = entry
        self._count += 1

        if normalized_rating >= 3:
            self._positive_count += 1
        else:
            self._negative_count += 1

        # Persist to database
        if self._db and self._db.is_connected:
            try:
                await self._db.execute(
                    """
                    INSERT INTO training_feedback 
                    (id, memory_id, rating, correction, comment, category,
                     session_id, module, original_query, original_response, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        feedback_id, memory_id, normalized_rating,
                        correction, comment, category,
                        session_id, module, original_query, original_response,
                        entry.created_at,
                    ),
                )
                await self._db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist feedback: {e}")

        logger.info(f"Feedback submitted: {feedback_id} (rating={normalized_rating})")
        return entry

    async def get_feedback_history(
        self,
        session_id: Optional[str] = None,
        module: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get feedback history with optional filtering.
        
        Args:
            session_id: Filter by session.
            module: Filter by module.
            limit: Maximum results.
            
        Returns:
            List of feedback dictionaries.
        """
        feedbacks = list(self._feedback.values())

        if session_id:
            feedbacks = [f for f in feedbacks if f.session_id == session_id]
        if module:
            feedbacks = [f for f in feedbacks if f.module == module]

        feedbacks.sort(key=lambda f: f.created_at, reverse=True)
        return [f.to_dict() for f in feedbacks[:limit]]

    async def get_feedback_stats(self) -> dict[str, Any]:
        """Get feedback statistics."""
        ratings = [f.rating for f in self._feedback.values()]

        return {
            "total_feedback": self._count,
            "positive": self._positive_count,
            "negative": self._negative_count,
            "neutral": self._count - self._positive_count - self._negative_count,
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
            "categories": self._count_by("category"),
            "modules": self._count_by("module"),
        }

    def _count_by(self, field_name: str) -> dict[str, int]:
        """Count feedback by a field."""
        counts: dict[str, int] = {}
        for f in self._feedback.values():
            value = getattr(f, field_name, "general")
            counts[value] = counts.get(value, 0) + 1
        return counts

    async def get_corrections(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get all feedback entries that include corrections."""
        corrections = [
            f.to_dict()
            for f in self._feedback.values()
            if f.correction is not None
        ]
        corrections.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        return corrections[:limit]

    async def load_from_db(self) -> int:
        """Load feedback history from database."""
        if not self._db or not self._db.is_connected:
            return 0

        try:
            rows = await self._db.fetchall("SELECT * FROM training_feedback ORDER BY created_at DESC LIMIT 1000")
            count = 0
            for row in rows:
                entry = FeedbackEntry(
                    id=row["id"] if isinstance(row["id"], str) else row[0],
                    memory_id=row["memory_id"] if isinstance(row["memory_id"], int) else row[1],
                    rating=row["rating"] if isinstance(row["rating"], int) else row[2],
                    correction=row["correction"] if isinstance(row["correction"], str) else row[3],
                    comment=row["comment"] if isinstance(row["comment"], str) else row[4],
                    category=row["category"] if isinstance(row["category"], str) else row[5],
                    session_id=row["session_id"] if isinstance(row["session_id"], str) else row[6],
                    module=row["module"] if isinstance(row["module"], str) else row[7],
                    original_query=row["original_query"] if isinstance(row["original_query"], str) else row[8],
                    original_response=row["original_response"] if isinstance(row["original_response"], str) else row[9],
                    created_at=row["created_at"] if isinstance(row["created_at"], str) else row[10],
                )
                self._feedback[entry.id] = entry
                count += 1
            return count
        except Exception as e:
            logger.warning(f"Failed to load feedback from db: {e}")
            return 0


# Global instance
feedback_manager = FeedbackManager()
