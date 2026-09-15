"""Security utilities for input validation and sanitization."""

from __future__ import annotations

import re
import html
from typing import Final

from athena.models.config import get_settings

# Patterns that indicate SQL injection attempts
SQL_INJECTION_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)", re.IGNORECASE),
    re.compile(r"(--|;|/\*|\*/|xp_|sp_)"),
    re.compile(r"('|\"|\\)", re.IGNORECASE),
]

# Patterns for XSS prevention
XSS_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
]


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
    import uuid
    return f"sess_{uuid.uuid4().hex[:12]}"
