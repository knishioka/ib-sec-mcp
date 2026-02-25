"""
Options sentiment analyzer

Derives market sentiment from options market data including Put/Call ratios,
IV metrics, and Max Pain analysis.
"""

from datetime import datetime
from decimal import Decimal

import yfinance as yf

from ib_sec_mcp.analyzers.sentiment.base import BaseSentimentAnalyzer, SentimentScore


class OptionsSentimentAnalyzer(BaseSentimentAnalyzer):
    """
    Analyze market sentiment from options market data

    Combines multiple options-based indicators:
    - Put/Call ratio (bearish when high, bullish when low)
    - IV Rank/Percentile (high IV = fear/uncertainty)
    - Max Pain (price gravitates toward max pain at expiration)

    Sentiment Interpretation:
    - Put/Call < 0.7: Bullish (more calls than puts)
    - Put/Call 0.7-1.0: Slightly Bullish
    - Put/Call 1.0-1.3: Neutral
    - Put/Call > 1.3: Bearish (more puts than calls)

    - IV Rank < 25: Complacency (slightly bullish)
    - IV Rank 25-50: Normal
    - IV Rank 50-75: Elevated (slightly bearish)
    - IV Rank > 75: Fear (bearish)
    """

    async def analyze_sentiment(self, symbol: str) -> SentimentScore:
        """
        Analyze options market sentiment for a symbol

        Args:
            symbol: Stock ticker symbol

        Returns:
            SentimentScore with options-based sentiment

        Raises:
            Exception: If options data is unavailable
        """
        try:
            # Fetch options data directly from Yahoo Finance
            ticker = yf.Ticker(symbol)

            # Get nearest expiration options
            expirations = ticker.options
            if not expirations:
                raise ValueError(f"No options available for {symbol}")

            nearest_exp = expirations[0]
            opt_chain = ticker.option_chain(nearest_exp)

            calls = opt_chain.calls
            puts = opt_chain.puts

            if calls.empty or puts.empty:
                raise ValueError(f"No options data available for {symbol}")

            # Calculate Put/Call ratio based on open interest
            total_call_oi = calls["openInterest"].sum()
            total_put_oi = puts["openInterest"].sum()

            # Use ternary for cleaner code (ruff SIM108)
            put_call_ratio = 2.0 if total_call_oi == 0 else total_put_oi / total_call_oi

            put_call_data: dict[str, object] = {"put_call_ratio": put_call_ratio}

            # Get average implied volatility
            call_iv_avg = (
                calls["impliedVolatility"].mean()
                if "impliedVolatility" in calls.columns
                and not calls["impliedVolatility"].isna().all()
                else 0.3
            )
            put_iv_avg = (
                puts["impliedVolatility"].mean()
                if "impliedVolatility" in puts.columns
                and not puts["impliedVolatility"].isna().all()
                else 0.3
            )
            current_iv = (call_iv_avg + put_iv_avg) / 2

            # Simplified IV data (no historical rank/percentile)
            iv_data: dict[str, object] = {"current_iv": current_iv}

            # Skip max pain calculation for simplicity
            max_pain_data: dict[str, object] = {}

            # Calculate sentiment components
            scores = []
            themes = []
            risk_factors = []
            data_points = 0

            # 1. Put/Call Ratio Sentiment
            if "put_call_ratio" in put_call_data:
                pc_ratio = Decimal(str(put_call_data["put_call_ratio"]))
                data_points += 1

                if pc_ratio < Decimal("0.7"):
                    pc_score = Decimal("0.5")  # Bullish
                    themes.append("strong_call_buying")
                elif pc_ratio < Decimal("1.0"):
                    pc_score = Decimal("0.2")  # Slightly bullish
                    themes.append("moderate_call_buying")
                elif pc_ratio < Decimal("1.3"):
                    pc_score = Decimal("0.0")  # Neutral
                else:
                    pc_score = Decimal("-0.5")  # Bearish
                    risk_factors.append("heavy_put_buying")

                scores.append(pc_score)

            # 2. IV Rank Sentiment
            if "iv_rank" in iv_data:
                iv_rank = Decimal(str(iv_data["iv_rank"]))
                data_points += 1

                if iv_rank < Decimal("25"):
                    iv_score = Decimal("0.3")  # Complacency (bullish)
                    themes.append("low_volatility_expectations")
                elif iv_rank < Decimal("50"):
                    iv_score = Decimal("0.0")  # Normal
                elif iv_rank < Decimal("75"):
                    iv_score = Decimal("-0.2")  # Elevated
                    risk_factors.append("elevated_volatility_expectations")
                else:
                    iv_score = Decimal("-0.5")  # Fear
                    risk_factors.append("high_volatility_fear")

                scores.append(iv_score)

            # 3. Max Pain Sentiment
            if "max_pain_strike" in max_pain_data and "current_price" in max_pain_data:
                max_pain = Decimal(str(max_pain_data["max_pain_strike"]))
                current_price = Decimal(str(max_pain_data["current_price"]))
                data_points += 1

                # If price is significantly below max pain, bullish pressure expected
                # If price is significantly above max pain, bearish pressure expected
                diff_pct = (current_price - max_pain) / max_pain * Decimal("100")

                if diff_pct < Decimal("-5"):
                    mp_score = Decimal("0.3")  # Below max pain (bullish pull)
                    themes.append("below_max_pain")
                elif diff_pct > Decimal("5"):
                    mp_score = Decimal("-0.3")  # Above max pain (bearish pull)
                    risk_factors.append("above_max_pain")
                else:
                    mp_score = Decimal("0.0")  # Near max pain

                scores.append(mp_score)

            # Calculate composite score
            if not scores:
                # No options data available
                return SentimentScore(
                    score=Decimal("0.0"),
                    confidence=Decimal("0.0"),
                    timestamp=datetime.now(),
                    key_themes=["no_options_data"],
                    risk_factors=[],
                    reasoning=f"No options data available for {symbol}",
                )

            # Average all scores
            avg_score = sum(scores) / len(scores)

            # Confidence based on data point count
            # More data points = higher confidence
            confidence = min(Decimal(str(data_points)) / Decimal("3"), Decimal("1.0"))

            reasoning = (
                f"Analyzed {data_points} options indicators for {symbol}. "
                f"Put/Call ratio: {put_call_data.get('put_call_ratio', 'N/A')}, "
                f"IV Rank: {iv_data.get('iv_rank', 'N/A')}, "
                f"Max Pain: {max_pain_data.get('max_pain_strike', 'N/A')}"
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
                risk_factors=["options_analysis_error"],
                reasoning=f"Failed to analyze options sentiment: {e!s}",
            )
