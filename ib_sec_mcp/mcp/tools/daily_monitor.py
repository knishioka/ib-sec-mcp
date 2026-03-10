"""Daily Monitor Tools

MCP tools for reliable daily fetch+sync pipeline with fallback and logging.
"""

import json
import time
from datetime import date
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP

from ib_sec_mcp.storage import PositionStore
from ib_sec_mcp.storage.database import DatabaseConnection
from ib_sec_mcp.storage.migrations import create_sync_log_table
from ib_sec_mcp.utils.logger import get_logger

logger = get_logger(__name__)

# Default paths
DEFAULT_DB_PATH = "data/processed/positions.db"
RAW_DATA_DIR = Path("data/raw")


def _find_latest_cached_xml() -> Path | None:
    """Find the most recently modified XML file in data/raw/."""
    if not RAW_DATA_DIR.exists():
        return None
    xml_files = list(RAW_DATA_DIR.glob("*.xml"))
    if not xml_files:
        return None
    return max(xml_files, key=lambda p: p.stat().st_mtime)


def _log_sync(
    db: DatabaseConnection,
    sync_date: str,
    status: str,
    source: str,
    accounts_synced: int = 0,
    positions_count: int = 0,
    error_message: str | None = None,
    xml_file_path: str | None = None,
    duration_seconds: float | None = None,
) -> None:
    """Record a sync attempt in the sync_log table."""
    with db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO sync_log
            (sync_date, status, source, accounts_synced, positions_count,
             error_message, xml_file_path, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sync_date,
                status,
                source,
                accounts_synced,
                positions_count,
                error_message,
                xml_file_path,
                duration_seconds,
            ),
        )


