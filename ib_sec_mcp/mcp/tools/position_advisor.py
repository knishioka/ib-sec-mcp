"""Position Advisor Tool

Synthesizes existing analyzers and data sources into a single, actionable
position decision for a *candidate* symbol:

- **Technicals**: support/resistance, trend, RSI/MACD/ADX/ATR, trading signals
  (reuses the helpers behind ``get_stock_analysis`` — no indicator math is
  re-implemented here).
- **Sentiment**: news sentiment via ``NewsSentimentAnalyzer``.
- **Valuation / info**: sector, P/E, dividend yield, beta, 52-week range
  (Yahoo Finance ``Ticker.info``).
- **Tax / FX**: Malaysia-resident withholding considerations and
  Ireland-domiciled ETF alternatives (``ETF_ALTERNATIVES``).
- **Staged entry**: 3-4 tranche accumulation plan that respects the user's
  "don't chase bounces" rule.
- **Portfolio fit**: target-allocation guidance derived from the user profile
  (``ib://user/profile`` → ``notes/investor-profile.yaml``).

The tool is composition-only: it orchestrates existing building blocks and adds
explicit decision logic (IE-domicile preference, staged entry, chase-avoidance).
It degrades gracefully — sentiment and valuation are best-effort, while price
history is required.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from fastmcp import Context, FastMCP

from ib_sec_mcp.analyzers.sentiment.base import SentimentScore
from ib_sec_mcp.analyzers.sentiment.news import NewsSentimentAnalyzer
from ib_sec_mcp.mcp.exceptions import (
    IBAnalyticsError,
    IBTimeoutError,
    ValidationError,
    YahooFinanceError,
)
from ib_sec_mcp.mcp.tools.ib_portfolio import ETF_ALTERNATIVES
from ib_sec_mcp.mcp.tools.technical_analysis import (
    _analyze_trends,
    _analyze_volume,
    _calculate_indicators,
    _find_support_resistance,
    _generate_signals,
)
from ib_sec_mcp.mcp.validators import validate_symbol
from ib_sec_mcp.utils.logger import get_logger

logger = get_logger(__name__)

# Timeout constants (in seconds)
DEFAULT_TIMEOUT = 30

# Minimum daily bars required for trend/indicator analysis (SMA-20 needs >= 20).
_MIN_HISTORY_POINTS = 20

# User investment profile location (same file backing ib://user/profile)
PROFILE_PATH = Path("notes/investor-profile.yaml")

# Staged-entry defaults
DEFAULT_TRANCHES = 4
# Cumulative discount from the entry anchor for tranches 1..4
_TRANCHE_DISCOUNTS = [0.00, 0.03, 0.06, 0.10]
# When the user should not "chase", first tranche waits for this pullback
_NO_CHASE_PULLBACK = 0.03

# Decision thresholds on the composite conviction score (~ -1.0 .. +1.0)
_BUY_THRESHOLD = 0.20
_AVOID_THRESHOLD = -0.15

# Weighting of technical vs sentiment in the composite score
_TECH_WEIGHT = 0.65
_SENTIMENT_WEIGHT = 0.35


# ---------------------------------------------------------------------------
# Profile / data helpers
# ---------------------------------------------------------------------------
def _read_user_profile() -> dict[str, Any]:
    """Read the user investment profile (notes/investor-profile.yaml).

    Returns an empty dict if the file is missing or malformed so callers can
    degrade gracefully.
    """
    if not PROFILE_PATH.exists():
        return {}
    try:
        with open(PROFILE_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (yaml.YAMLError, OSError) as e:
        logger.warning("Failed to read user profile: %s", e)
        return {}
    return data if isinstance(data, dict) else {}


async def _compute_technical_signals(symbol: str) -> dict[str, Any]:
    """Compute technical analysis by reusing the technical_analysis helpers.

    Fetches ~1y of daily history and runs the same support/resistance, trend,
    indicator, volume and signal computations used by ``get_stock_analysis``.

    Raises:
        IBTimeoutError: If Yahoo Finance times out.
        YahooFinanceError: If no history is available.
    """
    import yfinance as yf

    def _load() -> Any:
        return yf.Ticker(symbol).history(period="252d", interval="1d")

    try:
        hist = await asyncio.wait_for(asyncio.to_thread(_load), timeout=DEFAULT_TIMEOUT)
    except TimeoutError as e:
        raise IBTimeoutError(
            f"Yahoo Finance API timed out after {DEFAULT_TIMEOUT} seconds",
            operation="evaluate_position.technicals",
        ) from e

    if hist is None or hist.empty:
        raise YahooFinanceError(f"No price history found for {symbol}")
    if len(hist) < _MIN_HISTORY_POINTS:
        raise YahooFinanceError(
            f"Insufficient price history for {symbol}: {len(hist)} rows "
            f"(need at least {_MIN_HISTORY_POINTS} for trend/indicator analysis)"
        )

    close = hist["Close"]
    support_resistance = _find_support_resistance(hist)
    trend = _analyze_trends(close)
    indicators = _calculate_indicators(hist)
    volume = _analyze_volume(hist)
    signals = _generate_signals(
        float(close.iloc[-1]),
        support_resistance,
        trend,
        indicators,
        volume,
    )
    return {
        "current_price": float(close.iloc[-1]),
        "support_resistance": support_resistance,
        "trend": trend,
        "indicators": indicators,
        "signals": signals,
    }


async def _fetch_stock_context(symbol: str) -> dict[str, Any]:
    """Fetch valuation / info context via Yahoo Finance ``Ticker.info``.

    Best-effort: returns ``{}`` on any failure so the decision can still be made
    from technicals + sentiment.
    """
    import yfinance as yf

    def _load() -> dict[str, Any]:
        return yf.Ticker(symbol).info or {}

    try:
        info = await asyncio.wait_for(asyncio.to_thread(_load), timeout=DEFAULT_TIMEOUT)
    except Exception as e:
        logger.warning("Failed to fetch stock context for %s: %s", symbol, e)
        return {}

    price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
    return {
        "name": info.get("longName") or info.get("shortName"),
        "quote_type": info.get("quoteType"),  # "EQUITY" | "ETF" | ...
        "currency": info.get("currency"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "current_price": float(price) if price is not None else None,
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "market_cap": info.get("marketCap"),
    }


async def _fetch_sentiment(symbol: str, lookback_days: int) -> SentimentScore | None:
    """Fetch news sentiment, returning ``None`` on failure (best-effort)."""
    analyzer = NewsSentimentAnalyzer(lookback_days=lookback_days)
    try:
        return await asyncio.wait_for(analyzer.analyze_sentiment(symbol), timeout=DEFAULT_TIMEOUT)
    except Exception as e:
        logger.warning("Failed to fetch sentiment for %s: %s", symbol, e)
        return None


# ---------------------------------------------------------------------------
# Pure synthesis helpers
# ---------------------------------------------------------------------------
def _is_chasing(tech: dict[str, Any]) -> bool:
    """Detect whether buying now would be "chasing a bounce".

    True when price sits near resistance or RSI is overbought — situations the
    user explicitly wants to avoid following.
    """
    sr = tech.get("support_resistance") or {}
    if sr.get("current_level") == "near_resistance":
        return True
    rsi = (tech.get("indicators") or {}).get("rsi") or {}
    return bool(rsi.get("signal") == "overbought")


def _synthesize_recommendation(
    tech: dict[str, Any],
    sentiment: SentimentScore | None,
) -> dict[str, Any]:
    """Combine technical and sentiment signals into a Buy/Hold/Avoid decision.

    Returns a dict with ``recommendation``, ``conviction`` (composite score),
    ``technical_score``, ``sentiment_score`` and a ``rationale`` list.
    """
    signals = tech.get("signals") or {}
    technical_score = float(signals.get("score", 0.0))

    sentiment_score = 0.0
    if sentiment is not None:
        # Confidence-weight the sentiment contribution.
        sentiment_score = float(sentiment.score) * float(sentiment.confidence)

    composite = round(_TECH_WEIGHT * technical_score + _SENTIMENT_WEIGHT * sentiment_score, 3)
    chasing = _is_chasing(tech)

    rationale: list[str] = []
    # Surface the strongest technical signals.
    rationale.extend(f"Technical: {sig}" for sig in signals.get("signals", [])[:4])
    if sentiment is not None:
        rationale.extend(f"Sentiment: {theme}" for theme in (sentiment.key_themes or [])[:2])

    if composite >= _BUY_THRESHOLD and chasing:
        recommendation = "Hold"
        rationale.append(
            "Signals are constructive but price is near resistance / overbought — "
            "wait for a pullback rather than chasing the bounce."
        )
    elif composite >= _BUY_THRESHOLD:
        recommendation = "Buy"
        rationale.append(
            f"Composite conviction {composite:+.2f} clears the buy threshold "
            f"({_BUY_THRESHOLD:+.2f}); accumulate in staged tranches."
        )
    elif composite <= _AVOID_THRESHOLD:
        recommendation = "Avoid"
        rationale.append(
            f"Composite conviction {composite:+.2f} is below the avoid threshold "
            f"({_AVOID_THRESHOLD:+.2f}); no compelling entry."
        )
    else:
        recommendation = "Hold"
        rationale.append(
            f"Composite conviction {composite:+.2f} is neutral; wait for a clearer "
            "setup before committing capital."
        )

    return {
        "recommendation": recommendation,
        "conviction": composite,
        "technical_score": round(technical_score, 3),
        "sentiment_score": round(sentiment_score, 3),
        "chasing_risk": chasing,
        "rationale": rationale,
    }


def _build_staged_entry(
    *,
    current_price: float,
    support_resistance: dict[str, Any],
    candidate_size: float | None,
    recommendation: str,
    chasing_risk: bool,
    tranches: int = DEFAULT_TRANCHES,
) -> dict[str, Any]:
    """Build a 3-4 tranche staged-entry plan.

    Tranches step down from an anchor price toward nearest support. When the
    user should not chase (``chasing_risk`` or a non-Buy recommendation), the
    first tranche is set below market to wait for a pullback.
    """
    if recommendation == "Avoid":
        return {
            "applicable": False,
            "reason": "Recommendation is Avoid — no entry plan generated.",
            "tranches": [],
        }

    tranches = max(3, min(tranches, len(_TRANCHE_DISCOUNTS)))
    discounts = _TRANCHE_DISCOUNTS[:tranches]

    # Anchor: buy-at-market for a clean Buy, otherwise wait for a pullback.
    wait_for_pullback = chasing_risk or recommendation != "Buy"
    anchor = current_price * (1 - _NO_CHASE_PULLBACK) if wait_for_pullback else current_price

    nearest_support = support_resistance.get("nearest_support")

    per_tranche_size: float | None = None
    if candidate_size is not None:
        per_tranche_size = round(candidate_size / tranches, 2)
    weight_pct = round(100.0 / tranches, 1)

    plan: list[dict[str, Any]] = []
    for i, discount in enumerate(discounts):
        target = anchor * (1 - discount)
        # Anchor the deepest tranche to support when support sits below it.
        if i == len(discounts) - 1 and nearest_support is not None and nearest_support < target:
            target = float(nearest_support)
        plan.append(
            {
                "tranche": i + 1,
                "price_band": {
                    "low": round(target * 0.99, 2),
                    "high": round(target * 1.01, 2),
                },
                "weight_pct": weight_pct,
                "size": per_tranche_size,
            }
        )

    return {
        "applicable": True,
        "strategy": "staged_entry",
        "tranche_count": tranches,
        "anchor_price": round(anchor, 2),
        "waits_for_pullback": wait_for_pullback,
        "note": (
            "First tranche set below market to avoid chasing the bounce; scale in "
            "on weakness toward support."
            if wait_for_pullback
            else "Scale in across tranches; add on dips toward support."
        ),
        "tranches": plan,
    }


def _build_tax_fx_notes(
    *,
    symbol: str,
    stock_ctx: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Build tax and FX guidance for a Malaysia-resident, IE-domicile preference.

    - Flags Ireland-domiciled alternatives for US-listed ETFs.
    - Notes US dividend-withholding considerations.
    - Notes FX exposure when the security is not denominated in the base
      currency.
    """
    residency = (profile.get("residency") or {}).get("country")
    etf_prefs = profile.get("etf_preferences") or {}
    preferred_domicile = etf_prefs.get("domicile", "IE")
    base_currency = profile.get("base_currency") or "USD"

    notes: list[str] = []
    ie_alternative = ETF_ALTERNATIVES.get(symbol.upper())
    quote_type = (stock_ctx.get("quote_type") or "").upper()
    currency = stock_ctx.get("currency")
    dividend_yield = stock_ctx.get("dividend_yield")

    if ie_alternative:
        notes.append(
            f"{symbol} is US-domiciled. Prefer Ireland-domiciled {ie_alternative} "
            f"(15% US dividend withholding at fund level vs 30% for a Malaysia "
            f"resident holding US-domiciled funds) — matches your {preferred_domicile} "
            "domicile preference."
        )
    elif quote_type == "ETF" and preferred_domicile == "IE":
        notes.append(
            f"{symbol} is an ETF with no mapped Ireland-domiciled alternative; "
            "verify its domicile before buying to preserve withholding efficiency."
        )

    if dividend_yield and residency == "Malaysia" and not ie_alternative:
        notes.append(
            "Malaysia has no tax treaty reducing US dividend withholding; US-listed "
            "dividend payers incur 30% withholding. Favour IE-domiciled or "
            "low/no-dividend instruments."
        )

    if currency and currency != base_currency:
        notes.append(
            f"{symbol} trades in {currency} vs your {base_currency} base currency — "
            f"the position carries {currency}/{base_currency} FX exposure."
        )

    return {
        "residency": residency,
        "preferred_domicile": preferred_domicile,
        "base_currency": base_currency,
        "ireland_alternative": ie_alternative,
        "security_currency": currency,
        "notes": notes,
    }


