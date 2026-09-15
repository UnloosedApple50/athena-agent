"""Decision engine for sales strategies and trading analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from athena.core.memory import MemoryManager, EpisodicMemory
from athena.core.retrieval import RetrievalEngine, RetrievalResult
from athena.models.llm import LLMClient, llm_client
from athena.utils.logger import get_logger

logger = get_logger("decision")


@dataclass
class Decision:
    """A decision or recommendation."""

    context: str
    recommendation: str
    confidence: float
    reasoning: str
    module: str
    options: Optional[list[str]] = None
    selected_option: Optional[str] = None
    risks: Optional[list[str]] = None
    supporting_evidence: Optional[list[str]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "context": self.context,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "module": self.module,
            "options": self.options or [],
            "selected_option": self.selected_option,
            "risks": self.risks or [],
            "supporting_evidence": self.supporting_evidence or [],
        }


class DecisionEngine:
    """
    Makes decisions and recommendations based on context, memory, and rules.

    Supports:
    - Sales strategy recommendations
    - Trading analysis
    - Risk assessment
    - General advisory
    """

    # Rule-based patterns for when LLM is unavailable
    SALES_RULES: list[dict[str, Any]] = [
        {
            "pattern": r"\b(discount|pricing|price)\b",
            "category": "pricing_strategy",
            "advice": "Consider value-based pricing over discounting. Anchor to ROI, not cost.",
        },
        {
            "pattern": r"\b(objection|pushback|resistance)\b",
            "category": "objection_handling",
            "advice": "Use the Feel-Felt-Found framework. Acknowledge, empathize, reframe.",
        },
        {
            "pattern": r"\b(close|closing|deal)\b",
            "category": "closing",
            "advice": "Create urgency through scarcity or timeline. Use assumptive close techniques.",
        },
        {
            "pattern": r"\b(lead|prospect|pipeline)\b",
            "category": "prospecting",
            "advice": "Qualify using BANT (Budget, Authority, Need, Timeline). Focus on high-probability leads.",
        },
        {
            "pattern": r"\b(negotiation|negotiate|terms)\b",
            "category": "negotiation",
            "advice": "Never give without getting. Trade concessions, don't give them away.",
        },
    ]

    TRADING_RULES: list[dict[str, Any]] = [
        {
            "pattern": r"\b(risk|stop.?loss|position.?size)\b",
            "category": "risk_management",
            "advice": "Never risk more than 2% per trade. Always use stop losses.",
        },
        {
            "pattern": r"\b(trend|momentum|breakout)\b",
            "category": "trend_analysis",
            "advice": "Trade with the trend. Use multiple timeframe analysis for confirmation.",
        },
        {
            "pattern": r"\b(diversif|portfolio|allocation)\b",
            "category": "portfolio",
            "advice": "Diversify across uncorrelated assets. Rebalance quarterly.",
        },
        {
            "pattern": r"\b(support|resistance|level)\b",
            "category": "technical",
            "advice": "Wait for confirmation at key levels. Volume validates price action.",
        },
        {
            "pattern": r"\b(sentiment|fear|greed|news)\b",
            "category": "sentiment",
            "advice": "Contrarian at extremes. Don't trade the news, trade the reaction.",
        },
    ]

    def __init__(
        self,
        memory: MemoryManager,
        retrieval: RetrievalEngine,
        llm: LLMClient = llm_client,
    ) -> None:
        self._memory = memory
        self._retrieval = retrieval
        self._llm = llm

    async def analyze(
        self,
        query: str,
        module: str = "general",
        session_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> Decision:
        """
        Analyze a query and produce a decision/recommendation.

        Args:
            query: The query to analyze.
            module: Module context (sales/trading/general).
            session_id: Optional session ID.
            context: Additional context data.

        Returns:
            A Decision with recommendation and reasoning.
        """
        # Retrieve relevant memories
        memories = await self._retrieval.retrieve(query, module, session_id)

        # Build context for decision
        memory_context = self._format_memories(memories)

        if self._llm.is_available:
            return await self._llm_decide(query, module, memories, memory_context, context)
        else:
            return self._rule_decide(query, module, memories, memory_context)

    async def _llm_decide(
        self,
        query: str,
        module: str,
        memories: list[RetrievalResult],
        memory_context: str,
        extra_context: Optional[dict[str, Any]],
    ) -> Decision:
        """Use LLM for decision making."""
        system = self._build_system_prompt(module, memory_context)

        extra = ""
        if extra_context:
            extra = f"\n\nAdditional Context:\n{json.dumps(extra_context, indent=2)}"

        try:
            response = await self._llm.generate(
                system,
                query + extra,
                temperature=0.3,
                max_tokens=1024,
            )

            # Parse structured output from LLM
            recommendation = response.content
            confidence = response.confidence

            # Try to extract structured data
            if "{" in response.content:
                try:
                    # Look for JSON in response
                    start = response.content.index("{")
                    end = response.content.rindex("}") + 1
                    data = json.loads(response.content[start:end])
                    recommendation = data.get("recommendation", response.content[:500])
                    confidence = data.get("confidence", confidence)
                except json.JSONDecodeError:
                    pass

            return Decision(
                context=query,
                recommendation=recommendation,
                confidence=confidence,
                reasoning=f"Based on {len(memories)} relevant memory entries and domain knowledge.",
                module=module,
                supporting_evidence=[m.content for m in memories[:3]],
            )

        except Exception as e:
            logger.warning(f"LLM decision failed, falling back to rules: {e}")
            return self._rule_decide(query, module, memories, memory_context)

    def _rule_decide(
        self,
        query: str,
        module: str,
        memories: list[RetrievalResult],
        memory_context: str,
    ) -> Decision:
        """Rule-based decision fallback."""
        import re

        rules = self.SALES_RULES if module == "sales" else self.TRADING_RULES if module == "trading" else []

        recommendations: list[str] = []
        for rule in rules:
            if re.search(rule["pattern"], query, re.IGNORECASE):
                recommendations.append(f"[{rule['category']}] {rule['advice']}")

        # Also check semantic memories for matching rules
        for mem in memories:
            if mem.metadata.get("category") in ("strategy", "rule", "best_practice"):
                recommendations.append(mem.content)

        if recommendations:
            return Decision(
                context=query,
                recommendation="\n\n".join(recommendations[:3]),
                confidence=0.6,
                reasoning=f"Rule-based analysis matching {len(recommendations)} patterns from domain knowledge.",
                module=module,
                supporting_evidence=[m.content for m in memories[:3]],
            )

        # Generic response
        return Decision(
            context=query,
            recommendation=(
                f"I understand you're asking about {module} topics. "
                "While I don't have a specific rule for this exact query, "
                "I recommend: 1) Gather more data, 2) Consider multiple scenarios, "
                "3) Consult domain-specific knowledge base, 4) Review past similar cases."
            ),
            confidence=0.4,
            reasoning="No specific pattern match. Providing general advisory guidance.",
            module=module,
            supporting_evidence=[m.content for m in memories[:3]] if memories else None,
        )

    async def evaluate_options(
        self,
        context: str,
        options: list[str],
        module: str = "general",
        session_id: Optional[str] = None,
    ) -> Decision:
        """
        Evaluate multiple options and recommend one.

        Args:
            context: Decision context.
            options: Available options.
            module: Module context.
            session_id: Optional session ID.

        Returns:
            Decision with selected option.
        """
        query = f"Evaluate these options and recommend the best:\n" + "\n".join(f"- {o}" for o in options)

        decision = await self.analyze(query, module, session_id)
        decision.options = options

        # Simple scoring for fallback
        if not self._llm.is_available and options:
            # Score options based on keyword matches with memories
            scored: list[tuple[float, str]] = []
            for opt in options:
                score = 0.0
                for mem in await self._retrieval.retrieve(opt, module, session_id, top_k=3):
                    score += mem.relevance
                scored.append((score, opt))

            scored.sort(reverse=True)
            if scored:
                decision.selected_option = scored[0][1]
                decision.recommendation = f"Recommended option: {scored[0][1]}"

        return decision

    def _build_system_prompt(self, module: str, memory_context: str) -> str:
        """Build system prompt for LLM decision making."""
        module_prompts = {
            "sales": (
                "You are an expert sales strategist with deep knowledge of B2B sales, "
                "negotiation tactics, deal management, and customer psychology. "
                "Provide actionable, specific recommendations based on best practices."
            ),
            "trading": (
                "You are an experienced trading analyst with expertise in risk management, "
                "technical analysis, and market dynamics. "
                "Provide data-informed recommendations with clear risk assessments."
            ),
            "general": (
                "You are a knowledgeable financial and business advisor. "
                "Provide clear, practical recommendations based on sound principles."
            ),
        }

        base = module_prompts.get(module, module_prompts["general"])

        return f"""{base}

Relevant Context from Memory:
{memory_context if memory_context else "No relevant past interactions found."}

Provide your analysis in this format:
1. Key Insight
2. Recommendation
3. Risks/Considerations
4. Confidence (0-1)

Be concise and actionable."""

    def _format_memories(self, memories: list[RetrievalResult]) -> str:
        """Format retrieved memories for context."""
        if not memories:
            return ""

        parts: list[str] = []
        for i, mem in enumerate(memories[:5], 1):
            parts.append(f"[{i}] ({mem.source}) {mem.content[:200]}")

        return "\n".join(parts)
