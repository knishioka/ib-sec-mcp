"""Sync limit orders between IB Client Portal Gateway and local DB

Provides one-way sync from IB live orders to local limit_orders.db.
Matching logic: symbol + limit_price + order_type (BUY/SELL).
Conflict resolution: IB data is source of truth.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from ib_sec_mcp.api.cp_client import CPClient, CPConnectionError
from ib_sec_mcp.api.cp_models import CPOrder, CPOrderSide, CPOrderStatus
from ib_sec_mcp.storage.limit_order_store import LimitOrderStore
from ib_sec_mcp.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation"""

    added: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return self.added + self.updated + self.skipped

    def to_dict(self) -> dict[str, object]:
        return {
            "added": self.added,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
            "total_processed": self.total_processed,
        }


def _map_ib_side(side: CPOrderSide) -> str:
    """Map IB order side to local DB order_type"""
    return "BUY" if side == CPOrderSide.BUY else "SELL"


def _map_ib_status(status: CPOrderStatus) -> str | None:
    """Map IB order status to local DB status, or None if no update needed"""
    if status == CPOrderStatus.FILLED:
        return "FILLED"
    if status == CPOrderStatus.CANCELLED:
        return "CANCELLED"
    if status in (
        CPOrderStatus.SUBMITTED,
        CPOrderStatus.PRE_SUBMITTED,
        CPOrderStatus.PENDING_SUBMIT,
    ):
        return None  # Still active, no status change needed
    if status == CPOrderStatus.INACTIVE:
        return "CANCELLED"
    if status == CPOrderStatus.PENDING_CANCEL:
        return None  # Not yet cancelled
    return None


OrderKey = tuple[object, Decimal, object]
"""Match key: (symbol, limit_price, order_type)"""


def _build_order_map(
    orders: list[dict[str, object]],
) -> dict[OrderKey, dict[str, object]]:
    """Build a dict map keyed by (symbol, limit_price, order_type) for O(1) lookup"""
    result: dict[OrderKey, dict[str, object]] = {}
    for order in orders:
        key: OrderKey = (order["symbol"], Decimal(str(order["limit_price"])), order["order_type"])
        if key not in result:
            result[key] = order
    return result


async def sync_orders_from_ib(
    cp_client: CPClient,
    store: LimitOrderStore,
) -> SyncResult:
    """Sync IB live orders to local DB

    - New orders (IB has, DB doesn't) → add to DB
    - Filled orders (IB FILLED) → update DB status to FILLED
    - Cancelled orders (IB CANCELLED) → update DB status to CANCELLED
    - Existing match with same status → skip

    Args:
        cp_client: Authenticated CPClient instance
        store: LimitOrderStore instance

    Returns:
        SyncResult with counts of added/updated/skipped/errors
    """
    result = SyncResult()

    try:
        ib_orders = await cp_client.get_orders()
    except Exception as e:
        result.errors.append(f"Failed to fetch IB orders: {e}")
        return result

    # Get all local orders (pending + history) for matching
    all_local_orders = store.get_order_history()
    pending_orders = [o for o in all_local_orders if o["status"] == "PENDING"]

    # Build dict maps for O(1) lookup instead of O(N) list iteration
    pending_map = _build_order_map(pending_orders)
    all_orders_map = _build_order_map(all_local_orders)

    for ib_order in ib_orders:
        try:
            _process_single_order(ib_order, pending_map, all_orders_map, store, result)
        except Exception as e:
            result.errors.append(f"Error processing order {ib_order.symbol}: {e}")

    logger.info(
        "Sync complete: added=%d, updated=%d, skipped=%d, errors=%d",
        result.added,
        result.updated,
        result.skipped,
        len(result.errors),
    )
    return result


def _process_single_order(
    ib_order: CPOrder,
    pending_map: dict[OrderKey, dict[str, object]],
    all_orders_map: dict[OrderKey, dict[str, object]],
    store: LimitOrderStore,
    result: SyncResult,
) -> None:
    """Process a single IB order for sync"""
    symbol = ib_order.symbol
    limit_price = ib_order.price
    order_type = _map_ib_side(ib_order.side)
    db_status = _map_ib_status(ib_order.status)

    key: OrderKey = (symbol, limit_price, order_type)

    # Try to find matching order in pending orders first
    matched = pending_map.get(key)

    if matched is None:
        # Also check all orders (including terminal) to avoid re-adding
        if key in all_orders_map:
            # Already exists (possibly already filled/cancelled)
            result.skipped += 1
            return

        # New order: add to DB if it's an active order
        if db_status is None or db_status == "FILLED":
            # Active or filled IB order not in our DB → add it
            order_id = store.add_order(
                symbol=symbol,
                market="",  # IB doesn't provide market in order response
                order_type=order_type,
                limit_price=limit_price,
                created_date=date.today(),
                quantity=ib_order.quantity,
                notes="Synced from IB",
            )
            # If the order is already filled on IB, update status
            if db_status == "FILLED":
                filled_price = (
                    ib_order.avg_price if ib_order.avg_price > Decimal("0") else limit_price
                )
                store.update_order(
                    order_id=order_id,
                    status="FILLED",
                    filled_price=filled_price,
                    filled_date=date.today(),
                )
            result.added += 1
        elif db_status == "CANCELLED":
            # Don't add cancelled orders that were never in our DB
            result.skipped += 1
        else:
            result.skipped += 1
        return

    # Matched existing pending order
    if db_status is None:
        # Still active on IB, no change needed
        result.skipped += 1
        return

    matched_id: int = matched["id"]  # type: ignore[assignment]

    if db_status == "FILLED":
        filled_price = ib_order.avg_price if ib_order.avg_price > Decimal("0") else limit_price
        store.update_order(
            order_id=matched_id,
            status="FILLED",
            filled_price=filled_price,
            filled_date=date.today(),
        )
        result.updated += 1
    elif db_status == "CANCELLED":
        store.update_order(
            order_id=matched_id,
            status="CANCELLED",
        )
        result.updated += 1
    else:
        result.skipped += 1


async def sync_orders_to_ib(
    cp_client: CPClient,
    store: LimitOrderStore,
) -> SyncResult:
    """Sync local DB orders to IB (Phase 2 — not yet implemented)

    Args:
        cp_client: Authenticated CPClient instance
        store: LimitOrderStore instance

    Raises:
        NotImplementedError: Always, as this is reserved for Phase 2
    """
    raise NotImplementedError("sync_orders_to_ib is reserved for Phase 2")


async def try_sync_from_ib(
    store: LimitOrderStore,
    gateway_url: str | None = None,
) -> SyncResult | None:
    """Attempt to sync from IB, returning None if Gateway is not running

    This is the safe entry point for automated sync (e.g., /daily-check).
    It gracefully handles the case where Gateway is not running.

    Args:
        store: LimitOrderStore instance
        gateway_url: Optional gateway URL override

    Returns:
        SyncResult if sync was performed, None if Gateway was unreachable
    """
    try:
        async with CPClient(gateway_url=gateway_url, max_retries=1) as client:
            # Quick auth check — if it fails, Gateway is likely not running
            status = await client.check_auth_status()
            if not status.authenticated:
                logger.info("IB Gateway not authenticated, skipping sync")
                return None
            return await sync_orders_from_ib(client, store)
    except CPConnectionError:
        logger.info("IB Gateway not reachable, skipping order sync")
        return None
    except Exception as e:
        logger.warning("Unexpected error during order sync: %s", e)
        return None
