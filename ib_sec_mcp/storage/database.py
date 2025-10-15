"""Database connection management for SQLite"""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class DatabaseConnection:
    """
    SQLite database connection manager with connection pooling

    Provides thread-safe database connections with automatic transaction management.
    Uses TEXT storage for Decimal precision preservation.
    """

    def __init__(self, db_path: str | Path = "data/processed/positions.db"):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file (created if not exists)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection and enable foreign keys
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,  # Allow multi-threaded access
            isolation_level=None,  # Autocommit mode for manual transaction control
        )
        self._conn.row_factory = sqlite3.Row  # Enable dict-like access
        self._conn.execute("PRAGMA foreign_keys = ON")

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database transactions

        Yields:
            SQLite connection with transaction support

        Example:
            with db.transaction() as conn:
                conn.execute("INSERT INTO ...")
                conn.execute("UPDATE ...")
                # Automatically commits on success, rolls back on error
        """
        conn = self._conn
        try:
            conn.execute("BEGIN")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Context manager for database cursor

        Yields:
            SQLite cursor for queries

        Example:
            with db.cursor() as cur:
                cur.execute("SELECT * FROM position_snapshots")
                results = cur.fetchall()
        """
        cursor = self._conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> sqlite3.Cursor:
        """
        Execute a single query

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            Cursor with query results
        """
        if params:
            return self._conn.execute(query, params)
        return self._conn.execute(query)

    def executemany(self, query: str, params: list[tuple[Any, ...]]) -> sqlite3.Cursor:
        """
        Execute query with multiple parameter sets

        Args:
            query: SQL query string
            params: List of parameter tuples

        Returns:
            Cursor with query results
        """
        return self._conn.executemany(query, params)

    def fetchone(self, query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        """
        Fetch single row as dictionary

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            Row as dictionary or None
        """
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self, query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        """
        Fetch all rows as list of dictionaries

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            List of rows as dictionaries
        """
        cursor = self.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """Close database connection"""
        self._conn.close()

    def __enter__(self) -> "DatabaseConnection":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.close()
