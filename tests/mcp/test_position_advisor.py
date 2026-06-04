"""Tests for the ``evaluate_position`` position-advisor MCP tool.

The tool composes several network-backed building blocks (technicals, news
sentiment, Yahoo Finance info). Those are patched at the module's private
helper boundary so the tests focus on the tool's own synthesis logic:
Buy/Hold/Avoid decisioning, the chase-avoidance guard, staged-entry planning,
Ireland-domicile / FX tax notes, validation, and error masking.
"""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from fastmcp import FastMCP

import ib_sec_mcp.mcp.tools.position_advisor as pa
from ib_sec_mcp.analyzers.sentiment.base import SentimentScore
from ib_sec_mcp.mcp.exceptions import ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.tools.position_advisor import register_position_advisor_tools
from tests.mcp._fastmcp_helpers import call_tool_fn


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def make_tech(
    *,
    score: float = 0.5,
    current_price: float = 100.0,
    current_level: str = "neutral",
    rsi_signal: str = "neutral",
    nearest_support: float | None = 90.0,
    nearest_resistance: float | None = 110.0,
    signal_recommendation: str = "buy",
) -> dict:
    """Build a technical-signals dict matching ``_compute_technical_signals``."""
    return {
        "current_price": current_price,
        "support_resistance": {
            "current_level": current_level,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "support_levels": [nearest_support] if nearest_support else [],
            "resistance_levels": [nearest_resistance] if nearest_resistance else [],
        },
        "trend": {"trend_strength": "strong", "short_term": "uptrend"},
        "indicators": {
            "rsi": {"value": 55.0, "signal": rsi_signal},
            "macd": {"trend": "bullish", "histogram": 0.3},
        },
        "signals": {
            "recommendation": signal_recommendation,
            "score": score,
            "signals": ["Strong uptrend across timeframes"],
        },
    }


def make_stock_ctx(
    *,
    quote_type: str = "EQUITY",
    currency: str = "USD",
    dividend_yield: float | None = 0.015,
    name: str = "Test Corp",
) -> dict:
    return {
        "name": name,
        "quote_type": quote_type,
        "currency": currency,
        "sector": "Technology",
        "industry": "Software",
        "current_price": 100.0,
        "trailing_pe": 25.0,
        "forward_pe": 22.0,
        "dividend_yield": dividend_yield,
        "beta": 1.1,
        "fifty_two_week_high": 130.0,
        "fifty_two_week_low": 80.0,
        "market_cap": 1_000_000_000,
    }


def make_sentiment(score: str = "0.4", confidence: str = "0.8") -> SentimentScore:
    return SentimentScore(
        score=Decimal(score),
        confidence=Decimal(confidence),
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        key_themes=["earnings beat"],
        risk_factors=["macro headwinds"],
        reasoning="test",
    )


@pytest.fixture()
def test_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_position_advisor_tools(mcp)
    return mcp


def patch_components(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tech: dict,
    stock_ctx: dict | None = None,
    sentiment: SentimentScore | None = None,
    profile: dict | None = None,
    events: list[dict] | None = None,
) -> None:
    """Patch the private data-fetch helpers with deterministic results."""
    monkeypatch.setattr(pa, "_compute_technical_signals", AsyncMock(return_value=tech))
    monkeypatch.setattr(pa, "_fetch_stock_context", AsyncMock(return_value=stock_ctx or {}))
    monkeypatch.setattr(pa, "_fetch_sentiment", AsyncMock(return_value=sentiment))
    monkeypatch.setattr(pa, "_fetch_event_risk", AsyncMock(return_value=events or []))
    monkeypatch.setattr(pa, "_read_user_profile", lambda: profile or {})


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------
class TestRecommendation:
    async def test_buy_when_signals_strong(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.6, current_level="neutral"),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("0.5"),
        )
        result = await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)
        data = json.loads(result)
        assert data["symbol"] == "AAPL"
        assert data["recommendation"] == "Buy"
        assert data["conviction"] > pa._BUY_THRESHOLD
        assert data["staged_entry"]["applicable"] is True
        assert data["rationale"]
        # All top-level sections present
        for key in (
            "technical",
            "sentiment",
            "valuation",
            "staged_entry",
            "tax_fx",
            "portfolio_fit",
            "current_price",
        ):
            assert key in data

    async def test_avoid_when_signals_negative(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=-0.6, signal_recommendation="sell"),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("-0.5"),
        )
        result = await call_tool_fn(test_mcp, "evaluate_position", symbol="XYZ", ctx=None)
        data = json.loads(result)
        assert data["recommendation"] == "Avoid"
        assert data["conviction"] <= pa._AVOID_THRESHOLD
        assert data["staged_entry"]["applicable"] is False
        assert data["staged_entry"]["tranches"] == []

    async def test_hold_when_neutral(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.0),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("0.0"),
        )
        result = await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)
        data = json.loads(result)
        assert data["recommendation"] == "Hold"

    async def test_chase_guard_downgrades_buy_to_hold(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Strong score but price near resistance -> do not chase.
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.7, current_level="near_resistance"),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("0.5"),
        )
        result = await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)
        data = json.loads(result)
        assert data["recommendation"] == "Hold"
        assert data["technical"]["current_level"] == "near_resistance"
        assert data["staged_entry"]["waits_for_pullback"] is True
        assert any("pullback" in r.lower() or "chas" in r.lower() for r in data["rationale"])

    async def test_overbought_triggers_chase_guard(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.7, rsi_signal="overbought"),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("0.5"),
        )
        result = await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)
        data = json.loads(result)
        assert data["recommendation"] == "Hold"
        assert data["staged_entry"]["waits_for_pullback"] is True


