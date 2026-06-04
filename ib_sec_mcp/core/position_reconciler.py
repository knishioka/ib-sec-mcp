"""Reconcile live (Client Portal) positions against historical (Flex) snapshots.

The project carries two parallel, incompatible position representations:

- :class:`~ib_sec_mcp.api.cp_models.CPPosition` — real-time positions fetched
  live from the IB Client Portal Gateway (JSON).
- :class:`~ib_sec_mcp.models.position.Position` — historical positions parsed
  from Flex Query XML and persisted as daily snapshots in SQLite (read back as
  plain ``dict`` rows by :class:`~ib_sec_mcp.storage.PositionStore`).

This module normalizes both sides onto a single common view keyed by a
normalized symbol and computes the differences (newly opened, closed, quantity
changed, and valuation deltas) so they can be presented in one reconciliation
view.

The reconciler is pure and side-effect free: it takes already-fetched live and
snapshot data and returns a typed result. Data fetching, gateway connectivity,
and graceful degradation are handled by the MCP tool layer; this module only
needs to be told whether live data is available via ``live_available``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from ib_sec_mcp.api.cp_models import CPPosition

__all__ = [
    "ReconcileStatus",
    "ReconciledPosition",
    "ReconciliationResult",
    "ReconciliationSummary",
    "normalize_symbol",
    "reconcile_positions",
]


def normalize_symbol(symbol: str | None) -> str:
    """Normalize a trading symbol for cross-source matching.

    Live (CP) and historical (Flex) symbols may differ in casing or surrounding
    whitespace. Normalization upper-cases and strips so the same instrument
    matches across both sources.

    Args:
        symbol: Raw symbol from either source (may be ``None`` or empty).

    Returns:
        The normalized symbol (upper-cased, stripped). Empty string if the
        input is ``None`` or blank.
    """
    if not symbol:
        return ""
    return symbol.strip().upper()


class ReconcileStatus(StrEnum):
    """Status of a position when reconciling live vs snapshot."""

    NEW = "new"
    """Present live but absent from the snapshot (opened since the snapshot)."""

    CLOSED = "closed"
    """Present in the snapshot but absent live (closed since the snapshot)."""

    QUANTITY_CHANGED = "quantity_changed"
    """Present in both with a different quantity."""

    UNCHANGED = "unchanged"
    """Present in both with the same quantity (valuation may still differ)."""

    SNAPSHOT_ONLY = "snapshot_only"
    """Live data unavailable; entry sourced from the snapshot only (degraded)."""


class ReconciledPosition(BaseModel):
    """A single instrument reconciled across live and snapshot sources."""

    symbol: str = Field(..., description="Normalized trading symbol")
    status: ReconcileStatus = Field(..., description="Reconciliation status")

    in_live: bool = Field(..., description="Present in live (CP) data")
    in_snapshot: bool = Field(..., description="Present in the historical snapshot")

    live_quantity: Decimal | None = Field(None, description="Live position quantity")
    snapshot_quantity: Decimal | None = Field(None, description="Snapshot position quantity")
    quantity_diff: Decimal | None = Field(
        None, description="live - snapshot quantity (None when degraded)"
    )

    live_market_value: Decimal | None = Field(None, description="Live market value")
    snapshot_market_value: Decimal | None = Field(None, description="Snapshot position value")
    market_value_diff: Decimal | None = Field(
        None, description="live - snapshot market value (None when degraded)"
    )

    live_unrealized_pnl: Decimal | None = Field(None, description="Live unrealized P&L")
    snapshot_unrealized_pnl: Decimal | None = Field(None, description="Snapshot unrealized P&L")
    unrealized_pnl_diff: Decimal | None = Field(
        None, description="live - snapshot unrealized P&L (None when degraded)"
    )


class ReconciliationSummary(BaseModel):
    """Aggregate counts and totals for a reconciliation."""

    total_symbols: int = Field(..., description="Total distinct symbols reconciled")
    new_count: int = Field(0, description="Positions opened since the snapshot")
    closed_count: int = Field(0, description="Positions closed since the snapshot")
    quantity_changed_count: int = Field(0, description="Positions with a changed quantity")
    unchanged_count: int = Field(0, description="Positions with an unchanged quantity")
    snapshot_only_count: int = Field(0, description="Snapshot-only entries (degraded mode)")
    total_market_value_diff: Decimal = Field(
        Decimal("0"), description="Sum of live - snapshot market value across matched positions"
    )


class ReconciliationResult(BaseModel):
    """Full reconciliation of live vs snapshot positions for one account."""

    account_id: str = Field(..., description="Account ID")
    snapshot_date: str | None = Field(None, description="Snapshot date used (ISO), if any")
    live_available: bool = Field(..., description="Whether live (CP) data was available")
    degraded: bool = Field(
        ..., description="True when live data was unavailable (snapshot-only view)"
    )
    positions: list[ReconciledPosition] = Field(
        default_factory=list, description="Reconciled positions sorted by symbol"
    )
    summary: ReconciliationSummary = Field(..., description="Aggregate reconciliation summary")


class _CommonPosition:
    """Normalized intermediate view of a position from either source."""

    __slots__ = ("market_value", "quantity", "symbol", "unrealized_pnl")

    def __init__(
        self,
        symbol: str,
        quantity: Decimal,
        market_value: Decimal,
        unrealized_pnl: Decimal,
    ) -> None:
        self.symbol = symbol
        self.quantity = quantity
        self.market_value = market_value
        self.unrealized_pnl = unrealized_pnl


def _key(symbol: str, fallback: str) -> str:
    """Return a stable match key, falling back when the symbol is blank."""
    normalized = normalize_symbol(symbol)
    return normalized if normalized else fallback


def _from_cp(pos: CPPosition) -> tuple[str, _CommonPosition]:
    """Normalize a live CPPosition into a common view keyed for matching."""
    key = _key(pos.symbol, f"CONID:{pos.contract_id}")
    return key, _CommonPosition(
        symbol=key,
        quantity=pos.position,
        market_value=pos.market_value,
        unrealized_pnl=pos.unrealized_pnl,
    )


def _as_decimal(value: Any) -> Decimal:
    """Coerce a snapshot field (Decimal/str/number) to Decimal, default 0."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _from_snapshot(row: Mapping[str, Any]) -> tuple[str, _CommonPosition]:
    """Normalize a snapshot row (dict from PositionStore) into a common view."""
    symbol = str(row.get("symbol", ""))
    key = _key(symbol, symbol)
    return key, _CommonPosition(
        symbol=key,
        quantity=_as_decimal(row.get("quantity")),
        market_value=_as_decimal(row.get("position_value")),
        unrealized_pnl=_as_decimal(row.get("unrealized_pnl")),
    )


