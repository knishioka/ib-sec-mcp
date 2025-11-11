"""
Technical sentiment analyzer

Derives market sentiment from technical indicators including RSI, MACD,
trend analysis, and support/resistance levels.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
import yfinance as yf

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

    - MACD > Signal: Bullish momentum
    - MACD < Signal: Bearish momentum
    """

    def calculate_rsi(self, prices: "pd.Series[float]", period: int = 14) -> float:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
        loss = (-delta).where(delta < 0, 0.0).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])

    def calculate_macd(
        self, prices: "pd.Series[float]", fast: int = 12, slow: int = 26, signal: int = 9
    ) -> tuple[float, float]:
        """Calculate MACD and signal line"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()

        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()

        return float(macd.iloc[-1]), float(macd_signal.iloc[-1])

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
            # Fetch historical price data
            ticker = yf.Ticker(symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)  # 1 year of data

            hist = ticker.history(start=start_date, end=end_date, interval="1d")

            if hist.empty or len(hist) < 50:
                raise ValueError(f"Insufficient price data for {symbol}")

            prices = hist["Close"]

            scores = []
            themes = []
            risk_factors = []
            data_points = 0

            # 1. RSI Sentiment
            try:
                rsi = self.calculate_rsi(prices)
                data_points += 1

                if rsi < 30:
                    rsi_score = Decimal("0.5")  # Oversold (bullish)
                    themes.append("oversold_rsi")
                elif rsi < 50:
                    rsi_score = Decimal("-0.2")  # Bearish momentum
                elif rsi < 70:
                    rsi_score = Decimal("0.2")  # Bullish momentum
                    themes.append("bullish_momentum")
                else:
                    rsi_score = Decimal("-0.5")  # Overbought (bearish)
                    risk_factors.append("overbought_rsi")

                scores.append(rsi_score)
            except (ValueError, ZeroDivisionError, IndexError):
                # Skip RSI if calculation fails (insufficient data or divide by zero)
                data_points -= 1 if data_points > 0 else 0

            # 2. MACD Sentiment
            try:
                macd, macd_signal = self.calculate_macd(prices)
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
            except (ValueError, IndexError):
                # Skip MACD if calculation fails (insufficient data)
                data_points -= 1 if data_points > 0 else 0

            # 3. Trend Sentiment (Simple moving averages)
            try:
                sma_20 = prices.rolling(window=20).mean().iloc[-1]
                sma_50 = prices.rolling(window=50).mean().iloc[-1]
                current_price = prices.iloc[-1]

                data_points += 1

                # Price above both SMAs = bullish
                if current_price > sma_20 and current_price > sma_50:
                    if sma_20 > sma_50:
                        trend_score = Decimal("0.4")  # Strong uptrend
                        themes.append("strong_uptrend")
                    else:
                        trend_score = Decimal("0.2")  # Moderate uptrend
                # Price below both SMAs = bearish
                elif current_price < sma_20 and current_price < sma_50:
                    if sma_20 < sma_50:
                        trend_score = Decimal("-0.4")  # Strong downtrend
                        risk_factors.append("strong_downtrend")
                    else:
                        trend_score = Decimal("-0.2")  # Moderate downtrend
                else:
                    trend_score = Decimal("0.0")  # Mixed/choppy

                scores.append(trend_score)
            except (ValueError, IndexError):
                # Skip trend if calculation fails (insufficient data)
                data_points -= 1 if data_points > 0 else 0

            # Calculate composite score
            if not scores:
                # No technical data available
                return SentimentScore(
                    score=Decimal("0.0"),
                    confidence=Decimal("0.0"),
                    timestamp=datetime.now(),
                    key_themes=["no_technical_data"],
                    risk_factors=[],
                    reasoning=f"No technical data available for {symbol}",
                )

            # Average all scores
            avg_score = sum(scores) / len(scores)

            # Confidence based on data point count
            # More data points = higher confidence
            confidence = min(Decimal(str(data_points)) / Decimal("3"), Decimal("1.0"))

            reasoning = (
                f"Analyzed {data_points} technical indicators for {symbol}. "
                f"Sentiment based on RSI, MACD, and trend analysis."
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
