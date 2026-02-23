"""Sentiment Analysis Tools

Market sentiment analysis from news, options, and technical indicators.
"""

import asyncio
import json
from decimal import Decimal
from typing import Literal

from fastmcp import Context, FastMCP

from ib_sec_mcp.analyzers.sentiment.base import BaseSentimentAnalyzer, SentimentScore
from ib_sec_mcp.analyzers.sentiment.composite import CompositeSentimentAnalyzer
from ib_sec_mcp.analyzers.sentiment.news import NewsSentimentAnalyzer
from ib_sec_mcp.analyzers.sentiment.options import OptionsSentimentAnalyzer
from ib_sec_mcp.analyzers.sentiment.technical import TechnicalSentimentAnalyzer
from ib_sec_mcp.mcp.exceptions import IBTimeoutError, ValidationError
from ib_sec_mcp.mcp.validators import validate_symbol

# Timeout constants (in seconds)
DEFAULT_TIMEOUT = 30


def register_sentiment_analysis_tools(mcp: FastMCP) -> None:
    """Register sentiment analysis tools"""

    @mcp.tool
    async def analyze_market_sentiment(
        symbol: str,
        lookback_days: int = 7,
        sources: Literal["news", "options", "technical", "composite"] = "news",
        ctx: Context | None = None,
    ) -> str:
        """
        Analyze market sentiment from multiple sources

        Provides sentiment analysis combining news articles, options market data,
        and technical indicators to assess market psychology and investor sentiment.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA", "VOO")
            lookback_days: Historical period for analysis (default: 7 days)
            sources: Comma-separated list of sources (default: "news")
                     Available: news, options, technical, composite
                     Example: "news,options" or "composite" for all sources

        Returns:
            JSON string with sentiment analysis including:
            - sentiment_score: -1.0 (bearish) to +1.0 (bullish) as Decimal
            - confidence: 0.0 to 1.0 confidence level as Decimal
            - key_themes: List of identified market themes
            - risk_factors: List of identified risks
            - data_points: Number of data sources analyzed
            - timestamp: Analysis timestamp

        Raises:
            ValidationError: If inputs are invalid
            IBTimeoutError: If operation times out

        Example:
            >>> result = await analyze_market_sentiment("AAPL", lookback_days=7, sources="news")
            >>> # Returns news sentiment analysis for Apple Inc.

            >>> result = await analyze_market_sentiment("SPY", sources="composite")
            >>> # Returns composite sentiment from all available sources
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)

            if lookback_days < 1 or lookback_days > 365:
                raise ValidationError(
                    f"lookback_days must be between 1 and 365, got {lookback_days}",
                    field="lookback_days",
                )

            if ctx:
                await ctx.info(
                    f"Analyzing market sentiment for {symbol} "
                    f"(lookback: {lookback_days} days, sources: {sources})"
                )

            # Parse sources
            source_list = [s.strip().lower() for s in sources.split(",")]

            # Determine which analyzer to use
            analyzer: BaseSentimentAnalyzer
            if "composite" in source_list or len(source_list) > 1:
                # Use composite analyzer for multiple sources
                source_analyzers: dict[str, BaseSentimentAnalyzer] = {}
                source_weights: dict[str, Decimal] = {}

                if "news" in source_list or "composite" in source_list:
                    source_analyzers["news"] = NewsSentimentAnalyzer()
                    source_weights["news"] = Decimal("0.4")

                if "options" in source_list or "composite" in source_list:
                    source_analyzers["options"] = OptionsSentimentAnalyzer()
                    source_weights["options"] = Decimal("0.3")

                if "technical" in source_list or "composite" in source_list:
                    source_analyzers["technical"] = TechnicalSentimentAnalyzer()
                    source_weights["technical"] = Decimal("0.3")

                analyzer = CompositeSentimentAnalyzer(
                    sources=source_analyzers, weights=source_weights
                )
            elif "news" in source_list:
                # Use news analyzer for single news source
                analyzer = NewsSentimentAnalyzer()
            elif "options" in source_list:
                # Use options analyzer for single options source
                analyzer = OptionsSentimentAnalyzer()
            elif "technical" in source_list:
                # Use technical analyzer for single technical source
                analyzer = TechnicalSentimentAnalyzer()
            else:
                raise ValidationError(
                    f"Invalid source: {sources}. Available: news, options, technical, composite",
                    field="sources",
                )

            # Run analysis with timeout
            async def run_analysis() -> SentimentScore:
                return await analyzer.analyze_sentiment(symbol)

            sentiment_score = await asyncio.wait_for(run_analysis(), timeout=DEFAULT_TIMEOUT)

            # Convert to JSON-serializable format
            result = {
                "symbol": symbol,
                "sentiment_score": float(sentiment_score.score),
                "confidence": float(sentiment_score.confidence),
                "key_themes": sentiment_score.key_themes,
                "risk_factors": sentiment_score.risk_factors,
                "reasoning": sentiment_score.reasoning,
                "timestamp": sentiment_score.timestamp.isoformat(),
                "sources_analyzed": source_list,
            }

            # Add interpretation
            score = sentiment_score.score
            if score >= Decimal("0.5"):
                interpretation = "Strong Bullish"
            elif score >= Decimal("0.2"):
                interpretation = "Moderately Bullish"
            elif score <= Decimal("-0.5"):
                interpretation = "Strong Bearish"
            elif score <= Decimal("-0.2"):
                interpretation = "Moderately Bearish"
            else:
                interpretation = "Neutral"

            result["interpretation"] = interpretation

            if ctx:
                await ctx.info(
                    f"Sentiment analysis complete: {interpretation} "
                    f"(score: {float(score):.2f}, confidence: {float(sentiment_score.confidence):.2f})"
                )

            return json.dumps(result, indent=2)

        except (ValidationError, IBTimeoutError):
            raise
        except TimeoutError as e:
            if ctx:
                await ctx.error(f"Timeout analyzing sentiment for {symbol}")
            raise IBTimeoutError(
                f"Sentiment analysis timed out after {DEFAULT_TIMEOUT} seconds"
            ) from e
        except Exception as e:
            if ctx:
                await ctx.error(f"Unexpected error in analyze_market_sentiment: {str(e)}")
            # Don't expose internal errors to users
            raise ValidationError(f"Sentiment analysis failed for {symbol}") from e

    @mcp.tool
    async def get_news_sentiment(
        symbol: str,
        ctx: Context | None = None,
    ) -> str:
        """
        Get sentiment analysis from news articles only

        Convenience function for news-only sentiment analysis.
        Analyzes recent news headlines to determine market sentiment.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA", "VOO")
            ctx: MCP context for logging

        Returns:
            JSON string with news sentiment analysis including:
            - sentiment_score: -1.0 (bearish) to +1.0 (bullish)
            - confidence: 0.0 to 1.0 confidence level
            - key_themes: List of identified themes
            - risk_factors: List of identified risks

        Raises:
            ValidationError: If symbol is invalid
            IBTimeoutError: If operation times out

        Example:
            >>> result = await get_news_sentiment("AAPL")
            >>> # Returns news sentiment for Apple Inc.
        """
        try:
            symbol = validate_symbol(symbol)

            if ctx:
                await ctx.info(f"Fetching news sentiment for {symbol}")

            analyzer = NewsSentimentAnalyzer()

            async def run_analysis() -> SentimentScore:
                return await analyzer.analyze_sentiment(symbol)

            sentiment_score = await asyncio.wait_for(run_analysis(), timeout=DEFAULT_TIMEOUT)

            result = {
                "symbol": symbol,
                "sentiment_score": float(sentiment_score.score),
                "confidence": float(sentiment_score.confidence),
                "key_themes": sentiment_score.key_themes,
                "risk_factors": sentiment_score.risk_factors,
                "reasoning": sentiment_score.reasoning,
                "timestamp": sentiment_score.timestamp.isoformat(),
            }

            return json.dumps(result, indent=2)

        except (ValidationError, IBTimeoutError):
            raise
        except TimeoutError as e:
            if ctx:
                await ctx.error(f"Timeout fetching news sentiment for {symbol}")
            raise IBTimeoutError(
                f"News sentiment analysis timed out after {DEFAULT_TIMEOUT} seconds"
            ) from e
        except Exception as e:
            if ctx:
                await ctx.error(f"Unexpected error in get_news_sentiment: {str(e)}")
            raise ValidationError(f"News sentiment analysis failed for {symbol}") from e


__all__ = ["register_sentiment_analysis_tools"]
