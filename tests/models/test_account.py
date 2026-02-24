"""Tests for Account and CashBalance models"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass, BuySell, Trade


@pytest.fixture
def sample_cash_balance() -> CashBalance:
    """Create a sample cash balance."""
    return CashBalance(
        currency="USD",
        starting_cash=Decimal("10000.00"),
        ending_cash=Decimal("11000.00"),
        ending_settled_cash=Decimal("10500.00"),
        deposits=Decimal("2000.00"),
        withdrawals=Decimal("500.00"),
        dividends=Decimal("100.00"),
        interest=Decimal("50.00"),
        commissions=Decimal("-25.00"),
        fees=Decimal("-10.00"),
        net_trades_sales=Decimal("5000.00"),
        net_trades_purchases=Decimal("-4000.00"),
    )


@pytest.fixture
def sample_position() -> Position:
    """Create a sample position."""
    return Position(
        account_id="U1234567",
        symbol="AAPL",
        asset_class=AssetClass.STOCK,
        quantity=Decimal("100"),
        mark_price=Decimal("150.00"),
        position_value=Decimal("15000.00"),
        average_cost=Decimal("120.00"),
        cost_basis=Decimal("12000.00"),
        unrealized_pnl=Decimal("3000.00"),
        position_date=date(2025, 6, 30),
    )


@pytest.fixture
def sample_trade() -> Trade:
    """Create a sample trade."""
    return Trade(
        account_id="U1234567",
        trade_id="T001",
        trade_date=date(2025, 1, 15),
        symbol="AAPL",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.BUY,
        quantity=Decimal("100"),
        trade_price=Decimal("120.00"),
        trade_money=Decimal("-12000.00"),
        ib_commission=Decimal("-1.50"),
        fifo_pnl_realized=Decimal("500.00"),
    )


@pytest.fixture
def sample_account(
    sample_cash_balance: CashBalance,
    sample_position: Position,
    sample_trade: Trade,
) -> Account:
    """Create a sample account with positions and trades."""
    return Account(
        account_id="U1234567",
        account_alias="Test Account",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 6, 30),
        cash_balances=[sample_cash_balance],
        positions=[sample_position],
        trades=[sample_trade],
    )


class TestCashBalance:
    """Tests for CashBalance model"""

    def test_creation(self, sample_cash_balance: CashBalance) -> None:
        assert sample_cash_balance.currency == "USD"
        assert sample_cash_balance.starting_cash == Decimal("10000.00")
        assert sample_cash_balance.ending_cash == Decimal("11000.00")

    def test_default_values(self) -> None:
        balance = CashBalance(
            currency="USD",
            starting_cash=Decimal("10000.00"),
            ending_cash=Decimal("11000.00"),
            ending_settled_cash=Decimal("10500.00"),
        )
        assert balance.deposits == Decimal("0")
        assert balance.withdrawals == Decimal("0")
        assert balance.dividends == Decimal("0")
        assert balance.interest == Decimal("0")
        assert balance.commissions == Decimal("0")
        assert balance.fees == Decimal("0")
        assert balance.net_trades_sales == Decimal("0")
        assert balance.net_trades_purchases == Decimal("0")

    def test_decimal_conversion(self) -> None:
        balance = CashBalance(
            currency="USD",
            starting_cash=10000,
            ending_cash="11000.50",
            ending_settled_cash=10500.25,
            deposits="2000",
            withdrawals=500,
        )
        assert isinstance(balance.starting_cash, Decimal)
        assert isinstance(balance.ending_cash, Decimal)
        assert isinstance(balance.ending_settled_cash, Decimal)
        assert isinstance(balance.deposits, Decimal)
        assert isinstance(balance.withdrawals, Decimal)

    def test_net_change(self, sample_cash_balance: CashBalance) -> None:
        # 11000 - 10000 = 1000
        assert sample_cash_balance.net_change == Decimal("1000.00")

    def test_total_deposits_withdrawals(self, sample_cash_balance: CashBalance) -> None:
        # 2000 - 500 = 1500
        assert sample_cash_balance.total_deposits_withdrawals == Decimal("1500.00")

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            CashBalance(
                currency="USD",
                starting_cash=Decimal("10000"),
                # missing ending_cash and ending_settled_cash
            )


class TestAccount:
    """Tests for Account model"""

    def test_creation(self, sample_account: Account) -> None:
        assert sample_account.account_id == "U1234567"
        assert sample_account.account_alias == "Test Account"
        assert sample_account.from_date == date(2025, 1, 1)
        assert sample_account.to_date == date(2025, 6, 30)
        assert sample_account.base_currency == "USD"

    def test_default_fields(self) -> None:
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 6, 30),
        )
        assert account.account_alias is None
        assert account.account_type is None
        assert account.ib_entity is None
        assert account.cash_balances == []
        assert account.positions == []
        assert account.trades == []
        assert account.base_currency == "USD"

    def test_total_cash(self, sample_account: Account) -> None:
        assert sample_account.total_cash == Decimal("11000.00")

    def test_total_position_value(self, sample_account: Account) -> None:
        assert sample_account.total_position_value == Decimal("15000.00")

    def test_total_value(self, sample_account: Account) -> None:
        # cash 11000 + positions 15000 = 26000
        assert sample_account.total_value == Decimal("26000.00")

    def test_total_unrealized_pnl(self, sample_account: Account) -> None:
        assert sample_account.total_unrealized_pnl == Decimal("3000.00")

    def test_total_realized_pnl(self, sample_account: Account) -> None:
        assert sample_account.total_realized_pnl == Decimal("500.00")

    def test_total_commissions(self, sample_account: Account) -> None:
        assert sample_account.total_commissions == Decimal("1.50")

    def test_trade_count(self, sample_account: Account) -> None:
        assert sample_account.trade_count == 1

    def test_position_count(self, sample_account: Account) -> None:
        assert sample_account.position_count == 1

    def test_empty_account(self) -> None:
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 6, 30),
        )
        assert account.total_cash == Decimal("0")
        assert account.total_position_value == Decimal("0")
        assert account.total_value == Decimal("0")
        assert account.total_unrealized_pnl == Decimal("0")
        assert account.total_realized_pnl == Decimal("0")
        assert account.total_commissions == Decimal("0")
        assert account.trade_count == 0
        assert account.position_count == 0


class TestAccountMethods:
    """Tests for Account query methods"""

    def test_get_trades_by_symbol(self, sample_account: Account) -> None:
        trades = sample_account.get_trades_by_symbol("AAPL")
        assert len(trades) == 1
        assert trades[0].symbol == "AAPL"

    def test_get_trades_by_symbol_not_found(self, sample_account: Account) -> None:
        trades = sample_account.get_trades_by_symbol("TSLA")
        assert trades == []

    def test_get_position_by_symbol(self, sample_account: Account) -> None:
        position = sample_account.get_position_by_symbol("AAPL")
        assert position is not None
        assert position.symbol == "AAPL"

    def test_get_position_by_symbol_not_found(self, sample_account: Account) -> None:
        position = sample_account.get_position_by_symbol("TSLA")
        assert position is None

    def test_get_cash_balance(self, sample_account: Account) -> None:
        balance = sample_account.get_cash_balance("USD")
        assert balance is not None
        assert balance.currency == "USD"

    def test_get_cash_balance_not_found(self, sample_account: Account) -> None:
        balance = sample_account.get_cash_balance("JPY")
        assert balance is None

    def test_get_cash_balance_default(self, sample_account: Account) -> None:
        balance = sample_account.get_cash_balance()
        assert balance is not None
        assert balance.currency == "USD"
