"""Tests for Daily Monitor MCP tools"""

import json
import os
import time
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass
from ib_sec_mcp.storage.database import DatabaseConnection
from ib_sec_mcp.storage.migrations import create_schema, create_sync_log_table
from ib_sec_mcp.storage.position_store import PositionStore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACCOUNT_ID = "U1234567"
SNAP_DATE = date(2025, 6, 15)
FROM_DATE = date(2025, 6, 1)
TO_DATE = date(2025, 6, 15)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1234567">
      <OpenPositions>
        <OpenPosition
          accountId="U1234567"
          symbol="AAPL"
          description="APPLE INC"
          assetCategory="STK"
          quantity="100"
          markPrice="150.00"
          positionValue="15000.00"
          costBasisMoney="14000.00"
          costBasisPrice="140.00"
          fifoPnlUnrealized="1000.00"
          currency="USD"
          fxRateToBase="1.0"
          multiplier="1"
        />
      </OpenPositions>
      <CashReport>
        <CashReportCurrency
          currency="USD"
          startingCash="50000"
          endingCash="50000"
          endingSettledCash="50000"
        />
      </CashReport>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_position(
    account_id: str = ACCOUNT_ID,
    symbol: str = "AAPL",
    asset_class: AssetClass = AssetClass.STOCK,
    quantity: str = "100",
    mark_price: str = "150.00",
    position_value: str = "15000.00",
    cost_basis: str = "14000.00",
    average_cost: str = "140.00",
    unrealized_pnl: str = "1000.00",
) -> Position:
    return Position(
        account_id=account_id,
        symbol=symbol,
        description=f"{symbol} Inc",
        asset_class=asset_class,
        quantity=Decimal(quantity),
        mark_price=Decimal(mark_price),
        position_value=Decimal(position_value),
        average_cost=Decimal(average_cost),
        cost_basis=Decimal(cost_basis),
        unrealized_pnl=Decimal(unrealized_pnl),
        currency="USD",
        fx_rate_to_base=Decimal("1.0"),
        position_date=SNAP_DATE,
    )


def make_account(
    account_id: str = ACCOUNT_ID,
    positions: list[Position] | None = None,
    from_date: date = FROM_DATE,
    to_date: date = TO_DATE,
) -> Account:
    return Account(
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        cash_balances=[
            CashBalance(
                currency="USD",
                starting_cash=Decimal("50000"),
                ending_cash=Decimal("50000"),
                ending_settled_cash=Decimal("50000"),
            )
        ],
        positions=positions or [],
    )