def register_daily_monitor_tools(mcp: FastMCP) -> None:
    """Register daily monitor tools for reliable fetch+sync pipeline."""

    @mcp.tool
    async def sync_daily_snapshot(
        start_date: str | None = None,
        end_date: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """
        Fetch and sync daily portfolio snapshot with fallback and logging.

        Wraps the fetch+sync flow with reliability features:
        - Explicit success/failure status
        - Fallback to cached XML if API fails
        - Comparison with previous snapshot
        - Sync logging to sync_log table

        Args:
            start_date: Start date YYYY-MM-DD (defaults to 30 days ago)
            end_date: End date YYYY-MM-DD (defaults to today)
            ctx: MCP context for logging

        Returns:
            JSON string with sync_date, positions_count, accounts_synced,
            comparison_summary, status, and source
        """
        import asyncio

        from ib_sec_mcp.api.client import FlexQueryAPIError, FlexQueryClient
        from ib_sec_mcp.core.parsers import XMLParser
        from ib_sec_mcp.mcp.validators import validate_date_range, validate_date_string
        from ib_sec_mcp.utils.config import Config

        start_time = time.monotonic()
        today = date.today()

        # Parse dates
        to_date = validate_date_string(end_date, "end_date") if end_date else today
        from_date = (
            validate_date_string(start_date, "start_date")
            if start_date
            else date(to_date.year, to_date.month, 1)
        )

        from_date, to_date = validate_date_range(from_date, to_date)

        if ctx:
            await ctx.info(f"Starting daily sync for {from_date} to {to_date}")

        # Ensure sync_log table exists
        db = DatabaseConnection(DEFAULT_DB_PATH)
        create_sync_log_table(db)

        xml_data: str | None = None
        source = "api"
        xml_file_path: str | None = None
        api_error_msg: str | None = None

        # Step 1: Try API fetch
        try:
            config = Config.load()
            credentials = config.get_credentials()
            client = FlexQueryClient(
                query_id=credentials.query_id,
                token=credentials.token,
            )

            if ctx:
                await ctx.info("Fetching data from IB Flex Query API...")

            async def fetch_with_timeout() -> Any:
                return await asyncio.to_thread(client.fetch_statement, from_date, to_date)

            statement = await asyncio.wait_for(fetch_with_timeout(), timeout=60)
            xml_data = statement.raw_data

            # Save XML to cache
            RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"{statement.account_id}_{from_date}_{to_date}.xml"
            filepath = RAW_DATA_DIR / filename
            filepath.write_text(xml_data, encoding="utf-8")
            xml_file_path = str(filepath)

            if ctx:
                await ctx.info(f"API fetch successful, saved to {filepath}")

        except (TimeoutError, FlexQueryAPIError, Exception) as e:
            api_error_msg = f"{type(e).__name__}: {e!s}"
            source = "cached_xml"

            if ctx:
                await ctx.warning(f"API fetch failed: {api_error_msg}. Trying cached XML...")

            logger.warning(f"API fetch failed: {api_error_msg}")

            # Step 2: Fallback to cached XML
            cached_file = _find_latest_cached_xml()
            if cached_file:
                xml_data = cached_file.read_text(encoding="utf-8")
                xml_file_path = str(cached_file)
                if ctx:
                    await ctx.info(f"Using cached XML: {cached_file.name}")
            else:
                duration = time.monotonic() - start_time
                _log_sync(
                    db,
                    sync_date=today.isoformat(),
                    status="failure",
                    source="none",
                    error_message=f"API failed ({api_error_msg}) and no cached XML found",
                    duration_seconds=duration,
                )
                db.close()
                return json.dumps(
                    {
                        "sync_date": today.isoformat(),
                        "status": "failure",
                        "source": "none",
                        "error": f"API failed and no cached XML available. API error: {api_error_msg}",
                        "positions_count": 0,
                        "accounts_synced": 0,
                        "comparison_summary": None,
                    },
                    default=str,
                )

        # Step 3: Parse and sync to SQLite
        try:
            accounts = XMLParser.to_accounts(xml_data, from_date, to_date)

            store = PositionStore(DEFAULT_DB_PATH)
            total_positions = 0
            accounts_synced = 0
            account_details: list[dict[str, Any]] = []

            for account_id, account in accounts.items():
                positions_saved = store.save_snapshot(
                    account=account,
                    snapshot_date=to_date,
                    xml_file_path=xml_file_path or "unknown",
                )
                total_positions += positions_saved
                accounts_synced += 1
                account_details.append(
                    {
                        "account_id": account_id,
                        "positions_saved": positions_saved,
                    }
                )

            # Step 4: Compare with previous snapshot
            comparison_summary: dict[str, Any] | None = None
            for account_id in accounts:
                available_dates = store.get_available_dates(account_id)
                # Need at least 2 dates for comparison
                if len(available_dates) >= 2:
                    prev_date_str = available_dates[1]  # Second most recent
                    prev_date = date.fromisoformat(prev_date_str)
                    try:
                        comparison = store.compare_portfolio_snapshots(
                            account_id, prev_date, to_date
                        )
                        comparison_summary = {
                            "account_id": account_id,
                            "previous_date": prev_date.isoformat(),
                            "current_date": to_date.isoformat(),
                            "positions_added": comparison["positions_added"],
                            "positions_removed": comparison["positions_removed"],
                            "total_value_change": str(comparison["total_value_change"]),
                            "total_value_change_pct": str(comparison["total_value_change_pct"]),
                        }
                    except Exception as e:
                        logger.warning(f"Comparison failed for {account_id}: {e!s}")
                        comparison_summary = {
                            "note": f"Comparison unavailable: {e!s}",
                        }
                    break  # Compare first account only
                else:
                    comparison_summary = {
                        "note": "First sync or only one snapshot available, no comparison",
                    }

            store.close()

            duration = time.monotonic() - start_time

            # Log success
            _log_sync(
                db,
                sync_date=today.isoformat(),
                status="success" if source == "api" else "fallback",
                source=source,
                accounts_synced=accounts_synced,
                positions_count=total_positions,
                xml_file_path=xml_file_path,
                duration_seconds=duration,
                error_message=api_error_msg,
            )
            db.close()

            if ctx:
                await ctx.info(
                    f"Sync complete: {total_positions} positions from {accounts_synced} account(s)"
                )

            return json.dumps(
                {
                    "sync_date": today.isoformat(),
                    "status": "success" if source == "api" else "fallback",
                    "source": source,
                    "positions_count": total_positions,
                    "accounts_synced": accounts_synced,
                    "account_details": account_details,
                    "comparison_summary": comparison_summary,
                    "duration_seconds": round(duration, 2),
                    "xml_file_path": xml_file_path,
                },
                default=str,
            )

        except Exception as e:
            duration = time.monotonic() - start_time
            error_msg = f"{type(e).__name__}: {e!s}"
            logger.error(f"Sync failed: {error_msg}", exc_info=True)

            _log_sync(
                db,
                sync_date=today.isoformat(),
                status="failure",
                source=source,
                error_message=error_msg,
                xml_file_path=xml_file_path,
                duration_seconds=duration,
            )
            db.close()

            if ctx:
                await ctx.error(f"Sync failed: {error_msg}")

            return json.dumps(
                {
                    "sync_date": today.isoformat(),
                    "status": "failure",
                    "source": source,
                    "error": error_msg,
                    "positions_count": 0,
                    "accounts_synced": 0,
                    "comparison_summary": None,
                },
                default=str,
            )

    @mcp.tool
    async def get_sync_status(
        ctx: Context | None = None,
    ) -> str:
        """
        Check sync pipeline health status.

        Returns actionable health check info including:
        - Last sync date and status
        - Number of snapshots in DB
        - DB file size
        - Days since last sync (alerts if > 2 days)
        - Recent sync log entries

        Args:
            ctx: MCP context for logging

        Returns:
            JSON string with health check information
        """
        db_path = Path(DEFAULT_DB_PATH)

        # Check if DB exists
        if not db_path.exists():
            return json.dumps(
                {
                    "status": "no_database",
                    "message": "No database found. Run sync_daily_snapshot first.",
                    "db_path": str(db_path),
                    "db_size_bytes": 0,
                    "last_sync_date": None,
                    "days_since_last_sync": None,
                    "total_snapshots": 0,
                    "alert": True,
                    "alert_message": "Database does not exist",
                    "recent_sync_logs": [],
                }
            )

        db = DatabaseConnection(DEFAULT_DB_PATH)
        create_sync_log_table(db)

        today = date.today()

        # DB file size
        db_size_bytes = db_path.stat().st_size

        # Snapshot count and last sync date from snapshot_metadata
        snapshot_info = db.fetchone(
            """
            SELECT
                COUNT(*) as total_snapshots,
                MAX(snapshot_date) as last_snapshot_date,
                COUNT(DISTINCT account_id) as unique_accounts,
                COUNT(DISTINCT snapshot_date) as unique_dates
            FROM snapshot_metadata
            """
        )

        total_snapshots = snapshot_info["total_snapshots"] if snapshot_info else 0
        last_snapshot_date = snapshot_info["last_snapshot_date"] if snapshot_info else None
        unique_accounts = snapshot_info["unique_accounts"] if snapshot_info else 0
        unique_dates = snapshot_info["unique_dates"] if snapshot_info else 0

        # Calculate days since last sync
        days_since_last_sync: int | None = None
        if last_snapshot_date:
            last_date = date.fromisoformat(last_snapshot_date)
            days_since_last_sync = (today - last_date).days

        # Alert logic
        alert = False
        alert_message: str | None = None
        if days_since_last_sync is None:
            alert = True
            alert_message = "No snapshots found in database"
        elif days_since_last_sync > 2:
            alert = True
            alert_message = f"Last sync was {days_since_last_sync} days ago (threshold: 2 days)"

        # Recent sync logs
        recent_logs = db.fetchall(
            """
            SELECT
                sync_date, status, source, accounts_synced, positions_count,
                error_message, duration_seconds, created_at
            FROM sync_log
            ORDER BY created_at DESC
            LIMIT 10
            """
        )

        # Last successful sync from sync_log
        last_success = db.fetchone(
            """
            SELECT sync_date, source, positions_count, accounts_synced, created_at
            FROM sync_log
            WHERE status IN ('success', 'fallback')
            ORDER BY created_at DESC
            LIMIT 1
            """
        )

        db.close()

        result = {
            "status": "healthy" if not alert else "warning",
            "db_path": str(db_path),
            "db_size_bytes": db_size_bytes,
            "db_size_mb": round(db_size_bytes / (1024 * 1024), 2),
            "last_snapshot_date": last_snapshot_date,
            "days_since_last_sync": days_since_last_sync,
            "total_snapshots": total_snapshots,
            "unique_accounts": unique_accounts,
            "unique_snapshot_dates": unique_dates,
            "alert": alert,
            "alert_message": alert_message,
            "last_successful_sync": dict(last_success) if last_success else None,
            "recent_sync_logs": [dict(log) for log in recent_logs],
        }

        if ctx:
            status_emoji = "healthy" if not alert else "WARNING"
            await ctx.info(
                f"Sync status: {status_emoji} | "
                f"Last sync: {last_snapshot_date or 'never'} | "
                f"Snapshots: {total_snapshots}"
            )

        return json.dumps(result, default=str)
