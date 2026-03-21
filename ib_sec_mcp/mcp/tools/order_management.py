"""Order placement and management MCP tools with safety mechanisms

Provides order placement, modification, and cancellation via IB Client Portal
Gateway API with multiple safety layers:
- Dry-run mode (default ON)
- Per-order amount limit
- Daily order amount limit
- Read-only mode
- Full order logging with account masking
"""

import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP

from ib_sec_mcp.api.cp_client import (
    CPAuthenticationError,
    CPClient,
    CPClientError,
    CPConnectionError,
)
from ib_sec_mcp.api.cp_models import (
    CPOrderReply,
    CPOrderRequest,
    CPOrderSide,
    CPOrderType,
)
from ib_sec_mcp.utils.logger import mask_sensitive

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GATEWAY_NOT_RUNNING_MSG = (
    "IB Client Portal Gateway is not running. Start the gateway and login at https://localhost:5000"
)

SESSION_EXPIRED_MSG = (
    "IB Client Portal session has expired. Please re-authenticate at https://localhost:5000"
)

READ_ONLY_MSG = (
    "Order management is disabled. IB_READ_ONLY=1 is set. "
    "Unset IB_READ_ONLY to enable order placement."
)

DEFAULT_MAX_ORDER_AMOUNT_USD = Decimal("50000")
DEFAULT_DAILY_ORDER_LIMIT_USD = Decimal("200000")
DEFAULT_ORDER_LOG_PATH = Path("data/processed/order_log.jsonl")


# ---------------------------------------------------------------------------
# Safety helpers (module-level for testability)
# ---------------------------------------------------------------------------


def is_read_only() -> bool:
    """Check if read-only mode is enabled via IB_READ_ONLY env var."""
    return os.environ.get("IB_READ_ONLY", "0") in ("1", "true", "yes")


def is_dry_run() -> bool:
    """Check if dry-run mode is enabled via IB_ORDER_DRY_RUN env var.

    Dry-run is ON by default — must be explicitly disabled.
    """
    val = os.environ.get("IB_ORDER_DRY_RUN", "1")
    return val not in ("0", "false", "no")


def get_max_order_amount() -> Decimal:
    """Get per-order maximum amount from IB_MAX_ORDER_AMOUNT_USD env var."""
    val = os.environ.get("IB_MAX_ORDER_AMOUNT_USD")
    if val:
        return Decimal(val)
    return DEFAULT_MAX_ORDER_AMOUNT_USD


def get_daily_order_limit() -> Decimal:
    """Get daily order limit from IB_DAILY_ORDER_LIMIT_USD env var."""
    val = os.environ.get("IB_DAILY_ORDER_LIMIT_USD")
    if val:
        return Decimal(val)
    return DEFAULT_DAILY_ORDER_LIMIT_USD


def get_order_log_path() -> Path:
    """Get order log file path from IB_ORDER_LOG_PATH env var."""
    val = os.environ.get("IB_ORDER_LOG_PATH")
    if val:
        return Path(val)
    return DEFAULT_ORDER_LOG_PATH


def estimate_order_amount(quantity: Decimal, price: Decimal | None) -> Decimal:
    """Estimate order amount in USD for limit checks.

    For market orders without a price, returns 0 (cannot validate).
    """
    if price is None or price == Decimal("0"):
        return Decimal("0")
    return abs(quantity * price)


def check_order_amount_limit(quantity: Decimal, price: Decimal | None) -> str | None:
    """Check if order exceeds per-order amount limit.

    Returns error message if exceeded, None if within limits.
    """
    amount = estimate_order_amount(quantity, price)
    if amount == Decimal("0"):
        return None
    max_amount = get_max_order_amount()
    if amount > max_amount:
        return (
            f"Order amount ${amount:.2f} exceeds per-order limit "
            f"${max_amount:.2f} (IB_MAX_ORDER_AMOUNT_USD)"
        )
    return None


