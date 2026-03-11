"""Tests for limit order MCP tools"""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.mcp.tools.limit_orders import register_limit_order_tools

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with limit order tools registered."""
    mcp = FastMCP("test")
    register_limit_order_tools(mcp)
    return mcp


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _add_order(
    test_mcp: FastMCP,
    db_path: str,
    symbol: str = "CSPX",
    market: str = "LSE",
    order_type: str = "BUY",
    limit_price: str = "700.00",
    **kwargs,
) -> dict:
    """Add an order and return parsed result."""
    tool = await test_mcp.get_tool("add_limit_order")
    result = await tool.fn(
        symbol=symbol,
        market=market,
        order_type=order_type,
        limit_price=limit_price,
        db_path=db_path,
        ctx=None,
        **kwargs,
    )
    return json.loads(result)


# ---------------------------------------------------------------------------
# Tests: add_limit_order
# ---------------------------------------------------------------------------


class TestAddLimitOrder:
    """Tests for the add_limit_order MCP tool."""

    @pytest.mark.asyncio
    async def test_add_order_with_all_fields(self, test_mcp: FastMCP, tmp_path) -> None:
        """Order with all fields should be created successfully."""
        db_path = str(tmp_path / "test.db")
        data = await _add_order(
            test_mcp,
            db_path,
            symbol="CSPX",
            market="LSE",
            order_type="BUY",
            limit_price="700.00",
            created_date="2025-01-15",
            quantity="10",
            amount_usd="7000",
            tranche_number=1,
            rationale="SMA200 support",
            notes="First tranche",
        )

        assert data["status"] == "created"
        order = data["order"]
        assert order["symbol"] == "CSPX"
        assert order["market"] == "LSE"
        assert order["order_type"] == "BUY"
        assert Decimal(order["limit_price"]) == Decimal("700.00")
        assert Decimal(order["quantity"]) == Decimal("10")
        assert Decimal(order["amount_usd"]) == Decimal("7000")
        assert order["tranche_number"] == 1
        assert order["rationale"] == "SMA200 support"
        assert order["notes"] == "First tranche"
        assert order["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_add_order_with_minimal_fields(self, test_mcp: FastMCP, tmp_path) -> None:
        """Order with only required fields should be created successfully."""
        db_path = str(tmp_path / "test.db")
        data = await _add_order(
            test_mcp, db_path, symbol="VWRA", market="LSE", limit_price="100.50"
        )

        assert data["status"] == "created"
        order = data["order"]
        assert order["symbol"] == "VWRA"
        assert order["market"] == "LSE"
        assert order["order_type"] == "BUY"
        assert order["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_invalid_order_type_rejected(self, test_mcp: FastMCP, tmp_path) -> None:
        """Invalid order_type should raise ValidationError."""
        db_path = str(tmp_path / "test.db")
        with pytest.raises(ValidationError):
            await _add_order(test_mcp, db_path, order_type="INVALID")

    @pytest.mark.asyncio
    async def test_invalid_limit_price_rejected(self, test_mcp: FastMCP, tmp_path) -> None:
        """Non-numeric limit_price should raise ValidationError."""
        db_path = str(tmp_path / "test.db")
        with pytest.raises(ValidationError):
            await _add_order(test_mcp, db_path, limit_price="not_a_number")

    @pytest.mark.asyncio
    async def test_invalid_quantity_rejected(self, test_mcp: FastMCP, tmp_path) -> None:
        """Non-numeric quantity should raise ValidationError."""
        db_path = str(tmp_path / "test.db")
        with pytest.raises(ValidationError):
            await _add_order(test_mcp, db_path, quantity="abc")

    @pytest.mark.asyncio
    async def test_invalid_date_format_rejected(self, test_mcp: FastMCP, tmp_path) -> None:
        """Invalid date format should raise ValidationError."""
        db_path = str(tmp_path / "test.db")
        with pytest.raises(ValidationError):
            await _add_order(test_mcp, db_path, created_date="15-01-2025")


# ---------------------------------------------------------------------------
# Tests: update_limit_order
# ---------------------------------------------------------------------------


class TestUpdateLimitOrder:
    """Tests for the update_limit_order MCP tool."""

    @pytest.mark.asyncio
    async def test_update_price(self, test_mcp: FastMCP, tmp_path) -> None:
        """Updating limit_price should reflect in the returned order."""
        db_path = str(tmp_path / "test.db")
        created = await _add_order(test_mcp, db_path)
        order_id = created["order"]["id"]

        tool = await test_mcp.get_tool("update_limit_order")
        result = await tool.fn(order_id=order_id, limit_price="680.00", db_path=db_path, ctx=None)
        data = json.loads(result)

        assert data["status"] == "updated"
        assert Decimal(data["order"]["limit_price"]) == Decimal("680.00")

    @pytest.mark.asyncio
    async def test_fill_order_with_filled_price(self, test_mcp: FastMCP, tmp_path) -> None:
        """Filling an order should set status, filled_price, and filled_date."""
        db_path = str(tmp_path / "test.db")
        created = await _add_order(test_mcp, db_path)
        order_id = created["order"]["id"]

        tool = await test_mcp.get_tool("update_limit_order")
        result = await tool.fn(
            order_id=order_id,
            status="FILLED",
            filled_price="695.50",
            filled_date="2025-02-01",
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)

        assert data["status"] == "updated"
        order = data["order"]
        assert order["status"] == "FILLED"
        assert Decimal(order["filled_price"]) == Decimal("695.50")
        assert order["filled_date"] == "2025-02-01"

    @pytest.mark.asyncio
    async def test_fill_order_auto_sets_filled_date(self, test_mcp: FastMCP, tmp_path) -> None:
        """When status is FILLED without filled_date, today's date is used."""
        db_path = str(tmp_path / "test.db")
        created = await _add_order(test_mcp, db_path)
        order_id = created["order"]["id"]

        tool = await test_mcp.get_tool("update_limit_order")
        result = await tool.fn(
            order_id=order_id,
            status="FILLED",
            filled_price="695.50",
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)

        assert data["order"]["status"] == "FILLED"
        assert data["order"]["filled_date"] is not None

    @pytest.mark.asyncio
    async def test_cancel_order(self, test_mcp: FastMCP, tmp_path) -> None:
        """Cancelling an order should set status to CANCELLED."""
        db_path = str(tmp_path / "test.db")
        created = await _add_order(test_mcp, db_path)
        order_id = created["order"]["id"]

        tool = await test_mcp.get_tool("update_limit_order")
        result = await tool.fn(order_id=order_id, status="CANCELLED", db_path=db_path, ctx=None)
        data = json.loads(result)

        assert data["status"] == "updated"
        assert data["order"]["status"] == "CANCELLED"

    @pytest.mark.asyncio
    async def test_invalid_status_transition(self, test_mcp: FastMCP, tmp_path) -> None:
        """Transitioning from terminal status should raise ValidationError."""
        db_path = str(tmp_path / "test.db")
        created = await _add_order(test_mcp, db_path)
        order_id = created["order"]["id"]

        # First cancel
        tool = await test_mcp.get_tool("update_limit_order")
        await tool.fn(order_id=order_id, status="CANCELLED", db_path=db_path, ctx=None)

        # Then try to fill the cancelled order
        with pytest.raises(ValidationError):
            await tool.fn(order_id=order_id, status="FILLED", db_path=db_path, ctx=None)

    @pytest.mark.asyncio
    async def test_update_nonexistent_order(self, test_mcp: FastMCP, tmp_path) -> None:
        """Updating a nonexistent order should return not_found."""
        db_path = str(tmp_path / "test.db")
        # Initialize the DB by adding and ignoring an order
        await _add_order(test_mcp, db_path)

        tool = await test_mcp.get_tool("update_limit_order")
        result = await tool.fn(order_id=9999, limit_price="100.00", db_path=db_path, ctx=None)
        data = json.loads(result)

        assert data["status"] == "not_found"


