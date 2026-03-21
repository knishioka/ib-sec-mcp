"""Tests for Client Portal Gateway API models"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from ib_sec_mcp.api.cp_models import (
    CPAccountBalance,
    CPAuthStatus,
    CPOrder,
    CPOrderSide,
    CPOrderStatus,
    CPPosition,
)

# ---------------------------------------------------------------------------
# TestCPAuthStatus
# ---------------------------------------------------------------------------


class TestCPAuthStatus:
    def test_authenticated_session(self) -> None:
        status = CPAuthStatus(
            authenticated=True,
            competing=False,
            connected=True,
            message="",
        )
        assert status.authenticated is True
        assert status.connected is True

    def test_from_ib_json(self) -> None:
        data = {
            "authenticated": True,
            "competing": False,
            "connected": True,
            "message": "Session active",
        }
        status = CPAuthStatus.model_validate(data)
        assert status.authenticated is True
        assert status.message == "Session active"

    def test_defaults(self) -> None:
        status = CPAuthStatus(authenticated=False)
        assert status.competing is False
        assert status.connected is False
        assert status.message == ""

    def test_required_authenticated_field(self) -> None:
        with pytest.raises(ValidationError):
            CPAuthStatus()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TestCPOrderEnums
# ---------------------------------------------------------------------------


class TestCPOrderEnums:
    def test_order_side_values(self) -> None:
        assert CPOrderSide.BUY == "BUY"
        assert CPOrderSide.SELL == "SELL"

    def test_order_status_values(self) -> None:
        assert CPOrderStatus.SUBMITTED == "Submitted"
        assert CPOrderStatus.FILLED == "Filled"
        assert CPOrderStatus.CANCELLED == "Cancelled"
        assert CPOrderStatus.PRE_SUBMITTED == "PreSubmitted"


# ---------------------------------------------------------------------------
# TestCPOrder
# ---------------------------------------------------------------------------


class TestCPOrder:
    def test_from_ib_json_with_aliases(self) -> None:
        data = {
            "orderId": 12345,
            "symbol": "AAPL",
            "side": "BUY",
            "totalSize": "100",
            "price": "150.50",
            "avgPrice": "150.25",
            "status": "Submitted",
            "orderType": "LMT",
            "acct": "U1234567",
        }
        order = CPOrder.model_validate(data)
        assert order.order_id == 12345
        assert order.symbol == "AAPL"
        assert order.side == "BUY"
        assert order.quantity == Decimal("100")
        assert order.price == Decimal("150.50")
        assert order.avg_price == Decimal("150.25")
        assert order.status == "Submitted"
        assert order.order_type == "LMT"
        assert order.account_id == "U1234567"

    def test_from_python_field_names(self) -> None:
        order = CPOrder(
            order_id=1,
            symbol="MSFT",
            side="SELL",
            quantity=Decimal("50"),
            status="Filled",
        )
        assert order.order_id == 1
        assert order.quantity == Decimal("50")

    def test_decimal_precision(self) -> None:
        data = {
            "orderId": 1,
            "symbol": "AAPL",
            "side": "BUY",
            "totalSize": "100.5",
            "price": "150.123456",
            "avgPrice": "0",
            "status": "Submitted",
        }
        order = CPOrder.model_validate(data)
        assert order.price == Decimal("150.123456")
        assert isinstance(order.price, Decimal)

    def test_defaults(self) -> None:
        data = {
            "orderId": 1,
            "symbol": "AAPL",
            "side": "BUY",
            "totalSize": "10",
            "status": "Submitted",
        }
        order = CPOrder.model_validate(data)
        assert order.price == Decimal("0")
        assert order.avg_price == Decimal("0")
        assert order.order_type == ""
        assert order.account_id == ""

    def test_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            CPOrder.model_validate({"symbol": "AAPL"})


# ---------------------------------------------------------------------------
# TestCPAccountBalance
# ---------------------------------------------------------------------------


class TestCPAccountBalance:
    def test_from_ib_json_with_aliases(self) -> None:
        data = {
            "account_id": "U1234567",
            "netliquidation": "1000000.50",
            "totalcashvalue": "250000.75",
            "buyingpower": "500000.00",
            "grosspositionvalue": "750000.25",
        }
        balance = CPAccountBalance.model_validate(data)
        assert balance.account_id == "U1234567"
        assert balance.net_liquidation == Decimal("1000000.50")
        assert balance.total_cash == Decimal("250000.75")
        assert balance.buying_power == Decimal("500000.00")
        assert balance.gross_position_value == Decimal("750000.25")

    def test_decimal_types(self) -> None:
        data = {
            "account_id": "U1234567",
            "netliquidation": "123.456789",
        }
        balance = CPAccountBalance.model_validate(data)
        assert isinstance(balance.net_liquidation, Decimal)
        assert balance.net_liquidation == Decimal("123.456789")

    def test_defaults(self) -> None:
        balance = CPAccountBalance(account_id="U1234567")
        assert balance.net_liquidation == Decimal("0")
        assert balance.total_cash == Decimal("0")
        assert balance.buying_power == Decimal("0")
        assert balance.gross_position_value == Decimal("0")

    def test_required_account_id(self) -> None:
        with pytest.raises(ValidationError):
            CPAccountBalance()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TestCPPosition
# ---------------------------------------------------------------------------


class TestCPPosition:
    def test_from_ib_json_with_aliases(self) -> None:
        data = {
            "acctId": "U1234567",
            "conid": 265598,
            "symbol": "AAPL",
            "position": "100",
            "mktPrice": "175.50",
            "mktValue": "17550.00",
            "avgCost": "150.25",
            "unrealizedPnl": "2525.00",
            "currency": "USD",
        }
        pos = CPPosition.model_validate(data)
        assert pos.account_id == "U1234567"
        assert pos.contract_id == 265598
        assert pos.symbol == "AAPL"
        assert pos.position == Decimal("100")
        assert pos.market_price == Decimal("175.50")
        assert pos.market_value == Decimal("17550.00")
        assert pos.avg_cost == Decimal("150.25")
        assert pos.unrealized_pnl == Decimal("2525.00")
        assert pos.currency == "USD"

    def test_from_python_field_names(self) -> None:
        pos = CPPosition(
            account_id="U9999999",
            contract_id=12345,
            position=Decimal("50"),
        )
        assert pos.account_id == "U9999999"
        assert pos.contract_id == 12345

    def test_decimal_precision(self) -> None:
        data = {
            "acctId": "U1234567",
            "conid": 1,
            "position": "100.123456",
            "mktPrice": "0.000001",
        }
        pos = CPPosition.model_validate(data)
        assert pos.position == Decimal("100.123456")
        assert pos.market_price == Decimal("0.000001")
        assert isinstance(pos.market_price, Decimal)

    def test_defaults(self) -> None:
        pos = CPPosition(
            account_id="U1234567",
            contract_id=1,
            position=Decimal("10"),
        )
        assert pos.symbol == ""
        assert pos.market_price == Decimal("0")
        assert pos.market_value == Decimal("0")
        assert pos.avg_cost == Decimal("0")
        assert pos.unrealized_pnl == Decimal("0")
        assert pos.currency == "USD"

    def test_negative_unrealized_pnl(self) -> None:
        data = {
            "acctId": "U1234567",
            "conid": 1,
            "position": "100",
            "unrealizedPnl": "-500.75",
        }
        pos = CPPosition.model_validate(data)
        assert pos.unrealized_pnl == Decimal("-500.75")

    def test_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            CPPosition.model_validate({"symbol": "AAPL"})
