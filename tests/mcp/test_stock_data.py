"""Tests for stock data MCP tools.

These tests register the tools on a real :class:`fastmcp.FastMCP` instance and
invoke them through the FastMCP tool API so that the production code path is
exercised (and recorded by coverage). All yfinance access is mocked, so the
suite is network-independent.

Note on patch target: ``stock_data.py`` performs ``import yfinance as yf``
*inside* the tool functions, so the real module attribute ``yfinance.Ticker``
must be patched (not a module-level ``yf`` alias).
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.exceptions import IBTimeoutError, ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.tools.stock_data import register_stock_data_tools
from tests.mcp._fastmcp_helpers import call_tool_fn

PATCH_TARGET = "yfinance.Ticker"


def _make_history(rows: int = 250) -> pd.DataFrame:
    """Build a deterministic OHLCV DataFrame with a DatetimeIndex.

    Prices increase monotonically so indicators have non-NaN latest values once
    ``rows`` exceeds the longest window (200 for sma_200).
    """
    index = pd.date_range(start="2024-01-01", periods=rows, freq="D")
    close = [100.0 + i for i in range(rows)]
    data = {
        "Open": [c - 0.5 for c in close],
        "High": [c + 1.0 for c in close],
        "Low": [c - 1.0 for c in close],
        "Close": close,
        "Volume": [1_000_000 + i * 1_000 for i in range(rows)],
    }
    return pd.DataFrame(data, index=index)


class FakeTicker:
    """yfinance ticker fake backed by class-level fixtures.

    ``history_data`` / ``history_error`` drive ``get_stock_data``; ``info`` and
    ``dividends`` drive ``get_current_price`` / ``get_stock_info``. Errors stored
    on these attributes are raised when accessed.
    """

    history_data: pd.DataFrame | None = None
    history_error: Exception | None = None
    info_data: dict[str, Any] | Exception = {}
    dividends_data: pd.Series | Exception = pd.Series(dtype="float64")

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        if self.history_error is not None:
            raise self.history_error
        assert self.history_data is not None
        return self.history_data

    @property
    def info(self) -> dict[str, Any]:
        if isinstance(self.info_data, Exception):
            raise self.info_data
        return self.info_data

    @property
    def dividends(self) -> pd.Series:
        if isinstance(self.dividends_data, Exception):
            raise self.dividends_data
        return self.dividends_data


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with the stock data tools registered."""
    mcp = FastMCP("test")
    register_stock_data_tools(mcp)
    return mcp


@pytest.fixture()
def patch_ticker(monkeypatch: pytest.MonkeyPatch):
    """Install FakeTicker and configure its class-level fixtures.

    ``monkeypatch.setattr`` restores all attributes after each test, preventing
    cross-test state pollution.
    """

    def _apply(
        *,
        history_data: pd.DataFrame | None = None,
        history_error: Exception | None = None,
        info_data: dict[str, Any] | Exception | None = None,
        dividends_data: pd.Series | Exception | None = None,
    ) -> None:
        monkeypatch.setattr(FakeTicker, "history_data", history_data)
        monkeypatch.setattr(FakeTicker, "history_error", history_error)
        if info_data is not None:
            monkeypatch.setattr(FakeTicker, "info_data", info_data)
        if dividends_data is not None:
            monkeypatch.setattr(FakeTicker, "dividends_data", dividends_data)
        monkeypatch.setattr(PATCH_TARGET, FakeTicker)

    return _apply


# ---------------------------------------------------------------------------
# get_stock_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stock_data_happy_path(test_mcp: FastMCP, patch_ticker) -> None:
    """Valid request returns expected top-level keys and summary fields."""
    patch_ticker(history_data=_make_history(250))

    result = await call_tool_fn(
        test_mcp,
        "get_stock_data",
        symbol="VOO",
        period="1y",
        interval="1d",
        ctx=None,
    )
    parsed = json.loads(result)

    assert parsed["symbol"] == "VOO"
    assert parsed["period"] == "1y"
    assert parsed["interval"] == "1d"

    summary = parsed["summary"]
    for key in (
        "latest_close",
        "period_high",
        "period_low",
        "period_return",
        "avg_volume",
    ):
        assert key in summary

    # data present when summary_only is False (default)
    assert "data" in parsed
    assert parsed["summary"]["latest_close"] == 349.0
    assert parsed["summary"]["period_high"] == 350.0


