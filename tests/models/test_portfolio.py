"""Tests for Portfolio model"""

from datetime import date
from decimal import Decimal

import pytest

from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.portfolio import Portfolio
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass, BuySell, Trade


def _make_position(
    account_id: str, symbol: str, quantity: Decimal, value: Decimal, pnl: Decimal
) -> Position:
    """Helper to create a Position."""
    return Position(
        account_id=account_id,
        symbol=symbol,
        asset_class=AssetClass.STOCK,
        quantity=quantity,
        mark_price=value / quantity if quantity else Decimal("0"),
        position_value=value,
        average_cost=Decimal("100.00"),
        cost_basis=Decimal("100.00") * quantity,
        unrealized_pnl=pnl,
        position_date=date(2025, 6, 30),
    )


def _make_trade(
    account_id: str, symbol: str, pnl: Decimal, commission: Decimal = Decimal("-1.00")
) -> Trade:
    """Helper to create a Trade."""
    return Trade(
        account_id=account_id,
        trade_id=f"T-{account_id}-{symbol}",
        trade_date=date(2025, 3, 15),
        symbol=symbol,
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.BUY,
        quantity=Decimal("10"),
        trade_price=Decimal("100.00"),
        trade_money=Decimal("-1000.00"),
        ib_commission=commission,
        fifo_pnl_realized=pnl,
    )


@pytest.fixture
def two_account_portfolio() -> Portfolio:
    """Create a portfolio with two accounts."""
    account1 = Account(
        account_id="U1111111",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 6, 30),
        cash_balances=[
            CashBalance(
                currency="USD",
                starting_cash=Decimal("5000"),
                ending_cash=Decimal("6000"),
                ending_settled_cash=Decimal("6000"),
            )
        ],
        positions=[
            _make_position("U1111111", "AAPL", Decimal("50"), Decimal("7500"), Decimal("500")),
            _make_position("U1111111", "TSLA", Decimal("20"), Decimal("4000"), Decimal("200")),
        ],
        trades=[
            _make_trade("U1111111", "AAPL", Decimal("300")),
            _make_trade("U1111111", "TSLA", Decimal("-100")),
        ],
    )

    account2 = Account(
        account_id="U2222222",
        from_date=date(2025, 2, 1),
        to_date=date(2025, 5, 31),
        cash_balances=[
            CashBalance(
                currency="USD",
                starting_cash=Decimal("3000"),
                ending_cash=Decimal("4000"),
                ending_settled_cash=Decimal("4000"),
            )
        ],
        positions=[
            _make_position("U2222222", "AAPL", Decimal("30"), Decimal("4500"), Decimal("300")),
        ],
        trades=[
            _make_trade("U2222222", "AAPL", Decimal("150")),
        ],
    )

    return Portfolio.from_accounts([account1, account2])


class TestPortfolioCreation:
    """Tests for Portfolio creation"""

    def test_from_accounts(self, two_account_portfolio: Portfolio) -> None:
        assert two_account_portfolio.account_count == 2
        assert two_account_portfolio.base_currency == "USD"

    def test_from_accounts_date_range(self, two_account_portfolio: Portfolio) -> None:
        # min from_date and max to_date
        assert two_account_portfolio.from_date == date(2025, 1, 1)
        assert two_account_portfolio.to_date == date(2025, 6, 30)

    def test_from_accounts_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="At least one account is required"):
            Portfolio.from_accounts([])

    def test_from_accounts_custom_currency(self) -> None:
        account = Account(
            account_id="U1111111",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 6, 30),
        )
        portfolio = Portfolio.from_accounts([account], base_currency="JPY")
        assert portfolio.base_currency == "JPY"


class TestPortfolioProperties:
    """Tests for Portfolio aggregated properties"""

    def test_total_value(self, two_account_portfolio: Portfolio) -> None:
        # account1: cash 6000 + positions 11500 = 17500
        # account2: cash 4000 + positions 4500 = 8500
        assert two_account_portfolio.total_value == Decimal("26000")

    def test_total_cash(self, two_account_portfolio: Portfolio) -> None:
        assert two_account_portfolio.total_cash == Decimal("10000")

    def test_total_position_value(self, two_account_portfolio: Portfolio) -> None:
        # 7500 + 4000 + 4500 = 16000
        assert two_account_portfolio.total_position_value == Decimal("16000")

    def test_total_unrealized_pnl(self, two_account_portfolio: Portfolio) -> None:
        # 500 + 200 + 300 = 1000
        assert two_account_portfolio.total_unrealized_pnl == Decimal("1000")

    def test_total_realized_pnl(self, two_account_portfolio: Portfolio) -> None:
        # 300 + (-100) + 150 = 350
        assert two_account_portfolio.total_realized_pnl == Decimal("350")

    def test_total_commissions(self, two_account_portfolio: Portfolio) -> None:
        # 3 trades * 1.00 = 3.00
        assert two_account_portfolio.total_commissions == Decimal("3.00")

    def test_total_trades(self, two_account_portfolio: Portfolio) -> None:
        assert two_account_portfolio.total_trades == 3

    def test_total_positions(self, two_account_portfolio: Portfolio) -> None:
        assert two_account_portfolio.total_positions == 3

    def test_all_trades(self, two_account_portfolio: Portfolio) -> None:
        trades = two_account_portfolio.all_trades
        assert len(trades) == 3

    def test_all_positions(self, two_account_portfolio: Portfolio) -> None:
        positions = two_account_portfolio.all_positions
        assert len(positions) == 3


class TestPortfolioMethods:
    """Tests for Portfolio query methods"""

    def test_get_account(self, two_account_portfolio: Portfolio) -> None:
        account = two_account_portfolio.get_account("U1111111")
        assert account is not None
        assert account.account_id == "U1111111"

    def test_get_account_not_found(self, two_account_portfolio: Portfolio) -> None:
        assert two_account_portfolio.get_account("U9999999") is None

    def test_get_positions_by_symbol(self, two_account_portfolio: Portfolio) -> None:
        # AAPL in both accounts
        positions = two_account_portfolio.get_positions_by_symbol("AAPL")
        assert len(positions) == 2

    def test_get_positions_by_symbol_single(self, two_account_portfolio: Portfolio) -> None:
        # TSLA only in account1
        positions = two_account_portfolio.get_positions_by_symbol("TSLA")
        assert len(positions) == 1

    def test_get_positions_by_symbol_not_found(self, two_account_portfolio: Portfolio) -> None:
        positions = two_account_portfolio.get_positions_by_symbol("GOOGL")
        assert positions == []

    def test_get_trades_by_symbol(self, two_account_portfolio: Portfolio) -> None:
        # AAPL trades in both accounts
        trades = two_account_portfolio.get_trades_by_symbol("AAPL")
        assert len(trades) == 2

    def test_get_trades_by_symbol_not_found(self, two_account_portfolio: Portfolio) -> None:
        trades = two_account_portfolio.get_trades_by_symbol("GOOGL")
        assert trades == []

    def test_get_symbols(self, two_account_portfolio: Portfolio) -> None:
        symbols = two_account_portfolio.get_symbols()
        assert sorted(symbols) == ["AAPL", "TSLA"]

    def test_aggregate_positions_by_symbol(self, two_account_portfolio: Portfolio) -> None:
        aggregated = two_account_portfolio.aggregate_positions_by_symbol()
        assert aggregated["AAPL"] == Decimal("80")  # 50 + 30
        assert aggregated["TSLA"] == Decimal("20")
