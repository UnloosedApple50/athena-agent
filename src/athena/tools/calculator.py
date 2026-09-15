"""Calculator tool — math and financial calculations."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CalculationResult:
    """Result of a calculation."""

    expression: str
    result: float | str
    success: bool = True
    error: Optional[str] = None


class Calculator:
    """Math and financial calculations tool."""

    @staticmethod
    def evaluate(expression: str) -> CalculationResult:
        """
        Safely evaluate a mathematical expression.
        
        Args:
            expression: Math expression string.
            
        Returns:
            CalculationResult with result or error.
        """
        if not expression or not expression.strip():
            return CalculationResult(
                expression=expression,
                result="",
                success=False,
                error="Empty expression",
            )

        # Sanitize - only allow safe characters
        sanitized = re.sub(r'[^0-9+\-*/().eE\s,^%]', '', expression.strip())
        if not sanitized:
            return CalculationResult(
                expression=expression,
                result="",
                success=False,
                error="Invalid characters in expression",
            )

        # Replace ^ with ** for exponentiation
        sanitized = sanitized.replace('^', '**')

        # Allow math functions
        allowed_names: dict[str, Any] = {
            name: getattr(math, name)
            for name in dir(math)
            if not name.startswith('_')
        }

        try:
            result = eval(sanitized, {"__builtins__": {}}, allowed_names)  # noqa: S307
            return CalculationResult(
                expression=expression,
                result=result,
                success=True,
            )
        except Exception as e:
            return CalculationResult(
                expression=expression,
                result="",
                success=False,
                error=str(e),
            )

    @staticmethod
    def percentage(value: float, percent: float) -> float:
        """Calculate percentage of a value."""
        return value * (percent / 100)

    @staticmethod
    def percent_change(old: float, new: float) -> float:
        """Calculate percentage change."""
        if old == 0:
            return 0.0
        return ((new - old) / abs(old)) * 100

    @staticmethod
    def compound_interest(
        principal: float,
        rate: float,
        time_years: float,
        compounds_per_year: int = 12,
    ) -> float:
        """Calculate compound interest."""
        return principal * (1 + rate / 100 / compounds_per_year) ** (compounds_per_year * time_years)

    @staticmethod
    def simple_interest(principal: float, rate: float, time_years: float) -> float:
        """Calculate simple interest."""
        return principal * (1 + (rate / 100) * time_years)

    @staticmethod
    def roi(gain: float, cost: float) -> float:
        """Calculate return on investment as percentage."""
        if cost == 0:
            return 0.0
        return ((gain - cost) / cost) * 100

    @staticmethod
    def break_even(fixed_costs: float, price_per_unit: float, cost_per_unit: float) -> float:
        """Calculate break-even point in units."""
        if price_per_unit <= cost_per_unit:
            return float('inf')
        return fixed_costs / (price_per_unit - cost_per_unit)

    @staticmethod
    def profit_margin(revenue: float, costs: float) -> float:
        """Calculate profit margin as percentage."""
        if revenue == 0:
            return 0.0
        return ((revenue - costs) / revenue) * 100

    @staticmethod
    def weighted_average(values: list[float], weights: list[float]) -> float:
        """Calculate weighted average."""
        if len(values) != len(weights):
            raise ValueError("Values and weights must have same length")
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0
        return sum(v * w for v, w in zip(values, weights)) / total_weight

    @staticmethod
    def moving_average(data: list[float], window: int = 5) -> list[float]:
        """Calculate simple moving average."""
        if window > len(data):
            window = len(data)
        return [
            sum(data[i:i + window]) / window
            for i in range(len(data) - window + 1)
        ]

    @staticmethod
    def fibonacci(n: int) -> int:
        """Calculate nth Fibonacci number."""
        if n <= 0:
            return 0
        if n == 1:
            return 1
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b


# Global instance
calculator = Calculator()
