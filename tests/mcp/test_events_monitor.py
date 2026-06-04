"""Tests for the upcoming-events monitoring MCP tool.

The tool is registered on a real :class:`fastmcp.FastMCP` instance and invoked
through the FastMCP tool API so the production path is exercised. All yfinance
access is mocked, keeping the suite network-independent.
"""

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.tools.events_monitor import (
    build_symbol_events,
    register_events_monitor_tools,
)
from ib_sec_mcp.storage import PositionStore
from tests.mcp._fastmcp_helpers import call_tool_fn

PATCH_TARGET = "ib_sec_mcp.mcp.tools.events_monitor.yf.Ticker"


class FakeTicker:
    """yfinance ticker fake backed by per-symbol calendar data."""

    calendars: dict[str, Any] = {}

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    @property
    def calendar(self) -> Any:
        value = self.calendars[self.symbol]
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with the events monitor tool registered."""
    mcp = FastMCP("test")
    register_events_monitor_tools(mcp)
    return mcp


@pytest.fixture()
def patch_ticker(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, Any]], None]:
    """Install FakeTicker with the given per-symbol calendar data."""

    def _apply(calendars: dict[str, Any]) -> None:
        monkeypatch.setattr(FakeTicker, "calendars", calendars)
        monkeypatch.setattr(PATCH_TARGET, FakeTicker)

    return _apply


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """Freeze today and ignore env account IDs for deterministic days-until."""
    import ib_sec_mcp.mcp.tools.earnings_calendar as ec_module
    import ib_sec_mcp.mcp.tools.events_monitor as module

    monkeypatch.setattr(module, "_today", lambda: date(2026, 1, 1))
    for env_var in ec_module.ACCOUNT_ID_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


# ---------------------------------------------------------------------------
# Pure helper: build_symbol_events
# ---------------------------------------------------------------------------
def test_build_symbol_events_flags_and_filters() -> None:
    """Imminent events are flagged EVENT_SOON; out-of-horizon events dropped."""
    calendar = {
        "Earnings Date": [date(2026, 1, 3)],  # 2 days -> EVENT_SOON
        "Ex-Dividend Date": date(2026, 1, 10),  # 9 days -> no flag
    }
    records = build_symbol_events("AAPL", calendar, date(2026, 1, 1), 14, 3)

    by_type = {r["event_type"]: r for r in records}
    assert by_type["earnings"]["days_until"] == 2
    assert by_type["earnings"]["flag"] == "EVENT_SOON"
    assert by_type["ex_dividend"]["days_until"] == 9
    assert by_type["ex_dividend"]["flag"] is None


def test_build_symbol_events_omits_events_beyond_horizon() -> None:
    """Events past the horizon produce no records."""
    calendar = {"Earnings Date": [date(2026, 3, 1)], "Ex-Dividend Date": None}
    assert build_symbol_events("AAPL", calendar, date(2026, 1, 1), 14, 3) == []


# ---------------------------------------------------------------------------
# Tool: get_upcoming_events
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_upcoming_events_aggregates_and_sorts(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Events across symbols are flattened and sorted soonest-first."""
    patch_ticker(
        {
            "AAPL": {"Earnings Date": [date(2026, 1, 10)], "Ex-Dividend Date": None},
            "MSFT": {"Earnings Date": [date(2026, 1, 2)], "Ex-Dividend Date": None},
        }
    )

    result = await call_tool_fn(
        test_mcp,
        "get_upcoming_events",
        days=14,
        symbols=["AAPL", "MSFT"],
        ctx=None,
    )
    data = json.loads(result)

    assert data["event_count"] == 2
    assert [e["symbol"] for e in data["events"]] == ["MSFT", "AAPL"]
    assert data["events"][0]["days_until"] == 1
    assert data["events"][0]["flag"] == "EVENT_SOON"
    assert data["event_soon_count"] == 1


