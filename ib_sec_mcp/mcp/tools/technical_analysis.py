"""Advanced Technical Analysis Tools

Provides comprehensive technical analysis with support/resistance, multi-timeframe analysis,
and pre-computed trading signals for optimal token efficiency.
"""

import asyncio
import json
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from fastmcp import Context, FastMCP

from ib_sec_mcp.mcp.exceptions import IBTimeoutError, ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.validators import validate_symbol

# Timeout constants (in seconds)
DEFAULT_TIMEOUT = 30


def register_technical_analysis_tools(mcp: FastMCP) -> None:
    """Register advanced technical analysis tools"""

    async def _perform_stock_analysis(
        symbol: str,
        timeframe: str = "1d",
        lookback_days: int = 252,
        ctx: Context | None = None,
    ) -> str:
        """
        Get comprehensive technical analysis with actionable signals

        Provides pre-computed analysis including support/resistance levels, trend analysis,
        volume profile, and entry/exit signals. Optimized for token efficiency by returning
        computed insights rather than raw data.

        Args:
            symbol: Stock ticker symbol (e.g., "PG", "AAPL")
            timeframe: Analysis timeframe - "1d" (daily), "1wk" (weekly), "1mo" (monthly)
            lookback_days: Historical data period for analysis (default: 252 trading days ≈ 1 year)
            ctx: MCP context for logging

        Returns:
            JSON string with comprehensive analysis:
            - Support/Resistance levels with strength scores
            - Trend analysis (short/medium/long term)
            - Volume analysis and profile
            - Technical indicators (RSI, MACD, ADX, ATR)
            - Pivot points (classic, Fibonacci, Camarilla)
            - Entry/exit signals with confidence scores
            - Risk/reward calculations

        Raises:
            ValidationError: If input validation fails
            YahooFinanceError: If Yahoo Finance API call fails
            IBTimeoutError: If operation times out
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)

            if timeframe not in ["1d", "1wk", "1mo"]:
                raise ValidationError(
                    f"Invalid timeframe: {timeframe}. Must be one of: 1d, 1wk, 1mo"
                )

            if ctx:
                await ctx.info(
                    f"Analyzing {symbol} with timeframe={timeframe}",
                    extra={
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "lookback_days": lookback_days,
                    },
                )

            # Fetch historical data
            import yfinance as yf

            async def fetch_data() -> Any:
                ticker = yf.Ticker(symbol)
                # Map timeframe to period
                period_map = {"1d": f"{lookback_days}d", "1wk": "2y", "1mo": "5y"}
                period = period_map.get(timeframe, f"{lookback_days}d")
                return await asyncio.to_thread(
                    lambda: ticker.history(period=period, interval=timeframe)
                )

            try:
                hist = await asyncio.wait_for(fetch_data(), timeout=DEFAULT_TIMEOUT)
            except TimeoutError as e:
                raise IBTimeoutError(
                    f"Yahoo Finance API timed out after {DEFAULT_TIMEOUT} seconds",
                    operation="fetch_stock_analysis",
                ) from e

            if hist.empty:
                raise YahooFinanceError(f"No data found for {symbol}")

            # Calculate all technical indicators
            close = hist["Close"]

            # 1. Support/Resistance Detection
            support_resistance = _find_support_resistance(hist)

            # 2. Trend Analysis
            trend_analysis = _analyze_trends(close)

            # 3. Technical Indicators
            indicators = _calculate_indicators(hist)

            # 4. Pivot Points
            pivot_points = _calculate_pivot_points(hist)

            # 5. Volume Analysis
            volume_analysis = _analyze_volume(hist)

            # 6. Generate Trading Signals
            signals = _generate_signals(
                close.iloc[-1],
                support_resistance,
                trend_analysis,
                indicators,
                volume_analysis,
            )

            # Build result
            result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "current_price": float(close.iloc[-1]),
                "price_change_pct": float(
                    ((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]) * 100
                ),
                "support_resistance": support_resistance,
                "trend_analysis": trend_analysis,
                "technical_indicators": indicators,
                "pivot_points": pivot_points,
                "volume_analysis": volume_analysis,
                "trading_signals": signals,
            }

            if ctx:
                await ctx.info(
                    f"Successfully analyzed {symbol}",
                    extra={
                        "symbol": symbol,
                        "signal_strength": signals["confidence"],
                        "recommendation": signals["recommendation"],
                    },
                )

            return json.dumps(result, indent=2, default=str)

        except (ValidationError, YahooFinanceError, IBTimeoutError):
            raise

        except Exception as e:
            if ctx:
                await ctx.error(
                    f"Unexpected error: {str(e)}",
                    extra={"error_type": type(e).__name__},
                )
            raise YahooFinanceError(f"Unexpected error while analyzing {symbol}: {str(e)}") from e

    @mcp.tool
    async def get_stock_analysis(
        symbol: str,
        timeframe: str = "1d",
        lookback_days: int = 252,
        ctx: Context | None = None,
    ) -> str:
        """
        Get comprehensive technical analysis with actionable signals

        Provides pre-computed analysis including support/resistance levels, trend analysis,
        volume profile, and entry/exit signals. Optimized for token efficiency by returning
        computed insights rather than raw data.

        Args:
            symbol: Stock ticker symbol (e.g., "PG", "AAPL")
            timeframe: Analysis timeframe - "1d" (daily), "1wk" (weekly), "1mo" (monthly)
            lookback_days: Historical data period for analysis (default: 252 trading days ≈ 1 year)
            ctx: MCP context for logging

        Returns:
            JSON string with comprehensive analysis:
            - Support/Resistance levels with strength scores
            - Trend analysis (short/medium/long term)
            - Volume analysis and profile
            - Technical indicators (RSI, MACD, ADX, ATR)
            - Pivot points (classic, Fibonacci, Camarilla)
            - Entry/exit signals with confidence scores
            - Risk/reward calculations

        Raises:
            ValidationError: If input validation fails
            YahooFinanceError: If Yahoo Finance API call fails
            IBTimeoutError: If operation times out
        """
        return await _perform_stock_analysis(symbol, timeframe, lookback_days, ctx)

    @mcp.tool
    async def get_multi_timeframe_analysis(
        symbol: str,
        ctx: Context | None = None,
    ) -> str:
        """
        Analyze stock across multiple timeframes for confluence

        Provides aligned analysis across daily, weekly, and monthly timeframes
        to identify high-probability trading opportunities.

        Args:
            symbol: Stock ticker symbol (e.g., "PG", "AAPL")
            ctx: MCP context for logging

        Returns:
            JSON string with multi-timeframe analysis including:
            - Individual timeframe analyses
            - Timeframe alignment/confluence
            - Higher timeframe context
            - Multi-timeframe signals

        Raises:
            ValidationError: If input validation fails
            YahooFinanceError: If Yahoo Finance API call fails
            IBTimeoutError: If operation times out
        """
        try:
            symbol = validate_symbol(symbol)

            if ctx:
                await ctx.info(f"Running multi-timeframe analysis for {symbol}")

            # Run analyses in parallel
            daily_task = _perform_stock_analysis(symbol, "1d", 252, ctx)
            weekly_task = _perform_stock_analysis(symbol, "1wk", 252, ctx)
            monthly_task = _perform_stock_analysis(symbol, "1mo", 252, ctx)

            daily_json, weekly_json, monthly_json = await asyncio.gather(
                daily_task, weekly_task, monthly_task
            )

            # Parse results
            daily = json.loads(daily_json)
            weekly = json.loads(weekly_json)
            monthly = json.loads(monthly_json)

            # Analyze confluence
            confluence = _analyze_timeframe_confluence(daily, weekly, monthly)

            result = {
                "symbol": symbol,
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "timeframes": {
                    "daily": daily,
                    "weekly": weekly,
                    "monthly": monthly,
                },
                "confluence_analysis": confluence,
            }

            if ctx:
                await ctx.info(
                    f"Multi-timeframe analysis complete for {symbol}",
                    extra={"confluence_score": confluence["score"]},
                )

            return json.dumps(result, indent=2, default=str)

        except (ValidationError, YahooFinanceError, IBTimeoutError):
            raise

        except Exception as e:
            if ctx:
                await ctx.error(f"Multi-timeframe analysis error: {str(e)}")
            raise YahooFinanceError(
                f"Multi-timeframe analysis failed for {symbol}: {str(e)}"
            ) from e


def _find_support_resistance(hist: pd.DataFrame, window: int = 20) -> dict[str, Any]:
    """Find support and resistance levels using local extrema"""
    close = hist["Close"]
    high = hist["High"]
    low = hist["Low"]

    # Find local maxima (resistance) and minima (support)
    resistance_levels = []
    support_levels = []

    for i in range(window, len(close) - window):
        # Check if local maximum
        if high.iloc[i] == high.iloc[i - window : i + window + 1].max():
            resistance_levels.append(float(high.iloc[i]))

        # Check if local minimum
        if low.iloc[i] == low.iloc[i - window : i + window + 1].min():
            support_levels.append(float(low.iloc[i]))

    # Cluster nearby levels (within 2% of each other)
    def cluster_levels(levels: list[float], tolerance: float = 0.02) -> list[float]:
        if not levels:
            return []

        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]

        for level in levels[1:]:
            if (level - current_cluster[-1]) / current_cluster[-1] <= tolerance:
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]

        if current_cluster:
            clusters.append(np.mean(current_cluster))

        return [round(float(c), 2) for c in clusters]

    resistance = cluster_levels(resistance_levels)
    support = cluster_levels(support_levels)

    # Get current price
    current_price = float(close.iloc[-1])

    # Filter to nearby levels (within 10%)
    resistance = [r for r in resistance if r > current_price and r <= current_price * 1.1]
    support = [s for s in support if s < current_price and s >= current_price * 0.9]

    # Sort and limit
    resistance = sorted(resistance)[:3]
    support = sorted(support, reverse=True)[:3]

    return {
        "resistance_levels": resistance,
        "support_levels": support,
        "nearest_resistance": resistance[0] if resistance else None,
        "nearest_support": support[0] if support else None,
        "current_level": (
            "near_resistance"
            if resistance and (resistance[0] - current_price) / current_price < 0.02
            else (
                "near_support"
                if support and (current_price - support[0]) / current_price < 0.02
                else "neutral"
            )
        ),
    }


def _analyze_trends(close: pd.Series) -> dict[str, Any]:
    """Analyze trends across multiple timeframes"""
    # Short-term: 20-day MA
    sma_20 = close.rolling(window=20).mean()
    short_trend = "uptrend" if close.iloc[-1] > sma_20.iloc[-1] else "downtrend"

    # Medium-term: 50-day MA
    sma_50 = close.rolling(window=50).mean()
    medium_trend = "uptrend" if close.iloc[-1] > sma_50.iloc[-1] else "downtrend"

    # Long-term: 200-day MA
    sma_200 = close.rolling(window=200).mean()
    long_trend = (
        "uptrend"
        if not pd.isna(sma_200.iloc[-1]) and close.iloc[-1] > sma_200.iloc[-1]
        else "downtrend"
        if not pd.isna(sma_200.iloc[-1])
        else "insufficient_data"
    )

    # Overall trend strength
    aligned = sum([short_trend == "uptrend", medium_trend == "uptrend", long_trend == "uptrend"])
    trend_strength = "strong" if aligned >= 2 else "weak"

    return {
        "short_term": short_trend,
        "medium_term": medium_trend,
        "long_term": long_trend,
        "trend_strength": trend_strength,
        "sma_20": round(float(sma_20.iloc[-1]), 2),
        "sma_50": (round(float(sma_50.iloc[-1]), 2) if not pd.isna(sma_50.iloc[-1]) else None),
        "sma_200": (round(float(sma_200.iloc[-1]), 2) if not pd.isna(sma_200.iloc[-1]) else None),
    }


def _calculate_indicators(hist: pd.DataFrame) -> dict[str, Any]:
    """Calculate key technical indicators"""
    close = hist["Close"]
    high = hist["High"]
    low = hist["Low"]

    # RSI (14-period)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_latest = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

    # MACD (12, 26, 9)
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd = ema_12 - ema_26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_histogram = macd - macd_signal

    # ADX (14-period) - Trend strength
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean()

    up_move = high - high.shift()
    down_move = low.shift() - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    plus_di = 100 * pd.Series(plus_dm).rolling(window=14).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).rolling(window=14).mean() / atr
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=14).mean()
    adx_latest = float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else None

    # ATR - Volatility
    atr_latest = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None
    atr_pct = (atr_latest / close.iloc[-1]) * 100 if atr_latest else None

    return {
        "rsi": {
            "value": round(rsi_latest, 2) if rsi_latest else None,
            "signal": (
                "overbought"
                if rsi_latest and rsi_latest > 70
                else ("oversold" if rsi_latest and rsi_latest < 30 else "neutral")
            ),
        },
        "macd": {
            "value": round(float(macd.iloc[-1]), 2),
            "signal": round(float(macd_signal.iloc[-1]), 2),
            "histogram": round(float(macd_histogram.iloc[-1]), 2),
            "trend": "bullish" if macd_histogram.iloc[-1] > 0 else "bearish",
        },
        "adx": {
            "value": round(adx_latest, 2) if adx_latest else None,
            "trend_strength": (
                "strong"
                if adx_latest and adx_latest > 25
                else ("weak" if adx_latest else "insufficient_data")
            ),
        },
        "atr": {
            "value": round(atr_latest, 2) if atr_latest else None,
            "percent": round(atr_pct, 2) if atr_pct else None,
            "volatility": (
                "high"
                if atr_pct and atr_pct > 3
                else ("low" if atr_pct and atr_pct < 1.5 else "normal")
            ),
        },
    }


def _calculate_pivot_points(hist: pd.DataFrame) -> dict[str, Any]:
    """Calculate pivot points for support/resistance"""
    # Use most recent completed period
    high = float(hist["High"].iloc[-2])
    low = float(hist["Low"].iloc[-2])
    close = float(hist["Close"].iloc[-2])

    # Classic Pivot Points
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    # Fibonacci Levels
    fib_pivot = pivot
    fib_r1 = pivot + 0.382 * (high - low)
    fib_r2 = pivot + 0.618 * (high - low)
    fib_s1 = pivot - 0.382 * (high - low)
    fib_s2 = pivot - 0.618 * (high - low)

    return {
        "classic": {
            "pivot": round(pivot, 2),
            "resistance_1": round(r1, 2),
            "resistance_2": round(r2, 2),
            "support_1": round(s1, 2),
            "support_2": round(s2, 2),
        },
        "fibonacci": {
            "pivot": round(fib_pivot, 2),
            "resistance_1": round(fib_r1, 2),
            "resistance_2": round(fib_r2, 2),
            "support_1": round(fib_s1, 2),
            "support_2": round(fib_s2, 2),
        },
    }


def _analyze_volume(hist: pd.DataFrame) -> dict[str, Any]:
    """Analyze volume patterns"""
    volume = hist["Volume"]
    close = hist["Close"]

    # Volume moving average
    vol_ma_20 = volume.rolling(window=20).mean()

    # OBV (On-Balance Volume)
    obv = pd.Series(index=close.index, dtype=float)
    obv.iloc[0] = volume.iloc[0]
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] + volume.iloc[i]
        elif close.iloc[i] < close.iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i - 1]

    # Volume trend
    vol_latest = float(volume.iloc[-1])
    vol_ma_latest = float(vol_ma_20.iloc[-1])
    vol_ratio = vol_latest / vol_ma_latest if vol_ma_latest else 1.0

    return {
        "current_volume": int(vol_latest),
        "average_volume_20d": int(vol_ma_latest),
        "volume_ratio": round(vol_ratio, 2),
        "volume_trend": ("high" if vol_ratio > 1.5 else ("low" if vol_ratio < 0.5 else "normal")),
        "obv_trend": (
            "bullish"
            if obv.iloc[-1] > obv.iloc[-20]
            else "bearish"
            if obv.iloc[-1] < obv.iloc[-20]
            else "neutral"
        ),
    }


def _generate_signals(
    current_price: float,
    support_resistance: dict[str, Any],
    trend_analysis: dict[str, Any],
    indicators: dict[str, Any],
    volume_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Generate trading signals based on technical analysis"""
    signals = []
    score = 0.0

    # Support/Resistance signals
    if support_resistance["current_level"] == "near_support":
        signals.append("Price near support - potential bounce")
        score += 0.15
    elif support_resistance["current_level"] == "near_resistance":
        signals.append("Price near resistance - potential rejection")
        score -= 0.15

    # Trend signals
    if trend_analysis["trend_strength"] == "strong":
        if trend_analysis["short_term"] == "uptrend":
            signals.append("Strong uptrend across timeframes")
            score += 0.20
        else:
            signals.append("Strong downtrend across timeframes")
            score -= 0.20

    # RSI signals
    rsi = indicators["rsi"]
    if rsi["signal"] == "oversold":
        signals.append(f"RSI oversold ({rsi['value']}) - potential reversal")
        score += 0.20
    elif rsi["signal"] == "overbought":
        signals.append(f"RSI overbought ({rsi['value']}) - potential pullback")
        score -= 0.15

    # MACD signals
    macd = indicators["macd"]
    if macd["trend"] == "bullish" and macd["histogram"] > 0:
        signals.append("MACD bullish crossover")
        score += 0.15
    elif macd["trend"] == "bearish" and macd["histogram"] < 0:
        signals.append("MACD bearish crossover")
        score -= 0.15

    # ADX signals
    adx = indicators["adx"]
    if adx["trend_strength"] == "strong":
        signals.append(f"Strong trend (ADX {adx['value']})")
        score += 0.10

    # Volume signals
    if volume_analysis["volume_trend"] == "high" and volume_analysis["obv_trend"] == "bullish":
        signals.append("High volume with bullish accumulation")
        score += 0.15
    elif volume_analysis["volume_trend"] == "high" and volume_analysis["obv_trend"] == "bearish":
        signals.append("High volume with bearish distribution")
        score -= 0.15

    # Calculate entry/exit zones
    nearest_support = support_resistance["nearest_support"]
    nearest_resistance = support_resistance["nearest_resistance"]

    entry_zone = None
    stop_loss = None
    take_profit = None

    if score > 0.5:  # Bullish
        if nearest_support:
            entry_zone = {
                "low": round(nearest_support * 0.99, 2),
                "high": round(nearest_support * 1.01, 2),
            }
            stop_loss = round(nearest_support * 0.97, 2)
            if nearest_resistance:
                take_profit = round(nearest_resistance * 0.99, 2)
    elif score < -0.3 and nearest_resistance:  # Bearish
        entry_zone = {
            "low": round(nearest_resistance * 0.99, 2),
            "high": round(nearest_resistance * 1.01, 2),
        }
        stop_loss = round(nearest_resistance * 1.03, 2)
        if nearest_support:
            take_profit = round(nearest_support * 1.01, 2)

    # Risk/reward ratio
    risk_reward = None
    if entry_zone and stop_loss and take_profit:
        entry_avg = (entry_zone["low"] + entry_zone["high"]) / 2
        risk = abs(entry_avg - stop_loss)
        reward = abs(take_profit - entry_avg)
        risk_reward = round(reward / risk, 2) if risk > 0 else None

    # Final recommendation
    confidence = abs(score)
    if score > 0.5:
        recommendation = "strong_buy"
    elif score > 0.3:
        recommendation = "buy"
    elif score > 0:
        recommendation = "weak_buy"
    elif score > -0.3:
        recommendation = "hold"
    elif score > -0.5:
        recommendation = "weak_sell"
    else:
        recommendation = "sell"

    return {
        "recommendation": recommendation,
        "confidence": round(confidence, 2),
        "score": round(score, 2),
        "signals": signals,
        "entry_zone": entry_zone,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_reward_ratio": risk_reward,
    }


