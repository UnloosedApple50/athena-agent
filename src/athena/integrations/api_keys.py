"""API key generation, validation, and management for external access."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("integrations.api_keys")


@dataclass
class APIKey:
    """Represents an API key with metadata."""

    id: str
    name: str
    key_hash: str
    key_prefix: str
    scopes: list[str]
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None
    request_count: int = 0
    rate_limit: int = 100  # requests per minute


class APIKeyManager:
    """Manages API key lifecycle for external API access."""

    VALID_SCOPES: set[str] = {
        "chat",
        "decisions",
        "memory.read",
        "memory.write",
        "knowledge.read",
        "knowledge.write",
        "metrics",
        "system",
        "webhooks",
        "admin",
    }

    KEY_PREFIX: str = "athena_"

    def __init__(self, database: Optional[Database] = None) -> None:
        self._db = database
        self._keys: dict[str, APIKey] = {}  # key_hash -> APIKey

    def _generate_id(self) -> str:
        """Generate unique key ID."""
        return f"key_{uuid.uuid4().hex[:12]}"

    def _generate_key(self) -> str:
        """Generate a new API key."""
        return f"{self.KEY_PREFIX}{secrets.token_urlsafe(32)}"

    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    def _get_prefix(self, key: str) -> str:
        """Get the displayable prefix of an API key."""
        return key[:12] + "..."

    async def create_key(
        self,
        name: str,
        scopes: list[str],
        rate_limit: int = 100,
        expires_at: Optional[str] = None,
    ) -> tuple[str, APIKey]:
        """
        Create a new API key.
        
        Args:
            name: Human-readable name for the key.
            scopes: List of permission scopes.
            rate_limit: Requests per minute limit.
            expires_at: Optional expiration timestamp.
            
        Returns:
            Tuple of (full_key, APIKey) — full_key is shown only once.
            
        Raises:
            ValueError: If scopes are invalid.
        """
        # Validate scopes
        invalid_scopes = set(scopes) - self.VALID_SCOPES
        if invalid_scopes:
            raise ValueError(
                f"Invalid scopes: {invalid_scopes}. Valid: {self.VALID_SCOPES}"
            )

        full_key = self._generate_key()
        key_hash = self._hash_key(full_key)

        api_key = APIKey(
            id=self._generate_id(),
            name=name,
            key_hash=key_hash,
            key_prefix=self._get_prefix(full_key),
            scopes=list(set(scopes)),
            rate_limit=rate_limit,
            expires_at=expires_at,
        )

        self._keys[key_hash] = api_key

        # Persist
        if self._db and self._db.is_connected:
            try:
                await self._db.execute(
                    """
                    INSERT INTO api_keys (id, name, key_hash, key_prefix, scopes, 
                                         active, created_at, expires_at, rate_limit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        api_key.id, name, key_hash, api_key.key_prefix,
                        json.dumps(api_key.scopes), True,
                        api_key.created_at, expires_at, rate_limit,
                    ),
                )
                await self._db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist API key: {e}")

        logger.info(f"API key created: {api_key.id} ({name})")
        return full_key, api_key

    async def validate_key(self, key: str) -> Optional[APIKey]:
        """
        Validate an API key and return the associated metadata.
        
        Args:
            key: The full API key string.
            
        Returns:
            APIKey if valid, None otherwise.
        """
        key_hash = self._hash_key(key)
        api_key = self._keys.get(key_hash)

        if api_key is None:
            return None

        if not api_key.active:
            return None

        # Check expiration
        if api_key.expires_at:
            try:
                expires = datetime.fromisoformat(api_key.expires_at)
                if datetime.utcnow() > expires:
                    return None
            except (ValueError, TypeError):
                pass

        # Update usage
        api_key.last_used_at = datetime.utcnow().isoformat()
        api_key.request_count += 1

        return api_key

    async def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key by its ID.
        
        Args:
            key_id: The key ID.
            
        Returns:
            True if key was found and revoked.
        """
        for key_hash, api_key in list(self._keys.items()):
            if api_key.id == key_id:
                api_key.active = False
                if self._db and self._db.is_connected:
                    try:
                        await self._db.execute(
                            "UPDATE api_keys SET active = 0 WHERE id = ?",
                            (key_id,),
                        )
                        await self._db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to revoke key in db: {e}")
                logger.info(f"API key revoked: {key_id}")
                return True
        return False

    async def delete_key(self, key_id: str) -> bool:
        """Permanently delete an API key."""
        for key_hash, api_key in list(self._keys.items()):
            if api_key.id == key_id:
                del self._keys[key_hash]
                if self._db and self._db.is_connected:
                    try:
                        await self._db.execute(
                            "DELETE FROM api_keys WHERE id = ?",
                            (key_id,),
                        )
                        await self._db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to delete key from db: {e}")
                return True
        return False

    async def list_keys(self) -> list[APIKey]:
        """List all API keys (without sensitive data)."""
        return list(self._keys.values())

    def check_scope(self, api_key: APIKey, required_scope: str) -> bool:
        """Check if an API key has the required scope."""
        if "admin" in api_key.scopes:
            return True
        return required_scope in api_key.scopes

    async def load_from_db(self) -> int:
        """Load API keys from database."""
        if not self._db or not self._db.is_connected:
            return 0

        try:
            rows = await self._db.fetchall("SELECT * FROM api_keys WHERE active = 1")
            count = 0
            for row in rows:
                key_hash = row["key_hash"] if isinstance(row["key_hash"], str) else row[2]
                api_key = APIKey(
                    id=row["id"] if isinstance(row["id"], str) else row[0],
                    name=row["name"] if isinstance(row["name"], str) else row[1],
                    key_hash=key_hash,
                    key_prefix=row["key_prefix"] if isinstance(row["key_prefix"], str) else row[3],
                    scopes=json.loads(row["scopes"] if isinstance(row["scopes"], str) else row[4]),
                    active=True,
                    created_at=row["created_at"] if isinstance(row["created_at"], str) else row[6],
                    expires_at=row["expires_at"] if isinstance(row["expires_at"], str) else row[7],
                    rate_limit=row["rate_limit"] if isinstance(row["rate_limit"], int) else row[8],
                )
                self._keys[key_hash] = api_key
                count += 1
            return count
        except Exception as e:
            logger.warning(f"Failed to load API keys from db: {e}")
            return 0


# Global instance
api_key_manager = APIKeyManager()
