"""Sales and Trading knowledge base with seeded domain knowledge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class KnowledgeFact:
    """A single knowledge fact."""

    module: str
    category: str
    key: str
    value: str
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)


class KnowledgeBase:
    """
    Specialized knowledge base for sales and trading domains.

    Provides domain-specific facts, rules, and best practices
    that are seeded into semantic memory on first run.
    """

    def __init__(self) -> None:
        self._facts: list[KnowledgeFact] = []
        self._load_sales_knowledge()
        self._load_trading_knowledge()
        self._load_general_knowledge()

    def _load_sales_knowledge(self) -> None:
        """Load sales domain knowledge."""
        facts: list[KnowledgeFact] = [
            # Sales Methodologies
            KnowledgeFact(
                module="sales",
                category="methodology",
                key="bant_qualification",
                value=(
                    "BANT Framework: Budget (does the prospect have allocated funds?), "
                    "Authority (is this person the decision-maker?), Need (is there a "
                    "compelling business need?), Timeline (is there a defined purchase "
                    "timeline?). Score each 1-5; total 16+ indicates a qualified lead."
                ),
                confidence=0.9,
                tags=["qualification", "bant", "leads"],
            ),
            KnowledgeFact(
                module="sales",
                category="methodology",
                key="challenger_sale",
                value=(
                    "The Challenger Sale: Top performers teach customers something new "
                    "about their business, tailor the message to the customer's specific "
                    "needs, and take control of the sale conversation. The combination "
                    "of tailored teaching and constructive tension drives 53% of "
                    "high-performer win rates."
                ),
                confidence=0.85,
                tags=["methodology", "challenger", "teaching"],
            ),
            KnowledgeFact(
                module="sales",
                category="methodology",
                key="spin_selling",
                value=(
                    "SPIN Selling: Situation questions (understand context), Problem "
                    "questions (identify pain), Implication questions (amplify pain), "
                    "Need-payoff questions (let prospect articulate the solution value). "
                    "Avoid leading with Situation questions in complex sales."
                ),
                confidence=0.85,
                tags=["methodology", "spin", "discovery"],
            ),
            # Negotiation
            KnowledgeFact(
                module="sales",
                category="negotiation",
                key="anchoring",
                value=(
                    "Anchoring Effect: The first number put on the table disproportionately "
                    "influences the final outcome. Always anchor aggressively but "
                    "credibly. If you go first, set expectations. If they go first, "
                    "re-anchor immediately with data."
                ),
                confidence=0.9,
                tags=["negotiation", "anchoring", "psychology"],
            ),
            KnowledgeFact(
                module="sales",
                category="negotiation",
                key="concession_strategy",
                value=(
                    "Concession Strategy: Never give a concession without getting one "
                    "in return. Concede in decreasing increments (e.g., 5%, then 2%, "
                    "then 1%) to signal you're reaching your limit. Always trade "
                    "concessions; never give them unilaterally."
                ),
                confidence=0.9,
                tags=["negotiation", "concessions", "tactics"],
            ),
            # Closing
            KnowledgeFact(
                module="sales",
                category="closing",
                key="assumptive_close",
                value=(
                    "Assumptive Close: Proceed as if the prospect has already decided. "
                    "Use phrases like 'When would you like to start?' or 'Which "
                    "implementation schedule works for your team?' rather than "
                    "'Would you like to proceed?'"
                ),
                confidence=0.8,
                tags=["closing", "assumptive", "tactics"],
            ),
            KnowledgeFact(
                module="sales",
                category="closing",
                key="urgency_creation",
                value=(
                    "Urgency Creation: Legitimate urgency comes from real events: "
                    "price increases, limited capacity, expiring incentives, competitive "
                    "threats. Manufactured urgency damages trust. Always tie urgency to "
                    "the prospect's actual business drivers."
                ),
                confidence=0.85,
                tags=["closing", "urgency", "tactics"],
            ),
            # Account Management
            KnowledgeFact(
                module="sales",
                category="account_management",
                key="expansion_metrics",
                value=(
                    "Expansion Indicators: Look for usage growth >20% QoQ, new "
                    "department adoption, executive sponsor engagement, integration "
                    "requests. These signal readiness for upsell/cross-sell conversations."
                ),
                confidence=0.8,
                tags=["account_management", "expansion", "upsell"],
            ),
            # Objection Handling
            KnowledgeFact(
                module="sales",
                category="objection_handling",
                key="feel_felt_found",
                value=(
                    "Feel-Felt-Found Framework: 'I understand how you feel. Others "
                    "have felt the same way. What they found was...' This validates "
                    "concerns, normalizes them, and reframes with evidence."
                ),
                confidence=0.8,
                tags=["objections", "feel_felt_found", "reframing"],
            ),
        ]

        self._facts.extend(facts)

    def _load_trading_knowledge(self) -> None:
        """Load trading domain knowledge."""
        facts: list[KnowledgeFact] = [
            # Risk Management
            KnowledgeFact(
                module="trading",
                category="risk_management",
                key="position_sizing",
                value=(
                    "Position Sizing: Risk no more than 1-2% of total capital on any "
                    "single trade. Formula: Position Size = (Account Risk Amount) / "
                    "(Entry Price - Stop Loss Price). For a $100K account risking 1% "
                    "($1,000) with a $5 stop: position = 200 shares."
                ),
                confidence=0.95,
                tags=["risk", "position_sizing", "capital"],
            ),
            KnowledgeFact(
                module="trading",
                category="risk_management",
                key="risk_reward_ratio",
                value=(
                    "Risk-Reward Ratio: Minimum 1:2 ratio recommended. If risking "
                    "$1 per share, target at least $2 profit. With 1:2 ratio, you "
                    "can be right only 34% of the time to be profitable. Higher "
                    "ratios (1:3+) provide more margin for error."
                ),
                confidence=0.9,
                tags=["risk", "reward", "ratio"],
            ),
            KnowledgeFact(
                module="trading",
                category="risk_management",
                key="stop_loss_placement",
                value=(
                    "Stop Loss Placement: Place stops below structural support "
                    "(not arbitrary percentages). Use ATR-based stops (e.g., 2x ATR) "
                    "to account for volatility. Never widen a stop loss once placed; "
                    "only tighten as price moves favorably."
                ),
                confidence=0.9,
                tags=["stops", "risk", "atr"],
            ),
            # Technical Analysis
            KnowledgeFact(
                module="trading",
                category="technical",
                key="trend_confirmation",
                value=(
                    "Trend Confirmation: Use multiple timeframes. For a long trade: "
                    "monthly/weekly must be bullish, daily for setup, intraday for "
                    "entry. Moving averages (20, 50, 200 EMA) provide dynamic "
                    "support/resistance. Price above all three = strong uptrend."
                ),
                confidence=0.85,
                tags=["trend", "timeframes", "moving_averages"],
            ),
            KnowledgeFact(
                module="trading",
                category="technical",
                key="volume_confirmation",
                value=(
                    "Volume Confirmation: Price moves on low volume are suspect; "
                    "high-volume moves are institutional. Breakout above resistance "
                    "needs 1.5x average volume to confirm. Declining volume in an "
                    "uptrend signals exhaustion and potential reversal."
                ),
                confidence=0.85,
                tags=["volume", "confirmation", "breakout"],
            ),
            # Market Structure
            KnowledgeFact(
                module="trading",
                category="market_structure",
                key="support_resistance",
                value=(
                    "Support/Resistance: Key levels are where price has reversed "
                    "multiple times. The more touches, the more significant. When "
                    "resistance breaks, it becomes support (and vice versa). Round "
                    "numbers (100, 1000) act as psychological S/R levels."
                ),
                confidence=0.85,
                tags=["support", "resistance", "levels"],
            ),
            # Trading Psychology
            KnowledgeFact(
                module="trading",
                category="psychology",
                key="loss_aversion",
                value=(
                    "Loss Aversion Bias: Traders feel losses 2x more intensely than "
                    "gains. This leads to holding losers too long and cutting winners "
                    "short. Mitigate with pre-defined exit rules and automated stops. "
                    "Your plan should remove emotion from exit decisions."
                ),
                confidence=0.85,
                tags=["psychology", "bias", "loss_aversion"],
            ),
            KnowledgeFact(
                module="trading",
                category="psychology",
                key="journal_importance",
                value=(
                    "Trading Journal: Record entry reason, emotions, exit, and "
                    "outcome for every trade. Review weekly to identify patterns in "
                    "your mistakes. Top performers journal consistently; it's the "
                    "single highest-ROI activity for improvement."
                ),
                confidence=0.85,
                tags=["journal", "psychology", "improvement"],
            ),
            # Portfolio
            KnowledgeFact(
                module="trading",
                category="portfolio",
                key="correlation",
                value=(
                    "Correlation Management: Diversify across uncorrelated assets. "
                    "A portfolio of 5 tech stocks isn't diversified if correlation "
                    "is 0.9+. Mix stocks, bonds, commodities, and potentially "
                    "uncorrelated strategies. Target correlation <0.3 between holdings."
                ),
                confidence=0.85,
                tags=["diversification", "correlation", "portfolio"],
            ),
        ]

        self._facts.extend(facts)

    def _load_general_knowledge(self) -> None:
        """Load general business/finance knowledge."""
        facts: list[KnowledgeFact] = [
            KnowledgeFact(
                module="general",
                category="finance",
                key="compound_interest",
                value=(
                    "Compound Interest: Money grows exponentially over time. Rule "
                    "of 72: divide 72 by annual return rate to get doubling time. "
                    "At 8% returns, money doubles every 9 years. Starting early "
                    "matters more than contributing large amounts later."
                ),
                confidence=0.95,
                tags=["finance", "compound", "growth"],
            ),
            KnowledgeFact(
                module="general",
                category="finance",
                key="opportunity_cost",
                value=(
                    "Opportunity Cost: Every choice has a hidden cost — the value "
                    "of the next best alternative. In trading, capital deployed in "
                    "one position can't be used elsewhere. In sales, time spent on "
                    "unqualified leads is time not spent on opportunities."
                ),
                confidence=0.9,
                tags=["finance", "opportunity_cost", "decision_making"],
            ),
            KnowledgeFact(
                module="general",
                category="communication",
                key="active_listening",
                value=(
                    "Active Listening: In both sales and trading communications, "
                    "listen more than you speak. Paraphrase to confirm understanding. "
                    "Ask open-ended questions. The person who asks questions controls "
                    "the conversation."
                ),
                confidence=0.85,
                tags=["communication", "listening", "soft_skills"],
            ),
        ]

        self._facts.extend(facts)

    def get_all_facts(self) -> list[KnowledgeFact]:
        """Get all knowledge facts."""
        return self._facts.copy()

    def get_facts_by_module(self, module: str) -> list[KnowledgeFact]:
        """Get facts filtered by module."""
        return [f for f in self._facts if f.module == module]

    def get_facts_by_category(self, category: str) -> list[KnowledgeFact]:
        """Get facts filtered by category."""
        return [f for f in self._facts if f.category == category]

    def search_facts(self, query: str) -> list[KnowledgeFact]:
        """Search facts by keyword in key, value, or tags."""
        query_lower = query.lower()
        return [
            f for f in self._facts
            if query_lower in f.key.lower()
            or query_lower in f.value.lower()
            or any(query_lower in t.lower() for t in f.tags)
        ]


# Global instance
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """Get or create global knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
