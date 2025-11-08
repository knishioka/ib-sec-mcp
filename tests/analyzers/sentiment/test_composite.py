"""
Tests for Issue #7: Composite Sentiment Analyzer

Acceptance Criteria:
- [ ] CompositeSentimentAnalyzer aggregates multiple sentiment sources
- [ ] Configurable weights for different sentiment sources
- [ ] Combine news sentiment with future sources (social media, analyst ratings)
- [ ] Return aggregated SentimentScore with combined confidence
- [ ] Handle missing or failed sentiment sources gracefully
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

# These imports will fail until implementation exists
try:
    from ib_sec_mcp.analyzers.sentiment.base import (
        BaseSentimentAnalyzer,
        SentimentScore,
    )
    from ib_sec_mcp.analyzers.sentiment.composite import CompositeSentimentAnalyzer
except ImportError:
    CompositeSentimentAnalyzer = None
    BaseSentimentAnalyzer = None
    SentimentScore = None


pytestmark = pytest.mark.skipif(
    CompositeSentimentAnalyzer is None,
    reason="CompositeSentimentAnalyzer not implemented yet (TDD red phase)",
)


@pytest.fixture
def mock_news_analyzer():
    """Mock news sentiment analyzer"""
    analyzer = AsyncMock(spec=BaseSentimentAnalyzer)
    analyzer.analyze_sentiment = AsyncMock(
        return_value=SentimentScore(
            score=Decimal("0.7"), confidence=Decimal("0.8"), timestamp=datetime.now()
        )
    )
    return analyzer


@pytest.fixture
def mock_social_analyzer():
    """Mock social media sentiment analyzer (future implementation)"""
    analyzer = AsyncMock(spec=BaseSentimentAnalyzer)
    analyzer.analyze_sentiment = AsyncMock(
        return_value=SentimentScore(
            score=Decimal("0.5"), confidence=Decimal("0.6"), timestamp=datetime.now()
        )
    )
    return analyzer


@pytest.fixture
def mock_analyst_analyzer():
    """Mock analyst rating analyzer (future implementation)"""
    analyzer = AsyncMock(spec=BaseSentimentAnalyzer)
    analyzer.analyze_sentiment = AsyncMock(
        return_value=SentimentScore(
            score=Decimal("0.8"), confidence=Decimal("0.9"), timestamp=datetime.now()
        )
    )
    return analyzer


class TestCompositeSentimentAnalyzer:
    """Test suite for CompositeSentimentAnalyzer implementation"""

    @pytest.mark.asyncio
    async def test_composite_analyzer_basic_initialization(self):
        """
        Basic Test: Analyzer can be instantiated

        Should create composite analyzer with no sources
        """
        analyzer = CompositeSentimentAnalyzer()
        assert analyzer is not None

    @pytest.mark.asyncio
    async def test_composite_analyzer_inherits_base(self):
        """
        Acceptance Criterion: Inherits from BaseSentimentAnalyzer

        Should be instance of base class
        """
        analyzer = CompositeSentimentAnalyzer()
        assert isinstance(analyzer, BaseSentimentAnalyzer)

    @pytest.mark.asyncio
    async def test_composite_analyzer_single_source(self, mock_news_analyzer):
        """
        Basic Test: Composite with single sentiment source

        Should return sentiment from single source
        """
        analyzer = CompositeSentimentAnalyzer(sources={"news": mock_news_analyzer})

        result = await analyzer.analyze_sentiment("AAPL")

        assert isinstance(result, SentimentScore)
        assert result.score == Decimal("0.7")
        assert result.confidence == Decimal("0.8")

    @pytest.mark.asyncio
    async def test_composite_analyzer_multiple_sources(
        self, mock_news_analyzer, mock_social_analyzer
    ):
        """
        Acceptance Criterion: Aggregate multiple sentiment sources

        Should combine sentiments from multiple sources
        """
        analyzer = CompositeSentimentAnalyzer(
            sources={
                "news": mock_news_analyzer,
                "social": mock_social_analyzer,
            }
        )

        result = await analyzer.analyze_sentiment("AAPL")

        assert isinstance(result, SentimentScore)
        # Should be weighted average: (0.7 + 0.5) / 2 = 0.6
        assert Decimal("0.5") <= result.score <= Decimal("0.7")

    @pytest.mark.asyncio
    async def test_composite_analyzer_weighted_aggregation(
        self, mock_news_analyzer, mock_social_analyzer
    ):
        """
        Acceptance Criterion: Configurable weights for sources

        Should apply weights when aggregating sentiments
        """
        analyzer = CompositeSentimentAnalyzer(
            sources={
                "news": mock_news_analyzer,
                "social": mock_social_analyzer,
            },
            weights={
                "news": Decimal("0.7"),
                "social": Decimal("0.3"),
            },
        )

        result = await analyzer.analyze_sentiment("AAPL")

        assert isinstance(result, SentimentScore)
        # Weighted: 0.7*0.7 + 0.3*0.5 = 0.49 + 0.15 = 0.64
        assert Decimal("0.6") <= result.score <= Decimal("0.7")

    @pytest.mark.asyncio
    async def test_composite_analyzer_equal_weights_default(
        self, mock_news_analyzer, mock_social_analyzer
    ):
        """
        Integration Test: Default equal weights

        Should use equal weights if not specified
        """
        analyzer = CompositeSentimentAnalyzer(
            sources={
                "news": mock_news_analyzer,
                "social": mock_social_analyzer,
            }
        )

        result = await analyzer.analyze_sentiment("AAPL")

        # Equal weights: simple average
        expected = (Decimal("0.7") + Decimal("0.5")) / Decimal("2")
        assert abs(result.score - expected) < Decimal("0.01")

    @pytest.mark.asyncio
    async def test_composite_analyzer_confidence_aggregation(
        self, mock_news_analyzer, mock_social_analyzer
    ):
        """
        Acceptance Criterion: Combined confidence calculation

        Should aggregate confidence from multiple sources
        """
        analyzer = CompositeSentimentAnalyzer(
            sources={
                "news": mock_news_analyzer,
                "social": mock_social_analyzer,
            }
        )

        result = await analyzer.analyze_sentiment("AAPL")

        # Confidence should be aggregated (e.g., average or minimum)
        assert Decimal("0.6") <= result.confidence <= Decimal("0.8")

    @pytest.mark.asyncio
    async def test_composite_analyzer_source_failure(self, mock_news_analyzer):
        """
        Edge Case: One source fails

        Should handle gracefully and use remaining sources
        """
        failing_analyzer = AsyncMock(spec=BaseSentimentAnalyzer)
        failing_analyzer.analyze_sentiment = AsyncMock(side_effect=Exception("API error"))

        analyzer = CompositeSentimentAnalyzer(
            sources={
                "news": mock_news_analyzer,
                "failing": failing_analyzer,
            }
        )

        result = await analyzer.analyze_sentiment("AAPL")

        # Should still return valid result from working source
        assert isinstance(result, SentimentScore)
        assert result.score == Decimal("0.7")  # From news only

    @pytest.mark.asyncio
    async def test_composite_analyzer_all_sources_fail(self):
        """
        Edge Case: All sources fail

        Should return neutral sentiment with zero confidence
        """
        failing_analyzer = AsyncMock(spec=BaseSentimentAnalyzer)
        failing_analyzer.analyze_sentiment = AsyncMock(side_effect=Exception("API error"))

        analyzer = CompositeSentimentAnalyzer(
            sources={
                "news": failing_analyzer,
                "social": failing_analyzer,
            }
        )

        result = await analyzer.analyze_sentiment("AAPL")

        assert isinstance(result, SentimentScore)
        assert result.score == Decimal("0.0")  # Neutral fallback
        assert result.confidence == Decimal("0.0")  # No confidence

    @pytest.mark.asyncio
    async def test_composite_analyzer_no_sources(self):
        """
        Edge Case: No sources configured

        Should return neutral sentiment with zero confidence
        """
        analyzer = CompositeSentimentAnalyzer(sources={})

        result = await analyzer.analyze_sentiment("AAPL")

        assert isinstance(result, SentimentScore)
        assert result.score == Decimal("0.0")
        assert result.confidence == Decimal("0.0")

    @pytest.mark.asyncio
    async def test_composite_analyzer_conflicting_sentiments(self):
        """
        Integration Test: Conflicting sentiment signals

        Should aggregate positive and negative sentiments correctly
        """
        positive_analyzer = AsyncMock(spec=BaseSentimentAnalyzer)
        positive_analyzer.analyze_sentiment = AsyncMock(
            return_value=SentimentScore(
                score=Decimal("0.8"), confidence=Decimal("0.9"), timestamp=datetime.now()
            )
        )

        negative_analyzer = AsyncMock(spec=BaseSentimentAnalyzer)
        negative_analyzer.analyze_sentiment = AsyncMock(
            return_value=SentimentScore(
                score=Decimal("-0.6"), confidence=Decimal("0.7"), timestamp=datetime.now()
            )
        )

        analyzer = CompositeSentimentAnalyzer(
            sources={
                "positive": positive_analyzer,
                "negative": negative_analyzer,
            }
        )

        result = await analyzer.analyze_sentiment("AAPL")

        # Should average: (0.8 + -0.6) / 2 = 0.1
        assert Decimal("-0.2") <= result.score <= Decimal("0.2")

        # Confidence should be lower due to disagreement
        assert result.confidence < Decimal("0.8")

    @pytest.mark.asyncio
    async def test_composite_analyzer_decimal_precision(
        self, mock_news_analyzer, mock_social_analyzer
    ):
        """
        Financial Code Requirement: Maintain Decimal precision

        Ensure no float conversion during aggregation
        """
        analyzer = CompositeSentimentAnalyzer(
            sources={
                "news": mock_news_analyzer,
                "social": mock_social_analyzer,
            }
        )

        result = await analyzer.analyze_sentiment("AAPL")

        # Verify Decimal types
        assert isinstance(result.score, Decimal)
        assert isinstance(result.confidence, Decimal)

        # Verify not float
        assert not isinstance(result.score, float)
        assert not isinstance(result.confidence, float)

    @pytest.mark.asyncio
    async def test_composite_analyzer_weight_normalization(
        self, mock_news_analyzer, mock_social_analyzer
    ):
        """
        Integration Test: Weight normalization

        Should normalize weights if they don't sum to 1.0
        """
        analyzer = CompositeSentimentAnalyzer(
            sources={
                "news": mock_news_analyzer,
                "social": mock_social_analyzer,
            },
            weights={
                "news": Decimal("2.0"),  # Non-normalized
                "social": Decimal("1.0"),
            },
        )

        result = await analyzer.analyze_sentiment("AAPL")

        # Should normalize to: news=0.67, social=0.33
        # Result: 0.67*0.7 + 0.33*0.5 = 0.469 + 0.165 = 0.634
        assert isinstance(result, SentimentScore)
        assert Decimal("0.6") <= result.score <= Decimal("0.7")

    @pytest.mark.asyncio
    async def test_composite_analyzer_partial_source_failure(
        self, mock_news_analyzer, mock_social_analyzer
    ):
        """
        Integration Test: Partial source failure with weight adjustment

        Should re-weight remaining sources when one fails
        """
        failing_analyzer = AsyncMock(spec=BaseSentimentAnalyzer)
        failing_analyzer.analyze_sentiment = AsyncMock(side_effect=Exception("API error"))

        analyzer = CompositeSentimentAnalyzer(
            sources={
                "news": mock_news_analyzer,
                "social": mock_social_analyzer,
                "failing": failing_analyzer,
            },
            weights={
                "news": Decimal("0.5"),
                "social": Decimal("0.3"),
                "failing": Decimal("0.2"),
            },
        )

        result = await analyzer.analyze_sentiment("AAPL")

        # Should re-normalize: news=0.625, social=0.375
        # Result: 0.625*0.7 + 0.375*0.5 = 0.4375 + 0.1875 = 0.625
        assert isinstance(result, SentimentScore)
        assert Decimal("0.5") <= result.score <= Decimal("0.7")

    @pytest.mark.asyncio
    async def test_composite_analyzer_timestamp(self, mock_news_analyzer, mock_social_analyzer):
        """
        Integration Test: Timestamp reflects aggregation time

        Should use current timestamp for aggregated result
        """
        analyzer = CompositeSentimentAnalyzer(
            sources={
                "news": mock_news_analyzer,
                "social": mock_social_analyzer,
            }
        )

        before = datetime.now()
        result = await analyzer.analyze_sentiment("AAPL")
        after = datetime.now()

        assert before <= result.timestamp <= after

    @pytest.mark.parametrize("num_sources", [1, 2, 3, 5])
    @pytest.mark.asyncio
    async def test_composite_analyzer_various_source_counts(self, num_sources):
        """
        Parametrized Test: Various numbers of sources

        Should handle different numbers of sources correctly
        """
        sources = {}
        for i in range(num_sources):
            mock = AsyncMock(spec=BaseSentimentAnalyzer)
            mock.analyze_sentiment = AsyncMock(
                return_value=SentimentScore(
                    score=Decimal("0.5"), confidence=Decimal("0.8"), timestamp=datetime.now()
                )
            )
            sources[f"source_{i}"] = mock

        analyzer = CompositeSentimentAnalyzer(sources=sources)
        result = await analyzer.analyze_sentiment("AAPL")

        assert isinstance(result, SentimentScore)
        assert Decimal("0.4") <= result.score <= Decimal("0.6")

    @pytest.mark.asyncio
    async def test_composite_analyzer_extreme_sentiments(self):
        """
        Edge Case: Extreme sentiment values

        Should handle edge values correctly
        """
        max_positive = AsyncMock(spec=BaseSentimentAnalyzer)
        max_positive.analyze_sentiment = AsyncMock(
            return_value=SentimentScore(
                score=Decimal("1.0"), confidence=Decimal("1.0"), timestamp=datetime.now()
            )
        )

        max_negative = AsyncMock(spec=BaseSentimentAnalyzer)
        max_negative.analyze_sentiment = AsyncMock(
            return_value=SentimentScore(
                score=Decimal("-1.0"), confidence=Decimal("1.0"), timestamp=datetime.now()
            )
        )

        analyzer = CompositeSentimentAnalyzer(
            sources={
                "positive": max_positive,
                "negative": max_negative,
            }
        )

        result = await analyzer.analyze_sentiment("AAPL")

        # Should average to 0.0
        assert result.score == Decimal("0.0")

    @pytest.mark.asyncio
    async def test_composite_analyzer_confidence_disagreement_penalty(self):
        """
        Integration Test: Confidence penalty for disagreement

        High disagreement between sources should lower confidence
        """
        high_positive = AsyncMock(spec=BaseSentimentAnalyzer)
        high_positive.analyze_sentiment = AsyncMock(
            return_value=SentimentScore(
                score=Decimal("0.9"), confidence=Decimal("0.9"), timestamp=datetime.now()
            )
        )

        high_negative = AsyncMock(spec=BaseSentimentAnalyzer)
        high_negative.analyze_sentiment = AsyncMock(
            return_value=SentimentScore(
                score=Decimal("-0.8"), confidence=Decimal("0.9"), timestamp=datetime.now()
            )
        )

        analyzer = CompositeSentimentAnalyzer(
            sources={
                "positive": high_positive,
                "negative": high_negative,
            }
        )

        result = await analyzer.analyze_sentiment("AAPL")

        # Even though individual confidences are high,
        # disagreement should lower combined confidence
        assert result.confidence < Decimal("0.6")

    @pytest.mark.asyncio
    async def test_composite_analyzer_three_sources(
        self, mock_news_analyzer, mock_social_analyzer, mock_analyst_analyzer
    ):
        """
        Integration Test: Three sentiment sources

        Should aggregate three sources correctly
        """
        analyzer = CompositeSentimentAnalyzer(
            sources={
                "news": mock_news_analyzer,  # 0.7
                "social": mock_social_analyzer,  # 0.5
                "analyst": mock_analyst_analyzer,  # 0.8
            }
        )

        result = await analyzer.analyze_sentiment("AAPL")

        # Average: (0.7 + 0.5 + 0.8) / 3 = 0.667
        assert Decimal("0.6") <= result.score <= Decimal("0.7")

    @pytest.mark.asyncio
    async def test_composite_analyzer_invalid_weights(
        self, mock_news_analyzer, mock_social_analyzer
    ):
        """
        Edge Case: Invalid weight configuration

        Should handle negative or zero weights gracefully
        """
        with pytest.raises((ValueError, Exception)):
            CompositeSentimentAnalyzer(
                sources={
                    "news": mock_news_analyzer,
                    "social": mock_social_analyzer,
                },
                weights={
                    "news": Decimal("-0.5"),  # Negative weight
                    "social": Decimal("1.5"),
                },
            )
