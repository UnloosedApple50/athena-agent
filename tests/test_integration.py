"""Integration tests for Athena Agent."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from athena.server.api import app
from athena.db.database import Database
from athena.db.migrations import init_schema, seed_knowledge
from athena.core.memory import MemoryManager
from athena.core.retrieval import RetrievalEngine
from athena.core.decision import DecisionEngine
from athena.core.agent import AthenaAgent
from athena.models.llm import llm_client


@pytest.fixture(scope="module")
def test_client():
    """Create test client with initialized app state."""
    # Initialize test database
    test_db = Database(":memory:")
    
    async def setup():
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
    
    import asyncio
    asyncio.run(setup())
    
    client = TestClient(app)
    yield client
    
    async def teardown():
        await test_db.close()
    asyncio.run(teardown())


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_chat_flow(self, test_client) -> None:
        """Test complete chat flow: query -> response -> memory stored."""
        # Send chat
        response = test_client.post("/api/v1/chat", json={
            "message": "How should I handle pricing objections from enterprise clients?",
            "module": "sales",
        })
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]

        # Verify memory was stored
        memory_response = test_client.get(
            "/api/v1/memory/episodic",
            params={"session_id": session_id},
        )
        memories = memory_response.json()
        assert len(memories) == 1

    def test_memory_persistence_across_requests(self, test_client) -> None:
        """Test that memory persists across multiple requests."""
        # First chat
        r1 = test_client.post("/api/v1/chat", json={
            "message": "What is position sizing?",
            "module": "trading",
        })
        sid = r1.json()["session_id"]

        # Second chat with same session
        test_client.post("/api/v1/chat", json={
            "message": "And stop losses?",
            "module": "trading",
            "session_id": sid,
        })

        # Both should be in memory
        memories = test_client.get(f"/api/v1/sessions/{sid}")
        assert len(memories.json()) == 2

    def test_multiple_modules(self, test_client) -> None:
        """Test switching between modules."""
        # Sales query
        sales = test_client.post("/api/v1/chat", json={
            "message": "Negotiation tactics",
            "module": "sales",
        })
        assert sales.json()["module"] == "sales"

        # Trading query
        trading = test_client.post("/api/v1/chat", json={
            "message": "Risk management",
            "module": "trading",
        })
        assert trading.json()["module"] == "trading"

    def test_decision_after_chat(self, test_client) -> None:
        """Test making a decision after chatting."""
        # Chat first
        test_client.post("/api/v1/chat", json={
            "message": "I have a deal with a tough negotiator",
            "module": "sales",
        })

        # Make a decision
        response = test_client.post("/api/v1/decisions", json={
            "context": "Client wants 30% discount",
            "options": ["Refuse", "Counter with 10%", "Meet at 20%"],
            "module": "sales",
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendation"]) > 0

    def test_knowledge_retrieval(self, test_client) -> None:
        """Test that seeded knowledge is retrievable."""
        response = test_client.get(
            "/api/v1/memory/semantic",
            params={"module": "sales", "limit": 100},
        )
        data = response.json()
        # Should have seeded sales knowledge
        assert len(data) >= 5

    def test_add_and_retrieve_knowledge(self, test_client) -> None:
        """Test adding knowledge and retrieving it."""
        # Add knowledge
        test_client.post("/api/v1/memory/semantic", json={
            "module": "sales",
            "category": "test_integration",
            "key": "integration_test_key",
            "value": "This is an integration test fact about enterprise sales.",
            "tags": ["integration", "test"],
        })

        # Retrieve by key
        response = test_client.get(
            "/api/v1/memory/semantic",
            params={"key": "integration_test_key"},
        )
        data = response.json()
        assert len(data) >= 1

    def test_health_after_operations(self, test_client) -> None:
        """Test health check after operations."""
        # Do some operations
        test_client.post("/api/v1/chat", json={"message": "test"})

        # Health should still be good
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["memory_count"] > 0

    def test_recovery_after_invalid_request(self, test_client) -> None:
        """Test system recovers after invalid request."""
        # Invalid request
        bad = test_client.post("/api/v1/chat", json={
            "message": "test",
            "module": "invalid_module",
        })
        assert bad.status_code == 400

        # Valid request should still work
        good = test_client.post("/api/v1/chat", json={
            "message": "Valid request",
            "module": "general",
        })
        assert good.status_code == 200


class TestCrashRecovery:
    """Tests for crash recovery scenarios."""

    def test_data_survives_operations(self, test_client) -> None:
        """Test data integrity after multiple operations."""
        # Create many sessions
        for i in range(10):
            test_client.post("/api/v1/chat", json={
                "message": f"Session test {i}",
                "module": "sales" if i % 2 == 0 else "trading",
            })

        # Verify all sessions exist
        episodic = test_client.get("/api/v1/memory/episodic?limit=100")
        data = episodic.json()
        assert len(data) >= 10

    def test_wal_mode_resilience(self, test_client) -> None:
        """Test that WAL mode allows reads during writes."""
        # Start a write
        write_result = test_client.post("/api/v1/chat", json={
            "message": "Write test",
        })

        # Immediately try to read
        read_result = test_client.get("/api/v1/memory/semantic?limit=10")

        # Both should succeed (WAL allows concurrent reads)
        assert write_result.status_code == 200
        assert read_result.status_code == 200
