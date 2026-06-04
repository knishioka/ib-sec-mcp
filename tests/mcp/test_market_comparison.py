"""Tests for market comparison MCP tools.

These tests register the tools on a real :class:`fastmcp.FastMCP` instance and
invoke them through the FastMCP tool API so the production code path is
exercised (and recorded by coverage). All yfinance access is mocked via a
symbol-dispatching :class:`FakeTicker`, so the suite is network-independent.

Because :func:`compare_with_benchmark` imports ``yfinance`` lazily *inside* the
tool function (``import yfinance as yf``), the patch target is the real
``yfinance.Ticker`` attribute rather than a module-local alias.
"""

import json
from collections.abc import Callable
from typing import Any

import pandas as pd
import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.exceptions import ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.tools.market_comparison import register_market_comparison_tools
from tests.mcp._fastmcp_helpers import call_tool_fn

PATCH_TARGET = "yfinance.Ticker"


class FakeTicker:
    """yfinance ticker fake dispatching on the requested symbol.

    Class-level dicts hold per-symbol payloads:

    - ``histories``: DataFrame returned by ``.history(period=...)``
    - ``infos``: dict returned by the ``.info`` property
    - ``recommendations_data``: DataFrame returned by ``.recommendations``
    - ``calendars``: dict returned by the ``.calendar`` property

    A payload that is an ``Exception`` instance is raised, allowing failure
    simulation per access point.
    """

    histories: dict[str, Any] = {}
    infos: dict[str, Any] = {}
    recommendations_data: dict[str, Any] = {}
    calendars: dict[str, Any] = {}

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, period: str = "1y") -> Any:
        value = self.histories[self.symbol]
        if isinstance(value, Exception):
            raise value
        return value

    @property
    def info(self) -> Any:
        value = self.infos.get(self.symbol, {})
        if isinstance(value, Exception):
            raise value
        return value

    @property
    def recommendations(self) -> Any:
        return self.recommendations_data.get(self.symbol)

    @property
    def calendar(self) -> Any:
        return self.calendars.get(self.symbol)


