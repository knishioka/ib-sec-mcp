"""
News sentiment analyzer using Yahoo Finance news

Analyzes sentiment from news headlines and articles.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from ib_sec_mcp.analyzers.sentiment.base import BaseSentimentAnalyzer, SentimentScore

# Configure logging
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
_sentiment_cache: dict[str, tuple[SentimentScore, datetime]] = {}


class NewsSentimentAnalyzer(BaseSentimentAnalyzer):
    """
    News-based sentiment analyzer

    Fetches recent news articles for a stock symbol and analyzes
    their sentiment using LLM-based analysis.

    Attributes:
        lookback_days: Number of days to look back for news (default: 7)
        max_articles: Maximum number of articles to analyze (default: 10)
    """

    def __init__(
        self,
        lookback_days: int = 7,
        max_articles: int = 10,
    ):
        """
        Initialize news sentiment analyzer

        Args:
            lookback_days: Number of days to look back for news
            max_articles: Maximum number of articles to analyze
        """
        self.lookback_days = lookback_days
        self.max_articles = max_articles

    async def analyze_sentiment(self, symbol: str) -> SentimentScore:
        """
        Analyze news sentiment for a stock symbol

        Fetches recent news articles and analyzes their sentiment
        using LLM-based natural language processing.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")

        Returns:
            SentimentScore with aggregated sentiment from news articles

        Raises:
            Exception: If analysis fails completely (returns neutral sentiment)
        """
        # Check cache first
        cached_result = self._get_from_cache(symbol)
        if cached_result is not None:
            logger.debug(f"Using cached sentiment for {symbol}")
            return cached_result

        try:
            # Fetch news articles
            articles = await self._fetch_news(symbol)

            # Handle no news case
            if not articles:
                logger.warning(f"No news articles found for {symbol}")
                return SentimentScore(
                    score=Decimal("0.0"),
                    confidence=Decimal("0.0"),
                    timestamp=datetime.now(),
                    reasoning="No news articles available for analysis",
                )

            # Analyze sentiment
            result = await self._analyze_articles(symbol, articles)

            # Cache the result
            self._cache_result(symbol, result)

            return result

        except Exception as e:
            logger.error(f"Error analyzing sentiment for {symbol}: {e}")
            # Return neutral sentiment on failure
            return SentimentScore(
                score=Decimal("0.0"),
                confidence=Decimal("0.0"),
                timestamp=datetime.now(),
                reasoning=f"Analysis failed: {e!s}",
            )

    async def _fetch_news(self, symbol: str) -> list[dict[str, Any]]:
        """
        Fetch news articles for a symbol

        Args:
            symbol: Stock ticker symbol

        Returns:
            List of news articles with title, published, source

        Raises:
            Exception: If news fetch fails
        """
        try:
            import yfinance as yf

            # Fetch news with timeout
            async def fetch() -> Any:
                ticker = yf.Ticker(symbol)
                return ticker.news

            news_data: Any = await asyncio.wait_for(fetch(), timeout=30.0)
            news: list[dict[str, Any]] = news_data if news_data else []

            if not news:
                return []

            # Limit and format articles
            articles = []
            for item in news[: self.max_articles]:
                # yfinance returns news in nested structure
                content = item.get("content", item)

                title = content.get("title", "").strip()
                if not title:
                    continue

                articles.append(
                    {
                        "title": title,
                        "published": content.get("pubDate", datetime.now()),
                        "source": content.get("provider", {}).get("displayName", "Unknown"),
                    }
                )

            return articles

        except Exception as e:
            logger.error(f"Failed to fetch news for {symbol}: {e}")
            raise

    async def _analyze_articles(
        self, symbol: str, articles: list[dict[str, Any]]
    ) -> SentimentScore:
        """
        Analyze sentiment from news articles

        Uses a simple heuristic-based approach for sentiment analysis:
        - Positive keywords: surge, gain, profit, growth, success, upgrade, buy, strong
        - Negative keywords: fall, loss, decline, downgrade, sell, weak, concern, risk

        Args:
            symbol: Stock symbol for context
            articles: List of news articles to analyze

        Returns:
            Aggregated sentiment score
        """
        # Filter out empty titles
        valid_articles = [a for a in articles if a.get("title", "").strip()]

        if not valid_articles:
            return SentimentScore(
                score=Decimal("0.0"),
                confidence=Decimal("0.0"),
                timestamp=datetime.now(),
                reasoning="No valid news articles with content available",
            )

        # Sentiment keywords
        positive_keywords = {
            "surge",
            "surges",
            "gain",
            "gains",
            "profit",
            "profits",
            "growth",
            "success",
            "upgrade",
            "buy",
            "strong",
            "exceed",
            "exceeds",
            "beat",
            "beats",
            "record",
            "rise",
            "rises",
            "up",
            "increase",
        }

        negative_keywords = {
            "fall",
            "falls",
            "loss",
            "losses",
            "decline",
            "declines",
            "downgrade",
            "sell",
            "weak",
            "concern",
            "concerns",
            "risk",
            "risks",
            "miss",
            "misses",
            "drop",
            "drops",
            "down",
            "decrease",
            "plummet",
            "plummets",
        }

        # Analyze each article
        sentiments = []
        themes = set()
        risks = set()

        for article in valid_articles:
            title = article["title"].lower()
            words = set(title.split())

            # Count positive and negative words
            positive_count = len(words & positive_keywords)
            negative_count = len(words & negative_keywords)

            # Calculate article sentiment
            if positive_count > negative_count:
                sentiment = (
                    Decimal("0.7") if positive_count > negative_count + 1 else Decimal("0.4")
                )
                # Extract theme
                for word in words & positive_keywords:
                    themes.add(word)
            elif negative_count > positive_count:
                sentiment = (
                    Decimal("-0.7") if negative_count > positive_count + 1 else Decimal("-0.4")
                )
                # Extract risk
                for word in words & negative_keywords:
                    risks.add(word)
            else:
                sentiment = Decimal("0.0")

            sentiments.append(sentiment)

        # Aggregate sentiments
        if sentiments:
            avg_sentiment = sum(sentiments, Decimal("0.0")) / Decimal(len(sentiments))
        else:
            avg_sentiment = Decimal("0.0")

        # Calculate confidence based on number of articles and agreement
        confidence = self._calculate_confidence(sentiments)

        # Create reasoning
        reasoning = f"Analyzed {len(valid_articles)} news articles for {symbol}. "
        if avg_sentiment > Decimal("0.3"):
            reasoning += "Overall sentiment is positive."
        elif avg_sentiment < Decimal("-0.3"):
            reasoning += "Overall sentiment is negative."
        else:
            reasoning += "Overall sentiment is neutral."

        return SentimentScore(
            score=avg_sentiment,
            confidence=confidence,
            timestamp=datetime.now(),
            key_themes=list(themes)[:5],  # Limit to top 5
            risk_factors=list(risks)[:5],  # Limit to top 5
            reasoning=reasoning,
        )

    def _calculate_confidence(self, sentiments: list[Decimal]) -> Decimal:
        """
        Calculate confidence based on number of articles and agreement

        Args:
            sentiments: List of individual sentiment scores

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not sentiments:
            return Decimal("0.0")

        # Base confidence on number of articles
        num_articles = len(sentiments)
        if num_articles >= 10:
            base_confidence = Decimal("0.9")
        elif num_articles >= 5:
            base_confidence = Decimal("0.7")
        elif num_articles >= 3:
            base_confidence = Decimal("0.5")
        elif num_articles == 2:
            base_confidence = Decimal("0.25")
        else:  # 1 article
            base_confidence = Decimal("0.2")

        # Adjust for agreement (standard deviation penalty)
        if len(sentiments) > 1:
            mean = sum(sentiments, Decimal("0.0")) / Decimal(len(sentiments))
            variance = sum((s - mean) ** 2 for s in sentiments) / Decimal(len(sentiments))
            std_dev = variance ** Decimal("0.5")

            # High disagreement (std_dev > 0.5) reduces confidence
            if std_dev > Decimal("0.5"):
                base_confidence *= Decimal("0.7")
            elif std_dev > Decimal("0.3"):
                base_confidence *= Decimal("0.85")

        return min(base_confidence, Decimal("1.0"))

    def _get_from_cache(self, symbol: str) -> SentimentScore | None:
        """
        Get sentiment from cache if available and fresh

        Args:
            symbol: Stock symbol

        Returns:
            Cached SentimentScore or None
        """
        if symbol not in _sentiment_cache:
            return None

        result, timestamp = _sentiment_cache[symbol]
        age = datetime.now() - timestamp

        if age.total_seconds() < CACHE_TTL_SECONDS:
            return result

        # Cache expired
        del _sentiment_cache[symbol]
        return None

    def _cache_result(self, symbol: str, result: SentimentScore) -> None:
        """
        Cache sentiment result

        Args:
            symbol: Stock symbol
            result: Sentiment score to cache
        """
        _sentiment_cache[symbol] = (result, datetime.now())

    @staticmethod
    def clear_cache() -> None:
        """Clear the sentiment cache (useful for testing)"""
        _sentiment_cache.clear()


__all__ = ["NewsSentimentAnalyzer"]
