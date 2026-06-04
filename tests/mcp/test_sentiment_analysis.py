"""Tests for the ``analyze_market_sentiment`` MCP tool.

The underlying analyzers hit the network (news/options/technical), so they are
patched to return deterministic ``SentimentScore`` objects. Tests focus on the
tool's own logic: source routing, interpretation thresholds, validation, timeout
handling, and error masking (no internal error detail leaked to the caller).
"""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastmcp import FastMCP

import ib_sec_mcp.mcp.tools.sentiment_analysis as sentiment_module
from ib_sec_mcp.analyzers.sentiment.base import SentimentScore
from ib_sec_mcp.mcp.exceptions import IBTimeoutError, ValidationError
from ib_sec_mcp.mcp.tools.sentiment_analysis import register_sentiment_analysis_tools
from tests.mcp._fastmcp_helpers import call_tool_fn


def make_score(score: str, confidence: str = "0.8") -> SentimentScore:
    return SentimentScore(
        score=Decimal(score),
        confidence=Decimal(confidence),
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        key_themes=["theme_a"],
        risk_factors=["risk_a"],
        reasoning="test reasoning",
    )


@pytest.fixture()
def test_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_sentiment_analysis_tools(mcp)
    return mcp


def _patch_analyzer(
    monkeypatch: pytest.MonkeyPatch, class_name: str, score: SentimentScore
) -> None:
    """Patch ``<Analyzer>.analyze_sentiment`` to return a fixed score."""
    cls = getattr(sentiment_module, class_name)
    monkeypatch.setattr(cls, "analyze_sentiment", AsyncMock(return_value=score))


class TestSourceRouting:
    async def test_news_source_returns_expected_payload(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_analyzer(monkeypatch, "NewsSentimentAnalyzer", make_score("0.3"))
        result = await call_tool_fn(
            test_mcp, "analyze_market_sentiment", symbol="AAPL", sources="news", ctx=None
        )
        data = json.loads(result)
        assert data["symbol"] == "AAPL"
        assert data["sources_analyzed"] == ["news"]
        assert data["sentiment_score"] == pytest.approx(0.3)
        assert data["key_themes"] == ["theme_a"]

    async def test_technical_source(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_analyzer(monkeypatch, "TechnicalSentimentAnalyzer", make_score("0.0"))
        result = await call_tool_fn(
            test_mcp, "analyze_market_sentiment", symbol="TSLA", sources="technical", ctx=None
        )
        data = json.loads(result)
        assert data["sources_analyzed"] == ["technical"]

    async def test_composite_source_uses_composite_analyzer(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_analyzer(monkeypatch, "CompositeSentimentAnalyzer", make_score("0.6"))
        result = await call_tool_fn(
            test_mcp, "analyze_market_sentiment", symbol="SPY", sources="composite", ctx=None
        )
        data = json.loads(result)
        assert data["interpretation"] == "Strong Bullish"

    async def test_multiple_sources_routes_to_composite(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # "news,options" (len > 1) must use the composite analyzer.
        _patch_analyzer(monkeypatch, "CompositeSentimentAnalyzer", make_score("0.1"))
        result = await call_tool_fn(
            test_mcp, "analyze_market_sentiment", symbol="AAPL", sources="news,options", ctx=None
        )
        data = json.loads(result)
        assert data["sources_analyzed"] == ["news", "options"]


class TestInterpretation:
    @pytest.mark.parametrize(
        "score,expected",
        [
            ("0.6", "Strong Bullish"),
            ("0.3", "Moderately Bullish"),
            ("0.0", "Neutral"),
            ("-0.3", "Moderately Bearish"),
            ("-0.6", "Strong Bearish"),
        ],
    )
    async def test_interpretation_thresholds(
        self,
        test_mcp: FastMCP,
        monkeypatch: pytest.MonkeyPatch,
        score: str,
        expected: str,
    ) -> None:
        _patch_analyzer(monkeypatch, "NewsSentimentAnalyzer", make_score(score))
        result = await call_tool_fn(
            test_mcp, "analyze_market_sentiment", symbol="AAPL", sources="news", ctx=None
        )
        assert json.loads(result)["interpretation"] == expected


class TestValidation:
    async def test_invalid_symbol_raises_validation_error(self, test_mcp: FastMCP) -> None:
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp, "analyze_market_sentiment", symbol="!!!", sources="news", ctx=None
            )

    @pytest.mark.parametrize("lookback", [0, 366])
    async def test_lookback_out_of_range_raises(self, test_mcp: FastMCP, lookback: int) -> None:
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp,
                "analyze_market_sentiment",
                symbol="AAPL",
                lookback_days=lookback,
                sources="news",
                ctx=None,
            )


class TestErrorHandling:
    async def test_timeout_raises_ib_timeout_error(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cls = sentiment_module.NewsSentimentAnalyzer
        monkeypatch.setattr(cls, "analyze_sentiment", AsyncMock(side_effect=TimeoutError("slow")))
        with pytest.raises(IBTimeoutError):
            await call_tool_fn(
                test_mcp, "analyze_market_sentiment", symbol="AAPL", sources="news", ctx=None
            )

    async def test_internal_error_is_masked(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        secret = "SECRET_DB_CONNECTION_STRING"
        cls = sentiment_module.NewsSentimentAnalyzer
        monkeypatch.setattr(cls, "analyze_sentiment", AsyncMock(side_effect=RuntimeError(secret)))
        with pytest.raises(ValidationError) as exc_info:
            await call_tool_fn(
                test_mcp, "analyze_market_sentiment", symbol="AAPL", sources="news", ctx=None
            )
        # Internal error detail must not leak into the surfaced error message.
        assert secret not in str(exc_info.value)
