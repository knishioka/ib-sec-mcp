"""Tests for live trading MCP tools via Client Portal Gateway"""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.api.cp_client import CPAuthenticationError, CPConnectionError
from ib_sec_mcp.api.cp_models import (
    CPAccountBalance,
    CPAuthStatus,
    CPOrder,
    CPOrderSide,
    CPOrderStatus,
    CPPosition,
)
from ib_sec_mcp.mcp.tools.live_trading import (
    _balance_to_dict,
    _filter_orders,
    _order_to_dict,
    _position_to_dict,
    register_live_trading_tools,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with live trading tools registered."""
    mcp = FastMCP("test")
    register_live_trading_tools(mcp)
    return mcp


@pytest.fixture()
def mock_orders() -> list[CPOrder]:
    """Sample CPOrder objects."""
    return [
        CPOrder(
            orderId=1,
            symbol="AAPL",
            side=CPOrderSide.BUY,
            totalSize=Decimal("100"),
            price=Decimal("150.50"),
            avgPrice=Decimal("0"),
            status=CPOrderStatus.SUBMITTED,
            orderType="LMT",
            acct="U1234567",
        ),
        CPOrder(
            orderId=2,
            symbol="MSFT",
            side=CPOrderSide.SELL,
            totalSize=Decimal("50"),
            price=Decimal("400.00"),
            avgPrice=Decimal("380.25"),
            status=CPOrderStatus.FILLED,
            orderType="LMT",
            acct="U1234567",
        ),
    ]


@pytest.fixture()
def mock_positions() -> list[CPPosition]:
    """Sample CPPosition objects."""
    return [
        CPPosition(
            acctId="U1234567",
            conid=265598,
            symbol="AAPL",
            position=Decimal("100"),
            mktPrice=Decimal("155.30"),
            mktValue=Decimal("15530.00"),
            avgCost=Decimal("150.50"),
            unrealizedPnl=Decimal("480.00"),
            currency="USD",
        ),
    ]


@pytest.fixture()
def mock_balance() -> CPAccountBalance:
    """Sample CPAccountBalance object."""
    return CPAccountBalance(
        account_id="U1234567",
        netliquidation=Decimal("100000.50"),
        totalcashvalue=Decimal("25000.75"),
        buyingpower=Decimal("50000.00"),
        grosspositionvalue=Decimal("75000.25"),
    )


@pytest.fixture()
def mock_auth_status() -> CPAuthStatus:
    """Sample CPAuthStatus object."""
    return CPAuthStatus(
        authenticated=True,
        competing=False,
        connected=True,
        message="Session active",
    )


def _mock_cp_client(
    orders: list[CPOrder] | None = None,
    positions: list[CPPosition] | None = None,
    balance: CPAccountBalance | None = None,
    auth_status: CPAuthStatus | None = None,
    accounts: list[str] | None = None,
) -> MagicMock:
    """Create a mock CPClient as async context manager."""
    client = AsyncMock()
    client.get_orders = AsyncMock(return_value=orders if orders is not None else [])
    client.get_positions = AsyncMock(return_value=positions if positions is not None else [])
    client.get_account_balance = AsyncMock(return_value=balance)
    client.check_auth_status = AsyncMock(return_value=auth_status)
    client.get_accounts = AsyncMock(return_value=accounts if accounts is not None else ["U1234567"])

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# Tests: Module-level helpers
# ---------------------------------------------------------------------------


class TestOrderToDict:
    """Tests for _order_to_dict helper."""

    def test_converts_decimal_fields_to_strings(self, mock_orders: list[CPOrder]) -> None:
        result = _order_to_dict(mock_orders[0])
        assert result["quantity"] == "100"
        assert result["limit_price"] == "150.50"
        assert result["avg_price"] == "0"

    def test_preserves_string_fields(self, mock_orders: list[CPOrder]) -> None:
        result = _order_to_dict(mock_orders[0])
        assert result["symbol"] == "AAPL"
        assert result["order_id"] == 1
        assert result["account_id"] == "U1234567"


class TestPositionToDict:
    """Tests for _position_to_dict helper."""

    def test_converts_decimal_fields_to_strings(self, mock_positions: list[CPPosition]) -> None:
        result = _position_to_dict(mock_positions[0])
        assert result["quantity"] == "100"
        assert result["market_price"] == "155.30"
        assert result["unrealized_pnl"] == "480.00"

    def test_preserves_non_decimal_fields(self, mock_positions: list[CPPosition]) -> None:
        result = _position_to_dict(mock_positions[0])
        assert result["symbol"] == "AAPL"
        assert result["currency"] == "USD"


class TestBalanceToDict:
    """Tests for _balance_to_dict helper."""

    def test_converts_decimal_fields_to_strings(self, mock_balance: CPAccountBalance) -> None:
        result = _balance_to_dict(mock_balance)
        assert result["net_liquidation"] == "100000.50"
        assert result["total_cash"] == "25000.75"
        assert result["buying_power"] == "50000.00"
        assert result["gross_position_value"] == "75000.25"


class TestFilterOrders:
    """Tests for _filter_orders helper."""

    def test_no_filters(self, mock_orders: list[CPOrder]) -> None:
        result = _filter_orders(mock_orders)
        assert len(result) == 2

    def test_filter_by_symbol(self, mock_orders: list[CPOrder]) -> None:
        result = _filter_orders(mock_orders, symbol="AAPL")
        assert len(result) == 1
        assert result[0].symbol == "AAPL"

    def test_filter_by_symbol_case_insensitive(self, mock_orders: list[CPOrder]) -> None:
        result = _filter_orders(mock_orders, symbol="aapl")
        assert len(result) == 1

    def test_filter_by_side(self, mock_orders: list[CPOrder]) -> None:
        result = _filter_orders(mock_orders, side="SELL")
        assert len(result) == 1
        assert result[0].side == CPOrderSide.SELL

    def test_filter_by_status(self, mock_orders: list[CPOrder]) -> None:
        result = _filter_orders(mock_orders, status="Submitted")
        assert len(result) == 1
        assert result[0].status == CPOrderStatus.SUBMITTED

    def test_combined_filters(self, mock_orders: list[CPOrder]) -> None:
        result = _filter_orders(mock_orders, symbol="AAPL", side="BUY")
        assert len(result) == 1

    def test_invalid_side_returns_all(self, mock_orders: list[CPOrder]) -> None:
        result = _filter_orders(mock_orders, side="INVALID")
        assert len(result) == 2

    def test_invalid_status_returns_all(self, mock_orders: list[CPOrder]) -> None:
        result = _filter_orders(mock_orders, status="INVALID")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Tests: get_live_orders
# ---------------------------------------------------------------------------


class TestGetLiveOrders:
    """Tests for the get_live_orders MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_all_orders(self, test_mcp: FastMCP, mock_orders: list[CPOrder]) -> None:
        mock_cm = _mock_cp_client(orders=mock_orders)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_orders")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert data["total_orders"] == 2
        assert len(data["orders"]) == 2

    @pytest.mark.asyncio
    async def test_filter_by_symbol(self, test_mcp: FastMCP, mock_orders: list[CPOrder]) -> None:
        mock_cm = _mock_cp_client(orders=mock_orders)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_orders")
            result = await tool.fn(symbol="AAPL", ctx=None)
            data = json.loads(result)

        assert data["total_orders"] == 1
        assert data["orders"][0]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_decimal_precision_in_response(
        self, test_mcp: FastMCP, mock_orders: list[CPOrder]
    ) -> None:
        mock_cm = _mock_cp_client(orders=mock_orders)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_orders")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        order = data["orders"][0]
        # Values should be string representations of Decimal
        Decimal(order["limit_price"])
        Decimal(order["quantity"])

    @pytest.mark.asyncio
    async def test_gateway_not_running(self, test_mcp: FastMCP) -> None:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=CPConnectionError("unreachable"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_orders")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert "error" in data
        assert "not running" in data["error"]

    @pytest.mark.asyncio
    async def test_session_expired(self, test_mcp: FastMCP) -> None:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=CPAuthenticationError("expired"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_orders")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert "error" in data
        assert "expired" in data["error"]

    @pytest.mark.asyncio
    async def test_empty_orders(self, test_mcp: FastMCP) -> None:
        mock_cm = _mock_cp_client(orders=[])
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_orders")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert data["total_orders"] == 0
        assert data["orders"] == []


# ---------------------------------------------------------------------------
# Tests: get_live_account_balance
# ---------------------------------------------------------------------------


class TestGetLiveAccountBalance:
    """Tests for the get_live_account_balance MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_balance_with_explicit_account(
        self, test_mcp: FastMCP, mock_balance: CPAccountBalance
    ) -> None:
        mock_cm = _mock_cp_client(balance=mock_balance)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_account_balance")
            result = await tool.fn(account_id="U1234567", ctx=None)
            data = json.loads(result)

        assert data["account_id"] == "U1234567"
        assert Decimal(data["net_liquidation"]) == Decimal("100000.50")
        assert Decimal(data["total_cash"]) == Decimal("25000.75")

    @pytest.mark.asyncio
    async def test_auto_selects_first_account(
        self, test_mcp: FastMCP, mock_balance: CPAccountBalance
    ) -> None:
        mock_cm = _mock_cp_client(balance=mock_balance, accounts=["U1234567", "U7654321"])
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_account_balance")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert data["account_id"] == "U1234567"

    @pytest.mark.asyncio
    async def test_no_accounts_found(self, test_mcp: FastMCP) -> None:
        mock_cm = _mock_cp_client(accounts=[])
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_account_balance")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert "error" in data
        assert "No accounts" in data["error"]

    @pytest.mark.asyncio
    async def test_gateway_not_running(self, test_mcp: FastMCP) -> None:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=CPConnectionError("unreachable"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_account_balance")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert "error" in data
        assert "not running" in data["error"]

    @pytest.mark.asyncio
    async def test_decimal_precision(
        self, test_mcp: FastMCP, mock_balance: CPAccountBalance
    ) -> None:
        mock_cm = _mock_cp_client(balance=mock_balance)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_account_balance")
            result = await tool.fn(account_id="U1234567", ctx=None)
            data = json.loads(result)

        # All financial values should be parseable as Decimal
        for field in ["net_liquidation", "total_cash", "buying_power", "gross_position_value"]:
            Decimal(data[field])


# ---------------------------------------------------------------------------
# Tests: get_live_positions
# ---------------------------------------------------------------------------


class TestGetLivePositions:
    """Tests for the get_live_positions MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_positions(
        self, test_mcp: FastMCP, mock_positions: list[CPPosition]
    ) -> None:
        mock_cm = _mock_cp_client(positions=mock_positions, accounts=["U1234567"])
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_positions")
            result = await tool.fn(account_id="U1234567", ctx=None)
            data = json.loads(result)

        assert data["account_id"] == "U1234567"
        assert data["total_positions"] == 1
        pos = data["positions"][0]
        assert pos["symbol"] == "AAPL"
        assert Decimal(pos["unrealized_pnl"]) == Decimal("480.00")

    @pytest.mark.asyncio
    async def test_auto_selects_first_account(
        self, test_mcp: FastMCP, mock_positions: list[CPPosition]
    ) -> None:
        mock_cm = _mock_cp_client(positions=mock_positions, accounts=["U1234567"])
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_positions")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert data["account_id"] == "U1234567"

    @pytest.mark.asyncio
    async def test_no_accounts_found(self, test_mcp: FastMCP) -> None:
        mock_cm = _mock_cp_client(accounts=[])
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_positions")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_gateway_not_running(self, test_mcp: FastMCP) -> None:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=CPConnectionError("unreachable"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_positions")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert "error" in data
        assert "not running" in data["error"]

    @pytest.mark.asyncio
    async def test_decimal_precision(
        self, test_mcp: FastMCP, mock_positions: list[CPPosition]
    ) -> None:
        mock_cm = _mock_cp_client(positions=mock_positions, accounts=["U1234567"])
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("get_live_positions")
            result = await tool.fn(account_id="U1234567", ctx=None)
            data = json.loads(result)

        pos = data["positions"][0]
        for field in ["quantity", "market_price", "market_value", "avg_cost", "unrealized_pnl"]:
            Decimal(pos[field])


# ---------------------------------------------------------------------------
# Tests: check_gateway_status
# ---------------------------------------------------------------------------


class TestCheckGatewayStatus:
    """Tests for the check_gateway_status MCP tool."""

    @pytest.mark.asyncio
    async def test_gateway_connected_and_authenticated(
        self, test_mcp: FastMCP, mock_auth_status: CPAuthStatus
    ) -> None:
        mock_cm = _mock_cp_client(auth_status=mock_auth_status)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("check_gateway_status")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert data["connected"] is True
        assert data["authenticated"] is True
        assert data["competing"] is False
        assert data["server_connected"] is True

    @pytest.mark.asyncio
    async def test_gateway_not_running(self, test_mcp: FastMCP) -> None:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=CPConnectionError("unreachable"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("check_gateway_status")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert data["connected"] is False
        assert data["authenticated"] is False
        assert "not running" in data["message"]

    @pytest.mark.asyncio
    async def test_gateway_not_authenticated(self, test_mcp: FastMCP) -> None:
        unauth_status = CPAuthStatus(
            authenticated=False,
            competing=False,
            connected=True,
            message="Not authenticated",
        )
        mock_cm = _mock_cp_client(auth_status=unauth_status)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("check_gateway_status")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert data["connected"] is True
        assert data["authenticated"] is False

    @pytest.mark.asyncio
    async def test_response_is_valid_json(
        self, test_mcp: FastMCP, mock_auth_status: CPAuthStatus
    ) -> None:
        mock_cm = _mock_cp_client(auth_status=mock_auth_status)
        with patch("ib_sec_mcp.mcp.tools.live_trading.CPClient", return_value=mock_cm):
            tool = await test_mcp.get_tool("check_gateway_status")
            result = await tool.fn(ctx=None)

        data = json.loads(result)
        assert isinstance(data, dict)
        for key in ["connected", "authenticated", "competing", "server_connected", "message"]:
            assert key in data
