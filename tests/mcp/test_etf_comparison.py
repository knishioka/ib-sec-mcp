"""Tests for ETF comparison MCP tools.

These tests register :func:`compare_etf_performance` on a real
:class:`fastmcp.FastMCP` instance and invoke it through the FastMCP tool API so
that the production code path is exercised (and recorded by coverage). All
``yfinance`` access is mocked via ``yfinance.Ticker``, so the suite is
network-independent.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.exceptions import ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.tools.etf_comparison import register_etf_comparison_tools
from tests.mcp._fastmcp_helpers import call_tool_fn

PATCH_TARGET = "yfinance.Ticker"


def _make_history(closes: list[float]) -> pd.DataFrame:
    """Build a daily ``Close`` history DataFrame indexed by business days."""
    index = pd.date_range("2025-01-01", periods=len(closes), freq="B")
    return pd.DataFrame({"Close": closes}, index=index)


def _steady_growth(start: float, daily_rate: float, days: int) -> list[float]:
    """Generate a deterministic compounding price series."""
    return [start * (1 + daily_rate) ** i for i in range(days)]


def _random_walk(
    start: float, days: int, seed: int, drift: float = 0.0005, vol: float = 0.01
) -> list[float]:
    """Generate a deterministic random-walk price series with real variability.

    Unlike a smooth compounding curve, this produces both up and down days so
    downside-based metrics (Sortino, max drawdown) are well defined and the
    return series has non-zero variance for correlation calculations.
    """
    rng = np.random.default_rng(seed)
    shocks = rng.normal(drift, vol, days)
    prices = [start]
    for shock in shocks[1:]:
        prices.append(prices[-1] * (1 + shock))
    return prices


def _correlated_walk(base_prices: list[float], seed: int, noise: float = 0.001) -> list[float]:
    """Build a price series whose returns closely track ``base_prices``."""
    base = pd.Series(base_prices).pct_change().fillna(0.0).to_numpy()
    rng = np.random.default_rng(seed)
    new_returns = base * 0.9 + rng.normal(0, noise, len(base))
    prices = [base_prices[0]]
    for ret in new_returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    return prices


class FakeTicker:
    """yfinance ticker fake dispatching per-symbol history/info payloads.

    ``histories`` and ``infos`` are class-level dicts keyed by symbol. A value
    that is an :class:`Exception` instance is raised to simulate API failures.
    """

    histories: dict[str, Any] = {}
    infos: dict[str, Any] = {}

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, period: str = "1y", auto_adjust: bool = True) -> pd.DataFrame:
        value = self.histories[self.symbol]
        if isinstance(value, Exception):
            raise value
        return value

    @property
    def info(self) -> dict[str, Any]:
        value = self.infos[self.symbol]
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with the ETF comparison tool registered."""
    mcp = FastMCP("test")
    register_etf_comparison_tools(mcp)
    return mcp


@pytest.fixture()
def patch_ticker(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[dict[str, Any], dict[str, Any]], None]:
    """Install :class:`FakeTicker` with per-symbol history and info payloads."""

    def _apply(histories: dict[str, Any], infos: dict[str, Any]) -> None:
        monkeypatch.setattr(FakeTicker, "histories", histories)
        monkeypatch.setattr(FakeTicker, "infos", infos)
        monkeypatch.setattr(PATCH_TARGET, FakeTicker)

    return _apply


