"""Tests for MultiAccountAggregator"""

from datetime import date
from decimal import Decimal

from ib_sec_mcp.core.aggregator import MultiAccountAggregator
from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.portfolio import Portfolio
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass, BuySell, Trade

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

FROM_DATE = date(2025, 1, 1)
TO_DATE = date(2025, 1, 31)
POS_DATE = date(2025, 1, 31)


def make_position(
    account_id: str,
    symbol: str,
    asset_class: AssetClass = AssetClass.STOCK,
    quantity: str = "10",
    position_value: str = "1500",
    unrealized_pnl: str = "100",
) -> Position:
    return Position(
        account_id=account_id,
        symbol=symbol,
        description=f"{symbol} Inc",
        asset_class=asset_class,
        quantity=Decimal(quantity),
        mark_price=Decimal("150"),
        position_value=Decimal(position_value),
        average_cost=Decimal("140"),
        cost_basis=Decimal("1400"),
        unrealized_pnl=Decimal(unrealized_pnl),
        currency="USD",
        fx_rate_to_base=Decimal("1"),
        position_date=POS_DATE,
    )


def make_trade(
    account_id: str,
    symbol: str,
    asset_class: AssetClass = AssetClass.STOCK,
    buy_sell: BuySell = BuySell.BUY,
    trade_money: str = "-1500",
    commission: str = "-1.00",
    realized_pnl: str = "0",
) -> Trade:
    return Trade(
        account_id=account_id,
        trade_id=f"T-{account_id}-{symbol}",
        trade_date=date(2025, 1, 15),
        symbol=symbol,
        asset_class=asset_class,
        buy_sell=buy_sell,
        quantity=Decimal("10"),
        trade_price=Decimal("150"),
        trade_money=Decimal(trade_money),
        ib_commission=Decimal(commission),
        fifo_pnl_realized=Decimal(realized_pnl),
    )


def make_cash_balance(amount: str = "1000") -> CashBalance:
    return CashBalance(
        currency="USD",
        starting_cash=Decimal(amount),
        ending_cash=Decimal(amount),
        ending_settled_cash=Decimal(amount),
    )


def make_account(
    account_id: str,
    positions: list[Position] | None = None,
    trades: list[Trade] | None = None,
    cash: str = "1000",
) -> Account:
    return Account(
        account_id=account_id,
        from_date=FROM_DATE,
        to_date=TO_DATE,
        cash_balances=[make_cash_balance(cash)],
        positions=positions or [],
        trades=trades or [],
    )


# ---------------------------------------------------------------------------
# TestCreatePortfolio
# ---------------------------------------------------------------------------


class TestCreatePortfolio:
    def test_create_portfolio_single_account(self) -> None:
        account = make_account("U1111111")
        portfolio = MultiAccountAggregator.create_portfolio([account])
        assert isinstance(portfolio, Portfolio)
        assert len(portfolio.accounts) == 1
        assert portfolio.accounts[0].account_id == "U1111111"

    def test_create_portfolio_multiple_accounts(self) -> None:
        accounts = [make_account("U1111111"), make_account("U2222222")]
        portfolio = MultiAccountAggregator.create_portfolio(accounts)
        assert len(portfolio.accounts) == 2

    def test_create_portfolio_date_range(self) -> None:
        account_a = make_account("U1111111")
        account_b = Account(
            account_id="U2222222",
            from_date=date(2024, 12, 1),
            to_date=date(2025, 2, 28),
            cash_balances=[make_cash_balance()],
        )
        portfolio = MultiAccountAggregator.create_portfolio([account_a, account_b])
        # Should use earliest from_date and latest to_date
        assert portfolio.from_date == date(2024, 12, 1)
        assert portfolio.to_date == date(2025, 2, 28)


# ---------------------------------------------------------------------------
# TestAggregateTradesBySymbol
# ---------------------------------------------------------------------------


class TestAggregateTradesBySymbol:
    def test_single_account_trades(self) -> None:
        trades = [make_trade("U1111111", "AAPL"), make_trade("U1111111", "MSFT")]
        account = make_account("U1111111", trades=trades)
        portfolio = Portfolio.from_accounts([account])

        result = MultiAccountAggregator.aggregate_trades_by_symbol(portfolio)
        assert set(result.keys()) == {"AAPL", "MSFT"}
        assert len(result["AAPL"]) == 1
        assert len(result["MSFT"]) == 1

    def test_multi_account_same_symbol(self) -> None:
        trade_a = make_trade("U1111111", "AAPL")
        trade_b = make_trade("U2222222", "AAPL")
        account_a = make_account("U1111111", trades=[trade_a])
        account_b = make_account("U2222222", trades=[trade_b])
        portfolio = Portfolio.from_accounts([account_a, account_b])

        result = MultiAccountAggregator.aggregate_trades_by_symbol(portfolio)
        assert len(result["AAPL"]) == 2

    def test_empty_portfolio_no_trades(self) -> None:
        account = make_account("U1111111")
        portfolio = Portfolio.from_accounts([account])
        result = MultiAccountAggregator.aggregate_trades_by_symbol(portfolio)
        assert result == {}


