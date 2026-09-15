"""Tests for LLM client and configuration."""

from __future__ import annotations

import pytest
import os
from unittest.mock import MagicMock, AsyncMock, patch
from athena.models.llm import LLMClient, LLMResponse
from athena.models.config import Settings, get_settings


class TestLLMClient:
    """Tests for the LLM client."""

    def test_initialization(self) -> None:
        """Test LLM client initializes with correct defaults."""
        client = LLMClient()
        assert client._client is None
        assert client._healthy is False

    @pytest.mark.asyncio
    async def test_close_without_init(self) -> None:
        """Test closing uninitialized client doesn't error."""
        client = LLMClient()
        await client.close()

    def test_is_available_default(self) -> None:
        """Test is_available returns False by default."""
        client = LLMClient()
        assert client.is_available is False


class TestLLMResponse:
    """Tests for LLM response dataclass."""

    def test_create_response(self) -> None:
        """Test creating an LLM response."""
        response = LLMResponse(
            content="Test content",
            confidence=0.9,
            tokens_used=100,
            model="llama3.2",
        )
        assert response.content == "Test content"
        assert response.confidence == 0.9
        assert response.tokens_used == 100
        assert response.model == "llama3.2"
        assert response.error is None
        assert response.fallback is False

    def test_create_fallback_response(self) -> None:
        """Test creating a fallback response."""
        response = LLMResponse(
            content="Rule-based response",
            confidence=0.5,
            tokens_used=0,
            model="fallback",
            fallback=True,
        )
        assert response.fallback is True

    def test_create_error_response(self) -> None:
        """Test creating an error response."""
        response = LLMResponse(
            content="",
            confidence=0.0,
            tokens_used=0,
            model="test",
            error="Connection failed",
        )
        assert response.error == "Connection failed"
