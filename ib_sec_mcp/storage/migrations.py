"""Database schema migrations"""

from ib_sec_mcp.storage.database import DatabaseConnection


def create_schema(db: DatabaseConnection) -> None:
    """
    Create database schema for position storage

    Creates two tables:
    1. position_snapshots: Daily position data per account
    2. snapshot_metadata: Snapshot-level metadata and statistics
    """
    with db.transaction() as conn:
        # Position snapshots table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS position_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Composite key for uniqueness
                account_id TEXT NOT NULL,
                snapshot_date DATE NOT NULL,
                symbol TEXT NOT NULL,

                -- Position details
                description TEXT,
                asset_class TEXT NOT NULL,
                cusip TEXT,
                isin TEXT,

                -- Quantities and prices (TEXT for Decimal precision)
                quantity TEXT NOT NULL,
                multiplier TEXT DEFAULT '1',
                mark_price TEXT NOT NULL,
                position_value TEXT NOT NULL,

                -- Cost basis
                average_cost TEXT NOT NULL,
                cost_basis TEXT NOT NULL,

                -- P&L
                unrealized_pnl TEXT DEFAULT '0',
                realized_pnl TEXT DEFAULT '0',

                -- Currency
                currency TEXT DEFAULT 'USD',
                fx_rate_to_base TEXT DEFAULT '1.0',

                -- Bond-specific (nullable)
                coupon_rate TEXT,
                maturity_date DATE,
                ytm TEXT,
                duration TEXT,

                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Unique constraint to prevent duplicates
                UNIQUE(account_id, snapshot_date, symbol)
            )
            """
        )

        # Indexes for efficient queries
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_account_date
            ON position_snapshots(account_id, snapshot_date)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_symbol_date
            ON position_snapshots(symbol, snapshot_date)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_date
            ON position_snapshots(snapshot_date)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_asset_class
            ON position_snapshots(asset_class)
            """
        )

        # Snapshot metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshot_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                snapshot_date DATE NOT NULL,

                -- Source tracking
                xml_file_path TEXT NOT NULL,
                date_range_from DATE NOT NULL,
                date_range_to DATE NOT NULL,

                -- Snapshot statistics
                total_positions INTEGER NOT NULL,
                total_value TEXT NOT NULL,
                total_cash TEXT NOT NULL,

                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(account_id, snapshot_date)
            )
            """
        )

        # Index for snapshot metadata
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_snapshot_account_date
            ON snapshot_metadata(account_id, snapshot_date)
            """
        )


def drop_schema(db: DatabaseConnection) -> None:
    """
    Drop all tables (for testing purposes)

    WARNING: This will delete all stored position data!
    """
    with db.transaction() as conn:
        conn.execute("DROP TABLE IF EXISTS position_snapshots")
        conn.execute("DROP TABLE IF EXISTS snapshot_metadata")


def verify_schema(db: DatabaseConnection) -> bool:
    """
    Verify that schema is correctly created

    Returns:
        True if schema is valid, False otherwise
    """
    with db.cursor() as cur:
        # Check if tables exist
        cur.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('position_snapshots', 'snapshot_metadata')
            """
        )
        tables = {row[0] for row in cur.fetchall()}

        if tables != {"position_snapshots", "snapshot_metadata"}:
            return False

        # Check if indexes exist
        cur.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND name LIKE 'idx_%'
            """
        )
        indexes = {row[0] for row in cur.fetchall()}

        expected_indexes = {
            "idx_account_date",
            "idx_symbol_date",
            "idx_date",
            "idx_asset_class",
            "idx_snapshot_account_date",
        }

        return expected_indexes.issubset(indexes)
