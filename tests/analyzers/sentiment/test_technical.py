"""Tests for ``TechnicalSentimentAnalyzer``.

The RSI/MACD helpers are pure and tested directly on constructed price series.
``analyze_sentiment`` fetches data via yfinance, which is patched with a fake
ticker returning deterministic DataFrames to exercise the trend branches and the
graceful-degradation paths (insufficient / empty data -> neutral score).
"""

from decimal import Decimal

import pandas as pd
import pytest

from ib_sec_mcp.analyzers.sentiment.base import SentimentScore
from ib_sec_mcp.analyzers.sentiment.technical import TechnicalSentimentAnalyzer


@pytest.fixture()
def patch_ticker(monkeypatch: pytest.MonkeyPatch):
    def _apply(df: pd.DataFrame) -> None:
        # Define the fake ticker inside the closure so the history DataFrame is
        # captured per-call rather than stored on a shared class attribute. This
        # keeps tests isolated even under parallel execution (e.g. pytest-xdist).
        class FakeTicker:
            """Minimal yfinance.Ticker stand-in returning a fixed history DataFrame."""

            def __init__(self, symbol: str) -> None:
                self.symbol = symbol

            def history(self, *args: object, **kwargs: object) -> pd.DataFrame:
                return df

        monkeypatch.setattr("ib_sec_mcp.analyzers.sentiment.technical.yf.Ticker", FakeTicker)

    return _apply


def close_df(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"Close": values})


class TestRsiMacdHelpers:
    def test_rsi_high_for_rising_prices(self) -> None:
        analyzer = TechnicalSentimentAnalyzer()
        prices = pd.Series([float(p) for p in range(1, 60)])  # strictly increasing
        rsi = analyzer.calculate_rsi(prices)
        assert rsi == pytest.approx(100.0)

    def test_rsi_low_for_falling_prices(self) -> None:
        analyzer = TechnicalSentimentAnalyzer()
        prices = pd.Series([float(p) for p in range(60, 1, -1)])  # strictly decreasing
        rsi = analyzer.calculate_rsi(prices)
        assert rsi == pytest.approx(0.0)

    def test_macd_returns_two_floats(self) -> None:
        analyzer = TechnicalSentimentAnalyzer()
        prices = pd.Series([float(p) for p in range(1, 60)])
        macd, signal = analyzer.calculate_macd(prices)
        assert isinstance(macd, float)
        assert isinstance(signal, float)


class TestAnalyzeSentiment:
    async def test_uptrend_flags_strong_uptrend(self, patch_ticker) -> None:
        patch_ticker(close_df([100.0 + i for i in range(60)]))
        analyzer = TechnicalSentimentAnalyzer()
        result = await analyzer.analyze_sentiment("AAPL")

        assert isinstance(result, SentimentScore)
        assert "strong_uptrend" in result.key_themes
        assert Decimal("-1.0") <= result.score <= Decimal("1.0")
        assert result.confidence == Decimal("1.0")  # 3 indicators computed

    async def test_downtrend_flags_strong_downtrend(self, patch_ticker) -> None:
        patch_ticker(close_df([200.0 - i for i in range(60)]))
        analyzer = TechnicalSentimentAnalyzer()
        result = await analyzer.analyze_sentiment("AAPL")

        assert "strong_downtrend" in result.risk_factors
        assert result.score < Decimal("0")

    async def test_insufficient_data_returns_neutral(self, patch_ticker) -> None:
        patch_ticker(close_df([100.0 + i for i in range(10)]))  # < 50 rows
        analyzer = TechnicalSentimentAnalyzer()
        result = await analyzer.analyze_sentiment("AAPL")

        assert result.score == Decimal("0.0")
        assert result.confidence == Decimal("0.0")
        assert "technical_analysis_error" in result.risk_factors

    async def test_empty_history_returns_neutral(self, patch_ticker) -> None:
        patch_ticker(pd.DataFrame({"Close": []}))
        analyzer = TechnicalSentimentAnalyzer()
        result = await analyzer.analyze_sentiment("AAPL")

        assert result.score == Decimal("0.0")
        assert result.confidence == Decimal("0.0")

    async def test_score_and_confidence_are_decimal(self, patch_ticker) -> None:
        patch_ticker(close_df([100.0 + (i % 5) for i in range(60)]))
        analyzer = TechnicalSentimentAnalyzer()
        result = await analyzer.analyze_sentiment("AAPL")

        assert isinstance(result.score, Decimal)
        assert isinstance(result.confidence, Decimal)
