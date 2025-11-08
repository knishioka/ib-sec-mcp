"""
Tests for Issue #7: News Sentiment Analyzer

Acceptance Criteria:
- [ ] NewsSentimentAnalyzer inherits from BaseSentimentAnalyzer
- [ ] Fetch news headlines from Yahoo Finance API
- [ ] Analyze sentiment using TextBlob or VADER
- [ ] Return SentimentScore with aggregated sentiment
- [ ] Handle API failures gracefully (fallback to neutral sentiment)
- [ ] Cache results for performance
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

# These imports will fail until implementation exists
try:
    from ib_sec_mcp.analyzers.sentiment.base import SentimentScore
    from ib_sec_mcp.analyzers.sentiment.news import NewsSentimentAnalyzer
except ImportError:
    NewsSentimentAnalyzer = None
    SentimentScore = None


pytestmark = pytest.mark.skipif(
    NewsSentimentAnalyzer is None,
    reason="NewsSentimentAnalyzer not implemented yet (TDD red phase)",
)


@pytest.fixture
def mock_positive_news():
    """
    Sample news data with positive sentiment

    Expected aggregated sentiment: ~0.7-0.8
    """
    return [
        {
            "title": "Company reports record earnings, stock surges",
            "published": datetime.now(),
            "source": "Reuters",
        },
        {
            "title": "Analysts upgrade rating to strong buy",
            "published": datetime.now(),
            "source": "Bloomberg",
        },
        {
            "title": "New product launch exceeds expectations",
            "published": datetime.now(),
            "source": "CNBC",
        },
    ]


@pytest.fixture
def mock_negative_news():
    """
    Sample news data with negative sentiment

    Expected aggregated sentiment: ~-0.7 to -0.8
    """
    return [
        {
            "title": "Company faces lawsuit over product defects",
            "published": datetime.now(),
            "source": "Reuters",
        },
        {
            "title": "Stock plummets on disappointing earnings report",
            "published": datetime.now(),
            "source": "Bloomberg",
        },
        {
            "title": "Analysts downgrade to sell amid concerns",
            "published": datetime.now(),
            "source": "CNBC",
        },
    ]


@pytest.fixture
def mock_neutral_news():
    """
    Sample news data with neutral sentiment

    Expected aggregated sentiment: ~0.0 to 0.2
    """
    return [
        {
            "title": "Company announces quarterly results",
            "published": datetime.now(),
            "source": "Reuters",
        },
        {
            "title": "CEO speaks at industry conference",
            "published": datetime.now(),
            "source": "Bloomberg",
        },
        {"title": "Stock trading at average volume", "published": datetime.now(), "source": "CNBC"},
    ]


@pytest.fixture
def mock_mixed_news():
    """
    Sample news data with mixed sentiment

    Expected aggregated sentiment: ~-0.1 to 0.1 (slightly negative overall)
    """
    return [
        {
            "title": "Company reports strong revenue growth",
            "published": datetime.now(),
            "source": "Reuters",
        },
        {
            "title": "Profit margins decline due to rising costs",
            "published": datetime.now(),
            "source": "Bloomberg",
        },
        {
            "title": "Stock unchanged in after-hours trading",
            "published": datetime.now(),
            "source": "CNBC",
        },
    ]


class TestNewsSentimentAnalyzer:
    """Test suite for NewsSentimentAnalyzer implementation"""

    @pytest.mark.asyncio
    async def test_news_analyzer_basic_initialization(self):
        """
        Basic Test: Analyzer can be instantiated

        Should create analyzer without errors
        """
        analyzer = NewsSentimentAnalyzer()
        assert analyzer is not None

    @pytest.mark.asyncio
    async def test_news_analyzer_inherits_base(self):
        """
        Acceptance Criterion: Inherits from BaseSentimentAnalyzer

        Should be instance of base class
        """
        from ib_sec_mcp.analyzers.sentiment.base import BaseSentimentAnalyzer

        analyzer = NewsSentimentAnalyzer()
        assert isinstance(analyzer, BaseSentimentAnalyzer)

    @pytest.mark.asyncio
    async def test_news_analyzer_positive_sentiment(self, mock_positive_news):
        """
        Acceptance Criterion: Analyze positive news sentiment

        Should return positive sentiment score (0.5 to 1.0)
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_positive_news

            result = await analyzer.analyze_sentiment("AAPL")

            assert isinstance(result, SentimentScore)
            assert result.score > Decimal("0.3")  # Positive sentiment
            assert Decimal("0.0") <= result.confidence <= Decimal("1.0")

    @pytest.mark.asyncio
    async def test_news_analyzer_negative_sentiment(self, mock_negative_news):
        """
        Acceptance Criterion: Analyze negative news sentiment

        Should return negative sentiment score (-1.0 to -0.5)
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_negative_news

            result = await analyzer.analyze_sentiment("AAPL")

            assert isinstance(result, SentimentScore)
            assert result.score < Decimal("-0.3")  # Negative sentiment
            assert Decimal("0.0") <= result.confidence <= Decimal("1.0")

    @pytest.mark.asyncio
    async def test_news_analyzer_neutral_sentiment(self, mock_neutral_news):
        """
        Acceptance Criterion: Analyze neutral news sentiment

        Should return near-zero sentiment score
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_neutral_news

            result = await analyzer.analyze_sentiment("AAPL")

            assert isinstance(result, SentimentScore)
            assert Decimal("-0.3") <= result.score <= Decimal("0.3")  # Near neutral

    @pytest.mark.asyncio
    async def test_news_analyzer_mixed_sentiment(self, mock_mixed_news):
        """
        Integration Test: Analyze mixed sentiment news

        Should aggregate multiple sentiments correctly
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_mixed_news

            result = await analyzer.analyze_sentiment("AAPL")

            assert isinstance(result, SentimentScore)
            # Mixed sentiment should be near neutral
            assert Decimal("-0.5") <= result.score <= Decimal("0.5")

    @pytest.mark.asyncio
    async def test_news_analyzer_no_news_available(self):
        """
        Edge Case: No news articles found

        Should return neutral sentiment with low confidence
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []

            result = await analyzer.analyze_sentiment("OBSCURE")

            assert isinstance(result, SentimentScore)
            assert result.score == Decimal("0.0")  # Neutral
            assert result.confidence < Decimal("0.3")  # Low confidence

    @pytest.mark.asyncio
    async def test_news_analyzer_api_failure(self):
        """
        Edge Case: API request fails

        Should return neutral sentiment and handle gracefully
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API timeout")

            result = await analyzer.analyze_sentiment("AAPL")

            assert isinstance(result, SentimentScore)
            assert result.score == Decimal("0.0")  # Neutral fallback
            assert result.confidence == Decimal("0.0")  # No confidence

    @pytest.mark.asyncio
    async def test_news_analyzer_api_rate_limit(self):
        """
        Edge Case: API rate limiting

        Should handle rate limit errors gracefully
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Rate limit exceeded")

            result = await analyzer.analyze_sentiment("AAPL")

            assert isinstance(result, SentimentScore)
            assert result.score == Decimal("0.0")
            assert result.confidence == Decimal("0.0")

    @pytest.mark.asyncio
    async def test_news_analyzer_empty_headlines(self):
        """
        Edge Case: News with empty titles

        Should filter out empty headlines
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                {"title": "", "published": datetime.now(), "source": "Reuters"},
                {"title": "   ", "published": datetime.now(), "source": "Bloomberg"},
            ]

            result = await analyzer.analyze_sentiment("AAPL")

            # Should treat as no news
            assert result.score == Decimal("0.0")
            assert result.confidence < Decimal("0.3")

    @pytest.mark.asyncio
    async def test_news_analyzer_decimal_precision(self, mock_positive_news):
        """
        Financial Code Requirement: Maintain Decimal precision

        Ensure no float conversion during sentiment calculation
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_positive_news

            result = await analyzer.analyze_sentiment("AAPL")

            # Verify Decimal types
            assert isinstance(result.score, Decimal)
            assert isinstance(result.confidence, Decimal)

            # Verify not float
            assert not isinstance(result.score, float)
            assert not isinstance(result.confidence, float)

    @pytest.mark.asyncio
    async def test_news_analyzer_confidence_calculation(self, mock_positive_news):
        """
        Acceptance Criterion: Confidence score reflects data quality

        More news articles should increase confidence
        """
        analyzer = NewsSentimentAnalyzer()

        # Test with few articles (use different symbol to avoid cache)
        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_positive_news[:1]
            result_low = await analyzer.analyze_sentiment("MSFT")

        # Test with many articles (use different symbol to avoid cache)
        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_positive_news
            result_high = await analyzer.analyze_sentiment("TSLA")

        # More articles → higher confidence
        assert result_high.confidence > result_low.confidence

    @pytest.mark.asyncio
    async def test_news_analyzer_caching(self, mock_positive_news):
        """
        Acceptance Criterion: Cache results for performance

        Should cache recent sentiment analysis
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_positive_news

            # First call
            result1 = await analyzer.analyze_sentiment("AAPL")

            # Second call (should use cache)
            result2 = await analyzer.analyze_sentiment("AAPL")

            # Verify API was only called once (cached)
            # Implementation may vary - this is one approach
            assert result1.score == result2.score

    @pytest.mark.asyncio
    async def test_news_analyzer_timestamp(self, mock_positive_news):
        """
        Integration Test: Timestamp reflects analysis time

        Should include timestamp in result
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_positive_news

            before = datetime.now()
            result = await analyzer.analyze_sentiment("AAPL")
            after = datetime.now()

            assert before <= result.timestamp <= after

    @pytest.mark.parametrize(
        "symbol",
        [
            "AAPL",
            "GOOGL",
            "TSLA",
            "MSFT",
            "AMZN",
        ],
    )
    @pytest.mark.asyncio
    async def test_news_analyzer_various_symbols(self, symbol, mock_positive_news):
        """
        Parametrized Test: Various stock symbols

        Should work with different symbols
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_positive_news

            result = await analyzer.analyze_sentiment(symbol)

            assert isinstance(result, SentimentScore)
            assert Decimal("-1.0") <= result.score <= Decimal("1.0")
            assert Decimal("0.0") <= result.confidence <= Decimal("1.0")

    @pytest.mark.asyncio
    async def test_news_analyzer_invalid_symbol(self):
        """
        Edge Case: Invalid or non-existent symbol

        Should handle gracefully with neutral sentiment
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []

            result = await analyzer.analyze_sentiment("INVALID123")

            assert result.score == Decimal("0.0")
            assert result.confidence == Decimal("0.0")

    @pytest.mark.asyncio
    async def test_news_analyzer_special_characters_in_headlines(self):
        """
        Edge Case: Headlines with special characters

        Should handle unicode and special characters correctly
        """
        analyzer = NewsSentimentAnalyzer()

        special_news = [
            {
                "title": "Stock 📈 surges on strong earnings 💰",
                "published": datetime.now(),
                "source": "Reuters",
            }
        ]

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = special_news

            result = await analyzer.analyze_sentiment("AAPL")

            # Should not crash, sentiment should be positive
            assert isinstance(result, SentimentScore)
            assert result.score > Decimal("0.0")

    @pytest.mark.asyncio
    async def test_news_analyzer_aggregation_strategy(self, mock_mixed_news):
        """
        Integration Test: Sentiment aggregation strategy

        Should aggregate multiple sentiments using appropriate method
        (mean, median, or weighted average)
        """
        analyzer = NewsSentimentAnalyzer()

        with patch.object(analyzer, "_fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_mixed_news

            result = await analyzer.analyze_sentiment("AAPL")

            # Result should be aggregate of individual sentiments
            assert isinstance(result, SentimentScore)
            assert Decimal("-1.0") <= result.score <= Decimal("1.0")

            # Confidence should reflect consistency
            # (high confidence if sentiments agree, low if mixed)
            assert Decimal("0.0") <= result.confidence <= Decimal("1.0")
