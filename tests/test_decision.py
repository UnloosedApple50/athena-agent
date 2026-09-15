"""Tests for the decision engine."""

from __future__ import annotations

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from athena.core.memory import MemoryManager, SemanticMemory
from athena.core.retrieval import RetrievalEngine
from athena.core.decision import DecisionEngine, Decision
from athena.db.database import Database
from athena.db.migrations import init_schema
from athena.models.llm import LLMClient


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[Database, None]:
    """Create in-memory test database."""
    database = Database(":memory:")
    await database.initialize()
    await init_schema(database)
    yield database
    await database.close()


@pytest_asyncio.fixture
async def engine(db: Database) -> AsyncGenerator[DecisionEngine, None]:
    """Create a decision engine with rule-based fallback."""
    memory = MemoryManager(db)
    retrieval = RetrievalEngine(memory)

    # Create mock LLM client (unavailable)
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.is_available = False

    decision_engine = DecisionEngine(memory, retrieval, mock_llm)
    yield decision_engine


class TestDecisionEngine:
    """Tests for the decision engine."""

    @pytest.mark.asyncio
    async def test_analyze_sales_pricing(self, engine: DecisionEngine) -> None:
        """Test sales pricing query produces recommendation."""
        decision = await engine.analyze(
            query="What discount should I offer for a $500K enterprise deal?",
            module="sales",
        )

        assert isinstance(decision, Decision)
        assert decision.module == "sales"
        assert len(decision.recommendation) > 0
        assert 0.0 <= decision.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_sales_objection(self, engine: DecisionEngine) -> None:
        """Test sales objection handling query."""
        decision = await engine.analyze(
            query="How do I handle pushback from procurement?",
            module="sales",
        )

        assert decision.module == "sales"
        assert len(decision.recommendation) > 0

    @pytest.mark.asyncio
    async def test_analyze_sales_closing(self, engine: DecisionEngine) -> None:
        """Test sales closing strategy query."""
        decision = await engine.analyze(
            query="What are the best techniques to close a deal this quarter?",
            module="sales",
        )

        assert "close" in decision.recommendation.lower() or "closing" in decision.recommendation.lower() or len(decision.recommendation) > 20

    @pytest.mark.asyncio
    async def test_analyze_trading_risk(self, engine: DecisionEngine) -> None:
        """Test trading risk management query."""
        decision = await engine.analyze(
            query="What stop loss should I use for a volatile stock?",
            module="trading",
        )

        assert decision.module == "trading"
        assert len(decision.recommendation) > 0

    @pytest.mark.asyncio
    async def test_analyze_trading_trend(self, engine: DecisionEngine) -> None:
        """Test trading trend analysis query."""
        decision = await engine.analyze(
            query="How do I identify a strong trend for entry?",
            module="trading",
        )

        assert decision.module == "trading"
        assert len(decision.recommendation) > 0

    @pytest.mark.asyncio
    async def test_analyze_general(self, engine: DecisionEngine) -> None:
        """Test general module query."""
        decision = await engine.analyze(
            query="What should I consider for long-term investment?",
            module="general",
        )

        assert decision.module == "general"
        assert len(decision.recommendation) > 0

    @pytest.mark.asyncio
    async def test_decision_has_reasoning(self, engine: DecisionEngine) -> None:
        """Test that decisions include reasoning."""
        decision = await engine.analyze("test query", module="sales")

        assert len(decision.reasoning) > 0

    @pytest.mark.asyncio
    async def test_decision_to_dict(self, engine: DecisionEngine) -> None:
        """Test decision serialization."""
        decision = await engine.analyze("test query", module="sales")
        d = decision.to_dict()

        assert "context" in d
        assert "recommendation" in d
        assert "confidence" in d
        assert "reasoning" in d
        assert "module" in d
        assert isinstance(d["options"], list)
        assert isinstance(d["risks"], list)

    @pytest.mark.asyncio
    async def test_evaluate_options(self, engine: DecisionEngine) -> None:
        """Test evaluating multiple options."""
        decision = await engine.evaluate_options(
            context="Client wants 30% discount on enterprise deal",
            options=["Hold firm at 15%", "Meet at 25%", "Offer phased discount over 3 years"],
            module="sales",
        )

        assert isinstance(decision, Decision)
        assert decision.options is not None
        assert len(decision.options) == 3

    @pytest.mark.asyncio
    async def test_confidence_in_valid_range(self, engine: DecisionEngine) -> None:
        """Test that confidence is always between 0 and 1."""
        queries = [
            ("How do I negotiate?", "sales"),
            ("Risk management?", "trading"),
            ("Compound interest?", "general"),
        ]

        for query, module in queries:
            decision = await engine.analyze(query, module=module)
            assert 0.0 <= decision.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_rule_matching(self, engine: DecisionEngine) -> None:
        """Test that rules match expected patterns."""
        # Sales discount/pricing rule
        decision = await engine.analyze("How to handle discount request?", module="sales")
        assert decision.confidence >= 0.4  # At least generic confidence

    @pytest.mark.asyncio
    async def test_no_match_returns_generic(self, engine: DecisionEngine) -> None:
        """Test query with no pattern match returns generic guidance."""
        decision = await engine.analyze(
            "xyzabc completely unrelated random text",
            module="sales",
        )

        # Should still return a decision, possibly with lower confidence
        assert isinstance(decision, Decision)
        assert decision.confidence <= 0.6  # Lower confidence expected


class TestDecisionEngineWithLLM:
    """Tests for decision engine with LLM (mocked)."""

    @pytest.mark.asyncio
    async def test_llm_decision(self, db: Database) -> None:
        """Test decision with available LLM."""
        memory = MemoryManager(db)
        retrieval = RetrievalEngine(memory)

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.is_available = True

        # Mock the generate method
        mock_response = MagicMock()
        mock_response.content = "Recommendation: Use value-based pricing. Anchor to ROI data."
        mock_response.confidence = 0.85
        mock_llm.generate = AsyncMock(return_value=mock_response)

        engine = DecisionEngine(memory, retrieval, mock_llm)

        decision = await engine.analyze(
            "How should I price our enterprise solution?",
            module="sales",
        )

        assert decision.module == "sales"
        assert len(decision.recommendation) > 0
        # LLM was called
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_fallback_on_error(self, db: Database) -> None:
        """Test fallback to rules when LLM fails."""
        memory = MemoryManager(db)
        retrieval = RetrievalEngine(memory)

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.is_available = True
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM timeout"))

        engine = DecisionEngine(memory, retrieval, mock_llm)

        decision = await engine.analyze(
            "How do I handle pricing objections?",
            module="sales",
        )

        # Should still return a decision via rule fallback
        assert isinstance(decision, Decision)
        assert decision.confidence > 0
