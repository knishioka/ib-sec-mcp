"""
Technical sentiment analyzer

Derives market sentiment from technical indicators including RSI, MACD,
trend analysis, and support/resistance levels.
"""

import json
from datetime import datetime
from decimal import Decimal

from ib_sec_mcp.analyzers.sentiment.base import BaseSentimentAnalyzer, SentimentScore


class TechnicalSentimentAnalyzer(BaseSentimentAnalyzer):
    """
    Analyze market sentiment from technical indicators

    Combines multiple technical analysis signals:
    - RSI (Relative Strength Index): Overbought/oversold conditions
    - MACD: Trend momentum and reversals
    - Trend: Short/medium/long term trend direction
    - Support/Resistance: Price action near key levels

    Sentiment Interpretation:
    - RSI < 30: Oversold (bullish reversal signal)
    - RSI 30-50: Bearish momentum
    - RSI 50-70: Bullish momentum
    - RSI > 70: Overbought (bearish reversal signal)

    - MACD: Bullish cross = positive, Bearish cross = negative
    - Trend: Uptrend = positive, Downtrend = negative
    - Near Support: Bullish, Near Resistance: Bearish
    """

    async def analyze_sentiment(self, symbol: str) -> SentimentScore:
        """
        Analyze technical sentiment for a symbol

        Args:
            symbol: Stock ticker symbol

        Returns:
            SentimentScore with technical-based sentiment

        Raises:
            Exception: If technical data is unavailable
        """
        try:
            # Import MCP tools dynamically to avoid circular imports
            from ib_sec_mcp.mcp.tools.technical_analysis import (  # type: ignore[attr-defined]
                get_stock_analysis,
            )

            # Fetch technical analysis
            result = await get_stock_analysis(symbol=symbol, timeframe="1d", lookback_days=252)
            data = json.loads(result)

            scores = []
            themes = []
            risk_factors = []
            data_points = 0

            # 1. RSI Sentiment
            indicators = data.get("technical_indicators", {})
            if "rsi" in indicators:
                rsi = Decimal(str(indicators["rsi"]))
                data_points += 1

                if rsi < Decimal("30"):
                    rsi_score = Decimal("0.5")  # Oversold (bullish)
                    themes.append("oversold_rsi")
                elif rsi < Decimal("50"):
                    rsi_score = Decimal("-0.2")  # Bearish momentum
                elif rsi < Decimal("70"):
                    rsi_score = Decimal("0.2")  # Bullish momentum
                    themes.append("bullish_momentum")
                else:
                    rsi_score = Decimal("-0.5")  # Overbought (bearish)
                    risk_factors.append("overbought_rsi")

                scores.append(rsi_score)

            # 2. MACD Sentiment
            if "macd" in indicators and "macd_signal" in indicators:
                macd = Decimal(str(indicators["macd"]))
                macd_signal = Decimal(str(indicators["macd_signal"]))
                data_points += 1

                # MACD above signal = bullish
                if macd > macd_signal:
                    macd_score = Decimal("0.3")
                    themes.append("bullish_macd_cross")
                elif macd < macd_signal:
                    macd_score = Decimal("-0.3")
                    risk_factors.append("bearish_macd_cross")
                else:
                    macd_score = Decimal("0.0")

                scores.append(macd_score)

            # 3. Trend Sentiment
            trend_analysis = data.get("trend_analysis", {})
            if "short_term" in trend_analysis:
                data_points += 1
                short_trend = trend_analysis["short_term"].lower()
                medium_trend = trend_analysis.get("medium_term", "").lower()
                long_trend = trend_analysis.get("long_term", "").lower()

                trend_scores = []
                if "up" in short_trend:
                    trend_scores.append(Decimal("0.3"))
                    themes.append("short_term_uptrend")
                elif "down" in short_trend:
                    trend_scores.append(Decimal("-0.3"))
                    risk_factors.append("short_term_downtrend")

                if "up" in medium_trend:
                    trend_scores.append(Decimal("0.2"))
                elif "down" in medium_trend:
                    trend_scores.append(Decimal("-0.2"))

                if "up" in long_trend:
                    trend_scores.append(Decimal("0.1"))
                elif "down" in long_trend:
                    trend_scores.append(Decimal("-0.1"))

                if trend_scores:
                    trend_score = Decimal(sum(trend_scores) / len(trend_scores))
                    scores.append(trend_score)

            # 4. Support/Resistance Sentiment
            support_resistance = data.get("support_resistance", {})
            current_price = Decimal(str(data.get("current_price", 0)))
            if current_price > 0:
                supports = support_resistance.get("support_levels", [])
                resistances = support_resistance.get("resistance_levels", [])

                if supports and resistances:
                    data_points += 1
                    nearest_support = Decimal(str(supports[0]["price"]))
                    nearest_resistance = Decimal(str(resistances[0]["price"]))

                    # Calculate distance to support/resistance
                    support_dist = abs(current_price - nearest_support) / current_price
                    resistance_dist = abs(nearest_resistance - current_price) / current_price

                    # Near support (within 2%) = bullish
                    # Near resistance (within 2%) = bearish
                    if support_dist < Decimal("0.02"):
                        sr_score = Decimal("0.3")
                        themes.append("near_support")
                    elif resistance_dist < Decimal("0.02"):
                        sr_score = Decimal("-0.3")
                        risk_factors.append("near_resistance")
                    else:
                        # Between levels - neutral
                        sr_score = Decimal("0.0")

                    scores.append(sr_score)

            # Calculate composite score
            if not scores:
                # No technical data available
                return SentimentScore(
                    score=Decimal("0.0"),
                    confidence=Decimal("0.0"),
                    timestamp=datetime.now(),
                    key_themes=["no_technical_data"],
                    risk_factors=[],
                    reasoning=f"No technical analysis data available for {symbol}",
                )

            # Average all scores
            avg_score = sum(scores) / len(scores)

            # Confidence based on data point count and agreement
            # More data points = higher confidence
            base_confidence = min(Decimal(str(data_points)) / Decimal("4"), Decimal("1.0"))

            # Check agreement between indicators
            if len(scores) > 1:
                # All scores same sign = high agreement
                all_positive = all(s > 0 for s in scores)
                all_negative = all(s < 0 for s in scores)

                agreement_bonus = Decimal("0.2") if all_positive or all_negative else Decimal("0.0")

                confidence = min(base_confidence + agreement_bonus, Decimal("1.0"))
            else:
                confidence = base_confidence

            reasoning = (
                f"Analyzed {data_points} technical indicators for {symbol}. "
                f"RSI: {indicators.get('rsi', 'N/A')}, "
                f"MACD: {indicators.get('macd', 'N/A')}, "
                f"Trend: {trend_analysis.get('short_term', 'N/A')}"
            )

            return SentimentScore(
                score=avg_score,
                confidence=confidence,
                timestamp=datetime.now(),
                key_themes=themes,
                risk_factors=risk_factors,
                reasoning=reasoning,
            )

        except Exception as e:
            # Return neutral sentiment on error
            return SentimentScore(
                score=Decimal("0.0"),
                confidence=Decimal("0.0"),
                timestamp=datetime.now(),
                key_themes=[],
                risk_factors=["technical_analysis_error"],
                reasoning=f"Failed to analyze technical sentiment: {str(e)}",
            )
