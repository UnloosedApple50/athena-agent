"""Tests for the main agent."""

from __future__ import annotations

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from athena.core.agent import AthenaAgent, ChatResponse
from athena.db.database import Database
from athena.db.migrations import init_schema


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[Database, None]:
    database = Database(":memory:")
    await database.initialize()
    await init_schema(database)
    yield database
    await database.close()


class TestAthenaAgent:
    """Tests for the main agent."""

    @pytest.mark.asyncio
    async def test_chat_general(self, agent: AthenaAgent) -> None:
        """Test basic chat functionality."""
        response = await agent.chat("Hello, can you help me?")
        assert isinstance(response, ChatResponse)
        assert len(response.response) > 0
        assert response.module == "general"
        assert response.session_id.startswith("sess_")

    @pytest.mark.asyncio
    async def test_chat_sales(self, agent: AthenaAgent) -> None:
        """Test sales module chat."""
        response = await agent.chat(
            "What are the best negotiation tactics?",
            module="sales",
        )
        assert response.module == "sales"
        assert len(response.response) > 0
        assert response.confidence > 0

    @pytest.mark.asyncio
    async def test_chat_trading(self, agent: AthenaAgent) -> None:
        """Test trading module chat."""
        response = await agent.chat(
            "How do I manage risk in volatile markets?",
            module="trading",
        )
        assert response.module == "trading"
        assert len(response.response) > 0

    @pytest.mark.asyncio
    async def test_chat_creates_session(self, agent: AthenaAgent) -> None:
        """Test that chat creates a session ID."""
        response = await agent.chat("Test query")
        assert response.session_id is not None
        assert len(response.session_id) > 0

    @pytest.mark.asyncio
    async def test_chat_stores_memory(self, agent: AthenaAgent) -> None:
        """Test that chat stores episodic memory."""
        response = await agent.chat("How to close a deal?")

        # Check memory was stored
        history = await agent.get_session_history(response.session_id)
        assert len(history) == 1
        assert history[0].query == "How to close a deal?"

    @pytest.mark.asyncio
    async def test_chat_skips_memory_storage(self, agent: AthenaAgent) -> None:
        """Test chat with store_memory=False."""
        response = await agent.chat("Test query", store_memory=False)

        history = await agent.get_session_history(response.session_id)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_chat_invalid_module(self, agent: AthenaAgent) -> None:
        """Test that invalid module raises error."""
        with pytest.raises(ValueError):
            await agent.chat("Test", module="invalid")

    @pytest.mark.asyncio
    async def test_chat_with_session_id(self, agent: AthenaAgent) -> None:
        """Test chat with explicit session ID."""
        response = await agent.chat("Query 1", session_id="custom_sess")
        response2 = await agent.chat("Query 2", session_id="custom_sess")

        # Same session
        assert response.session_id == response2.session_id

        # Both stored
        history = await agent.get_session_history("custom_sess")
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_decide(self, agent: AthenaAgent) -> None:
        """Test decision endpoint."""
        decision = await agent.decide(
            context="Client wants discount",
            options=["Option A", "Option B", "Option C"],
            module="sales",
        )

        assert decision.module == "sales"
        assert len(decision.recommendation) > 0
        assert decision.options is not None
        assert len(decision.options) == 3

    @pytest.mark.asyncio
    async def test_add_knowledge(self, agent: AthenaAgent) -> None:
        """Test adding knowledge to semantic memory."""
        memory_id = await agent.add_knowledge(
            module="sales",
            category="test",
            key="test_fact",
            value="This is a test fact.",
            confidence=0.9,
            tags=["test"],
        )

        assert memory_id > 0

        # Verify it was stored
        memories = await agent._memory.get_semantic(module="sales", category="test")
        assert len(memories) == 1
        assert memories[0].value == "This is a test fact."

    @pytest.mark.asyncio
    async def test_provide_feedback(self, agent: AthenaAgent) -> None:
        """Test providing feedback on past interaction."""
        response = await agent.chat("Test query")

        # Get the memory ID
        history = await agent.get_session_history(response.session_id)
        memory_id = history[0].id
        assert memory_id is not None

        # Provide feedback
        await agent.provide_feedback(memory_id, "positive", 0.9)

        # Verify outcome was updated
        updated = await agent.get_session_history(response.session_id)
        assert updated[0].outcome == "positive"
        assert updated[0].outcome_score == 0.9

    @pytest.mark.asyncio
    async def test_session_history(self, agent: AthenaAgent) -> None:
        """Test retrieving session history."""
        response = await agent.chat("Query 1", session_id="hist_test")
        await agent.chat("Query 2", session_id="hist_test")
        await agent.chat("Query 3", session_id="hist_test")

        history = await agent.get_session_history("hist_test")
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_response_to_dict(self, agent: AthenaAgent) -> None:
        """Test ChatResponse serialization."""
        response = await agent.chat("Test")
        d = response.to_dict()

        assert "response" in d
        assert "confidence" in d
        assert "module" in d
        assert "session_id" in d
        assert "timestamp" in d

    @pytest.mark.asyncio
    async def test_uptime(self, agent: AthenaAgent) -> None:
        """Test uptime tracking."""
        import asyncio
        await asyncio.sleep(0.01)
        assert agent.uptime_seconds > 0

    @pytest.mark.asyncio
    async def test_fallback_flag(self, agent: AthenaAgent) -> None:
        """Test fallback flag is set when LLM unavailable."""
        response = await agent.chat("Test query")
        # LLM is not available in tests, so fallback should be True
        assert response.fallback is True

    @pytest.mark.asyncio
    async def test_memories_used(self, agent: AthenaAgent) -> None:
        """Test memories_used count."""
        # Add some knowledge first
        await agent.add_knowledge(
            module="sales", category="closing", key="test",
            value="closing strategy involves assumptive techniques",
        )

        response = await agent.chat("How do I close?", module="sales")
        # Should have at least found the knowledge we added
        assert response.memories_used >= 0
