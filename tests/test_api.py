"""Tests for the FastAPI server."""

from __future__ import annotations

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
import asyncio

from athena.server.api import app
from athena.db.database import Database
from athena.db.migrations import init_schema, seed_knowledge
from athena.core.memory import MemoryManager
from athena.core.retrieval import RetrievalEngine
from athena.core.decision import DecisionEngine
from athena.core.agent import AthenaAgent
from athena.models.llm import llm_client


@pytest.fixture(scope="module")
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture()
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client with initialized app state."""
    # Initialize test database
    test_db = Database(":memory:")
    await test_db.initialize()
    await init_schema(test_db)
    await seed_knowledge(test_db)
    
    # Initialize LLM as unavailable for tests
    llm_client._healthy = False
    
    # Create components
    memory = MemoryManager(test_db)
    retrieval = RetrievalEngine(memory, llm_client)
    decision = DecisionEngine(memory, retrieval, llm_client)
    test_agent = AthenaAgent(memory, retrieval, decision, llm_client)
    
    # Set app state
    app.state.agent = test_agent
    app.state.db = test_db
    
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        await test_db.close()


class TestHealthEndpoint:
    """Tests for health endpoint."""

    @pytest.mark.asyncio
    async def test_health(self, test_client: AsyncClient) -> None:
        """Test health check returns 200."""
        response = await test_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["db_connected"] is True

    @pytest.mark.asyncio
    async def test_health_has_version(self, test_client: AsyncClient) -> None:
        """Test health response includes version."""
        response = await test_client.get("/api/v1/health")
        data = response.json()
        assert "version" in data


class TestChatEndpoint:
    """Tests for chat endpoint."""

    @pytest.mark.asyncio
    async def test_chat_success(self, test_client: AsyncClient) -> None:
        """Test successful chat request."""
        response = await test_client.post("/api/v1/chat", json={
            "message": "How do I close a deal?",
            "module": "sales",
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 0
        assert data["module"] == "sales"
        assert "session_id" in data
        assert "confidence" in data

    @pytest.mark.asyncio
    async def test_chat_default_module(self, test_client: AsyncClient) -> None:
        """Test chat with default module."""
        response = await test_client.post("/api/v1/chat", json={
            "message": "Test query",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "general"

    @pytest.mark.asyncio
    async def test_chat_invalid_module(self, test_client: AsyncClient) -> None:
        """Test chat with invalid module returns 400."""
        response = await test_client.post("/api/v1/chat", json={
            "message": "Test",
            "module": "invalid",
        })

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_chat_empty_message(self, test_client: AsyncClient) -> None:
        """Test chat with empty message returns 422."""
        response = await test_client.post("/api/v1/chat", json={
            "message": "",
            "module": "general",
        })

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_preserves_session(self, test_client: AsyncClient) -> None:
        """Test that session_id is preserved across requests."""
        response1 = await test_client.post("/api/v1/chat", json={
            "message": "First message",
        })

        session_id = response1.json()["session_id"]

        response2 = await test_client.post("/api/v1/chat", json={
            "message": "Second message",
            "session_id": session_id,
        })

        assert response2.json()["session_id"] == session_id


class TestMemoryEndpoints:
    """Tests for memory endpoints."""

    @pytest.mark.asyncio
    async def test_get_episodic_with_data(self, test_client: AsyncClient) -> None:
        """Test getting episodic memories after chat."""
        await test_client.post("/api/v1/chat", json={
            "message": "Test episodic query",
        })

        response = await test_client.get("/api/v1/memory/episodic")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_get_semantic(self, test_client: AsyncClient) -> None:
        """Test getting semantic memories (seeded knowledge)."""
        response = await test_client.get("/api/v1/memory/semantic")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_add_semantic(self, test_client: AsyncClient) -> None:
        """Test adding semantic knowledge."""
        response = await test_client.post("/api/v1/memory/semantic", json={
            "module": "sales",
            "category": "test",
            "key": "test_key",
            "value": "Test value",
            "confidence": 0.9,
            "tags": ["test"],
        })

        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    @pytest.mark.asyncio
    async def test_delete_memory(self, test_client: AsyncClient) -> None:
        """Test deleting a memory."""
        add_response = await test_client.post("/api/v1/memory/semantic", json={
            "module": "sales",
            "category": "test",
            "key": "delete_test",
            "value": "To be deleted",
        })

        memory_id = add_response.json()["id"]

        response = await test_client.delete(
            f"/api/v1/memory/{memory_id}",
            params={"memory_type": "semantic"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_nonexistent_memory(self, test_client: AsyncClient) -> None:
        """Test deleting non-existent memory returns 404."""
        response = await test_client.delete(
            "/api/v1/memory/99999",
            params={"memory_type": "episodic"},
        )
        assert response.status_code == 404


class TestDecisionEndpoint:
    """Tests for decision endpoint."""

    @pytest.mark.asyncio
    async def test_make_decision(self, test_client: AsyncClient) -> None:
        """Test making a decision."""
        response = await test_client.post("/api/v1/decisions", json={
            "context": "Client requesting discount",
            "options": ["Option A", "Option B"],
            "module": "sales",
        })

        assert response.status_code == 200
        data = response.json()
        assert "recommendation" in data
        assert "confidence" in data

    @pytest.mark.asyncio
    async def test_decision_too_few_options(self, test_client: AsyncClient) -> None:
        """Test decision with too few options."""
        response = await test_client.post("/api/v1/decisions", json={
            "context": "Test",
            "options": ["Only one"],
            "module": "sales",
        })

        assert response.status_code == 422


class TestSessionEndpoint:
    """Tests for session endpoint."""

    @pytest.mark.asyncio
    async def test_get_session(self, test_client: AsyncClient) -> None:
        """Test getting session history."""
        response = await test_client.post("/api/v1/chat", json={
            "message": "Session test query",
        })
        session_id = response.json()["session_id"]

        response = await test_client.get(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_get_session_with_history(self, test_client: AsyncClient) -> None:
        """Test getting session with multiple messages."""
        r1 = await test_client.post("/api/v1/chat", json={"message": "Q1"})
        sid = r1.json()["session_id"]
        await test_client.post("/api/v1/chat", json={"message": "Q2", "session_id": sid})

        response = await test_client.get(f"/api/v1/sessions/{sid}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestFeedbackEndpoint:
    """Tests for feedback endpoint."""

    @pytest.mark.asyncio
    async def test_feedback_invalid_score(self, test_client: AsyncClient) -> None:
        """Test feedback with invalid score."""
        response = await test_client.post(
            "/api/v1/feedback/1",
            json={"outcome": "test", "score": 1.5},
        )
        assert response.status_code == 422