# ---------------------------------------------------------------------------
# Staged entry
# ---------------------------------------------------------------------------
class TestStagedEntry:
    async def test_tranches_and_sizing(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.6),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("0.5"),
        )
        result = await call_tool_fn(
            test_mcp, "evaluate_position", symbol="AAPL", candidate_size=10000.0, ctx=None
        )
        data = json.loads(result)
        staged = data["staged_entry"]
        assert staged["tranche_count"] == pa.DEFAULT_TRANCHES
        assert len(staged["tranches"]) == pa.DEFAULT_TRANCHES
        # Equal split of candidate size across tranches.
        sizes = [t["size"] for t in staged["tranches"]]
        assert all(s == pytest.approx(10000.0 / pa.DEFAULT_TRANCHES) for s in sizes)
        # Price bands step downward (accumulate on weakness).
        highs = [t["price_band"]["high"] for t in staged["tranches"]]
        assert highs == sorted(highs, reverse=True)

    async def test_deepest_tranche_anchors_to_support(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.6, current_price=100.0, nearest_support=85.0),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("0.5"),
        )
        result = await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)
        data = json.loads(result)
        last = data["staged_entry"]["tranches"][-1]
        # Deepest band brackets the support level (85.0).
        assert last["price_band"]["low"] <= 85.0 <= last["price_band"]["high"]


# ---------------------------------------------------------------------------
# Tax / FX
# ---------------------------------------------------------------------------
class TestTaxFx:
    async def test_ireland_alternative_flagged_for_us_etf(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.6),
            stock_ctx=make_stock_ctx(quote_type="ETF"),
            sentiment=make_sentiment("0.3"),
            profile={
                "residency": {"country": "Malaysia"},
                "etf_preferences": {"domicile": "IE"},
            },
        )
        # VOO is a US-listed ETF mapped to an Ireland-domiciled alternative.
        result = await call_tool_fn(test_mcp, "evaluate_position", symbol="VOO", ctx=None)
        data = json.loads(result)
        assert data["tax_fx"]["ireland_alternative"] == "VUAA.L"
        assert any("Ireland-domiciled" in n for n in data["tax_fx"]["notes"])

    async def test_fx_note_when_currency_differs(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.3),
            stock_ctx=make_stock_ctx(currency="GBP"),
            sentiment=make_sentiment("0.2"),
            profile={"base_currency": "USD"},
        )
        result = await call_tool_fn(test_mcp, "evaluate_position", symbol="IDTL", ctx=None)
        data = json.loads(result)
        assert data["tax_fx"]["security_currency"] == "GBP"
        assert any("FX exposure" in n for n in data["tax_fx"]["notes"])

    async def test_portfolio_fit_size_pct(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.6),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("0.3"),
            profile={
                "allocation_targets": {"stocks": 75, "bonds": 15, "cash": 10},
                "external_holdings": {"total_value": 100000},
            },
        )
        result = await call_tool_fn(
            test_mcp, "evaluate_position", symbol="AAPL", candidate_size=10000.0, ctx=None
        )
        data = json.loads(result)
        fit = data["portfolio_fit"]
        assert fit["asset_class"] == "STK"
        assert fit["target_allocation_pct"] == 75.0
        assert fit["candidate_size_pct_of_external"] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Degradation and validation
