"""Webhook registration and event dispatch for external integrations."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import httpx

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("integrations.webhooks")


@dataclass
class Webhook:
    """Registered webhook configuration."""

    id: str
    url: str
    events: list[str]
    secret: str
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_triggered: Optional[str] = None
    failure_count: int = 0
    success_count: int = 0


@dataclass
class WebhookEvent:
    """Event payload sent to webhooks."""

    event_type: str
    timestamp: str
    data: dict[str, Any]
    webhook_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class WebhookManager:
    """Manages webhook registration and event dispatch."""

    VALID_EVENTS: set[str] = {
        "chat.created",
        "chat.response",
        "decision.made",
        "memory.created",
        "memory.updated",
        "knowledge.added",
        "training.feedback",
        "system.alert",
    }

    def __init__(self, database: Optional[Database] = None) -> None:
        self._db = database
        self._webhooks: dict[str, Webhook] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=10.0,
                headers={"Content-Type": "application/json"},
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def _generate_id(self) -> str:
        """Generate unique webhook ID."""
        return f"wh_{uuid.uuid4().hex[:12]}"

    def _generate_secret(self) -> str:
        """Generate webhook signing secret."""
        return f"whsec_{uuid.uuid4().hex}"

    def _sign_payload(self, payload: str, secret: str) -> str:
        """Create HMAC signature for webhook payload."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def register(
        self,
        url: str,
        events: list[str],
        secret: Optional[str] = None,
    ) -> Webhook:
        """
        Register a new webhook.
        
        Args:
            url: Webhook endpoint URL.
            events: List of event types to subscribe to.
            secret: Optional signing secret (auto-generated if not provided).
            
        Returns:
            Registered Webhook instance.
            
        Raises:
            ValueError: If URL or events are invalid.
        """
        if not url or not url.startswith(("http://", "https://")):
            raise ValueError("Invalid webhook URL. Must start with http:// or https://")

        # Validate events
        invalid_events = set(events) - self.VALID_EVENTS
        if invalid_events:
            raise ValueError(
                f"Invalid events: {invalid_events}. Valid: {self.VALID_EVENTS}"
            )

        webhook = Webhook(
            id=self._generate_id(),
            url=url,
            events=list(set(events)),  # Deduplicate
            secret=secret or self._generate_secret(),
        )

        self._webhooks[webhook.id] = webhook

        # Persist to database
        if self._db and self._db.is_connected:
            try:
                await self._db.execute(
                    """
                    INSERT INTO webhooks (id, url, events, secret, active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        webhook.id,
                        webhook.url,
                        json.dumps(webhook.events),
                        webhook.secret,
                        webhook.active,
                        webhook.created_at,
                    ),
                )
                await self._db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist webhook: {e}")

        logger.info(f"Webhook registered: {webhook.id} -> {url}")
        return webhook

    async def unregister(self, webhook_id: str) -> bool:
        """
        Remove a webhook registration.
        
        Args:
            webhook_id: Webhook ID to remove.
            
        Returns:
            True if webhook was found and removed.
        """
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]

            if self._db and self._db.is_connected:
                try:
                    await self._db.execute(
                        "DELETE FROM webhooks WHERE id = ?",
                        (webhook_id,),
                    )
                    await self._db.commit()
                except Exception as e:
                    logger.warning(f"Failed to delete webhook from db: {e}")

            logger.info(f"Webhook unregistered: {webhook_id}")
            return True
        return False

    async def list_webhooks(self) -> list[Webhook]:
        """List all registered webhooks."""
        return list(self._webhooks.values())

    async def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get a webhook by ID."""
        return self._webhooks.get(webhook_id)

    async def dispatch(self, event_type: str, data: dict[str, Any]) -> int:
        """
        Dispatch an event to all matching webhooks.
        
        Args:
            event_type: Type of event.
            data: Event payload data.
            
        Returns:
            Number of webhooks the event was sent to.
        """
        if event_type not in self.VALID_EVENTS:
            logger.warning(f"Unknown event type: {event_type}")
            return 0

        event = WebhookEvent(
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            data=data,
        )

        sent_count = 0
        client = await self._get_client()

        for webhook in self._webhooks.values():
            if not webhook.active:
                continue
            if event_type not in webhook.events:
                continue

            payload = json.dumps(event.to_dict())
            signature = self._sign_payload(payload, webhook.secret)

            try:
                response = await client.post(
                    webhook.url,
                    content=payload,
                    headers={
                        "X-Webhook-ID": webhook.id,
                        "X-Webhook-Signature": signature,
                        "X-Webhook-Event": event_type,
                    },
                )

                if response.status_code < 400:
                    webhook.success_count += 1
                    sent_count += 1
                else:
                    webhook.failure_count += 1
                    logger.warning(
                        f"Webhook {webhook.id} returned {response.status_code}"
                    )

                webhook.last_triggered = datetime.utcnow().isoformat()

            except Exception as e:
                webhook.failure_count += 1
                logger.warning(f"Failed to dispatch to {webhook.id}: {e}")

        return sent_count

    async def load_from_db(self) -> int:
        """Load webhooks from database. Returns count loaded."""
        if not self._db or not self._db.is_connected:
            return 0

        try:
            rows = await self._db.fetchall("SELECT * FROM webhooks WHERE active = 1")
            count = 0
            for row in rows:
                webhook = Webhook(
                    id=row["id"] if isinstance(row["id"], str) else row[0],
                    url=row["url"] if isinstance(row["url"], str) else row[1],
                    events=json.loads(row["events"] if isinstance(row["events"], str) else row[2]),
                    secret=row["secret"] if isinstance(row["secret"], str) else row[3],
                    active=True,
                    created_at=row["created_at"] if isinstance(row["created_at"], str) else row[5],
                )
                self._webhooks[webhook.id] = webhook
                count += 1
            return count
        except Exception as e:
            logger.warning(f"Failed to load webhooks from db: {e}")
            return 0


# Global instance
webhook_manager = WebhookManager()
