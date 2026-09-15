"""Context retrieval engine combining keyword + LLM-based relevance."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from athena.core.memory import MemoryManager, SemanticMemory
from athena.models.llm import LLMClient, llm_client
from athena.utils.logger import get_logger

logger = get_logger("retrieval")


@dataclass
class RetrievalResult:
    """A retrieved memory with relevance score."""

    source: str  # "episodic" or "semantic"
    content: str
    relevance: float
    memory_id: Optional[int] = None
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


class RetrievalEngine:
    """
    Retrieves relevant context from memory for a given query.

    Strategy:
    1. Keyword matching (fast) to get candidate set
    2. LLM-based re-ranking (when available) for top candidates
    3. Combine with working memory context
    """

    def __init__(self, memory: MemoryManager, llm: LLMClient = llm_client) -> None:
        self._memory = memory
        self._llm = llm

    async def retrieve(
        self,
        query: str,
        module: str = "general",
        session_id: Optional[str] = None,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant memories for a query.

        Args:
            query: The query to find context for.
            module: Module context.
            session_id: Optional session for episodic retrieval.
            top_k: Maximum number of results.

        Returns:
            List of retrieval results sorted by relevance.
        """
        results: list[RetrievalResult] = []

        # 1. Keyword-based retrieval from semantic memory
        semantic_candidates = await self._keyword_search_semantic(query, module)
        results.extend(semantic_candidates)

        # 2. Keyword-based retrieval from episodic memory
        episodic_candidates = await self._keyword_search_episodic(query, module, session_id)
        results.extend(episodic_candidates)

        # 3. LLM re-ranking (if available)
        if self._llm.is_available and results:
            results = await self._llm_rerank(query, results)

        # 4. Sort by relevance and return top_k
        results.sort(key=lambda r: r.relevance, reverse=True)
        return results[:top_k]

    async def _keyword_search_semantic(
        self,
        query: str,
        module: str,
    ) -> list[RetrievalResult]:
        """Search semantic memory using keyword matching."""
        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        # Fetch all relevant semantic memories
        memories = await self._memory.get_semantic(module=module, limit=100)

        results: list[RetrievalResult] = []
        for mem in memories:
            score = self._keyword_score(keywords, mem.value + " " + mem.key + " " + " ".join(mem.tags))
            if score > 0.1:
                results.append(RetrievalResult(
                    source="semantic",
                    content=f"[{mem.category}] {mem.key}: {mem.value}",
                    relevance=score * mem.confidence,
                    memory_id=mem.id,
                    metadata={
                        "category": mem.category,
                        "tags": mem.tags,
                        "source_type": mem.source,
                    },
                ))

        return results

    async def _keyword_search_episodic(
        self,
        query: str,
        module: str,
        session_id: Optional[str],
    ) -> list[RetrievalResult]:
        """Search episodic memory using keyword matching."""
        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        memories = await self._memory.get_episodic(
            session_id=session_id,
            module=module,
            limit=50,
        )

        results: list[RetrievalResult] = []
        for mem in memories:
            score = self._keyword_score(keywords, mem.query + " " + mem.response)
            if score > 0.1:
                results.append(RetrievalResult(
                    source="episodic",
                    content=f"Q: {mem.query}\nA: {mem.response}",
                    relevance=score * mem.confidence,
                    memory_id=mem.id,
                    metadata={
                        "session_id": mem.session_id,
                        "outcome": mem.outcome,
                    },
                ))

        return results

    async def _llm_rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """Re-rank candidates using LLM relevance scoring."""
        # Only re-rank top 10 to avoid too many LLM calls
        to_rerank = candidates[:10]

        for result in to_rerank:
            try:
                llm_score = await self._llm.score_relevance(query, result.content)
                # Combine keyword and LLM scores
                result.relevance = (result.relevance * 0.4) + (llm_score * 0.6)
            except Exception as e:
                logger.debug(f"LLM re-rank failed for result: {e}")
                # Keep original keyword score

        return candidates

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text."""
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again",
            "further", "then", "once", "and", "but", "or", "nor", "not",
            "so", "than", "too", "very", "just", "about", "this", "that",
            "these", "those", "it", "its", "i", "me", "my", "we", "our",
            "you", "your", "he", "him", "his", "she", "her", "they", "them",
            "their", "what", "which", "who", "whom", "when", "where", "why",
            "how", "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "no", "only", "own", "same", "than",
            "too", "very", "just", "because", "if", "while", "up", "down",
            "what's", "how's", "isn't", "don't", "won't", "shouldn't",
        }

        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]
        return keywords

    def _keyword_score(self, keywords: list[str], text: str) -> float:
        """
        Calculate keyword overlap score.

        Args:
            keywords: Query keywords.
            text: Text to score against.

        Returns:
            Score between 0.0 and 1.0.
        """
        if not keywords or not text:
            return 0.0

        text_lower = text.lower()
        text_words = set(re.findall(r'\b[a-zA-Z]{2,}\b', text_lower))

        if not text_words:
            return 0.0

        matches = sum(1 for kw in keywords if kw in text_words)
        return matches / len(keywords)
