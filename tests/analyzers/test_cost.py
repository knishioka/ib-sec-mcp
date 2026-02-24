"""Tests for cost analyzer"""

from datetime import date
from decimal import Decimal

import pytest

from ib_sec_mcp.analyzers.cost import CostAnalyzer
from ib_sec_mcp.models.account import Account
from ib_sec_mcp.models.trade import AssetClass, BuySell, Trade


@pytest.fixture
def small_trade():
    """A small trade (abs(trade_money) < 5000)."""
    return Trade(
        account_id="U1234567",
        trade_id="SM1",
        trade_date=date(2025, 1, 10),
        settle_date=date(2025, 1, 12),
        symbol="AAPL",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.BUY,
        quantity=Decimal("10"),
        trade_price=Decimal("150"),
        trade_money=Decimal("-1500"),
        ib_commission=Decimal("-1.50"),
        fifo_pnl_realized=Decimal("0"),
    )


@pytest.fixture
def medium_trade():
    """A medium trade (5000 <= abs(trade_money) < 50000)."""
    return Trade(
        account_id="U1234567",
        trade_id="MD1",
        trade_date=date(2025, 1, 15),
        settle_date=date(2025, 1, 17),
        symbol="MSFT",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.BUY,
        quantity=Decimal("20"),
        trade_price=Decimal("400"),
        trade_money=Decimal("-8000"),
        ib_commission=Decimal("-3.00"),
        fifo_pnl_realized=Decimal("50"),
    )


@pytest.fixture
def large_trade():
    """A large trade (abs(trade_money) >= 50000)."""
    return Trade(
        account_id="U1234567",
        trade_id="LG1",
        trade_date=date(2025, 1, 20),
        settle_date=date(2025, 1, 22),
        symbol="GOOG",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.BUY,
        quantity=Decimal("30"),
        trade_price=Decimal("2000"),
        trade_money=Decimal("-60000"),
        ib_commission=Decimal("-5.00"),
        fifo_pnl_realized=Decimal("200"),
    )


@pytest.fixture
def bond_trade():
    """A bond trade for asset class breakdown."""
    return Trade(
        account_id="U1234567",
        trade_id="BD1",
        trade_date=date(2025, 1, 12),
        settle_date=date(2025, 1, 14),
        symbol="US912810SJ88",
        description="US T-BOND STRIPS 2035",
        asset_class=AssetClass.BOND,
        buy_sell=BuySell.BUY,
        quantity=Decimal("10000"),
        trade_price=Decimal("65"),
        trade_money=Decimal("-6500"),
        ib_commission=Decimal("-2.50"),
        fifo_pnl_realized=Decimal("0"),
    )


@pytest.fixture
def mixed_cost_account(small_trade, medium_trade, large_trade):
    """Account with trades across all size categories."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        trades=[small_trade, medium_trade, large_trade],
        positions=[],
    )


@pytest.fixture
def empty_account():
    """Account with no trades."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        trades=[],
        positions=[],
    )


