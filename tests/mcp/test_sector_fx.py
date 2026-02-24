"""Tests for sector allocation and FX exposure MCP tools"""

import json
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

SAMPLE_XML_MULTI_CURRENCY = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="10000" endingCash="10000" endingSettledCash="10000"
          deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
          commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" />
        <CashReportCurrency currency="USD"
          startingCash="5000" endingCash="5000" endingSettledCash="5000"
          deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
          commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="CSPX" description="ISHARES CORE S&amp;P 500"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="IE00B5BMR087" position="10" markPrice="735.00"
          positionValue="7350" costBasisMoney="6000" fifoPnlUnrealized="1350"
          reportDate="20250131" multiplier="1" />
        <OpenPosition symbol="9433.T" description="KDDI CORPORATION"
          assetCategory="STK" currency="JPY" fxRateToBase="0.006547"
          isin="JP3496400007" position="100" markPrice="5000"
          positionValue="500000" costBasisMoney="450000" fifoPnlUnrealized="50000"
          reportDate="20250131" multiplier="1" />
        <OpenPosition symbol="IDTL" description="ISHARES USD TRES 20PLUS YR"
          assetCategory="STK" currency="GBP" fxRateToBase="1.27"
          isin="IE00BSKRJZ44" position="100" markPrice="3.20"
          positionValue="320" costBasisMoney="300" fifoPnlUnrealized="20"
          reportDate="20250131" multiplier="1" />
      </OpenPositions>
      <Trades />
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""


@pytest.fixture
def tool_registry():
    """Register sector_fx tools with a capture MCP and return tool functions."""
    from ib_sec_mcp.mcp.tools.sector_fx import register_sector_fx_tools

    tools = {}

    class CaptureMCP:
        def tool(self, fn):
            tools[fn.__name__] = fn
            return fn

    register_sector_fx_tools(CaptureMCP())
    return tools


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables."""
    monkeypatch.setenv("QUERY_ID", "test_query_id")
    monkeypatch.setenv("TOKEN", "test_token")


class TestAnalyzeSectorAllocationTool:
    """Tests for analyze_sector_allocation MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_json(self, tool_registry, mock_env):
        """Test that the tool returns valid JSON."""
        mock_sector_data = {
            "CSPX": {"sector": "Technology", "industry": "Asset Management"},
            "9433.T": {"sector": "Communication Services", "industry": "Telecom"},
            "IDTL": {"sector": "Financial Services", "industry": "Asset Management"},
        }
        with (
            patch(
                "ib_sec_mcp.mcp.tools.sector_fx._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(
                    SAMPLE_XML_MULTI_CURRENCY,
                    date(2025, 1, 1),
                    date(2025, 1, 31),
                ),
            ),
            patch(
                "ib_sec_mcp.analyzers.sector.fetch_sector_info",
                new_callable=AsyncMock,
                return_value=mock_sector_data,
            ),
        ):
            result = await tool_registry["analyze_sector_allocation"](
                start_date="2025-01-01",
            )

        parsed = json.loads(result)
        assert "sectors" in parsed
        assert "concentration_risk" in parsed
        assert parsed["analyzer"] == "Sector"

    @pytest.mark.asyncio
    async def test_contains_all_positions(self, tool_registry, mock_env):
        """Test that all positions are represented in sector data."""
        mock_sector_data = {
            "CSPX": {"sector": "Technology", "industry": "ETF"},
            "9433.T": {"sector": "Communication Services", "industry": "Telecom"},
            "IDTL": {"sector": "Financial Services", "industry": "Bond ETF"},
        }
        with (
            patch(
                "ib_sec_mcp.mcp.tools.sector_fx._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(
                    SAMPLE_XML_MULTI_CURRENCY,
                    date(2025, 1, 1),
                    date(2025, 1, 31),
                ),
            ),
            patch(
                "ib_sec_mcp.analyzers.sector.fetch_sector_info",
                new_callable=AsyncMock,
                return_value=mock_sector_data,
            ),
        ):
            result = await tool_registry["analyze_sector_allocation"](
                start_date="2025-01-01",
            )

        parsed = json.loads(result)
        assert parsed["position_count"] == 3
        assert parsed["equity_count"] == 3


