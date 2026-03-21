"""Live trading MCP tools via IB Client Portal Gateway API"""

import json
from typing import Any

from fastmcp import Context, FastMCP

from ib_sec_mcp.api.cp_client import (
    CPAuthenticationError,
    CPClient,
    CPConnectionError,
)
from ib_sec_mcp.api.cp_models import CPOrderSide, CPOrderStatus

GATEWAY_NOT_RUNNING_MSG = (
    "IB Client Portal Gateway is not running. Start the gateway and login at https://localhost:5000"
)

SESSION_EXPIRED_MSG = (
    "IB Client Portal session has expired. Please re-authenticate at https://localhost:5000"
)


def _error_response(error: str) -> str:
    """Return a JSON error response."""
    return json.dumps({"error": error}, indent=2)


def _order_to_dict(order: Any) -> dict[str, Any]:
    """Convert a CPOrder to a serializable dict preserving Decimal as string."""
    return {
        "order_id": order.order_id,
        "symbol": order.symbol,
        "side": str(order.side),
        "quantity": str(order.quantity),
        "limit_price": str(order.price),
        "avg_price": str(order.avg_price),
        "status": str(order.status),
        "order_type": order.order_type,
        "account_id": order.account_id,
    }


def _position_to_dict(pos: Any) -> dict[str, Any]:
    """Convert a CPPosition to a serializable dict preserving Decimal as string."""
    return {
        "account_id": pos.account_id,
        "contract_id": pos.contract_id,
        "symbol": pos.symbol,
        "quantity": str(pos.position),
        "market_price": str(pos.market_price),
        "market_value": str(pos.market_value),
        "avg_cost": str(pos.avg_cost),
        "unrealized_pnl": str(pos.unrealized_pnl),
        "currency": pos.currency,
    }


def _balance_to_dict(bal: Any) -> dict[str, Any]:
    """Convert a CPAccountBalance to a serializable dict preserving Decimal as string."""
    return {
        "account_id": bal.account_id,
        "net_liquidation": str(bal.net_liquidation),
        "total_cash": str(bal.total_cash),
        "buying_power": str(bal.buying_power),
        "gross_position_value": str(bal.gross_position_value),
    }


def _filter_orders(
    orders: list[Any],
    symbol: str | None = None,
    side: str | None = None,
    status: str | None = None,
) -> list[Any]:
    """Filter orders by symbol, side, and status."""
    filtered = orders
    if symbol:
        filtered = [o for o in filtered if o.symbol.upper() == symbol.upper()]
    if side:
        try:
            side_enum = CPOrderSide(side.upper())
            filtered = [o for o in filtered if o.side == side_enum]
        except ValueError:
            pass
    if status:
        try:
            status_enum = CPOrderStatus(status)
            filtered = [o for o in filtered if o.status == status_enum]
        except ValueError:
            pass
    return filtered


def register_live_trading_tools(mcp: FastMCP) -> None:
    """Register live trading tools via Client Portal Gateway"""

    @mcp.tool
    async def get_live_orders(
        symbol: str | None = None,
        side: str | None = None,
        status: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """
        Get live orders from IB Client Portal Gateway

        Returns all active orders from the IB platform with optional filtering.

        Args:
            symbol: Filter by trading symbol (e.g., "AAPL")
            side: Filter by order side ("BUY" or "SELL")
            status: Filter by order status (e.g., "Submitted", "Filled")
            ctx: MCP context for logging

        Returns:
            JSON string with list of live orders
        """
        if ctx:
            await ctx.info("Fetching live orders from IB Gateway")

        try:
            async with CPClient() as client:
                orders = await client.get_orders()
                filtered = _filter_orders(orders, symbol=symbol, side=side, status=status)
                return json.dumps(
                    {
                        "total_orders": len(filtered),
                        "orders": [_order_to_dict(o) for o in filtered],
                    },
                    indent=2,
                )
        except CPConnectionError:
            return _error_response(GATEWAY_NOT_RUNNING_MSG)
        except CPAuthenticationError:
            return _error_response(SESSION_EXPIRED_MSG)

    @mcp.tool
    async def get_live_account_balance(
        account_id: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """
        Get real-time account balance from IB Client Portal Gateway

        Returns total value, cash, buying power, and margin information.

        Args:
            account_id: IB account ID (optional, uses first account if not specified)
            ctx: MCP context for logging

        Returns:
            JSON string with account balance details
        """
        if ctx:
            await ctx.info("Fetching account balance from IB Gateway")

        try:
            async with CPClient() as client:
                if not account_id:
                    accounts = await client.get_accounts()
                    if not accounts:
                        return _error_response("No accounts found")
                    account_id = accounts[0]

                balance = await client.get_account_balance(account_id)
                return json.dumps(_balance_to_dict(balance), indent=2)
        except CPConnectionError:
            return _error_response(GATEWAY_NOT_RUNNING_MSG)
        except CPAuthenticationError:
            return _error_response(SESSION_EXPIRED_MSG)

    @mcp.tool
    async def get_live_positions(
        account_id: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """
        Get real-time positions from IB Client Portal Gateway

        Returns symbol, quantity, market value, average cost, and unrealized P&L.

        Args:
            account_id: IB account ID (optional, uses first account if not specified)
            ctx: MCP context for logging

        Returns:
            JSON string with list of positions
        """
        if ctx:
            await ctx.info("Fetching positions from IB Gateway")

        try:
            async with CPClient() as client:
                if not account_id:
                    accounts = await client.get_accounts()
                    if not accounts:
                        return _error_response("No accounts found")
                    account_id = accounts[0]

                positions = await client.get_positions(account_id)
                return json.dumps(
                    {
                        "account_id": account_id,
                        "total_positions": len(positions),
                        "positions": [_position_to_dict(p) for p in positions],
                    },
                    indent=2,
                )
        except CPConnectionError:
            return _error_response(GATEWAY_NOT_RUNNING_MSG)
        except CPAuthenticationError:
            return _error_response(SESSION_EXPIRED_MSG)

    @mcp.tool
    async def check_gateway_status(
        ctx: Context | None = None,
    ) -> str:
        """
        Check IB Client Portal Gateway connection status

        Returns connection state, authentication status, and session information.

        Args:
            ctx: MCP context for logging

        Returns:
            JSON string with gateway status
        """
        if ctx:
            await ctx.info("Checking IB Gateway status")

        try:
            async with CPClient() as client:
                auth_status = await client.check_auth_status()
                return json.dumps(
                    {
                        "connected": True,
                        "authenticated": auth_status.authenticated,
                        "competing": auth_status.competing,
                        "server_connected": auth_status.connected,
                        "message": auth_status.message,
                    },
                    indent=2,
                )
        except CPConnectionError:
            return json.dumps(
                {
                    "connected": False,
                    "authenticated": False,
                    "competing": False,
                    "server_connected": False,
                    "message": GATEWAY_NOT_RUNNING_MSG,
                },
                indent=2,
            )


__all__ = ["register_live_trading_tools"]
