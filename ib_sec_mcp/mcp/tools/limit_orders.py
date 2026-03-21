"""Limit order management MCP tools"""

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fastmcp import Context, FastMCP

from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.storage.limit_order_store import LimitOrderStore

MARKET_SUFFIX_MAP: dict[str, str] = {
    "LSE": ".L",
    "TSE": ".T",
    "HKG": ".HK",
    "SGX": ".SI",
    "ASX": ".AX",
    "FRA": ".F",
}
"""Map market identifiers to yfinance ticker suffixes."""


def _get_yfinance_symbol(symbol: str, market: str) -> str:
    """Return the yfinance-compatible ticker for a given symbol and market."""
    suffix = MARKET_SUFFIX_MAP.get(market, "")
    if suffix and symbol.upper().endswith(suffix.upper()):
        return symbol
    return f"{symbol}{suffix}"


def register_limit_order_tools(mcp: FastMCP) -> None:
    """Register limit order management tools"""

    @mcp.tool
    async def add_limit_order(
        symbol: str,
        market: str,
        order_type: str,
        limit_price: str,
        created_date: str | None = None,
        quantity: str | None = None,
        amount_usd: str | None = None,
        tranche_number: int | None = None,
        rationale: str | None = None,
        notes: str | None = None,
        db_path: str = "data/processed/limit_orders.db",
        ctx: Context | None = None,
    ) -> str:
        """
        Register a new limit order for price monitoring

        Args:
            symbol: Trading symbol (e.g., "CSPX", "VWRA", "1329.T")
            market: Market identifier (LSE, TSE, NYSE, BOND)
            order_type: BUY or SELL
            limit_price: Limit price as string for Decimal precision (e.g., "700.00")
            created_date: Order creation date in YYYY-MM-DD (default: today)
            quantity: Number of shares/units (optional)
            amount_usd: Target USD amount (optional, e.g., "10000")
            tranche_number: Tranche number for staged entries (1, 2, 3, 4)
            rationale: Why this price level (e.g., "SMA200 support")
            notes: Additional notes
            db_path: Path to SQLite database
            ctx: MCP context for logging

        Returns:
            JSON string with created order details

        Example:
            >>> result = await add_limit_order(
            ...     symbol="CSPX", market="LSE", order_type="BUY",
            ...     limit_price="700.00", tranche_number=1,
            ...     rationale="SMA200 support level"
            ... )
        """
        try:
            price = Decimal(limit_price)
        except InvalidOperation as e:
            raise ValidationError(f"Invalid limit_price: {limit_price}") from e

        qty = None
        if quantity is not None:
            try:
                qty = Decimal(quantity)
            except InvalidOperation as e:
                raise ValidationError(f"Invalid quantity: {quantity}") from e

        amt = None
        if amount_usd is not None:
            try:
                amt = Decimal(amount_usd)
            except InvalidOperation as e:
                raise ValidationError(f"Invalid amount_usd: {amount_usd}") from e

        order_date = date.today()
        if created_date is not None:
            try:
                order_date = date.fromisoformat(created_date)
            except ValueError as e:
                raise ValidationError(f"Invalid date format: {created_date}") from e

        if ctx:
            await ctx.info(f"Adding {order_type} limit order for {symbol} at {limit_price}")

        try:
            store = LimitOrderStore(db_path)
            order_id = store.add_order(
                symbol=symbol,
                market=market,
                order_type=order_type,
                limit_price=price,
                created_date=order_date,
                quantity=qty,
                amount_usd=amt,
                tranche_number=tranche_number,
                rationale=rationale,
                notes=notes,
            )
            order = store.get_order_by_id(order_id)
            store.close()

            return json.dumps(
                {"status": "created", "order": order},
                indent=2,
                default=str,
            )
        except ValueError as e:
            raise ValidationError(str(e)) from e

    @mcp.tool
    async def update_limit_order(
        order_id: int,
        status: str | None = None,
        filled_price: str | None = None,
        filled_date: str | None = None,
        limit_price: str | None = None,
        quantity: str | None = None,
        amount_usd: str | None = None,
        notes: str | None = None,
        db_path: str = "data/processed/limit_orders.db",
        ctx: Context | None = None,
    ) -> str:
        """
        Update an existing limit order

        Status transitions: PENDING -> FILLED/CANCELLED/EXPIRED (no reverse).
        Can also update price, quantity, or amount for PENDING orders.

        Args:
            order_id: ID of the order to update
            status: New status (FILLED, CANCELLED, EXPIRED)
            filled_price: Price at which order was filled (for FILLED status)
            filled_date: Date when filled in YYYY-MM-DD (default: today if FILLED)
            limit_price: Updated limit price
            quantity: Updated quantity
            amount_usd: Updated USD amount
            notes: Updated notes
            db_path: Path to SQLite database
            ctx: MCP context for logging

        Returns:
            JSON string with updated order details
        """
        fp = None
        if filled_price is not None:
            try:
                fp = Decimal(filled_price)
            except InvalidOperation as e:
                raise ValidationError(f"Invalid filled_price: {filled_price}") from e

        fd = None
        if filled_date is not None:
            try:
                fd = date.fromisoformat(filled_date)
            except ValueError as e:
                raise ValidationError(f"Invalid filled_date: {filled_date}") from e
        elif status == "FILLED":
            fd = date.today()

        lp = None
        if limit_price is not None:
            try:
                lp = Decimal(limit_price)
            except InvalidOperation as e:
                raise ValidationError(f"Invalid limit_price: {limit_price}") from e

        qty = None
        if quantity is not None:
            try:
                qty = Decimal(quantity)
            except InvalidOperation as e:
                raise ValidationError(f"Invalid quantity: {quantity}") from e

        amt = None
        if amount_usd is not None:
            try:
                amt = Decimal(amount_usd)
            except InvalidOperation as e:
                raise ValidationError(f"Invalid amount_usd: {amount_usd}") from e

        if ctx:
            await ctx.info(f"Updating limit order #{order_id}")

        try:
            store = LimitOrderStore(db_path)
            updated = store.update_order(
                order_id=order_id,
                status=status,
                filled_price=fp,
                filled_date=fd,
                limit_price=lp,
                quantity=qty,
                amount_usd=amt,
                notes=notes,
            )

            if not updated:
                store.close()
                return json.dumps(
                    {"status": "not_found", "message": f"Order #{order_id} not found"},
                    indent=2,
                )

            order = store.get_order_by_id(order_id)
            store.close()

            return json.dumps(
                {"status": "updated", "order": order},
                indent=2,
                default=str,
            )
        except ValueError as e:
            raise ValidationError(str(e)) from e

    @mcp.tool
    async def get_pending_orders(
        symbol: str | None = None,
        market: str | None = None,
        db_path: str = "data/processed/limit_orders.db",
        ctx: Context | None = None,
    ) -> str:
        """
        List all pending limit orders

        Args:
            symbol: Filter by symbol (optional, e.g., "CSPX")
            market: Filter by market (optional, e.g., "LSE")
            db_path: Path to SQLite database
            ctx: MCP context for logging

        Returns:
            JSON string with list of pending orders

        Example:
            >>> orders = await get_pending_orders(symbol="CSPX")
        """
        if ctx:
            msg = "Fetching pending orders"
            if symbol:
                msg += f" for {symbol}"
            if market:
                msg += f" on {market}"
            await ctx.info(msg)

        store = LimitOrderStore(db_path)
        orders = store.get_pending_orders(symbol=symbol, market=market)
        store.close()

        return json.dumps(
            {
                "pending_count": len(orders),
                "orders": orders,
            },
            indent=2,
            default=str,
        )

    @mcp.tool
    async def check_order_proximity(
        threshold_pct: float = 5.0,
        symbol: str | None = None,
        db_path: str = "data/processed/limit_orders.db",
        ctx: Context | None = None,
    ) -> str:
        """
        Check proximity of current prices to pending limit orders

        For each pending order, fetches current price and calculates distance.
        Flags orders within threshold percentage as alerts.

        Args:
            threshold_pct: Alert threshold percentage (default: 5.0%)
            symbol: Check only this symbol (optional)
            db_path: Path to SQLite database
            ctx: MCP context for logging

        Returns:
            JSON string with proximity analysis for each pending order

        Example:
            >>> result = await check_order_proximity(threshold_pct=3.0)
        """
        import yfinance as yf

        if ctx:
            await ctx.info("Checking order proximity to current prices")

        store = LimitOrderStore(db_path)
        orders = store.get_pending_orders(symbol=symbol)
        store.close()

        if not orders:
            return json.dumps(
                {"message": "No pending orders found", "alerts": [], "results": []},
                indent=2,
            )

        threshold = Decimal(str(threshold_pct))
        results = []
        alerts = []

        # Group orders by (symbol, market) to minimize API calls
        symbol_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for order in orders:
            key = (order["symbol"], order["market"])
            if key not in symbol_groups:
                symbol_groups[key] = []
            symbol_groups[key].append(order)

        for (sym, market), sym_orders in symbol_groups.items():
            current_price = None
            error_msg = None

            # Resolve Yahoo Finance ticker with market suffix
            yf_symbol = _get_yfinance_symbol(sym, market)

            try:
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                raw_price = info.get("currentPrice") or info.get("regularMarketPrice")
                if raw_price is not None:
                    current_price = Decimal(str(raw_price))
                else:
                    error_msg = f"No price data available for {yf_symbol}"
            except Exception as e:
                error_msg = f"Failed to fetch price for {yf_symbol}: {e!s}"

            for order in sym_orders:
                limit_price = order["limit_price"]
                entry: dict[str, Any] = {
                    "order_id": order["id"],
                    "symbol": sym,
                    "market": order["market"],
                    "order_type": order["order_type"],
                    "limit_price": limit_price,
                    "tranche_number": order["tranche_number"],
                    "rationale": order["rationale"],
                }

                if current_price is not None and limit_price != Decimal("0"):
                    distance = current_price - limit_price
                    distance_pct = (distance / limit_price) * Decimal("100")

                    entry["current_price"] = current_price
                    entry["distance"] = distance
                    entry["distance_pct"] = distance_pct.quantize(Decimal("0.01"))

                    is_alert = abs(distance_pct) <= threshold
                    entry["alert"] = is_alert

                    if is_alert:
                        alerts.append(entry)
                else:
                    entry["current_price"] = None
                    entry["error"] = error_msg or "Limit price is zero"
                    entry["alert"] = False

                results.append(entry)

        return json.dumps(
            {
                "threshold_pct": threshold_pct,
                "total_orders": len(results),
                "alert_count": len(alerts),
                "alerts": alerts,
                "results": results,
            },
            indent=2,
            default=str,
        )

    @mcp.tool
    async def get_order_history(
        symbol: str | None = None,
        db_path: str = "data/processed/limit_orders.db",
        ctx: Context | None = None,
    ) -> str:
        """
        Get complete order history for audit trail

        Lists all orders including filled, cancelled, and expired.

        Args:
            symbol: Filter by symbol (optional)
            db_path: Path to SQLite database
            ctx: MCP context for logging

        Returns:
            JSON string with all orders sorted by date descending

        Example:
            >>> history = await get_order_history(symbol="CSPX")
        """
        if ctx:
            msg = "Fetching order history"
            if symbol:
                msg += f" for {symbol}"
            await ctx.info(msg)

        store = LimitOrderStore(db_path)
        orders = store.get_order_history(symbol=symbol)
        store.close()

        # Calculate summary stats
        status_counts: dict[str, int] = {}
        for order in orders:
            s = order["status"]
            status_counts[s] = status_counts.get(s, 0) + 1

        return json.dumps(
            {
                "total_orders": len(orders),
                "status_summary": status_counts,
                "orders": orders,
            },
            indent=2,
            default=str,
        )

    @mcp.tool
    async def sync_limit_orders(
        db_path: str = "data/processed/limit_orders.db",
        gateway_url: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """
        Sync limit orders from IB Client Portal Gateway to local DB

        Fetches live orders from IB and synchronizes with local limit_orders.db:
        - New IB orders not in DB → added
        - IB filled orders → DB status updated to FILLED
        - IB cancelled orders → DB status updated to CANCELLED
        - Existing matches → skipped

        Requires IB Client Portal Gateway to be running. If Gateway is not
        reachable, returns a skip message (no error).

        Args:
            db_path: Path to SQLite database
            gateway_url: IB Gateway URL override (default: from env or https://localhost:5000)
            ctx: MCP context for logging

        Returns:
            JSON string with sync results (added, updated, skipped, errors)

        Example:
            >>> result = await sync_limit_orders()
        """
        from ib_sec_mcp.storage.order_sync import try_sync_from_ib

        if ctx:
            await ctx.info("Starting limit order sync from IB Gateway")

        store = LimitOrderStore(db_path)
        try:
            sync_result = await try_sync_from_ib(
                store=store,
                gateway_url=gateway_url,
            )

            if sync_result is None:
                if ctx:
                    await ctx.info("IB Gateway not available, sync skipped")
                return json.dumps(
                    {
                        "status": "skipped",
                        "message": "IB Gateway not available or not authenticated",
                    },
                    indent=2,
                )

            if ctx:
                await ctx.info(
                    f"Sync complete: {sync_result.added} added, "
                    f"{sync_result.updated} updated, "
                    f"{sync_result.skipped} skipped"
                )

            return json.dumps(
                {
                    "status": "completed",
                    "sync_result": sync_result.to_dict(),
                },
                indent=2,
            )
        finally:
            store.close()


__all__ = ["register_limit_order_tools"]
