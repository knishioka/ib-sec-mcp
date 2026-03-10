"""Limit order storage and retrieval"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from ib_sec_mcp.storage.database import DatabaseConnection

# Valid status values and allowed transitions
VALID_STATUSES = {"PENDING", "FILLED", "CANCELLED", "EXPIRED"}
TERMINAL_STATUSES = {"FILLED", "CANCELLED", "EXPIRED"}


def create_limit_orders_schema(db: DatabaseConnection) -> None:
    """Create limit_orders table and indexes"""
    with db.transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS limit_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                market TEXT NOT NULL,
                order_type TEXT NOT NULL,
                limit_price TEXT NOT NULL,
                quantity TEXT,
                amount_usd TEXT,
                tranche_number INTEGER,
                rationale TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_date DATE NOT NULL,
                updated_date DATE,
                filled_date DATE,
                filled_price TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, tranche_number, status)
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_limit_orders_status
            ON limit_orders(status)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_limit_orders_symbol
            ON limit_orders(symbol)
            """
        )


class LimitOrderStore:
    """
    Storage layer for limit orders

    Provides CRUD operations for limit order management with Decimal precision.
    Uses SQLite with TEXT storage for financial calculations.
    """

    def __init__(self, db_path: str | Path = "data/processed/limit_orders.db"):
        """
        Initialize limit order store

        Args:
            db_path: Path to SQLite database file
        """
        self.db = DatabaseConnection(db_path)
        create_limit_orders_schema(self.db)

    def add_order(
        self,
        symbol: str,
        market: str,
        order_type: str,
        limit_price: Decimal,
        created_date: date,
        quantity: Decimal | None = None,
        amount_usd: Decimal | None = None,
        tranche_number: int | None = None,
        rationale: str | None = None,
        notes: str | None = None,
    ) -> int:
        """
        Add a new limit order

        Args:
            symbol: Trading symbol (e.g., "CSPX", "VWRA")
            market: Market (e.g., "LSE", "TSE", "NYSE", "BOND")
            order_type: Order type ("BUY" or "SELL")
            limit_price: Limit price
            created_date: Date the order was created
            quantity: Number of shares/units (optional)
            amount_usd: Target USD amount (optional)
            tranche_number: Tranche number (1, 2, 3, 4)
            rationale: Reasoning for this price level
            notes: Additional notes

        Returns:
            ID of the inserted order

        Raises:
            ValueError: If order_type is invalid
        """
        if order_type not in ("BUY", "SELL"):
            raise ValueError(f"Invalid order_type: {order_type}. Must be BUY or SELL")

        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO limit_orders
                (symbol, market, order_type, limit_price, quantity, amount_usd,
                 tranche_number, rationale, status, created_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
                """,
                (
                    symbol,
                    market,
                    order_type,
                    str(limit_price),
                    str(quantity) if quantity is not None else None,
                    str(amount_usd) if amount_usd is not None else None,
                    tranche_number,
                    rationale,
                    created_date.isoformat(),
                    notes,
                ),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def update_order(
        self,
        order_id: int,
        status: str | None = None,
        filled_price: Decimal | None = None,
        filled_date: date | None = None,
        limit_price: Decimal | None = None,
        quantity: Decimal | None = None,
        amount_usd: Decimal | None = None,
        notes: str | None = None,
    ) -> bool:
        """
        Update an existing limit order

        Status transitions: PENDING → FILLED/CANCELLED/EXPIRED (no reverse)

        Args:
            order_id: ID of the order to update
            status: New status (FILLED, CANCELLED, EXPIRED)
            filled_price: Price at which order was filled
            filled_date: Date when order was filled
            limit_price: Updated limit price
            quantity: Updated quantity
            amount_usd: Updated USD amount
            notes: Updated notes

        Returns:
            True if order was updated, False if not found

        Raises:
            ValueError: If status transition is invalid
        """
        # Get current order
        current = self.db.fetchone(
            "SELECT id, status FROM limit_orders WHERE id = ?",
            (order_id,),
        )
        if not current:
            return False

        current_status = current["status"]

        # Validate status transition
        if status is not None:
            if status not in VALID_STATUSES:
                raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
            if current_status in TERMINAL_STATUSES:
                raise ValueError(
                    f"Cannot transition from {current_status}. Terminal statuses cannot be changed."
                )
            if status == "PENDING":
                raise ValueError("Cannot transition back to PENDING")

        # Build dynamic UPDATE
        updates: list[str] = []
        params: list[Any] = []

        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if filled_price is not None:
            updates.append("filled_price = ?")
            params.append(str(filled_price))
        if filled_date is not None:
            updates.append("filled_date = ?")
            params.append(filled_date.isoformat())
        if limit_price is not None:
            updates.append("limit_price = ?")
            params.append(str(limit_price))
        if quantity is not None:
            updates.append("quantity = ?")
            params.append(str(quantity))
        if amount_usd is not None:
            updates.append("amount_usd = ?")
            params.append(str(amount_usd))
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if not updates:
            return True  # Nothing to update

        updates.append("updated_date = ?")
        params.append(date.today().isoformat())
        params.append(order_id)

        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE limit_orders SET {', '.join(updates)} WHERE id = ?",  # nosec B608
                tuple(params),
            )

        return True

    def get_pending_orders(
        self,
        symbol: str | None = None,
        market: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get all pending limit orders

        Args:
            symbol: Filter by symbol (optional)
            market: Filter by market (optional)

        Returns:
            List of pending orders with Decimal values
        """
        query = "SELECT * FROM limit_orders WHERE status = 'PENDING'"
        params: list[Any] = []

        if symbol is not None:
            query += " AND symbol = ?"
            params.append(symbol)
        if market is not None:
            query += " AND market = ?"
            params.append(market)

        query += " ORDER BY symbol, tranche_number"

        results = self.db.fetchall(query, tuple(params) if params else None)
        return [self._row_to_dict(row) for row in results]

    def get_order_history(
        self,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get all orders (including filled/cancelled) for audit trail

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            List of all orders ordered by created_date descending
        """
        query = "SELECT * FROM limit_orders"
        params: list[Any] = []

        if symbol is not None:
            query += " WHERE symbol = ?"
            params.append(symbol)

        query += " ORDER BY created_date DESC, id DESC"

        results = self.db.fetchall(query, tuple(params) if params else None)
        return [self._row_to_dict(row) for row in results]

    def get_order_by_id(self, order_id: int) -> dict[str, Any] | None:
        """
        Get a single order by ID

        Args:
            order_id: Order ID

        Returns:
            Order dict or None if not found
        """
        result = self.db.fetchone(
            "SELECT * FROM limit_orders WHERE id = ?",
            (order_id,),
        )
        return self._row_to_dict(result) if result else None

    @staticmethod
    def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
        """Convert database row to dict with Decimal values"""
        result = dict(row)

        # Convert TEXT fields back to Decimal
        if result.get("limit_price") is not None:
            result["limit_price"] = Decimal(result["limit_price"])
        if result.get("quantity") is not None:
            result["quantity"] = Decimal(result["quantity"])
        if result.get("amount_usd") is not None:
            result["amount_usd"] = Decimal(result["amount_usd"])
        if result.get("filled_price") is not None:
            result["filled_price"] = Decimal(result["filled_price"])

        return result

    def close(self) -> None:
        """Close database connection"""
        self.db.close()

    def __enter__(self) -> "LimitOrderStore":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.close()
