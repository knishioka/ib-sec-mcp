"""Tests for Position model"""

from datetime import date
from decimal import Decimal

from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass


class TestPositionCreation:
    """Tests for Position model creation"""

    def test_stock_position(self) -> None:
        position = Position(
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
        assert position.symbol == "AAPL"
        assert position.asset_class == AssetClass.STOCK
        assert position.quantity == Decimal("100")

    def test_bond_position(self) -> None:
        position = Position(
            account_id="U1234567",
            symbol="US912810TD00",
            asset_class=AssetClass.BOND,
            quantity=Decimal("10000"),
            mark_price=Decimal("95.50"),
            position_value=Decimal("9550.00"),
            average_cost=Decimal("90.00"),
            cost_basis=Decimal("9000.00"),
            unrealized_pnl=Decimal("550.00"),
            position_date=date(2025, 6, 30),
            coupon_rate=Decimal("4.5"),
            maturity_date=date(2030, 12, 31),
        )
        assert position.is_bond is True
        assert position.coupon_rate == Decimal("4.5")
        assert position.maturity_date == date(2030, 12, 31)

    def test_default_fields(self) -> None:
        position = Position(
            account_id="U1234567",
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("100"),
            mark_price=Decimal("150.00"),
            position_value=Decimal("15000.00"),
            average_cost=Decimal("120.00"),
            cost_basis=Decimal("12000.00"),
            position_date=date(2025, 6, 30),
        )
        assert position.unrealized_pnl == Decimal("0")
        assert position.realized_pnl == Decimal("0")
        assert position.currency == "USD"
        assert position.fx_rate_to_base == Decimal("1.0")
        assert position.multiplier == Decimal("1")
        assert position.description is None
        assert position.cusip is None
        assert position.isin is None
        assert position.coupon_rate is None
        assert position.maturity_date is None
        assert position.ytm is None
        assert position.duration is None


class TestPositionDecimalConversion:
    """Tests for field_validator decimal conversion"""

    def test_int_conversion(self) -> None:
        position = Position(
            account_id="U1234567",
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            quantity=100,
            mark_price=150,
            position_value=15000,
            average_cost=Decimal("120.00"),
            cost_basis=Decimal("12000.00"),
            position_date=date(2025, 6, 30),
        )
        assert isinstance(position.quantity, Decimal)
        assert isinstance(position.mark_price, Decimal)
        assert isinstance(position.position_value, Decimal)

    def test_str_conversion(self) -> None:
        position = Position(
            account_id="U1234567",
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            quantity="100",
            mark_price="150.50",
            position_value="15050.00",
            average_cost=Decimal("120.00"),
            cost_basis=Decimal("12000.00"),
            position_date=date(2025, 6, 30),
        )
        assert position.quantity == Decimal("100")
        assert position.mark_price == Decimal("150.50")
        assert position.position_value == Decimal("15050.00")


class TestPositionProperties:
    """Tests for Position computed properties"""

    def test_market_value(self) -> None:
        position = Position(
            account_id="U1234567",
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("100"),
            mark_price=Decimal("150.00"),
            position_value=Decimal("15000.00"),
            average_cost=Decimal("120.00"),
            cost_basis=Decimal("12000.00"),
            position_date=date(2025, 6, 30),
        )
        assert position.market_value == Decimal("15000.00")

    def test_total_pnl(self) -> None:
        position = Position(
            account_id="U1234567",
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("100"),
            mark_price=Decimal("150.00"),
            position_value=Decimal("15000.00"),
            average_cost=Decimal("120.00"),
            cost_basis=Decimal("12000.00"),
            unrealized_pnl=Decimal("3000.00"),
            realized_pnl=Decimal("500.00"),
            position_date=date(2025, 6, 30),
        )
        assert position.total_pnl == Decimal("3500.00")

    def test_pnl_percentage(self) -> None:
        position = Position(
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
        # 3000 / 12000 * 100 = 25%
        assert position.pnl_percentage == Decimal("25")

    def test_pnl_percentage_zero_cost_basis(self) -> None:
        position = Position(
            account_id="U1234567",
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("100"),
            mark_price=Decimal("150.00"),
            position_value=Decimal("15000.00"),
            average_cost=Decimal("0"),
            cost_basis=Decimal("0"),
            unrealized_pnl=Decimal("3000.00"),
            position_date=date(2025, 6, 30),
        )
        assert position.pnl_percentage == Decimal("0")

    def test_is_long(self) -> None:
        position = Position(
            account_id="U1234567",
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("100"),
            mark_price=Decimal("150.00"),
            position_value=Decimal("15000.00"),
            average_cost=Decimal("120.00"),
            cost_basis=Decimal("12000.00"),
            position_date=date(2025, 6, 30),
        )
        assert position.is_long is True
        assert position.is_short is False

    def test_is_short(self) -> None:
        position = Position(
            account_id="U1234567",
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("-100"),
            mark_price=Decimal("150.00"),
            position_value=Decimal("-15000.00"),
            average_cost=Decimal("160.00"),
            cost_basis=Decimal("-16000.00"),
            position_date=date(2025, 6, 30),
        )
        assert position.is_short is True
        assert position.is_long is False

    def test_is_bond(self) -> None:
        stock = Position(
            account_id="U1234567",
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("100"),
            mark_price=Decimal("150.00"),
            position_value=Decimal("15000.00"),
            average_cost=Decimal("120.00"),
            cost_basis=Decimal("12000.00"),
            position_date=date(2025, 6, 30),
        )
        bond = Position(
            account_id="U1234567",
            symbol="US912810TD00",
            asset_class=AssetClass.BOND,
            quantity=Decimal("10000"),
            mark_price=Decimal("95.50"),
            position_value=Decimal("9550.00"),
            average_cost=Decimal("90.00"),
            cost_basis=Decimal("9000.00"),
            position_date=date(2025, 6, 30),
        )
        assert stock.is_bond is False
        assert bond.is_bond is True
