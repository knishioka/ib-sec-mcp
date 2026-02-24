"""Tests for performance analyzer"""

from datetime import date
from decimal import Decimal

import pytest

from ib_sec_mcp.analyzers.performance import PerformanceAnalyzer
from ib_sec_mcp.models.account import Account
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass, BuySell, Trade


@pytest.fixture
def winning_trade():
    """A single winning trade."""
    return Trade(
        account_id="U1234567",
        trade_id="100001",
        trade_date=date(2025, 1, 10),
        settle_date=date(2025, 1, 12),
        symbol="AAPL",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.SELL,
        quantity=Decimal("10"),
        trade_price=Decimal("160"),
        trade_money=Decimal("1600"),
        ib_commission=Decimal("-1.50"),
        fifo_pnl_realized=Decimal("100"),
    )


@pytest.fixture
def losing_trade():
    """A single losing trade."""
    return Trade(
        account_id="U1234567",
        trade_id="100002",
        trade_date=date(2025, 1, 15),
        settle_date=date(2025, 1, 17),
        symbol="MSFT",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.SELL,
        quantity=Decimal("5"),
        trade_price=Decimal("380"),
        trade_money=Decimal("1900"),
        ib_commission=Decimal("-2.00"),
        fifo_pnl_realized=Decimal("-50"),
    )


@pytest.fixture
def zero_pnl_trade():
    """A trade with zero realized PnL (e.g., opening position)."""
    return Trade(
        account_id="U1234567",
        trade_id="100003",
        trade_date=date(2025, 1, 20),
        settle_date=date(2025, 1, 22),
        symbol="GOOG",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.BUY,
        quantity=Decimal("3"),
        trade_price=Decimal("175"),
        trade_money=Decimal("-525"),
        ib_commission=Decimal("-1.00"),
        fifo_pnl_realized=Decimal("0"),
    )


@pytest.fixture
def sample_position():
    """A sample stock position."""
    return Position(
        account_id="U1234567",
        symbol="AAPL",
        description="Apple Inc",
        asset_class=AssetClass.STOCK,
        quantity=Decimal("10"),
        mark_price=Decimal("150"),
        position_value=Decimal("1500"),
        average_cost=Decimal("120"),
        cost_basis=Decimal("1200"),
        unrealized_pnl=Decimal("300"),
        currency="USD",
        fx_rate_to_base=Decimal("1"),
        position_date=date(2025, 1, 31),
    )


@pytest.fixture
def mixed_account(winning_trade, losing_trade, zero_pnl_trade, sample_position):
    """Account with a mix of winning, losing, and zero-PnL trades."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        trades=[winning_trade, losing_trade, zero_pnl_trade],
        positions=[sample_position],
    )


@pytest.fixture
def empty_account():
    """Account with no trades or positions."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        trades=[],
        positions=[],
    )


@pytest.fixture
def all_winning_account():
    """Account where every trade is a winner."""
    trades = [
        Trade(
            account_id="U1234567",
            trade_id=f"W{i}",
            trade_date=date(2025, 1, 5 + i),
            settle_date=date(2025, 1, 7 + i),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.SELL,
            quantity=Decimal("10"),
            trade_price=Decimal("160"),
            trade_money=Decimal("1600"),
            ib_commission=Decimal("-1.00"),
            fifo_pnl_realized=Decimal(str(50 + i * 10)),
        )
        for i in range(3)
    ]
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        trades=trades,
        positions=[],
    )


@pytest.fixture
def all_losing_account():
    """Account where every trade is a loser."""
    trades = [
        Trade(
            account_id="U1234567",
            trade_id=f"L{i}",
            trade_date=date(2025, 1, 5 + i),
            settle_date=date(2025, 1, 7 + i),
            symbol="MSFT",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.SELL,
            quantity=Decimal("5"),
            trade_price=Decimal("380"),
            trade_money=Decimal("1900"),
            ib_commission=Decimal("-2.00"),
            fifo_pnl_realized=Decimal(str(-30 - i * 10)),
        )
        for i in range(3)
    ]
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        trades=trades,
        positions=[],
    )


