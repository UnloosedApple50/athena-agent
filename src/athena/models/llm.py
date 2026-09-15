"""LLM client for Ollama/OpenAI-compatible APIs with graceful degradation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from athena.models.config import get_settings
from athena.utils.logger import get_logger

logger = get_logger("llm")


@dataclass
class LLMResponse:
    """Structured LLM response."""

    content: str
    confidence: float
    tokens_used: int
    model: str
    error: Optional[str] = None
    fallback: bool = False


class LLMClient:
    """
    HTTP client for OpenAI-compatible LLM endpoints (Ollama, etc.).

    Features:
    - Connection pooling
    - Configurable timeouts
    - Automatic retries with exponential backoff
    - Health checking
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._healthy: bool = False

    async def initialize(self) -> None:
        """Initialize HTTP client with connection pooling."""
        self._client = httpx.AsyncClient(
            base_url=self._settings.llm_base_url,
            timeout=self._settings.llm_timeout,
            headers={
                "Authorization": f"Bearer {self._settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        await self.health_check()

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self._healthy

    async def health_check(self) -> bool:
        """
        Check if LLM service is reachable.

        Returns:
            True if service is healthy.
        """
        try:
            response = await self._client.get("/models")
            self._healthy = response.status_code == 200
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            self._healthy = False

        return self._healthy

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            system_prompt: System-level instructions.
            user_message: User query.
            temperature: Sampling temperature.
            max_tokens: Maximum response tokens.

        Returns:
            LLMResponse with generated content.

        Raises:
            RuntimeError: If client is not initialized.
        """
        if not self._client:
            raise RuntimeError("LLM client not initialized. Call initialize() first.")

        payload = {
            "model": self._settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        logger.debug(f"Sending request to LLM (model={self._settings.llm_model})")

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)

        return LLMResponse(
            content=content,
            confidence=0.8,  # Base confidence for LLM responses
            tokens_used=tokens_used,
            model=self._settings.llm_model,
        )

    async def score_relevance(
        self,
        query: str,
        text: str,
    ) -> float:
        """
        Use LLM to score relevance between query and text.

        Args:
            query: Original query.
            text: Text to score against.

        Returns:
            Relevance score between 0.0 and 1.0.
        """
        if not self.is_available:
            return 0.5  # Neutral score when LLM unavailable

        system = (
            "You are a relevance scoring system. Given a query and a text, "
            "return ONLY a number between 0.0 (completely irrelevant) and "
            "1.0 (perfectly relevant). Nothing else."
        )

        user = f"Query: {query}\n\nText: {text}\n\nRelevance score:"

        try:
            response = await self.generate(system, user, temperature=0.1, max_tokens=10)
            score = float(response.content.strip())
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.warning(f"Relevance scoring failed: {e}")
            return 0.5


# Global instance
llm_client = LLMClient()
