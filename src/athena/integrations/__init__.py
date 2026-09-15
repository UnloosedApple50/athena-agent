"""Integrations subpackage for external service connections."""

from athena.integrations.webhooks import WebhookManager, Webhook, WebhookEvent
from athena.integrations.api_keys import APIKeyManager, APIKey
from athena.integrations.connectors import (
    ConnectorManager,
    ConnectorConfig,
    SlackConnector,
    DiscordConnector,
    TelegramConnector,
    ZapierConnector,
)
from athena.integrations.oauth import OAuthManager, OAuthToken, OAuthProvider

__all__ = [
    "WebhookManager",
    "Webhook",
    "WebhookEvent",
    "APIKeyManager",
    "APIKey",
    "ConnectorManager",
    "ConnectorConfig",
    "SlackConnector",
    "DiscordConnector",
    "TelegramConnector",
    "ZapierConnector",
    "OAuthManager",
    "OAuthToken",
    "OAuthProvider",
]
