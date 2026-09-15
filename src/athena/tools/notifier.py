"""Notifier tool — send notifications via configured channels."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("tools.notifier")


@dataclass
class Notification:
    """A notification message."""

    id: str
    title: str
    message: str
    level: str = "info"  # info, warning, error, success
    channel: str = "web"  # web, email, slack, discord, telegram
    read: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    data: dict[str, Any] = field(default_factory=dict)


class Notifier:
    """Send notifications via configured channels."""

    VALID_LEVELS: set[str] = {"info", "warning", "error", "success"}
    VALID_CHANNELS: set[str] = {"web", "email", "slack", "discord", "telegram"}

    def __init__(self, database: Optional[Database] = None) -> None:
        self._db = database
        self._notifications: dict[str, Notification] = {}
        self._channel_configs: dict[str, dict[str, Any]] = {}

    def configure_channel(
        self,
        channel: str,
        config: dict[str, Any],
    ) -> None:
        """
        Configure a notification channel.
        
        Args:
            channel: Channel name.
            config: Channel-specific configuration.
        """
        if channel not in self.VALID_CHANNELS:
            raise ValueError(f"Invalid channel: {channel}. Valid: {self.VALID_CHANNELS}")
        self._channel_configs[channel] = config

    async def notify(
        self,
        title: str,
        message: str,
        level: str = "info",
        channel: str = "web",
        data: Optional[dict[str, Any]] = None,
    ) -> Notification:
        """
        Send a notification.
        
        Args:
            title: Notification title.
            message: Notification message body.
            level: Severity level.
            channel: Target channel.
            data: Additional data.
            
        Returns:
            Notification instance.
        """
        if level not in self.VALID_LEVELS:
            level = "info"

        notification = Notification(
            id=f"notif_{uuid.uuid4().hex[:12]}",
            title=title,
            message=message,
            level=level,
            channel=channel,
            data=data or {},
        )

        self._notifications[notification.id] = notification

        # Persist
        if self._db and self._db.is_connected:
            try:
                await self._db.execute(
                    """
                    INSERT INTO notifications 
                    (id, title, message, level, channel, read, created_at, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        notification.id, title, message, level,
                        channel, False, notification.created_at,
                        json.dumps(data or {}),
                    ),
                )
                await self._db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist notification: {e}")

        # Attempt to send via channel
        await self._send_to_channel(notification)

        logger.info(f"Notification sent: {title} ({level}) via {channel}")
        return notification

    async def _send_to_channel(self, notification: Notification) -> bool:
        """Send notification to its configured channel."""
        config = self._channel_configs.get(notification.channel, {})

        if notification.channel == "web":
            # Web notifications are stored and fetched via API
            return True

        if notification.channel == "slack":
            return await self._send_slack(notification, config)

        if notification.channel == "discord":
            return await self._send_discord(notification, config)

        if notification.channel == "telegram":
            return await self._send_telegram(notification, config)

        if notification.channel == "email":
            return await self._send_email(notification, config)

        return False

    async def _send_slack(self, notification: Notification, config: dict[str, Any]) -> bool:
        """Send notification to Slack."""
        import httpx

        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            return False

        color_map = {
            "info": "#36a64f",
            "warning": "#ff9900",
            "error": "#ff0000",
            "success": "#36a64f",
        }

        payload = {
            "attachments": [{
                "color": color_map.get(notification.level, "#36a64f"),
                "title": notification.title,
                "text": notification.message,
                "ts": int(time.time()),
            }]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to send Slack notification: {e}")
            return False

    async def _send_discord(self, notification: Notification, config: dict[str, Any]) -> bool:
        """Send notification to Discord."""
        import httpx

        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            return False

        color_map = {
            "info": 0x36a64f,
            "warning": 0xff9900,
            "error": 0xff0000,
            "success": 0x36a64f,
        }

        payload = {
            "embeds": [{
                "title": notification.title,
                "description": notification.message,
                "color": color_map.get(notification.level, 0x36a64f),
                "timestamp": notification.created_at,
            }]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                return response.status_code in (200, 204)
        except Exception as e:
            logger.warning(f"Failed to send Discord notification: {e}")
            return False

    async def _send_telegram(self, notification: Notification, config: dict[str, Any]) -> bool:
        """Send notification to Telegram."""
        import httpx

        bot_token = config.get("bot_token", "")
        chat_id = config.get("chat_id", "")
        if not bot_token or not chat_id:
            return False

        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
        }

        emoji = emoji_map.get(notification.level, "ℹ️")
        text = f"*{emoji} {notification.title}*\n\n{notification.message}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                    },
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to send Telegram notification: {e}")
            return False

    async def _send_email(self, notification: Notification, config: dict[str, Any]) -> bool:
        """Send notification via email (placeholder)."""
        # Would integrate with SMTP or email service
        logger.info(f"Email notification to {config.get('to', 'N/A')}: {notification.title}")
        return True

    async def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        if notification_id in self._notifications:
            self._notifications[notification_id].read = True
            if self._db and self._db.is_connected:
                try:
                    await self._db.execute(
                        "UPDATE notifications SET read = 1 WHERE id = ?",
                        (notification_id,),
                    )
                    await self._db.commit()
                except Exception as e:
                    logger.warning(f"Failed to update notification: {e}")
            return True
        return False

    async def mark_all_read(self) -> int:
        """Mark all notifications as read."""
        count = 0
        for notif in self._notifications.values():
            if not notif.read:
                notif.read = True
                count += 1

        if self._db and self._db.is_connected:
            try:
                await self._db.execute("UPDATE notifications SET read = 1 WHERE read = 0")
                await self._db.commit()
            except Exception as e:
                logger.warning(f"Failed to update notifications: {e}")

        return count

    def get_notifications(
        self,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        """Get notifications."""
        notifs = list(self._notifications.values())
        if unread_only:
            notifs = [n for n in notifs if not n.read]
        notifs.sort(key=lambda n: n.created_at, reverse=True)
        return notifs[:limit]

    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        return sum(1 for n in self._notifications.values() if not n.read)


# Global instance
notifier = Notifier()