def _default_info(**overrides: Any) -> dict[str, Any]:
    """A baseline yfinance ``.info`` dict with optional overrides."""
    info = {
        "longName": "Test ETF",
        "category": "Bonds",
        "dividendYield": 0.02,
        "dividendRate": 1.5,
        "trailingAnnualDividendYield": 0.018,
        "annualReportExpenseRatio": 0.0007,
        "currentPrice": 100.0,
        "fiftyTwoWeekHigh": 110.0,
        "fiftyTwoWeekLow": 90.0,
    }
    info.update(overrides)
    return info


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_etf_performance_happy_path(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    """Two ETFs plus SPY benchmark produce a full comparison with ranking."""
    # AAA grows faster than BBB, so AAA must be the best performer.
    aaa_hist = _make_history(_steady_growth(100.0, 0.001, 260))
    bbb_hist = _make_history(_steady_growth(100.0, 0.0003, 260))
    spy_hist = _make_history(_steady_growth(100.0, 0.0005, 260))

    patch_ticker(
        {
            "AAA": aaa_hist,
            "BBB": bbb_hist,
            "SPY": spy_hist,
        },
        {
            "AAA": _default_info(longName="Alpha ETF", dividendYield=0.01),
            "BBB": _default_info(longName="Beta ETF", dividendYield=0.05),
            "SPY": _default_info(longName="SPDR S&P 500"),
        },
    )

    result = await call_tool_fn(
        test_mcp, "compare_etf_performance", symbols="AAA,BBB", period="1y", ctx=None
    )
    data = json.loads(result)

    # Top-level structure
    assert set(data) == {
        "comparison_summary",
        "performance_comparison",
        "correlation_analysis",
        "investment_insights",
    }

    summary = data["comparison_summary"]
    assert summary["symbols"] == ["AAA", "BBB"]
    assert summary["period"] == "1y"
    assert summary["num_symbols_analyzed"] == 2

    # AAA compounds faster -> best total return; BBB has the higher dividend yield.
    assert summary["best_performer"]["symbol"] == "AAA"
    assert summary["highest_dividend"]["symbol"] == "BBB"

    # Per-ETF metric blocks exist with expected nested keys.
    perf = data["performance_comparison"]
    assert set(perf) == {"AAA", "BBB"}
    aaa = perf["AAA"]
    assert set(aaa) == {
        "returns",
        "risk",
        "dividends",
        "costs",
        "market_metrics",
        "info",
    }
    assert aaa["returns"]["total_return_pct"] > bbb_total(perf)
    assert aaa["info"]["long_name"] == "Alpha ETF"
    # dividendYield 0.05 -> 5.0 pct (multiplied by 100 in source)
    assert perf["BBB"]["dividends"]["yield_pct"] == pytest.approx(5.0)
    # Expense ratio 0.0007 -> 0.07 pct, cost per 10k = 7.0
    assert aaa["costs"]["expense_ratio_pct"] == pytest.approx(0.07)
    assert aaa["costs"]["estimated_annual_cost_per_10k"] == pytest.approx(7.0)
    # _returns_series scratch key must be stripped from the output.
    assert "_returns_series" not in aaa

    # Correlation analysis: self-correlation is 1.0, matrix square over the symbols.
    matrix = data["correlation_analysis"]["matrix"]
    assert set(matrix) == {"AAA", "BBB"}
    assert matrix["AAA"]["AAA"] == pytest.approx(1.0)

    # Investment insights reference the ranked symbols.
    insights = data["investment_insights"]
    assert insights["best_total_return"].startswith("AAA")
    assert isinstance(insights["recommendations"], list)


def bbb_total(perf: dict[str, Any]) -> float:
    return float(perf["BBB"]["returns"]["total_return_pct"])


@pytest.mark.asyncio
async def test_compare_etf_performance_high_correlation_pair(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    """Two near-identical series are flagged as a high-correlation pair."""
    base = _random_walk(100.0, 260, seed=1)
    aaa_hist = _make_history(base)
    # CCC tracks AAA's day-to-day returns closely -> correlation > 0.7.
    ccc_hist = _make_history(_correlated_walk(base, seed=2))
    spy_hist = _make_history(_random_walk(100.0, 260, seed=3))

    patch_ticker(
        {"AAA": aaa_hist, "CCC": ccc_hist, "SPY": spy_hist},
        {
            "AAA": _default_info(),
            "CCC": _default_info(),
            "SPY": _default_info(),
        },
    )

    result = await call_tool_fn(test_mcp, "compare_etf_performance", symbols="AAA,CCC", ctx=None)
    data = json.loads(result)

    pairs = data["correlation_analysis"]["high_correlation_pairs"]
    assert len(pairs) == 1
    pair = pairs[0]
    assert {pair["symbol1"], pair["symbol2"]} == {"AAA", "CCC"}
    assert abs(pair["correlation"]) > 0.7


# ---------------------------------------------------------------------------
# 2. One symbol fails, others succeed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_etf_performance_skips_empty_symbol(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    """A symbol returning an empty history is dropped, others still analyzed."""
    good_hist = _make_history(_steady_growth(100.0, 0.0008, 260))
    spy_hist = _make_history(_steady_growth(100.0, 0.0005, 260))

    patch_ticker(
        {
            "GOOD": good_hist,
            "EMPTY": pd.DataFrame({"Close": []}),
            "SPY": spy_hist,
        },
        {
            "GOOD": _default_info(),
            "EMPTY": _default_info(),
            "SPY": _default_info(),
        },
    )

    result = await call_tool_fn(test_mcp, "compare_etf_performance", symbols="GOOD,EMPTY", ctx=None)
    data = json.loads(result)

    assert data["comparison_summary"]["symbols"] == ["GOOD"]
    assert data["comparison_summary"]["num_symbols_analyzed"] == 1
    assert set(data["performance_comparison"]) == {"GOOD"}


@pytest.mark.asyncio
async def test_compare_etf_performance_skips_raising_symbol(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    """A symbol whose fetch raises is silently dropped (per-symbol try/except)."""
    good_hist = _make_history(_steady_growth(100.0, 0.0008, 260))
    spy_hist = _make_history(_steady_growth(100.0, 0.0005, 260))

    patch_ticker(
        {
            "GOOD": good_hist,
            "BROKEN": RuntimeError("yahoo exploded"),
            "SPY": spy_hist,
        },
        {
            "GOOD": _default_info(),
            "BROKEN": _default_info(),
            "SPY": _default_info(),
        },
    )

    result = await call_tool_fn(
        test_mcp, "compare_etf_performance", symbols="GOOD,BROKEN", ctx=None
    )
    data = json.loads(result)

    assert set(data["performance_comparison"]) == {"GOOD"}
    assert data["comparison_summary"]["num_symbols_analyzed"] == 1


@pytest.mark.asyncio
async def test_compare_etf_performance_all_fail_raises(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    """When no symbol yields data, a YahooFinanceError is raised."""
    patch_ticker(
        {
            "AAA": pd.DataFrame({"Close": []}),
            "BBB": pd.DataFrame({"Close": []}),
            "SPY": _make_history(_steady_growth(100.0, 0.0005, 260)),
        },
        {
            "AAA": _default_info(),
            "BBB": _default_info(),
            "SPY": _default_info(),
        },
    )

    with pytest.raises(YahooFinanceError):
        await call_tool_fn(test_mcp, "compare_etf_performance", symbols="AAA,BBB", ctx=None)


# ---------------------------------------------------------------------------
# 3. Input validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_etf_performance_invalid_symbol_raises(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    """An invalid symbol is rejected by validate_symbol before any fetch."""
    # No ticker should be fetched, but install a fake to avoid network anyway.
    patch_ticker({}, {})

    with pytest.raises(ValidationError):
        await call_tool_fn(test_mcp, "compare_etf_performance", symbols="AAA,!!bad!!", ctx=None)


@pytest.mark.asyncio
async def test_compare_etf_performance_invalid_period_raises(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    """An unsupported period is rejected by validate_period."""
    patch_ticker({}, {})

    with pytest.raises(ValidationError):
        await call_tool_fn(
            test_mcp,
            "compare_etf_performance",
            symbols="AAA",
            period="bogus",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_compare_etf_performance_too_many_symbols_raises(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    """More than 10 symbols is rejected before any fetch."""
    patch_ticker({}, {})
    symbols = ",".join(f"SYM{i}" for i in range(11))

    with pytest.raises(ValidationError):
        await call_tool_fn(test_mcp, "compare_etf_performance", symbols=symbols, ctx=None)


# ---------------------------------------------------------------------------
# 4. Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_etf_performance_single_etf(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    """A single ETF still produces a complete, self-consistent comparison."""
    aaa_hist = _make_history(_steady_growth(100.0, 0.0006, 260))
    spy_hist = _make_history(_steady_growth(100.0, 0.0005, 260))

    patch_ticker(
        {"AAA": aaa_hist, "SPY": spy_hist},
        {"AAA": _default_info(longName="Solo ETF"), "SPY": _default_info()},
    )

    result = await call_tool_fn(test_mcp, "compare_etf_performance", symbols="AAA", ctx=None)
    data = json.loads(result)

    summary = data["comparison_summary"]
    assert summary["num_symbols_analyzed"] == 1
    # With one symbol it is simultaneously best/worst on every dimension.
    assert summary["best_performer"]["symbol"] == "AAA"
    assert summary["lowest_volatility"]["symbol"] == "AAA"
    assert summary["best_risk_adjusted"]["symbol"] == "AAA"
    assert summary["highest_dividend"]["symbol"] == "AAA"
    # Self-correlation only.
    assert data["correlation_analysis"]["matrix"]["AAA"]["AAA"] == pytest.approx(1.0)
    assert data["correlation_analysis"]["high_correlation_pairs"] == []


@pytest.mark.asyncio
async def test_compare_etf_performance_benchmark_spy_failure_is_tolerated(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    """A failing SPY benchmark fetch drops the symbol relying on it.

    SPY history is fetched per-symbol for beta. The source wraps each ETF's
    computation in a try/except that returns ``None`` on any exception, so a
    broken SPY removes that symbol's data. With only one symbol depending on
    SPY, the result is a YahooFinanceError ("could not fetch data").
    """
    aaa_hist = _make_history(_steady_growth(100.0, 0.0006, 260))

    patch_ticker(
        {
            "AAA": aaa_hist,
            "SPY": RuntimeError("benchmark unavailable"),
        },
        {"AAA": _default_info(), "SPY": _default_info()},
    )

    with pytest.raises(YahooFinanceError):
        await call_tool_fn(test_mcp, "compare_etf_performance", symbols="AAA", ctx=None)


@pytest.mark.asyncio
async def test_compare_etf_performance_financial_values_are_numeric(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any], dict[str, Any]], None],
) -> None:
    """Metric values are JSON numbers (no NaN/inf leaking into the payload)."""
    # A real random walk has down days, so downside-based metrics are finite.
    aaa_hist = _make_history(_random_walk(100.0, 260, seed=7))
    spy_hist = _make_history(_random_walk(100.0, 260, seed=8))

    patch_ticker(
        {"AAA": aaa_hist, "SPY": spy_hist},
        {"AAA": _default_info(), "SPY": _default_info()},
    )

    result = await call_tool_fn(test_mcp, "compare_etf_performance", symbols="AAA", ctx=None)
    data = json.loads(result)
    risk = data["performance_comparison"]["AAA"]["risk"]

    for key in ("volatility_pct", "sharpe_ratio", "sortino_ratio", "max_drawdown_pct"):
        value = risk[key]
        assert isinstance(value, (int, float))
        assert not np.isnan(value)
        assert not np.isinf(value)
