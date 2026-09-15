"""Analyzer tool — text and data analysis utilities."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TextAnalysis:
    """Results of text analysis."""

    word_count: int
    char_count: int
    sentence_count: int
    avg_word_length: float
    avg_sentence_length: float
    top_words: list[tuple[str, int]] = field(default_factory=list)
    sentiment_estimate: str = "neutral"
    language: str = "unknown"


@dataclass
class DataStats:
    """Basic statistics for numeric data."""

    count: int
    mean: float
    median: float
    std_dev: float
    minimum: float
    maximum: float
    total: float


class Analyzer:
    """Text and data analysis tool."""

    # Common English stop words
    STOP_WORDS: set[str] = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
        "from", "as", "into", "through", "during", "before", "after", "above",
        "below", "between", "under", "again", "further", "then", "once", "here",
        "there", "when", "where", "why", "how", "all", "both", "each", "few",
        "more", "most", "other", "some", "such", "no", "nor", "not", "only",
        "own", "same", "so", "than", "too", "very", "just", "because", "but",
        "and", "or", "if", "while", "about", "up", "out", "off", "over", "i",
        "me", "my", "myself", "we", "our", "ours", "you", "your", "yours",
        "he", "him", "his", "she", "her", "hers", "it", "its", "they", "them",
        "their", "theirs", "what", "which", "who", "whom", "this", "that",
        "these", "those", "am", "been", "being", "have", "has", "having", "do",
        "does", "doing", "a", "an", "the", "and", "but", "if", "or", "because",
        "as", "until", "while", "of", "at", "by", "for", "with", "about",
        "between", "into", "through", "during", "before", "after", "above",
        "below", "to", "from", "up", "down", "in", "out", "on", "off",
    }

    POSITIVE_WORDS: set[str] = {
        "good", "great", "excellent", "amazing", "wonderful", "fantastic",
        "outstanding", "superb", "brilliant", "impressive", "positive",
        "success", "successful", "profit", "profitable", "growth", "growing",
        "improve", "improved", "improvement", "benefit", "beneficial",
        "advantage", "opportunity", "gain", "win", "winning", "strong",
        "strength", "optimistic", "confident", "satisfied", "happy",
        "pleased", "delighted", "best", "better", "progress", "innovative",
        "efficient", "effective", "robust", "thriving", "booming", "bullish",
    }

    NEGATIVE_WORDS: set[str] = {
        "bad", "terrible", "horrible", "awful", "poor", "negative", "fail",
        "failure", "loss", "losing", "lose", "decline", "declining", "drop",
        "dropping", "fall", "falling", "crash", "crashed", "risk", "risky",
        "danger", "dangerous", "threat", "weak", "weakness", "pessimistic",
        "concern", "concerned", "worry", "worried", "problem", "issue",
        "difficult", "difficulty", "crisis", "recession", "bearish",
        "volatile", "volatility", "uncertain", "uncertainty", "doubt",
        "worse", "worst", "struggle", "struggling", "debt", "deficit",
    }

    @classmethod
    def analyze_text(cls, text: str) -> TextAnalysis:
        """
        Perform comprehensive text analysis.
        
        Args:
            text: Text to analyze.
            
        Returns:
            TextAnalysis with metrics.
        """
        if not text:
            return TextAnalysis(
                word_count=0, char_count=0, sentence_count=0,
                avg_word_length=0.0, avg_sentence_length=0.0,
            )

        # Clean and tokenize
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        sentences = re.split(r'[.!?]+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        word_count = len(words)
        char_count = len(text)
        sentence_count = max(len(sentences), 1)

        # Word stats
        word_lengths = [len(w) for w in words]
        avg_word_length = sum(word_lengths) / max(word_count, 1)
        avg_sentence_length = word_count / sentence_count

        # Top words (excluding stop words)
        content_words = [w for w in words if w not in cls.STOP_WORDS and len(w) > 2]
        word_freq = Counter(content_words)
        top_words = word_freq.most_common(10)

        # Simple sentiment estimate
        positive_count = sum(1 for w in words if w in cls.POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in cls.NEGATIVE_WORDS)

        if positive_count > negative_count * 1.5:
            sentiment = "positive"
        elif negative_count > positive_count * 1.5:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return TextAnalysis(
            word_count=word_count,
            char_count=char_count,
            sentence_count=sentence_count,
            avg_word_length=round(avg_word_length, 2),
            avg_sentence_length=round(avg_sentence_length, 2),
            top_words=top_words,
            sentiment_estimate=sentiment,
        )

    @classmethod
    def analyze_data(cls, data: list[float]) -> DataStats:
        """
        Calculate basic statistics for numeric data.
        
        Args:
            data: List of numeric values.
            
        Returns:
            DataStats with statistics.
        """
        if not data:
            return DataStats(
                count=0, mean=0.0, median=0.0, std_dev=0.0,
                minimum=0.0, maximum=0.0, total=0.0,
            )

        import math

        sorted_data = sorted(data)
        n = len(sorted_data)

        mean = sum(data) / n
        minimum = sorted_data[0]
        maximum = sorted_data[-1]
        total = sum(data)

        # Median
        if n % 2 == 0:
            median = (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
        else:
            median = sorted_data[n // 2]

        # Standard deviation
        variance = sum((x - mean) ** 2 for x in data) / n
        std_dev = math.sqrt(variance)

        return DataStats(
            count=n,
            mean=round(mean, 4),
            median=round(median, 4),
            std_dev=round(std_dev, 4),
            minimum=round(minimum, 4),
            maximum=round(maximum, 4),
            total=round(total, 4),
        )

    @staticmethod
    def extract_entities(text: str) -> dict[str, list[str]]:
        """
        Extract potential entities from text.
        
        Args:
            text: Input text.
            
        Returns:
            Dictionary of entity types to values.
        """
        entities: dict[str, list[str]] = {
            "emails": [],
            "urls": [],
            "numbers": [],
            "percentages": [],
            "money": [],
            "dates": [],
            "phones": [],
        }

        # Emails
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        entities["emails"] = emails

        # URLs
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text)
        entities["urls"] = urls

        # Numbers
        numbers = re.findall(r'\b\d+\.?\d*\b', text)
        entities["numbers"] = numbers

        # Percentages
        percentages = re.findall(r'\b\d+\.?\d*\s*%', text)
        entities["percentages"] = percentages

        # Money
        money = re.findall(r'[$€£¥]\s*\d+[\d,]*\.?\d*|\d+[\d,]*\.?\d*\s*(USD|EUR|GBP|JPY)', text)
        entities["money"] = money

        # Dates
        dates = re.findall(r'\b\d{1,4}[-/]\d{1,2}[-/]\d{1,4}\b', text)
        entities["dates"] = dates

        # Phone numbers
        phones = re.findall(r'\b\+?[\d\s\-\(\)]{10,15}\b', text)
        entities["phones"] = phones

        return entities

    @staticmethod
    def count_pattern_matches(text: str, pattern: str) -> list[str]:
        """
        Find all matches of a regex pattern in text.
        
        Args:
            text: Text to search.
            pattern: Regex pattern.
            
        Returns:
            List of matched strings.
        """
        try:
            return re.findall(pattern, text)
        except re.error:
            return []

    @classmethod
    def keyword_density(cls, text: str, top_n: int = 10) -> list[tuple[str, float]]:
        """
        Calculate keyword density in text.
        
        Args:
            text: Input text.
            top_n: Number of top keywords.
            
        Returns:
            List of (word, density_percentage) tuples.
        """
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        content_words = [w for w in words if w not in cls.STOP_WORDS and len(w) > 2]

        if not content_words:
            return []

        word_count = len(content_words)
        freq = Counter(content_words)
        return [
            (word, round(count / word_count * 100, 2))
            for word, count in freq.most_common(top_n)
        ]


# Global instance
analyzer = Analyzer()