async def _get_tool_fn(mcp, tool_name: str):
    """Retrieve a tool's underlying function from a FastMCP instance."""
    tool = await mcp.get_tool(tool_name)
    assert tool is not None, f"Tool '{tool_name}' not found"
    return tool.fn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Return a temporary DB path."""
    return tmp_path / "test_positions.db"


@pytest.fixture
def raw_data_dir(tmp_path: Path) -> Path:
    """Return a temporary raw data directory."""
    d = tmp_path / "raw"
    d.mkdir()
    return d


@pytest.fixture
def db(db_path: Path) -> DatabaseConnection:
    """Create a DatabaseConnection with sync_log table."""
    connection = DatabaseConnection(db_path)
    create_sync_log_table(connection)
    yield connection
    connection.close()


@pytest.fixture
def store(db_path: Path) -> PositionStore:
    """Create a PositionStore using the same DB path."""
    s = PositionStore(db_path)
    yield s
    s.close()


@pytest.fixture
def _patch_db_path(monkeypatch, db_path: Path):
    """Patch DEFAULT_DB_PATH in daily_monitor module."""
    import ib_sec_mcp.mcp.tools.daily_monitor as dm_module

    monkeypatch.setattr(dm_module, "DEFAULT_DB_PATH", str(db_path))


@pytest.fixture
def _patch_raw_dir(monkeypatch, raw_data_dir: Path):
    """Patch RAW_DATA_DIR in daily_monitor module."""
    import ib_sec_mcp.mcp.tools.daily_monitor as dm_module

    monkeypatch.setattr(dm_module, "RAW_DATA_DIR", raw_data_dir)


@pytest.fixture
def mock_config():
    """Mock Config.load() returning credentials."""
    mock_creds = MagicMock()
    mock_creds.query_id = "test_query_id"
    mock_creds.token = "test_token"

    mock_cfg = MagicMock()
    mock_cfg.get_credentials.return_value = mock_creds

    return mock_cfg


@pytest.fixture
def mock_statement():
    """Mock FlexQueryClient statement result."""
    stmt = MagicMock()
    stmt.raw_data = SAMPLE_XML
    stmt.account_id = ACCOUNT_ID
    return stmt


@pytest.fixture
def mock_accounts():
    """Mock XMLParser.to_accounts result."""
    pos = make_position()
    account = make_account(positions=[pos])
    return {ACCOUNT_ID: account}


@pytest.fixture
def mcp_with_tools():
    """Create a FastMCP instance with daily monitor tools registered."""
    from fastmcp import FastMCP

    from ib_sec_mcp.mcp.tools.daily_monitor import register_daily_monitor_tools

    mcp = FastMCP("test")
    register_daily_monitor_tools(mcp)
    return mcp


# ---------------------------------------------------------------------------
# TestSyncDailySnapshot
# ---------------------------------------------------------------------------


class TestSyncDailySnapshot:
    """Tests for the sync_daily_snapshot tool."""

    @pytest.mark.asyncio
    async def test_happy_path_api_fetch(
        self,
        tmp_path,
        db_path,
        raw_data_dir,
        mock_config,
        mock_statement,
        mock_accounts,
        _patch_db_path,
        _patch_raw_dir,
        mcp_with_tools,
    ):
        """API fetch succeeds, data is parsed and synced."""
        tool_fn = await _get_tool_fn(mcp_with_tools, "sync_daily_snapshot")

        mock_client_instance = MagicMock()
        mock_client_instance.fetch_statement.return_value = mock_statement

        with (
            patch("ib_sec_mcp.utils.config.Config.load", return_value=mock_config),
            patch(
                "ib_sec_mcp.api.client.FlexQueryClient",
                return_value=mock_client_instance,
            ),
            patch(
                "ib_sec_mcp.core.parsers.XMLParser.to_accounts",
                return_value=mock_accounts,
            ),
        ):
            result_str = await tool_fn(
                start_date="2025-06-01",
                end_date="2025-06-15",
                ctx=None,
            )

        result = json.loads(result_str)
        assert result["status"] == "success"
        assert result["source"] == "api"
        assert result["positions_count"] == 1
        assert result["accounts_synced"] == 1
        assert result["account_details"][0]["account_id"] == ACCOUNT_ID
        assert "duration_seconds" in result
        assert result["xml_file_path"] is not None

    @pytest.mark.asyncio
    async def test_api_failure_fallback_to_cached_xml(
        self,
        tmp_path,
        db_path,
        raw_data_dir,
        mock_accounts,
        _patch_db_path,
        _patch_raw_dir,
        mcp_with_tools,
    ):
        """When API fails, falls back to cached XML file."""
        from ib_sec_mcp.api.client import FlexQueryAPIError

        tool_fn = await _get_tool_fn(mcp_with_tools, "sync_daily_snapshot")

        # Create a cached XML file
        cached_xml = raw_data_dir / "U1234567_2025-06-01_2025-06-15.xml"
        cached_xml.write_text(SAMPLE_XML, encoding="utf-8")

        mock_cfg = MagicMock()
        mock_creds = MagicMock()
        mock_creds.query_id = "test_query_id"
        mock_creds.token = "test_token"
        mock_cfg.get_credentials.return_value = mock_creds

        mock_client = MagicMock()
        mock_client.fetch_statement.side_effect = FlexQueryAPIError("API timeout")

        with (
            patch("ib_sec_mcp.utils.config.Config.load", return_value=mock_cfg),
            patch(
                "ib_sec_mcp.api.client.FlexQueryClient",
                return_value=mock_client,
            ),
            patch(
                "ib_sec_mcp.core.parsers.XMLParser.to_accounts",
                return_value=mock_accounts,
            ),
        ):
            result_str = await tool_fn(
                start_date="2025-06-01",
                end_date="2025-06-15",
                ctx=None,
            )

        result = json.loads(result_str)
        assert result["status"] == "fallback"
        assert result["source"] == "cached_xml"
        assert result["positions_count"] == 1
        assert result["accounts_synced"] == 1

    @pytest.mark.asyncio
    async def test_both_api_and_cache_fail(
        self,
        tmp_path,
        db_path,
        raw_data_dir,
        _patch_db_path,
        _patch_raw_dir,
        mcp_with_tools,
    ):
        """When both API and cached XML fail, returns graceful failure."""
        from ib_sec_mcp.api.client import FlexQueryAPIError

        tool_fn = await _get_tool_fn(mcp_with_tools, "sync_daily_snapshot")

        mock_cfg = MagicMock()
        mock_creds = MagicMock()
        mock_creds.query_id = "test_query_id"
        mock_creds.token = "test_token"
        mock_cfg.get_credentials.return_value = mock_creds

        mock_client = MagicMock()
        mock_client.fetch_statement.side_effect = FlexQueryAPIError("Network error")

        # No cached XML files in raw_data_dir (empty directory)

        with (
            patch("ib_sec_mcp.utils.config.Config.load", return_value=mock_cfg),
            patch(
                "ib_sec_mcp.api.client.FlexQueryClient",
                return_value=mock_client,
            ),
        ):
            result_str = await tool_fn(
                start_date="2025-06-01",
                end_date="2025-06-15",
                ctx=None,
            )

        result = json.loads(result_str)
        assert result["status"] == "failure"
        assert result["source"] == "none"
        assert result["positions_count"] == 0
        assert result["accounts_synced"] == 0
        assert "error" in result
        assert "Network error" in result["error"]
        assert result["comparison_summary"] is None

    @pytest.mark.asyncio
    async def test_comparison_with_previous_snapshot(
        self,
        tmp_path,
        db_path,
        raw_data_dir,
        mock_config,
        mock_statement,
        _patch_db_path,
        _patch_raw_dir,
        mcp_with_tools,
    ):
        """When a previous snapshot exists, comparison summary is populated."""
        tool_fn = await _get_tool_fn(mcp_with_tools, "sync_daily_snapshot")

        # Pre-populate a previous snapshot
        prev_store = PositionStore(db_path)
        prev_date = date(2025, 6, 10)
        prev_pos = make_position(position_value="14000.00", unrealized_pnl="0.00")
        prev_account = make_account(
            positions=[prev_pos],
            from_date=date(2025, 6, 1),
            to_date=prev_date,
        )
        prev_store.save_snapshot(prev_account, prev_date, "/data/prev.xml")
        prev_store.close()

        # Current snapshot positions (value changed)
        current_pos = make_position(position_value="15000.00", unrealized_pnl="1000.00")
        current_account = make_account(positions=[current_pos])
        current_accounts = {ACCOUNT_ID: current_account}

        mock_client = MagicMock()
        mock_client.fetch_statement.return_value = mock_statement

        with (
            patch("ib_sec_mcp.utils.config.Config.load", return_value=mock_config),
            patch(
                "ib_sec_mcp.api.client.FlexQueryClient",
                return_value=mock_client,
            ),
            patch(
                "ib_sec_mcp.core.parsers.XMLParser.to_accounts",
                return_value=current_accounts,
            ),
        ):
            result_str = await tool_fn(
                start_date="2025-06-01",
                end_date="2025-06-15",
                ctx=None,
            )

        result = json.loads(result_str)
        assert result["status"] == "success"
        comp = result["comparison_summary"]
        assert comp is not None
        assert comp["account_id"] == ACCOUNT_ID
        assert comp["previous_date"] == prev_date.isoformat()
        assert comp["current_date"] == TO_DATE.isoformat()
        # Value changed from 14000 to 15000
        assert "total_value_change" in comp

    @pytest.mark.asyncio
    async def test_first_sync_no_previous_snapshot(
        self,
        tmp_path,
        db_path,
        raw_data_dir,
        mock_config,
        mock_statement,
        mock_accounts,
        _patch_db_path,
        _patch_raw_dir,
        mcp_with_tools,
    ):
        """First sync has no previous snapshot, comparison shows note."""
        tool_fn = await _get_tool_fn(mcp_with_tools, "sync_daily_snapshot")

        mock_client = MagicMock()
        mock_client.fetch_statement.return_value = mock_statement

        with (
            patch("ib_sec_mcp.utils.config.Config.load", return_value=mock_config),
            patch(
                "ib_sec_mcp.api.client.FlexQueryClient",
                return_value=mock_client,
            ),
            patch(
                "ib_sec_mcp.core.parsers.XMLParser.to_accounts",
                return_value=mock_accounts,
            ),
        ):
            result_str = await tool_fn(
                start_date="2025-06-01",
                end_date="2025-06-15",
                ctx=None,
            )

        result = json.loads(result_str)
        assert result["status"] == "success"
        comp = result["comparison_summary"]
        assert comp is not None
        assert "note" in comp
        assert "First sync" in comp["note"] or "one snapshot" in comp["note"]

    @pytest.mark.asyncio
    async def test_sync_logs_success_to_sync_log(
        self,
        tmp_path,
        db_path,
        raw_data_dir,
        mock_config,
        mock_statement,
        mock_accounts,
        _patch_db_path,
        _patch_raw_dir,
        mcp_with_tools,
    ):
        """Successful sync creates an entry in sync_log table."""
        tool_fn = await _get_tool_fn(mcp_with_tools, "sync_daily_snapshot")

        mock_client = MagicMock()
        mock_client.fetch_statement.return_value = mock_statement

        with (
            patch("ib_sec_mcp.utils.config.Config.load", return_value=mock_config),
            patch(
                "ib_sec_mcp.api.client.FlexQueryClient",
                return_value=mock_client,
            ),
            patch(
                "ib_sec_mcp.core.parsers.XMLParser.to_accounts",
                return_value=mock_accounts,
            ),
        ):
            await tool_fn(
                start_date="2025-06-01",
                end_date="2025-06-15",
                ctx=None,
            )

        # Check sync_log table
        check_db = DatabaseConnection(db_path)
        create_sync_log_table(check_db)
        logs = check_db.fetchall("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1")
        check_db.close()

        assert len(logs) == 1
        log = logs[0]
        assert log["status"] == "success"
        assert log["source"] == "api"
        assert log["accounts_synced"] == 1
        assert log["positions_count"] == 1
        assert log["duration_seconds"] is not None
        assert log["error_message"] is None

    @pytest.mark.asyncio
    async def test_sync_logs_failure_to_sync_log(
        self,
        tmp_path,
        db_path,
        raw_data_dir,
        _patch_db_path,
        _patch_raw_dir,
        mcp_with_tools,
    ):
        """Failed sync (both API and cache) creates a failure entry in sync_log."""
        from ib_sec_mcp.api.client import FlexQueryAPIError

        tool_fn = await _get_tool_fn(mcp_with_tools, "sync_daily_snapshot")

        mock_cfg = MagicMock()
        mock_creds = MagicMock()
        mock_creds.query_id = "q"
        mock_creds.token = "t"
        mock_cfg.get_credentials.return_value = mock_creds

        mock_client = MagicMock()
        mock_client.fetch_statement.side_effect = FlexQueryAPIError("Down")

        with (
            patch("ib_sec_mcp.utils.config.Config.load", return_value=mock_cfg),
            patch(
                "ib_sec_mcp.api.client.FlexQueryClient",
                return_value=mock_client,
            ),
        ):
            await tool_fn(
                start_date="2025-06-01",
                end_date="2025-06-15",
                ctx=None,
            )

        check_db = DatabaseConnection(db_path)
        create_sync_log_table(check_db)
        logs = check_db.fetchall("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1")
        check_db.close()

        assert len(logs) == 1
        log = logs[0]
        assert log["status"] == "failure"
        assert log["source"] == "none"
        assert log["error_message"] is not None
        assert "Down" in log["error_message"]


# ---------------------------------------------------------------------------
# TestGetSyncStatus
# ---------------------------------------------------------------------------


class TestGetSyncStatus:
    """Tests for the get_sync_status tool."""

    @pytest.mark.asyncio
    async def test_status_with_existing_data(
        self,
        db_path,
        store,
        _patch_db_path,
        mcp_with_tools,
    ):
        """Returns healthy status when recent snapshots exist."""
        tool_fn = await _get_tool_fn(mcp_with_tools, "get_sync_status")

        # Save a snapshot with today's date
        today = date.today()
        pos = make_position()
        account = make_account(positions=[pos], from_date=today, to_date=today)
        store.save_snapshot(account, today, "/data/today.xml")

        # Also add a sync_log entry
        log_db = DatabaseConnection(db_path)
        create_sync_log_table(log_db)
        with log_db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO sync_log (sync_date, status, source, accounts_synced,
                                      positions_count, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (today.isoformat(), "success", "api", 1, 1, 2.5),
            )
        log_db.close()

        result_str = await tool_fn(ctx=None)
        result = json.loads(result_str)

        assert result["status"] == "healthy"
        assert result["alert"] is False
        assert result["total_snapshots"] >= 1
        assert result["last_snapshot_date"] == today.isoformat()
        assert result["days_since_last_sync"] == 0
        assert result["db_size_bytes"] > 0
        assert result["unique_accounts"] >= 1
        assert result["last_successful_sync"] is not None
        assert len(result["recent_sync_logs"]) >= 1

    @pytest.mark.asyncio
    async def test_status_with_no_database(
        self,
        tmp_path,
        monkeypatch,
        mcp_with_tools,
    ):
        """Returns no_database status when DB file does not exist."""
        import ib_sec_mcp.mcp.tools.daily_monitor as dm_module

        tool_fn = await _get_tool_fn(mcp_with_tools, "get_sync_status")

        # Point to a non-existent DB path (use a file that definitely does not exist)
        non_existent = tmp_path / "nonexistent_dir" / "positions.db"
        monkeypatch.setattr(dm_module, "DEFAULT_DB_PATH", str(non_existent))

        result_str = await tool_fn(ctx=None)
        result = json.loads(result_str)

        assert result["status"] == "no_database"
        assert result["alert"] is True
        assert result["alert_message"] == "Database does not exist"
        assert result["total_snapshots"] == 0
        assert result["last_sync_date"] is None
        assert result["db_size_bytes"] == 0
        assert result["recent_sync_logs"] == []

    @pytest.mark.asyncio
    async def test_status_empty_database(
        self,
        db_path,
        _patch_db_path,
        mcp_with_tools,
    ):
        """Returns warning when DB exists but has no snapshots."""
        tool_fn = await _get_tool_fn(mcp_with_tools, "get_sync_status")

        # Create an empty DB with schema but no data
        empty_db = DatabaseConnection(db_path)
        create_schema(empty_db)
        create_sync_log_table(empty_db)
        empty_db.close()

        result_str = await tool_fn(ctx=None)
        result = json.loads(result_str)

        assert result["status"] == "warning"
        assert result["alert"] is True
        assert result["alert_message"] == "No snapshots found in database"
        assert result["total_snapshots"] == 0
        assert result["days_since_last_sync"] is None

    @pytest.mark.asyncio
    async def test_stale_alert_over_two_days(
        self,
        db_path,
        store,
        _patch_db_path,
        mcp_with_tools,
    ):
        """Returns warning when last sync was more than 2 days ago."""
        tool_fn = await _get_tool_fn(mcp_with_tools, "get_sync_status")

        # Save a snapshot from 5 days ago
        stale_date = date.today() - timedelta(days=5)
        pos = make_position()
        account = make_account(positions=[pos], from_date=stale_date, to_date=stale_date)
        store.save_snapshot(account, stale_date, "/data/stale.xml")

        result_str = await tool_fn(ctx=None)
        result = json.loads(result_str)

        assert result["status"] == "warning"
        assert result["alert"] is True
        assert "5 days ago" in result["alert_message"]
        assert result["days_since_last_sync"] == 5

    @pytest.mark.asyncio
    async def test_recent_sync_logs_returned(
        self,
        db_path,
        store,
        _patch_db_path,
        mcp_with_tools,
    ):
        """Recent sync log entries are included in the response."""
        tool_fn = await _get_tool_fn(mcp_with_tools, "get_sync_status")

        today = date.today()
        pos = make_position()
        account = make_account(positions=[pos], from_date=today, to_date=today)
        store.save_snapshot(account, today, "/data/today.xml")

        # Insert multiple sync log entries
        log_db = DatabaseConnection(db_path)
        create_sync_log_table(log_db)
        for i in range(3):
            with log_db.transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO sync_log (sync_date, status, source,
                                          accounts_synced, positions_count)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (today.isoformat(), "success", "api", 1, i + 1),
                )
        log_db.close()

        result_str = await tool_fn(ctx=None)
        result = json.loads(result_str)

        assert len(result["recent_sync_logs"]) == 3


# ---------------------------------------------------------------------------
# TestHelpers
# ---------------------------------------------------------------------------


class TestHelpers:
    """Tests for module-level helper functions."""

    def test_find_latest_cached_xml_no_directory(self, monkeypatch, tmp_path):
        """Returns None when RAW_DATA_DIR does not exist."""
        import ib_sec_mcp.mcp.tools.daily_monitor as dm_module

        non_existent = tmp_path / "does_not_exist"
        monkeypatch.setattr(dm_module, "RAW_DATA_DIR", non_existent)

        from ib_sec_mcp.mcp.tools.daily_monitor import _find_latest_cached_xml

        assert _find_latest_cached_xml() is None

    def test_find_latest_cached_xml_empty_directory(self, monkeypatch, tmp_path):
        """Returns None when directory exists but has no XML files."""
        import ib_sec_mcp.mcp.tools.daily_monitor as dm_module

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.setattr(dm_module, "RAW_DATA_DIR", empty_dir)

        from ib_sec_mcp.mcp.tools.daily_monitor import _find_latest_cached_xml

        assert _find_latest_cached_xml() is None

    def test_find_latest_cached_xml_returns_most_recent(self, monkeypatch, tmp_path):
        """Returns the most recently modified XML file."""
        import ib_sec_mcp.mcp.tools.daily_monitor as dm_module

        data_dir = tmp_path / "raw"
        data_dir.mkdir()
        monkeypatch.setattr(dm_module, "RAW_DATA_DIR", data_dir)

        # Create two XML files with different modification times
        old_file = data_dir / "old.xml"
        old_file.write_text("<old/>", encoding="utf-8")

        # Ensure different mtime
        os.utime(old_file, (time.time() - 100, time.time() - 100))

        new_file = data_dir / "new.xml"
        new_file.write_text("<new/>", encoding="utf-8")

        from ib_sec_mcp.mcp.tools.daily_monitor import _find_latest_cached_xml

        result = _find_latest_cached_xml()
        assert result == new_file

    def test_find_latest_cached_xml_ignores_non_xml(self, monkeypatch, tmp_path):
        """Non-XML files are ignored."""
        import ib_sec_mcp.mcp.tools.daily_monitor as dm_module

        data_dir = tmp_path / "raw"
        data_dir.mkdir()
        monkeypatch.setattr(dm_module, "RAW_DATA_DIR", data_dir)

        # Create only non-XML files
        (data_dir / "data.csv").write_text("csv data", encoding="utf-8")
        (data_dir / "notes.txt").write_text("notes", encoding="utf-8")

        from ib_sec_mcp.mcp.tools.daily_monitor import _find_latest_cached_xml

        assert _find_latest_cached_xml() is None

    def test_log_sync_records_entry(self, db):
        """_log_sync inserts a row into sync_log table."""
        from ib_sec_mcp.mcp.tools.daily_monitor import _log_sync

        _log_sync(
            db=db,
            sync_date="2025-06-15",
            status="success",
            source="api",
            accounts_synced=2,
            positions_count=15,
            duration_seconds=3.45,
        )

        logs = db.fetchall("SELECT * FROM sync_log")
        assert len(logs) == 1
        log = logs[0]
        assert log["sync_date"] == "2025-06-15"
        assert log["status"] == "success"
        assert log["source"] == "api"
        assert log["accounts_synced"] == 2
        assert log["positions_count"] == 15
        assert log["error_message"] is None
        assert log["xml_file_path"] is None
        assert log["duration_seconds"] == 3.45

    def test_log_sync_records_error(self, db):
        """_log_sync records error details correctly."""
        from ib_sec_mcp.mcp.tools.daily_monitor import _log_sync

        _log_sync(
            db=db,
            sync_date="2025-06-15",
            status="failure",
            source="none",
            error_message="FlexQueryAPIError: timeout",
            xml_file_path="/data/raw/cached.xml",
            duration_seconds=60.0,
        )

        logs = db.fetchall("SELECT * FROM sync_log")
        assert len(logs) == 1
        log = logs[0]
        assert log["status"] == "failure"
        assert log["source"] == "none"
        assert log["error_message"] == "FlexQueryAPIError: timeout"
        assert log["xml_file_path"] == "/data/raw/cached.xml"
        assert log["duration_seconds"] == 60.0

    def test_log_sync_multiple_entries(self, db):
        """Multiple _log_sync calls create multiple rows."""
        from ib_sec_mcp.mcp.tools.daily_monitor import _log_sync

        for i in range(5):
            _log_sync(
                db=db,
                sync_date=f"2025-06-{10 + i:02d}",
                status="success",
                source="api",
                positions_count=i * 10,
            )

        logs = db.fetchall("SELECT * FROM sync_log ORDER BY id")
        assert len(logs) == 5
        assert logs[0]["positions_count"] == 0
        assert logs[4]["positions_count"] == 40

    def test_log_sync_fallback_status(self, db):
        """_log_sync correctly records fallback status with API error."""
        from ib_sec_mcp.mcp.tools.daily_monitor import _log_sync

        _log_sync(
            db=db,
            sync_date="2025-06-15",
            status="fallback",
            source="cached_xml",
            accounts_synced=1,
            positions_count=5,
            error_message="FlexQueryAPIError: API down",
            xml_file_path="/data/raw/cached.xml",
            duration_seconds=1.2,
        )

        logs = db.fetchall("SELECT * FROM sync_log")
        assert len(logs) == 1
        log = logs[0]
        assert log["status"] == "fallback"
        assert log["source"] == "cached_xml"
        assert log["error_message"] == "FlexQueryAPIError: API down"
