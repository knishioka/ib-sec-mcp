"""Position history MCP tools using SQLite storage"""

import json
from datetime import date

from fastmcp import Context, FastMCP

from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.storage import PositionStore


def register_position_history_tools(mcp: FastMCP) -> None:
    """Register position history tools"""

    @mcp.tool
    async def get_position_history(
        account_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
        db_path: str = "data/processed/positions.db",
        ctx: Context | None = None,
    ) -> str:
        """
        Get position history for a symbol over date range

        Retrieves daily position snapshots from SQLite storage for time-series analysis.

        Args:
            account_id: Account ID (e.g., "U1234567")
            symbol: Trading symbol (e.g., "PG", "AAPL")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            db_path: Path to SQLite database (default: data/processed/positions.db)
            ctx: MCP context for logging

        Returns:
            JSON string with position history including dates, quantities, prices, and P&L

        Example:
            >>> history = await get_position_history(
            ...     account_id="U1234567",
            ...     symbol="PG",
            ...     start_date="2025-01-01",
            ...     end_date="2025-10-15"
            ... )
        """
        try:
            # Parse dates
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)

            if ctx:
                await ctx.info(
                    f"Fetching position history for {symbol} from {start_date} to {end_date}",
                    extra={"account_id": account_id, "symbol": symbol},
                )

            # Query database
            store = PositionStore(db_path)
            history = store.get_position_history(account_id, symbol, start, end)
            store.close()

            if not history:
                return json.dumps(
                    {
                        "account_id": account_id,
                        "symbol": symbol,
                        "date_range": {"from": start_date, "to": end_date},
                        "snapshots": [],
                        "message": "No position history found for this symbol and date range",
                    },
                    indent=2,
                    default=str,
                )

            return json.dumps(
                {
                    "account_id": account_id,
                    "symbol": symbol,
                    "date_range": {"from": start_date, "to": end_date},
                    "snapshot_count": len(history),
                    "snapshots": history,
                },
                indent=2,
                default=str,
            )

        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}") from e
        except Exception as e:
            if ctx:
                await ctx.error(f"Error fetching position history: {e!s}")
            raise

    @mcp.tool
    async def get_portfolio_snapshot(
        account_id: str,
        snapshot_date: str,
        db_path: str = "data/processed/positions.db",
        ctx: Context | None = None,
    ) -> str:
        """
        Get all positions for an account on a specific date

        Retrieves a single-day portfolio snapshot from SQLite storage.

        Args:
            account_id: Account ID (e.g., "U1234567")
            snapshot_date: Date in YYYY-MM-DD format
            db_path: Path to SQLite database (default: data/processed/positions.db)
            ctx: MCP context for logging

        Returns:
            JSON string with all positions on that date

        Example:
            >>> snapshot = await get_portfolio_snapshot(
            ...     account_id="U1234567",
            ...     snapshot_date="2025-10-15"
            ... )
        """
        try:
            # Parse date
            snap_date = date.fromisoformat(snapshot_date)

            if ctx:
                await ctx.info(
                    f"Fetching portfolio snapshot for {account_id} on {snapshot_date}",
                    extra={"account_id": account_id, "date": snapshot_date},
                )

            # Query database
            store = PositionStore(db_path)
            positions = store.get_portfolio_snapshot(account_id, snap_date)
            store.close()

            # Calculate totals
            from decimal import Decimal

            total_value = sum((pos["position_value"] for pos in positions), Decimal("0"))
            total_unrealized_pnl = sum((pos["unrealized_pnl"] for pos in positions), Decimal("0"))

            return json.dumps(
                {
                    "account_id": account_id,
                    "snapshot_date": snapshot_date,
                    "position_count": len(positions),
                    "total_value": total_value,
                    "total_unrealized_pnl": total_unrealized_pnl,
                    "positions": positions,
                },
                indent=2,
                default=str,
            )

        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}") from e
        except Exception as e:
            if ctx:
                await ctx.error(f"Error fetching portfolio snapshot: {e!s}")
            raise

    @mcp.tool
    async def compare_portfolio_snapshots(
        account_id: str,
        date1: str,
        date2: str,
        db_path: str = "data/processed/positions.db",
        ctx: Context | None = None,
    ) -> str:
        """
        Compare portfolio composition between two dates

        Identifies positions added, removed, and changed between two snapshots.

        Args:
            account_id: Account ID (e.g., "U1234567")
            date1: First date in YYYY-MM-DD format
            date2: Second date in YYYY-MM-DD format
            db_path: Path to SQLite database (default: data/processed/positions.db)
            ctx: MCP context for logging

        Returns:
            JSON string with comparison including added/removed positions and value changes

        Example:
            >>> comparison = await compare_portfolio_snapshots(
            ...     account_id="U1234567",
            ...     date1="2025-09-01",
            ...     date2="2025-10-15"
            ... )
        """
        try:
            # Parse dates
            d1 = date.fromisoformat(date1)
            d2 = date.fromisoformat(date2)

            if ctx:
                await ctx.info(
                    f"Comparing portfolio snapshots for {account_id} between {date1} and {date2}",
                    extra={"account_id": account_id, "date1": date1, "date2": date2},
                )

            # Query database
            store = PositionStore(db_path)
            comparison = store.compare_portfolio_snapshots(account_id, d1, d2)
            store.close()

            return json.dumps(comparison, indent=2, default=str)

        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}") from e
        except Exception as e:
            if ctx:
                await ctx.error(f"Error comparing portfolio snapshots: {e!s}")
            raise

    @mcp.tool
    async def get_position_statistics(
        account_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
        db_path: str = "data/processed/positions.db",
        ctx: Context | None = None,
    ) -> str:
        """
        Get statistical summary for a position over date range

        Calculates min/max/average metrics for position over time.

        Args:
            account_id: Account ID (e.g., "U1234567")
            symbol: Trading symbol (e.g., "PG", "AAPL")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            db_path: Path to SQLite database (default: data/processed/positions.db)
            ctx: MCP context for logging

        Returns:
            JSON string with min/max/avg statistics for price, value, and P&L

        Example:
            >>> stats = await get_position_statistics(
            ...     account_id="U1234567",
            ...     symbol="PG",
            ...     start_date="2025-01-01",
            ...     end_date="2025-10-15"
            ... )
        """
        try:
            # Parse dates
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)

            if ctx:
                await ctx.info(
                    f"Calculating statistics for {symbol} from {start_date} to {end_date}",
                    extra={"account_id": account_id, "symbol": symbol},
                )

            # Query database
            store = PositionStore(db_path)
            stats = store.get_position_statistics(account_id, symbol, start, end)
            store.close()

            return json.dumps(stats, indent=2, default=str)

        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}") from e
        except Exception as e:
            if ctx:
                await ctx.error(f"Error calculating position statistics: {e!s}")
            raise

    @mcp.tool
    async def get_available_snapshot_dates(
        account_id: str,
        db_path: str = "data/processed/positions.db",
        ctx: Context | None = None,
    ) -> str:
        """
        Get list of available snapshot dates for an account

        Lists all dates with position snapshots stored in the database.

        Args:
            account_id: Account ID (e.g., "U1234567")
            db_path: Path to SQLite database (default: data/processed/positions.db)
            ctx: MCP context for logging

        Returns:
            JSON string with list of available dates in descending order

        Example:
            >>> dates = await get_available_snapshot_dates(account_id="U1234567")
        """
        try:
            if ctx:
                await ctx.info(
                    f"Fetching available snapshot dates for {account_id}",
                    extra={"account_id": account_id},
                )

            # Query database
            store = PositionStore(db_path)
            dates = store.get_available_dates(account_id)
            store.close()

            return json.dumps(
                {
                    "account_id": account_id,
                    "snapshot_count": len(dates),
                    "available_dates": dates,
                },
                indent=2,
            )

        except Exception as e:
            if ctx:
                await ctx.error(f"Error fetching available dates: {e!s}")
            raise


__all__ = ["register_position_history_tools"]
