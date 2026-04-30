"""Earnings and dividend calendar MCP tools."""

import asyncio
import json
import os
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from typing import Any

import yfinance as yf
from fastmcp import Context, FastMCP

from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.mcp.validators import validate_symbol
from ib_sec_mcp.storage import PositionStore

DEFAULT_DB_PATH = "data/processed/positions.db"
ACCOUNT_ID_ENV_VARS = ("IB_ACCOUNT_ID", "ACCOUNT_ID", "IBKR_ACCOUNT_ID")
FETCH_CONCURRENCY_LIMIT = 8


def _today() -> date:
    """Return today's date."""
    return date.today()


def _get_configured_account_id() -> str | None:
    """Return an account ID configured through environment variables."""
    for env_var in ACCOUNT_ID_ENV_VARS:
        value = os.getenv(env_var)
        if value:
            return value.strip()
    return None


def _get_account_ids_from_store(store: PositionStore) -> list[str]:
    """Return account IDs ordered by their most recent snapshot date."""
    configured_account_id = _get_configured_account_id()
    if configured_account_id:
        return [configured_account_id]

    rows = store.db.fetchall(
        """
        SELECT account_id
        FROM snapshot_metadata
        GROUP BY account_id
        ORDER BY MAX(snapshot_date) DESC
        """
    )
    return [str(row["account_id"]) for row in rows if row.get("account_id")]


def _load_symbols_from_latest_snapshot(db_path: str | None = None) -> list[str]:
    """Load distinct symbols from the latest available portfolio snapshot."""
    store = PositionStore(db_path or DEFAULT_DB_PATH)
    try:
        symbols: list[str] = []
        seen: set[str] = set()

        for account_id in _get_account_ids_from_store(store):
            available_dates = store.get_available_dates(account_id)
            if not available_dates:
                continue

            snapshot_date = date.fromisoformat(available_dates[0])
            positions = store.get_portfolio_snapshot(account_id, snapshot_date)
            for position in positions:
                symbol = str(position.get("symbol", "")).strip().upper()
                if symbol and symbol not in seen:
                    seen.add(symbol)
                    symbols.append(symbol)

        return symbols
    finally:
        store.close()


def _normalize_symbols(symbols: Iterable[str]) -> tuple[list[str], list[dict[str, str]]]:
    """Normalize symbols and return validation errors without raising."""
    normalized: list[str] = []
    errors: list[dict[str, str]] = []
    seen: set[str] = set()

    for raw_symbol in symbols:
        try:
            symbol = validate_symbol(raw_symbol)
        except ValidationError as exc:
            errors.append({"symbol": str(raw_symbol), "error": str(exc)})
            continue

        if symbol not in seen:
            seen.add(symbol)
            normalized.append(symbol)

    return normalized, errors


def _extract_calendar_value(calendar: Any, key: str) -> Any:
    """Extract a calendar field from yfinance's dict or DataFrame-like shapes."""
    if isinstance(calendar, Mapping):
        return calendar.get(key)

    if hasattr(calendar, "loc"):
        try:
            value = calendar.loc[key]
        except (KeyError, IndexError, TypeError, AttributeError):
            return None

        if hasattr(value, "tolist"):
            values = value.tolist()
            if isinstance(values, list) and len(values) == 1:
                return values[0]
            return values
        return value

    return None