def _reconcile_one(
    key: str,
    live: _CommonPosition | None,
    snap: _CommonPosition | None,
) -> ReconciledPosition:
    """Reconcile a single symbol that appears live, in the snapshot, or both."""
    in_live = live is not None
    in_snapshot = snap is not None

    live_qty = live.quantity if live else None
    snap_qty = snap.quantity if snap else None
    live_mv = live.market_value if live else None
    snap_mv = snap.market_value if snap else None
    live_pnl = live.unrealized_pnl if live else None
    snap_pnl = snap.unrealized_pnl if snap else None

    # Diffs treat a missing side as zero so the magnitude is meaningful for
    # newly opened (full live qty) and closed (negative snapshot qty) positions.
    quantity_diff = (live_qty or Decimal("0")) - (snap_qty or Decimal("0"))
    market_value_diff = (live_mv or Decimal("0")) - (snap_mv or Decimal("0"))
    unrealized_pnl_diff = (live_pnl or Decimal("0")) - (snap_pnl or Decimal("0"))

    if in_live and not in_snapshot:
        status = ReconcileStatus.NEW
    elif in_snapshot and not in_live:
        status = ReconcileStatus.CLOSED
    elif live_qty == snap_qty:
        status = ReconcileStatus.UNCHANGED
    else:
        status = ReconcileStatus.QUANTITY_CHANGED

    return ReconciledPosition(
        symbol=key,
        status=status,
        in_live=in_live,
        in_snapshot=in_snapshot,
        live_quantity=live_qty,
        snapshot_quantity=snap_qty,
        quantity_diff=quantity_diff,
        live_market_value=live_mv,
        snapshot_market_value=snap_mv,
        market_value_diff=market_value_diff,
        live_unrealized_pnl=live_pnl,
        snapshot_unrealized_pnl=snap_pnl,
        unrealized_pnl_diff=unrealized_pnl_diff,
    )


