"""Pre-built connectors for external services: Slack, Discord, Telegram, Zapier."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from athena.utils.logger import get_logger

logger = get_logger("integrations.connectors")


@dataclass
class ConnectorConfig:
    """Configuration for an external service connector."""

    service: str
    webhook_url: str = ""
    bot_token: str = ""
    channel_id: str = ""
    api_key: str = ""
    enabled: bool = True
    settings: dict[str, Any] = field(default_factory=dict)


class SlackConnector:
    """Connector for Slack workspace integration."""

    def __init__(self, config: ConnectorConfig) -> None:
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self._config.bot_token}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Send a message to a Slack channel."""
        client = await self._get_client()
        payload: dict[str, Any] = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks

        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def send_webhook(self, text: str, attachments: Optional[list] = None) -> bool:
        """Send a message via Slack incoming webhook."""
        if not self._config.webhook_url:
            return False

        payload: dict[str, Any] = {"text": text}
        if attachments:
            payload["attachments"] = attachments

        client = await self._get_client()
        response = await client.post(self._config.webhook_url, json=payload)
        return response.status_code == 200


class DiscordConnector:
    """Connector for Discord server integration."""

    def __init__(self, config: ConnectorConfig) -> None:
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bot {self._config.bot_token}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def send_message(
        self,
        channel_id: str,
        content: str,
        embeds: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Send a message to a Discord channel."""
        client = await self._get_client()
        payload: dict[str, Any] = {"content": content}
        if embeds:
            payload["embeds"] = embeds

        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    async def send_webhook(
        self,
        content: str,
        username: str = "Athena Agent",
        avatar_url: str = "",
        embeds: Optional[list[dict[str, Any]]] = None,
    ) -> bool:
        """Send a message via Discord webhook."""
        if not self._config.webhook_url:
            return False

        payload: dict[str, Any] = {"content": content, "username": username}
        if avatar_url:
            payload["avatar_url"] = avatar_url
        if embeds:
            payload["embeds"] = embeds

        client = await self._get_client()
        response = await client.post(
            self._config.webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        return response.status_code in (200, 204)


class TelegramConnector:
    """Connector for Telegram bot integration."""

    API_BASE = "https://api.telegram.org/bot"

    def __init__(self, config: ConnectorConfig) -> None:
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _api_url(self, method: str) -> str:
        return f"{self.API_BASE}{self._config.bot_token}/{method}"

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False,
    ) -> dict[str, Any]:
        """Send a message to a Telegram chat."""
        client = await self._get_client()
        response = await client.post(
            self._api_url("sendMessage"),
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_notification": disable_notification,
            },
        )
        response.raise_for_status()
        return response.json()

    async def send_chat_action(self, chat_id: str, action: str = "typing") -> bool:
        """Send a chat action (typing indicator)."""
        client = await self._get_client()
        response = await client.post(
            self._api_url("sendChatAction"),
            json={"chat_id": chat_id, "action": action},
        )
        return response.status_code == 200


class ZapierConnector:
    """Connector for Zapier webhook integration."""

    def __init__(self, config: ConnectorConfig) -> None:
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"Content-Type": "application/json"},
                timeout=10.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def trigger_zap(
        self,
        event: str,
        data: dict[str, Any],
    ) -> bool:
        """Trigger a Zapier zap via webhook URL."""
        if not self._config.webhook_url:
            return False

        payload = {
            "event": event,
            "timestamp": time.time(),
            "data": data,
        }

        client = await self._get_client()
        response = await client.post(
            self._config.webhook_url,
            json=payload,
        )
        return response.status_code == 200


class ConnectorManager:
    """Manages all external service connectors."""

    SUPPORTED_SERVICES = {"slack", "discord", "telegram", "zapier"}

    def __init__(self) -> None:
        self._connectors: dict[str, Any] = {}

    def create_connector(self, config: ConnectorConfig) -> Any:
        """
        Create a connector for a supported service.
        
        Args:
            config: Connector configuration.
            
        Returns:
            Service-specific connector instance.
            
        Raises:
            ValueError: If service is not supported.
        """
        service = config.service.lower()
        if service not in self.SUPPORTED_SERVICES:
            raise ValueError(
                f"Unsupported service: {service}. Supported: {self.SUPPORTED_SERVICES}"
            )

        connector: Any
        if service == "slack":
            connector = SlackConnector(config)
        elif service == "discord":
            connector = DiscordConnector(config)
        elif service == "telegram":
            connector = TelegramConnector(config)
        elif service == "zapier":
            connector = ZapierConnector(config)
        else:
            raise ValueError(f"Unknown service: {service}")

        self._connectors[service] = connector
        logger.info(f"Connector created for {service}")
        return connector

    def get_connector(self, service: str) -> Optional[Any]:
        """Get a connector by service name."""
        return self._connectors.get(service.lower())

    def remove_connector(self, service: str) -> bool:
        """Remove a connector."""
        if service.lower() in self._connectors:
            del self._connectors[service.lower()]
            return True
        return False

    def list_connectors(self) -> list[str]:
        """List all active connector services."""
        return list(self._connectors.keys())

    async def close_all(self) -> None:
        """Close all connector HTTP clients."""
        for connector in self._connectors.values():
            if hasattr(connector, "close"):
                await connector.close()
        self._connectors.clear()


# Global instance
connector_manager = ConnectorManager()
