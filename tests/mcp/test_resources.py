"""Tests for IB Analytics MCP resources.

Covers the read-only resources backed by ``data/raw`` XML files and the user
profile YAML. Resource handlers read from the current working directory, so tests
``chdir`` into a temp dir and stage ``data/raw`` / ``notes`` as needed.

Note: the rebalancing target-allocation precedence logic is covered separately in
``test_resources_rebalancing.py``; here we verify the resource payload shapes.
"""

import inspect
import json
from pathlib import Path

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.resources import (
    RESOURCE_PORTFOLIO_LATEST,
    RESOURCE_PORTFOLIO_LIST,
    RESOURCE_POSITIONS_CURRENT,
    RESOURCE_STRATEGY_REBALANCING,
    RESOURCE_STRATEGY_RISK,
    RESOURCE_STRATEGY_TAX,
    RESOURCE_TRADES_RECENT,
    RESOURCE_USER_PROFILE,
    register_resources,
)

ACCOUNT_ID = "U1234567"
XML_NAME = "U1234567_2025-01-01_2025-06-30.xml"

# Portfolio with a gain (CSPX) + a loss (EEM, for tax loss harvesting) and two trades.
PORTFOLIO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250630">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="5000" endingCash="5000" endingSettledCash="5000" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="CSPX" description="ISHARES CORE S&amp;P 500"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="IE00B5BMR087" position="10" markPrice="735.00"
          positionValue="7350" costBasisMoney="6000" fifoPnlUnrealized="1350"
          reportDate="20250630" multiplier="1" />
        <OpenPosition symbol="EEM" description="ISHARES MSCI EMERGING MARKETS"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US4642872349" position="200" markPrice="38.00"
          positionValue="7600" costBasisMoney="9000" fifoPnlUnrealized="-1400"
          reportDate="20250630" multiplier="1" />
      </OpenPositions>
      <Trades>
        <Trade tradeID="T001" accountId="U1234567" symbol="CSPX"
          description="ISHARES CORE S&amp;P 500" assetCategory="STK"
          currency="USD" fxRateToBase="1"
          buySell="BUY" quantity="10" tradePrice="600.00"
          tradeMoney="-6000" ibCommission="-1.00" ibCommissionCurrency="USD"
          tradeDate="20250301" settleDate="20250303"
          fifoPnlRealized="0" mtmPnl="0" multiplier="1"
          orderID="O001" execID="E001" />
        <Trade tradeID="T002" accountId="U1234567" symbol="EEM"
          description="ISHARES MSCI EMERGING MARKETS" assetCategory="STK"
          currency="USD" fxRateToBase="1"
          buySell="BUY" quantity="200" tradePrice="45.00"
          tradeMoney="-9000" ibCommission="-1.00" ibCommissionCurrency="USD"
          tradeDate="20250115" settleDate="20250117"
          fifoPnlRealized="0" mtmPnl="0" multiplier="1"
          orderID="O002" execID="E002" />
      </Trades>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""


async def _maybe_await(value: object) -> object:
    if inspect.isawaitable(value):
        return await value
    return value


async def read_resource(mcp: FastMCP, uri: str) -> str:
    """Read a static resource's text content."""
    res = await _maybe_await(mcp.get_resource(uri))
    return await _maybe_await(res.read())


async def read_account_resource(mcp: FastMCP, account_id: str) -> str:
    """Invoke the ``ib://accounts/{account_id}`` template handler."""
    # Use the singular get_resource_template(key) — present across the
    # FastMCP 2.x versions in local/CI; the plural get_resource_templates()
    # is not available on all of them.
    template = await _maybe_await(mcp.get_resource_template("ib://accounts/{account_id}"))
    assert template is not None, "expected an account resource template"
    return await _maybe_await(template.fn(account_id=account_id))


@pytest.fixture()
def test_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_resources(mcp)
    return mcp


