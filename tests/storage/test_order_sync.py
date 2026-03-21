"""Tests for order sync logic (IB → local DB)"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from ib_sec_mcp.api.cp_client import CPConnectionError
from ib_sec_mcp.api.cp_models import CPAuthStatus, CPOrder, CPOrderSide, CPOrderStatus
from ib_sec_mcp.storage.limit_order_store import LimitOrderStore
from ib_sec_mcp.storage.order_sync import (
    SyncResult,
    sync_orders_from_ib,
    sync_orders_to_ib,
    try_sync_from_ib,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path) -> LimitOrderStore:
    """Fresh LimitOrderStore with test DB"""
    return LimitOrderStore(tmp_path / "test.db")


@pytest.fixture()
def mock_cp_client() -> AsyncMock:
    """Mock CPClient"""
    client = AsyncMock()
    client.get_orders = AsyncMock(return_value=[])
    client.check_auth_status = AsyncMock(
        return_value=CPAuthStatus(authenticated=True, connected=True)
    )
    return client


def _make_ib_order(
    symbol: str = "CSPX",
    side: CPOrderSide = CPOrderSide.BUY,
    price: str = "700.00",
    quantity: str = "10",
    status: CPOrderStatus = CPOrderStatus.SUBMITTED,
    avg_price: str = "0",
    order_id: int = 1001,
) -> CPOrder:
    """Create a CPOrder for testing"""
    return CPOrder(
        orderId=order_id,
        symbol=symbol,
        side=side,
        totalSize=Decimal(quantity),
        price=Decimal(price),
        avgPrice=Decimal(avg_price),
        status=status,
        orderType="LMT",
        acct="U1234567",
    )


# ---------------------------------------------------------------------------
# Tests: SyncResult
# ---------------------------------------------------------------------------


class TestSyncResult:
    def test_empty_result(self) -> None:
        result = SyncResult()
        assert result.added == 0
        assert result.updated == 0
        assert result.skipped == 0
        assert result.errors == []
        assert result.total_processed == 0

    def test_to_dict(self) -> None:
        result = SyncResult(added=2, updated=1, skipped=3, errors=["err1"])
        d = result.to_dict()
        assert d["added"] == 2
        assert d["updated"] == 1
        assert d["skipped"] == 3
        assert d["errors"] == ["err1"]
        assert d["total_processed"] == 6


# ---------------------------------------------------------------------------
# Tests: sync_orders_from_ib — new orders
# ---------------------------------------------------------------------------


class TestSyncNewOrders:
    @pytest.mark.asyncio
    async def test_new_ib_order_added_to_db(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """IB order not in DB should be added"""
        mock_cp_client.get_orders.return_value = [
            _make_ib_order(symbol="CSPX", price="700.00", status=CPOrderStatus.SUBMITTED)
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.added == 1
        assert result.updated == 0
        orders = store.get_pending_orders()
        assert len(orders) == 1
        assert orders[0]["symbol"] == "CSPX"
        assert orders[0]["limit_price"] == Decimal("700.00")
        assert orders[0]["order_type"] == "BUY"
        assert orders[0]["notes"] == "Synced from IB"

    @pytest.mark.asyncio
    async def test_multiple_new_orders_added(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """Multiple new IB orders should all be added"""
        mock_cp_client.get_orders.return_value = [
            _make_ib_order(symbol="CSPX", price="700.00", order_id=1001),
            _make_ib_order(symbol="VWRA", price="100.00", order_id=1002),
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.added == 2
        orders = store.get_pending_orders()
        assert len(orders) == 2

    @pytest.mark.asyncio
    async def test_new_filled_order_added_with_status(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """New IB order already filled should be added with FILLED status"""
        mock_cp_client.get_orders.return_value = [
            _make_ib_order(
                symbol="CSPX",
                price="700.00",
                status=CPOrderStatus.FILLED,
                avg_price="695.50",
            )
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.added == 1
        history = store.get_order_history(symbol="CSPX")
        assert len(history) == 1
        assert history[0]["status"] == "FILLED"
        assert history[0]["filled_price"] == Decimal("695.50")


# ---------------------------------------------------------------------------
# Tests: sync_orders_from_ib — filled orders
# ---------------------------------------------------------------------------


class TestSyncFilledOrders:
    @pytest.mark.asyncio
    async def test_pending_order_filled_on_ib(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """Pending local order that is filled on IB should be updated"""
        from datetime import date

        # Add a pending order locally
        store.add_order(
            symbol="CSPX",
            market="LSE",
            order_type="BUY",
            limit_price=Decimal("700.00"),
            created_date=date.today(),
        )

        mock_cp_client.get_orders.return_value = [
            _make_ib_order(
                symbol="CSPX",
                price="700.00",
                status=CPOrderStatus.FILLED,
                avg_price="698.00",
            )
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.updated == 1
        history = store.get_order_history(symbol="CSPX")
        assert history[0]["status"] == "FILLED"
        assert history[0]["filled_price"] == Decimal("698.00")

    @pytest.mark.asyncio
    async def test_filled_order_uses_limit_price_when_no_avg(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """When avg_price is 0, filled_price should fall back to limit_price"""
        from datetime import date

        store.add_order(
            symbol="CSPX",
            market="LSE",
            order_type="BUY",
            limit_price=Decimal("700.00"),
            created_date=date.today(),
        )

        mock_cp_client.get_orders.return_value = [
            _make_ib_order(
                symbol="CSPX",
                price="700.00",
                status=CPOrderStatus.FILLED,
                avg_price="0",
            )
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.updated == 1
        history = store.get_order_history(symbol="CSPX")
        assert history[0]["filled_price"] == Decimal("700.00")


# ---------------------------------------------------------------------------
# Tests: sync_orders_from_ib — cancelled orders
# ---------------------------------------------------------------------------


class TestSyncCancelledOrders:
    @pytest.mark.asyncio
    async def test_pending_order_cancelled_on_ib(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """Pending local order cancelled on IB should be updated"""
        from datetime import date

        store.add_order(
            symbol="CSPX",
            market="LSE",
            order_type="BUY",
            limit_price=Decimal("700.00"),
            created_date=date.today(),
        )

        mock_cp_client.get_orders.return_value = [
            _make_ib_order(
                symbol="CSPX",
                price="700.00",
                status=CPOrderStatus.CANCELLED,
            )
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.updated == 1
        history = store.get_order_history(symbol="CSPX")
        assert history[0]["status"] == "CANCELLED"

    @pytest.mark.asyncio
    async def test_inactive_order_treated_as_cancelled(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """IB Inactive status should be treated as CANCELLED"""
        from datetime import date

        store.add_order(
            symbol="CSPX",
            market="LSE",
            order_type="BUY",
            limit_price=Decimal("700.00"),
            created_date=date.today(),
        )

        mock_cp_client.get_orders.return_value = [
            _make_ib_order(
                symbol="CSPX",
                price="700.00",
                status=CPOrderStatus.INACTIVE,
            )
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.updated == 1
        history = store.get_order_history(symbol="CSPX")
        assert history[0]["status"] == "CANCELLED"


# ---------------------------------------------------------------------------
# Tests: sync_orders_from_ib — matching and skipping
# ---------------------------------------------------------------------------


class TestSyncMatching:
    @pytest.mark.asyncio
    async def test_existing_pending_order_no_change(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """Active IB order matching pending local order → skip"""
        from datetime import date

        store.add_order(
            symbol="CSPX",
            market="LSE",
            order_type="BUY",
            limit_price=Decimal("700.00"),
            created_date=date.today(),
        )

        mock_cp_client.get_orders.return_value = [
            _make_ib_order(symbol="CSPX", price="700.00", status=CPOrderStatus.SUBMITTED)
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.skipped == 1
        assert result.added == 0
        assert result.updated == 0

    @pytest.mark.asyncio
    async def test_matching_by_side(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """BUY and SELL at same price/symbol should not match"""
        from datetime import date

        store.add_order(
            symbol="CSPX",
            market="LSE",
            order_type="BUY",
            limit_price=Decimal("700.00"),
            created_date=date.today(),
        )

        # IB has a SELL order at same price
        mock_cp_client.get_orders.return_value = [
            _make_ib_order(
                symbol="CSPX",
                side=CPOrderSide.SELL,
                price="700.00",
                status=CPOrderStatus.SUBMITTED,
            )
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        # Should add as new (SELL doesn't match BUY)
        assert result.added == 1
        orders = store.get_pending_orders()
        assert len(orders) == 2

    @pytest.mark.asyncio
    async def test_cancelled_ib_order_not_in_db_skipped(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """Cancelled IB order with no local match should be skipped"""
        mock_cp_client.get_orders.return_value = [
            _make_ib_order(symbol="CSPX", price="700.00", status=CPOrderStatus.CANCELLED)
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.skipped == 1
        assert result.added == 0

    @pytest.mark.asyncio
    async def test_already_filled_in_db_skipped(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """IB order matching an already-filled local order should be skipped"""
        from datetime import date

        order_id = store.add_order(
            symbol="CSPX",
            market="LSE",
            order_type="BUY",
            limit_price=Decimal("700.00"),
            created_date=date.today(),
        )
        store.update_order(
            order_id=order_id,
            status="FILLED",
            filled_price=Decimal("695.00"),
            filled_date=date.today(),
        )

        mock_cp_client.get_orders.return_value = [
            _make_ib_order(symbol="CSPX", price="700.00", status=CPOrderStatus.FILLED)
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.skipped == 1
        assert result.added == 0
        assert result.updated == 0

    @pytest.mark.asyncio
    async def test_manual_orders_unaffected(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        """Manual orders not in IB should remain untouched"""
        from datetime import date

        store.add_order(
            symbol="MANUAL_STOCK",
            market="NYSE",
            order_type="BUY",
            limit_price=Decimal("50.00"),
            created_date=date.today(),
            notes="Manual entry",
        )

        # IB has different orders
        mock_cp_client.get_orders.return_value = [
            _make_ib_order(symbol="CSPX", price="700.00", status=CPOrderStatus.SUBMITTED)
        ]

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.added == 1  # CSPX added
        # Manual order still pending
        manual = store.get_pending_orders(symbol="MANUAL_STOCK")
        assert len(manual) == 1
        assert manual[0]["notes"] == "Manual entry"


# ---------------------------------------------------------------------------
# Tests: sync_orders_from_ib — error handling
# ---------------------------------------------------------------------------


class TestSyncErrorHandling:
    @pytest.mark.asyncio
    async def test_ib_api_failure(self, mock_cp_client: AsyncMock, store: LimitOrderStore) -> None:
        """Failure to fetch IB orders should return error in result"""
        mock_cp_client.get_orders.side_effect = Exception("API timeout")

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert len(result.errors) == 1
        assert "API timeout" in result.errors[0]
        assert result.added == 0

    @pytest.mark.asyncio
    async def test_empty_ib_orders(self, mock_cp_client: AsyncMock, store: LimitOrderStore) -> None:
        """Empty IB orders list should result in no changes"""
        mock_cp_client.get_orders.return_value = []

        result = await sync_orders_from_ib(mock_cp_client, store)

        assert result.added == 0
        assert result.updated == 0
        assert result.skipped == 0


# ---------------------------------------------------------------------------
# Tests: sync_orders_to_ib (Phase 2 stub)
# ---------------------------------------------------------------------------


class TestSyncToIB:
    @pytest.mark.asyncio
    async def test_raises_not_implemented(
        self, mock_cp_client: AsyncMock, store: LimitOrderStore
    ) -> None:
        with pytest.raises(NotImplementedError, match="Phase 2"):
            await sync_orders_to_ib(mock_cp_client, store)


# ---------------------------------------------------------------------------
# Tests: try_sync_from_ib (Gateway-safe wrapper)
# ---------------------------------------------------------------------------


class TestTrySyncFromIB:
    @pytest.mark.asyncio
    async def test_gateway_not_reachable_returns_none(self, store: LimitOrderStore) -> None:
        """When Gateway is not running, should return None (no error)"""
        with patch("ib_sec_mcp.storage.order_sync.CPClient", autospec=True) as mock_cls:
            mock_instance = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_instance.check_auth_status.side_effect = CPConnectionError("refused")

            # CPConnectionError during check_auth_status should be caught by the
            # except block, but actually the ensure_authenticated is called inside
            # get_orders. Let's mock the context manager properly.
            mock_ctx = AsyncMock()
            mock_ctx.check_auth_status.side_effect = CPConnectionError("Connection refused")
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)

            result = await try_sync_from_ib(store)

        assert result is None

    @pytest.mark.asyncio
    async def test_gateway_not_authenticated_returns_none(self, store: LimitOrderStore) -> None:
        """When Gateway is running but not authenticated, should return None"""
        with patch("ib_sec_mcp.storage.order_sync.CPClient", autospec=True) as mock_cls:
            mock_ctx = AsyncMock()
            mock_ctx.check_auth_status.return_value = CPAuthStatus(
                authenticated=False, connected=True
            )
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await try_sync_from_ib(store)

        assert result is None

    @pytest.mark.asyncio
    async def test_successful_sync(self, store: LimitOrderStore) -> None:
        """When Gateway is running and authenticated, should perform sync"""
        with patch("ib_sec_mcp.storage.order_sync.CPClient", autospec=True) as mock_cls:
            mock_ctx = AsyncMock()
            mock_ctx.check_auth_status.return_value = CPAuthStatus(
                authenticated=True, connected=True
            )
            mock_ctx.get_orders.return_value = [
                _make_ib_order(symbol="CSPX", price="700.00", status=CPOrderStatus.SUBMITTED)
            ]
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await try_sync_from_ib(store)

        assert result is not None
        assert result.added == 1
