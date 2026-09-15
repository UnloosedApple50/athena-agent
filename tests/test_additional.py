"""Additional coverage tests for connectors, notifier, and scheduler."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from athena.tools.scheduler import Scheduler
from athena.tools.notifier import Notifier
from athena.integrations.connectors import (
    ConnectorManager, ConnectorConfig, 
    SlackConnector, DiscordConnector, TelegramConnector, ZapierConnector
)


class TestSlackConnector:
    def test_init(self):
        config = ConnectorConfig(service="slack", bot_token="xoxb-test")
        conn = SlackConnector(config)
        assert conn._config.bot_token == "xoxb-test"

    @pytest.mark.asyncio
    async def test_close(self):
        config = ConnectorConfig(service="slack")
        conn = SlackConnector(config)
        await conn.close()


class TestDiscordConnector:
    def test_init(self):
        config = ConnectorConfig(service="discord", bot_token="token")
        conn = DiscordConnector(config)
        assert conn._config.bot_token == "token"

    @pytest.mark.asyncio
    async def test_close(self):
        config = ConnectorConfig(service="discord")
        conn = DiscordConnector(config)
        await conn.close()


class TestTelegramConnector:
    def test_init(self):
        config = ConnectorConfig(service="telegram", bot_token="123456")
        conn = TelegramConnector(config)
        assert conn._config.bot_token == "123456"

    def test_api_url(self):
        config = ConnectorConfig(service="telegram", bot_token="123456")
        conn = TelegramConnector(config)
        assert "123456" in conn._api_url("sendMessage")

    @pytest.mark.asyncio
    async def test_close(self):
        config = ConnectorConfig(service="telegram")
        conn = TelegramConnector(config)
        await conn.close()


class TestZapierConnector:
    def test_init(self):
        config = ConnectorConfig(service="zapier", webhook_url="https://zapier.com/hook")
        conn = ZapierConnector(config)
        assert conn._config.webhook_url == "https://zapier.com/hook"

    @pytest.mark.asyncio
    async def test_close(self):
        config = ConnectorConfig(service="zapier")
        conn = ZapierConnector(config)
        await conn.close()


class TestConnectorManager:
    @pytest.mark.asyncio
    async def test_create_connector(self):
        manager = ConnectorManager()
        config = ConnectorConfig(service="slack", bot_token="test")
        conn = manager.create_connector(config)
        assert isinstance(conn, SlackConnector)
        assert "slack" in manager.list_connectors()

    def test_create_connector_invalid(self):
        manager = ConnectorManager()
        with pytest.raises(ValueError):
            manager.create_connector(ConnectorConfig(service="invalid"))

    def test_get_connector(self):
        manager = ConnectorManager()
        assert manager.get_connector("slack") is None

    @pytest.mark.asyncio
    async def test_close_all(self):
        manager = ConnectorManager()
        config = ConnectorConfig(service="slack")
        manager.create_connector(config)
        await manager.close_all()
        assert len(manager.list_connectors()) == 0


class TestNotifierExtended:
    @pytest.mark.asyncio
    async def test_notify_all_levels(self):
        notifier = Notifier()
        for level in ["info", "warning", "error", "success"]:
            n = await notifier.notify(title="Test", message="Msg", level=level)
            assert n.level == level

    def test_get_notifications_unread_only(self):
        notifier = Notifier()
        # Manually add notifications
        from athena.tools.notifier import Notification
        notifier._notifications["test1"] = Notification(
            id="test1", title="T", message="M", read=False
        )
        notifier._notifications["test2"] = Notification(
            id="test2", title="T", message="M", read=True
        )
        unread = notifier.get_notifications(unread_only=True)
        assert len(unread) == 1

    def test_get_unread_count_multiple(self):
        notifier = Notifier()
        from athena.tools.notifier import Notification
        notifier._notifications["a"] = Notification(id="a", title="T", message="M", read=False)
        notifier._notifications["b"] = Notification(id="b", title="T", message="M", read=False)
        notifier._notifications["c"] = Notification(id="c", title="T", message="M", read=True)
        assert notifier.get_unread_count() == 2


class TestSchedulerExtended:
    def test_list_tasks_include_completed(self):
        scheduler = Scheduler()
        from athena.tools.scheduler import ScheduledTask
        scheduler._tasks["t1"] = ScheduledTask(
            id="t1", name="Test", description="",
            scheduled_at="2025-01-01T00:00:00", completed=False
        )
        scheduler._tasks["t2"] = ScheduledTask(
            id="t2", name="Test2", description="",
            scheduled_at="2025-01-01T00:00:00", completed=True
        )
        assert len(scheduler.list_tasks()) == 1
        assert len(scheduler.list_tasks(include_completed=True)) == 2

    @pytest.mark.asyncio
    async def test_check_and_execute_past_task(self):
        scheduler = Scheduler()
        callback = AsyncMock()
        scheduler.register_callback("test_cb", callback)
        
        await scheduler.schedule(
            name="past-task",
            description="",
            scheduled_at="2020-01-01T00:00:00",  # Past date
            callback="test_cb",
        )
        results = await scheduler.check_and_execute()
        assert len(results) == 1
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_recurring_task(self):
        scheduler = Scheduler()
        await scheduler.schedule(
            name="recurring",
            description="",
            scheduled_at="2020-01-01T00:00:00",
            recurring=True,
            interval_seconds=60,
        )
        results = await scheduler.check_and_execute()
        assert len(results) == 1
        # Task should not be marked completed
        task = list(scheduler._tasks.values())[0]
        assert task.completed is False
