"""Main Athena agent loop — orchestrates all components."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

from athena.core.memory import MemoryManager, EpisodicMemory
from athena.core.retrieval import RetrievalEngine
from athena.core.decision import DecisionEngine, Decision
from athena.models.llm import LLMClient, llm_client
from athena.utils.security import sanitize_input, validate_module, generate_session_id
from athena.utils.logger import get_logger

logger = get_logger("agent")


@dataclass
class ChatResponse:
    """Response from the agent."""

    response: str
    confidence: float
    module: str
    session_id: str
    memories_used: int = 0
    fallback: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "response": self.response,
            "confidence": self.confidence,
            "module": self.module,
            "session_id": self.session_id,
            "memories_used": self.memories_used,
            "fallback": self.fallback,
            "timestamp": self.timestamp,
        }


class AthenaAgent:
    """
    Main agent class that orchestrates memory, retrieval, decision, and LLM components.

    Usage:
        agent = AthenaAgent(memory_manager, retrieval_engine, decision_engine)
        response = await agent.chat("How should I handle price objections?", module="sales")
    """

    def __init__(
        self,
        memory: MemoryManager,
        retrieval: RetrievalEngine,
        decision: DecisionEngine,
        llm: LLMClient = llm_client,
    ) -> None:
        self._memory = memory
        self._retrieval = retrieval
        self._decision = decision
        self._llm = llm
        self._started_at: float = time.time()

    @property
    def uptime_seconds(self) -> float:
        """Get agent uptime in seconds."""
        return time.time() - self._started_at

    async def chat(
        self,
        message: str,
        module: str = "general",
        session_id: Optional[str] = None,
        store_memory: bool = True,
    ) -> ChatResponse:
        """
        Process a chat message and return a response.

        Args:
            message: User's message/query.
            module: Module context (sales/trading/general).
            session_id: Session identifier (auto-generated if None).
            store_memory: Whether to store in episodic memory.

        Returns:
            ChatResponse with agent's reply.
        """
        # Validate and sanitize
        module = validate_module(module)
        message = sanitize_input(message)

        # Generate session ID if not provided
        if not session_id:
            session_id = generate_session_id()
            await self._memory.create_session(session_id, module)

        logger.info(f"Chat [{module}] session={session_id}: {message[:100]}...")

        # Analyze and get decision
        decision = await self._decision.analyze(
            query=message,
            module=module,
            session_id=session_id,
        )

        # Track memories used
        memories = await self._retrieval.retrieve(message, module, session_id)
        memories_used = len(memories)

        # Build response
        response_text = self._format_response(decision)

        # Store in episodic memory
        if store_memory:
            episodic = EpisodicMemory(
                session_id=session_id,
                module=module,
                query=message,
                response=response_text,
                confidence=decision.confidence,
                metadata={
                    "memories_used": memories_used,
                    "fallback": not self._llm.is_available,
                    "module": module,
                },
            )
            await self._memory.store_episodic(episodic)
            await self._memory.increment_session_messages(session_id)

        return ChatResponse(
            response=response_text,
            confidence=decision.confidence,
            module=module,
            session_id=session_id,
            memories_used=memories_used,
            fallback=not self._llm.is_available,
        )

    async def decide(
        self,
        context: str,
        options: list[str],
        module: str = "general",
        session_id: Optional[str] = None,
    ) -> Decision:
        """
        Make a decision between options.

        Args:
            context: Decision context.
            options: Available options.
            module: Module context.
            session_id: Optional session ID.

        Returns:
            Decision with selected option.
        """
        module = validate_module(module)
        context = sanitize_input(context)

        if not session_id:
            session_id = generate_session_id()

        logger.info(f"Decision [{module}]: {context[:100]}...")

        decision = await self._decision.evaluate_options(
            context=context,
            options=options,
            module=module,
            session_id=session_id,
        )

        return decision

    async def add_knowledge(
        self,
        module: str,
        category: str,
        key: str,
        value: str,
        confidence: float = 0.5,
        tags: Optional[list[str]] = None,
    ) -> int:
        """
        Add knowledge to semantic memory.

        Args:
            module: Module.
            category: Knowledge category.
            key: Knowledge key.
            value: Knowledge value.
            confidence: Confidence level.
            tags: Optional tags.

        Returns:
            Memory ID.
        """
        from athena.core.memory import SemanticMemory

        module = validate_module(module)

        memory = SemanticMemory(
            module=module,
            category=sanitize_input(category),
            key=sanitize_input(key),
            value=sanitize_input(value),
            confidence=confidence,
            source="user",
            tags=tags or [],
        )

        memory_id = await self._memory.store_semantic(memory)
        logger.info(f"Added knowledge: {module}/{category}/{key} (id={memory_id})")
        return memory_id

    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[EpisodicMemory]:
        """
        Get chat history for a session.

        Args:
            session_id: Session identifier.
            limit: Maximum entries.

        Returns:
            List of episodic memories.
        """
        return await self._memory.get_episodic(session_id=session_id, limit=limit)

    async def provide_feedback(
        self,
        memory_id: int,
        outcome: str,
        score: float,
    ) -> None:
        """
        Provide feedback on a past interaction.

        Args:
            memory_id: Episodic memory ID.
            outcome: Outcome description.
            score: Outcome score (0-1).
        """
        await self._memory.update_episodic_outcome(memory_id, sanitize_input(outcome), score)
        logger.info(f"Feedback provided for memory {memory_id}: score={score}")

    def _format_response(self, decision: Decision) -> str:
        """Format decision into a readable response."""
        parts: list[str] = []

        parts.append(decision.recommendation)

        if decision.risks:
            parts.append("\n**Risks:**")
            for risk in decision.risks:
                parts.append(f"- {risk}")

        if decision.supporting_evidence:
            parts.append("\n**Based on:**")
            for ev in decision.supporting_evidence[:3]:
                parts.append(f"- {ev[:150]}")

        return "\n".join(parts)