def get_daily_total(log_path: Path) -> Decimal:
    """Calculate total order amount placed today from order log."""
    if not log_path.exists():
        return Decimal("0")

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    total = Decimal("0")

    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Only count actual submissions (not dry runs, not cancels)
            if record.get("dry_run", False):
                continue
            if record.get("action") != "place":
                continue
            if record.get("status") != "submitted":
                continue
            ts = record.get("timestamp", "")
            if not ts.startswith(today):
                continue
            qty = Decimal(str(record.get("quantity", "0")))
            price = Decimal(str(record.get("limit_price", "0")))
            total += abs(qty * price)

    return total


def check_daily_limit(quantity: Decimal, price: Decimal | None, log_path: Path) -> str | None:
    """Check if order would exceed daily limit.

    Returns error message if exceeded, None if within limits.
    """
    amount = estimate_order_amount(quantity, price)
    if amount == Decimal("0"):
        return None
    daily_total = get_daily_total(log_path)
    daily_limit = get_daily_order_limit()
    if daily_total + amount > daily_limit:
        return (
            f"Order would bring daily total to ${daily_total + amount:.2f}, "
            f"exceeding daily limit ${daily_limit:.2f} (IB_DAILY_ORDER_LIMIT_USD). "
            f"Today's total so far: ${daily_total:.2f}"
        )
    return None


def mask_account_id(account_id: str) -> str:
    """Mask account ID for logging, showing only last 4 chars."""
    return mask_sensitive(account_id, show_chars=4)


