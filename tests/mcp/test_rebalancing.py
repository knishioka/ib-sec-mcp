"""Tests for Portfolio Rebalancing MCP tools"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.mcp.tools.rebalancing import (
    _estimate_commission,
    register_rebalancing_tools,
)
from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass


@pytest.fixture
def sample_account():
    """Create a sample account with positions for testing."""
    return Account(
        account_id="U12345678",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 6, 30),
        base_currency="USD",
        cash_balances=[
            CashBalance(
                currency="USD",
                starting_cash=Decimal("10000"),
                ending_cash=Decimal("5000"),
                ending_settled_cash=Decimal("5000"),
            )
        ],
        positions=[
            Position(
                account_id="U12345678",
                symbol="AAPL",
                asset_class=AssetClass.STOCK,
                quantity=Decimal("100"),
                multiplier=Decimal("1"),
                mark_price=Decimal("150.00"),
                position_value=Decimal("15000.00"),
                average_cost=Decimal("120.00"),
                cost_basis=Decimal("12000.00"),
                unrealized_pnl=Decimal("3000.00"),
                position_date=date(2025, 6, 30),
            ),
            Position(
                account_id="U12345678",
                symbol="MSFT",
                asset_class=AssetClass.STOCK,
                quantity=Decimal("50"),
                multiplier=Decimal("1"),
                mark_price=Decimal("400.00"),
                position_value=Decimal("20000.00"),
                average_cost=Decimal("350.00"),
                cost_basis=Decimal("17500.00"),
                unrealized_pnl=Decimal("2500.00"),
                position_date=date(2025, 6, 30),
            ),
            Position(
                account_id="U12345678",
                symbol="VOO",
                asset_class=AssetClass.STOCK,
                quantity=Decimal("20"),
                multiplier=Decimal("1"),
                mark_price=Decimal("500.00"),
                position_value=Decimal("10000.00"),
                average_cost=Decimal("450.00"),
                cost_basis=Decimal("9000.00"),
                unrealized_pnl=Decimal("1000.00"),
                position_date=date(2025, 6, 30),
            ),
        ],
        trades=[],
    )


@pytest.fixture
def sample_xml_data():
    """Sample XML data string."""
    return (
        "<FlexQueryResponse><FlexStatements><FlexStatement/></FlexStatements></FlexQueryResponse>"
    )


class TestEstimateCommission:
    """Tests for _estimate_commission helper."""

    def test_stock_commission_per_share(self):
        commission = _estimate_commission("AAPL", "STK", Decimal("15000"), Decimal("100"))
        # 100 shares * $0.005 = $0.50, but minimum is $1.00
        assert commission == Decimal("1.00")

    def test_stock_commission_large_order(self):
        commission = _estimate_commission("AAPL", "STK", Decimal("150000"), Decimal("1000"))
        # 1000 shares * $0.005 = $5.00
        assert commission == Decimal("5.000")

    def test_stock_commission_minimum(self):
        commission = _estimate_commission("AAPL", "STK", Decimal("150"), Decimal("1"))
        # 1 share * $0.005 = $0.005, minimum $1.00
        assert commission == Decimal("1.00")

    def test_bond_commission(self):
        commission = _estimate_commission("UST", "BOND", Decimal("100000"), Decimal("100"))
        # 0.1% of $100,000 = $100
        assert commission == Decimal("100.000")

    def test_option_commission(self):
        commission = _estimate_commission("AAPL", "OPT", Decimal("500"), Decimal("5"))
        # 5 contracts * $0.65 = $3.25
        assert commission == Decimal("3.25")

    def test_futures_commission(self):
        commission = _estimate_commission("ES", "FUT", Decimal("250000"), Decimal("2"))
        # 2 contracts * $2.25 = $4.50
        assert commission == Decimal("4.50")

    def test_forex_commission(self):
        commission = _estimate_commission("USDJPY", "CASH", Decimal("100000"), Decimal("100000"))
        # 0.002% of $100,000 = $2.00
        assert commission == Decimal("2.00000")

    def test_unknown_asset_class_uses_default(self):
        commission = _estimate_commission("XYZ", "UNKNOWN", Decimal("10000"), Decimal("100"))
        # Default 0.1% of $10,000 = $10
        assert commission == Decimal("10.000")


class TestGenerateRebalancingTrades:
    """Tests for generate_rebalancing_trades tool."""

    @pytest.mark.asyncio
    async def test_basic_rebalancing(self, sample_account, sample_xml_data):
        """Test basic rebalancing trade generation."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            # Target: equal weight across three stocks
            tool_fn = mcp._tool_manager._tools["generate_rebalancing_trades"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 33.33, "MSFT": 33.33, "VOO": 33.34},
                start_date="2025-01-01",
                end_date="2025-06-30",
            )

            result = json.loads(result_str)

            assert "portfolio_summary" in result
            assert "rebalancing_trades" in result
            assert "trade_summary" in result
            assert result["portfolio_summary"]["total_value"] == "50000.00"
            assert result["portfolio_summary"]["position_count"] == 3

    @pytest.mark.asyncio
    async def test_rebalancing_with_new_position(self, sample_account, sample_xml_data):
        """Test rebalancing when target includes a symbol not in current portfolio."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            tool_fn = mcp._tool_manager._tools["generate_rebalancing_trades"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 25.0, "MSFT": 25.0, "VOO": 25.0, "GOOG": 25.0},
                start_date="2025-01-01",
            )

            result = json.loads(result_str)
            symbols = [t["symbol"] for t in result["rebalancing_trades"]]
            assert "GOOG" in symbols

            goog_trade = next(t for t in result["rebalancing_trades"] if t["symbol"] == "GOOG")
            assert goog_trade["direction"] == "BUY"
            assert goog_trade["mark_price"] == "N/A"

    @pytest.mark.asyncio
    async def test_rebalancing_close_position(self, sample_account, sample_xml_data):
        """Test rebalancing when a current position should be closed."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            # Target only AAPL and VOO, closing MSFT
            tool_fn = mcp._tool_manager._tools["generate_rebalancing_trades"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 60.0, "VOO": 40.0},
                start_date="2025-01-01",
            )

            result = json.loads(result_str)
            msft_trade = next(t for t in result["rebalancing_trades"] if t["symbol"] == "MSFT")
            assert msft_trade["direction"] == "SELL"
            assert msft_trade["target_weight_pct"] == "0.00"

    @pytest.mark.asyncio
    async def test_custom_portfolio_value(self, sample_account, sample_xml_data):
        """Test rebalancing with custom total_portfolio_value override."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            tool_fn = mcp._tool_manager._tools["generate_rebalancing_trades"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 50.0, "MSFT": 50.0},
                start_date="2025-01-01",
                total_portfolio_value=100000.0,
            )

            result = json.loads(result_str)
            assert result["portfolio_summary"]["total_value"] == "100000.00"

    @pytest.mark.asyncio
    async def test_validation_empty_allocation(self, sample_account, sample_xml_data):
        """Test that empty target allocation raises ValidationError."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        tool_fn = mcp._tool_manager._tools["generate_rebalancing_trades"].fn
        with pytest.raises(ValidationError, match="target_allocation cannot be empty"):
            await tool_fn(
                target_allocation={},
                start_date="2025-01-01",
            )

    @pytest.mark.asyncio
    async def test_validation_weights_not_100(self, sample_account, sample_xml_data):
        """Test that weights not summing to 100 raises ValidationError."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        tool_fn = mcp._tool_manager._tools["generate_rebalancing_trades"].fn
        with pytest.raises(ValidationError, match="must sum to 100"):
            await tool_fn(
                target_allocation={"AAPL": 30.0, "MSFT": 30.0},
                start_date="2025-01-01",
            )

    @pytest.mark.asyncio
    async def test_validation_negative_weight(self, sample_account, sample_xml_data):
        """Test that negative weight raises ValidationError."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        tool_fn = mcp._tool_manager._tools["generate_rebalancing_trades"].fn
        with pytest.raises(ValidationError, match="must be non-negative"):
            await tool_fn(
                target_allocation={"AAPL": -10.0, "MSFT": 110.0},
                start_date="2025-01-01",
            )

    @pytest.mark.asyncio
    async def test_validation_negative_portfolio_value(self, sample_account, sample_xml_data):
        """Test that negative portfolio value raises ValidationError."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            tool_fn = mcp._tool_manager._tools["generate_rebalancing_trades"].fn
            with pytest.raises(ValidationError, match="must be positive"):
                await tool_fn(
                    target_allocation={"AAPL": 100.0},
                    start_date="2025-01-01",
                    total_portfolio_value=-1000.0,
                )

    @pytest.mark.asyncio
    async def test_validation_empty_symbol(self, sample_account, sample_xml_data):
        """Test that empty symbol raises ValidationError."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        tool_fn = mcp._tool_manager._tools["generate_rebalancing_trades"].fn
        with pytest.raises(ValidationError, match="Symbol cannot be empty"):
            await tool_fn(
                target_allocation={"": 100.0},
                start_date="2025-01-01",
            )

    @pytest.mark.asyncio
    async def test_trade_summary_values(self, sample_account, sample_xml_data):
        """Test that trade summary correctly sums buy/sell values."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            tool_fn = mcp._tool_manager._tools["generate_rebalancing_trades"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 33.33, "MSFT": 33.33, "VOO": 33.34},
                start_date="2025-01-01",
            )

            result = json.loads(result_str)
            summary = result["trade_summary"]
            assert int(summary["total_trades"]) > 0
            assert Decimal(summary["total_estimated_commission"]) >= Decimal("0")

    @pytest.mark.asyncio
    async def test_json_serialization(self, sample_account, sample_xml_data):
        """Test that result is valid JSON with proper Decimal serialization."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            tool_fn = mcp._tool_manager._tools["generate_rebalancing_trades"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 50.0, "MSFT": 50.0},
                start_date="2025-01-01",
            )

            # Should parse without errors
            result = json.loads(result_str)
            assert isinstance(result, dict)

            # Check no Decimal objects leaked through
            def check_no_decimal(obj):
                if isinstance(obj, dict):
                    for v in obj.values():
                        check_no_decimal(v)
                elif isinstance(obj, list):
                    for v in obj:
                        check_no_decimal(v)
                else:
                    assert not isinstance(obj, Decimal), f"Found Decimal in JSON: {obj}"

            check_no_decimal(result)