@pytest.mark.asyncio
async def test_get_stock_data_with_indicators(test_mcp: FastMCP, patch_ticker) -> None:
    """Requested indicators appear under technical_indicators."""
    patch_ticker(history_data=_make_history(250))

    result = await call_tool_fn(
        test_mcp,
        "get_stock_data",
        symbol="AAPL",
        period="1y",
        interval="1d",
        indicators="sma_20,rsi,macd,bollinger,volume_ma,ema_12",
        ctx=None,
    )
    parsed = json.loads(result)

    indicators = parsed["technical_indicators"]
    for key in ("sma_20", "rsi", "macd", "bollinger", "volume_ma", "ema_12"):
        assert key in indicators

    # With 250 monotonic rows the latest values are non-NaN (not None).
    assert indicators["sma_20"]["latest"] is not None
    assert indicators["rsi"]["latest"] is not None
    assert indicators["macd"]["macd"] is not None


@pytest.mark.asyncio
async def test_get_stock_data_summary_only(test_mcp: FastMCP, patch_ticker) -> None:
    """summary_only=True omits the detailed data array."""
    patch_ticker(history_data=_make_history(250))

    result = await call_tool_fn(
        test_mcp,
        "get_stock_data",
        symbol="VOO",
        summary_only=True,
        ctx=None,
    )
    parsed = json.loads(result)

    assert "data" not in parsed
    assert parsed["summary"]["num_records_returned"] == 0


@pytest.mark.asyncio
async def test_get_stock_data_limit(test_mcp: FastMCP, patch_ticker) -> None:
    """limit=N returns only the latest N records."""
    patch_ticker(history_data=_make_history(250))

    result = await call_tool_fn(
        test_mcp,
        "get_stock_data",
        symbol="VOO",
        limit=5,
        ctx=None,
    )
    parsed = json.loads(result)

    assert parsed["summary"]["num_records_returned"] == 5
    assert len(parsed["data"]) == 5
    # num_records reflects the full unlimited dataset.
    assert parsed["summary"]["num_records"] == 250


@pytest.mark.asyncio
async def test_get_stock_data_short_history_nan_indicators(test_mcp: FastMCP, patch_ticker) -> None:
    """Indicators needing more rows than available yield None latest values."""
    patch_ticker(history_data=_make_history(5))

    result = await call_tool_fn(
        test_mcp,
        "get_stock_data",
        symbol="VOO",
        indicators="sma_20",
        ctx=None,
    )
    parsed = json.loads(result)

    # 5 rows < 20-day window -> rolling mean latest is NaN -> serialized None.
    assert parsed["technical_indicators"]["sma_20"]["latest"] is None