def _analyze_timeframe_confluence(
    daily: dict[str, Any], weekly: dict[str, Any], monthly: dict[str, Any]
) -> dict[str, Any]:
    """Analyze confluence across multiple timeframes"""
    # Check trend alignment
    daily_trend = daily["trend_analysis"]["short_term"]
    weekly_trend = weekly["trend_analysis"]["medium_term"]
    monthly_trend = monthly["trend_analysis"]["long_term"]

    trends_aligned = daily_trend == weekly_trend == monthly_trend

    # Check indicator alignment
    daily_rsi = daily["technical_indicators"]["rsi"]["signal"]
    weekly_rsi = weekly["technical_indicators"]["rsi"]["signal"]

    indicators_aligned = daily_rsi == weekly_rsi

    # Calculate confluence score
    score = 0.0
    if trends_aligned:
        score += 0.5
    if indicators_aligned:
        score += 0.3

    # Check for divergences
    divergences = []
    if daily_trend != weekly_trend:
        divergences.append(f"Daily {daily_trend} vs Weekly {weekly_trend}")
    if weekly_trend != monthly_trend:
        divergences.append(f"Weekly {weekly_trend} vs Monthly {monthly_trend}")

    # Overall assessment
    if score > 0.7:
        assessment = "strong_confluence"
        recommendation = "High probability setup - all timeframes aligned"
    elif score > 0.4:
        assessment = "moderate_confluence"
        recommendation = "Decent setup - partial alignment"
    else:
        assessment = "low_confluence"
        recommendation = "Mixed signals - wait for better alignment"

    return {
        "score": round(score, 2),
        "assessment": assessment,
        "trends_aligned": trends_aligned,
        "indicators_aligned": indicators_aligned,
        "divergences": divergences,
        "recommendation": recommendation,
        "higher_timeframe_context": {
            "weekly_trend": weekly_trend,
            "monthly_trend": monthly_trend,
            "weekly_support": weekly["support_resistance"]["nearest_support"],
            "weekly_resistance": weekly["support_resistance"]["nearest_resistance"],
        },
    }


__all__ = ["register_technical_analysis_tools"]
