"""Integration tests for live order retrieval from Client Portal Gateway"""

from decimal import Decimal

from ib_sec_mcp.api.cp_client import CPClient
from ib_sec_mcp.api.cp_models import CPOrder, CPOrderSide, CPOrderStatus


class TestLiveOrders:
    """Test live order retrieval and filtering"""

    async def test_get_orders_returns_list(self, cp_client: CPClient) -> None:
        """Verify get_orders returns a list (may be empty if no orders)."""
        orders = await cp_client.get_orders()
        assert isinstance(orders, list)

    async def test_order_model_fields(self, cp_client: CPClient) -> None:
        """Verify order objects have correct field types when orders exist."""
        orders = await cp_client.get_orders()
        for order in orders:
            assert isinstance(order, CPOrder)
            assert isinstance(order.order_id, int)
            assert isinstance(order.symbol, str)
            assert isinstance(order.side, CPOrderSide)
            assert isinstance(order.quantity, Decimal)
            assert isinstance(order.status, CPOrderStatus)

    async def test_filter_orders_by_status(self, cp_client: CPClient) -> None:
        """Verify orders can be filtered by status in application code."""
        orders = await cp_client.get_orders()
        active_statuses = {
            CPOrderStatus.SUBMITTED,
            CPOrderStatus.PRE_SUBMITTED,
            CPOrderStatus.PENDING_SUBMIT,
        }
        active_orders = [o for o in orders if o.status in active_statuses]
        # All filtered orders should have active status
        for order in active_orders:
            assert order.status in active_statuses

    async def test_filter_orders_by_symbol(self, cp_client: CPClient) -> None:
        """Verify orders can be filtered by symbol in application code."""
        orders = await cp_client.get_orders()
        if orders:
            target_symbol = orders[0].symbol
            filtered = [o for o in orders if o.symbol == target_symbol]
            assert len(filtered) >= 1
            assert all(o.symbol == target_symbol for o in filtered)


class TestAccountBalance:
    """Test account balance retrieval"""

    async def test_get_account_balance(self, cp_client: CPClient, paper_account_id: str) -> None:
        """Verify balance retrieval returns valid Decimal values."""
        balance = await cp_client.get_account_balance(paper_account_id)
        assert balance.account_id == paper_account_id
        assert isinstance(balance.net_liquidation, Decimal)
        assert isinstance(balance.total_cash, Decimal)
        assert isinstance(balance.buying_power, Decimal)
        # Paper Trading accounts have initial capital
        assert balance.net_liquidation > Decimal("0")

    async def test_get_positions(self, cp_client: CPClient, paper_account_id: str) -> None:
        """Verify positions retrieval returns a list."""
        positions = await cp_client.get_positions(paper_account_id)
        assert isinstance(positions, list)
        for pos in positions:
            assert isinstance(pos.position, Decimal)
            assert isinstance(pos.symbol, str)
