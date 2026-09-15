"""Tests for the memory system."""

from __future__ import annotations

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from athena.core.memory import MemoryManager, EpisodicMemory, SemanticMemory
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
async def manager(db: Database) -> AsyncGenerator[MemoryManager, None]:
    """Create memory manager."""
    mem = MemoryManager(db)
    yield mem


class TestEpisodicMemory:
    """Tests for episodic memory CRUD operations."""

    @pytest.mark.asyncio
    async def test_store_episodic(self, manager: MemoryManager) -> None:
        """Test storing an episodic memory."""
        memory = EpisodicMemory(
            session_id="test_session_1",
            module="sales",
            query="How do I handle price objections?",
            response="Use the feel-felt-found framework.",
            confidence=0.85,
        )

        memory_id = await manager.store_episodic(memory)
        assert memory_id > 0

    @pytest.mark.asyncio
    async def test_get_episodic_by_session(self, manager: MemoryManager) -> None:
        """Test retrieving episodic memories by session ID."""
        # Store multiple memories
        for i in range(3):
            await manager.store_episodic(EpisodicMemory(
                session_id="session_a",
                module="sales",
                query=f"Question {i}",
                response=f"Answer {i}",
                confidence=0.8,
            ))

        for i in range(2):
            await manager.store_episodic(EpisodicMemory(
                session_id="session_b",
                module="trading",
                query=f"Trade question {i}",
                response=f"Trade answer {i}",
                confidence=0.9,
            ))

        # Retrieve by session
        results = await manager.get_episodic(session_id="session_a")
        assert len(results) == 3

        results = await manager.get_episodic(session_id="session_b")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_episodic_by_module(self, manager: MemoryManager) -> None:
        """Test retrieving episodic memories by module."""
        await manager.store_episodic(EpisodicMemory(
            session_id="s1", module="sales", query="q1", response="a1",
        ))
        await manager.store_episodic(EpisodicMemory(
            session_id="s2", module="trading", query="q2", response="a2",
        ))
        await manager.store_episodic(EpisodicMemory(
            session_id="s3", module="sales", query="q3", response="a3",
        ))

        results = await manager.get_episodic(module="sales")
        assert len(results) == 2

        results = await manager.get_episodic(module="trading")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_episodic_with_limit(self, manager: MemoryManager) -> None:
        """Test limit parameter on episodic retrieval."""
        for i in range(10):
            await manager.store_episodic(EpisodicMemory(
                session_id="s1", module="general", query=f"q{i}", response=f"a{i}",
            ))

        results = await manager.get_episodic(session_id="s1", limit=5)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_update_episodic_outcome(self, manager: MemoryManager) -> None:
        """Test updating outcome of episodic memory."""
        memory_id = await manager.store_episodic(EpisodicMemory(
            session_id="s1", module="sales", query="q", response="a",
        ))

        await manager.update_episodic_outcome(memory_id, "success", 0.9)

        results = await manager.get_episodic(session_id="s1")
        assert results[0].outcome == "success"
        assert results[0].outcome_score == 0.9

    @pytest.mark.asyncio
    async def test_delete_episodic(self, manager: MemoryManager) -> None:
        """Test deleting an episodic memory."""
        memory_id = await manager.store_episodic(EpisodicMemory(
            session_id="s1", module="sales", query="q", response="a",
        ))

        success = await manager.delete_episodic(memory_id)
        assert success is True

        results = await manager.get_episodic(session_id="s1")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_episodic(self, manager: MemoryManager) -> None:
        """Test deleting a non-existent memory returns False."""
        success = await manager.delete_episodic(99999)
        assert success is False

    @pytest.mark.asyncio
    async def test_count_episodic(self, manager: MemoryManager) -> None:
        """Test counting episodic memories."""
        assert await manager.count_episodic() == 0

        for i in range(5):
            await manager.store_episodic(EpisodicMemory(
                session_id="s1", module="general", query=f"q{i}", response=f"a{i}",
            ))

        assert await manager.count_episodic() == 5