class TestSimulateRebalancing:
    """Tests for simulate_rebalancing tool."""

    @pytest.mark.asyncio
    async def test_basic_simulation(self, sample_account, sample_xml_data):
        """Test basic rebalancing simulation."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            tool_fn = mcp._tool_manager._tools["simulate_rebalancing"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 33.33, "MSFT": 33.33, "VOO": 33.34},
                start_date="2025-01-01",
            )

            result = json.loads(result_str)

            assert result["simulation_summary"]["is_dry_run"] is True
            assert "current_allocation" in result
            assert "projected_allocation" in result
            assert "cost_analysis" in result
            assert "tax_impact" in result
            assert "cash_position" in result

    @pytest.mark.asyncio
    async def test_simulation_tax_impact_with_gain(self, sample_account, sample_xml_data):
        """Test that simulation correctly calculates tax impact for selling positions with gains."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            # Sell MSFT (has unrealized gain of $2500) to buy more AAPL
            tool_fn = mcp._tool_manager._tools["simulate_rebalancing"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 80.0, "VOO": 20.0},
                start_date="2025-01-01",
            )

            result = json.loads(result_str)
            tax = result["tax_impact"]

            # MSFT should appear in gains (unrealized_pnl = $2500, fully sold)
            assert len(tax["positions_with_gains"]) > 0
            assert Decimal(tax["total_estimated_taxable_gain"]) > Decimal("0")

    @pytest.mark.asyncio
    async def test_simulation_warnings_new_positions(self, sample_account, sample_xml_data):
        """Test warnings for new positions not in current portfolio."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            tool_fn = mcp._tool_manager._tools["simulate_rebalancing"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 25.0, "MSFT": 25.0, "VOO": 25.0, "GOOG": 25.0},
                start_date="2025-01-01",
            )

            result = json.loads(result_str)
            warnings = result["warnings"]
            assert any("New positions to open" in w for w in warnings)
            assert any("GOOG" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_simulation_warnings_close_positions(self, sample_account, sample_xml_data):
        """Test warnings for positions to be fully closed."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            tool_fn = mcp._tool_manager._tools["simulate_rebalancing"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 60.0, "VOO": 40.0},
                start_date="2025-01-01",
            )

            result = json.loads(result_str)
            warnings = result["warnings"]
            assert any("Positions to fully close" in w for w in warnings)
            assert any("MSFT" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_simulation_validation_errors(self):
        """Test that simulation validates inputs properly."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        tool_fn = mcp._tool_manager._tools["simulate_rebalancing"].fn

        with pytest.raises(ValidationError, match="target_allocation cannot be empty"):
            await tool_fn(target_allocation={}, start_date="2025-01-01")

        with pytest.raises(ValidationError, match="must sum to 100"):
            await tool_fn(
                target_allocation={"AAPL": 50.0},
                start_date="2025-01-01",
            )

    @pytest.mark.asyncio
    async def test_simulation_commission_percentage(self, sample_account, sample_xml_data):
        """Test that commission as percentage of portfolio is calculated."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            tool_fn = mcp._tool_manager._tools["simulate_rebalancing"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 50.0, "MSFT": 50.0},
                start_date="2025-01-01",
            )

            result = json.loads(result_str)
            cost = result["cost_analysis"]
            assert "commission_as_pct_of_portfolio" in cost
            pct = Decimal(cost["commission_as_pct_of_portfolio"])
            assert pct >= Decimal("0")

    @pytest.mark.asyncio
    async def test_simulation_json_serialization(self, sample_account, sample_xml_data):
        """Test that simulation result is valid JSON."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            tool_fn = mcp._tool_manager._tools["simulate_rebalancing"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 50.0, "MSFT": 25.0, "VOO": 25.0},
                start_date="2025-01-01",
            )

            result = json.loads(result_str)
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_simulation_with_custom_portfolio_value(self, sample_account, sample_xml_data):
        """Test simulation with overridden portfolio value."""
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register_rebalancing_tools(mcp)

        with (
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=(sample_xml_data, date(2025, 1, 1), date(2025, 6, 30)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.rebalancing._parse_account_by_index",
                return_value=sample_account,
            ),
        ):
            tool_fn = mcp._tool_manager._tools["simulate_rebalancing"].fn
            result_str = await tool_fn(
                target_allocation={"AAPL": 50.0, "MSFT": 50.0},
                start_date="2025-01-01",
                total_portfolio_value=200000.0,
            )

            result = json.loads(result_str)
            assert result["simulation_summary"]["portfolio_value"] == "200000.00"
