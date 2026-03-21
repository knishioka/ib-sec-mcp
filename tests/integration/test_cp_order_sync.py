"""Integration tests for order sync between IB Gateway and local DB"""

import asyncio
from decimal import Decimal
from pathlib import Path

from ib_sec_mcp.api.cp_client import CPClient
from ib_sec_mcp.api.cp_models import (
    CPOrderRequest,
    CPOrderSide,
    CPOrderType,
)
from ib_sec_mcp.storage.limit_order_store import LimitOrderStore
from ib_sec_mcp.storage.order_sync import sync_orders_from_ib, try_sync_from_ib

AAPL_CONID = 265598


class TestOrderSync:
    """Test sync between IB live orders and local DB"""

    async def test_sync_with_no_local_orders(
        self,
        cp_client: CPClient,
        tmp_path: Path,
    ) -> None:
        """Sync should add IB orders to an empty local DB."""
        store = LimitOrderStore(tmp_path / "test_sync.db")
        result = await sync_orders_from_ib(cp_client, store)

        assert result.errors == []
        assert result.total_processed >= 0
        # added + updated + skipped == total_processed
        assert result.added + result.updated + result.skipped == result.total_processed

    async def test_sync_idempotent(
        self,
        cp_client: CPClient,
        tmp_path: Path,
    ) -> None:
        """Running sync twice should not duplicate orders."""
        store = LimitOrderStore(tmp_path / "test_idempotent.db")

        await sync_orders_from_ib(cp_client, store)
        result2 = await sync_orders_from_ib(cp_client, store)

        # Second sync should add 0 new orders
        assert result2.added == 0
        assert result2.errors == []

    async def test_sync_after_placing_order(
        self,
        cp_client: CPClient,
        paper_account_id: str,
        cleanup_orders: list[int],
        tmp_path: Path,
    ) -> None:
        """Place an order via API, then sync should capture it in local DB."""
        store = LimitOrderStore(tmp_path / "test_place_sync.db")

        # Place a test order
        order = CPOrderRequest(
            account_id=paper_account_id,
            contract_id=AAPL_CONID,
            side=CPOrderSide.BUY,
            quantity=Decimal("1"),
            order_type=CPOrderType.LIMIT,
            price=Decimal("1.06"),
            tif="DAY",
        )
        replies = await cp_client.place_order(order)
        assert replies, "Order placement should return at least one reply"
        order_id = int(replies[0].order_id) if replies[0].order_id else None
        assert order_id is not None, "Order placement should return an order ID"
        cleanup_orders.append(order_id)

        await asyncio.sleep(1)

        # Sync
        result = await sync_orders_from_ib(cp_client, store)
        assert result.errors == []
        assert result.added > 0

        # Verify order is in local DB
        history = store.get_order_history()
        aapl_orders = [o for o in history if o["symbol"] == "AAPL"]
        assert len(aapl_orders) > 0

    async def test_sync_after_cancel_updates_status(
        self,
        cp_client: CPClient,
        paper_account_id: str,
        tmp_path: Path,
    ) -> None:
        """Cancel an order, then sync should update local DB status."""
        store = LimitOrderStore(tmp_path / "test_cancel_sync.db")

        # Place and then cancel
        order = CPOrderRequest(
            account_id=paper_account_id,
            contract_id=AAPL_CONID,
            side=CPOrderSide.BUY,
            quantity=Decimal("1"),
            order_type=CPOrderType.LIMIT,
            price=Decimal("1.07"),
            tif="DAY",
        )
        replies = await cp_client.place_order(order)
        order_id = int(replies[0].order_id) if replies[0].order_id else None
        assert order_id is not None

        await asyncio.sleep(1)

        # First sync — captures the active order
        result1 = await sync_orders_from_ib(cp_client, store)
        assert result1.errors == []

        # Cancel the order
        await cp_client.cancel_order(paper_account_id, order_id)
        await asyncio.sleep(2)

        # Second sync — should detect cancellation
        result2 = await sync_orders_from_ib(cp_client, store)
        assert result2.errors == []

        # Verify order status is CANCELLED in local DB
        history = store.get_order_history()
        synced = [
            o for o in history if o["symbol"] == "AAPL" and o["limit_price"] == Decimal("1.07")
        ]
        assert len(synced) > 0, "Synced order should exist in local DB"
        assert synced[0]["status"] == "CANCELLED", (
            f"Order should be CANCELLED after sync, got {synced[0]['status']}"
        )


class TestTrySyncFromIB:
    """Test the safe sync entry point"""

    async def test_try_sync_with_running_gateway(self, tmp_path: Path) -> None:
        """try_sync_from_ib should succeed when Gateway is running."""
        store = LimitOrderStore(tmp_path / "test_try_sync.db")
        result = await try_sync_from_ib(store)
        # Should return a SyncResult, not None
        assert result is not None
        assert result.errors == []

    async def test_try_sync_with_bad_url(self, tmp_path: Path) -> None:
        """try_sync_from_ib should return None when Gateway is unreachable."""
        store = LimitOrderStore(tmp_path / "test_bad_url.db")
        result = await try_sync_from_ib(store, gateway_url="https://localhost:59999")
        assert result is None
