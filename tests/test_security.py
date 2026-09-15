"""Tests for enhanced security module."""

from __future__ import annotations

import pytest
from athena.utils.security import (
    RateLimiter,
    AuditLogger,
    sanitize_input,
    validate_module,
    check_sql_injection,
    generate_session_id,
    generate_csrf_token,
    validate_csrf_token,
    hash_sensitive_value,
)


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_init(self):
        limiter = RateLimiter(requests_per_minute=100)
        assert limiter._rpm == 100

    def test_check_rate_limit_allowed(self):
        limiter = RateLimiter(requests_per_minute=10)
        allowed, info = limiter.check_rate_limit("client1")
        assert allowed is True
        assert info["allowed"] is True

    def test_check_rate_limit_exceeded(self):
        limiter = RateLimiter(requests_per_minute=2)
        limiter.check_rate_limit("client1")
        limiter.check_rate_limit("client1")
        allowed, info = limiter.check_rate_limit("client1")
        assert allowed is False
        assert info["allowed"] is False

    def test_get_stats(self):
        limiter = RateLimiter()
        limiter.check_rate_limit("client1")
        stats = limiter.get_stats()
        assert "active_clients" in stats


class TestAuditLogger:
    """Tests for AuditLogger."""

    def test_init(self):
        logger = AuditLogger()
        assert logger is not None


class TestSanitizeInput:
    def test_basic(self):
        result = sanitize_input("Hello World")
        assert result == "Hello World"

    def test_html_escape(self):
        result = sanitize_input("<script>alert('xss')</script>")
        assert "<script>" not in result

    def test_null_bytes(self):
        result = sanitize_input("hello\x00world")
        assert "\x00" not in result

    def test_whitespace_normalize(self):
        result = sanitize_input("hello   world")
        assert result == "hello world"


class TestValidateModule:
    def test_valid(self):
        assert validate_module("sales") == "sales"
        assert validate_module("trading") == "trading"
        assert validate_module("general") == "general"

    def test_case_insensitive(self):
        assert validate_module("SALES") == "sales"

    def test_invalid(self):
        with pytest.raises(ValueError):
            validate_module("invalid")


class TestSQLInjection:
    def test_safe(self):
        assert check_sql_injection("Hello World") is False

    def test_unsafe(self):
        assert check_sql_injection("'; DROP TABLE users;") is True


class TestSessionID:
    def test_unique(self):
        id1 = generate_session_id()
        id2 = generate_session_id()
        assert id1 != id2

    def test_prefix(self):
        id = generate_session_id()
        assert id.startswith("sess_")


class TestCSRFToken:
    def test_generate(self):
        token = generate_csrf_token()
        assert len(token) > 0

    def test_validate(self):
        token = generate_csrf_token()
        assert validate_csrf_token(token, token) is True
        assert validate_csrf_token(token, "different") is False


class TestHashSensitive:
    def test_hash(self):
        hash1 = hash_sensitive_value("test")
        hash2 = hash_sensitive_value("test")
        hash3 = hash_sensitive_value("different")
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA256 hex