@pytest.mark.asyncio
async def test_get_stock_data_invalid_symbol_raises(test_mcp: FastMCP, patch_ticker) -> None:
    """An invalid symbol raises ValidationError before any yfinance access."""
    patch_ticker(history_data=_make_history(250))

    with pytest.raises(ValidationError):
        await call_tool_fn(
            test_mcp,
            "get_stock_data",
            symbol="!!bad!!",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_get_stock_data_empty_dataframe_raises(test_mcp: FastMCP, patch_ticker) -> None:
    """An empty DataFrame raises YahooFinanceError ('No data found')."""
    patch_ticker(history_data=pd.DataFrame())

    with pytest.raises(YahooFinanceError):
        await call_tool_fn(
            test_mcp,
            "get_stock_data",
            symbol="VOO",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_get_stock_data_history_exception_raises(test_mcp: FastMCP, patch_ticker) -> None:
    """An exception inside history() is wrapped as YahooFinanceError."""
    patch_ticker(history_error=RuntimeError("yfinance boom"))

    with pytest.raises(YahooFinanceError):
        await call_tool_fn(
            test_mcp,
            "get_stock_data",
            symbol="VOO",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_get_stock_data_timeout_in_history_raises_timeout(
    test_mcp: FastMCP, patch_ticker
) -> None:
    """A TimeoutError raised by history() is caught first and becomes IBTimeoutError.

    The source's ``except TimeoutError`` precedes ``except Exception``, so a
    ``TimeoutError`` propagating from ``history()`` is wrapped as
    ``IBTimeoutError`` (asserting actual behavior, not the broader except).
    """
    patch_ticker(history_error=TimeoutError("slow"))

    with pytest.raises(IBTimeoutError):
        await call_tool_fn(
            test_mcp,
            "get_stock_data",
            symbol="VOO",
            ctx=None,
        )


# ---------------------------------------------------------------------------
# get_current_price
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_price_happy_path(test_mcp: FastMCP, patch_ticker) -> None:
    """Returns current_price from currentPrice when present."""
    patch_ticker(
        info_data={
            "currentPrice": 350.25,
            "regularMarketPrice": 349.0,
            "previousClose": 348.0,
            "volume": 1_234_567,
            "marketCap": 1_000_000_000,
            "trailingPE": 25.5,
        }
    )

    result = await call_tool_fn(test_mcp, "get_current_price", symbol="VOO", ctx=None)
    parsed = json.loads(result)

    assert parsed["symbol"] == "VOO"
    assert parsed["current_price"] == 350.25
    assert parsed["previous_close"] == 348.0


@pytest.mark.asyncio
async def test_get_current_price_falls_back_to_regular_market_price(
    test_mcp: FastMCP, patch_ticker
) -> None:
    """current_price falls back to regularMarketPrice when currentPrice missing."""
    patch_ticker(
        info_data={
            "regularMarketPrice": 349.0,
            "previousClose": 348.0,
        }
    )

    result = await call_tool_fn(test_mcp, "get_current_price", symbol="VOO", ctx=None)
    parsed = json.loads(result)

    assert parsed["current_price"] == 349.0


@pytest.mark.asyncio
async def test_get_current_price_exception_returns_error(test_mcp: FastMCP, patch_ticker) -> None:
    """A yfinance failure is caught and returned as an error JSON (no raise)."""
    patch_ticker(info_data=RuntimeError("info failed"))

    result = await call_tool_fn(test_mcp, "get_current_price", symbol="VOO", ctx=None)
    parsed = json.loads(result)

    assert "error" in parsed
    assert parsed["error"] == "info failed"


# ---------------------------------------------------------------------------
# get_stock_info
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stock_info_happy_path(test_mcp: FastMCP, patch_ticker) -> None:
    """Returns nested sections with dividends populated from the dividends Series."""
    dividends = pd.Series(
        [1.0, 1.1, 1.2],
        index=pd.date_range("2025-01-01", periods=3, freq="QE"),
    )
    patch_ticker(
        info_data={
            "longName": "Vanguard S&P 500 ETF",
            "shortName": "VOO",
            "sector": "Financial Services",
            "marketCap": 1_000_000_000,
            "trailingPE": 25.5,
            "dividendRate": 4.5,
            "dividendYield": 0.013,
        },
        dividends_data=dividends,
    )

    result = await call_tool_fn(test_mcp, "get_stock_info", symbol="VOO", ctx=None)
    parsed = json.loads(result)

    assert parsed["symbol"] == "VOO"
    assert parsed["basic_info"]["long_name"] == "Vanguard S&P 500 ETF"
    assert parsed["valuation_metrics"]["market_cap"] == 1_000_000_000

    recent = parsed["dividend_info"]["recent_dividends"]
    assert len(recent) == 3
    assert recent[0]["amount"] == 1.0
    assert "date" in recent[0]


@pytest.mark.asyncio
async def test_get_stock_info_empty_dividends(test_mcp: FastMCP, patch_ticker) -> None:
    """An empty dividends Series yields an empty recent_dividends list."""
    patch_ticker(
        info_data={"longName": "No Div Corp"},
        dividends_data=pd.Series(dtype="float64"),
    )

    result = await call_tool_fn(test_mcp, "get_stock_info", symbol="NODIV", ctx=None)
    parsed = json.loads(result)

    assert parsed["dividend_info"]["recent_dividends"] == []


@pytest.mark.asyncio
async def test_get_stock_info_exception_returns_error(test_mcp: FastMCP, patch_ticker) -> None:
    """A yfinance failure is caught and returned as an error JSON (no raise)."""
    patch_ticker(info_data=RuntimeError("info exploded"))

    result = await call_tool_fn(test_mcp, "get_stock_info", symbol="VOO", ctx=None)
    parsed = json.loads(result)

    assert "error" in parsed
    assert parsed["error"] == "info exploded"