# ---------------------------------------------------------------------------
class TestRobustness:
    async def test_sentiment_unavailable_still_returns(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.6),
            stock_ctx=make_stock_ctx(),
            sentiment=None,
        )
        result = await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)
        data = json.loads(result)
        assert data["sentiment"]["available"] is False
        assert data["recommendation"] in {"Buy", "Hold", "Avoid"}

    async def test_invalid_candidate_size_raises(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(monkeypatch, tech=make_tech(), stock_ctx=make_stock_ctx())
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp, "evaluate_position", symbol="AAPL", candidate_size=-5.0, ctx=None
            )

    async def test_invalid_lookback_raises(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(monkeypatch, tech=make_tech(), stock_ctx=make_stock_ctx())
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp, "evaluate_position", symbol="AAPL", lookback_days=0, ctx=None
            )

    async def test_technical_failure_raises_yahoo_error(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            pa,
            "_compute_technical_signals",
            AsyncMock(side_effect=YahooFinanceError("No price history found for AAPL")),
        )
        monkeypatch.setattr(pa, "_fetch_stock_context", AsyncMock(return_value={}))
        monkeypatch.setattr(pa, "_fetch_sentiment", AsyncMock(return_value=None))
        monkeypatch.setattr(pa, "_read_user_profile", lambda: {})
        with pytest.raises(YahooFinanceError):
            await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)

    async def test_generic_technical_failure_is_masked(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A non-IBAnalyticsError from the core technical fetch is wrapped, not leaked.
        monkeypatch.setattr(
            pa,
            "_compute_technical_signals",
            AsyncMock(side_effect=RuntimeError("internal boom")),
        )
        monkeypatch.setattr(pa, "_fetch_stock_context", AsyncMock(return_value={}))
        monkeypatch.setattr(pa, "_fetch_sentiment", AsyncMock(return_value=None))
        monkeypatch.setattr(pa, "_read_user_profile", lambda: {})
        with pytest.raises(YahooFinanceError) as exc_info:
            await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)
        assert "internal boom" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
class TestPureHelpers:
    def test_is_chasing_near_resistance(self) -> None:
        assert pa._is_chasing(make_tech(current_level="near_resistance")) is True

    def test_is_chasing_overbought(self) -> None:
        assert pa._is_chasing(make_tech(rsi_signal="overbought")) is True

    def test_is_chasing_neutral(self) -> None:
        assert pa._is_chasing(make_tech()) is False

    def test_is_chasing_handles_none_valued_keys(self) -> None:
        # Keys present but explicitly None must not raise (gemini PR #149 feedback).
        assert pa._is_chasing({"support_resistance": None, "indicators": None}) is False

    def test_staged_entry_avoid_not_applicable(self) -> None:
        plan = pa._build_staged_entry(
            current_price=100.0,
            support_resistance={"nearest_support": 90.0},
            candidate_size=None,
            recommendation="Avoid",
            chasing_risk=False,
        )
        assert plan["applicable"] is False

    def test_staged_entry_buy_anchors_at_market(self) -> None:
        plan = pa._build_staged_entry(
            current_price=100.0,
            support_resistance={"nearest_support": 90.0},
            candidate_size=None,
            recommendation="Buy",
            chasing_risk=False,
        )
        assert plan["waits_for_pullback"] is False
        assert plan["anchor_price"] == pytest.approx(100.0)
        # Weights sum to ~100%.
        total_weight = sum(t["weight_pct"] for t in plan["tranches"])
        assert total_weight == pytest.approx(100.0, abs=0.5)


# ---------------------------------------------------------------------------
# Technical-signal data guards
# ---------------------------------------------------------------------------
class TestComputeTechnicalSignals:
    async def test_empty_history_raises(self) -> None:
        with patch("yfinance.Ticker") as ticker:
            ticker.return_value.history.return_value = pd.DataFrame()
            with pytest.raises(YahooFinanceError, match="No price history"):
                await pa._compute_technical_signals("AAPL")

    async def test_insufficient_history_raises(self) -> None:
        # Fewer than _MIN_HISTORY_POINTS rows -> guard trips before NaN math
        # (gemini PR #149 feedback).
        short = pd.DataFrame(
            {
                "Open": [1.0] * 5,
                "High": [1.0] * 5,
                "Low": [1.0] * 5,
                "Close": [1.0] * 5,
                "Volume": [100] * 5,
            }
        )
        with patch("yfinance.Ticker") as ticker:
            ticker.return_value.history.return_value = short
            with pytest.raises(YahooFinanceError, match="Insufficient price history"):
                await pa._compute_technical_signals("AAPL")


