"""SQLite database layer with WAL mode for crash safety."""

from __future__ import annotations

import aiosqlite
from pathlib import Path
from typing import Any, Optional

from athena.models.config import get_settings
from athena.utils.logger import get_logger

logger = get_logger("db")


class Database:
    """Async SQLite database manager with WAL mode."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._settings = get_settings()
        self._db_path = Path(db_path) if db_path else self._settings.db_path_resolved
        self._connection: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize database connection and enable WAL mode."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = await aiosqlite.connect(str(self._db_path))
        self._connection.row_factory = aiosqlite.Row

        # Enable WAL mode for concurrent reads + crash safety
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA synchronous=NORMAL")
        await self._connection.execute("PRAGMA foreign_keys=ON")
        await self._connection.execute("PRAGMA cache_size=-2000")  # 2MB cache
        await self._connection.execute("PRAGMA temp_store=MEMORY")

        logger.info(f"Database initialized at {self._db_path}")

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    async def execute(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> aiosqlite.Cursor:
        """
        Execute a parameterized query.

        Args:
            query: SQL query with ? or :param placeholders.
            params: Query parameters.

        Returns:
            Database cursor.
        """
        if not self._connection:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        if params is None:
            params = ()
        return await self._connection.execute(query, params)

    async def executemany(
        self,
        query: str,
        params_list: list[tuple[Any, ...] | dict[str, Any]],
    ) -> aiosqlite.Cursor:
        """Execute a query multiple times with different parameters."""
        if not self._connection:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return await self._connection.executemany(query, params_list)

    async def commit(self) -> None:
        """Commit current transaction."""
        if self._connection:
            await self._connection.commit()

    async def fetchall(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> list[aiosqlite.Row]:
        """Execute query and return all rows."""
        cursor = await self.execute(query, params)
        return await cursor.fetchall()

    async def fetchone(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> Optional[aiosqlite.Row]:
        """Execute query and return first row."""
        cursor = await self.execute(query, params)
        return await cursor.fetchone()

    async def fetchval(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None,
        column: int = 0,
    ) -> Any:
        """Execute query and return single value."""
        row = await self.fetchone(query, params)
        if row is None:
            return None
        return row[column]

    @property
    def is_connected(self) -> bool:
        """Check if database connection is active."""
        return self._connection is not None


# Global database instance
db = Database()