def _coerce_to_date(value: Any) -> date | None:
    """Convert yfinance calendar values to date objects when possible."""
    if value is None:
        return None

    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        clean_value = value.strip()
        if not clean_value:
            return None
        try:
            return datetime.fromisoformat(clean_value.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(clean_value[:10])
            except ValueError:
                return None

    return None


def _flatten_calendar_values(value: Any) -> list[Any]:
    """Flatten scalar and sequence calendar values into a simple list."""
    if value is None:
        return []

    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        flattened: list[Any] = []
        for item in value:
            flattened.extend(_flatten_calendar_values(item))
        return flattened

    return [value]


def _first_upcoming_date(value: Any, current_date: date) -> date | None:
    """Return the first calendar date that is today or in the future."""
    dates = [
        parsed_date
        for parsed_date in (_coerce_to_date(item) for item in _flatten_calendar_values(value))
        if parsed_date and parsed_date >= current_date
    ]
    if not dates:
        return None
    return min(dates)


def _days_until(event_date: date | None, current_date: date, days_ahead: int) -> int | None:
    """Return days until an event when it falls within the requested horizon."""
    if event_date is None:
        return None

    days = (event_date - current_date).days
    if 0 <= days <= days_ahead:
        return days
    return None


def _build_calendar_entry(
    symbol: str,
    calendar: Any,
    current_date: date,
    days_ahead: int,
) -> dict[str, Any] | None:
    """Build one normalized calendar entry from yfinance calendar data."""
    earnings_date = _first_upcoming_date(
        _extract_calendar_value(calendar, "Earnings Date"),
        current_date,
    )
    ex_dividend_date = _first_upcoming_date(
        _extract_calendar_value(calendar, "Ex-Dividend Date"),
        current_date,
    )

    if earnings_date is None and ex_dividend_date is None:
        return {"symbol": symbol, "error": "No earnings or ex-dividend date found"}

    days_until_earnings = _days_until(earnings_date, current_date, days_ahead)
    days_until_ex_dividend = _days_until(ex_dividend_date, current_date, days_ahead)

    if days_until_earnings is None and days_until_ex_dividend is None:
        return None

    next_earnings_date = (
        earnings_date.isoformat()
        if earnings_date is not None and days_until_earnings is not None
        else None
    )
    ex_dividend_date_iso = (
        ex_dividend_date.isoformat()
        if ex_dividend_date is not None and days_until_ex_dividend is not None
        else None
    )

    return {
        "symbol": symbol,
        "next_earnings_date": next_earnings_date,
        "days_until_earnings": days_until_earnings,
        "ex_dividend_date": ex_dividend_date_iso,
        "days_until_ex_dividend": days_until_ex_dividend,
    }


def _sort_calendar_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort calendar entries by upcoming earnings date, then dividend date."""

    def sort_key(entry: dict[str, Any]) -> tuple[int, int, str]:
        if "error" in entry:
            return (1, 999_999, str(entry.get("symbol", "")))

        days_until_earnings = entry.get("days_until_earnings")
        if isinstance(days_until_earnings, int):
            return (0, days_until_earnings, str(entry.get("symbol", "")))

        days_until_ex_dividend = entry.get("days_until_ex_dividend")
        if isinstance(days_until_ex_dividend, int):
            return (0, days_until_ex_dividend, str(entry.get("symbol", "")))

        return (0, 999_999, str(entry.get("symbol", "")))

    return sorted(entries, key=sort_key)


async def _fetch_calendar_entry(
    symbol: str,
    current_date: date,
    days_ahead: int,
) -> dict[str, Any] | None:
    """Fetch and normalize yfinance calendar data for a single symbol."""
    try:
        calendar = await asyncio.to_thread(lambda: yf.Ticker(symbol).calendar)
        return _build_calendar_entry(symbol, calendar, current_date, days_ahead)
    except Exception as exc:
        return {"symbol": symbol, "error": str(exc)}


async def _fetch_calendar_entry_with_limit(
    symbol: str,
    current_date: date,
    days_ahead: int,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any] | None:
    """Fetch one symbol while limiting concurrent yfinance requests."""
    async with semaphore:
        return await _fetch_calendar_entry(symbol, current_date, days_ahead)


def register_earnings_calendar_tools(mcp: FastMCP) -> None:
    """Register earnings and dividend calendar tools."""

    @mcp.tool
    async def get_earnings_calendar(
        symbols: list[str] | None = None,
        days_ahead: int = 90,
        ctx: Context | None = None,
    ) -> str:
        """
        Get upcoming earnings and ex-dividend dates for portfolio or requested symbols.

        Args:
            symbols: Ticker symbols to inspect. When omitted, symbols are loaded from
                the latest portfolio snapshot in the position store.
            days_ahead: Maximum number of days ahead to include events.
            ctx: MCP context for logging.

        Returns:
            JSON string with entries containing symbol, next_earnings_date,
            days_until_earnings, ex_dividend_date, and days_until_ex_dividend.
            Per-symbol yfinance failures are returned as error entries.
        """
        if days_ahead < 0:
            return json.dumps([{"error": "days_ahead must be zero or greater"}], indent=2)

        source_symbols = symbols if symbols is not None else _load_symbols_from_latest_snapshot()
        normalized_symbols, errors = _normalize_symbols(source_symbols)

        if ctx:
            await ctx.info(
                f"Fetching earnings calendar for {len(normalized_symbols)} symbol(s)",
                extra={"days_ahead": days_ahead},
            )

        current_date = _today()
        semaphore = asyncio.Semaphore(FETCH_CONCURRENCY_LIMIT)
        fetched_entries = await asyncio.gather(
            *(
                _fetch_calendar_entry_with_limit(
                    symbol,
                    current_date,
                    days_ahead,
                    semaphore,
                )
                for symbol in normalized_symbols
            )
        )

        entries = [entry for entry in fetched_entries if entry is not None]
        entries.extend(errors)

        return json.dumps(_sort_calendar_entries(entries), indent=2, default=str)
