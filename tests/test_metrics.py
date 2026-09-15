"""Tests for metrics tracking module."""

from __future__ import annotations

import pytest
import pytest_asyncio
from athena.monitor.metrics import MetricsTracker, TokenRecord, ThroughputStats


class TestMetricsTracker:
    """Tests for MetricsTracker class."""

    def test_init(self):
        tracker = MetricsTracker()
        assert tracker._total_requests == 0

    @pytest.mark.asyncio
    async def test_record(self):
        tracker = MetricsTracker()
        record = await tracker.record(
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=500,
            model="test-model",
            module="general",
        )
        assert isinstance(record, TokenRecord)
        assert record.prompt_tokens == 100
        assert record.completion_tokens == 50
        assert record.total_tokens == 150
        assert record.tokens_per_second > 0

    @pytest.mark.asyncio
    async def test_record_multiple(self):
        tracker = MetricsTracker()
        for i in range(10):
            await tracker.record(
                prompt_tokens=100,
                completion_tokens=50,
                latency_ms=500,
            )
        assert tracker._total_requests == 10

    def test_get_stats_empty(self):
        tracker = MetricsTracker()
        stats = tracker.get_stats()
        assert isinstance(stats, ThroughputStats)
        assert stats.total_requests == 0

    @pytest.mark.asyncio
    async def test_get_stats(self):
        tracker = MetricsTracker()
        await tracker.record(100, 50, 500)
        await tracker.record(200, 100, 1000)
        
        stats = tracker.get_stats()
        assert stats.total_requests == 2
        assert stats.total_prompt_tokens == 300
        assert stats.total_completion_tokens == 150
        assert stats.total_tokens == 450

    def test_get_recent_records(self):
        tracker = MetricsTracker()
        # Manually add records
        tracker._records.append(TokenRecord(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            tokens_per_second=300.0,
            latency_ms=500,
            model="test",
            module="general",
        ))
        records = tracker.get_recent_records(10)
        assert len(records) == 1

    def test_get_rolling_average(self):
        tracker = MetricsTracker()
        for i in range(5):
            tracker._records.append(TokenRecord(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                tokens_per_second=100.0 + i * 10,
                latency_ms=500,
                model="test",
                module="general",
            ))
        avg = tracker.get_rolling_average()
        assert avg > 0

    def test_reset(self):
        tracker = MetricsTracker()
        tracker._total_requests = 10
        tracker._total_prompt_tokens = 1000
        tracker.reset()
        assert tracker._total_requests == 0
        assert tracker._total_prompt_tokens == 0

    @pytest.mark.asyncio
    async def test_to_dict(self):
        tracker = MetricsTracker()
        await tracker.record(100, 50, 500)
        d = tracker.to_dict()
        assert "total_requests" in d
        assert "total_tokens" in d
        assert "avg_tokens_per_second" in d
        assert d["total_requests"] == 1


class TestTokenRecord:
    def test_creation(self):
        record = TokenRecord(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            tokens_per_second=300.0,
            latency_ms=500,
            model="test",
            module="general",
        )
        assert record.prompt_tokens == 100
        assert record.total_tokens == 150