class TestAnalyzeFXExposureTool:
    """Tests for analyze_fx_exposure MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_json(self, tool_registry, mock_env):
        """Test that the tool returns valid JSON."""
        with patch(
            "ib_sec_mcp.mcp.tools.sector_fx._get_or_fetch_data",
            new_callable=AsyncMock,
            return_value=(
                SAMPLE_XML_MULTI_CURRENCY,
                date(2025, 1, 1),
                date(2025, 1, 31),
            ),
        ):
            result = await tool_registry["analyze_fx_exposure"](
                start_date="2025-01-01",
            )

        parsed = json.loads(result)
        assert "currency_exposures" in parsed
        assert "scenarios" in parsed
        assert "hedge_recommendations" in parsed
        assert parsed["analyzer"] == "FXExposure"

    @pytest.mark.asyncio
    async def test_multi_currency_detected(self, tool_registry, mock_env):
        """Test that multiple currencies are detected."""
        with patch(
            "ib_sec_mcp.mcp.tools.sector_fx._get_or_fetch_data",
            new_callable=AsyncMock,
            return_value=(
                SAMPLE_XML_MULTI_CURRENCY,
                date(2025, 1, 1),
                date(2025, 1, 31),
            ),
        ):
            result = await tool_registry["analyze_fx_exposure"](
                start_date="2025-01-01",
            )

        parsed = json.loads(result)
        exposures = parsed["currency_exposures"]
        assert "USD" in exposures
        assert "JPY" in exposures
        assert "GBP" in exposures

    @pytest.mark.asyncio
    async def test_custom_scenario_pct(self, tool_registry, mock_env):
        """Test custom FX scenario percentage."""
        with patch(
            "ib_sec_mcp.mcp.tools.sector_fx._get_or_fetch_data",
            new_callable=AsyncMock,
            return_value=(
                SAMPLE_XML_MULTI_CURRENCY,
                date(2025, 1, 1),
                date(2025, 1, 31),
            ),
        ):
            result = await tool_registry["analyze_fx_exposure"](
                start_date="2025-01-01",
                fx_scenario_pct=15.0,
            )

        parsed = json.loads(result)
        assert parsed["fx_scenario_pct"] == "15.0"

    @pytest.mark.asyncio
    async def test_invalid_scenario_pct_rejected(self, tool_registry, mock_env):
        """Test that invalid scenario percentage is rejected."""
        from ib_sec_mcp.mcp.exceptions import ValidationError

        with pytest.raises(ValidationError, match="fx_scenario_pct"):
            await tool_registry["analyze_fx_exposure"](
                start_date="2025-01-01",
                fx_scenario_pct=0.0,
            )

        with pytest.raises(ValidationError, match="fx_scenario_pct"):
            await tool_registry["analyze_fx_exposure"](
                start_date="2025-01-01",
                fx_scenario_pct=101.0,
            )

    @pytest.mark.asyncio
    async def test_scenarios_exclude_base_currency(self, tool_registry, mock_env):
        """Test that base currency is excluded from scenarios."""
        with patch(
            "ib_sec_mcp.mcp.tools.sector_fx._get_or_fetch_data",
            new_callable=AsyncMock,
            return_value=(
                SAMPLE_XML_MULTI_CURRENCY,
                date(2025, 1, 1),
                date(2025, 1, 31),
            ),
        ):
            result = await tool_registry["analyze_fx_exposure"](
                start_date="2025-01-01",
            )

        parsed = json.loads(result)
        assert "USD" not in parsed["scenarios"]["by_currency"]

    @pytest.mark.asyncio
    async def test_hedge_recommendations_included(self, tool_registry, mock_env):
        """Test that hedge recommendations are present."""
        with patch(
            "ib_sec_mcp.mcp.tools.sector_fx._get_or_fetch_data",
            new_callable=AsyncMock,
            return_value=(
                SAMPLE_XML_MULTI_CURRENCY,
                date(2025, 1, 1),
                date(2025, 1, 31),
            ),
        ):
            result = await tool_registry["analyze_fx_exposure"](
                start_date="2025-01-01",
            )

        parsed = json.loads(result)
        recs = parsed["hedge_recommendations"]
        assert isinstance(recs, list)
        assert len(recs) >= 1
        for rec in recs:
            assert "risk_level" in rec
            assert "recommendation" in rec