def write_order_log(
    log_path: Path,
    action: str,
    account_id: str,
    symbol: str,
    side: str,
    quantity: Decimal,
    limit_price: Decimal | None,
    order_id: str | int | None,
    status: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Write an order log entry to JSONL file.

    Returns the log record dict.
    """
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "account_id": mask_account_id(account_id),
        "symbol": symbol,
        "side": side,
        "quantity": str(quantity),
        "limit_price": str(limit_price) if limit_price is not None else None,
        "order_id": str(order_id) if order_id is not None else None,
        "status": status,
        "dry_run": dry_run,
    }

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

    return record


def _error_response(error: str) -> str:
    """Return a JSON error response."""
    return json.dumps({"error": error}, indent=2)


def _reply_to_dict(reply: CPOrderReply) -> dict[str, Any]:
    """Convert a CPOrderReply to a serializable dict."""
    return {
        "order_id": reply.order_id,
        "order_status": reply.order_status,
        "message": reply.message,
    }


def _validate_order_type(order_type: str) -> CPOrderType | None:
    """Validate and convert order type string."""
    try:
        return CPOrderType(order_type.upper())
    except ValueError:
        return None


def _validate_side(side: str) -> CPOrderSide | None:
    """Validate and convert side string."""
    try:
        return CPOrderSide(side.upper())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def register_order_management_tools(mcp: FastMCP) -> None:
    """Register order management tools via Client Portal Gateway"""

    @mcp.tool
    async def place_order(
        account_id: str,
        contract_id: int,
        symbol: str,
        side: str,
        quantity: str,
        order_type: str = "LMT",
        limit_price: str | None = None,
        tif: str = "GTC",
        ctx: Context | None = None,
    ) -> str:
        """
        Place an order via IB Client Portal Gateway

        Places a buy or sell order with multiple safety mechanisms:
        - Dry-run mode (default ON, set IB_ORDER_DRY_RUN=0 to disable)
        - Per-order amount limit (IB_MAX_ORDER_AMOUNT_USD, default $50,000)
        - Daily order limit (IB_DAILY_ORDER_LIMIT_USD, default $200,000)
        - Read-only mode (IB_READ_ONLY=1 disables all order tools)
        - Full order logging to data/processed/order_log.jsonl

        Args:
            account_id: IB account ID
            contract_id: IB contract ID for the instrument
            symbol: Trading symbol (e.g., "AAPL") for logging
            side: Order side ("BUY" or "SELL")
            quantity: Order quantity (as string for precision)
            order_type: Order type ("LMT", "MKT", "STP", "STP_LMT")
            limit_price: Limit price (required for LMT/STP_LMT orders)
            tif: Time in force ("GTC", "DAY", "IOC")
            ctx: MCP context for logging

        Returns:
            JSON string with order placement result
        """
        # Safety check: read-only mode
        if is_read_only():
            return _error_response(READ_ONLY_MSG)

        # Validate inputs
        side_enum = _validate_side(side)
        if side_enum is None:
            return _error_response(f"Invalid side: {side}. Use 'BUY' or 'SELL'")

        order_type_enum = _validate_order_type(order_type)
        if order_type_enum is None:
            return _error_response(
                f"Invalid order type: {order_type}. Use 'LMT', 'MKT', 'STP', or 'STP_LMT'"
            )

        qty = Decimal(quantity)
        if qty <= Decimal("0"):
            return _error_response("Quantity must be positive")

        price = Decimal(limit_price) if limit_price else None

        if order_type_enum in (CPOrderType.LIMIT, CPOrderType.STOP_LIMIT) and price is None:
            return _error_response(f"Limit price is required for {order_type} orders")

        # Safety check: per-order amount limit
        amount_error = check_order_amount_limit(qty, price)
        if amount_error:
            return _error_response(amount_error)

        # Safety check: daily limit
        log_path = get_order_log_path()
        daily_error = check_daily_limit(qty, price, log_path)
        if daily_error:
            return _error_response(daily_error)

        dry_run = is_dry_run()

        if dry_run:
            if ctx:
                await ctx.info(f"[DRY RUN] Would place {side} {quantity} {symbol}")
            log_record = write_order_log(
                log_path=log_path,
                action="place",
                account_id=account_id,
                symbol=symbol,
                side=side_enum.value,
                quantity=qty,
                limit_price=price,
                order_id=None,
                status="dry_run",
                dry_run=True,
            )
            return json.dumps(
                {
                    "dry_run": True,
                    "message": "[DRY RUN] Order not submitted. Set IB_ORDER_DRY_RUN=0 to enable.",
                    "order_details": {
                        "symbol": symbol,
                        "side": side_enum.value,
                        "quantity": str(qty),
                        "order_type": order_type_enum.value,
                        "limit_price": str(price) if price else None,
                        "tif": tif,
                    },
                    "log": log_record,
                },
                indent=2,
            )

        # Live order placement
        if ctx:
            await ctx.info(f"Placing {side} {quantity} {symbol} @ {limit_price or 'MKT'}")

        try:
            order_request = CPOrderRequest(
                account_id=account_id,
                contract_id=contract_id,
                side=side_enum,
                quantity=qty,
                order_type=order_type_enum,
                price=price,
                tif=tif,
            )

            async with CPClient() as client:
                replies = await client.place_order(order_request)

            order_id = None
            status = "submitted"
            for reply in replies:
                if reply.order_id:
                    order_id = reply.order_id
                if reply.order_status:
                    status = reply.order_status

            log_record = write_order_log(
                log_path=log_path,
                action="place",
                account_id=account_id,
                symbol=symbol,
                side=side_enum.value,
                quantity=qty,
                limit_price=price,
                order_id=order_id,
                status=status,
                dry_run=False,
            )

            return json.dumps(
                {
                    "dry_run": False,
                    "status": status,
                    "order_id": order_id,
                    "replies": [_reply_to_dict(r) for r in replies],
                    "log": log_record,
                },
                indent=2,
            )

        except CPConnectionError:
            return _error_response(GATEWAY_NOT_RUNNING_MSG)
        except CPAuthenticationError:
            return _error_response(SESSION_EXPIRED_MSG)
        except CPClientError as e:
            write_order_log(
                log_path=log_path,
                action="place",
                account_id=account_id,
                symbol=symbol,
                side=side_enum.value,
                quantity=qty,
                limit_price=price,
                order_id=None,
                status="rejected",
                dry_run=False,
            )
            return _error_response(f"Order placement failed: {e}")

    @mcp.tool
    async def modify_order(
        account_id: str,
        order_id: int,
        symbol: str = "",
        quantity: str | None = None,
        limit_price: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """
        Modify an existing order via IB Client Portal Gateway

        Changes quantity and/or limit price of an active order.

        Args:
            account_id: IB account ID
            order_id: Order ID to modify
            symbol: Trading symbol (for logging)
            quantity: New quantity (optional)
            limit_price: New limit price (optional)
            ctx: MCP context for logging

        Returns:
            JSON string with modification result
        """
        if is_read_only():
            return _error_response(READ_ONLY_MSG)

        if quantity is None and limit_price is None:
            return _error_response("At least one of quantity or limit_price must be provided")

        qty = Decimal(quantity) if quantity else None
        price = Decimal(limit_price) if limit_price else None

        if qty is not None and qty <= Decimal("0"):
            return _error_response("Quantity must be positive")

        # Safety check: per-order amount limit (if both qty and price available)
        if qty and price:
            amount_error = check_order_amount_limit(qty, price)
            if amount_error:
                return _error_response(amount_error)

        log_path = get_order_log_path()
        dry_run = is_dry_run()

        if dry_run:
            if ctx:
                await ctx.info(f"[DRY RUN] Would modify order {order_id}")
            log_record = write_order_log(
                log_path=log_path,
                action="modify",
                account_id=account_id,
                symbol=symbol,
                side="",
                quantity=qty or Decimal("0"),
                limit_price=price,
                order_id=order_id,
                status="dry_run",
                dry_run=True,
            )
            return json.dumps(
                {
                    "dry_run": True,
                    "message": "[DRY RUN] Order not modified. Set IB_ORDER_DRY_RUN=0 to enable.",
                    "order_id": order_id,
                    "modifications": {
                        "quantity": str(qty) if qty else None,
                        "limit_price": str(price) if price else None,
                    },
                    "log": log_record,
                },
                indent=2,
            )

        if ctx:
            await ctx.info(f"Modifying order {order_id}")

        try:
            async with CPClient() as client:
                replies = await client.modify_order(
                    account_id=account_id,
                    order_id=order_id,
                    quantity=qty,
                    limit_price=price,
                )

            status = "modified"
            for reply in replies:
                if reply.order_status:
                    status = reply.order_status

            log_record = write_order_log(
                log_path=log_path,
                action="modify",
                account_id=account_id,
                symbol=symbol,
                side="",
                quantity=qty or Decimal("0"),
                limit_price=price,
                order_id=order_id,
                status=status,
                dry_run=False,
            )

            return json.dumps(
                {
                    "dry_run": False,
                    "status": status,
                    "order_id": order_id,
                    "replies": [_reply_to_dict(r) for r in replies],
                    "log": log_record,
                },
                indent=2,
            )

        except CPConnectionError:
            return _error_response(GATEWAY_NOT_RUNNING_MSG)
        except CPAuthenticationError:
            return _error_response(SESSION_EXPIRED_MSG)
        except CPClientError as e:
            write_order_log(
                log_path=log_path,
                action="modify",
                account_id=account_id,
                symbol=symbol,
                side="",
                quantity=qty or Decimal("0"),
                limit_price=price,
                order_id=order_id,
                status="rejected",
                dry_run=False,
            )
            return _error_response(f"Order modification failed: {e}")

    @mcp.tool
    async def cancel_order(
        account_id: str,
        order_id: int,
        symbol: str = "",
        ctx: Context | None = None,
    ) -> str:
        """
        Cancel an existing order via IB Client Portal Gateway

        Args:
            account_id: IB account ID
            order_id: Order ID to cancel
            symbol: Trading symbol (for logging)
            ctx: MCP context for logging

        Returns:
            JSON string with cancellation result
        """
        if is_read_only():
            return _error_response(READ_ONLY_MSG)

        log_path = get_order_log_path()
        dry_run = is_dry_run()

        if dry_run:
            if ctx:
                await ctx.info(f"[DRY RUN] Would cancel order {order_id}")
            log_record = write_order_log(
                log_path=log_path,
                action="cancel",
                account_id=account_id,
                symbol=symbol,
                side="",
                quantity=Decimal("0"),
                limit_price=None,
                order_id=order_id,
                status="dry_run",
                dry_run=True,
            )
            return json.dumps(
                {
                    "dry_run": True,
                    "message": "[DRY RUN] Order not cancelled. Set IB_ORDER_DRY_RUN=0 to enable.",
                    "order_id": order_id,
                    "log": log_record,
                },
                indent=2,
            )

        if ctx:
            await ctx.info(f"Cancelling order {order_id}")

        try:
            async with CPClient() as client:
                result = await client.cancel_order(account_id, order_id)

            log_record = write_order_log(
                log_path=log_path,
                action="cancel",
                account_id=account_id,
                symbol=symbol,
                side="",
                quantity=Decimal("0"),
                limit_price=None,
                order_id=order_id,
                status="cancelled",
                dry_run=False,
            )

            return json.dumps(
                {
                    "dry_run": False,
                    "status": "cancelled",
                    "order_id": order_id,
                    "api_response": result,
                    "log": log_record,
                },
                indent=2,
            )

        except CPConnectionError:
            return _error_response(GATEWAY_NOT_RUNNING_MSG)
        except CPAuthenticationError:
            return _error_response(SESSION_EXPIRED_MSG)
        except CPClientError as e:
            write_order_log(
                log_path=log_path,
                action="cancel",
                account_id=account_id,
                symbol=symbol,
                side="",
                quantity=Decimal("0"),
                limit_price=None,
                order_id=order_id,
                status="rejected",
                dry_run=False,
            )
            return _error_response(f"Order cancellation failed: {e}")

    @mcp.tool
    async def cancel_all_orders(
        ctx: Context | None = None,
    ) -> str:
        """
        Cancel all open orders via IB Client Portal Gateway (emergency use)

        Cancels ALL open orders across all accounts. Use with caution.

        Args:
            ctx: MCP context for logging

        Returns:
            JSON string with cancellation results
        """
        if is_read_only():
            return _error_response(READ_ONLY_MSG)

        log_path = get_order_log_path()
        dry_run = is_dry_run()

        if dry_run:
            if ctx:
                await ctx.info("[DRY RUN] Would cancel all open orders")
            log_record = write_order_log(
                log_path=log_path,
                action="cancel_all",
                account_id="ALL",
                symbol="ALL",
                side="",
                quantity=Decimal("0"),
                limit_price=None,
                order_id=None,
                status="dry_run",
                dry_run=True,
            )
            return json.dumps(
                {
                    "dry_run": True,
                    "message": "[DRY RUN] Orders not cancelled. Set IB_ORDER_DRY_RUN=0 to enable.",
                    "log": log_record,
                },
                indent=2,
            )

        if ctx:
            await ctx.info("Cancelling all open orders")

        try:
            async with CPClient() as client:
                orders = await client.get_orders()
                active_orders = [
                    o
                    for o in orders
                    if o.status.value in ("Submitted", "PreSubmitted", "PendingSubmit")
                ]

                if not active_orders:
                    return json.dumps(
                        {"dry_run": False, "message": "No active orders to cancel"},
                        indent=2,
                    )

                results: list[dict[str, Any]] = []
                for order in active_orders:
                    try:
                        cancel_result = await client.cancel_order(order.account_id, order.order_id)
                        write_order_log(
                            log_path=log_path,
                            action="cancel",
                            account_id=order.account_id,
                            symbol=order.symbol,
                            side=order.side.value,
                            quantity=order.quantity,
                            limit_price=order.price,
                            order_id=order.order_id,
                            status="cancelled",
                            dry_run=False,
                        )
                        results.append(
                            {
                                "order_id": order.order_id,
                                "symbol": order.symbol,
                                "status": "cancelled",
                                "api_response": cancel_result,
                            }
                        )
                    except CPClientError as e:
                        results.append(
                            {
                                "order_id": order.order_id,
                                "symbol": order.symbol,
                                "status": "failed",
                                "error": str(e),
                            }
                        )

                return json.dumps(
                    {
                        "dry_run": False,
                        "total_cancelled": sum(1 for r in results if r["status"] == "cancelled"),
                        "total_failed": sum(1 for r in results if r["status"] == "failed"),
                        "results": results,
                    },
                    indent=2,
                )

        except CPConnectionError:
            return _error_response(GATEWAY_NOT_RUNNING_MSG)
        except CPAuthenticationError:
            return _error_response(SESSION_EXPIRED_MSG)


__all__ = ["register_order_management_tools"]