# ---------------------------------------------------------------------------
# TestAggregatePositionsBySymbol
# ---------------------------------------------------------------------------


class TestAggregatePositionsBySymbol:
    def test_single_account_positions(self) -> None:
        positions = [make_position("U1111111", "AAPL"), make_position("U1111111", "MSFT")]
        account = make_account("U1111111", positions=positions)
        portfolio = Portfolio.from_accounts([account])

        result = MultiAccountAggregator.aggregate_positions_by_symbol(portfolio)
        assert set(result.keys()) == {"AAPL", "MSFT"}

    def test_multi_account_same_symbol(self) -> None:
        pos_a = make_position("U1111111", "AAPL")
        pos_b = make_position("U2222222", "AAPL")
        account_a = make_account("U1111111", positions=[pos_a])
        account_b = make_account("U2222222", positions=[pos_b])
        portfolio = Portfolio.from_accounts([account_a, account_b])

        result = MultiAccountAggregator.aggregate_positions_by_symbol(portfolio)
        assert len(result["AAPL"]) == 2

    def test_empty_portfolio_no_positions(self) -> None:
        account = make_account("U1111111")
        portfolio = Portfolio.from_accounts([account])
        result = MultiAccountAggregator.aggregate_positions_by_symbol(portfolio)
        assert result == {}


# ---------------------------------------------------------------------------
# TestCalculateTotalPositionBySymbol
# ---------------------------------------------------------------------------


class TestCalculateTotalPositionBySymbol:
    def test_single_account_totals(self) -> None:
        position = make_position(
            "U1111111", "AAPL", quantity="10", position_value="1500", unrealized_pnl="100"
        )
        account = make_account("U1111111", positions=[position])
        portfolio = Portfolio.from_accounts([account])

        result = MultiAccountAggregator.calculate_total_position_by_symbol(portfolio)
        qty, value, pnl = result["AAPL"]
        assert qty == Decimal("10")
        assert value == Decimal("1500")
        assert pnl == Decimal("100")

    def test_multi_account_aggregation(self) -> None:
        pos_a = make_position(
            "U1111111", "AAPL", quantity="10", position_value="1500", unrealized_pnl="100"
        )
        pos_b = make_position(
            "U2222222", "AAPL", quantity="5", position_value="750", unrealized_pnl="50"
        )
        account_a = make_account("U1111111", positions=[pos_a])
        account_b = make_account("U2222222", positions=[pos_b])
        portfolio = Portfolio.from_accounts([account_a, account_b])

        result = MultiAccountAggregator.calculate_total_position_by_symbol(portfolio)
        qty, value, pnl = result["AAPL"]
        assert qty == Decimal("15")
        assert value == Decimal("2250")
        assert pnl == Decimal("150")


# ---------------------------------------------------------------------------
# TestCalculateTotalTradesBySymbol
# ---------------------------------------------------------------------------


class TestCalculateTotalTradesBySymbol:
    def test_single_account_trade_totals(self) -> None:
        trade = make_trade(
            "U1111111", "AAPL", trade_money="-1500", commission="-1.00", realized_pnl="0"
        )
        account = make_account("U1111111", trades=[trade])
        portfolio = Portfolio.from_accounts([account])

        result = MultiAccountAggregator.calculate_total_trades_by_symbol(portfolio)
        count, volume, pnl = result["AAPL"]
        assert count == 1
        assert volume == Decimal("1500")  # abs(-1500)
        assert pnl == Decimal("0")

    def test_multi_account_trade_aggregation(self) -> None:
        trade_a = make_trade("U1111111", "AAPL", realized_pnl="50")
        trade_b = make_trade("U2222222", "AAPL", realized_pnl="30")
        account_a = make_account("U1111111", trades=[trade_a])
        account_b = make_account("U2222222", trades=[trade_b])
        portfolio = Portfolio.from_accounts([account_a, account_b])

        result = MultiAccountAggregator.calculate_total_trades_by_symbol(portfolio)
        count, volume, pnl = result["AAPL"]
        assert count == 2
        assert pnl == Decimal("80")


# ---------------------------------------------------------------------------
# TestAggregateByAssetClass
# ---------------------------------------------------------------------------


