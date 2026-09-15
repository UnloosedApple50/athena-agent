"""Adaptation engine — adjusts agent behavior based on feedback patterns."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from athena.db.database import Database
from athena.utils.logger import get_logger

logger = get_logger("training.adaptation")


@dataclass
class AdaptationRule:
    """A rule derived from feedback patterns."""

    id: str
    pattern: str
    action: str
    confidence: float = 0.5
    applied_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    module: str = "general"
    source_feedback_ids: list[str] = field(default_factory=list)


class AdaptationManager:
    """Adapts agent behavior based on feedback patterns."""

    def __init__(self, database: Optional[Database] = None) -> None:
        self._db = database
        self._rules: dict[str, AdaptationRule] = {}
        self._adaptation_count: int = 0

    async def analyze_feedback(self, feedback_entries: list[dict[str, Any]]) -> list[AdaptationRule]:
        """
        Analyze feedback patterns and generate adaptation rules.
        
        Args:
            feedback_entries: List of feedback dictionaries.
            
        Returns:
            List of new adaptation rules.
        """
        rules: list[AdaptationRule] = []

        # Group by module
        by_module: dict[str, list[dict[str, Any]]] = {}
        for entry in feedback_entries:
            module = entry.get("module", "general")
            by_module.setdefault(module, []).append(entry)

        for module, entries in by_module.items():
            # Find common patterns in low-rated feedback
            low_rated = [e for e in entries if e.get("rating", 3) <= 2]
            if not low_rated:
                continue

            # Extract common keywords from corrections
            corrections = [
                e.get("correction", "")
                for e in low_rated
                if e.get("correction")
            ]

            if corrections:
                rule = AdaptationRule(
                    id=f"rule_{module}_{int(time.time())}",
                    pattern=f"low_rating_{module}",
                    action=f"Review and improve {module} responses",
                    confidence=min(len(corrections) * 0.1, 1.0),
                    module=module,
                    source_feedback_ids=[e.get("id", "") for e in low_rated[:5]],
                )
                rules.append(rule)
                self._rules[rule.id] = rule

        # Analyze categories
        by_category: dict[str, list[dict[str, Any]]] = {}
        for entry in feedback_entries:
            category = entry.get("category", "general")
            by_category.setdefault(category, []).append(entry)

        for category, entries in by_category.items():
            avg_rating = sum(e.get("rating", 3) for e in entries) / len(entries)
            if avg_rating < 2.5:
                rule = AdaptationRule(
                    id=f"rule_{category}_{int(time.time())}",
                    pattern=f"low_rating_{category}",
                    action=f"Prioritize improvement in {category} category",
                    confidence=0.7,
                    module=category,
                )
                rules.append(rule)
                self._rules[rule.id] = rule

        self._adaptation_count += len(rules)
        logger.info(f"Generated {len(rules)} adaptation rules from {len(feedback_entries)} feedback entries")
        return rules

    async def apply_adaptations(self) -> dict[str, Any]:
        """
        Apply all active adaptation rules.
        
        Returns:
            Summary of applied adaptations.
        """
        applied = 0
        for rule in self._rules.values():
            if rule.confidence >= 0.5:
                rule.applied_count += 1
                applied += 1

        return {
            "total_rules": len(self._rules),
            "applied": applied,
            "skipped": len(self._rules) - applied,
        }

    def get_rules(self, module: Optional[str] = None) -> list[AdaptationRule]:
        """Get adaptation rules, optionally filtered by module."""
        rules = list(self._rules.values())
        if module:
            rules = [r for r in rules if r.module == module]
        return rules

    def get_rule(self, rule_id: str) -> Optional[AdaptationRule]:
        """Get a specific rule by ID."""
        return self._rules.get(rule_id)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an adaptation rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """Get adaptation statistics."""
        return {
            "total_rules": len(self._rules),
            "total_adaptations": self._adaptation_count,
            "modules_covered": len(set(r.module for r in self._rules.values())),
            "avg_confidence": round(
                sum(r.confidence for r in self._rules.values()) / max(len(self._rules), 1),
                2,
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        """Get all data as dictionary."""
        return {
            "stats": self.get_stats(),
            "rules": [
                {
                    "id": r.id,
                    "pattern": r.pattern,
                    "action": r.action,
                    "confidence": r.confidence,
                    "module": r.module,
                    "applied_count": r.applied_count,
                }
                for r in self._rules.values()
            ],
        }


# Global instance
adaptation_manager = AdaptationManager()
