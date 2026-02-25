"""Tests for Trade model, BuySell enum, and AssetClass enum"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ib_sec_mcp.models.trade import AssetClass, BuySell, Trade


class TestBuySell:
    """Tests for BuySell enum"""

    def test_buy_value(self) -> None:
        assert BuySell.BUY == "BUY"
        assert BuySell.BUY.value == "BUY"

    def test_sell_value(self) -> None:
        assert BuySell.SELL == "SELL"
        assert BuySell.SELL.value == "SELL"

    def test_from_string(self) -> None:
        assert BuySell("BUY") is BuySell.BUY
        assert BuySell("SELL") is BuySell.SELL

    def test_invalid_value(self) -> None:
        with pytest.raises(ValueError):
            BuySell("HOLD")


class TestAssetClass:
    """Tests for AssetClass enum"""

    def test_all_values(self) -> None:
        assert AssetClass.STOCK.value == "STK"
        assert AssetClass.BOND.value == "BOND"
        assert AssetClass.OPTION.value == "OPT"
        assert AssetClass.FUTURE.value == "FUT"
        assert AssetClass.FOREX.value == "CASH"
        assert AssetClass.FUND.value == "FUND"
        assert AssetClass.OTHER.value == "OTHER"

    def test_from_string(self) -> None:
        assert AssetClass("STK") is AssetClass.STOCK
        assert AssetClass("BOND") is AssetClass.BOND

    def test_invalid_value(self) -> None:
        with pytest.raises(ValueError):
            AssetClass("INVALID")


@pytest.fixture
def sample_trade() -> Trade:
    """Create a sample trade for testing."""
    return Trade(
        account_id="U1234567",
        trade_id="T001",
        trade_date=date(2025, 1, 15),
        settle_date=date(2025, 1, 17),
        symbol="AAPL",
        description="APPLE INC",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.BUY,
        quantity=Decimal("100"),
        trade_price=Decimal("150.50"),
        trade_money=Decimal("-15050.00"),
        currency="USD",
        fx_rate_to_base=Decimal("1.0"),
        ib_commission=Decimal("-1.50"),
        fifo_pnl_realized=Decimal("500.00"),
        mtm_pnl=Decimal("200.00"),
    )


class TestTradeCreation:
    """Tests for Trade model creation"""

    def test_required_fields(self, sample_trade: Trade) -> None:
        assert sample_trade.account_id == "U1234567"
        assert sample_trade.trade_id == "T001"
        assert sample_trade.trade_date == date(2025, 1, 15)
        assert sample_trade.symbol == "AAPL"
        assert sample_trade.asset_class == AssetClass.STOCK
        assert sample_trade.buy_sell == BuySell.BUY

    def test_optional_fields_default_none(self) -> None:
        trade = Trade(
            account_id="U1234567",
            trade_id="T001",
            trade_date=date(2025, 1, 15),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.BUY,
            quantity=Decimal("100"),
            trade_price=Decimal("150.00"),
            trade_money=Decimal("-15000.00"),
        )
        assert trade.settle_date is None
        assert trade.open_date is None
        assert trade.description is None
        assert trade.cusip is None
        assert trade.isin is None
        assert trade.order_id is None
        assert trade.execution_id is None
        assert trade.order_time is None
        assert trade.notes is None

    def test_open_date_field(self) -> None:
        trade = Trade(
            account_id="U1234567",
            trade_id="T001",
            trade_date=date(2025, 1, 15),
            settle_date=date(2025, 1, 17),
            open_date=date(2024, 6, 1),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.SELL,
            quantity=Decimal("100"),
            trade_price=Decimal("160.00"),
            trade_money=Decimal("16000.00"),
        )
        assert trade.open_date == date(2024, 6, 1)

    def test_default_decimal_fields(self) -> None:
        trade = Trade(
            account_id="U1234567",
            trade_id="T001",
            trade_date=date(2025, 1, 15),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.BUY,
            quantity=Decimal("100"),
            trade_price=Decimal("150.00"),
            trade_money=Decimal("-15000.00"),
        )
        assert trade.fx_rate_to_base == Decimal("1.0")
        assert trade.ib_commission == Decimal("0")
        assert trade.fifo_pnl_realized == Decimal("0")
        assert trade.mtm_pnl == Decimal("0")

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            Trade(
                account_id="U1234567",
                trade_id="T001",
                # missing trade_date
                symbol="AAPL",
                asset_class=AssetClass.STOCK,
                buy_sell=BuySell.BUY,
                quantity=Decimal("100"),
                trade_price=Decimal("150.00"),
                trade_money=Decimal("-15000.00"),
            )

    def test_order_time_datetime(self) -> None:
        order_time = datetime(2025, 1, 15, 10, 30, 0)
        trade = Trade(
            account_id="U1234567",
            trade_id="T001",
            trade_date=date(2025, 1, 15),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.BUY,
            quantity=Decimal("100"),
            trade_price=Decimal("150.00"),
            trade_money=Decimal("-15000.00"),
            order_time=order_time,
        )
        assert trade.order_time == order_time


class TestTradeDecimalConversion:
    """Tests for field_validator decimal conversion"""

    def test_int_to_decimal(self) -> None:
        trade = Trade(
            account_id="U1234567",
            trade_id="T001",
            trade_date=date(2025, 1, 15),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.BUY,
            quantity=100,
            trade_price=150,
            trade_money=Decimal("-15000.00"),
        )
        assert isinstance(trade.quantity, Decimal)
        assert trade.quantity == Decimal("100")
        assert isinstance(trade.trade_price, Decimal)
        assert trade.trade_price == Decimal("150")

    def test_float_to_decimal(self) -> None:
        trade = Trade(
            account_id="U1234567",
            trade_id="T001",
            trade_date=date(2025, 1, 15),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.BUY,
            quantity=100.5,
            trade_price=150.25,
            trade_money=Decimal("-15000.00"),
        )
        assert isinstance(trade.quantity, Decimal)
        assert isinstance(trade.trade_price, Decimal)

    def test_str_to_decimal(self) -> None:
        trade = Trade(
            account_id="U1234567",
            trade_id="T001",
            trade_date=date(2025, 1, 15),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.BUY,
            quantity="100",
            trade_price="150.50",
            trade_money=Decimal("-15000.00"),
        )
        assert isinstance(trade.quantity, Decimal)
        assert trade.quantity == Decimal("100")
        assert isinstance(trade.trade_price, Decimal)
        assert trade.trade_price == Decimal("150.50")


class TestTradeProperties:
    """Tests for Trade computed properties"""

    def test_gross_amount(self, sample_trade: Trade) -> None:
        assert sample_trade.gross_amount == Decimal("15050.00")

    def test_net_amount(self, sample_trade: Trade) -> None:
        # gross_amount (15050) - abs(commission) (1.50)
        assert sample_trade.net_amount == Decimal("15048.50")

    def test_is_buy(self, sample_trade: Trade) -> None:
        assert sample_trade.is_buy is True
        assert sample_trade.is_sell is False

    def test_is_sell(self) -> None:
        trade = Trade(
            account_id="U1234567",
            trade_id="T002",
            trade_date=date(2025, 1, 20),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.SELL,
            quantity=Decimal("100"),
            trade_price=Decimal("160.00"),
            trade_money=Decimal("16000.00"),
        )
        assert trade.is_sell is True
        assert trade.is_buy is False

    def test_commission_rate(self, sample_trade: Trade) -> None:
        # abs(1.50) / 15050.00 * 100
        expected = Decimal("1.50") / Decimal("15050.00") * 100
        assert sample_trade.commission_rate == expected

    def test_commission_rate_zero_gross(self) -> None:
        trade = Trade(
            account_id="U1234567",
            trade_id="T001",
            trade_date=date(2025, 1, 15),
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.BUY,
            quantity=Decimal("100"),
            trade_price=Decimal("150.00"),
            trade_money=Decimal("0"),
        )
        assert trade.commission_rate == Decimal("0")
