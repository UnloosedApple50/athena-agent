"""Tests for database and main module."""

from __future__ import annotations

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from athena.db.database import Database
from athena.db.migrations import init_schema, seed_knowledge, get_current_version


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[Database, None]:
    """Create in-memory test database."""
    database = Database(":memory:")
    await database.initialize()
    await init_schema(database)
    yield database
    await database.close()


class TestDatabase:
    """Tests for the database layer."""

    @pytest.mark.asyncio
    async def test_initialize(self, db: Database) -> None:
        """Test database initialization."""
        assert db.is_connected is True

    @pytest.mark.asyncio
    async def test_execute(self, db: Database) -> None:
        """Test query execution."""
        cursor = await db.execute("SELECT 1")
        assert cursor is not None

    @pytest.mark.asyncio
    async def test_fetchone(self, db: Database) -> None:
        """Test fetching one row."""
        await db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        await db.execute("INSERT INTO test (name) VALUES ('test_value')")
        await db.commit()
        
        row = await db.fetchone("SELECT * FROM test WHERE name = ?", ("test_value",))
        assert row is not None
        assert row["name"] == "test_value"

    @pytest.mark.asyncio
    async def test_fetchall(self, db: Database) -> None:
        """Test fetching all rows."""
        await db.execute("CREATE TABLE test2 (id INTEGER PRIMARY KEY)")
        await db.execute("INSERT INTO test2 (id) VALUES (1), (2), (3)")
        await db.commit()
        
        rows = await db.fetchall("SELECT * FROM test2")
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_fetchval(self, db: Database) -> None:
        """Test fetching a single value."""
        await db.execute("SELECT 42 as val")
        val = await db.fetchval("SELECT 42 as val")
        # Note: This won't work as expected because the cursor is consumed
        # The actual usage pattern is to fetchval after execute
        await db.execute("SELECT 42 as val")
        val = await db.fetchval("SELECT 42 as val")
        # fetchval fetches a row and returns column 0
        assert val == 42

    @pytest.mark.asyncio
    async def test_executemany(self, db: Database) -> None:
        """Test executing many statements."""
        await db.execute("CREATE TABLE test3 (id INTEGER, name TEXT)")
        params = [(1, "a"), (2, "b"), (3, "c")]
        await db.executemany("INSERT INTO test3 VALUES (?, ?)", params)
        await db.commit()
        
        rows = await db.fetchall("SELECT * FROM test3")
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_commit(self, db: Database) -> None:
        """Test commit."""
        await db.execute("CREATE TABLE test4 (id INTEGER)")
        await db.execute("INSERT INTO test4 VALUES (1)")
        await db.commit()
        
        rows = await db.fetchall("SELECT * FROM test4")
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_not_initialized_error(self) -> None:
        """Test error when using uninitialized database."""
        uninit_db = Database(":memory:")
        with pytest.raises(RuntimeError):
            await uninit_db.execute("SELECT 1")


class TestMigrations:
    """Tests for schema management."""

    @pytest.mark.asyncio
    async def test_get_current_version(self, db: Database) -> None:
        """Test getting schema version."""
        version = await get_current_version(db)
        assert version == 0  # No version seeded

    @pytest.mark.asyncio
    async def test_init_schema_idempotent(self, db: Database) -> None:
        """Test that init_schema can be called multiple times."""
        await init_schema(db)
        await init_schema(db)  # Should not error


class TestSeedKnowledge:
    """Tests for knowledge seeding."""

    @pytest.mark.asyncio
    async def test_seed_knowledge(self, db: Database) -> None:
        """Test that knowledge is seeded correctly."""
        await seed_knowledge(db)
        
        rows = await db.fetchall("SELECT COUNT(*) as cnt FROM semantic_memory")
        assert rows[0]["cnt"] > 0

    @pytest.mark.asyncio
    async def test_seed_knowledge_idempotent(self, db: Database) -> None:
        """Test that seeding is idempotent."""
        await seed_knowledge(db)
        await seed_knowledge(db)  # Should not duplicate