@pytest.fixture()
def with_portfolio(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """chdir into tmp_path with a populated data/raw directory."""
    monkeypatch.chdir(tmp_path)
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    (raw / XML_NAME).write_text(PORTFOLIO_XML)
    return tmp_path


@pytest.fixture()
def empty_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestPortfolioListAndLatest:
    async def test_list_no_data_dir(self, test_mcp: FastMCP, empty_cwd: Path) -> None:
        data = json.loads(await read_resource(test_mcp, RESOURCE_PORTFOLIO_LIST))
        assert data["files"] == []

    async def test_list_returns_files(self, test_mcp: FastMCP, with_portfolio: Path) -> None:
        data = json.loads(await read_resource(test_mcp, RESOURCE_PORTFOLIO_LIST))
        assert data["count"] == 1
        assert data["files"][0]["filename"] == XML_NAME

    async def test_latest_no_data_dir(self, test_mcp: FastMCP, empty_cwd: Path) -> None:
        data = json.loads(await read_resource(test_mcp, RESOURCE_PORTFOLIO_LATEST))
        assert "error" in data

    async def test_latest_summary(self, test_mcp: FastMCP, with_portfolio: Path) -> None:
        data = json.loads(await read_resource(test_mcp, RESOURCE_PORTFOLIO_LATEST))
        assert data["account_id"] == ACCOUNT_ID
        assert data["num_positions"] == 2
        assert data["file"] == XML_NAME


class TestAccountResource:
    async def test_account_data(self, test_mcp: FastMCP, with_portfolio: Path) -> None:
        data = json.loads(await read_account_resource(test_mcp, ACCOUNT_ID))
        assert data["account_id"] == ACCOUNT_ID
        assert "total_value" in data

    async def test_unknown_account_returns_error(
        self, test_mcp: FastMCP, with_portfolio: Path
    ) -> None:
        data = json.loads(await read_account_resource(test_mcp, "U9999999"))
        assert "error" in data


class TestTradesAndPositions:
    async def test_recent_trades(self, test_mcp: FastMCP, with_portfolio: Path) -> None:
        data = json.loads(await read_resource(test_mcp, RESOURCE_TRADES_RECENT))
        assert data["count"] == 2
        symbols = {t["symbol"] for t in data["trades"]}
        assert symbols == {"CSPX", "EEM"}

    async def test_current_positions(self, test_mcp: FastMCP, with_portfolio: Path) -> None:
        data = json.loads(await read_resource(test_mcp, RESOURCE_POSITIONS_CURRENT))
        assert data["count"] == 2
        position = data["positions"][0]
        assert "market_value" in position
        assert "unrealized_pnl" in position


class TestStrategyResources:
    async def test_tax_context_has_loss_harvesting(
        self, test_mcp: FastMCP, with_portfolio: Path
    ) -> None:
        data = json.loads(await read_resource(test_mcp, RESOURCE_STRATEGY_TAX))
        assert "tax_lot_summary" in data
        assert "wash_sale_warnings" in data
        # EEM has an unrealized loss -> a loss harvesting opportunity.
        symbols = {o["symbol"] for o in data["tax_loss_harvesting_opportunities"]}
        assert "EEM" in symbols

    async def test_rebalancing_context_shape(self, test_mcp: FastMCP, with_portfolio: Path) -> None:
        data = json.loads(await read_resource(test_mcp, RESOURCE_STRATEGY_REBALANCING))
        assert set(data["current_allocation"]) == {"BOND", "STK", "CASH"}
        assert "drift_analysis" in data
        assert isinstance(data["rebalancing_needed"], bool)

    async def test_risk_context_shape(self, test_mcp: FastMCP, with_portfolio: Path) -> None:
        data = json.loads(await read_resource(test_mcp, RESOURCE_STRATEGY_RISK))
        assert "portfolio_risk_metrics" in data
        assert "interest_rate_scenarios" in data
        assert "liquidity_risk" in data


class TestUserProfile:
    async def test_profile_missing_returns_error(self, test_mcp: FastMCP, empty_cwd: Path) -> None:
        data = json.loads(await read_resource(test_mcp, RESOURCE_USER_PROFILE))
        assert data["error"] == "Profile not found"

    async def test_profile_returned(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.chdir(tmp_path)
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "investor-profile.yaml").write_text(
            "residency:\n  country: Malaysia\ninvestment_profile:\n  type: balanced\n"
        )
        data = json.loads(await read_resource(test_mcp, RESOURCE_USER_PROFILE))
        assert data["residency"]["country"] == "Malaysia"
