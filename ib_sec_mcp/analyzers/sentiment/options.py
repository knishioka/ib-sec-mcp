"""
Options sentiment analyzer

Derives market sentiment from options market data using the Put/Call ratio.
"""

from datetime import datetime
from decimal import Decimal

import yfinance as yf

from ib_sec_mcp.analyzers.sentiment.base import BaseSentimentAnalyzer, SentimentScore


class OptionsSentimentAnalyzer(BaseSentimentAnalyzer):
    """
    Analyze market sentiment from options market data

    Derives sentiment from the Put/Call open-interest ratio
    (bearish when high, bullish when low).

    Sentiment Interpretation:
    - Put/Call < 0.7: Bullish (more calls than puts)
    - Put/Call 0.7-1.0: Slightly Bullish
    - Put/Call 1.0-1.3: Neutral
    - Put/Call > 1.3: Bearish (more puts than calls)
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

            # Calculate sentiment components
            scores = []
            themes = []
            risk_factors = []
            data_points = 0

            # Put/Call Ratio Sentiment
            pc_ratio = Decimal(str(put_call_ratio))
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

            # Average all scores
            avg_score = sum(scores) / len(scores)

            # Confidence based on data point count
            # More data points = higher confidence
            confidence = min(Decimal(str(data_points)) / Decimal("3"), Decimal("1.0"))

            reasoning = (
                f"Analyzed {data_points} options indicators for {symbol}. "
                f"Put/Call ratio: {put_call_ratio}"
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
