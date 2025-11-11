"""
Tests for Issue #7: Base Sentiment Analyzer

Acceptance Criteria:
- [ ] SentimentScore model with score (-1.0 to 1.0) and confidence (0.0 to 1.0) as Decimal
- [ ] BaseSentimentAnalyzer abstract base class
- [ ] Abstract analyze_sentiment(symbol: str) -> SentimentScore method
- [ ] Validate score and confidence ranges
- [ ] Maintain Decimal precision throughout
"""

from datetime import datetime
from decimal import Decimal

import pytest

# These imports will fail until implementation exists
try:
    from ib_sec_mcp.analyzers.sentiment.base import (
        BaseSentimentAnalyzer,
        SentimentScore,
    )
except ImportError:
    # Allow tests to be discovered even without implementation
    BaseSentimentAnalyzer = None
    SentimentScore = None


pytestmark = pytest.mark.skipif(
    BaseSentimentAnalyzer is None,
    reason="BaseSentimentAnalyzer not implemented yet (TDD red phase)",
)


class TestSentimentScore:
    """Test suite for SentimentScore model"""

    def test_sentiment_score_basic_creation(self):
        """
        Acceptance Criterion: SentimentScore model with score and confidence

        Expected: Valid model creation with Decimal values
        """
        score = SentimentScore(
            score=Decimal("0.75"), confidence=Decimal("0.85"), timestamp=datetime.now()
        )

        assert isinstance(score.score, Decimal)
        assert isinstance(score.confidence, Decimal)
        assert score.score == Decimal("0.75")
        assert score.confidence == Decimal("0.85")

    def test_sentiment_score_range_validation_positive(self):
        """
        Acceptance Criterion: Validate score range (-1.0 to 1.0)

        Test positive sentiment within valid range
        """
        score = SentimentScore(
            score=Decimal("1.0"), confidence=Decimal("0.9"), timestamp=datetime.now()
        )

        assert Decimal("-1.0") <= score.score <= Decimal("1.0")

    def test_sentiment_score_range_validation_negative(self):
        """
        Acceptance Criterion: Validate score range (-1.0 to 1.0)

        Test negative sentiment within valid range
        """
        score = SentimentScore(
            score=Decimal("-1.0"), confidence=Decimal("0.9"), timestamp=datetime.now()
        )

        assert Decimal("-1.0") <= score.score <= Decimal("1.0")

    def test_sentiment_score_range_validation_neutral(self):
        """
        Acceptance Criterion: Validate score range (-1.0 to 1.0)

        Test neutral sentiment (zero)
        """
        score = SentimentScore(
            score=Decimal("0.0"), confidence=Decimal("0.5"), timestamp=datetime.now()
        )

        assert score.score == Decimal("0.0")

    def test_sentiment_score_invalid_range_too_high(self):
        """
        Edge Case: Score exceeds maximum (1.0)

        Should raise validation error
        """
        with pytest.raises((ValueError, Exception)):  # Pydantic ValidationError
            SentimentScore(
                score=Decimal("1.5"), confidence=Decimal("0.9"), timestamp=datetime.now()
            )

    def test_sentiment_score_invalid_range_too_low(self):
        """
        Edge Case: Score below minimum (-1.0)

        Should raise validation error
        """
        with pytest.raises((ValueError, Exception)):
            SentimentScore(
                score=Decimal("-1.5"), confidence=Decimal("0.9"), timestamp=datetime.now()
            )

    def test_confidence_range_validation_valid(self):
        """
        Acceptance Criterion: Validate confidence range (0.0 to 1.0)

        Test confidence within valid range
        """
        score = SentimentScore(
            score=Decimal("0.5"), confidence=Decimal("1.0"), timestamp=datetime.now()
        )

        assert Decimal("0.0") <= score.confidence <= Decimal("1.0")

    def test_confidence_invalid_range_too_high(self):
        """
        Edge Case: Confidence exceeds maximum (1.0)

        Should raise validation error
        """
        with pytest.raises((ValueError, Exception)):
            SentimentScore(
                score=Decimal("0.5"), confidence=Decimal("1.5"), timestamp=datetime.now()
            )

    def test_confidence_invalid_range_negative(self):
        """
        Edge Case: Confidence is negative

        Should raise validation error
        """
        with pytest.raises((ValueError, Exception)):
            SentimentScore(
                score=Decimal("0.5"), confidence=Decimal("-0.1"), timestamp=datetime.now()
            )

    def test_sentiment_score_decimal_precision(self):
        """
        Financial Code Requirement: Maintain Decimal precision

        Ensure no float conversion occurs
        """
        score = SentimentScore(
            score=Decimal("0.123456789"),
            confidence=Decimal("0.987654321"),
            timestamp=datetime.now(),
        )

        # Verify Decimal type is preserved
        assert isinstance(score.score, Decimal)
        assert isinstance(score.confidence, Decimal)

        # Verify precision is maintained
        assert str(score.score) == "0.123456789"
        assert str(score.confidence) == "0.987654321"

    def test_sentiment_score_serialization(self):
        """
        Integration Test: JSON serialization for MCP tools

        Should serialize to JSON-compatible format
        """
        score = SentimentScore(
            score=Decimal("0.75"), confidence=Decimal("0.85"), timestamp=datetime.now()
        )

        # Pydantic v2 model_dump() returns dict
        data = score.model_dump()

        assert "score" in data
        assert "confidence" in data
        assert "timestamp" in data

    @pytest.mark.parametrize(
        "score_value,confidence_value",
        [
            (Decimal("0.0"), Decimal("0.0")),
            (Decimal("0.5"), Decimal("0.5")),
            (Decimal("1.0"), Decimal("1.0")),
            (Decimal("-1.0"), Decimal("1.0")),
            (Decimal("-0.5"), Decimal("0.75")),
        ],
    )
    def test_sentiment_score_various_valid_combinations(self, score_value, confidence_value):
        """
        Parametrized Test: Various valid score and confidence combinations

        All combinations should be valid
        """
        score = SentimentScore(
            score=score_value, confidence=confidence_value, timestamp=datetime.now()
        )

        assert Decimal("-1.0") <= score.score <= Decimal("1.0")
        assert Decimal("0.0") <= score.confidence <= Decimal("1.0")