@pytest.fixture
def multi_asset_account(small_trade, bond_trade):
    """Account with trades across multiple asset classes."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        trades=[small_trade, bond_trade],
        positions=[],
    )


@pytest.fixture
def multi_symbol_account():
    """Account with multiple trades per symbol."""
    trades = [
        Trade(
            account_id="U1234567",
            trade_id="MSY1",
            trade_date=date(2025, 1, 10),
            settle_date=date(2025, 1, 12),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.BUY,
            quantity=Decimal("10"),
            trade_price=Decimal("150"),
            trade_money=Decimal("-1500"),
            ib_commission=Decimal("-1.50"),
            fifo_pnl_realized=Decimal("0"),
        ),
        Trade(
            account_id="U1234567",
            trade_id="MSY2",
            trade_date=date(2025, 1, 20),
            settle_date=date(2025, 1, 22),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.SELL,
            quantity=Decimal("10"),
            trade_price=Decimal("160"),
            trade_money=Decimal("1600"),
            ib_commission=Decimal("-1.50"),
            fifo_pnl_realized=Decimal("100"),
        ),
        Trade(
            account_id="U1234567",
            trade_id="MSY3",
            trade_date=date(2025, 1, 15),
            settle_date=date(2025, 1, 17),
            symbol="MSFT",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.SELL,
            quantity=Decimal("5"),
            trade_price=Decimal("400"),
            trade_money=Decimal("2000"),
            ib_commission=Decimal("-2.00"),
            fifo_pnl_realized=Decimal("-30"),
        ),
    ]
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        trades=trades,
        positions=[],
    )


class TestCostAnalyzer:
    """Tests for CostAnalyzer."""

    def test_analyzer_name(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()
        assert result["analyzer"] == "Cost"

    def test_empty_account_returns_zeros(self, empty_account):
        analyzer = CostAnalyzer(account=empty_account)
        result = analyzer.analyze()

        assert result["total_commissions"] == "0"
        assert result["total_volume"] == "0"
        assert result["commission_rate"] == "0"
        assert result["by_asset_class"] == {}
        assert result["by_symbol"] == {}
        # Should NOT have other keys present when empty
        assert "avg_commission_per_trade" not in result

    def test_total_commissions(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()

        # abs(-1.50) + abs(-3.00) + abs(-5.00) = 9.50
        assert Decimal(result["total_commissions"]) == Decimal("9.50")

    def test_total_volume(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()

        # abs(-1500) + abs(-8000) + abs(-60000) = 69500
        assert Decimal(result["total_volume"]) == Decimal("69500")

    def test_commission_rate(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()

        expected_rate = (Decimal("9.50") / Decimal("69500")) * 100
        assert Decimal(result["commission_rate"]) == expected_rate

    def test_avg_commission_per_trade(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()

        # 9.50 / 3 trades
        expected_avg = Decimal("9.50") / Decimal("3")
        assert Decimal(result["avg_commission_per_trade"]) == expected_avg

    def test_commission_impact_pct(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()

        # total_realized_pnl = 0 + 50 + 200 = 250
        # commission_impact = (9.50 / abs(250)) * 100 = 3.8
        expected_impact = (Decimal("9.50") / Decimal("250")) * 100
        assert Decimal(result["commission_impact_pct"]) == expected_impact

    def test_commission_impact_zero_pnl(self):
        """When total realized PnL is zero, commission impact should be zero."""
        trades = [
            Trade(
                account_id="U1234567",
                trade_id="ZERO1",
                trade_date=date(2025, 1, 10),
                settle_date=date(2025, 1, 12),
                symbol="AAPL",
                asset_class=AssetClass.STOCK,
                buy_sell=BuySell.BUY,
                quantity=Decimal("10"),
                trade_price=Decimal("150"),
                trade_money=Decimal("-1500"),
                ib_commission=Decimal("-1.50"),
                fifo_pnl_realized=Decimal("0"),
            ),
        ]
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=trades,
            positions=[],
        )
        analyzer = CostAnalyzer(account=account)
        result = analyzer.analyze()

        assert Decimal(result["commission_impact_pct"]) == Decimal("0")

    def test_trade_size_distribution(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()

        assert result["small_trades_count"] == 1  # 1500 < 5000
        assert result["medium_trades_count"] == 1  # 5000 <= 8000 < 50000
        assert result["large_trades_count"] == 1  # 60000 >= 50000

    def test_small_trades_avg_commission(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()

        # Only 1 small trade with commission 1.50
        assert Decimal(result["small_trades_avg_commission"]) == Decimal("1.50")

    def test_medium_trades_avg_commission(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()

        assert Decimal(result["medium_trades_avg_commission"]) == Decimal("3.00")

    def test_large_trades_avg_commission(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()

        assert Decimal(result["large_trades_avg_commission"]) == Decimal("5.00")

    def test_no_trades_in_size_category(self):
        """When a size category has no trades, avg commission should be 0."""
        # Only medium trades
        trades = [
            Trade(
                account_id="U1234567",
                trade_id="MED_ONLY",
                trade_date=date(2025, 1, 10),
                settle_date=date(2025, 1, 12),
                symbol="AAPL",
                asset_class=AssetClass.STOCK,
                buy_sell=BuySell.BUY,
                quantity=Decimal("50"),
                trade_price=Decimal("150"),
                trade_money=Decimal("-7500"),
                ib_commission=Decimal("-2.00"),
                fifo_pnl_realized=Decimal("0"),
            ),
        ]
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=trades,
            positions=[],
        )
        analyzer = CostAnalyzer(account=account)
        result = analyzer.analyze()

        assert result["small_trades_count"] == 0
        assert Decimal(result["small_trades_avg_commission"]) == Decimal("0")
        assert result["large_trades_count"] == 0
        assert Decimal(result["large_trades_avg_commission"]) == Decimal("0")

    def test_by_asset_class_breakdown(self, multi_asset_account):
        analyzer = CostAnalyzer(account=multi_asset_account)
        result = analyzer.analyze()

        by_asset = result["by_asset_class"]
        assert AssetClass.STOCK.value in by_asset
        assert AssetClass.BOND.value in by_asset

        stock_data = by_asset[AssetClass.STOCK.value]
        assert stock_data["trade_count"] == 1
        assert Decimal(stock_data["total_commissions"]) == Decimal("1.50")
        assert Decimal(stock_data["total_volume"]) == Decimal("1500")

        bond_data = by_asset[AssetClass.BOND.value]
        assert bond_data["trade_count"] == 1
        assert Decimal(bond_data["total_commissions"]) == Decimal("2.50")
        assert Decimal(bond_data["total_volume"]) == Decimal("6500")

    def test_by_symbol_breakdown(self, multi_symbol_account):
        analyzer = CostAnalyzer(account=multi_symbol_account)
        result = analyzer.analyze()

        by_symbol = result["by_symbol"]
        assert "AAPL" in by_symbol
        assert "MSFT" in by_symbol

        aapl = by_symbol["AAPL"]
        assert aapl["trade_count"] == 2
        # abs(-1.50) + abs(-1.50) = 3.00
        assert Decimal(aapl["total_commissions"]) == Decimal("3.00")
        # abs(-1500) + abs(1600) = 3100
        assert Decimal(aapl["total_volume"]) == Decimal("3100")

        msft = by_symbol["MSFT"]
        assert msft["trade_count"] == 1
        assert Decimal(msft["total_commissions"]) == Decimal("2.00")
        assert Decimal(msft["total_volume"]) == Decimal("2000")

    def test_by_symbol_commission_rate(self, multi_symbol_account):
        analyzer = CostAnalyzer(account=multi_symbol_account)
        result = analyzer.analyze()

        aapl = result["by_symbol"]["AAPL"]
        expected_rate = (Decimal("3.00") / Decimal("3100")) * 100
        assert Decimal(aapl["commission_rate"]) == expected_rate

    def test_single_trade(self, small_trade):
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=[small_trade],
            positions=[],
        )
        analyzer = CostAnalyzer(account=account)
        result = analyzer.analyze()

        assert Decimal(result["total_commissions"]) == Decimal("1.50")
        assert Decimal(result["total_volume"]) == Decimal("1500")
        assert Decimal(result["avg_commission_per_trade"]) == Decimal("1.50")
        assert result["small_trades_count"] == 1
        assert result["medium_trades_count"] == 0
        assert result["large_trades_count"] == 0

    def test_boundary_trade_at_5000(self):
        """Trade at exactly 5000 is medium, not small."""
        trade = Trade(
            account_id="U1234567",
            trade_id="BOUNDARY_5K",
            trade_date=date(2025, 1, 10),
            settle_date=date(2025, 1, 12),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.BUY,
            quantity=Decimal("50"),
            trade_price=Decimal("100"),
            trade_money=Decimal("-5000"),
            ib_commission=Decimal("-2.00"),
            fifo_pnl_realized=Decimal("0"),
        )
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=[trade],
            positions=[],
        )
        analyzer = CostAnalyzer(account=account)
        result = analyzer.analyze()

        assert result["small_trades_count"] == 0
        assert result["medium_trades_count"] == 1

    def test_boundary_trade_at_50000(self):
        """Trade at exactly 50000 is large, not medium."""
        trade = Trade(
            account_id="U1234567",
            trade_id="BOUNDARY_50K",
            trade_date=date(2025, 1, 10),
            settle_date=date(2025, 1, 12),
            symbol="GOOG",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.BUY,
            quantity=Decimal("25"),
            trade_price=Decimal("2000"),
            trade_money=Decimal("-50000"),
            ib_commission=Decimal("-4.00"),
            fifo_pnl_realized=Decimal("0"),
        )
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=[trade],
            positions=[],
        )
        analyzer = CostAnalyzer(account=account)
        result = analyzer.analyze()

        assert result["medium_trades_count"] == 0
        assert result["large_trades_count"] == 1

    def test_decimal_precision(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()

        numeric_keys = [
            "total_commissions",
            "total_volume",
            "commission_rate",
            "avg_commission_per_trade",
            "total_realized_pnl",
            "commission_impact_pct",
            "small_trades_avg_commission",
            "medium_trades_avg_commission",
            "large_trades_avg_commission",
        ]
        for key in numeric_keys:
            value_str = result[key]
            parsed = Decimal(value_str)
            reparsed = str(parsed)
            assert "000000001" not in reparsed

    def test_metadata_fields(self, mixed_cost_account):
        analyzer = CostAnalyzer(account=mixed_cost_account)
        result = analyzer.analyze()

        assert result["account_id"] == "U1234567"
        assert result["from_date"] == "2025-01-01"
        assert result["to_date"] == "2025-01-31"
        assert result["is_multi_account"] is False

    def test_no_account_raises(self):
        with pytest.raises(ValueError, match="Either portfolio or account"):
            CostAnalyzer()
