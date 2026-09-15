"""Database schema management and migrations."""

from __future__ import annotations

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("migrations")

# Schema version for tracking migrations
SCHEMA_VERSION: int = 2

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

    # === New tables for v2 ===

    """CREATE TABLE IF NOT EXISTS metrics_throughput (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt_tokens INTEGER NOT NULL DEFAULT 0,
        completion_tokens INTEGER NOT NULL DEFAULT 0,
        total_tokens INTEGER NOT NULL DEFAULT 0,
        tokens_per_second REAL DEFAULT 0.0,
        latency_ms REAL DEFAULT 0.0,
        model TEXT DEFAULT 'unknown',
        module TEXT DEFAULT 'general',
        session_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",

    """CREATE INDEX IF NOT EXISTS idx_metrics_created ON metrics_throughput(created_at)""",
    """CREATE INDEX IF NOT EXISTS idx_metrics_module ON metrics_throughput(module)""",

    """CREATE TABLE IF NOT EXISTS webhooks (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        events TEXT NOT NULL DEFAULT '[]',
        secret TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_triggered TIMESTAMP,
        failure_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS api_keys (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL UNIQUE,
        key_prefix TEXT,
        scopes TEXT NOT NULL DEFAULT '[]',
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP,
        expires_at TIMESTAMP,
        request_count INTEGER DEFAULT 0,
        rate_limit INTEGER DEFAULT 100
    )""",

    """CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)""",

    """CREATE TABLE IF NOT EXISTS oauth_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        access_token TEXT NOT NULL,
        refresh_token TEXT,
        expires_in INTEGER DEFAULT 3600,
        scope TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",

    """CREATE TABLE IF NOT EXISTS training_feedback (
        id TEXT PRIMARY KEY,
        memory_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        correction TEXT,
        comment TEXT,
        category TEXT DEFAULT 'general',
        session_id TEXT,
        module TEXT DEFAULT 'general',
        original_query TEXT,
        original_response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",

    """CREATE INDEX IF NOT EXISTS idx_feedback_memory ON training_feedback(memory_id)""",
    """CREATE INDEX IF NOT EXISTS idx_feedback_session ON training_feedback(session_id)""",
    """CREATE INDEX IF NOT EXISTS idx_feedback_rating ON training_feedback(rating)""",

    """CREATE TABLE IF NOT EXISTS scheduled_tasks (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        scheduled_at TEXT NOT NULL,
        recurring INTEGER DEFAULT 0,
        interval_seconds INTEGER DEFAULT 0,
        callback TEXT,
        data TEXT DEFAULT '{}',
        completed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_run TIMESTAMP
    )""",

    """CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        level TEXT DEFAULT 'info',
        channel TEXT DEFAULT 'web',
        read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data TEXT DEFAULT '{}'
    )""",

    """CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read)""",
    """CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at)""",

    """CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        user_id TEXT,
        resource_type TEXT,
        resource_id TEXT,
        details TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",

    """CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)""",
    """CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at)""",
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