@pytest.mark.asyncio
async def test_get_upcoming_events_merges_watchlist(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Watchlist symbols are monitored alongside the base symbol set."""
    patch_ticker(
        {
            "AAPL": {"Earnings Date": [date(2026, 1, 5)], "Ex-Dividend Date": None},
            "NVDA": {"Earnings Date": [date(2026, 1, 8)], "Ex-Dividend Date": None},
        }
    )

    result = await call_tool_fn(
        test_mcp,
        "get_upcoming_events",
        days=14,
        symbols=["AAPL"],
        watchlist=["NVDA"],
        ctx=None,
    )
    data = json.loads(result)

    assert {e["symbol"] for e in data["events"]} == {"AAPL", "NVDA"}


@pytest.mark.asyncio
async def test_get_upcoming_events_custom_soon_threshold(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """A wider soon threshold flags more events as EVENT_SOON."""
    patch_ticker({"AAPL": {"Earnings Date": [date(2026, 1, 6)], "Ex-Dividend Date": None}})

    result = await call_tool_fn(
        test_mcp,
        "get_upcoming_events",
        days=14,
        symbols=["AAPL"],
        soon_threshold_days=7,
        ctx=None,
    )
    data = json.loads(result)

    assert data["events"][0]["flag"] == "EVENT_SOON"
    assert data["event_soon_count"] == 1


@pytest.mark.asyncio
async def test_get_upcoming_events_collects_per_symbol_errors(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """A yfinance failure becomes an error entry without aborting the sweep."""
    patch_ticker(
        {
            "AAPL": {"Earnings Date": [date(2026, 1, 5)], "Ex-Dividend Date": None},
            "BROKEN": RuntimeError("symbol not supported"),
        }
    )

    result = await call_tool_fn(
        test_mcp,
        "get_upcoming_events",
        days=14,
        symbols=["AAPL", "BROKEN"],
        ctx=None,
    )
    data = json.loads(result)

    assert [e["symbol"] for e in data["events"]] == ["AAPL"]
    assert data["errors"] == [{"symbol": "BROKEN", "error": "symbol not supported"}]


@pytest.mark.asyncio
async def test_get_upcoming_events_reports_invalid_symbols(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Invalid symbols are surfaced as errors while valid ones are processed."""
    patch_ticker({"AAPL": {"Earnings Date": [date(2026, 1, 5)], "Ex-Dividend Date": None}})

    result = await call_tool_fn(
        test_mcp,
        "get_upcoming_events",
        days=14,
        symbols=["AAPL", "!!bad!!"],
        ctx=None,
    )
    data = json.loads(result)

    assert [e["symbol"] for e in data["events"]] == ["AAPL"]
    assert any(e.get("symbol") == "!!bad!!" for e in data["errors"])


@pytest.mark.asyncio
async def test_get_upcoming_events_rejects_negative_days(test_mcp: FastMCP) -> None:
    """A negative horizon is rejected before any yfinance access."""
    result = await call_tool_fn(test_mcp, "get_upcoming_events", days=-1, ctx=None)
    assert json.loads(result) == {"error": "days must be zero or greater"}


@pytest.mark.asyncio
async def test_get_upcoming_events_rejects_negative_soon_threshold(test_mcp: FastMCP) -> None:
    """A negative soon threshold is rejected before any yfinance access."""
    result = await call_tool_fn(
        test_mcp, "get_upcoming_events", days=14, soon_threshold_days=-1, ctx=None
    )
    assert json.loads(result) == {"error": "soon_threshold_days must be zero or greater"}


@pytest.mark.asyncio
async def test_get_upcoming_events_loads_symbols_from_snapshot(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any]], None],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When symbols are omitted, the latest PositionStore snapshot supplies them."""
    import ib_sec_mcp.mcp.tools.earnings_calendar as ec_module

    db_path = tmp_path / "positions.db"
    with PositionStore(db_path) as store, store.db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO snapshot_metadata
            (account_id, snapshot_date, xml_file_path, date_range_from, date_range_to,
             total_positions, total_value, total_cash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("U1234567", "2025-12-31", "test.xml", "2025-12-01", "2025-12-31", 1, "1", "0"),
        )
        conn.execute(
            """
            INSERT INTO position_snapshots
            (account_id, snapshot_date, symbol, description, asset_class,
             quantity, mark_price, position_value, average_cost, cost_basis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("U1234567", "2025-12-31", "AAPL", "AAPL", "STK", "1", "1", "1", "1", "1"),
        )

    monkeypatch.setattr(ec_module, "DEFAULT_DB_PATH", str(db_path))
    patch_ticker({"AAPL": {"Earnings Date": [date(2026, 1, 5)], "Ex-Dividend Date": None}})

    result = await call_tool_fn(test_mcp, "get_upcoming_events", days=14, ctx=None)
    data = json.loads(result)

    assert [e["symbol"] for e in data["events"]] == ["AAPL"]
