"""Tests for earnings calendar MCP tools."""

import json
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from ib_sec_mcp.storage import PositionStore


class CaptureMCP:
    """Capture registered FastMCP tool functions."""

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, fn: Any) -> Any:
        self.tools[fn.__name__] = fn
        return fn


class FakeTicker:
    """Simple yfinance ticker fake backed by per-symbol calendar data."""

    calendars: dict[str, Any] = {}

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    @property
    def calendar(self) -> Any:
        value = self.calendars[self.symbol]
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture
def tool_registry() -> dict[str, Any]:
    """Register earnings calendar tools and return captured functions."""
    from ib_sec_mcp.mcp.tools.earnings_calendar import register_earnings_calendar_tools

    mcp = CaptureMCP()
    register_earnings_calendar_tools(mcp)
    return mcp.tools


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make days-until calculations deterministic."""
    import ib_sec_mcp.mcp.tools.earnings_calendar as module

    monkeypatch.setattr(module, "_today", lambda: date(2026, 1, 1))
    for env_var in module.ACCOUNT_ID_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


@pytest.mark.asyncio
async def test_get_earnings_calendar_returns_sorted_events(tool_registry: dict[str, Any]) -> None:
    """Multiple symbol results are returned in upcoming event order."""
    FakeTicker.calendars = {
        "AAPL": {
            "Earnings Date": [date(2026, 1, 20)],
            "Ex-Dividend Date": date(2026, 1, 10),
        },
        "MSFT": {
            "Earnings Date": [date(2026, 1, 5)],
            "Ex-Dividend Date": date(2026, 3, 1),
        },
    }

    with patch("ib_sec_mcp.mcp.tools.earnings_calendar.yf.Ticker", FakeTicker):
        result = await tool_registry["get_earnings_calendar"](
            symbols=["AAPL", "MSFT"],
            days_ahead=90,
            ctx=None,
        )

    parsed = json.loads(result)

    assert [entry["symbol"] for entry in parsed] == ["MSFT", "AAPL"]
    assert parsed[0]["next_earnings_date"] == "2026-01-05"
    assert parsed[0]["days_until_earnings"] == 4
    assert parsed[1]["ex_dividend_date"] == "2026-01-10"
    assert parsed[1]["days_until_ex_dividend"] == 9


@pytest.mark.asyncio
async def test_get_earnings_calendar_includes_per_symbol_errors(
    tool_registry: dict[str, Any],
) -> None:
    """A yfinance failure for one symbol is included without stopping processing."""
    FakeTicker.calendars = {
        "AAPL": {
            "Earnings Date": [date(2026, 1, 20)],
            "Ex-Dividend Date": None,
        },
        "BROKEN": RuntimeError("symbol not supported"),
    }

    with patch("ib_sec_mcp.mcp.tools.earnings_calendar.yf.Ticker", FakeTicker):
        result = await tool_registry["get_earnings_calendar"](
            symbols=["AAPL", "BROKEN"],
            days_ahead=90,
            ctx=None,
        )

    parsed = json.loads(result)

    assert parsed[0]["symbol"] == "AAPL"
    assert parsed[1] == {"symbol": "BROKEN", "error": "symbol not supported"}


@pytest.mark.asyncio
async def test_get_earnings_calendar_filters_events_outside_days_ahead(
    tool_registry: dict[str, Any],
) -> None:
    """Events beyond the requested horizon are omitted."""
    FakeTicker.calendars = {
        "AAPL": {
            "Earnings Date": [date(2026, 6, 1)],
            "Ex-Dividend Date": date(2026, 7, 1),
        },
    }

    with patch("ib_sec_mcp.mcp.tools.earnings_calendar.yf.Ticker", FakeTicker):
        result = await tool_registry["get_earnings_calendar"](
            symbols=["AAPL"],
            days_ahead=30,
            ctx=None,
        )

    assert json.loads(result) == []


@pytest.mark.asyncio
async def test_get_earnings_calendar_loads_symbols_from_latest_snapshot(
    tool_registry: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When symbols are omitted, the latest PositionStore snapshot supplies symbols."""
    import ib_sec_mcp.mcp.tools.earnings_calendar as module

    db_path = tmp_path / "positions.db"
    store = PositionStore(db_path)
    try:
        with store.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO snapshot_metadata
                (account_id, snapshot_date, xml_file_path, date_range_from, date_range_to,
                 total_positions, total_value, total_cash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("U1234567", "2025-12-31", "test.xml", "2025-12-01", "2025-12-31", 2, "2", "0"),
            )
            for symbol in ("AAPL", "MSFT"):
                conn.execute(
                    """
                    INSERT INTO position_snapshots
                    (account_id, snapshot_date, symbol, description, asset_class,
                     quantity, mark_price, position_value, average_cost, cost_basis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("U1234567", "2025-12-31", symbol, symbol, "STK", "1", "1", "1", "1", "1"),
                )
    finally:
        store.close()

    monkeypatch.setattr(module, "DEFAULT_DB_PATH", str(db_path))
    FakeTicker.calendars = {
        "AAPL": {"Earnings Date": [date(2026, 1, 20)], "Ex-Dividend Date": None},
        "MSFT": {"Earnings Date": [date(2026, 1, 5)], "Ex-Dividend Date": None},
    }

    with patch("ib_sec_mcp.mcp.tools.earnings_calendar.yf.Ticker", FakeTicker):
        result = await tool_registry["get_earnings_calendar"](
            symbols=None,
            days_ahead=90,
            ctx=None,
        )

    parsed = json.loads(result)

    assert [entry["symbol"] for entry in parsed] == ["MSFT", "AAPL"]