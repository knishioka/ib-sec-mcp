"""
Sentiment Analysis Examples

Demonstrates usage of the market sentiment analysis MCP tools.
These examples show how to use the sentiment analyzers programmatically
or through natural language queries in Claude Desktop.

For complete documentation, see README.md section "Market Sentiment Analysis"
"""

import asyncio

from ib_sec_mcp.mcp.tools.sentiment import analyze_market_sentiment


async def example_composite_sentiment():
    """Example: Get composite sentiment from all sources"""
    print("\n=== Composite Sentiment Analysis ===")

    result = await analyze_market_sentiment(symbol="AAPL", sources="composite")

    print(result)
    print("\nUse Case: Comprehensive view combining news, options, and technical indicators")


async def example_technical_only():
    """Example: Get technical sentiment only"""
    print("\n=== Technical Sentiment Analysis ===")

    result = await analyze_market_sentiment(symbol="SPY", sources="technical")

    print(result)
    print("\nUse Case: Pure technical analysis without fundamental or news bias")


async def example_options_sentiment():
    """Example: Get options market sentiment"""
    print("\n=== Options Market Sentiment ===")

    result = await analyze_market_sentiment(symbol="QQQ", sources="options")

    print(result)
    print("\nUse Case: Understand institutional positioning and implied volatility")


async def example_news_sentiment():
    """Example: Get news sentiment only"""
    print("\n=== News Sentiment Analysis ===")

    result = await analyze_market_sentiment(symbol="TSLA", sources="news")

    print(result)
    print("\nUse Case: Track media coverage and public sentiment")


# Natural Language Usage Examples (for Claude Desktop)
NATURAL_LANGUAGE_EXAMPLES = """
=== Natural Language Usage (Claude Desktop) ===

Once the MCP server is configured in Claude Desktop, you can use natural language:

1. Composite Sentiment (Recommended):
   "Analyze market sentiment for AAPL using all sources"
   "What's the overall sentiment for SPY right now?"
   "Should I buy NVDA based on current sentiment?"

2. Technical Sentiment:
   "What's the technical sentiment for QQQ?"
   "Is the RSI showing overbought conditions for TSLA?"
   "Analyze the trend sentiment for MSFT"

3. Options Market Sentiment:
   "What's the options market sentiment for SPY?"
   "Are institutions bullish or bearish on QQQ based on options?"
   "Check the Put/Call ratio and IV rank for AAPL"

4. News Sentiment:
   "What's the news sentiment around Tesla?"
   "Is the media bullish or bearish on NVDA?"
   "Analyze recent news sentiment for AAPL"

5. Integrated with Symbol Analysis:
   Use the /analyze-symbol command for comprehensive analysis including sentiment:

   /analyze-symbol AAPL

   This automatically includes:
   - Multi-timeframe technical analysis
   - Current price and fundamentals
   - Options market analysis (when available)
   - Composite sentiment analysis (news + options + technical)
   - Trading recommendation with sentiment-based conviction

=== Sentiment Interpretation Guide ===

Score Range | Sentiment      | Interpretation
------------|----------------|----------------------------------
0.5 to 1.0  | Very Bullish   | Strong buy signals
0.2 to 0.5  | Bullish        | Buy bias with good conviction
-0.2 to 0.2 | Neutral        | Mixed signals, wait for clarity
-0.5 to -0.2| Bearish        | Sell bias
-1.0 to -0.5| Very Bearish   | Strong sell signals

Confidence Level | Reliability
-----------------|-------------------------------------
0.7 - 1.0        | High - Multiple sources agree
0.4 - 0.7        | Medium - Some agreement
0.0 - 0.4        | Low - Sources disagree

=== Use Cases ===

1. Entry Timing:
   "Analyze sentiment for AAPL - is this a good entry point?"
   Use composite sentiment + technical analysis to confirm entry

2. Exit Strategy:
   "Has sentiment shifted for my TSLA position?"
   Monitor sentiment changes for position management

3. Risk Assessment:
   "What's the market mood for tech stocks right now?"
   Gauge overall sentiment before major positions

4. Contrarian Signals:
   "Is sentiment extremely bullish or bearish for SPY?"
   Identify potential reversal opportunities

5. Options Strategy Selection:
   "Should I buy or sell options premium for NVDA?"
   Use IV environment from options sentiment to choose strategy

=== Performance ===

- Composite sentiment: ~2-3 seconds
- Individual sources: ~1-2 seconds
- Cached results: 5-minute validity
- Concurrent analysis: Supported for multiple symbols

=== Integration ===

The sentiment analysis is automatically integrated into:
- /analyze-symbol command (Mode 3)
- Claude Desktop natural language queries (Mode 1)
- Direct MCP tool calls (Mode 2)
"""


async def main():
    """Run all examples"""
    print("Market Sentiment Analysis Examples")
    print("=" * 60)

    # Programmatic examples
    await example_composite_sentiment()
    await example_technical_only()
    await example_options_sentiment()
    await example_news_sentiment()

    # Natural language examples
    print(NATURAL_LANGUAGE_EXAMPLES)


if __name__ == "__main__":
    asyncio.run(main())