def _snapshot_only(key: str, snap: _CommonPosition) -> ReconciledPosition:
    """Build a degraded (snapshot-only) entry when live data is unavailable."""
    return ReconciledPosition(
        symbol=key,
        status=ReconcileStatus.SNAPSHOT_ONLY,
        in_live=False,
        in_snapshot=True,
        live_quantity=None,
        snapshot_quantity=snap.quantity,
        quantity_diff=None,
        live_market_value=None,
        snapshot_market_value=snap.market_value,
        market_value_diff=None,
        live_unrealized_pnl=None,
        snapshot_unrealized_pnl=snap.unrealized_pnl,
        unrealized_pnl_diff=None,
    )


def _summarize(positions: Sequence[ReconciledPosition]) -> ReconciliationSummary:
    """Compute aggregate counts and the total matched market-value delta."""
    counts: dict[ReconcileStatus, int] = dict.fromkeys(ReconcileStatus, 0)
    total_mv_diff = Decimal("0")
    for pos in positions:
        counts[pos.status] += 1
        # Only sum the delta for positions present on both sides (matched).
        if pos.in_live and pos.in_snapshot and pos.market_value_diff is not None:
            total_mv_diff += pos.market_value_diff

    return ReconciliationSummary(
        total_symbols=len(positions),
        new_count=counts[ReconcileStatus.NEW],
        closed_count=counts[ReconcileStatus.CLOSED],
        quantity_changed_count=counts[ReconcileStatus.QUANTITY_CHANGED],
        unchanged_count=counts[ReconcileStatus.UNCHANGED],
        snapshot_only_count=counts[ReconcileStatus.SNAPSHOT_ONLY],
        total_market_value_diff=total_mv_diff,
    )


def reconcile_positions(
    account_id: str,
    live_positions: Sequence[CPPosition],
    snapshot_positions: Sequence[Mapping[str, Any]],
    snapshot_date: str | None = None,
    live_available: bool = True,
) -> ReconciliationResult:
    """Reconcile live (CP) positions against a historical (Flex) snapshot.

    Args:
        account_id: Account ID the positions belong to.
        live_positions: Live positions from the Client Portal Gateway. Ignored
            when ``live_available`` is ``False``.
        snapshot_positions: Snapshot rows as returned by
            :meth:`~ib_sec_mcp.storage.PositionStore.get_portfolio_snapshot`.
        snapshot_date: ISO date of the snapshot used, for reporting.
        live_available: Whether live data could be fetched. When ``False`` the
            result degrades to a snapshot-only view (no diffs) and ``degraded``
            is set.

    Returns:
        A :class:`ReconciliationResult` with per-symbol entries sorted by symbol
        and an aggregate summary.
    """
    snap_map: dict[str, _CommonPosition] = {}
    for row in snapshot_positions:
        key, common = _from_snapshot(row)
        snap_map[key] = common

    # Degraded mode: present snapshot positions only, with no diffs.
    if not live_available:
        positions = [_snapshot_only(key, snap_map[key]) for key in sorted(snap_map)]
        return ReconciliationResult(
            account_id=account_id,
            snapshot_date=snapshot_date,
            live_available=False,
            degraded=True,
            positions=positions,
            summary=_summarize(positions),
        )

    live_map: dict[str, _CommonPosition] = {}
    for pos in live_positions:
        key, common = _from_cp(pos)
        live_map[key] = common

    all_keys = sorted(set(live_map) | set(snap_map))
    positions = [_reconcile_one(key, live_map.get(key), snap_map.get(key)) for key in all_keys]

    return ReconciliationResult(
        account_id=account_id,
        snapshot_date=snapshot_date,
        live_available=True,
        degraded=False,
        positions=positions,
        summary=_summarize(positions),
    )
