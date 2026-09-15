"""Tests for the retrieval engine."""

from __future__ import annotations

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from athena.core.memory import MemoryManager, SemanticMemory
from athena.core.retrieval import RetrievalEngine
from athena.db.database import Database
from athena.db.migrations import init_schema


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[Database, None]:
    """Create in-memory test database."""
    database = Database(":memory:")
    await database.initialize()
    await init_schema(database)
    yield database
    await database.close()


@pytest_asyncio.fixture
async def populated_db(db: Database) -> AsyncGenerator[Database, None]:
    """Create a database pre-populated with test knowledge."""
    manager = MemoryManager(db)

    # Add semantic knowledge
    knowledge_items = [
        SemanticMemory(
            module="sales", category="closing", key="assumptive_close",
            value="Proceed as if the prospect has already decided to buy. Use phrases like 'When would we start implementation?'",
            confidence=0.9, tags=["closing", "tactic"],
        ),
        SemanticMemory(
            module="sales", category="negotiation", key="anchoring",
            value="The first number put on the table disproportionately influences the final outcome. Always anchor aggressively but credibly.",
            confidence=0.95, tags=["negotiation", "anchoring"],
        ),
        SemanticMemory(
            module="sales", category="objection_handling", key="feel_felt_found",
            value="I understand how you feel. Others have felt the same way. What they found was...",
            confidence=0.8, tags=["objections", "reframing"],
        ),
        SemanticMemory(
            module="trading", category="risk_management", key="position_sizing",
            value="Risk no more than 1-2% of total capital on any single trade. Use the formula: Position Size = Account Risk / Stop Distance.",
            confidence=0.95, tags=["risk", "position_sizing"],
        ),
        SemanticMemory(
            module="trading", category="technical", key="trend_confirmation",
            value="Use multiple timeframes for trend confirmation. Price above 20, 50, and 200 EMA indicates strong uptrend.",
            confidence=0.85, tags=["trend", "ema", "technical"],
        ),
        SemanticMemory(
            module="general", category="finance", key="compound_interest",
            value="Rule of 72: divide 72 by annual return rate to get doubling time. At 8% returns, money doubles every 9 years.",
            confidence=0.95, tags=["finance", "compound"],
        ),
    ]

    for item in knowledge_items:
        await manager.store_semantic(item)

    yield db


class TestRetrievalEngine:
    """Tests for context retrieval."""

    @pytest.mark.asyncio
    async def test_retrieve_from_empty_memory(self, db: Database) -> None:
        """Test retrieval from empty memory returns empty list."""
        manager = MemoryManager(db)
        engine = RetrievalEngine(manager)

        results = await engine.retrieve("any query", module="sales")
        assert results == []

    @pytest.mark.asyncio
    async def test_extract_keywords(self, populated_db: Database) -> None:
        """Test keyword extraction."""
        manager = MemoryManager(populated_db)
        engine = RetrievalEngine(manager)

        keywords = engine._extract_keywords("How do I handle price objections in sales?")
        assert "handle" in keywords
        assert "price" in keywords
        assert "objections" in keywords
        assert "sales" in keywords

        # Stop words should be removed
        assert "how" not in keywords
        assert "do" not in keywords

    @pytest.mark.asyncio
    async def test_keyword_score(self, populated_db: Database) -> None:
        """Test keyword scoring."""
        manager = MemoryManager(populated_db)
        engine = RetrievalEngine(manager)

        score = engine._keyword_score(["price", "strategy"], "This pricing strategy guide covers competitive pricing and price optimization.")
        assert score > 0.0

        score_no_match = engine._keyword_score(["xyz123"], "Completely unrelated text about trading")
        assert score_no_match == 0.0

    @pytest.mark.asyncio
    async def test_retrieve_results_have_relevance(self, populated_db: Database) -> None:
        """Test that results have valid relevance scores."""
        manager = MemoryManager(populated_db)
        engine = RetrievalEngine(manager)

        results = await engine.retrieve("closing strategy", module="sales")

        for r in results:
            assert 0.0 <= r.relevance <= 1.0

    @pytest.mark.asyncio
    async def test_retrieve_results_sorted_by_relevance(self, populated_db: Database) -> None:
        """Test that results are sorted by relevance descending."""
        manager = MemoryManager(populated_db)
        engine = RetrievalEngine(manager)

        results = await engine.retrieve("negotiation tactics", module="sales", top_k=5)

        if len(results) >= 2:
            for i in range(len(results) - 1):
                assert results[i].relevance >= results[i + 1].relevance

    @pytest.mark.asyncio
    async def test_retrieve_with_top_k(self, populated_db: Database) -> None:
        """Test top_k limits results."""
        manager = MemoryManager(populated_db)
        engine = RetrievalEngine(manager)

        results = await engine.retrieve("risk management", top_k=2)

        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_retrieve_returns_correct_fields(self, populated_db: Database) -> None:
        """Test that results contain expected fields."""
        manager = MemoryManager(populated_db)
        engine = RetrievalEngine(manager)

        results = await engine.retrieve("anchoring", module="sales")

        for r in results:
            assert hasattr(r, "source")
            assert hasattr(r, "content")
            assert hasattr(r, "relevance")
            assert hasattr(r, "metadata")
            assert r.source in ("semantic", "episodic")