def _build_portfolio_fit(
    *,
    stock_ctx: dict[str, Any],
    candidate_size: float | None,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Assess fit against the user's target allocation and external holdings.

    Lightweight, credential-free guidance: maps the candidate to an asset class
    and compares the candidate size against external holdings for rough sizing.
    Deep concentration/overlap checks against live IB positions are out of scope
    for this tool (they require account data) and are tracked as follow-up.
    """
    quote_type = (stock_ctx.get("quote_type") or "").upper()
    asset_class = "BOND" if quote_type in {"BOND"} else "STK"

    allocation_targets = profile.get("allocation_targets") or {}
    external = profile.get("external_holdings") or {}
    total_value = external.get("total_value")

    notes: list[str] = []
    target_pct: float | None = None
    if asset_class == "STK" and "stocks" in allocation_targets:
        target_pct = float(allocation_targets["stocks"])
    elif asset_class == "BOND" and "bonds" in allocation_targets:
        target_pct = float(allocation_targets["bonds"])
    if target_pct is not None:
        notes.append(
            f"Candidate maps to asset class {asset_class}; your target allocation "
            f"for this class is {target_pct:.0f}%."
        )

    size_pct: float | None = None
    if candidate_size is not None and total_value:
        try:
            size_pct = round(candidate_size / float(total_value) * 100, 2)
            notes.append(
                f"Candidate size {candidate_size:,.0f} is ~{size_pct:.2f}% of your "
                f"~{float(total_value):,.0f} external holdings."
            )
        except (TypeError, ValueError, ZeroDivisionError, ArithmeticError):
            size_pct = None

    notes.append(
        "Live concentration/overlap against existing IB positions requires account "
        "data and is not evaluated here."
    )

    return {
        "asset_class": asset_class,
        "target_allocation_pct": target_pct,
        "candidate_size_pct_of_external": size_pct,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------
def register_position_advisor_tools(mcp: FastMCP) -> None:
    """Register the position advisor tool."""

    @mcp.tool
    async def evaluate_position(
        symbol: str,
        candidate_size: float | None = None,
        account: int = 0,
        lookback_days: int = 7,
        ctx: Context | None = None,
    ) -> str:
        """
        Evaluate a candidate symbol and return a single integrated position decision.

        Synthesizes technicals, news sentiment, valuation, tax/FX considerations,
        a staged-entry plan and portfolio-fit guidance into one Buy/Hold/Avoid
        recommendation with rationale — tailored to the user's investment profile
        (Malaysia tax residency, Ireland-domiciled ETF preference, staged entry,
        no chasing bounces).

        Args:
            symbol: Candidate ticker symbol (e.g., "CSPX", "VOO", "AAPL").
            candidate_size: Optional intended position size (base-currency amount).
                When provided, the staged-entry plan and portfolio-fit notes
                include per-tranche sizing.
            account: Account index for profile/portfolio context (default: 0).
            lookback_days: News sentiment lookback window in days (default: 7).
            ctx: MCP context for logging.

        Returns:
            JSON string with:
            - ``recommendation``: "Buy" | "Hold" | "Avoid"
            - ``conviction``: composite score (~ -1.0 .. +1.0)
            - ``rationale``: list of reasons behind the decision
            - ``technical``, ``sentiment``, ``valuation``: component summaries
            - ``staged_entry``: tranche plan with price bands and sizing
            - ``tax_fx``: withholding / Ireland-domicile / FX notes
            - ``portfolio_fit``: target-allocation guidance

        Raises:
            ValidationError: If input validation fails.
            YahooFinanceError: If no price data is available.
            IBTimeoutError: If a data fetch times out.
        """
        try:
            symbol = validate_symbol(symbol)
            if candidate_size is not None and candidate_size <= 0:
                raise ValidationError("candidate_size must be positive", field="candidate_size")
            if lookback_days <= 0:
                raise ValidationError("lookback_days must be positive", field="lookback_days")

            if ctx:
                await ctx.info(f"Evaluating position for {symbol}")

            profile = _read_user_profile()

            # Gather components concurrently. Technicals are required; sentiment
            # and valuation are best-effort.
            tech_res, stock_res, sentiment_res = await asyncio.gather(
                _compute_technical_signals(symbol),
                _fetch_stock_context(symbol),
                _fetch_sentiment(symbol, lookback_days),
                return_exceptions=True,
            )

            if isinstance(tech_res, BaseException):
                if isinstance(tech_res, IBAnalyticsError):
                    raise tech_res
                raise YahooFinanceError(f"Could not evaluate technicals for {symbol}") from tech_res

            tech: dict[str, Any] = tech_res
            stock_ctx: dict[str, Any] = {} if isinstance(stock_res, BaseException) else stock_res
            sentiment: SentimentScore | None = (
                None if isinstance(sentiment_res, BaseException) else sentiment_res
            )

            current_price = tech.get("current_price") or stock_ctx.get("current_price")
            if not current_price:
                raise YahooFinanceError(f"No current price available for {symbol}")

            decision = _synthesize_recommendation(tech, sentiment)
            staged_entry = _build_staged_entry(
                current_price=float(current_price),
                support_resistance=tech.get("support_resistance") or {},
                candidate_size=candidate_size,
                recommendation=decision["recommendation"],
                chasing_risk=decision["chasing_risk"],
            )
            tax_fx = _build_tax_fx_notes(symbol=symbol, stock_ctx=stock_ctx, profile=profile)
            portfolio_fit = _build_portfolio_fit(
                stock_ctx=stock_ctx, candidate_size=candidate_size, profile=profile
            )

            signals = tech.get("signals") or {}
            support_resistance = tech.get("support_resistance") or {}
            indicators = tech.get("indicators") or {}
            trend = tech.get("trend") or {}
            result: dict[str, Any] = {
                "symbol": symbol,
                "as_of": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "candidate_size": candidate_size,
                "recommendation": decision["recommendation"],
                "conviction": decision["conviction"],
                "current_price": round(float(current_price), 2),
                "rationale": decision["rationale"],
                "technical": {
                    "score": decision["technical_score"],
                    "signal": signals.get("recommendation"),
                    "signals": signals.get("signals", []),
                    "current_level": support_resistance.get("current_level"),
                    "nearest_support": support_resistance.get("nearest_support"),
                    "nearest_resistance": support_resistance.get("nearest_resistance"),
                    "rsi": indicators.get("rsi"),
                    "trend": trend.get("trend_strength"),
                },
                "sentiment": (
                    {
                        "available": True,
                        "score": float(sentiment.score),
                        "confidence": float(sentiment.confidence),
                        "key_themes": sentiment.key_themes,
                        "risk_factors": sentiment.risk_factors,
                    }
                    if sentiment is not None
                    else {"available": False}
                ),
                "valuation": {
                    "name": stock_ctx.get("name"),
                    "quote_type": stock_ctx.get("quote_type"),
                    "sector": stock_ctx.get("sector"),
                    "currency": stock_ctx.get("currency"),
                    "trailing_pe": stock_ctx.get("trailing_pe"),
                    "forward_pe": stock_ctx.get("forward_pe"),
                    "dividend_yield": stock_ctx.get("dividend_yield"),
                    "beta": stock_ctx.get("beta"),
                    "fifty_two_week_high": stock_ctx.get("fifty_two_week_high"),
                    "fifty_two_week_low": stock_ctx.get("fifty_two_week_low"),
                },
                "staged_entry": staged_entry,
                "tax_fx": tax_fx,
                "portfolio_fit": portfolio_fit,
            }

            if ctx:
                await ctx.info(
                    f"{symbol}: {decision['recommendation']} "
                    f"(conviction {decision['conviction']:+.2f})"
                )

            return json.dumps(result, indent=2, default=str)

        except IBAnalyticsError:
            raise
        except Exception as e:
            if ctx:
                await ctx.error(f"Unexpected error in evaluate_position: {e!s}")
            raise ValidationError(f"evaluate_position failed for {symbol}") from e
