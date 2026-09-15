"""Database schema management and migrations."""

from __future__ import annotations

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("migrations")

# Schema version for tracking migrations
SCHEMA_VERSION: int = 1

# Individual migration statements (executed in order)
MIGRATION_STATEMENTS: list[str] = [
    """CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE TABLE IF NOT EXISTS episodic_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        module TEXT NOT NULL DEFAULT 'general',
        query TEXT NOT NULL,
        response TEXT NOT NULL,
        confidence REAL DEFAULT 0.5,
        outcome TEXT,
        outcome_score REAL,
        metadata TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE INDEX IF NOT EXISTS idx_episodic_session ON episodic_memory(session_id)""",
    """CREATE INDEX IF NOT EXISTS idx_episodic_module ON episodic_memory(module)""",
    """CREATE INDEX IF NOT EXISTS idx_episodic_created ON episodic_memory(created_at)""",
    
    """CREATE TABLE IF NOT EXISTS semantic_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module TEXT NOT NULL DEFAULT 'general',
        category TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        confidence REAL DEFAULT 0.5,
        source TEXT DEFAULT 'system',
        tags TEXT DEFAULT '[]',
        use_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(module, category, key)
    )""",
    
    """CREATE INDEX IF NOT EXISTS idx_semantic_module ON semantic_memory(module)""",
    """CREATE INDEX IF NOT EXISTS idx_semantic_category ON semantic_memory(category)""",
    """CREATE INDEX IF NOT EXISTS idx_semantic_key ON semantic_memory(key)""",
    
    """CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        module TEXT NOT NULL DEFAULT 'general',
        context TEXT NOT NULL,
        options TEXT NOT NULL,
        selected_option TEXT,
        confidence REAL DEFAULT 0.5,
        reasoning TEXT,
        outcome TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions(session_id)""",
    """CREATE INDEX IF NOT EXISTS idx_decisions_module ON decisions(module)""",
    
    """CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        module TEXT NOT NULL DEFAULT 'general',
        message_count INTEGER DEFAULT 0,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
]


async def init_schema(database: Database) -> None:
    """
    Initialize database schema.

    Args:
        database: Database instance to initialize.
    """
    logger.info("Initializing database schema...")

    for stmt in MIGRATION_STATEMENTS:
        try:
            await database.execute(stmt)
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

    await database.commit()
    logger.info("Database schema initialized successfully")


async def get_current_version(database: Database) -> int:
    """Get current schema version."""
    try:
        result = await database.fetchval(
            "SELECT MAX(version) FROM schema_version"
        )
        return result or 0
    except Exception:
        return 0


async def seed_knowledge(database: Database) -> None:
    """Seed initial sales and trading knowledge."""
    from athena.knowledge.base import get_knowledge_base
    kb = get_knowledge_base()

    import json
    facts = kb.get_all_facts()
    for fact in facts:
        await database.execute(
            """
            INSERT OR IGNORE INTO semantic_memory (module, category, key, value, confidence, source, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact.module,
                fact.category,
                fact.key,
                fact.value,
                fact.confidence,
                "seed",
                json.dumps(fact.tags),
            ),
        )

    await database.commit()
    logger.info(f"Seeded {len(facts)} knowledge facts")