class TestAggregateByAssetClass:
    def test_stock_and_bond_positions(self) -> None:
        stock_pos = make_position(
            "U1111111",
            "AAPL",
            asset_class=AssetClass.STOCK,
            position_value="1500",
            unrealized_pnl="100",
        )
        bond_pos = make_position(
            "U1111111",
            "T 4.5 25",
            asset_class=AssetClass.BOND,
            position_value="5000",
            unrealized_pnl="-50",
        )
        account = make_account("U1111111", positions=[stock_pos, bond_pos])
        portfolio = Portfolio.from_accounts([account])

        result = MultiAccountAggregator.aggregate_by_asset_class(portfolio)
        assert AssetClass.STOCK.value in result
        assert AssetClass.BOND.value in result
        assert result[AssetClass.STOCK.value]["position_value"] == Decimal("1500")
        assert result[AssetClass.BOND.value]["position_value"] == Decimal("5000")

    def test_trade_commissions_aggregated(self) -> None:
        trade = make_trade(
            "U1111111", "AAPL", asset_class=AssetClass.STOCK, commission="-2.50", realized_pnl="100"
        )
        account = make_account("U1111111", trades=[trade])
        portfolio = Portfolio.from_accounts([account])

        result = MultiAccountAggregator.aggregate_by_asset_class(portfolio)
        assert result[AssetClass.STOCK.value]["commissions"] == Decimal("2.50")
        assert result[AssetClass.STOCK.value]["realized_pnl"] == Decimal("100")
        assert result[AssetClass.STOCK.value]["trade_count"] == Decimal("1")

    def test_empty_portfolio(self) -> None:
        account = make_account("U1111111")
        portfolio = Portfolio.from_accounts([account])
        result = MultiAccountAggregator.aggregate_by_asset_class(portfolio)
        assert result == {}


# ---------------------------------------------------------------------------
# TestAggregateByAccount
# ---------------------------------------------------------------------------


class TestAggregateByAccount:
    def test_multi_account_metrics(self) -> None:
        pos = make_position("U1111111", "AAPL", position_value="1500", unrealized_pnl="100")
        trade = make_trade("U1111111", "AAPL", commission="-1.00", realized_pnl="50")
        account = make_account("U1111111", positions=[pos], trades=[trade], cash="500")
        portfolio = Portfolio.from_accounts([account])

        result = MultiAccountAggregator.aggregate_by_account(portfolio)
        assert "U1111111" in result
        metrics = result["U1111111"]
        assert metrics["position_value"] == Decimal("1500")
        assert metrics["unrealized_pnl"] == Decimal("100")
        assert metrics["realized_pnl"] == Decimal("50")
        assert metrics["commissions"] == Decimal("1.00")
        assert metrics["trade_count"] == Decimal("1")
        assert metrics["position_count"] == Decimal("1")


# ---------------------------------------------------------------------------
# TestCalculateAccountAllocation
# ---------------------------------------------------------------------------


class TestCalculateAccountAllocation:
    def test_two_accounts_sum_to_100(self) -> None:
        pos_a = make_position("U1111111", "AAPL", position_value="3000")
        pos_b = make_position("U2222222", "MSFT", position_value="1000")
        account_a = make_account("U1111111", positions=[pos_a], cash="0")
        account_b = make_account("U2222222", positions=[pos_b], cash="0")
        portfolio = Portfolio.from_accounts([account_a, account_b])

        result = MultiAccountAggregator.calculate_account_allocation(portfolio)
        total = sum(result.values())
        assert abs(total - Decimal("100")) < Decimal("0.01")
        assert result["U1111111"] > result["U2222222"]

    def test_zero_total_value_returns_zero(self) -> None:
        account = make_account("U1111111", cash="0")
        portfolio = Portfolio.from_accounts([account])
        result = MultiAccountAggregator.calculate_account_allocation(portfolio)
        assert result["U1111111"] == Decimal("0")


# ---------------------------------------------------------------------------
# TestCalculateSymbolAllocation
# ---------------------------------------------------------------------------


class TestCalculateSymbolAllocation:
    def test_multi_symbol_allocation(self) -> None:
        pos_a = make_position("U1111111", "AAPL", position_value="3000")
        pos_b = make_position("U1111111", "MSFT", position_value="1000")
        account = make_account("U1111111", positions=[pos_a, pos_b], cash="0")
        portfolio = Portfolio.from_accounts([account])

        result = MultiAccountAggregator.calculate_symbol_allocation(portfolio)
        assert "AAPL" in result
        assert "MSFT" in result
        total = sum(result.values())
        assert abs(total - Decimal("100")) < Decimal("0.01")
        assert result["AAPL"] > result["MSFT"]

    def test_zero_position_value_returns_empty(self) -> None:
        account = make_account("U1111111")
        portfolio = Portfolio.from_accounts([account])
        result = MultiAccountAggregator.calculate_symbol_allocation(portfolio)
        assert result == {}