class TestBaseSentimentAnalyzer:
    """Test suite for BaseSentimentAnalyzer abstract base class"""

    def test_base_analyzer_is_abstract(self):
        """
        Acceptance Criterion: BaseSentimentAnalyzer is abstract

        Should not be instantiable directly
        """
        with pytest.raises(TypeError):
            BaseSentimentAnalyzer()

    def test_base_analyzer_requires_analyze_sentiment(self):
        """
        Acceptance Criterion: Abstract analyze_sentiment method

        Subclasses must implement analyze_sentiment
        """

        # Create concrete implementation
        class IncompleteSentimentAnalyzer(BaseSentimentAnalyzer):
            pass

        with pytest.raises(TypeError):
            IncompleteSentimentAnalyzer()

    def test_base_analyzer_concrete_implementation(self):
        """
        Integration Test: Concrete analyzer implementation

        Should be instantiable when analyze_sentiment is implemented
        """

        class ConcreteSentimentAnalyzer(BaseSentimentAnalyzer):
            async def analyze_sentiment(self, symbol: str) -> SentimentScore:
                return SentimentScore(
                    score=Decimal("0.5"), confidence=Decimal("0.8"), timestamp=datetime.now()
                )

        analyzer = ConcreteSentimentAnalyzer()
        assert analyzer is not None

    @pytest.mark.asyncio
    async def test_base_analyzer_analyze_sentiment_signature(self):
        """
        Acceptance Criterion: analyze_sentiment(symbol: str) -> SentimentScore

        Verify method signature and return type
        """

        class TestAnalyzer(BaseSentimentAnalyzer):
            async def analyze_sentiment(self, symbol: str) -> SentimentScore:
                return SentimentScore(
                    score=Decimal("0.0"), confidence=Decimal("1.0"), timestamp=datetime.now()
                )

        analyzer = TestAnalyzer()
        result = await analyzer.analyze_sentiment("AAPL")

        assert isinstance(result, SentimentScore)
        assert isinstance(result.score, Decimal)
        assert isinstance(result.confidence, Decimal)

    @pytest.mark.asyncio
    async def test_base_analyzer_returns_decimal_types(self):
        """
        Financial Code Requirement: Return Decimal values

        Ensure analyzer returns Decimal, not float
        """

        class TestAnalyzer(BaseSentimentAnalyzer):
            async def analyze_sentiment(self, symbol: str) -> SentimentScore:
                return SentimentScore(
                    score=Decimal("0.123"), confidence=Decimal("0.987"), timestamp=datetime.now()
                )

        analyzer = TestAnalyzer()
        result = await analyzer.analyze_sentiment("AAPL")

        # Verify types
        assert isinstance(result.score, Decimal)
        assert isinstance(result.confidence, Decimal)

        # Verify not float
        assert not isinstance(result.score, float)
        assert not isinstance(result.confidence, float)

    @pytest.mark.asyncio
    async def test_base_analyzer_symbol_parameter(self):
        """
        Acceptance Criterion: Symbol-based analysis

        Analyzer should accept stock symbol string
        """

        class TestAnalyzer(BaseSentimentAnalyzer):
            async def analyze_sentiment(self, symbol: str) -> SentimentScore:
                # Verify symbol is passed correctly
                assert isinstance(symbol, str)
                assert symbol == "TSLA"

                return SentimentScore(
                    score=Decimal("0.0"), confidence=Decimal("0.0"), timestamp=datetime.now()
                )

        analyzer = TestAnalyzer()
        await analyzer.analyze_sentiment("TSLA")