def _make_history(closes: list[float]) -> pd.DataFrame:
    """Build a minimal history DataFrame with a deterministic Close series."""
    return pd.DataFrame({"Close": closes})


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with the market comparison tools registered."""
    mcp = FastMCP("test")
    register_market_comparison_tools(mcp)
    return mcp


@pytest.fixture()
def patch_ticker(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """Install FakeTicker with the supplied per-symbol payloads.

    ``monkeypatch.setattr`` restores both ``yfinance.Ticker`` and the
    class-level payload dicts after each test, preventing state leakage.
    """

    def _apply(
        *,
        histories: dict[str, Any] | None = None,
        infos: dict[str, Any] | None = None,
        recommendations: dict[str, Any] | None = None,
        calendars: dict[str, Any] | None = None,
    ) -> None:
        monkeypatch.setattr(FakeTicker, "histories", histories or {})
        monkeypatch.setattr(FakeTicker, "infos", infos or {})
        monkeypatch.setattr(FakeTicker, "recommendations_data", recommendations or {})
        monkeypatch.setattr(FakeTicker, "calendars", calendars or {})
        monkeypatch.setattr(PATCH_TARGET, FakeTicker)

    return _apply


# ---------------------------------------------------------------------------
# compare_with_benchmark
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_with_benchmark_happy_path(
    test_mcp: FastMCP, patch_ticker: Callable[..., None]
) -> None:
    """Valid inputs produce the full comparison payload with expected keys.

    The stock rises 20% (100 -> 120) while the benchmark rises 10%
    (100 -> 110), so the stock outperforms by ~10 percentage points.
    """
    patch_ticker(
        histories={
            "AAPL": _make_history([100.0, 105.0, 110.0, 115.0, 120.0]),
            "SPY": _make_history([100.0, 102.5, 105.0, 107.5, 110.0]),
        }
    )

    result = await call_tool_fn(
        test_mcp,
        "compare_with_benchmark",
        symbol="AAPL",
        benchmark="SPY",
        period="1y",
        ctx=None,
    )
    data = json.loads(result)

    assert data["symbol"] == "AAPL"
    assert data["benchmark"] == "SPY"
    assert data["period"] == "1y"

    perf = data["performance"]
    assert perf["stock_return_pct"] == 20.0
    assert perf["benchmark_return_pct"] == 10.0
    assert perf["outperformance_pct"] == 10.0

    risk = data["risk_metrics"]
    # Perfectly co-linear (both are straight lines) -> correlation == 1.0
    assert risk["correlation"] == 1.0
    assert "beta" in risk
    assert "alpha_pct" in risk

    interp = data["interpretation"]
    assert set(interp) == {"beta", "alpha", "sharpe"}


@pytest.mark.asyncio
async def test_compare_with_benchmark_detects_underperformance(
    test_mcp: FastMCP, patch_ticker: Callable[..., None]
) -> None:
    """A declining stock vs a rising benchmark yields negative outperformance."""
    patch_ticker(
        histories={
            "TSLA": _make_history([100.0, 95.0, 90.0, 85.0, 80.0]),
            "SPY": _make_history([100.0, 103.0, 106.0, 109.0, 112.0]),
        }
    )

    result = await call_tool_fn(
        test_mcp,
        "compare_with_benchmark",
        symbol="TSLA",
        benchmark="SPY",
        period="6mo",
        ctx=None,
    )
    data = json.loads(result)

    assert data["performance"]["stock_return_pct"] == -20.0
    assert data["performance"]["benchmark_return_pct"] == 12.0
    assert data["performance"]["outperformance_pct"] == -32.0
    assert data["interpretation"]["alpha"].startswith("Underperformed")


@pytest.mark.asyncio
async def test_compare_with_benchmark_invalid_symbol_raises(
    test_mcp: FastMCP, patch_ticker: Callable[..., None]
) -> None:
    """An invalid symbol is rejected before any yfinance access."""
    patch_ticker(histories={})

    with pytest.raises(ValidationError):
        await call_tool_fn(
            test_mcp,
            "compare_with_benchmark",
            symbol="!!bad!!",
            benchmark="SPY",
            period="1y",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_compare_with_benchmark_invalid_period_raises(
    test_mcp: FastMCP, patch_ticker: Callable[..., None]
) -> None:
    """An unsupported period string is rejected by the validator."""
    patch_ticker(histories={})

    with pytest.raises(ValidationError):
        await call_tool_fn(
            test_mcp,
            "compare_with_benchmark",
            symbol="AAPL",
            benchmark="SPY",
            period="7y",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_compare_with_benchmark_empty_dataframe_raises_yahoo_error(
    test_mcp: FastMCP, patch_ticker: Callable[..., None]
) -> None:
    """An empty history DataFrame surfaces as a YahooFinanceError."""
    patch_ticker(
        histories={
            "AAPL": pd.DataFrame({"Close": []}),
            "SPY": _make_history([100.0, 110.0]),
        }
    )

    with pytest.raises(YahooFinanceError):
        await call_tool_fn(
            test_mcp,
            "compare_with_benchmark",
            symbol="AAPL",
            benchmark="SPY",
            period="1y",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_compare_with_benchmark_yfinance_failure_wrapped(
    test_mcp: FastMCP, patch_ticker: Callable[..., None]
) -> None:
    """An unexpected yfinance error is wrapped into a YahooFinanceError."""
    patch_ticker(
        histories={
            "AAPL": RuntimeError("network down"),
            "SPY": _make_history([100.0, 110.0]),
        }
    )

    with pytest.raises(YahooFinanceError):
        await call_tool_fn(
            test_mcp,
            "compare_with_benchmark",
            symbol="AAPL",
            benchmark="SPY",
            period="1y",
            ctx=None,
        )


# ---------------------------------------------------------------------------
# get_analyst_consensus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_analyst_consensus_happy_path(
    test_mcp: FastMCP, patch_ticker: Callable[..., None]
) -> None:
    """Info, recommendations and calendar are aggregated into consensus output."""
    recommendations = pd.DataFrame(
        [
            {"strongBuy": 5, "buy": 10, "hold": 3, "sell": 1, "strongSell": 0},
        ]
    )
    patch_ticker(
        infos={
            "AAPL": {
                "currentPrice": 100.0,
                "targetMeanPrice": 120.0,
                "targetHighPrice": 150.0,
                "targetLowPrice": 90.0,
                "targetMedianPrice": 118.0,
                "numberOfAnalystOpinions": 19,
            }
        },
        recommendations={"AAPL": recommendations},
        calendars={
            "AAPL": {
                "Earnings Date": ["2026-02-01"],
                "Earnings Average": 1.5,
                "Earnings High": 1.8,
                "Earnings Low": 1.2,
                "Revenue Average": 1000,
                "Revenue High": 1100,
                "Revenue Low": 900,
            }
        },
    )

    result = await call_tool_fn(
        test_mcp,
        "get_analyst_consensus",
        symbol="AAPL",
        ctx=None,
    )
    data = json.loads(result)

    assert data["symbol"] == "AAPL"
    assert data["analyst_count"] == 19

    recs = data["analyst_recommendations"]
    assert recs["strong_buy"] == 5
    assert recs["buy"] == 10
    assert recs["total_analysts"] == 19
    # strongBuy (5) is not > 50% of 19, but strongBuy+buy (15) is -> "Buy"
    assert recs["consensus"] == "Buy"

    target = data["target_price"]
    assert target["current_price"] == 100.0
    assert target["target_mean"] == 120.0
    assert target["upside_potential_pct"] == 20.0

    earnings = data["earnings_estimates"]
    assert earnings["earnings_date"] == "2026-02-01"
    assert earnings["earnings_average"] == 1.5


@pytest.mark.asyncio
async def test_get_analyst_consensus_strong_buy_consensus(
    test_mcp: FastMCP, patch_ticker: Callable[..., None]
) -> None:
    """A dominant strongBuy count yields a "Strong Buy" consensus label."""
    recommendations = pd.DataFrame(
        [{"strongBuy": 8, "buy": 1, "hold": 1, "sell": 0, "strongSell": 0}]
    )
    patch_ticker(
        infos={"AAPL": {"regularMarketPrice": 50.0, "targetMeanPrice": 60.0}},
        recommendations={"AAPL": recommendations},
    )

    result = await call_tool_fn(
        test_mcp,
        "get_analyst_consensus",
        symbol="AAPL",
        ctx=None,
    )
    data = json.loads(result)

    assert data["analyst_recommendations"]["consensus"] == "Strong Buy"
    # current_price falls back to regularMarketPrice when currentPrice is absent
    assert data["target_price"]["current_price"] == 50.0
    assert data["target_price"]["upside_potential_pct"] == 20.0


@pytest.mark.asyncio
async def test_get_analyst_consensus_minimal_info(
    test_mcp: FastMCP, patch_ticker: Callable[..., None]
) -> None:
    """Missing recommendations/calendar yield empty sub-objects, not failures."""
    patch_ticker(
        infos={"NVDA": {"currentPrice": 200.0}},
        recommendations={"NVDA": None},
        calendars={"NVDA": None},
    )

    result = await call_tool_fn(
        test_mcp,
        "get_analyst_consensus",
        symbol="NVDA",
        ctx=None,
    )
    data = json.loads(result)

    assert data["analyst_recommendations"] == {}
    assert data["earnings_estimates"] == {}
    # No target_mean -> no upside computed
    assert "upside_potential_pct" not in data["target_price"]
    assert data["target_price"]["current_price"] == 200.0


@pytest.mark.asyncio
async def test_get_analyst_consensus_invalid_symbol_raises(
    test_mcp: FastMCP, patch_ticker: Callable[..., None]
) -> None:
    """An invalid symbol is rejected before any yfinance access."""
    patch_ticker(infos={})

    with pytest.raises(ValidationError):
        await call_tool_fn(
            test_mcp,
            "get_analyst_consensus",
            symbol="",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_get_analyst_consensus_yfinance_failure_wrapped(
    test_mcp: FastMCP, patch_ticker: Callable[..., None]
) -> None:
    """An error reading ``ticker.info`` is wrapped into a YahooFinanceError."""
    patch_ticker(infos={"AAPL": RuntimeError("info unavailable")})

    with pytest.raises(YahooFinanceError):
        await call_tool_fn(
            test_mcp,
            "get_analyst_consensus",
            symbol="AAPL",
            ctx=None,
        )
