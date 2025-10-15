"""Position snapshot storage and retrieval"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from ib_sec_mcp.models.account import Account
from ib_sec_mcp.storage.database import DatabaseConnection
from ib_sec_mcp.storage.migrations import create_schema


class PositionStore:
    """
    Storage layer for position snapshots

    Provides CRUD operations for daily position data with Decimal precision preservation.
    Uses SQLite with TEXT storage for financial calculations.
    """

    def __init__(self, db_path: str | Path = "data/processed/positions.db"):
        """
        Initialize position store

        Args:
            db_path: Path to SQLite database file
        """
        self.db = DatabaseConnection(db_path)

        # Ensure schema exists
        create_schema(self.db)

    def save_snapshot(self, account: Account, snapshot_date: date, xml_file_path: str) -> int:
        """
        Save position snapshot from Account model

        Args:
            account: Account model with positions
            snapshot_date: Date for this snapshot
            xml_file_path: Source XML file path

        Returns:
            Number of positions saved
        """
        positions_saved = 0

        with self.db.transaction() as conn:
            # Save snapshot metadata
            conn.execute(
                """
                INSERT OR REPLACE INTO snapshot_metadata
                (account_id, snapshot_date, xml_file_path, date_range_from, date_range_to,
                 total_positions, total_value, total_cash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account.account_id,
                    snapshot_date.isoformat(),
                    xml_file_path,
                    account.from_date.isoformat(),
                    account.to_date.isoformat(),
                    len(account.positions),
                    str(account.total_value),
                    str(account.total_cash),
                ),
            )

            # Save positions
            for position in account.positions:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO position_snapshots
                    (account_id, snapshot_date, symbol, description, asset_class,
                     cusip, isin, quantity, multiplier, mark_price, position_value,
                     average_cost, cost_basis, unrealized_pnl, realized_pnl,
                     currency, fx_rate_to_base, coupon_rate, maturity_date, ytm, duration)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        position.account_id,
                        snapshot_date.isoformat(),
                        position.symbol,
                        position.description,
                        position.asset_class.value,
                        position.cusip,
                        position.isin,
                        str(position.quantity),
                        str(position.multiplier),
                        str(position.mark_price),
                        str(position.position_value),
                        str(position.average_cost),
                        str(position.cost_basis),
                        str(position.unrealized_pnl),
                        str(position.realized_pnl),
                        position.currency,
                        str(position.fx_rate_to_base),
                        str(position.coupon_rate) if position.coupon_rate else None,
                        position.maturity_date.isoformat() if position.maturity_date else None,
                        str(position.ytm) if position.ytm else None,
                        str(position.duration) if position.duration else None,
                    ),
                )
                positions_saved += 1

        return positions_saved

    def get_position_history(
        self,
        account_id: str,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """
        Get position history for a symbol over date range

        Args:
            account_id: Account ID
            symbol: Trading symbol
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of position snapshots ordered by date
        """
        query = """
            SELECT
                snapshot_date,
                symbol,
                description,
                asset_class,
                quantity,
                mark_price,
                position_value,
                average_cost,
                cost_basis,
                unrealized_pnl,
                realized_pnl,
                currency
            FROM position_snapshots
            WHERE account_id = ?
                AND symbol = ?
                AND snapshot_date >= ?
                AND snapshot_date <= ?
            ORDER BY snapshot_date ASC
        """

        results = self.db.fetchall(
            query,
            (account_id, symbol, start_date.isoformat(), end_date.isoformat()),
        )

        # Convert TEXT fields back to Decimal
        for row in results:
            row["quantity"] = Decimal(row["quantity"])
            row["mark_price"] = Decimal(row["mark_price"])
            row["position_value"] = Decimal(row["position_value"])
            row["average_cost"] = Decimal(row["average_cost"])
            row["cost_basis"] = Decimal(row["cost_basis"])
            row["unrealized_pnl"] = Decimal(row["unrealized_pnl"])
            row["realized_pnl"] = Decimal(row["realized_pnl"])

        return results

    def get_portfolio_snapshot(self, account_id: str, snapshot_date: date) -> list[dict[str, Any]]:
        """
        Get all positions for an account on a specific date

        Args:
            account_id: Account ID
            snapshot_date: Snapshot date

        Returns:
            List of positions on that date
        """
        query = """
            SELECT
                symbol,
                description,
                asset_class,
                quantity,
                mark_price,
                position_value,
                average_cost,
                cost_basis,
                unrealized_pnl,
                realized_pnl,
                currency,
                coupon_rate,
                maturity_date
            FROM position_snapshots
            WHERE account_id = ?
                AND snapshot_date = ?
            ORDER BY position_value DESC
        """

        results = self.db.fetchall(query, (account_id, snapshot_date.isoformat()))

        # Convert TEXT fields back to Decimal
        for row in results:
            row["quantity"] = Decimal(row["quantity"])
            row["mark_price"] = Decimal(row["mark_price"])
            row["position_value"] = Decimal(row["position_value"])
            row["average_cost"] = Decimal(row["average_cost"])
            row["cost_basis"] = Decimal(row["cost_basis"])
            row["unrealized_pnl"] = Decimal(row["unrealized_pnl"])
            row["realized_pnl"] = Decimal(row["realized_pnl"])
            if row["coupon_rate"]:
                row["coupon_rate"] = Decimal(row["coupon_rate"])

        return results

    def compare_portfolio_snapshots(
        self, account_id: str, date1: date, date2: date
    ) -> dict[str, Any]:
        """
        Compare portfolio composition between two dates

        Args:
            account_id: Account ID
            date1: First date
            date2: Second date

        Returns:
            Dictionary with comparison statistics
        """
        snapshot1 = self.get_portfolio_snapshot(account_id, date1)
        snapshot2 = self.get_portfolio_snapshot(account_id, date2)

        # Build symbol sets
        symbols1 = {pos["symbol"] for pos in snapshot1}
        symbols2 = {pos["symbol"] for pos in snapshot2}

        # Identify changes
        added = symbols2 - symbols1
        removed = symbols1 - symbols2
        common = symbols1 & symbols2

        # Calculate value changes
        pos_map1 = {pos["symbol"]: pos for pos in snapshot1}
        pos_map2 = {pos["symbol"]: pos for pos in snapshot2}

        total_value1 = sum((pos["position_value"] for pos in snapshot1), Decimal("0"))
        total_value2 = sum((pos["position_value"] for pos in snapshot2), Decimal("0"))

        changes = []
        for symbol in common:
            value1 = pos_map1[symbol]["position_value"]
            value2 = pos_map2[symbol]["position_value"]
            change = value2 - value1
            change_pct = (change / value1 * 100) if value1 != 0 else Decimal("0")

            changes.append(
                {
                    "symbol": symbol,
                    "value_change": change,
                    "value_change_pct": change_pct,
                    "value_date1": value1,
                    "value_date2": value2,
                }
            )

        # Sort by absolute change
        changes.sort(key=lambda x: abs(x["value_change"]), reverse=True)

        return {
            "date1": date1.isoformat(),
            "date2": date2.isoformat(),
            "total_value_date1": total_value1,
            "total_value_date2": total_value2,
            "total_value_change": total_value2 - total_value1,
            "total_value_change_pct": (
                (total_value2 - total_value1) / total_value1 * 100
                if total_value1 != 0
                else Decimal("0")
            ),
            "positions_added": list(added),
            "positions_removed": list(removed),
            "positions_changed": changes,
        }

    def get_position_statistics(
        self,
        account_id: str,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """
        Get statistical summary for a position over date range

        Args:
            account_id: Account ID
            symbol: Trading symbol
            start_date: Start date
            end_date: End date

        Returns:
            Dictionary with min/max/avg statistics
        """
        query = """
            SELECT
                COUNT(*) as snapshot_count,
                MIN(mark_price) as min_price,
                MAX(mark_price) as max_price,
                AVG(CAST(mark_price AS REAL)) as avg_price,
                MIN(position_value) as min_value,
                MAX(position_value) as max_value,
                AVG(CAST(position_value AS REAL)) as avg_value,
                MIN(unrealized_pnl) as min_pnl,
                MAX(unrealized_pnl) as max_pnl,
                AVG(CAST(unrealized_pnl AS REAL)) as avg_pnl
            FROM position_snapshots
            WHERE account_id = ?
                AND symbol = ?
                AND snapshot_date >= ?
                AND snapshot_date <= ?
        """

        result = self.db.fetchone(
            query,
            (account_id, symbol, start_date.isoformat(), end_date.isoformat()),
        )

        if not result or result["snapshot_count"] == 0:
            return {
                "symbol": symbol,
                "date_range": {"from": start_date.isoformat(), "to": end_date.isoformat()},
                "snapshot_count": 0,
            }

        return {
            "symbol": symbol,
            "date_range": {"from": start_date.isoformat(), "to": end_date.isoformat()},
            "snapshot_count": result["snapshot_count"],
            "price_statistics": {
                "min": Decimal(str(result["min_price"])),
                "max": Decimal(str(result["max_price"])),
                "avg": Decimal(str(result["avg_price"])),
            },
            "value_statistics": {
                "min": Decimal(str(result["min_value"])),
                "max": Decimal(str(result["max_value"])),
                "avg": Decimal(str(result["avg_value"])),
            },
            "pnl_statistics": {
                "min": Decimal(str(result["min_pnl"])),
                "max": Decimal(str(result["max_pnl"])),
                "avg": Decimal(str(result["avg_pnl"])),
            },
        }

    def get_available_dates(self, account_id: str) -> list[str]:
        """
        Get list of available snapshot dates for an account

        Args:
            account_id: Account ID

        Returns:
            List of dates with snapshots (ISO format)
        """
        query = """
            SELECT DISTINCT snapshot_date
            FROM snapshot_metadata
            WHERE account_id = ?
            ORDER BY snapshot_date DESC
        """

        results = self.db.fetchall(query, (account_id,))
        return [row["snapshot_date"] for row in results]

    def close(self) -> None:
        """Close database connection"""
        self.db.close()

    def __enter__(self) -> "PositionStore":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.close()