# ---------------------------------------------------------------------------
# Tests: get_pending_orders
# ---------------------------------------------------------------------------


class TestGetPendingOrders:
    """Tests for the get_pending_orders MCP tool."""

    @pytest.mark.asyncio
    async def test_return_all_pending_orders(self, test_mcp: FastMCP, tmp_path) -> None:
        """Should return all pending orders."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="CSPX", limit_price="700.00")
        await _add_order(test_mcp, db_path, symbol="VWRA", limit_price="100.00")

        tool = await test_mcp.get_tool("get_pending_orders")
        result = await tool.fn(db_path=db_path, ctx=None)
        data = json.loads(result)

        assert data["pending_count"] == 2
        symbols = [o["symbol"] for o in data["orders"]]
        assert "CSPX" in symbols
        assert "VWRA" in symbols

    @pytest.mark.asyncio
    async def test_filter_by_symbol(self, test_mcp: FastMCP, tmp_path) -> None:
        """Filtering by symbol should return only matching orders."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="CSPX", limit_price="700.00")
        await _add_order(test_mcp, db_path, symbol="VWRA", limit_price="100.00")

        tool = await test_mcp.get_tool("get_pending_orders")
        result = await tool.fn(symbol="CSPX", db_path=db_path, ctx=None)
        data = json.loads(result)

        assert data["pending_count"] == 1
        assert data["orders"][0]["symbol"] == "CSPX"

    @pytest.mark.asyncio
    async def test_filter_by_market(self, test_mcp: FastMCP, tmp_path) -> None:
        """Filtering by market should return only matching orders."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="CSPX", market="LSE", limit_price="700.00")
        await _add_order(test_mcp, db_path, symbol="1329", market="TSE", limit_price="2500.00")

        tool = await test_mcp.get_tool("get_pending_orders")
        result = await tool.fn(market="TSE", db_path=db_path, ctx=None)
        data = json.loads(result)

        assert data["pending_count"] == 1
        assert data["orders"][0]["symbol"] == "1329"

    @pytest.mark.asyncio
    async def test_empty_result(self, test_mcp: FastMCP, tmp_path) -> None:
        """Empty DB should return zero pending orders."""
        db_path = str(tmp_path / "test.db")

        tool = await test_mcp.get_tool("get_pending_orders")
        result = await tool.fn(db_path=db_path, ctx=None)
        data = json.loads(result)

        assert data["pending_count"] == 0
        assert data["orders"] == []


# ---------------------------------------------------------------------------
# Tests: check_order_proximity
# ---------------------------------------------------------------------------


class TestCheckOrderProximity:
    """Tests for the check_order_proximity MCP tool."""

    @pytest.mark.asyncio
    async def test_price_fetch_and_alert(self, test_mcp: FastMCP, tmp_path) -> None:
        """Order within threshold should trigger an alert."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="AAPL", market="NYSE", limit_price="200.00")

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.info = {"currentPrice": 205.0}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("check_order_proximity")
            result = await tool.fn(threshold_pct=5.0, db_path=db_path, ctx=None)
            data = json.loads(result)

        assert data["alert_count"] == 1
        assert data["results"][0]["alert"] is True
        assert Decimal(data["results"][0]["current_price"]) == Decimal("205")

    @pytest.mark.asyncio
    async def test_price_outside_threshold_no_alert(self, test_mcp: FastMCP, tmp_path) -> None:
        """Order outside threshold should not trigger an alert."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="AAPL", market="NYSE", limit_price="200.00")

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.info = {"currentPrice": 230.0}  # 15% above
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("check_order_proximity")
            result = await tool.fn(threshold_pct=5.0, db_path=db_path, ctx=None)
            data = json.loads(result)

        assert data["alert_count"] == 0
        assert data["results"][0]["alert"] is False

    @pytest.mark.asyncio
    async def test_market_suffix_lse(self, test_mcp: FastMCP, tmp_path) -> None:
        """LSE market orders should use .L suffix for yfinance."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="CSPX", market="LSE", limit_price="700.00")

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.info = {"currentPrice": 710.0}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("check_order_proximity")
            await tool.fn(threshold_pct=5.0, db_path=db_path, ctx=None)

        # Verify yfinance was called with the correct suffix
        mock_ticker_cls.assert_called_once_with("CSPX.L")

    @pytest.mark.asyncio
    async def test_market_suffix_tse(self, test_mcp: FastMCP, tmp_path) -> None:
        """TSE market orders should use .T suffix for yfinance."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="1329", market="TSE", limit_price="2500.00")

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.info = {"currentPrice": 2550.0}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("check_order_proximity")
            await tool.fn(threshold_pct=5.0, db_path=db_path, ctx=None)

        mock_ticker_cls.assert_called_once_with("1329.T")

    @pytest.mark.asyncio
    async def test_market_suffix_nyse_no_suffix(self, test_mcp: FastMCP, tmp_path) -> None:
        """NYSE market orders should use symbol as-is (no suffix)."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="AAPL", market="NYSE", limit_price="200.00")

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.info = {"currentPrice": 205.0}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("check_order_proximity")
            await tool.fn(threshold_pct=5.0, db_path=db_path, ctx=None)

        mock_ticker_cls.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_multiple_tranches_single_api_call(self, test_mcp: FastMCP, tmp_path) -> None:
        """Multiple tranches for same symbol should make only one API call."""
        db_path = str(tmp_path / "test.db")
        await _add_order(
            test_mcp,
            db_path,
            symbol="CSPX",
            market="LSE",
            limit_price="700.00",
            tranche_number=1,
        )
        # Add a second tranche at different price
        tool = await test_mcp.get_tool("add_limit_order")
        await tool.fn(
            symbol="CSPX",
            market="LSE",
            order_type="BUY",
            limit_price="680.00",
            tranche_number=2,
            db_path=db_path,
            ctx=None,
        )

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.info = {"currentPrice": 710.0}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("check_order_proximity")
            result = await tool.fn(threshold_pct=5.0, db_path=db_path, ctx=None)
            data = json.loads(result)

        # Only one API call despite two orders for the same symbol
        assert mock_ticker_cls.call_count == 1
        assert data["total_orders"] == 2

    @pytest.mark.asyncio
    async def test_yfinance_failure_graceful_degradation(self, test_mcp: FastMCP, tmp_path) -> None:
        """yfinance failure should return error info, not crash."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="CSPX", market="LSE", limit_price="700.00")

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_cls.side_effect = Exception("Network error")

            tool = await test_mcp.get_tool("check_order_proximity")
            result = await tool.fn(threshold_pct=5.0, db_path=db_path, ctx=None)
            data = json.loads(result)

        assert data["total_orders"] == 1
        assert data["alert_count"] == 0
        assert data["results"][0]["current_price"] is None
        assert "error" in data["results"][0]
        assert data["results"][0]["alert"] is False

    @pytest.mark.asyncio
    async def test_no_pending_orders_empty_result(self, test_mcp: FastMCP, tmp_path) -> None:
        """No pending orders should return empty results."""
        db_path = str(tmp_path / "test.db")

        tool = await test_mcp.get_tool("check_order_proximity")
        result = await tool.fn(threshold_pct=5.0, db_path=db_path, ctx=None)
        data = json.loads(result)

        assert data["alerts"] == []
        assert data["results"] == []
        assert "No pending orders found" in data["message"]

    @pytest.mark.asyncio
    async def test_fallback_to_regular_market_price(self, test_mcp: FastMCP, tmp_path) -> None:
        """Should fall back to regularMarketPrice if currentPrice is missing."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="AAPL", market="NYSE", limit_price="200.00")

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.info = {"regularMarketPrice": 202.0}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("check_order_proximity")
            result = await tool.fn(threshold_pct=5.0, db_path=db_path, ctx=None)
            data = json.loads(result)

        assert Decimal(data["results"][0]["current_price"]) == Decimal("202")

    @pytest.mark.asyncio
    async def test_symbol_already_has_suffix_no_double_append(
        self, test_mcp: FastMCP, tmp_path
    ) -> None:
        """Symbol stored with suffix (e.g., '1329.T') should not get double suffix."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="1329.T", market="TSE", limit_price="2500.00")

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.info = {"currentPrice": 2550.0}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("check_order_proximity")
            await tool.fn(threshold_pct=5.0, db_path=db_path, ctx=None)

        # Should be called with "1329.T", NOT "1329.T.T"
        mock_ticker_cls.assert_called_once_with("1329.T")

    @pytest.mark.asyncio
    async def test_symbol_lowercase_suffix_no_double_append(
        self, test_mcp: FastMCP, tmp_path
    ) -> None:
        """Symbol with lowercase suffix (e.g., '1329.t') should not get double suffix."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="1329.t", market="TSE", limit_price="2500.00")

        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.info = {"currentPrice": 2550.0}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("check_order_proximity")
            await tool.fn(threshold_pct=5.0, db_path=db_path, ctx=None)

        # Should be called with "1329.t", NOT "1329.t.T"
        mock_ticker_cls.assert_called_once_with("1329.t")

    @pytest.mark.asyncio
    async def test_same_symbol_different_markets(self, test_mcp: FastMCP, tmp_path) -> None:
        """Same symbol on different markets should make separate API calls."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="FOO", market="NYSE", limit_price="100.00")
        await _add_order(test_mcp, db_path, symbol="FOO", market="LSE", limit_price="80.00")

        call_args_list = []

        def make_ticker(symbol: str) -> MagicMock:
            call_args_list.append(symbol)
            ticker = MagicMock()
            ticker.info = {"currentPrice": 105.0}
            return ticker

        with patch("yfinance.Ticker", side_effect=make_ticker):
            tool = await test_mcp.get_tool("check_order_proximity")
            result = await tool.fn(threshold_pct=10.0, db_path=db_path, ctx=None)
            data = json.loads(result)

        # Two separate API calls: "FOO" (NYSE) and "FOO.L" (LSE)
        assert len(call_args_list) == 2
        assert "FOO" in call_args_list
        assert "FOO.L" in call_args_list
        assert data["total_orders"] == 2


# ---------------------------------------------------------------------------
# Tests: get_order_history
# ---------------------------------------------------------------------------


class TestGetOrderHistory:
    """Tests for the get_order_history MCP tool."""

    @pytest.mark.asyncio
    async def test_return_all_statuses(self, test_mcp: FastMCP, tmp_path) -> None:
        """Should return orders in all statuses."""
        db_path = str(tmp_path / "test.db")
        created = await _add_order(test_mcp, db_path, symbol="CSPX", limit_price="700.00")
        order_id = created["order"]["id"]

        # Fill the order
        update_tool = await test_mcp.get_tool("update_limit_order")
        await update_tool.fn(
            order_id=order_id,
            status="FILLED",
            filled_price="695.00",
            db_path=db_path,
            ctx=None,
        )

        # Add another order (stays pending)
        await _add_order(test_mcp, db_path, symbol="VWRA", limit_price="100.00")

        tool = await test_mcp.get_tool("get_order_history")
        result = await tool.fn(db_path=db_path, ctx=None)
        data = json.loads(result)

        assert data["total_orders"] == 2
        assert "FILLED" in data["status_summary"]
        assert "PENDING" in data["status_summary"]

    @pytest.mark.asyncio
    async def test_filter_by_symbol(self, test_mcp: FastMCP, tmp_path) -> None:
        """Filtering by symbol should return only matching orders."""
        db_path = str(tmp_path / "test.db")
        await _add_order(test_mcp, db_path, symbol="CSPX", limit_price="700.00")
        await _add_order(test_mcp, db_path, symbol="VWRA", limit_price="100.00")

        tool = await test_mcp.get_tool("get_order_history")
        result = await tool.fn(symbol="CSPX", db_path=db_path, ctx=None)
        data = json.loads(result)

        assert data["total_orders"] == 1
        assert data["orders"][0]["symbol"] == "CSPX"

    @pytest.mark.asyncio
    async def test_empty_history(self, test_mcp: FastMCP, tmp_path) -> None:
        """Empty DB should return zero orders."""
        db_path = str(tmp_path / "test.db")

        tool = await test_mcp.get_tool("get_order_history")
        result = await tool.fn(db_path=db_path, ctx=None)
        data = json.loads(result)

        assert data["total_orders"] == 0
        assert data["status_summary"] == {}
        assert data["orders"] == []
