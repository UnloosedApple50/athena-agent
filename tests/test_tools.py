"""Tests for tools module."""

from __future__ import annotations

import pytest
from athena.tools.calculator import Calculator, CalculationResult
from athena.tools.converter import Converter, ConversionResult
from athena.tools.analyzer import Analyzer, TextAnalysis, DataStats


class TestCalculator:
    """Tests for Calculator."""

    def test_evaluate_basic(self):
        result = Calculator.evaluate("2 + 2")
        assert result.success
        assert result.result == 4

    def test_evaluate_complex(self):
        result = Calculator.evaluate("(10 + 5) * 2")
        assert result.success
        assert result.result == 30

    def test_evaluate_empty(self):
        result = Calculator.evaluate("")
        assert not result.success

    def test_evaluate_invalid(self):
        result = Calculator.evaluate("invalid +")
        assert not result.success

    def test_percentage(self):
        assert Calculator.percentage(100, 20) == 20.0

    def test_percent_change(self):
        assert Calculator.percent_change(100, 120) == 20.0
        assert Calculator.percent_change(100, 80) == -20.0

    def test_compound_interest(self):
        result = Calculator.compound_interest(1000, 5, 1)
        assert result > 1000

    def test_simple_interest(self):
        result = Calculator.simple_interest(1000, 5, 1)
        assert result == 1050.0

    def test_roi(self):
        assert Calculator.roi(120, 100) == 20.0

    def test_break_even(self):
        result = Calculator.break_even(1000, 50, 30)
        assert result == 50.0

    def test_profit_margin(self):
        assert Calculator.profit_margin(100, 70) == 30.0

    def test_weighted_average(self):
        result = Calculator.weighted_average([10, 20, 30], [1, 2, 3])
        assert result == (10 + 40 + 90) / 6

    def test_moving_average(self):
        result = Calculator.moving_average([1, 2, 3, 4, 5], 3)
        assert len(result) == 3
        assert result[0] == 2.0

    def test_fibonacci(self):
        assert Calculator.fibonacci(0) == 0
        assert Calculator.fibonacci(1) == 1
        assert Calculator.fibonacci(10) == 55


class TestConverter:
    """Tests for Converter."""

    def test_convert_length(self):
        result = Converter.convert(1, "m", "cm")
        assert result.success
        assert result.result == 100.0

    def test_convert_weight(self):
        result = Converter.convert(1, "kg", "g")
        assert result.success
        assert result.result == 1000.0

    def test_convert_temperature_c_to_f(self):
        result = Converter.convert(0, "c", "f")
        assert result.success
        assert abs(result.result - 32.0) < 0.01

    def test_convert_temperature_f_to_c(self):
        result = Converter.convert(32, "f", "c")
        assert result.success
        assert abs(result.result - 0.0) < 0.01

    def test_convert_currency(self):
        result = Converter.convert(100, "usd", "eur")
        assert result.success
        assert result.result > 0

    def test_convert_invalid(self):
        result = Converter.convert(1, "invalid", "also_invalid")
        assert not result.success

    def test_get_supported_units(self):
        units = Converter.get_supported_units()
        assert "length" in units
        assert "weight" in units
        assert "temperature" in units


class TestAnalyzer:
    """Tests for Analyzer."""

    def test_analyze_text(self):
        result = Analyzer.analyze_text("This is a test sentence for analysis.")
        assert isinstance(result, TextAnalysis)
        assert result.word_count > 0
        assert result.char_count > 0

    def test_analyze_text_sentiment_positive(self):
        result = Analyzer.analyze_text("This is great and amazing!")
        assert result.sentiment_estimate == "positive"

    def test_analyze_text_sentiment_negative(self):
        result = Analyzer.analyze_text("This is terrible and awful!")
        assert result.sentiment_estimate == "negative"

    def test_analyze_text_top_words(self):
        result = Analyzer.analyze_text("test test test word word other")
        assert len(result.top_words) > 0

    def test_analyze_data(self):
        result = Analyzer.analyze_data([1, 2, 3, 4, 5])
        assert isinstance(result, DataStats)
        assert result.count == 5
        assert result.mean == 3.0
        assert result.median == 3.0

    def test_analyze_data_empty(self):
        result = Analyzer.analyze_data([])
        assert result.count == 0

    def test_extract_entities(self):
        text = "Contact us at test@example.com or visit https://example.com"
        entities = Analyzer.extract_entities(text)
        assert len(entities["emails"]) > 0
        assert len(entities["urls"]) > 0

    def test_keyword_density(self):
        result = Analyzer.keyword_density("test test test word word other")
        assert len(result) > 0
