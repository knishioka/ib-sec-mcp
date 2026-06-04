"""Tests for options analysis MCP tools.

These tests register the options tools on a real :class:`fastmcp.FastMCP`
instance and invoke them through the FastMCP tool API so the production code
path is exercised (and recorded by coverage). All yfinance/network access is
mocked via a ``FakeTicker`` patched over ``yfinance.Ticker`` (the module does
``import yfinance as yf`` inside each tool), so the suite is fully
network-independent.

Every tool in :mod:`ib_sec_mcp.mcp.tools.options` wraps its body in
``try/except`` and returns ``{"error": ...}`` JSON on failure; none of them
raise. Tests therefore assert the actual error-JSON behaviour rather than
expecting raised exceptions.
"""

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, NamedTuple

import pandas as pd
import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.tools.options import register_options_tools
from tests.mcp._fastmcp_helpers import call_tool_fn

PATCH_TARGET = "yfinance.Ticker"


class OptionChain(NamedTuple):
    """Mimic yfinance ``Options`` result with ``.calls`` / ``.puts`` frames."""

    calls: pd.DataFrame
    puts: pd.DataFrame


def make_option_frame(
    strikes: list[float],
    *,
    volumes: list[int] | None = None,
    open_interest: list[int] | None = None,
    last_prices: list[float] | None = None,
    ivs: list[float] | None = None,
) -> pd.DataFrame:
    """Build a realistic options DataFrame with the columns the tools access.

    Columns mirror the yfinance ``option_chain`` schema accessed by the source:
    ``strike``, ``lastPrice``, ``bid``, ``ask``, ``volume``, ``openInterest``,
    ``impliedVolatility``, ``inTheMoney``, ``contractSymbol``.
    """
    n = len(strikes)
    volumes = volumes if volumes is not None else [100] * n
    open_interest = open_interest if open_interest is not None else [500] * n
    last_prices = last_prices if last_prices is not None else [1.0] * n
    ivs = ivs if ivs is not None else [0.30] * n

    return pd.DataFrame(
        {
            "contractSymbol": [f"OPT{int(s)}" for s in strikes],
            "strike": strikes,
            "lastPrice": last_prices,
            "bid": [p - 0.05 for p in last_prices],
            "ask": [p + 0.05 for p in last_prices],
            "volume": volumes,
            "openInterest": open_interest,
            "impliedVolatility": ivs,
            "inTheMoney": [False] * n,
        }
    )


def _future_expiry(days: int = 30) -> str:
    """Return a future expiration date string in YYYY-MM-DD format."""
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


