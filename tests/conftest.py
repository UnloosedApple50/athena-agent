"""Pytest configuration and fixtures for Athena Agent tests."""

from __future__ import annotations

import asyncio
import os
import tempfile
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from pathlib import Path

# Set test environment before imports
os.environ["ATHENA_DB_PATH"] = ":memory:"
os.environ["ATHENA_LOG_LEVEL"] = "WARNING"
os.environ["ATHENA_LLM_BASE_URL"] = "http://localhost:11434/v1"
os.environ["ATHENA_LLM_MODEL"] = "test-model"

from athena.db.database import Database
from athena.db.migrations import init_schema, seed_knowledge
from athena.core.memory import MemoryManager
from athena.core.retrieval import RetrievalEngine
from athena.core.decision import DecisionEngine
from athena.core.agent import AthenaAgent
from athena.models.llm import LLMClient


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def database() -> AsyncGenerator[Database, None]:
    """Create a test database."""
    db = Database(":memory:")
    await db.initialize()
    await init_schema(db)
    yield db
    await db.close()


@pytest_asyncio.fixture
async def memory(database: Database) -> AsyncGenerator[MemoryManager, None]:
    """Create a memory manager with test database."""
    manager = MemoryManager(database)
    yield manager


@pytest_asyncio.fixture
async def retrieval(memory: MemoryManager) -> AsyncGenerator[RetrievalEngine, None]:
    """Create a retrieval engine with test memory."""
    engine = RetrievalEngine(memory)
    yield engine


@pytest_asyncio.fixture
async def decision(
    memory: MemoryManager,
    retrieval: RetrievalEngine,
) -> AsyncGenerator[DecisionEngine, None]:
    """Create a decision engine with test components."""
    engine = DecisionEngine(memory, retrieval)
    yield engine


@pytest_asyncio.fixture
async def agent(
    memory: MemoryManager,
    retrieval: RetrievalEngine,
    decision: DecisionEngine,
) -> AsyncGenerator[AthenaAgent, None]:
    """Create an agent with test components."""
    a = AthenaAgent(memory, retrieval, decision)
    yield a


@pytest.fixture
def mock_llm() -> LLMClient:
    """Create a mock LLM client."""
    client = LLMClient()
    client._healthy = False  # Simulate unavailable LLM
    return client
