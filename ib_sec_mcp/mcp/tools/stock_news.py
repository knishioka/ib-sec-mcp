"""Stock News Tools

Yahoo Finance news retrieval tools for market intelligence.
"""

import asyncio
import json
from datetime import datetime
from typing import Any

from fastmcp import Context, FastMCP

from ib_sec_mcp.mcp.exceptions import IBTimeoutError, ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.validators import validate_symbol

# Timeout constants (in seconds)
DEFAULT_TIMEOUT = 30


def register_stock_news_tools(mcp: FastMCP) -> None:
    """Register stock news retrieval tools"""

    @mcp.tool
    async def get_stock_news(
        symbol: str,
        limit: int = 10,
        ctx: Context | None = None,
    ) -> str:
        """
        Get latest news articles for a stock symbol

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA", "VOO")
            limit: Maximum number of news articles to return (default: 10, max: 50)
            ctx: MCP context for logging

        Returns:
            JSON string with news articles including title, publisher, link, publish_time, type

        Raises:
            ValidationError: If symbol is invalid or limit is out of range
            YahooFinanceError: If data fetch fails
            TimeoutError: If operation times out

        Example:
            >>> result = await get_stock_news("AAPL", limit=5)
            >>> # Returns latest 5 news articles for Apple Inc.
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)

            if limit < 1 or limit > 50:
                raise ValidationError(f"Limit must be between 1 and 50, got {limit}", field="limit")

            if ctx:
                await ctx.info(f"Fetching latest {limit} news articles for {symbol}")

            import yfinance as yf

            # Fetch news with timeout
            async def fetch_news() -> Any:
                ticker = yf.Ticker(symbol)
                return ticker.news

            news = await asyncio.wait_for(fetch_news(), timeout=DEFAULT_TIMEOUT)

            if not news:
                return json.dumps(
                    {
                        "symbol": symbol,
                        "news_count": 0,
                        "message": f"No news articles found for {symbol}",
                        "articles": [],
                    },
                    indent=2,
                )

            # Limit results
            news = news[:limit]

            result: dict[str, Any] = {
                "symbol": symbol,
                "news_count": len(news),
                "fetch_time": datetime.now().isoformat(),
                "articles": [],
            }

            for article in news:
                # yfinance returns news in nested 'content' structure
                content = article.get("content", article)

                article_data = {
                    "title": content.get("title", "N/A"),
                    "publisher": content.get("provider", {}).get("displayName", "Unknown"),
                    "link": content.get("canonicalUrl", {}).get("url", "")
                    or content.get("link", ""),
                    "publish_time": content.get("pubDate", "N/A"),
                    "type": content.get("contentType", "STORY"),
                    "summary": content.get("summary", ""),
                }

                # Add thumbnail if available
                thumbnail = content.get("thumbnail")
                if thumbnail and isinstance(thumbnail, dict):
                    resolutions = thumbnail.get("resolutions", [])
                    if resolutions and isinstance(resolutions, list):
                        article_data["thumbnail_url"] = resolutions[0].get("url", "")

                # Add related tickers if available (from top-level or content)
                related_tickers = article.get("relatedTickers") or content.get("relatedTickers")
                if related_tickers:
                    article_data["related_tickers"] = related_tickers

                result["articles"].append(article_data)

            return json.dumps(result, indent=2)

        except (ValidationError, YahooFinanceError, IBTimeoutError):
            raise
        except TimeoutError as e:
            if ctx:
                await ctx.error(f"Timeout fetching news for {symbol}")
            raise IBTimeoutError(f"News fetch timed out after {DEFAULT_TIMEOUT} seconds") from e
        except Exception as e:
            if ctx:
                await ctx.error(f"Unexpected error in get_stock_news: {e!s}")
            raise YahooFinanceError(f"Unexpected error: {e!s}") from e


__all__ = ["register_stock_news_tools"]
