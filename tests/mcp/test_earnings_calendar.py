"""Tests for earnings calendar MCP tools.

These tests register the tool on a real :class:`fastmcp.FastMCP` instance and
invoke it through the FastMCP tool API so that the production code path is
exercised (and recorded by coverage). All yfinance access is mocked, so the
suite is network-independent.
"""

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.tools.earnings_calendar import register_earnings_calendar_tools
from ib_sec_mcp.storage import PositionStore
from tests.mcp._fastmcp_helpers import call_tool_fn

PATCH_TARGET = "ib_sec_mcp.mcp.tools.earnings_calendar.yf.Ticker"


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


class FakeDataFrameCalendar:
    """Minimal DataFrame-like object exposing a ``.loc`` accessor."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def loc(self) -> "FakeDataFrameCalendar":
        return self

    def __getitem__(self, key: str) -> Any:
        if key not in self._data:
            raise KeyError(key)
        return _Cell(self._data[key])


class _Cell:
    """Wrap a value so it mimics a single-element pandas Series via ``tolist``."""

    def __init__(self, value: Any) -> None:
        self._value = value

    def tolist(self) -> list[Any]:
        return [self._value]


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with the earnings calendar tool registered."""
    mcp = FastMCP("test")
    register_earnings_calendar_tools(mcp)
    return mcp


@pytest.fixture()
def patch_ticker(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, Any]], None]:
    """Return a helper that installs FakeTicker with the given calendar data.

    Uses ``monkeypatch.setattr`` so both the patched ``yf.Ticker`` and the
    per-symbol calendar payload are restored automatically after each test,
    preventing cross-test state pollution.
    """

    def _apply(calendars: dict[str, Any]) -> None:
        monkeypatch.setattr(FakeTicker, "calendars", calendars)
        monkeypatch.setattr(PATCH_TARGET, FakeTicker)

    return _apply


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make days-until calculations deterministic and ignore env account IDs."""
    import ib_sec_mcp.mcp.tools.earnings_calendar as module

    monkeypatch.setattr(module, "_today", lambda: date(2026, 1, 1))
    for env_var in module.ACCOUNT_ID_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


@pytest.mark.asyncio
async def test_get_earnings_calendar_returns_sorted_events(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Multiple symbol results are returned in upcoming event order."""
    patch_ticker(
        {
            "AAPL": {
                "Earnings Date": [date(2026, 1, 20)],
                "Ex-Dividend Date": date(2026, 1, 10),
            },
            "MSFT": {
                "Earnings Date": [date(2026, 1, 5)],
                "Ex-Dividend Date": date(2026, 3, 1),
            },
        }
    )

    result = await call_tool_fn(
        test_mcp,
        "get_earnings_calendar",
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
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """A yfinance failure for one symbol is included without stopping processing."""
    patch_ticker(
        {
            "AAPL": {
                "Earnings Date": [date(2026, 1, 20)],
                "Ex-Dividend Date": None,
            },
            "BROKEN": RuntimeError("symbol not supported"),
        }
    )

    result = await call_tool_fn(
        test_mcp,
        "get_earnings_calendar",
        symbols=["AAPL", "BROKEN"],
        days_ahead=90,
        ctx=None,
    )
    parsed = json.loads(result)

    assert parsed[0]["symbol"] == "AAPL"
    assert parsed[1] == {"symbol": "BROKEN", "error": "symbol not supported"}


@pytest.mark.asyncio
async def test_get_earnings_calendar_filters_events_outside_days_ahead(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Events beyond the requested horizon are omitted."""
    patch_ticker(
        {
            "AAPL": {
                "Earnings Date": [date(2026, 6, 1)],
                "Ex-Dividend Date": date(2026, 7, 1),
            },
        }
    )

    result = await call_tool_fn(
        test_mcp,
        "get_earnings_calendar",
        symbols=["AAPL"],
        days_ahead=30,
        ctx=None,
    )

    assert json.loads(result) == []


@pytest.mark.asyncio
async def test_get_earnings_calendar_reports_missing_dates(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """A calendar with no upcoming dates yields a per-symbol error entry."""
    patch_ticker({"AAPL": {"Earnings Date": None, "Ex-Dividend Date": None}})

    result = await call_tool_fn(
        test_mcp,
        "get_earnings_calendar",
        symbols=["AAPL"],
        days_ahead=90,
        ctx=None,
    )
    parsed = json.loads(result)

    assert parsed == [{"symbol": "AAPL", "error": "No earnings or ex-dividend date found"}]


@pytest.mark.asyncio
async def test_get_earnings_calendar_rejects_negative_days_ahead(test_mcp: FastMCP) -> None:
    """A negative horizon is rejected before any yfinance access."""
    result = await call_tool_fn(
        test_mcp,
        "get_earnings_calendar",
        symbols=["AAPL"],
        days_ahead=-1,
        ctx=None,
    )

    assert json.loads(result) == [{"error": "days_ahead must be zero or greater"}]


@pytest.mark.asyncio
async def test_get_earnings_calendar_reports_invalid_symbols(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """Invalid symbols become error entries while valid ones are still processed."""
    patch_ticker({"AAPL": {"Earnings Date": [date(2026, 1, 20)], "Ex-Dividend Date": None}})

    result = await call_tool_fn(
        test_mcp,
        "get_earnings_calendar",
        symbols=["AAPL", "!!bad!!"],
        days_ahead=90,
        ctx=None,
    )
    parsed = json.loads(result)
    by_symbol = {entry["symbol"]: entry for entry in parsed}

    assert by_symbol["AAPL"]["next_earnings_date"] == "2026-01-20"
    assert "error" in by_symbol["!!bad!!"]


@pytest.mark.asyncio
async def test_get_earnings_calendar_handles_dataframe_calendar(
    test_mcp: FastMCP, patch_ticker: Callable[[dict[str, Any]], None]
) -> None:
    """DataFrame-like calendars (``.loc`` accessor) and string dates are parsed."""
    patch_ticker(
        {
            "AAPL": FakeDataFrameCalendar(
                {
                    "Earnings Date": "2026-01-15",
                    "Ex-Dividend Date": "2026-01-08",
                }
            ),
        }
    )

    result = await call_tool_fn(
        test_mcp,
        "get_earnings_calendar",
        symbols=["AAPL"],
        days_ahead=90,
        ctx=None,
    )
    parsed = json.loads(result)

    assert parsed[0]["next_earnings_date"] == "2026-01-15"
    assert parsed[0]["ex_dividend_date"] == "2026-01-08"


@pytest.mark.asyncio
async def test_get_earnings_calendar_loads_symbols_from_latest_snapshot(
    test_mcp: FastMCP,
    patch_ticker: Callable[[dict[str, Any]], None],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When symbols are omitted, the latest PositionStore snapshot supplies symbols."""
    import ib_sec_mcp.mcp.tools.earnings_calendar as module

    db_path = tmp_path / "positions.db"
    with PositionStore(db_path) as store, store.db.transaction() as conn:
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

    monkeypatch.setattr(module, "DEFAULT_DB_PATH", str(db_path))
    patch_ticker(
        {
            "AAPL": {"Earnings Date": [date(2026, 1, 20)], "Ex-Dividend Date": None},
            "MSFT": {"Earnings Date": [date(2026, 1, 5)], "Ex-Dividend Date": None},
        }
    )

    result = await call_tool_fn(
        test_mcp,
        "get_earnings_calendar",
        symbols=None,
        days_ahead=90,
        ctx=None,
    )
    parsed = json.loads(result)

    assert [entry["symbol"] for entry in parsed] == ["MSFT", "AAPL"]
