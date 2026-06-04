"""Tests for stock news MCP tools.

These tests register the ``get_stock_news`` tool on a real
:class:`fastmcp.FastMCP` instance and invoke it through the FastMCP tool API so
that the production code path is exercised (and recorded by coverage). All
yfinance access is mocked via ``monkeypatch.setattr("yfinance.Ticker", ...)``,
so the suite is network-independent.
"""

import json
from collections.abc import Callable
from typing import Any

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.exceptions import ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.tools.stock_news import register_stock_news_tools
from tests.mcp._fastmcp_helpers import call_tool_fn


class FakeTicker:
    """yfinance ticker fake backed by per-symbol news payloads.

    ``stock_news`` performs ``import yfinance as yf`` inside the tool and reads
    ``ticker.news``. The class attribute is swapped per test via monkeypatch.
    """

    news_by_symbol: dict[str, Any] = {}

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    @property
    def news(self) -> Any:
        value = self.news_by_symbol[self.symbol]
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with the stock news tool registered."""
    mcp = FastMCP("test")
    register_stock_news_tools(mcp)
    return mcp


@pytest.fixture()
def patch_ticker(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, Any]], None]:
    """Return a helper installing FakeTicker with the given per-symbol news.

    Patches ``yfinance.Ticker`` directly because the tool imports yfinance
    lazily inside the function body.
    """

    def _apply(news_by_symbol: dict[str, Any]) -> None:
        monkeypatch.setattr(FakeTicker, "news_by_symbol", news_by_symbol)
        monkeypatch.setattr("yfinance.Ticker", FakeTicker)

    return _apply


def _nested_article(
    title: str,
    publisher: str,
    url: str,
    pub_date: str,
    summary: str = "",
    content_type: str = "STORY",
) -> dict[str, Any]:
    """Build an article using yfinance's nested ``content`` shape."""
    return {
        "content": {
            "title": title,
            "provider": {"displayName": publisher},
            "canonicalUrl": {"url": url},
            "pubDate": pub_date,
            "contentType": content_type,
            "summary": summary,
        }
    }


