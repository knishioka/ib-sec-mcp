"""
Sentiment analysis module for stock market analysis

Provides multi-source sentiment analysis combining news, options market data,
and technical indicators to gauge overall market sentiment for stocks and ETFs.

Architecture
------------
The module uses a strategy pattern with pluggable sentiment analyzers:

1. **BaseSentimentAnalyzer**: Abstract base class defining the interface
2. **NewsSentimentAnalyzer**: Sentiment from news articles and headlines
3. **OptionsSentimentAnalyzer**: Sentiment from Put/Call ratios, IV, and Max Pain
4. **TechnicalSentimentAnalyzer**: Sentiment from RSI, MACD, trends, and levels
5. **CompositeSentimentAnalyzer**: Weighted aggregation of multiple sources

Usage
-----

Basic Usage (via MCP tools):
    >>> from ib_sec_mcp.mcp.tools.sentiment import analyze_market_sentiment
    >>> # Get composite sentiment from all sources
    >>> result = await analyze_market_sentiment(symbol="AAPL", sources="composite")
    >>> # Get technical sentiment only
    >>> result = await analyze_market_sentiment(symbol="SPY", sources="technical")

Programmatic Usage:
    >>> from ib_sec_mcp.analyzers.sentiment import (
    ...     NewsSentimentAnalyzer,
    ...     OptionsSentimentAnalyzer,
    ...     TechnicalSentimentAnalyzer,
    ...     CompositeSentimentAnalyzer,
    ... )
    >>> from decimal import Decimal
    >>>
    >>> # Create individual analyzers
    >>> news_analyzer = NewsSentimentAnalyzer()
    >>> options_analyzer = OptionsSentimentAnalyzer()
    >>> technical_analyzer = TechnicalSentimentAnalyzer()
    >>>
    >>> # Create composite with custom weights
    >>> composite = CompositeSentimentAnalyzer(
    ...     sources={
    ...         "news": news_analyzer,
    ...         "options": options_analyzer,
    ...         "technical": technical_analyzer,
    ...     },
    ...     weights={
    ...         "news": Decimal("0.4"),      # 40% weight
    ...         "options": Decimal("0.3"),   # 30% weight
    ...         "technical": Decimal("0.3"), # 30% weight
    ...     },
    ... )
    >>>
    >>> # Analyze sentiment
    >>> result = await composite.analyze_sentiment(symbol="AAPL")
    >>> print(f"Score: {result.score}, Confidence: {result.confidence}")

Sentiment Score Interpretation
------------------------------
Scores range from -1.0 (very bearish) to +1.0 (very bullish):

    - 0.5 to 1.0: Very Bullish (strong buy signals)
    - 0.2 to 0.5: Bullish (buy bias with good conviction)
    - -0.2 to 0.2: Neutral (mixed signals, wait for clarity)
    - -0.5 to -0.2: Bearish (sell bias)
    - -1.0 to -0.5: Very Bearish (strong sell signals)

Confidence scores range from 0.0 to 1.0:
    - 0.7-1.0: High confidence (multiple sources agree)
    - 0.4-0.7: Medium confidence (some agreement)
    - 0.0-0.4: Low confidence (sources disagree)

Components
----------

News Sentiment (40% default weight):
    - Headlines and article sentiment analysis
    - Publisher credibility weighting
    - Time decay for article recency

Options Market Sentiment (30% default weight):
    - Put/Call ratio: <0.7 bullish, >1.3 bearish
    - IV Rank: High IV favors selling premium
    - Max Pain: Price gravitation toward max pain strike

Technical Sentiment (30% default weight):
    - RSI: <30 oversold (bullish), >70 overbought (bearish)
    - MACD: Bullish/bearish crossovers
    - Trend: Multi-timeframe trend alignment
    - Support/Resistance: Price proximity to key levels

Integration
-----------
Sentiment analysis is integrated into:
    - MCP tools: `analyze_market_sentiment` function
    - /analyze-symbol command: Automatic sentiment inclusion
    - Claude Desktop: Natural language queries

See Also
--------
- README.md section "Market Sentiment Analysis" for complete documentation
- .claude/commands/analyze-symbol.md for integration with symbol analysis
"""

from ib_sec_mcp.analyzers.sentiment.base import BaseSentimentAnalyzer, SentimentScore
from ib_sec_mcp.analyzers.sentiment.composite import CompositeSentimentAnalyzer
from ib_sec_mcp.analyzers.sentiment.news import NewsSentimentAnalyzer
from ib_sec_mcp.analyzers.sentiment.options import OptionsSentimentAnalyzer
from ib_sec_mcp.analyzers.sentiment.technical import TechnicalSentimentAnalyzer

__all__ = [
    "BaseSentimentAnalyzer",
    "SentimentScore",
    "NewsSentimentAnalyzer",
    "OptionsSentimentAnalyzer",
    "TechnicalSentimentAnalyzer",
    "CompositeSentimentAnalyzer",
]
