"""Position reconciliation MCP tool.

Provides a unified position view that reconciles real-time positions from the
IB Client Portal Gateway against the most recent historical snapshot stored in
SQLite (parsed from Flex Query data). See
:mod:`ib_sec_mcp.core.position_reconciler` for the normalization and diff logic.

The tool degrades gracefully: when the CP Gateway is not running or the session
has expired, it falls back to a snapshot-only view rather than failing.
"""

from __future__ import annotations

import json
from datetime import date

from fastmcp import Context, FastMCP

from ib_sec_mcp.api.cp_client import (
    CPAuthenticationError,
    CPClient,
    CPConnectionError,
)
from ib_sec_mcp.api.cp_models import CPPosition
from ib_sec_mcp.core.position_reconciler import reconcile_positions
from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.storage import PositionStore

DEFAULT_DB_PATH = "data/processed/positions.db"


async def _fetch_live_positions(
    account_id: str | None,
    ctx: Context | None = None,
) -> tuple[str | None, list[CPPosition], bool]:
    """Fetch live positions from the CP Gateway, degrading gracefully.

    Args:
        account_id: Account ID, or ``None`` to auto-resolve the first account.
        ctx: MCP context for logging.

    Returns:
        Tuple of ``(resolved_account_id, positions, live_available)``. When the
        gateway is unreachable or the session expired, ``live_available`` is
        ``False`` and ``positions`` is empty; ``resolved_account_id`` falls back
        to the supplied ``account_id``.
    """
    try:
        async with CPClient() as client:
            resolved = account_id
            if not resolved:
                accounts = await client.get_accounts()
                resolved = accounts[0] if accounts else None
            if not resolved:
                return account_id, [], True
            positions = await client.get_positions(resolved)
            return resolved, positions, True
    except (CPConnectionError, CPAuthenticationError) as e:
        if ctx:
            await ctx.warning(
                f"Live positions unavailable ({e!s}); falling back to snapshot-only view"
            )
        return account_id, [], False


def register_position_reconcile_tools(mcp: FastMCP) -> None:
    """Register the position reconciliation tool."""

    @mcp.tool
    async def reconcile_positions_view(
        account_id: str | None = None,
        snapshot_date: str | None = None,
        db_path: str = DEFAULT_DB_PATH,
        ctx: Context | None = None,
    ) -> str:
        """
        Reconcile live (CP Gateway) positions against the latest stored snapshot

        Produces a single unified view that compares real-time broker positions
        with the most recent historical snapshot (parsed from Flex Query data),
        flagging newly opened, closed, and quantity-changed positions along with
        market value and unrealized P&L deltas.

        Degrades gracefully: if the IB Client Portal Gateway is not running or
        the session has expired, returns a snapshot-only view with
        ``degraded: true`` instead of failing.

        Args:
            account_id: IB account ID. When omitted, the first account from the
                gateway is used (requires the gateway to be running).
            snapshot_date: Snapshot date in YYYY-MM-DD format. Defaults to the
                most recent available snapshot for the account.
            db_path: Path to the SQLite snapshot database
                (default: data/processed/positions.db).
            ctx: MCP context for logging.

        Returns:
            JSON string with the reconciliation result including per-symbol
            entries (status, quantities, values, and diffs) and a summary.

        Example:
            >>> result = await reconcile_positions_view(account_id="U1234567")
        """
        # Validate snapshot_date early if provided.
        requested_date: date | None = None
        if snapshot_date:
            try:
                requested_date = date.fromisoformat(snapshot_date)
            except ValueError as e:
                raise ValidationError(
                    f"Invalid snapshot_date '{snapshot_date}': expected YYYY-MM-DD"
                ) from e

        if ctx:
            await ctx.info(
                "Reconciling live positions against snapshot",
                extra={"account_id": account_id, "snapshot_date": snapshot_date},
            )

        # Fetch live positions (graceful degradation on gateway issues).
        resolved_account, live_positions, live_available = await _fetch_live_positions(
            account_id, ctx
        )

        if not resolved_account:
            raise ValidationError(
                "account_id is required: the CP Gateway is unavailable to "
                "auto-resolve an account. Provide account_id explicitly."
            )

        # Resolve snapshot date and load snapshot positions.
        store = PositionStore(db_path)
        try:
            effective_date = requested_date
            if effective_date is None:
                available = store.get_available_dates(resolved_account)
                effective_date = date.fromisoformat(available[0]) if available else None

            snapshot_positions = (
                store.get_portfolio_snapshot(resolved_account, effective_date)
                if effective_date is not None
                else []
            )
        finally:
            store.close()

        result = reconcile_positions(
            account_id=resolved_account,
            live_positions=live_positions,
            snapshot_positions=snapshot_positions,
            snapshot_date=effective_date.isoformat() if effective_date else None,
            live_available=live_available,
        )

        if ctx:
            await ctx.info(
                f"Reconciliation complete: {result.summary.total_symbols} symbols "
                f"(degraded={result.degraded})"
            )

        return json.dumps(result.model_dump(), indent=2, default=str)


__all__ = ["register_position_reconcile_tools"]
