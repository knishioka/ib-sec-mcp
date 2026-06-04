"""Tests for advanced technical analysis MCP tools.

These tests register the tools on a real :class:`fastmcp.FastMCP` instance and
invoke them through the FastMCP tool API so the production code path is
exercised (and recorded by coverage). All yfinance/network access is mocked via
``monkeypatch.setattr("yfinance.Ticker", ...)`` so the suite is
network-independent.

The module-level helper functions operate on plain pandas objects and are unit
tested directly against small, controlled DataFrames.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.exceptions import ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.tools.technical_analysis import (
    _analyze_timeframe_confluence,
    _analyze_trends,
    _analyze_volume,
    _calculate_indicators,
    _calculate_pivot_points,
    _find_support_resistance,
    _generate_signals,
    register_technical_analysis_tools,
)
from tests.mcp._fastmcp_helpers import call_tool_fn

PATCH_TARGET = "yfinance.Ticker"


def _make_history(rows: int = 250, seed: int = 7) -> pd.DataFrame:
    """Build a realistic OHLCV DataFrame with enough rows for all indicators.

    A gently trending random walk keeps Close above the long-term SMA so trend
    and signal logic produce deterministic, non-NaN output.
    """
    rng = np.random.default_rng(seed)
    index = pd.date_range(end="2026-01-01", periods=rows, freq="D")

    # Upward drift plus mild noise -> non-degenerate highs/lows/volume.
    base = 100.0 + np.cumsum(rng.normal(0.15, 1.0, rows))
    base = np.maximum(base, 5.0)
    close = base
    open_ = base + rng.normal(0.0, 0.3, rows)
    high = np.maximum(open_, close) + np.abs(rng.normal(0.5, 0.3, rows))
    low = np.minimum(open_, close) - np.abs(rng.normal(0.5, 0.3, rows))
    volume = rng.integers(1_000_000, 5_000_000, rows)

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )


class FakeTicker:
    """yfinance ticker fake whose ``history`` returns a preset DataFrame.

    ``history_result`` may be a DataFrame (returned for every period) or an
    Exception instance (raised when ``history`` is called).
    """

    history_result: object = None

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, *args: object, **kwargs: object) -> pd.DataFrame:
        result = type(self).history_result
        if isinstance(result, Exception):
            raise result
        assert isinstance(result, pd.DataFrame)
        return result


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with technical analysis tools registered."""
    mcp = FastMCP("test")
    register_technical_analysis_tools(mcp)
    return mcp


@pytest.fixture()
def patch_history(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[object], None]:
    """Install FakeTicker with the given ``history`` payload for the test."""

    def _apply(history_result: object) -> None:
        # Use a fresh per-call subclass so concurrent tests never share state.
        class LocalFakeTicker(FakeTicker):
            pass

        LocalFakeTicker.history_result = history_result
        monkeypatch.setattr(PATCH_TARGET, LocalFakeTicker)

    return _apply


# ---------------------------------------------------------------------------
# get_stock_analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stock_analysis_happy_path(
    test_mcp: FastMCP, patch_history: Callable[[object], None]
) -> None:
    """A successful analysis returns valid JSON with all top-level sections."""
    patch_history(_make_history())

    result = await call_tool_fn(
        test_mcp,
        "get_stock_analysis",
        symbol="PG",
        timeframe="1d",
        lookback_days=252,
        ctx=None,
    )
    data = json.loads(result)

    assert data["symbol"] == "PG"
    assert data["timeframe"] == "1d"
    assert isinstance(data["current_price"], float)
    for key in (
        "support_resistance",
        "trend_analysis",
        "technical_indicators",
        "pivot_points",
        "volume_analysis",
        "trading_signals",
    ):
        assert key in data

    indicators = data["technical_indicators"]
    assert set(indicators) == {"rsi", "macd", "adx", "atr"}
    signals = data["trading_signals"]
    assert "recommendation" in signals
    assert "confidence" in signals
    assert isinstance(signals["signals"], list)


