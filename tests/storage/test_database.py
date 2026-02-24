"""Tests for DatabaseConnection and schema migrations"""

from pathlib import Path

import pytest

from ib_sec_mcp.storage.database import DatabaseConnection
from ib_sec_mcp.storage.migrations import create_schema, drop_schema, verify_schema

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path: Path) -> DatabaseConnection:
    db = DatabaseConnection(tmp_path / "test.db")
    yield db
    db.close()


@pytest.fixture
def db_with_schema(tmp_path: Path) -> DatabaseConnection:
    db = DatabaseConnection(tmp_path / "test.db")
    create_schema(db)
    yield db
    db.close()


# ---------------------------------------------------------------------------
# TestDatabaseConnection
# ---------------------------------------------------------------------------


class TestDatabaseConnection:
    def test_init_creates_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "dir" / "test.db"
        db = DatabaseConnection(nested)
        assert nested.exists()
        db.close()

    def test_execute_and_fetchone(self, db: DatabaseConnection) -> None:
        db.execute("CREATE TABLE t (id INTEGER, val TEXT)")
        db.execute("INSERT INTO t VALUES (?, ?)", (1, "hello"))
        row = db.fetchone("SELECT * FROM t WHERE id = ?", (1,))
        assert row is not None
        assert row["id"] == 1
        assert row["val"] == "hello"

    def test_execute_and_fetchall(self, db: DatabaseConnection) -> None:
        db.execute("CREATE TABLE t (id INTEGER, val TEXT)")
        db.execute("INSERT INTO t VALUES (?, ?)", (1, "a"))
        db.execute("INSERT INTO t VALUES (?, ?)", (2, "b"))
        rows = db.fetchall("SELECT * FROM t ORDER BY id")
        assert len(rows) == 2
        assert rows[0]["val"] == "a"
        assert rows[1]["val"] == "b"

    def test_executemany(self, db: DatabaseConnection) -> None:
        db.execute("CREATE TABLE t (id INTEGER, val TEXT)")
        params = [(i, f"val{i}") for i in range(5)]
        db.executemany("INSERT INTO t VALUES (?, ?)", params)
        rows = db.fetchall("SELECT * FROM t")
        assert len(rows) == 5

    def test_fetchone_returns_none_for_empty(self, db: DatabaseConnection) -> None:
        db.execute("CREATE TABLE t (id INTEGER)")
        result = db.fetchone("SELECT * FROM t WHERE id = ?", (999,))
        assert result is None

    def test_fetchall_returns_empty_list(self, db: DatabaseConnection) -> None:
        db.execute("CREATE TABLE t (id INTEGER)")
        result = db.fetchall("SELECT * FROM t")
        assert result == []

    def test_transaction_commits_on_success(self, db: DatabaseConnection) -> None:
        db.execute("CREATE TABLE t (id INTEGER)")
        with db.transaction() as conn:
            conn.execute("INSERT INTO t VALUES (?)", (42,))
        # After transaction, data should be persisted
        row = db.fetchone("SELECT * FROM t WHERE id = ?", (42,))
        assert row is not None

    def test_transaction_rolls_back_on_error(self, db: DatabaseConnection) -> None:
        db.execute("CREATE TABLE t (id INTEGER)")
        with pytest.raises(RuntimeError), db.transaction() as conn:
            conn.execute("INSERT INTO t VALUES (?)", (1,))
            raise RuntimeError("deliberate failure")
        # Row should not be persisted
        rows = db.fetchall("SELECT * FROM t")
        assert rows == []

    def test_cursor_context_manager(self, db: DatabaseConnection) -> None:
        db.execute("CREATE TABLE t (id INTEGER)")
        db.execute("INSERT INTO t VALUES (?)", (7,))
        with db.cursor() as cur:
            cur.execute("SELECT * FROM t")
            rows = cur.fetchall()
        assert len(rows) == 1

    def test_context_manager_protocol(self, tmp_path: Path) -> None:
        db_path = tmp_path / "ctx.db"
        with DatabaseConnection(db_path) as db:
            db.execute("CREATE TABLE t (id INTEGER)")
            db.execute("INSERT INTO t VALUES (?)", (1,))
            row = db.fetchone("SELECT * FROM t")
            assert row is not None

    def test_foreign_keys_enabled(self, db: DatabaseConnection) -> None:
        result = db.fetchone("PRAGMA foreign_keys")
        assert result is not None
        assert result["foreign_keys"] == 1

    def test_execute_without_params(self, db: DatabaseConnection) -> None:
        db.execute("CREATE TABLE t (id INTEGER)")
        db.execute("INSERT INTO t VALUES (1)")
        rows = db.fetchall("SELECT * FROM t")
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# TestSchemaCreation
# ---------------------------------------------------------------------------


class TestSchemaCreation:
    def test_create_schema_creates_tables(self, db: DatabaseConnection) -> None:
        create_schema(db)
        tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_names = {row["name"] for row in tables}
        assert "position_snapshots" in table_names
        assert "snapshot_metadata" in table_names

    def test_create_schema_creates_indexes(self, db: DatabaseConnection) -> None:
        create_schema(db)
        indexes = db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        index_names = {row["name"] for row in indexes}
        assert "idx_account_date" in index_names
        assert "idx_symbol_date" in index_names
        assert "idx_date" in index_names
        assert "idx_asset_class" in index_names
        assert "idx_snapshot_account_date" in index_names

    def test_create_schema_idempotent(self, db: DatabaseConnection) -> None:
        # Should not raise on second call
        create_schema(db)
        create_schema(db)
        tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = {row["name"] for row in tables}
        assert "position_snapshots" in table_names

    def test_drop_schema(self, db: DatabaseConnection) -> None:
        create_schema(db)
        drop_schema(db)
        # SQLite keeps internal sqlite_sequence; only check user tables are dropped
        tables = db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        assert tables == []

    def test_verify_schema_success(self, db: DatabaseConnection) -> None:
        create_schema(db)
        assert verify_schema(db) is True

    def test_verify_schema_failure_missing_table(self, db: DatabaseConnection) -> None:
        # Don't create schema — should fail
        assert verify_schema(db) is False

    def test_verify_schema_failure_after_drop(self, db: DatabaseConnection) -> None:
        create_schema(db)
        drop_schema(db)
        assert verify_schema(db) is False