@pytest.fixture
def multi_symbol_account():
    """Account with trades across multiple symbols."""
    trades = [
        Trade(
            account_id="U1234567",
            trade_id="MS1",
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
            trade_id="MS2",
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
            trade_id="MS3",
            trade_date=date(2025, 1, 12),
            settle_date=date(2025, 1, 14),
            symbol="MSFT",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.SELL,
            quantity=Decimal("5"),
            trade_price=Decimal("400"),
            trade_money=Decimal("2000"),
            ib_commission=Decimal("-2.00"),
            fifo_pnl_realized=Decimal("-25"),
        ),
    ]
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        trades=trades,
        positions=[],
    )


class TestPerformanceAnalyzer:
    """Tests for PerformanceAnalyzer."""

    def test_analyzer_name(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()
        assert result["analyzer"] == "Performance"

    def test_normal_case_metrics(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        assert result["total_trades"] == 3
        assert result["total_positions"] == 1
        # realized: 100 + (-50) + 0 = 50
        assert Decimal(result["total_realized_pnl"]) == Decimal("50")
        # unrealized: 300
        assert Decimal(result["total_unrealized_pnl"]) == Decimal("300")
        # total: 50 + 300 = 350
        assert Decimal(result["total_pnl"]) == Decimal("350")

    def test_win_rate_mixed(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        # 1 win, 1 loss (zero-PnL excluded), so win_rate = 50%
        assert result["winning_trades"] == 1
        assert result["losing_trades"] == 1
        assert Decimal(result["win_rate"]) == Decimal("50")

    def test_profit_factor_mixed(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        # gross profit = 100, gross loss = 50, profit_factor = 2
        assert Decimal(result["profit_factor"]) == Decimal("2")

    def test_avg_win_and_loss(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        assert Decimal(result["avg_win"]) == Decimal("100")
        assert Decimal(result["avg_loss"]) == Decimal("50")

    def test_risk_reward_ratio(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        # avg_win=100, avg_loss=50, ratio=2
        assert Decimal(result["risk_reward_ratio"]) == Decimal("2")

    def test_largest_win_and_loss(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        assert Decimal(result["largest_win"]) == Decimal("100")
        assert Decimal(result["largest_loss"]) == Decimal("50")

    def test_commissions_and_volume(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        # commissions: abs(-1.50) + abs(-2.00) + abs(-1.00) = 4.50
        assert Decimal(result["total_commissions"]) == Decimal("4.50")
        # volume: abs(1600) + abs(1900) + abs(-525) = 4025
        assert Decimal(result["total_volume"]) == Decimal("4025")

    def test_trading_frequency(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        assert result["first_trade_date"] == "2025-01-10"
        assert result["last_trade_date"] == "2025-01-20"
        # days: (Jan 20 - Jan 10) + 1 = 11
        assert result["trading_days"] == 11

    def test_empty_account_all_zeros(self, empty_account):
        analyzer = PerformanceAnalyzer(account=empty_account)
        result = analyzer.analyze()

        assert result["total_trades"] == 0
        assert result["total_positions"] == 0
        assert Decimal(result["total_realized_pnl"]) == Decimal("0")
        assert Decimal(result["total_unrealized_pnl"]) == Decimal("0")
        assert Decimal(result["total_pnl"]) == Decimal("0")
        assert result["winning_trades"] == 0
        assert result["losing_trades"] == 0
        assert Decimal(result["win_rate"]) == Decimal("0")
        assert Decimal(result["profit_factor"]) == Decimal("0")
        assert Decimal(result["avg_win"]) == Decimal("0")
        assert Decimal(result["avg_loss"]) == Decimal("0")
        assert Decimal(result["risk_reward_ratio"]) == Decimal("0")
        assert Decimal(result["largest_win"]) == Decimal("0")
        assert Decimal(result["largest_loss"]) == Decimal("0")
        assert result["first_trade_date"] is None
        assert result["last_trade_date"] is None
        assert result["trading_days"] == 0
        assert Decimal(result["trades_per_day"]) == Decimal("0")
        assert result["by_symbol"] == {}

    def test_all_winning_trades(self, all_winning_account):
        analyzer = PerformanceAnalyzer(account=all_winning_account)
        result = analyzer.analyze()

        assert Decimal(result["win_rate"]) == Decimal("100")
        assert Decimal(result["profit_factor"]) == Decimal("999.99")
        assert Decimal(result["avg_loss"]) == Decimal("0")
        assert Decimal(result["largest_loss"]) == Decimal("0")
        assert Decimal(result["risk_reward_ratio"]) == Decimal("999.99")

    def test_all_losing_trades(self, all_losing_account):
        analyzer = PerformanceAnalyzer(account=all_losing_account)
        result = analyzer.analyze()

        assert Decimal(result["win_rate"]) == Decimal("0")
        assert Decimal(result["profit_factor"]) == Decimal("0")
        assert Decimal(result["avg_win"]) == Decimal("0")
        assert Decimal(result["largest_win"]) == Decimal("0")

    def test_single_trade(self, winning_trade):
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=[winning_trade],
            positions=[],
        )
        analyzer = PerformanceAnalyzer(account=account)
        result = analyzer.analyze()

        assert result["total_trades"] == 1
        assert result["winning_trades"] == 1
        assert result["losing_trades"] == 0
        assert Decimal(result["win_rate"]) == Decimal("100")
        # single day: trading_days = 1
        assert result["trading_days"] == 1

    def test_only_zero_pnl_trades(self, zero_pnl_trade):
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=[zero_pnl_trade],
            positions=[],
        )
        analyzer = PerformanceAnalyzer(account=account)
        result = analyzer.analyze()

        assert result["total_trades"] == 1
        assert result["winning_trades"] == 0
        assert result["losing_trades"] == 0
        # total_with_pnl=0 -> win_rate=0
        assert Decimal(result["win_rate"]) == Decimal("0")

    def test_by_symbol_breakdown(self, multi_symbol_account):
        analyzer = PerformanceAnalyzer(account=multi_symbol_account)
        result = analyzer.analyze()

        by_symbol = result["by_symbol"]
        assert "AAPL" in by_symbol
        assert "MSFT" in by_symbol

        aapl = by_symbol["AAPL"]
        assert aapl["trade_count"] == 2
        assert aapl["buy_count"] == 1
        assert aapl["sell_count"] == 1
        assert Decimal(aapl["realized_pnl"]) == Decimal("100")

        msft = by_symbol["MSFT"]
        assert msft["trade_count"] == 1
        assert Decimal(msft["realized_pnl"]) == Decimal("-25")

    def test_by_symbol_avg_prices(self, multi_symbol_account):
        analyzer = PerformanceAnalyzer(account=multi_symbol_account)
        result = analyzer.analyze()

        aapl = result["by_symbol"]["AAPL"]
        assert Decimal(aapl["avg_buy_price"]) == Decimal("150")
        assert Decimal(aapl["avg_sell_price"]) == Decimal("160")
        assert Decimal(aapl["qty_bought"]) == Decimal("10")
        assert Decimal(aapl["qty_sold"]) == Decimal("10")

    def test_decimal_precision_no_float_artifacts(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        # All string-valued numerics should parse cleanly to Decimal
        numeric_keys = [
            "total_realized_pnl",
            "total_unrealized_pnl",
            "total_pnl",
            "win_rate",
            "profit_factor",
            "avg_win",
            "avg_loss",
            "risk_reward_ratio",
            "largest_win",
            "largest_loss",
            "total_commissions",
            "total_volume",
            "commission_rate",
            "trades_per_day",
        ]
        for key in numeric_keys:
            value = Decimal(result[key])
            # No float artifacts like 0.30000000000000004
            reparsed = str(value)
            assert "999999" not in reparsed or key in (
                "profit_factor",
                "risk_reward_ratio",
            )
            assert "000000001" not in reparsed

    def test_commission_rate_calculation(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        total_commissions = Decimal(result["total_commissions"])
        total_volume = Decimal(result["total_volume"])
        commission_rate = Decimal(result["commission_rate"])

        expected_rate = (total_commissions / total_volume) * 100
        assert commission_rate == expected_rate

    def test_metadata_fields(self, mixed_account):
        analyzer = PerformanceAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        assert result["account_id"] == "U1234567"
        assert result["from_date"] == "2025-01-01"
        assert result["to_date"] == "2025-01-31"
        assert result["is_multi_account"] is False
        assert result["timestamp"] is not None

    def test_no_account_raises(self):
        with pytest.raises(ValueError, match="Either portfolio or account"):
            PerformanceAnalyzer()
