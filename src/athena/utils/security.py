"""Enhanced security utilities — rate limiting, audit logging, input validation."""

from __future__ import annotations

import hashlib
import hmac
import html
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Final, Optional

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("security")

# Patterns that indicate SQL injection attempts
SQL_INJECTION_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)", re.IGNORECASE),
    re.compile(r"(--|;|/\*|\*/|xp_|sp_)"),
    re.compile(r"('|\\\")", re.IGNORECASE),
]

# Patterns for XSS prevention
XSS_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
]

# Allowed HTML tags (for rich content)
ALLOWED_TAGS: Final[set[str]] = {
    "p", "br", "strong", "em", "ul", "ol", "li", "code", "pre", "blockquote",
}


@dataclass
class RateLimitEntry:
    """Rate limit tracking for a client."""

    requests: list[float] = field(default_factory=list)
    blocked_until: float = 0.0
    total_requests: int = 0
    total_blocked: int = 0


class RateLimiter:
    """In-memory rate limiter with configurable limits."""

    def __init__(
        self,
        requests_per_minute: int = 100,
        burst_size: int = 10,
        block_duration: int = 60,
    ) -> None:
        self._rpm = requests_per_minute
        self._burst = burst_size
        self._block_duration = block_duration
        self._clients: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._global_requests: list[float] = []

    def _cleanup(self) -> None:
        """Remove old entries."""
        now = time.time()
        cutoff = now - 60
        for client_id in list(self._clients.keys()):
            entry = self._clients[client_id]
            entry.requests = [t for t in entry.requests if t > cutoff]
            if not entry.requests and entry.blocked_until < now:
                del self._clients[client_id]
        self._global_requests = [t for t in self._global_requests if t > cutoff]

    def check_rate_limit(self, client_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Check if a client is within rate limits.
        
        Args:
            client_id: Unique client identifier (IP, session, API key).
            
        Returns:
            Tuple of (allowed, info_dict).
        """
        self._cleanup()
        now = time.time()
        entry = self._clients[client_id]

        # Check if blocked
        if entry.blocked_until > time.time():
            entry.total_blocked += 1
            return False, {
                "allowed": False,
                "retry_after": int(entry.blocked_until - now),
                "limit": self._rpm,
                "window": "60",
            }

        # Count recent requests
        cutoff = now - 60
        entry.requests = [t for t in entry.requests if t > cutoff]
        entry.requests.append(now)
        entry.total_requests += 1
        self._global_requests.append(now)

        # Check limits
        if len(entry.requests) > self._rpm:
            entry.blocked_until = now + self._block_duration
            entry.total_blocked += 1
            logger.warning(f"Rate limit exceeded for {client_id}")
            return False, {
                "allowed": False,
                "retry_after": self._block_duration,
                "limit": self._rpm,
                "window": "60",
            }

        remaining = max(0, self._rpm - len(entry.requests))
        return True, {
            "allowed": True,
            "remaining": remaining,
            "limit": self._rpm,
            "reset": int(now + 60),
        }

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics."""
        self._cleanup()
        return {
            "active_clients": len(self._clients),
            "global_rpm": len(self._global_requests),
            "config": {
                "requests_per_minute": self._rpm,
                "burst_size": self._burst,
                "block_duration": self._block_duration,
            },
        }


class AuditLogger:
    """Audit logging for security-relevant operations."""

    def __init__(self, database: Optional[Database] = None) -> None:
        self._db = database

    async def log(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Log an auditable action.
        
        Args:
            action: Action type (e.g., 'chat.create', 'api_key.create').
            user_id: User who performed the action.
            resource_type: Type of resource affected.
            resource_id: Resource identifier.
            details: Additional details dict.
            ip_address: Client IP.
        """
        if self._db and self._db.is_connected:
            try:
                await self._db.execute(
                    """
                    INSERT INTO audit_log 
                    (action, user_id, resource_type, resource_id, details, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action,
                        user_id,
                        resource_type,
                        resource_id,
                        __import__("json").dumps(details or {}),
                        ip_address,
                    ),
                )
                await self._db.commit()
            except Exception as e:
                logger.warning(f"Failed to write audit log: {e}")

    async def get_audit_log(
        self,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve audit log entries."""
        if not self._db or not self._db.is_connected:
            return []

        query = "SELECT * FROM audit_log"
        params: list[Any] = []

        if action:
            query += " WHERE action = ?"
            params.append(action)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        try:
            rows = await self._db.fetchall(query, tuple(params))
            return [
                {
                    "id": row["id"] if isinstance(row["id"], int) else row[0],
                    "action": row["action"] if isinstance(row["action"], str) else row[1],
                    "user_id": row["user_id"] if isinstance(row["user_id"], str) else row[2],
                    "resource_type": row["resource_type"] if isinstance(row["resource_type"], str) else row[3],
                    "resource_id": row["resource_id"] if isinstance(row["resource_id"], str) else row[4],
                    "details": __import__("json").loads(row["details"] if isinstance(row["details"], str) else row[5]) if (row["details"] if isinstance(row["details"], str) else row[5]) else {},
                    "ip_address": row["ip_address"] if isinstance(row["ip_address"], str) else row[6],
                    "created_at": row["created_at"] if isinstance(row["created_at"], str) else row[7],
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning(f"Failed to read audit log: {e}")
            return []


def sanitize_input(text: str) -> str:
    """
    Sanitize user input by escaping HTML and removing dangerous content.

    Args:
        text: Raw user input.

    Returns:
        Sanitized text safe for processing and display.

    Raises:
        ValueError: If input exceeds maximum length.
    """
    from athena.models.config import get_settings
    settings = get_settings()

    if len(text) > settings.max_input_length:
        raise ValueError(
            f"Input exceeds maximum length of {settings.max_input_length} characters"
        )

    # Remove null bytes
    text = text.replace("\x00", "")

    # Escape HTML entities
    text = html.escape(text)

    # Remove potential XSS vectors
    for pattern in XSS_PATTERNS:
        text = pattern.sub("", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def validate_module(module: str) -> str:
    """
    Validate and normalize module name.

    Args:
        module: Module identifier.

    Returns:
        Normalized module name.

    Raises:
        ValueError: If module is not recognized.
    """
    valid_modules = {"sales", "trading", "general"}
    normalized = module.lower().strip()

    if normalized not in valid_modules:
        raise ValueError(
            f"Invalid module '{module}'. Must be one of: {', '.join(sorted(valid_modules))}"
        )

    return normalized


def check_sql_injection(text: str) -> bool:
    """
    Check if text contains potential SQL injection patterns.

    Args:
        text: Input text to check.

    Returns:
        True if suspicious patterns detected.
    """
    return any(pattern.search(text) for pattern in SQL_INJECTION_PATTERNS)


def generate_session_id() -> str:
    """Generate a unique session identifier."""
    return f"sess_{uuid.uuid4().hex[:12]}"


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return uuid.uuid4().hex


def validate_csrf_token(token: str, expected: str) -> bool:
    """Validate a CSRF token using constant-time comparison."""
    return hmac.compare_digest(token, expected)


def hash_sensitive_value(value: str) -> str:
    """Hash a sensitive value for secure storage."""
    return hashlib.sha256(value.encode()).hexdigest()


# Global instances
rate_limiter = RateLimiter()
audit_logger = AuditLogger()
