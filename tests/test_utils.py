"""Tests for utility functions."""

from __future__ import annotations

import pytest
from athena.utils.security import (
    sanitize_input,
    validate_module,
    check_sql_injection,
    generate_session_id,
)
from athena.utils.logger import get_logger


class TestSecurityUtils:
    """Tests for security utilities."""

    def test_sanitize_input_basic(self) -> None:
        """Test basic input sanitization."""
        result = sanitize_input("Hello World")
        assert result == "Hello World"

    def test_sanitize_input_html(self) -> None:
        """Test HTML escaping."""
        result = sanitize_input("<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result

    def test_sanitize_input_whitespace(self) -> None:
        """Test whitespace normalization."""
        result = sanitize_input("  Hello   World  ")
        assert result == "Hello World"

    def test_sanitize_input_null_bytes(self) -> None:
        """Test null byte removal."""
        result = sanitize_input("Hello\x00World")
        assert "\x00" not in result

    def test_sanitize_input_too_long(self) -> None:
        """Test that overly long input raises error."""
        with pytest.raises(ValueError):
            sanitize_input("x" * 10001)

    def test_validate_module_valid(self) -> None:
        """Test valid module names."""
        assert validate_module("sales") == "sales"
        assert validate_module("trading") == "trading"
        assert validate_module("general") == "general"

    def test_validate_module_invalid(self) -> None:
        """Test invalid module name raises error."""
        with pytest.raises(ValueError):
            validate_module("invalid")

    def test_validate_module_case_insensitive(self) -> None:
        """Test module validation is case-insensitive."""
        assert validate_module("SALES") == "sales"
        assert validate_module("Sales") == "sales"

    def test_check_sql_injection(self) -> None:
        """Test SQL injection detection."""
        assert check_sql_injection("'; DROP TABLE users; --") is True
        # assert check_sql_injection("SELECT * FROM users") is True

    def test_check_sql_injection_safe(self) -> None:
        """Test safe input passes SQL injection check."""
        assert check_sql_injection("Hello World") is False
        assert check_sql_injection("How do I close a deal?") is False

    def test_generate_session_id(self) -> None:
        """Test session ID generation."""
        sid = generate_session_id()
        assert sid.startswith("sess_")
        assert len(sid) > 10

    def test_generate_session_id_unique(self) -> None:
        """Test session IDs are unique."""
        ids = {generate_session_id() for _ in range(100)}
        assert len(ids) == 100


class TestUtils:
    """Tests for utility functions."""

    def test_get_logger(self) -> None:
        """Test logger creation."""
        logger = get_logger("test")
        assert logger is not None

    def test_get_logger_cached(self) -> None:
        """Test logger caching."""
        logger1 = get_logger("cached")
        logger2 = get_logger("cached")
        assert logger1 is logger2
