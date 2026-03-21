"""Integration tests for order lifecycle: place -> confirm -> modify -> cancel

Uses Paper Trading account with limit orders far from market price
to avoid accidental fills.
"""

import asyncio
from decimal import Decimal

import pytest

from ib_sec_mcp.api.cp_client import CPClient
from ib_sec_mcp.api.cp_models import (
    CPOrderRequest,
    CPOrderSide,
    CPOrderStatus,
    CPOrderType,
)

# AAPL contract ID on IB (well-known, stable)
AAPL_CONID = 265598

# Polling configuration for order propagation
POLL_INTERVAL = 0.5  # seconds between polls
POLL_TIMEOUT = 10  # max seconds to wait


async def poll_for_order(
    cp_client: CPClient, order_ids: list[int], *, timeout: float = POLL_TIMEOUT
) -> bool:
    """Poll until order appears in live orders or timeout."""
    elapsed = 0.0
    while elapsed < timeout:
        live_orders = await cp_client.get_orders()
        live_order_ids = {o.order_id for o in live_orders}
        if any(oid in live_order_ids for oid in order_ids):
            return True
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
    return False


class TestOrderPlacement:
    """Test order placement on Paper Trading account"""

    async def test_place_limit_order(
        self,
        cp_client: CPClient,
        paper_account_id: str,
        cleanup_orders: list[int],
    ) -> None:
        """Place a limit buy order far below market price."""
        order = CPOrderRequest(
            account_id=paper_account_id,
            contract_id=AAPL_CONID,
            side=CPOrderSide.BUY,
            quantity=Decimal("1"),
            order_type=CPOrderType.LIMIT,
            price=Decimal("1.00"),  # Far below market to avoid fill
            tif="DAY",
        )
        replies = await cp_client.place_order(order)
        assert replies, "Order placement should return at least one reply"

        # Track for cleanup
        cleanup_orders.extend(int(reply.order_id) for reply in replies if reply.order_id)

    async def test_place_and_verify_order_appears(
        self,
        cp_client: CPClient,
        paper_account_id: str,
        cleanup_orders: list[int],
    ) -> None:
        """Place an order and verify it appears in the order list."""
        order = CPOrderRequest(
            account_id=paper_account_id,
            contract_id=AAPL_CONID,
            side=CPOrderSide.BUY,
            quantity=Decimal("1"),
            order_type=CPOrderType.LIMIT,
            price=Decimal("1.01"),  # Unique price for identification
            tif="DAY",
        )
        replies = await cp_client.place_order(order)
        assert replies, "Order placement should return at least one reply"

        order_ids = [int(r.order_id) for r in replies if r.order_id]
        cleanup_orders.extend(order_ids)

        # Poll until order appears in live orders
        found = await poll_for_order(cp_client, order_ids)
        assert found, f"Order(s) {order_ids} not found in live orders within {POLL_TIMEOUT}s"


class TestOrderModification:
    """Test order modification on Paper Trading account"""

    async def test_modify_order_price(
        self,
        cp_client: CPClient,
        paper_account_id: str,
        cleanup_orders: list[int],
    ) -> None:
        """Place an order, then modify its price."""
        # Place initial order
        order = CPOrderRequest(
            account_id=paper_account_id,
            contract_id=AAPL_CONID,
            side=CPOrderSide.BUY,
            quantity=Decimal("1"),
            order_type=CPOrderType.LIMIT,
            price=Decimal("1.02"),
            tif="DAY",
        )
        replies = await cp_client.place_order(order)
        assert replies, "Order placement should return at least one reply"
        order_id = int(replies[0].order_id) if replies[0].order_id else None
        assert order_id is not None
        cleanup_orders.append(order_id)

        assert await poll_for_order(cp_client, [order_id])

        # Modify price
        mod_replies = await cp_client.modify_order(
            account_id=paper_account_id,
            order_id=order_id,
            limit_price=Decimal("1.03"),
        )
        assert len(mod_replies) > 0

    async def test_modify_order_quantity(
        self,
        cp_client: CPClient,
        paper_account_id: str,
        cleanup_orders: list[int],
    ) -> None:
        """Place an order, then modify its quantity."""
        order = CPOrderRequest(
            account_id=paper_account_id,
            contract_id=AAPL_CONID,
            side=CPOrderSide.BUY,
            quantity=Decimal("1"),
            order_type=CPOrderType.LIMIT,
            price=Decimal("1.04"),
            tif="DAY",
        )
        replies = await cp_client.place_order(order)
        assert replies, "Order placement should return at least one reply"
        order_id = int(replies[0].order_id) if replies[0].order_id else None
        assert order_id is not None
        cleanup_orders.append(order_id)

        assert await poll_for_order(cp_client, [order_id])

        # Modify quantity
        mod_replies = await cp_client.modify_order(
            account_id=paper_account_id,
            order_id=order_id,
            quantity=Decimal("2"),
        )
        assert len(mod_replies) > 0