class TestSemanticMemory:
    """Tests for semantic memory CRUD operations."""

    @pytest.mark.asyncio
    async def test_store_semantic(self, manager: MemoryManager) -> None:
        """Test storing a semantic memory."""
        memory = SemanticMemory(
            module="sales",
            category="closing",
            key="assumptive_close",
            value="Proceed as if the prospect has decided.",
            confidence=0.9,
            tags=["closing", "tactic"],
        )

        memory_id = await manager.store_semantic(memory)
        assert memory_id > 0

    @pytest.mark.asyncio
    async def test_store_semantic_upsert(self, manager: MemoryManager) -> None:
        """Test that storing with same key updates existing record."""
        memory1 = SemanticMemory(
            module="sales", category="closing", key="test_key",
            value="Original value", confidence=0.5,
        )
        memory2 = SemanticMemory(
            module="sales", category="closing", key="test_key",
            value="Updated value", confidence=0.9,
        )

        id1 = await manager.store_semantic(memory1)
        id2 = await manager.store_semantic(memory2)

        # Should update, not create new
        results = await manager.get_semantic(module="sales", category="closing", key="test_key")
        assert len(results) == 1
        assert results[0].value == "Updated value"
        assert results[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_get_semantic_by_module(self, manager: MemoryManager) -> None:
        """Test filtering semantic memories by module."""
        await manager.store_semantic(SemanticMemory(
            module="sales", category="c1", key="k1", value="v1",
        ))
        await manager.store_semantic(SemanticMemory(
            module="trading", category="c2", key="k2", value="v2",
        ))

        results = await manager.get_semantic(module="sales")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_semantic_by_category(self, manager: MemoryManager) -> None:
        """Test filtering semantic memories by category."""
        await manager.store_semantic(SemanticMemory(
            module="sales", category="closing", key="k1", value="v1",
        ))
        await manager.store_semantic(SemanticMemory(
            module="sales", category="negotiation", key="k2", value="v2",
        ))

        results = await manager.get_semantic(module="sales", category="closing")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_delete_semantic(self, manager: MemoryManager) -> None:
        """Test deleting a semantic memory."""
        memory_id = await manager.store_semantic(SemanticMemory(
            module="sales", category="c", key="k", value="v",
        ))

        success = await manager.delete_semantic(memory_id)
        assert success is True

        results = await manager.get_semantic(module="sales", category="c", key="k")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_increment_use_count(self, manager: MemoryManager) -> None:
        """Test incrementing use count."""
        memory_id = await manager.store_semantic(SemanticMemory(
            module="sales", category="c", key="k", value="v", use_count=0,
        ))

        await manager.increment_use_count(memory_id)
        await manager.increment_use_count(memory_id)

        results = await manager.get_semantic(module="sales", category="c", key="k")
        assert results[0].use_count == 2


class TestWorkingMemory:
    """Tests for working memory (in-memory session context)."""

    @pytest.mark.asyncio
    async def test_working_memory_via_episodic(self, manager: MemoryManager) -> None:
        """Test that storing episodic memory updates working memory."""
        await manager.store_episodic(EpisodicMemory(
            session_id="test_session", module="sales",
            query="q1", response="a1",
        ))

        working = await manager.get_working("test_session")
        assert len(working) == 1
        assert working[0]["query"] == "q1"

    @pytest.mark.asyncio
    async def test_working_memory_max_size(self, manager: MemoryManager) -> None:
        """Test working memory respects max size limit."""
        # Store more than max_working size
        for i in range(25):
            await manager.store_episodic(EpisodicMemory(
                session_id="big_session", module="general",
                query=f"q{i}", response=f"a{i}",
            ))

        working = await manager.get_working("big_session")
        # Should be trimmed to max_working (20)
        assert len(working) <= 20

    @pytest.mark.asyncio
    async def test_clear_working_memory(self, manager: MemoryManager) -> None:
        """Test clearing working memory for a session."""
        await manager.store_episodic(EpisodicMemory(
            session_id="s1", module="general", query="q", response="a",
        ))

        await manager.clear_working("s1")
        working = await manager.get_working("s1")
        assert len(working) == 0


class TestSessionManagement:
    """Tests for session tracking."""

    @pytest.mark.asyncio
    async def test_create_session(self, manager: MemoryManager) -> None:
        """Test creating a new session."""
        await manager.create_session("session_123", "sales")

        # Should be able to increment
        await manager.increment_session_messages("session_123")
        await manager.increment_session_messages("session_123")

    @pytest.mark.asyncio
    async def test_increment_session_messages(self, manager: MemoryManager) -> None:
        """Test incrementing session message count."""
        await manager.create_session("s1")
        await manager.increment_session_messages("s1")
        await manager.increment_session_messages("s1")

        # No exception = pass