@pytest.mark.asyncio
async def test_get_stock_analysis_empty_dataframe_raises(
    test_mcp: FastMCP, patch_history: Callable[[object], None]
) -> None:
    """An empty history frame surfaces as a YahooFinanceError."""
    patch_history(pd.DataFrame())

    with pytest.raises(YahooFinanceError):
        await call_tool_fn(
            test_mcp,
            "get_stock_analysis",
            symbol="PG",
            timeframe="1d",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_get_stock_analysis_yfinance_error_wrapped(
    test_mcp: FastMCP, patch_history: Callable[[object], None]
) -> None:
    """An unexpected yfinance failure is wrapped in YahooFinanceError."""
    patch_history(RuntimeError("network down"))

    with pytest.raises(YahooFinanceError):
        await call_tool_fn(
            test_mcp,
            "get_stock_analysis",
            symbol="PG",
            timeframe="1d",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_get_stock_analysis_invalid_symbol_raises(test_mcp: FastMCP) -> None:
    """An invalid symbol is rejected by validation before any fetch."""
    with pytest.raises(ValidationError):
        await call_tool_fn(
            test_mcp,
            "get_stock_analysis",
            symbol="!!bad!!",
            timeframe="1d",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_get_stock_analysis_invalid_timeframe_raises(
    test_mcp: FastMCP, patch_history: Callable[[object], None]
) -> None:
    """An unsupported timeframe is rejected with ValidationError."""
    patch_history(_make_history())

    with pytest.raises(ValidationError):
        await call_tool_fn(
            test_mcp,
            "get_stock_analysis",
            symbol="PG",
            timeframe="3h",
            ctx=None,
        )


# ---------------------------------------------------------------------------
# get_multi_timeframe_analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_multi_timeframe_analysis_happy_path(
    test_mcp: FastMCP, patch_history: Callable[[object], None]
) -> None:
    """Multi-timeframe analysis returns each timeframe plus confluence."""
    patch_history(_make_history())

    result = await call_tool_fn(
        test_mcp,
        "get_multi_timeframe_analysis",
        symbol="PG",
        ctx=None,
    )
    data = json.loads(result)

    assert data["symbol"] == "PG"
    assert set(data["timeframes"]) == {"daily", "weekly", "monthly"}
    assert data["timeframes"]["daily"]["timeframe"] == "1d"
    assert data["timeframes"]["weekly"]["timeframe"] == "1wk"
    assert data["timeframes"]["monthly"]["timeframe"] == "1mo"

    confluence = data["confluence_analysis"]
    for key in (
        "score",
        "assessment",
        "trends_aligned",
        "indicators_aligned",
        "divergences",
        "recommendation",
        "higher_timeframe_context",
    ):
        assert key in confluence


@pytest.mark.asyncio
async def test_get_multi_timeframe_analysis_propagates_error(
    test_mcp: FastMCP, patch_history: Callable[[object], None]
) -> None:
    """An empty frame in any timeframe surfaces as YahooFinanceError."""
    patch_history(pd.DataFrame())

    with pytest.raises(YahooFinanceError):
        await call_tool_fn(
            test_mcp,
            "get_multi_timeframe_analysis",
            symbol="PG",
            ctx=None,
        )


@pytest.mark.asyncio
async def test_get_multi_timeframe_analysis_invalid_symbol_raises(test_mcp: FastMCP) -> None:
    """An invalid symbol is rejected before any fetch."""
    with pytest.raises(ValidationError):
        await call_tool_fn(
            test_mcp,
            "get_multi_timeframe_analysis",
            symbol="!!bad!!",
            ctx=None,
        )


# ---------------------------------------------------------------------------
# Module-level helper unit tests
# ---------------------------------------------------------------------------


def test_calculate_indicators_keys_and_signals() -> None:
    """Indicators dict has the expected nested structure and RSI signal logic."""
    hist = _make_history()
    indicators = _calculate_indicators(hist)

    assert set(indicators) == {"rsi", "macd", "adx", "atr"}
    assert set(indicators["rsi"]) == {"value", "signal"}
    assert indicators["rsi"]["signal"] in {"overbought", "oversold", "neutral"}
    assert set(indicators["macd"]) == {"value", "signal", "histogram", "trend"}
    assert indicators["macd"]["trend"] in {"bullish", "bearish"}
    assert indicators["adx"]["trend_strength"] in {"strong", "weak", "insufficient_data"}
    assert indicators["atr"]["volatility"] in {"high", "low", "normal"}


def test_calculate_indicators_rsi_overbought() -> None:
    """A monotonically rising series drives RSI to the overbought band."""
    index = pd.date_range(end="2026-01-01", periods=60, freq="D")
    close = pd.Series(np.linspace(100.0, 160.0, 60), index=index)
    hist = pd.DataFrame(
        {
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(60, 1_000_000),
        },
        index=index,
    )

    indicators = _calculate_indicators(hist)

    assert indicators["rsi"]["value"] is not None
    assert indicators["rsi"]["value"] > 70
    assert indicators["rsi"]["signal"] == "overbought"


def test_find_support_resistance_structure() -> None:
    """Support/resistance returns lists and a categorical current level."""
    hist = _make_history()
    sr = _find_support_resistance(hist)

    assert set(sr) == {
        "resistance_levels",
        "support_levels",
        "nearest_resistance",
        "nearest_support",
        "current_level",
    }
    assert isinstance(sr["resistance_levels"], list)
    assert isinstance(sr["support_levels"], list)
    assert sr["current_level"] in {"near_resistance", "near_support", "neutral"}
    # Resistance levels (when present) sit above current price; support below.
    current = float(hist["Close"].iloc[-1])
    for level in sr["resistance_levels"]:
        assert level > current
    for level in sr["support_levels"]:
        assert level < current


def test_analyze_trends_uptrend_alignment() -> None:
    """A strictly rising series yields aligned uptrends and strong strength."""
    index = pd.date_range(end="2026-01-01", periods=250, freq="D")
    close = pd.Series(np.linspace(50.0, 300.0, 250), index=index)

    trends = _analyze_trends(close)

    assert set(trends) == {
        "short_term",
        "medium_term",
        "long_term",
        "trend_strength",
        "sma_20",
        "sma_50",
        "sma_200",
    }
    assert trends["short_term"] == "uptrend"
    assert trends["medium_term"] == "uptrend"
    assert trends["long_term"] == "uptrend"
    assert trends["trend_strength"] == "strong"


def test_analyze_trends_insufficient_long_term() -> None:
    """Fewer than 200 points leaves the long-term trend undetermined."""
    index = pd.date_range(end="2026-01-01", periods=60, freq="D")
    close = pd.Series(np.linspace(50.0, 120.0, 60), index=index)

    trends = _analyze_trends(close)

    assert trends["long_term"] == "insufficient_data"
    assert trends["sma_200"] is None


def test_calculate_pivot_points_classic_relationships() -> None:
    """Classic pivot points satisfy the standard ordering r2 > r1 > s1 > s2."""
    index = pd.date_range(end="2026-01-01", periods=5, freq="D")
    hist = pd.DataFrame(
        {
            "Open": [10, 11, 12, 13, 14],
            "High": [12, 13, 14, 15, 16],
            "Low": [8, 9, 10, 11, 12],
            "Close": [11, 12, 13, 14, 15],
            "Volume": [100, 100, 100, 100, 100],
        },
        index=index,
    )

    pivots = _calculate_pivot_points(hist)

    # Uses the second-to-last row: high=15, low=11, close=14 -> pivot=40/3.
    classic = pivots["classic"]
    assert classic["pivot"] == round((15 + 11 + 14) / 3, 2)
    assert classic["resistance_2"] > classic["resistance_1"] > classic["pivot"]
    assert classic["pivot"] > classic["support_1"] > classic["support_2"]
    assert set(pivots) == {"classic", "fibonacci"}


def test_analyze_volume_structure_and_obv() -> None:
    """Volume analysis returns ratio/trend fields and a directional OBV trend."""
    index = pd.date_range(end="2026-01-01", periods=30, freq="D")
    close = pd.Series(np.linspace(100.0, 130.0, 30), index=index)
    hist = pd.DataFrame(
        {
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.full(30, 1_000_000),
        },
        index=index,
    )

    vol = _analyze_volume(hist)

    assert set(vol) == {
        "current_volume",
        "average_volume_20d",
        "volume_ratio",
        "volume_trend",
        "obv_trend",
    }
    assert vol["current_volume"] == 1_000_000
    assert vol["volume_trend"] in {"high", "low", "normal"}
    # Strictly rising closes accumulate positive OBV -> bullish.
    assert vol["obv_trend"] == "bullish"


def test_generate_signals_bullish_recommendation() -> None:
    """A confluence of bullish inputs yields a buy-side recommendation."""
    support_resistance = {
        "current_level": "near_support",
        "nearest_support": 95.0,
        "nearest_resistance": 110.0,
    }
    trend_analysis = {"trend_strength": "strong", "short_term": "uptrend"}
    indicators = {
        "rsi": {"value": 25.0, "signal": "oversold"},
        "macd": {"trend": "bullish", "histogram": 0.5},
        "adx": {"value": 30.0, "trend_strength": "strong"},
    }
    volume_analysis = {"volume_trend": "high", "obv_trend": "bullish"}

    signals = _generate_signals(
        100.0, support_resistance, trend_analysis, indicators, volume_analysis
    )

    assert set(signals) == {
        "recommendation",
        "confidence",
        "score",
        "signals",
        "entry_zone",
        "stop_loss",
        "take_profit",
        "risk_reward_ratio",
    }
    assert signals["score"] > 0.5
    assert signals["recommendation"] == "strong_buy"
    # Bullish branch builds an entry zone around nearest support.
    assert signals["entry_zone"] is not None
    assert signals["stop_loss"] is not None
    assert signals["risk_reward_ratio"] is not None


def test_generate_signals_bearish_recommendation() -> None:
    """A confluence of bearish inputs yields a sell recommendation."""
    support_resistance = {
        "current_level": "near_resistance",
        "nearest_support": 90.0,
        "nearest_resistance": 105.0,
    }
    trend_analysis = {"trend_strength": "strong", "short_term": "downtrend"}
    indicators = {
        "rsi": {"value": 80.0, "signal": "overbought"},
        "macd": {"trend": "bearish", "histogram": -0.5},
        "adx": {"value": 30.0, "trend_strength": "strong"},
    }
    volume_analysis = {"volume_trend": "high", "obv_trend": "bearish"}

    signals = _generate_signals(
        100.0, support_resistance, trend_analysis, indicators, volume_analysis
    )

    assert signals["score"] < -0.5
    assert signals["recommendation"] == "sell"


def test_generate_signals_neutral_hold() -> None:
    """Balanced inputs leave the recommendation at hold with no entry zone."""
    support_resistance = {
        "current_level": "neutral",
        "nearest_support": None,
        "nearest_resistance": None,
    }
    trend_analysis = {"trend_strength": "weak", "short_term": "uptrend"}
    indicators = {
        "rsi": {"value": 50.0, "signal": "neutral"},
        "macd": {"trend": "bullish", "histogram": 0.0},
        "adx": {"value": 10.0, "trend_strength": "weak"},
    }
    volume_analysis = {"volume_trend": "normal", "obv_trend": "neutral"}

    signals = _generate_signals(
        100.0, support_resistance, trend_analysis, indicators, volume_analysis
    )

    assert signals["recommendation"] == "hold"
    assert signals["entry_zone"] is None
    assert signals["risk_reward_ratio"] is None


def test_analyze_timeframe_confluence_strong() -> None:
    """All timeframes aligned produces strong confluence with no divergences."""
    daily = {
        "trend_analysis": {"short_term": "uptrend"},
        "technical_indicators": {"rsi": {"signal": "neutral"}},
    }
    weekly = {
        "trend_analysis": {"medium_term": "uptrend"},
        "technical_indicators": {"rsi": {"signal": "neutral"}},
        "support_resistance": {"nearest_support": 90.0, "nearest_resistance": 110.0},
    }
    monthly = {"trend_analysis": {"long_term": "uptrend"}}

    confluence = _analyze_timeframe_confluence(daily, weekly, monthly)

    assert confluence["trends_aligned"] is True
    assert confluence["indicators_aligned"] is True
    assert confluence["score"] == pytest.approx(0.8)
    assert confluence["assessment"] == "strong_confluence"
    assert confluence["divergences"] == []
    assert confluence["higher_timeframe_context"]["weekly_support"] == 90.0


def test_analyze_timeframe_confluence_divergent() -> None:
    """Conflicting trends produce low confluence and recorded divergences."""
    daily = {
        "trend_analysis": {"short_term": "uptrend"},
        "technical_indicators": {"rsi": {"signal": "overbought"}},
    }
    weekly = {
        "trend_analysis": {"medium_term": "downtrend"},
        "technical_indicators": {"rsi": {"signal": "neutral"}},
        "support_resistance": {"nearest_support": None, "nearest_resistance": None},
    }
    monthly = {"trend_analysis": {"long_term": "uptrend"}}

    confluence = _analyze_timeframe_confluence(daily, weekly, monthly)

    assert confluence["trends_aligned"] is False
    assert confluence["indicators_aligned"] is False
    assert confluence["score"] == pytest.approx(0.0)
    assert confluence["assessment"] == "low_confluence"
    assert len(confluence["divergences"]) == 2