# ---------------------------------------------------------------------------
# Near-term event risk (issue #131)
# ---------------------------------------------------------------------------
class TestEventRisk:
    async def test_no_events_reports_empty_event_risk(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.6),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("0.5"),
            events=[],
        )
        data = json.loads(
            await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)
        )
        assert data["event_risk"]["near_term"] is False
        assert data["event_risk"]["events"] == []

    async def test_imminent_earnings_forces_pullback_and_rationale(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Strong Buy signals that would normally enter at market...
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.6, current_level="neutral", rsi_signal="neutral"),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("0.5"),
            events=[
                {
                    "symbol": "AAPL",
                    "event_type": "earnings",
                    "event_date": "2026-01-03",
                    "days_until": 2,
                    "flag": "EVENT_SOON",
                }
            ],
        )
        data = json.loads(
            await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)
        )
        # ...but imminent earnings make the plan wait for a pullback.
        assert data["event_risk"]["near_term"] is True
        assert data["event_risk"]["next_earnings_days"] == 2
        assert data["staged_entry"]["waits_for_pullback"] is True
        assert any("event risk" in r.lower() for r in data["rationale"])

    async def test_distant_event_does_not_flag_near_term(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.6),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("0.5"),
            events=[
                {
                    "symbol": "AAPL",
                    "event_type": "ex_dividend",
                    "event_date": "2026-01-12",
                    "days_until": 11,
                    "flag": None,
                }
            ],
        )
        data = json.loads(
            await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)
        )
        assert data["event_risk"]["near_term"] is False
        assert data["event_risk"]["events"]  # still surfaced for visibility

    async def test_imminent_rate_event_flags_near_term_with_label(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An imminent macro rate decision drives near-term risk and a labelled note."""
        patch_components(
            monkeypatch,
            tech=make_tech(score=0.6, current_level="neutral", rsi_signal="neutral"),
            stock_ctx=make_stock_ctx(),
            sentiment=make_sentiment("0.5"),
            events=[
                {
                    "symbol": None,
                    "event_type": "rate",
                    "event_date": "2026-01-03",
                    "days_until": 2,
                    "flag": "EVENT_SOON",
                    "central_bank": "FOMC",
                    "region": "US",
                    "currency": "USD",
                    "description": "FOMC interest rate decision",
                }
            ],
        )
        data = json.loads(
            await call_tool_fn(test_mcp, "evaluate_position", symbol="AAPL", ctx=None)
        )
        assert data["event_risk"]["near_term"] is True
        assert data["event_risk"]["next_earnings_days"] is None
        assert any("FOMC interest rate decision" in r for r in data["rationale"])

    async def test_fetch_event_risk_merges_global_rate_events(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_fetch_event_risk appends curated rate events to per-symbol events."""
        rate_record = {
            "symbol": None,
            "event_type": "rate",
            "event_date": "2026-01-02",
            "days_until": 1,
            "flag": "EVENT_SOON",
            "central_bank": "FOMC",
            "region": "US",
            "currency": "USD",
            "description": "FOMC interest rate decision",
        }
        monkeypatch.setattr(pa, "build_rate_events", lambda *a, **k: [rate_record])

        class _Ticker:
            def __init__(self, symbol: str) -> None:
                self.symbol = symbol

            @property
            def calendar(self) -> dict:
                return {"Earnings Date": [], "Ex-Dividend Date": None}

        with patch("yfinance.Ticker", _Ticker):
            events = await pa._fetch_event_risk("AAPL")

        assert rate_record in events
        assert any(e["event_type"] == "rate" for e in events)

    async def test_fetch_event_risk_keeps_rate_events_on_yfinance_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A yfinance failure still yields the offline rate events."""
        rate_record = {"symbol": None, "event_type": "rate", "days_until": 1, "flag": "EVENT_SOON"}
        monkeypatch.setattr(pa, "build_rate_events", lambda *a, **k: [rate_record])

        class _Ticker:
            def __init__(self, symbol: str) -> None:
                pass

            @property
            def calendar(self) -> dict:
                raise RuntimeError("yfinance down")

        with patch("yfinance.Ticker", _Ticker):
            events = await pa._fetch_event_risk("AAPL")

        assert events == [rate_record]
