"""Token throughput tracking — metrics for LLM token usage and performance."""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("metrics")

ROLLING_WINDOW_SIZE: int = 100


@dataclass
class TokenRecord:
    """Single token usage record."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tokens_per_second: float
    latency_ms: float
    model: str
    module: str
    session_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ThroughputStats:
    """Aggregated throughput statistics."""

    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    avg_tokens_per_second: float
    avg_latency_ms: float
    rolling_avg_tps: float  # Rolling average over last N requests
    peak_tps: float
    min_tps: float
    requests_per_minute: float
    models_used: dict[str, int]
    modules_used: dict[str, int]


class MetricsTracker:
    """
    Tracks token throughput metrics for LLM requests.
    
    Maintains both in-memory rolling window and persistent SQLite storage.
    """

    def __init__(self, database: Optional[Database] = None) -> None:
        self._db = database
        self._records: deque[TokenRecord] = deque(maxlen=ROLLING_WINDOW_SIZE)
        self._all_records: list[TokenRecord] = []
        self._start_time: float = time.time()

        # Counters
        self._total_prompt_tokens: int = 0
        self._total_completion_tokens: int = 0
        self._total_requests: int = 0
        self._peak_tps: float = 0.0
        self._min_tps: float = float("inf")
        self._models_used: dict[str, int] = {}
        self._modules_used: dict[str, int] = {}

    async def record(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        model: str = "unknown",
        module: str = "general",
        session_id: Optional[str] = None,
    ) -> TokenRecord:
        """
        Record a token usage event.
        
        Args:
            prompt_tokens: Number of prompt tokens.
            completion_tokens: Number of completion tokens.
            latency_ms: Request latency in milliseconds.
            model: Model name used.
            module: Module context.
            session_id: Optional session ID.
            
        Returns:
            The created TokenRecord.
        """
        total_tokens = prompt_tokens + completion_tokens
        tokens_per_second = (total_tokens / (latency_ms / 1000.0)) if latency_ms > 0 else 0.0

        record = TokenRecord(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            tokens_per_second=tokens_per_second,
            latency_ms=latency_ms,
            model=model,
            module=module,
            session_id=session_id,
        )

        # Update memory
        self._records.append(record)
        self._all_records.append(record)

        # Update counters
        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens
        self._total_requests += 1

        if tokens_per_second > self._peak_tps:
            self._peak_tps = tokens_per_second
        if tokens_per_second < self._min_tps:
            self._min_tps = tokens_per_second

        self._models_used[model] = self._models_used.get(model, 0) + 1
        self._modules_used[module] = self._modules_used.get(module, 0) + 1

        # Persist to database
        if self._db and self._db.is_connected:
            try:
                await self._db.execute(
                    """
                    INSERT INTO metrics_throughput 
                    (prompt_tokens, completion_tokens, total_tokens, tokens_per_second, 
                     latency_ms, model, module, session_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        prompt_tokens, completion_tokens, total_tokens,
                        tokens_per_second, latency_ms, model, module, session_id,
                    ),
                )
                await self._db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist metrics: {e}")

        return record

    def get_stats(self) -> ThroughputStats:
        """Get current aggregated statistics."""
        rolling_avg_tps = 0.0
        if self._records:
            rolling_avg_tps = sum(r.tokens_per_second for r in self._records) / len(self._records)

        avg_tps = 0.0
        avg_latency = 0.0
        if self._total_requests > 0:
            elapsed = time.time() - self._start_time
            avg_tps = (self._total_prompt_tokens + self._total_completion_tokens) / max(elapsed, 1)
            avg_latency = sum(r.latency_ms for r in self._all_records) / len(self._all_records)

        elapsed_minutes = (time.time() - self._start_time) / 60.0
        rpm = self._total_requests / max(elapsed_minutes, 0.01)

        return ThroughputStats(
            total_requests=self._total_requests,
            total_prompt_tokens=self._total_prompt_tokens,
            total_completion_tokens=self._total_completion_tokens,
            total_tokens=self._total_prompt_tokens + self._total_completion_tokens,
            avg_tokens_per_second=avg_tps,
            avg_latency_ms=avg_latency,
            rolling_avg_tps=rolling_avg_tps,
            peak_tps=self._peak_tps,
            min_tps=self._min_tps if self._min_tps != float("inf") else 0.0,
            requests_per_minute=rpm,
            models_used=dict(self._models_used),
            modules_used=dict(self._modules_used),
        )

    def get_recent_records(self, count: int = 50) -> list[TokenRecord]:
        """Get recent token records."""
        return list(self._records)[-count:]

    def get_rolling_average(self, window: int = ROLLING_WINDOW_SIZE) -> float:
        """Get rolling average tokens per second over last N records."""
        records = list(self._records)[-window:]
        if not records:
            return 0.0
        return sum(r.tokens_per_second for r in records) / len(records)

    async def get_historical_stats(
        self, 
        hours: int = 24, 
        database: Optional[Database] = None,
    ) -> dict[str, Any]:
        """
        Get historical metrics from database.
        
        Args:
            hours: Number of hours to look back.
            database: Optional database instance (uses stored one if not provided).
            
        Returns:
            Dictionary with historical statistics.
        """
        db = database or self._db
        if not db or not db.is_connected:
            return {"error": "Database not available"}

        try:
            row = await db.fetchone(
                """
                SELECT 
                    COUNT(*) as total_requests,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                    COALESCE(AVG(tokens_per_second), 0) as avg_tps,
                    COALESCE(AVG(latency_ms), 0) as avg_latency,
                    COALESCE(MAX(tokens_per_second), 0) as peak_tps
                FROM metrics_throughput
                WHERE created_at >= datetime('now', ?)
                """,
                (f"-{hours} hours",),
            )

            if row:
                return {
                    "period_hours": hours,
                    "total_requests": row[0] if isinstance(row[0], int) else row["total_requests"],
                    "total_tokens": row[1] if isinstance(row[1], int) else row["total_tokens"],
                    "avg_tps": row[5] if isinstance(row[5], float) else row["avg_tps"],
                    "avg_latency_ms": row[6] if isinstance(row[6], float) else row["avg_latency"],
                    "peak_tps": row[7] if isinstance(row[7], float) else row["peak_tps"],
                }
        except Exception as e:
            logger.warning(f"Failed to fetch historical metrics: {e}")

        return {"period_hours": hours, "total_requests": 0, "total_tokens": 0}

    def reset(self) -> None:
        """Reset all in-memory counters."""
        self._records.clear()
        self._all_records.clear()
        self._start_time = time.time()
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_requests = 0
        self._peak_tps = 0.0
        self._min_tps = float("inf")
        self._models_used.clear()
        self._modules_used.clear()

    def to_dict(self) -> dict[str, Any]:
        """Get all stats as a dictionary."""
        stats = self.get_stats()
        return {
            "total_requests": stats.total_requests,
            "total_prompt_tokens": stats.total_prompt_tokens,
            "total_completion_tokens": stats.total_completion_tokens,
            "total_tokens": stats.total_tokens,
            "avg_tokens_per_second": round(stats.avg_tokens_per_second, 2),
            "avg_latency_ms": round(stats.avg_latency_ms, 2),
            "rolling_avg_tps": round(stats.rolling_avg_tps, 2),
            "peak_tps": round(stats.peak_tps, 2),
            "min_tps": round(stats.min_tps, 2),
            "requests_per_minute": round(stats.requests_per_minute, 2),
            "models_used": stats.models_used,
            "modules_used": stats.modules_used,
        }


# Global instance
metrics_tracker = MetricsTracker()
