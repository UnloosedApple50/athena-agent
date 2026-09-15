"""Converter tool — unit and currency conversion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ConversionResult:
    """Result of a conversion."""

    value: float
    from_unit: str
    to_unit: str
    result: float
    success: bool = True
    error: Optional[str] = None


class Converter:
    """Unit and currency conversion tool."""

    # Length conversions (to meters)
    LENGTH_TO_METERS: dict[str, float] = {
        "mm": 0.001,
        "cm": 0.01,
        "m": 1.0,
        "km": 1000.0,
        "in": 0.0254,
        "ft": 0.3048,
        "yd": 0.9144,
        "mi": 1609.344,
        "nmi": 1852.0,
    }

    # Weight conversions (to grams)
    WEIGHT_TO_GRAMS: dict[str, float] = {
        "mg": 0.001,
        "g": 1.0,
        "kg": 1000.0,
        "oz": 28.3495,
        "lb": 453.592,
        "st": 6350.29,
        "ton": 1000000.0,
    }

    # Volume conversions (to liters)
    VOLUME_TO_LITERS: dict[str, float] = {
        "ml": 0.001,
        "l": 1.0,
        "gal": 3.78541,
        "qt": 0.946353,
        "pt": 0.473176,
        "cup": 0.236588,
        "floz": 0.0295735,
        "tbsp": 0.0147868,
        "tsp": 0.00492892,
    }

    # Temperature units (special handling)
    TEMPERATURE_UNITS: set[str] = {"c", "f", "k"}

    # Data size conversions (to bytes)
    DATA_TO_BYTES: dict[str, float] = {
        "b": 1.0,
        "kb": 1024.0,
        "mb": 1024.0 ** 2,
        "gb": 1024.0 ** 3,
        "tb": 1024.0 ** 4,
        "pb": 1024.0 ** 5,
    }

    # Time conversions (to seconds)
    TIME_TO_SECONDS: dict[str, float] = {
        "ms": 0.001,
        "s": 1.0,
        "min": 60.0,
        "h": 3600.0,
        "day": 86400.0,
        "week": 604800.0,
        "month": 2592000.0,  # 30 days
        "year": 31536000.0,  # 365 days
    }

    # Currency rates (relative to USD) - approximate, would be updated from API
    CURRENCY_TO_USD: dict[str, float] = {
        "usd": 1.0,
        "eur": 1.08,
        "gbp": 1.26,
        "jpy": 0.0067,
        "cny": 0.14,
        "cad": 0.74,
        "aud": 0.65,
        "chf": 1.13,
        "inr": 0.012,
        "brl": 0.20,
        "mxn": 0.058,
        "krw": 0.00075,
        "sgd": 0.75,
        "hkd": 0.13,
        "nok": 0.095,
        "sek": 0.096,
        "dkk": 0.145,
        "nzd": 0.61,
        "zar": 0.054,
        "try": 0.037,
        "rub": 0.011,
    }

    @classmethod
    def convert(cls, value: float, from_unit: str, to_unit: str) -> ConversionResult:
        """
        Convert a value between units.
        
        Args:
            value: Numeric value to convert.
            from_unit: Source unit.
            to_unit: Target unit.
            
        Returns:
            ConversionResult with converted value.
        """
        from_u = from_unit.lower().strip()
        to_u = to_unit.lower().strip()

        # Temperature special case
        if from_u in cls.TEMPERATURE_UNITS and to_u in cls.TEMPERATURE_UNITS:
            return cls._convert_temperature(value, from_u, to_u)

        # Currency
        if from_u in cls.CURRENCY_TO_USD and to_u in cls.CURRENCY_TO_USD:
            return cls._convert_currency(value, from_u, to_u)

        # Find conversion category
        for category in [cls.LENGTH_TO_METERS, cls.WEIGHT_TO_GRAMS, 
                        cls.VOLUME_TO_LITERS, cls.DATA_TO_BYTES, cls.TIME_TO_SECONDS]:
            if from_u in category and to_u in category:
                return cls._convert_linear(value, from_u, to_u, category)

        return ConversionResult(
            value=value,
            from_unit=from_unit,
            to_unit=to_unit,
            result=0.0,
            success=False,
            error=f"Cannot convert {from_unit} to {to_unit}",
        )

    @classmethod
    def _convert_linear(
        cls,
        value: float,
        from_u: str,
        to_u: str,
        factors: dict[str, float],
    ) -> ConversionResult:
        """Convert using linear factor table."""
        base_value = value * factors[from_u]
        result = base_value / factors[to_u]
        return ConversionResult(
            value=value,
            from_unit=from_u,
            to_unit=to_u,
            result=result,
        )

    @classmethod
    def _convert_temperature(cls, value: float, from_u: str, to_u: str) -> ConversionResult:
        """Convert temperature between C, F, K."""
        if from_u == to_u:
            return ConversionResult(value=value, from_unit=from_u, to_unit=to_u, result=value)

        # Convert to Celsius first
        if from_u == "c":
            celsius = value
        elif from_u == "f":
            celsius = (value - 32) * 5 / 9
        elif from_u == "k":
            celsius = value - 273.15
        else:
            return ConversionResult(
                value=value, from_unit=from_u, to_unit=to_u,
                result=0.0, success=False, error=f"Unknown temperature unit: {from_u}"
            )

        # Convert from Celsius to target
        if to_u == "c":
            result = celsius
        elif to_u == "f":
            result = celsius * 9 / 5 + 32
        elif to_u == "k":
            result = celsius + 273.15
        else:
            return ConversionResult(
                value=value, from_unit=from_u, to_unit=to_u,
                result=0.0, success=False, error=f"Unknown temperature unit: {to_u}"
            )

        return ConversionResult(value=value, from_unit=from_u, to_unit=to_u, result=result)

    @classmethod
    def _convert_currency(cls, value: float, from_u: str, to_u: str) -> ConversionResult:
        """Convert currency using approximate rates."""
        if from_u not in cls.CURRENCY_TO_USD or to_u not in cls.CURRENCY_TO_USD:
            return ConversionResult(
                value=value, from_unit=from_u, to_unit=to_u,
                result=0.0, success=False, error="Unknown currency",
            )

        usd_value = value * cls.CURRENCY_TO_USD[from_u]
        result = usd_value / cls.CURRENCY_TO_USD[to_u]

        return ConversionResult(value=value, from_unit=from_u, to_unit=to_u, result=result)

    @classmethod
    def get_supported_units(cls) -> dict[str, list[str]]:
        """Get all supported unit categories."""
        return {
            "length": sorted(cls.LENGTH_TO_METERS.keys()),
            "weight": sorted(cls.WEIGHT_TO_GRAMS.keys()),
            "volume": sorted(cls.VOLUME_TO_LITERS.keys()),
            "temperature": sorted(cls.TEMPERATURE_UNITS),
            "data": sorted(cls.DATA_TO_BYTES.keys()),
            "time": sorted(cls.TIME_TO_SECONDS.keys()),
            "currency": sorted(cls.CURRENCY_TO_USD.keys()),
        }


# Global instance
converter = Converter()