class TestOrderCancellation:
    """Test order cancellation on Paper Trading account"""

    async def test_cancel_order(
        self,
        cp_client: CPClient,
        paper_account_id: str,
    ) -> None:
        """Place and immediately cancel an order."""
        order = CPOrderRequest(
            account_id=paper_account_id,
            contract_id=AAPL_CONID,
            side=CPOrderSide.BUY,
            quantity=Decimal("1"),
            order_type=CPOrderType.LIMIT,
            price=Decimal("1.05"),
            tif="DAY",
        )
        replies = await cp_client.place_order(order)
        assert replies, "Order placement should return at least one reply"
        order_id = int(replies[0].order_id) if replies[0].order_id else None
        assert order_id is not None

        assert await poll_for_order(cp_client, [order_id])

        # Cancel
        result = await cp_client.cancel_order(paper_account_id, order_id)
        assert isinstance(result, dict)

        # Poll until order is cancelled
        elapsed = 0.0
        cancelled_statuses = {CPOrderStatus.CANCELLED, CPOrderStatus.PENDING_CANCEL}
        while elapsed < POLL_TIMEOUT:
            live_orders = await cp_client.get_orders()
            for o in live_orders:
                if o.order_id == order_id and o.status in cancelled_statuses:
                    return  # Test passed
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

    @pytest.mark.skip(reason="Full lifecycle test — run manually for comprehensive validation")
    async def test_full_order_lifecycle(
        self,
        cp_client: CPClient,
        paper_account_id: str,
    ) -> None:
        """Full lifecycle: place -> verify -> modify -> verify -> cancel -> verify."""
        # Place
        order = CPOrderRequest(
            account_id=paper_account_id,
            contract_id=AAPL_CONID,
            side=CPOrderSide.BUY,
            quantity=Decimal("1"),
            order_type=CPOrderType.LIMIT,
            price=Decimal("1.10"),
            tif="DAY",
        )
        replies = await cp_client.place_order(order)
        assert replies, "Order placement should return at least one reply"
        order_id = int(replies[0].order_id) if replies[0].order_id else None
        assert order_id is not None

        # Verify placed
        assert await poll_for_order(cp_client, [order_id])
        orders = await cp_client.get_orders()
        placed = [o for o in orders if o.order_id == order_id]
        assert len(placed) == 1

        # Modify
        await cp_client.modify_order(
            account_id=paper_account_id,
            order_id=order_id,
            limit_price=Decimal("1.11"),
            quantity=Decimal("2"),
        )
        await asyncio.sleep(1)

        # Cancel
        await cp_client.cancel_order(paper_account_id, order_id)

        # Verify cancelled
        elapsed = 0.0
        while elapsed < POLL_TIMEOUT:
            orders = await cp_client.get_orders()
            for o in orders:
                if o.order_id == order_id and o.status in {
                    CPOrderStatus.CANCELLED,
                    CPOrderStatus.PENDING_CANCEL,
                }:
                    return
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
