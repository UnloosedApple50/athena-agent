"""Tests for the knowledge base."""

from __future__ import annotations

import pytest
from athena.knowledge.base import KnowledgeBase, KnowledgeFact, get_knowledge_base


class TestKnowledgeBase:
    """Tests for the knowledge base."""

    def test_singleton(self) -> None:
        """Test that get_knowledge_base returns same instance."""
        kb1 = get_knowledge_base()
        kb2 = get_knowledge_base()
        assert kb1 is kb2

    def test_get_all_facts(self) -> None:
        """Test getting all knowledge facts."""
        kb = KnowledgeBase()
        facts = kb.get_all_facts()
        assert len(facts) > 0

    def test_sales_facts_exist(self) -> None:
        """Test that sales facts are loaded."""
        kb = KnowledgeBase()
        sales_facts = kb.get_facts_by_module("sales")
        assert len(sales_facts) > 0

    def test_trading_facts_exist(self) -> None:
        """Test that trading facts are loaded."""
        kb = KnowledgeBase()
        trading_facts = kb.get_facts_by_module("trading")
        assert len(trading_facts) > 0

    def test_general_facts_exist(self) -> None:
        """Test that general facts are loaded."""
        kb = KnowledgeBase()
        general_facts = kb.get_facts_by_module("general")
        assert len(general_facts) > 0

    def test_facts_by_category(self) -> None:
        """Test filtering facts by category."""
        kb = KnowledgeBase()
        closing_facts = kb.get_facts_by_category("closing")
        assert len(closing_facts) > 0

    def test_search_facts(self) -> None:
        """Test searching facts by keyword."""
        kb = KnowledgeBase()
        results = kb.search_facts("closing")
        assert len(results) > 0

    def test_fact_structure(self) -> None:
        """Test that facts have correct structure."""
        kb = KnowledgeBase()
        facts = kb.get_all_facts()
        fact = facts[0]
        assert isinstance(fact, KnowledgeFact)
        assert fact.module in ("sales", "trading", "general")
        assert len(fact.category) > 0
        assert len(fact.key) > 0
        assert len(fact.value) > 0
        assert 0.0 <= fact.confidence <= 1.0
        assert isinstance(fact.tags, list)

    def test_fact_confidence_levels(self) -> None:
        """Test that facts have reasonable confidence levels."""
        kb = KnowledgeBase()
        facts = kb.get_all_facts()
        for fact in facts:
            assert fact.confidence >= 0.5  # All seeded facts should be >= 0.5
