"""Tests for training module."""

from __future__ import annotations

import pytest
import pytest_asyncio
from athena.training.feedback import FeedbackManager, FeedbackEntry
from athena.training.adaptation import AdaptationManager, AdaptationRule


class TestFeedbackManager:
    """Tests for FeedbackManager."""

    def test_init(self):
        manager = FeedbackManager()
        assert manager is not None

    @pytest.mark.asyncio
    async def test_submit_feedback(self):
        manager = FeedbackManager()
        entry = await manager.submit_feedback(
            memory_id=1,
            rating=4,
            correction="Better response",
            comment="Good but could improve",
        )
        assert isinstance(entry, FeedbackEntry)
        assert entry.rating == 4
        assert entry.correction == "Better response"

    @pytest.mark.asyncio
    async def test_submit_feedback_thumbs(self):
        manager = FeedbackManager()
        # rating 1 stays as 1
        entry = await manager.submit_feedback(memory_id=1, rating=1)
        assert entry.rating == 1

        # rating -1 becomes 1 (clamped)
        entry2 = await manager.submit_feedback(memory_id=2, rating=-1)
        assert entry2.rating == 1

    @pytest.mark.asyncio
    async def test_get_feedback_history(self):
        manager = FeedbackManager()
        await manager.submit_feedback(memory_id=1, rating=5)
        await manager.submit_feedback(memory_id=2, rating=3)
        history = await manager.get_feedback_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_feedback_stats(self):
        manager = FeedbackManager()
        await manager.submit_feedback(memory_id=1, rating=5)
        await manager.submit_feedback(memory_id=2, rating=1)
        stats = await manager.get_feedback_stats()
        assert stats["total_feedback"] == 2
        assert stats["avg_rating"] == 3.0

    @pytest.mark.asyncio
    async def test_get_corrections(self):
        manager = FeedbackManager()
        await manager.submit_feedback(memory_id=1, rating=2, correction="Fix this")
        await manager.submit_feedback(memory_id=2, rating=5)
        corrections = await manager.get_corrections()
        assert len(corrections) == 1


class TestAdaptationManager:
    """Tests for AdaptationManager."""

    def test_init(self):
        manager = AdaptationManager()
        assert manager is not None

    @pytest.mark.asyncio
    async def test_analyze_feedback(self):
        manager = AdaptationManager()
        feedback = [
            {"id": "fb1", "module": "sales", "rating": 1, "correction": "Fix"},
            {"id": "fb2", "module": "sales", "rating": 2, "correction": "Fix2"},
            {"id": "fb3", "module": "sales", "rating": 5},
        ]
        rules = await manager.analyze_feedback(feedback)
        assert len(rules) > 0

    @pytest.mark.asyncio
    async def test_apply_adaptations(self):
        manager = AdaptationManager()
        await manager.analyze_feedback([
            {"id": "fb1", "module": "sales", "rating": 1, "correction": "Fix"},
        ])
        result = await manager.apply_adaptations()
        assert "total_rules" in result

    def test_get_rules(self):
        manager = AdaptationManager()
        rules = manager.get_rules()
        assert isinstance(rules, list)

    def test_remove_rule(self):
        manager = AdaptationManager()
        assert manager.remove_rule("nonexistent") is False

    def test_get_stats(self):
        manager = AdaptationManager()
        stats = manager.get_stats()
        assert "total_rules" in stats