class FakeTicker:
    """yfinance ticker fake backed by class-level per-symbol payloads.

    Each payload is a dict with optional keys:
    ``options`` (tuple of expiry strings), ``chains`` (mapping expiry -> chain
    or a single chain used for any expiry), ``info`` (dict), ``history``
    (DataFrame). An ``Exception`` value anywhere triggers that error to surface
    when the corresponding attribute/method is accessed.
    """

    payloads: dict[str, Any] = {}

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        payload = self.payloads[symbol]
        if isinstance(payload, Exception):
            raise payload
        self._payload = payload

    @property
    def options(self) -> tuple[str, ...]:
        value = self._payload.get("options", ())
        if isinstance(value, Exception):
            raise value
        return value

    def option_chain(self, expiry: str) -> OptionChain:
        chains = self._payload.get("chains")
        if isinstance(chains, Exception):
            raise chains
        if isinstance(chains, OptionChain):
            return chains
        if isinstance(chains, dict):
            return chains[expiry]
        raise ValueError("no chain configured")

    @property
    def info(self) -> dict[str, Any]:
        value = self._payload.get("info", {})
        if isinstance(value, Exception):
            raise value
        return value

    def history(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
        value = self._payload.get("history", pd.DataFrame())
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with the options tools registered."""
    mcp = FastMCP("test")
    register_options_tools(mcp)
    return mcp


@pytest.fixture()
def patch_ticker(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, Any]], None]:
    """Return a helper that installs FakeTicker with the given per-symbol payloads."""

    def _apply(payloads: dict[str, Any]) -> None:
        monkeypatch.setattr(FakeTicker, "payloads", payloads)
        monkeypatch.setattr(PATCH_TARGET, FakeTicker)

    return _apply


# ---------------------------------------------------------------------------
# get_options_chain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_options_chain_returns_expected_keys(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """A valid chain yields calls/puts records and an aggregated summary."""
    exp = _future_expiry()
    chain = OptionChain(
        calls=make_option_frame([90.0, 100.0], volumes=[10, 20], open_interest=[100, 200]),
        puts=make_option_frame([90.0, 100.0], volumes=[5, 15], open_interest=[50, 150]),
    )
    patch_ticker({"SPY": {"options": (exp,), "chains": chain, "info": {"currentPrice": 100.0}}})

    result = await call_tool_fn(test_mcp, "get_options_chain", symbol="SPY", ctx=None)
    data = json.loads(result)

    assert data["symbol"] == "SPY"
    assert data["expiration_date"] == exp
    assert data["available_expirations"] == [exp]
    assert len(data["calls"]) == 2
    assert len(data["puts"]) == 2
    summary = data["summary"]
    assert summary["num_calls"] == 2
    assert summary["num_puts"] == 2
    assert summary["total_call_volume"] == 30
    assert summary["total_put_volume"] == 20
    assert summary["total_call_oi"] == 300
    assert summary["total_put_oi"] == 200


@pytest.mark.asyncio
async def test_get_options_chain_no_options_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """An empty ``.options`` tuple yields a graceful error payload (no raise)."""
    patch_ticker({"NOPT": {"options": ()}})

    result = await call_tool_fn(test_mcp, "get_options_chain", symbol="NOPT", ctx=None)
    data = json.loads(result)

    assert data == {"error": "No options data available for NOPT"}


@pytest.mark.asyncio
async def test_get_options_chain_invalid_expiration_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """An expiration not in the available list returns an error payload."""
    exp = _future_expiry()
    chain = OptionChain(calls=make_option_frame([100.0]), puts=make_option_frame([100.0]))
    patch_ticker({"SPY": {"options": (exp,), "chains": chain, "info": {}}})

    result = await call_tool_fn(
        test_mcp, "get_options_chain", symbol="SPY", expiration_date="1999-01-01", ctx=None
    )
    data = json.loads(result)

    assert "error" in data
    assert "Invalid expiration date" in data["error"]


@pytest.mark.asyncio
async def test_get_options_chain_yfinance_raises_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """A yfinance failure is caught and surfaced as an error payload."""
    patch_ticker({"BOOM": RuntimeError("network down")})

    result = await call_tool_fn(test_mcp, "get_options_chain", symbol="BOOM", ctx=None)
    data = json.loads(result)

    assert data == {"error": "network down"}


# ---------------------------------------------------------------------------
# calculate_put_call_ratio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_call_ratio_open_interest(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Open-interest PCR is put OI / call OI with a bearish interpretation."""
    exp = _future_expiry()
    chain = OptionChain(
        calls=make_option_frame([95.0, 105.0], volumes=[40, 60], open_interest=[100, 100]),
        puts=make_option_frame([95.0, 105.0], volumes=[80, 70], open_interest=[150, 150]),
    )
    patch_ticker({"SPY": {"options": (exp,), "chains": chain, "info": {"currentPrice": 100.0}}})

    result = await call_tool_fn(test_mcp, "calculate_put_call_ratio", symbol="SPY", ctx=None)
    data = json.loads(result)

    # put OI = 300, call OI = 200 -> 1.5
    assert data["put_call_ratio"] == 1.5
    assert data["ratio_type"] == "open_interest"
    assert data["interpretation"].startswith("Bearish")
    assert data["details"]["total_puts"] == 300
    assert data["details"]["total_calls"] == 200
    # ATM strike: nearest to 100.0 among [95, 105] -> 95 (abs tie broken low)
    assert data["strike_distribution"]["atm_strike"] in (95.0, 105.0)


@pytest.mark.asyncio
async def test_put_call_ratio_volume(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Volume PCR divides put volume by call volume."""
    exp = _future_expiry()
    chain = OptionChain(
        calls=make_option_frame([100.0], volumes=[200], open_interest=[10]),
        puts=make_option_frame([100.0], volumes=[100], open_interest=[10]),
    )
    patch_ticker({"SPY": {"options": (exp,), "chains": chain, "info": {"currentPrice": 100.0}}})

    result = await call_tool_fn(
        test_mcp, "calculate_put_call_ratio", symbol="SPY", ratio_type="volume", ctx=None
    )
    data = json.loads(result)

    # put vol 100 / call vol 200 = 0.5 -> Bullish (< 0.7)
    assert data["put_call_ratio"] == 0.5
    assert data["ratio_type"] == "volume"
    assert data["interpretation"].startswith("Bullish")


@pytest.mark.asyncio
async def test_put_call_ratio_zero_calls_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Zero call total yields an explicit error (avoids division by zero)."""
    exp = _future_expiry()
    chain = OptionChain(
        calls=make_option_frame([100.0], volumes=[0], open_interest=[0]),
        puts=make_option_frame([100.0], volumes=[10], open_interest=[10]),
    )
    patch_ticker({"SPY": {"options": (exp,), "chains": chain, "info": {"currentPrice": 100.0}}})

    result = await call_tool_fn(test_mcp, "calculate_put_call_ratio", symbol="SPY", ctx=None)
    data = json.loads(result)

    assert data == {"error": "Call total is zero, cannot calculate ratio"}


@pytest.mark.asyncio
async def test_put_call_ratio_no_options_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Empty options tuple yields a graceful error payload."""
    patch_ticker({"NOPT": {"options": ()}})

    result = await call_tool_fn(test_mcp, "calculate_put_call_ratio", symbol="NOPT", ctx=None)
    data = json.loads(result)

    assert data == {"error": "No options data available for NOPT"}


# ---------------------------------------------------------------------------
# calculate_greeks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_greeks_returns_all_greeks(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Greeks are computed for every strike with sane ATM values."""
    exp = _future_expiry(30)
    strikes = [90.0, 100.0, 110.0]
    chain = OptionChain(
        calls=make_option_frame(strikes, open_interest=[100, 100, 100], ivs=[0.25, 0.25, 0.25]),
        puts=make_option_frame(strikes, open_interest=[100, 100, 100], ivs=[0.25, 0.25, 0.25]),
    )
    patch_ticker({"AAPL": {"options": (exp,), "chains": chain, "info": {"currentPrice": 100.0}}})

    result = await call_tool_fn(test_mcp, "calculate_greeks", symbol="AAPL", ctx=None)
    data = json.loads(result)

    assert data["symbol"] == "AAPL"
    assert data["current_price"] == 100.0
    assert data["expiration_date"] == exp
    assert data["atm_strike"] == 100.0

    call_greek = data["atm_greeks"]["call"]
    put_greek = data["atm_greeks"]["put"]
    for key in ("strike", "delta", "gamma", "theta", "vega", "rho", "implied_volatility"):
        assert key in call_greek
        assert key in put_greek

    # ATM call delta is roughly 0.5; put delta roughly -0.5; gamma/vega positive.
    assert 0.4 < call_greek["delta"] < 0.7
    assert -0.7 < put_greek["delta"] < -0.3
    assert call_greek["gamma"] > 0
    assert call_greek["vega"] > 0
    assert call_greek["theta"] < 0  # time decay

    assert len(data["all_strikes"]["calls"]) == 3
    assert len(data["all_strikes"]["puts"]) == 3
    assert "net_delta" in data["summary"]


@pytest.mark.asyncio
async def test_calculate_greeks_defaults_missing_iv(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """A zero/NaN IV is replaced by the 30% default, so Greeks stay finite."""
    exp = _future_expiry(45)
    chain = OptionChain(
        calls=make_option_frame([100.0], open_interest=[10], ivs=[0.0]),
        puts=make_option_frame([100.0], open_interest=[10], ivs=[0.0]),
    )
    patch_ticker(
        {"AAPL": {"options": (exp,), "chains": chain, "info": {"regularMarketPrice": 100.0}}}
    )

    result = await call_tool_fn(test_mcp, "calculate_greeks", symbol="AAPL", ctx=None)
    data = json.loads(result)

    assert data["atm_greeks"]["call"]["implied_volatility"] == 0.3


@pytest.mark.asyncio
async def test_calculate_greeks_no_price_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Missing current price yields an error payload."""
    exp = _future_expiry()
    chain = OptionChain(calls=make_option_frame([100.0]), puts=make_option_frame([100.0]))
    patch_ticker({"AAPL": {"options": (exp,), "chains": chain, "info": {}}})

    result = await call_tool_fn(test_mcp, "calculate_greeks", symbol="AAPL", ctx=None)
    data = json.loads(result)

    assert data == {"error": "Could not fetch current stock price"}


@pytest.mark.asyncio
async def test_calculate_greeks_no_options_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Empty options tuple yields a graceful error payload."""
    patch_ticker({"NOPT": {"options": ()}})

    result = await call_tool_fn(test_mcp, "calculate_greeks", symbol="NOPT", ctx=None)
    data = json.loads(result)

    assert data == {"error": "No options data available for NOPT"}


# ---------------------------------------------------------------------------
# calculate_iv_metrics
# ---------------------------------------------------------------------------


def _history_frame(prices: list[float]) -> pd.DataFrame:
    """Build a minimal history frame with a ``Close`` column."""
    return pd.DataFrame({"Close": prices})


@pytest.mark.asyncio
async def test_calculate_iv_metrics_returns_metrics(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """IV metrics include the rank/percentile keys and the proxy ``note``."""
    exp = _future_expiry()
    chain = OptionChain(
        calls=make_option_frame([95.0, 100.0, 105.0], ivs=[0.20, 0.35, 0.40]),
        puts=make_option_frame([95.0, 100.0, 105.0], ivs=[0.20, 0.35, 0.40]),
    )
    # 60 trading days of mildly varying closes -> non-degenerate rolling vol.
    prices = [100.0 + (i % 7) - 3 for i in range(60)]
    patch_ticker(
        {
            "SPY": {
                "options": (exp,),
                "chains": chain,
                "info": {"currentPrice": 100.0},
                "history": _history_frame(prices),
            }
        }
    )

    result = await call_tool_fn(test_mcp, "calculate_iv_metrics", symbol="SPY", ctx=None)
    data = json.loads(result)

    assert data["symbol"] == "SPY"
    assert data["current_price"] == 100.0
    # ATM strike is 100.0 with IV 0.35 -> current_iv reported as 35.0%.
    assert data["current_iv"] == 35.0
    for key in (
        "iv_rank",
        "iv_percentile",
        "iv_52week_high",
        "iv_52week_low",
        "iv_52week_mean",
        "interpretation",
        "lookback_days",
        "note",
    ):
        assert key in data
    assert "proxy" in data["note"]
    assert 0 <= data["iv_percentile"] <= 100


@pytest.mark.asyncio
async def test_calculate_iv_metrics_insufficient_history_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Fewer than 20 history rows yields an insufficient-data error."""
    exp = _future_expiry()
    chain = OptionChain(
        calls=make_option_frame([100.0], ivs=[0.30]),
        puts=make_option_frame([100.0], ivs=[0.30]),
    )
    patch_ticker(
        {
            "SPY": {
                "options": (exp,),
                "chains": chain,
                "info": {"currentPrice": 100.0},
                "history": _history_frame([100.0] * 5),
            }
        }
    )

    result = await call_tool_fn(test_mcp, "calculate_iv_metrics", symbol="SPY", ctx=None)
    data = json.loads(result)

    assert data == {"error": "Insufficient historical data"}


@pytest.mark.asyncio
async def test_calculate_iv_metrics_zero_iv_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """A zero ATM IV yields an explicit error before history is consulted."""
    exp = _future_expiry()
    chain = OptionChain(
        calls=make_option_frame([100.0], ivs=[0.0]),
        puts=make_option_frame([100.0], ivs=[0.0]),
    )
    patch_ticker({"SPY": {"options": (exp,), "chains": chain, "info": {"currentPrice": 100.0}}})

    result = await call_tool_fn(test_mcp, "calculate_iv_metrics", symbol="SPY", ctx=None)
    data = json.loads(result)

    assert data == {"error": "Could not fetch current implied volatility"}


# ---------------------------------------------------------------------------
# calculate_max_pain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_max_pain_deterministic_strike(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Max pain is the strike minimising total writer payout for a crafted OI."""
    exp = _future_expiry(7)
    strikes = [90.0, 100.0, 110.0]
    # Heavy call OI at 90 and heavy put OI at 110 push max pain to the middle (100).
    chain = OptionChain(
        calls=make_option_frame(
            strikes, open_interest=[1000, 10, 10], last_prices=[12.0, 5.0, 1.0]
        ),
        puts=make_option_frame(strikes, open_interest=[10, 10, 1000], last_prices=[1.0, 5.0, 12.0]),
    )
    patch_ticker({"SPY": {"options": (exp,), "chains": chain, "info": {"currentPrice": 100.0}}})

    result = await call_tool_fn(test_mcp, "calculate_max_pain", symbol="SPY", ctx=None)
    data = json.loads(result)

    assert data["symbol"] == "SPY"
    assert data["expiration_date"] == exp
    assert data["max_pain_strike"] == 100.0
    assert data["current_price"] == 100.0
    assert data["distance_to_max_pain"] == 0.0
    assert "pain_by_strike" in data
    assert set(data["pain_by_strike"].keys()) == {"90.0", "100.0", "110.0"}
    assert len(data["top_pain_strikes"]) == 3
    # ATM straddle expected move from last prices at strike 100 (5 + 5).
    assert data["expected_move"] == 10.0


@pytest.mark.asyncio
async def test_calculate_max_pain_no_price_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Missing current price yields an error payload."""
    exp = _future_expiry()
    chain = OptionChain(calls=make_option_frame([100.0]), puts=make_option_frame([100.0]))
    patch_ticker({"SPY": {"options": (exp,), "chains": chain, "info": {}}})

    result = await call_tool_fn(test_mcp, "calculate_max_pain", symbol="SPY", ctx=None)
    data = json.loads(result)

    assert data == {"error": "Could not fetch current stock price"}


@pytest.mark.asyncio
async def test_calculate_max_pain_no_future_expiration_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """When all expirations are in the past, an explicit error is returned."""
    past = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    chain = OptionChain(calls=make_option_frame([100.0]), puts=make_option_frame([100.0]))
    patch_ticker({"SPY": {"options": (past,), "chains": chain, "info": {"currentPrice": 100.0}}})

    result = await call_tool_fn(test_mcp, "calculate_max_pain", symbol="SPY", ctx=None)
    data = json.loads(result)

    assert data == {"error": "No future expiration dates available"}


@pytest.mark.asyncio
async def test_calculate_max_pain_no_options_returns_error(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Empty options tuple yields a graceful error payload."""
    patch_ticker({"NOPT": {"options": ()}})

    result = await call_tool_fn(test_mcp, "calculate_max_pain", symbol="NOPT", ctx=None)
    data = json.loads(result)

    assert data == {"error": "No options data available for NOPT"}