@pytest.mark.asyncio
async def test_get_stock_news_nested_content_mapping(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Nested ``content`` articles map onto the documented article fields."""
    patch_ticker(
        {
            "AAPL": [
                _nested_article(
                    title="Apple unveils new chip",
                    publisher="Reuters",
                    url="https://example.com/apple-chip",
                    pub_date="2026-01-02T10:00:00Z",
                    summary="A summary of the chip launch.",
                    content_type="STORY",
                )
            ]
        }
    )

    result = await call_tool_fn(test_mcp, "get_stock_news", symbol="AAPL", limit=10, ctx=None)
    parsed = json.loads(result)

    assert parsed["symbol"] == "AAPL"
    assert parsed["news_count"] == 1
    assert "fetch_time" in parsed

    article = parsed["articles"][0]
    assert article["title"] == "Apple unveils new chip"
    assert article["publisher"] == "Reuters"
    assert article["link"] == "https://example.com/apple-chip"
    assert article["publish_time"] == "2026-01-02T10:00:00Z"
    assert article["type"] == "STORY"
    assert article["summary"] == "A summary of the chip launch."


@pytest.mark.asyncio
async def test_get_stock_news_flat_fallback_shape(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Flat articles (no ``content`` key) fall back to top-level fields."""
    patch_ticker(
        {
            "TSLA": [
                {
                    "title": "Tesla flat-shape headline",
                    "provider": {"displayName": "Bloomberg"},
                    # No canonicalUrl -> link fallback is exercised.
                    "link": "https://example.com/tesla-flat",
                    "pubDate": "2026-01-03T08:00:00Z",
                    "contentType": "VIDEO",
                    "summary": "Flat summary.",
                }
            ]
        }
    )

    result = await call_tool_fn(test_mcp, "get_stock_news", symbol="TSLA", limit=10, ctx=None)
    parsed = json.loads(result)

    article = parsed["articles"][0]
    assert article["title"] == "Tesla flat-shape headline"
    assert article["publisher"] == "Bloomberg"
    assert article["link"] == "https://example.com/tesla-flat"
    assert article["publish_time"] == "2026-01-03T08:00:00Z"
    assert article["type"] == "VIDEO"
    assert article["summary"] == "Flat summary."


@pytest.mark.asyncio
async def test_get_stock_news_missing_fields_use_defaults(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Articles missing fields fall back to documented default values."""
    patch_ticker({"AAPL": [{"content": {}}]})

    result = await call_tool_fn(test_mcp, "get_stock_news", symbol="AAPL", limit=10, ctx=None)
    parsed = json.loads(result)

    article = parsed["articles"][0]
    assert article["title"] == "N/A"
    assert article["publisher"] == "Unknown"
    assert article["link"] == ""
    assert article["publish_time"] == "N/A"
    assert article["type"] == "STORY"
    assert article["summary"] == ""
    assert "thumbnail_url" not in article
    assert "related_tickers" not in article


@pytest.mark.asyncio
async def test_get_stock_news_thumbnail_and_related_tickers(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Thumbnail resolutions and related tickers are surfaced when present."""
    patch_ticker(
        {
            "AAPL": [
                {
                    "content": {
                        "title": "With extras",
                        "provider": {"displayName": "CNBC"},
                        "canonicalUrl": {"url": "https://example.com/extras"},
                        "pubDate": "2026-01-04T12:00:00Z",
                        "contentType": "STORY",
                        "summary": "Has thumbnail and related tickers.",
                        "thumbnail": {
                            "resolutions": [
                                {"url": "https://img.example.com/large.jpg"},
                                {"url": "https://img.example.com/small.jpg"},
                            ]
                        },
                        "relatedTickers": ["AAPL", "MSFT"],
                    }
                }
            ]
        }
    )

    result = await call_tool_fn(test_mcp, "get_stock_news", symbol="AAPL", limit=10, ctx=None)
    parsed = json.loads(result)

    article = parsed["articles"][0]
    assert article["thumbnail_url"] == "https://img.example.com/large.jpg"
    assert article["related_tickers"] == ["AAPL", "MSFT"]


@pytest.mark.asyncio
async def test_get_stock_news_related_tickers_from_top_level(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """``relatedTickers`` may live at the article top level, not in content."""
    patch_ticker(
        {
            "AAPL": [
                {
                    "content": {
                        "title": "Top-level related tickers",
                        "provider": {"displayName": "WSJ"},
                        "canonicalUrl": {"url": "https://example.com/top"},
                        "pubDate": "2026-01-05T09:00:00Z",
                        "contentType": "STORY",
                        "summary": "",
                    },
                    "relatedTickers": ["GOOG"],
                }
            ]
        }
    )

    result = await call_tool_fn(test_mcp, "get_stock_news", symbol="AAPL", limit=10, ctx=None)
    parsed = json.loads(result)

    assert parsed["articles"][0]["related_tickers"] == ["GOOG"]


@pytest.mark.asyncio
async def test_get_stock_news_limit_caps_articles(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """The ``limit`` parameter caps the number of returned articles."""
    articles = [
        _nested_article(
            title=f"Headline {i}",
            publisher="Reuters",
            url=f"https://example.com/{i}",
            pub_date="2026-01-02T10:00:00Z",
        )
        for i in range(8)
    ]
    patch_ticker({"AAPL": articles})

    result = await call_tool_fn(test_mcp, "get_stock_news", symbol="AAPL", limit=3, ctx=None)
    parsed = json.loads(result)

    assert parsed["news_count"] == 3
    assert len(parsed["articles"]) == 3
    assert [a["title"] for a in parsed["articles"]] == ["Headline 0", "Headline 1", "Headline 2"]


@pytest.mark.asyncio
async def test_get_stock_news_empty_news_list(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """An empty news list yields a zero-count payload with a message."""
    patch_ticker({"AAPL": []})

    result = await call_tool_fn(test_mcp, "get_stock_news", symbol="AAPL", limit=10, ctx=None)
    parsed = json.loads(result)

    assert parsed["symbol"] == "AAPL"
    assert parsed["news_count"] == 0
    assert parsed["articles"] == []
    assert "message" in parsed


@pytest.mark.asyncio
async def test_get_stock_news_invalid_symbol_raises(test_mcp: FastMCP) -> None:
    """An invalid symbol is rejected before any yfinance access."""
    with pytest.raises(ValidationError):
        await call_tool_fn(test_mcp, "get_stock_news", symbol="!!bad!!", limit=10, ctx=None)


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, 51, -1])
async def test_get_stock_news_limit_out_of_range_raises(test_mcp: FastMCP, limit: int) -> None:
    """A limit below 1 or above 50 raises a ValidationError."""
    with pytest.raises(ValidationError):
        await call_tool_fn(test_mcp, "get_stock_news", symbol="AAPL", limit=limit, ctx=None)


@pytest.mark.asyncio
async def test_get_stock_news_yfinance_failure_raises(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """A yfinance error during news access surfaces as YahooFinanceError."""
    patch_ticker({"AAPL": RuntimeError("yahoo is down")})

    with pytest.raises(YahooFinanceError):
        await call_tool_fn(test_mcp, "get_stock_news", symbol="AAPL", limit=10, ctx=None)
