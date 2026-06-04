"""Tests for the portfolio analytics MCP tools.

``calculate_portfolio_metrics`` and ``analyze_portfolio_correlation`` both fetch
price history from yfinance, which is patched with a fake ticker returning a
varied deterministic series. Validation/early-exit branches are tested without
any network access.
"""

import json
from pathlib import Path

import pandas as pd
import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.exceptions import FileOperationError, ValidationError
from ib_sec_mcp.mcp.tools.portfolio_analytics import register_portfolio_analytics_tools
from tests.mcp._fastmcp_helpers import call_tool_fn

# Multi-position XML (filename carries the date range parsed by the tool).
XML_TWO_POSITIONS = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="10000" endingCash="10000" endingSettledCash="10000" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="CSPX" description="ISHARES CORE S&amp;P 500"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="IE00B5BMR087" position="10" markPrice="735.00"
          positionValue="7350" costBasisMoney="6000" fifoPnlUnrealized="1350"
          reportDate="20250131" multiplier="1" />
        <OpenPosition symbol="IDTL" description="ISHARES USD TRES 20PLUS YR"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="IE00BSKRJZ44" position="100" markPrice="50.00"
          positionValue="5000" costBasisMoney="4800" fifoPnlUnrealized="200"
          reportDate="20250131" multiplier="1" />
      </OpenPositions>
      <Trades />
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

XML_ONE_POSITION = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="10000" endingCash="10000" endingSettledCash="10000" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="CSPX" description="ISHARES CORE S&amp;P 500"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="IE00B5BMR087" position="10" markPrice="735.00"
          positionValue="7350" costBasisMoney="6000" fifoPnlUnrealized="1350"
          reportDate="20250131" multiplier="1" />
      </OpenPositions>
      <Trades />
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

XML_NO_POSITIONS = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="10000" endingCash="10000" endingSettledCash="10000" />
      </CashReport>
      <OpenPositions />
      <Trades />
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""


def _varied_prices(n: int = 90) -> list[float]:
    """Deterministic price series with both up and down moves (non-zero variance)."""
    prices = []
    value = 100.0
    for i in range(n):
        value += 1.5 if i % 3 else -1.0
        prices.append(value)
    return prices


class FakeTicker:
    """yfinance.Ticker stand-in returning a fixed varied Close history."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, *args: object, **kwargs: object) -> pd.DataFrame:
        return pd.DataFrame({"Close": _varied_prices()})


@pytest.fixture()
def test_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_portfolio_analytics_tools(mcp)
    return mcp


@pytest.fixture()
def patch_yfinance(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("yfinance.Ticker", FakeTicker)


def write_xml(
    tmp_path: Path, content: str, name: str = "U1234567_2025-01-01_2025-01-31.xml"
) -> str:
    path = tmp_path / name
    path.write_text(content)
    return str(path)


class TestCalculatePortfolioMetricsValidation:
    async def test_missing_file_raises_validation_error(self, test_mcp: FastMCP) -> None:
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp,
                "calculate_portfolio_metrics",
                file_path="/nonexistent/portfolio.xml",
                ctx=None,
            )

    async def test_invalid_period_raises(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        path = write_xml(tmp_path, XML_TWO_POSITIONS)
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp,
                "calculate_portfolio_metrics",
                file_path=path,
                period="bogus",
                ctx=None,
            )

    async def test_invalid_risk_free_rate_raises(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        path = write_xml(tmp_path, XML_TWO_POSITIONS)
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp,
                "calculate_portfolio_metrics",
                file_path=path,
                risk_free_rate=5.0,  # 500% -> out of [0, 0.5]
                ctx=None,
            )

    async def test_non_xml_content_raises_file_operation_error(
        self, test_mcp: FastMCP, tmp_path: Path
    ) -> None:
        path = write_xml(tmp_path, "this is not xml at all")
        with pytest.raises(FileOperationError):
            await call_tool_fn(test_mcp, "calculate_portfolio_metrics", file_path=path, ctx=None)

    async def test_no_positions_raises(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        path = write_xml(tmp_path, XML_NO_POSITIONS)
        with pytest.raises(ValidationError):
            await call_tool_fn(test_mcp, "calculate_portfolio_metrics", file_path=path, ctx=None)


class TestCalculatePortfolioMetricsHappyPath:
    async def test_returns_metrics_json(
        self, test_mcp: FastMCP, tmp_path: Path, patch_yfinance
    ) -> None:
        path = write_xml(tmp_path, XML_TWO_POSITIONS)
        result = await call_tool_fn(
            test_mcp, "calculate_portfolio_metrics", file_path=path, ctx=None
        )
        data = json.loads(result)

        assert data["portfolio_summary"]["num_positions"] == 2
        assert "sharpe_ratio" in data["risk_adjusted_metrics"]
        assert "maximum_drawdown_pct" in data["risk_metrics"]
        assert "beta" in data["risk_metrics"]
        assert set(data["interpretation"]) == {"sharpe", "sortino", "max_drawdown"}


class TestAnalyzePortfolioCorrelation:
    async def test_single_position_returns_message(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        path = write_xml(tmp_path, XML_ONE_POSITION)
        result = await call_tool_fn(
            test_mcp, "analyze_portfolio_correlation", file_path=path, ctx=None
        )
        data = json.loads(result)
        assert data["num_positions"] == 1
        assert "message" in data

    async def test_correlation_matrix_returned(
        self, test_mcp: FastMCP, tmp_path: Path, patch_yfinance
    ) -> None:
        path = write_xml(tmp_path, XML_TWO_POSITIONS)
        result = await call_tool_fn(
            test_mcp, "analyze_portfolio_correlation", file_path=path, ctx=None
        )
        data = json.loads(result)

        assert data["summary"]["num_positions"] == 2
        assert "correlation_matrix" in data
        assert "CSPX" in data["correlation_matrix"]
        assert "position_weights" in data

    async def test_invalid_period_raises(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        path = write_xml(tmp_path, XML_TWO_POSITIONS)
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp,
                "analyze_portfolio_correlation",
                file_path=path,
                period="bogus",
                ctx=None,
            )
