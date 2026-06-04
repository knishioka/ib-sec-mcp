"""Upcoming event monitoring MCP tools.

Aggregates near-term corporate events — earnings and ex-dividend dates (and,
best-effort, interest-rate events) — for portfolio holdings plus an optional
watchlist, flagging events that are imminent (``EVENT_SOON``).

This complements ``get_earnings_calendar`` (single-shot lookup) by turning the
same yfinance-backed calendar data into a monitoring feed: a flat, sorted list
of events with proximity flags suitable for ``/daily-check`` alerts and for
feeding near-term event risk into position decisions (``evaluate_position``).

The parsing/normalisation helpers are reused from
:mod:`ib_sec_mcp.mcp.tools.earnings_calendar` so the two tools agree on how
yfinance calendar payloads are interpreted.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from datetime import date
from typing import Any

import yfinance as yf
from fastmcp import Context, FastMCP

from ib_sec_mcp.mcp.tools.earnings_calendar import (
    FETCH_CONCURRENCY_LIMIT,
    _days_until,
    _extract_calendar_value,
    _first_upcoming_date,
    _load_symbols_from_latest_snapshot,
    _normalize_symbols,
)

# Default proximity threshold: events within this many days are flagged EVENT_SOON.
EVENT_SOON_THRESHOLD_DAYS = 3

# Default monitoring horizon (issue #131: get_upcoming_events(days=14)).
DEFAULT_DAYS_AHEAD = 14

# Event types sourced from the yfinance calendar (key -> normalized event_type).
_CALENDAR_EVENT_TYPES: tuple[tuple[str, str], ...] = (
    ("Earnings Date", "earnings"),
    ("Ex-Dividend Date", "ex_dividend"),
)

# Proximity flag emitted for imminent events.
EVENT_SOON_FLAG = "EVENT_SOON"


def _today() -> date:
    """Return today's date (indirection so tests can freeze the clock)."""
    return date.today()


def build_symbol_events(
    symbol: str,
    calendar: Any,
    current_date: date,
    days_ahead: int,
    soon_threshold_days: int,
) -> list[dict[str, Any]]:
    """Build the list of upcoming event records for a single symbol.

    Pure transformation over an already-fetched yfinance ``calendar`` payload.
    Only events that fall within ``[today, today + days_ahead]`` are returned.

    Args:
        symbol: Normalized ticker symbol.
        calendar: yfinance ``Ticker.calendar`` payload (dict or DataFrame-like).
        current_date: Reference "today".
        days_ahead: Inclusive monitoring horizon in days.
        soon_threshold_days: Events within this many days are flagged EVENT_SOON.

    Returns:
        List of event records, each with ``symbol``, ``event_type``,
        ``event_date`` (ISO string), ``days_until`` and ``flag``
        (``"EVENT_SOON"`` or ``None``).
    """
    records: list[dict[str, Any]] = []
    for calendar_key, event_type in _CALENDAR_EVENT_TYPES:
        event_date = _first_upcoming_date(
            _extract_calendar_value(calendar, calendar_key),
            current_date,
        )
        days_until = _days_until(event_date, current_date, days_ahead)
        if days_until is None or event_date is None:
            continue
        records.append(
            {
                "symbol": symbol,
                "event_type": event_type,
                "event_date": event_date.isoformat(),
                "days_until": days_until,
                "flag": EVENT_SOON_FLAG if days_until <= soon_threshold_days else None,
            }
        )
    return records


def _collect_symbols(
    symbols: Iterable[str] | None,
    watchlist: Iterable[str] | None,
) -> tuple[list[str], list[dict[str, str]]]:
    """Resolve the monitored symbol set (holdings + watchlist) and validate it.

    When ``symbols`` is ``None`` the portfolio holdings from the latest snapshot
    are used as the base set. ``watchlist`` symbols are always merged in.
    Duplicates are removed while preserving first-seen order.
    """
    base = list(symbols) if symbols is not None else _load_symbols_from_latest_snapshot()
    if watchlist:
        base = [*base, *watchlist]
    return _normalize_symbols(base)


async def _fetch_symbol_events(
    symbol: str,
    current_date: date,
    days_ahead: int,
    soon_threshold_days: int,
    semaphore: asyncio.Semaphore,
) -> list[dict[str, Any]]:
    """Fetch and normalize upcoming events for one symbol (concurrency-limited).

    A yfinance failure is returned as a single error record rather than raising,
    so one bad symbol never aborts the whole sweep.
    """
    async with semaphore:
        try:
            calendar = await asyncio.to_thread(lambda: yf.Ticker(symbol).calendar)
            return build_symbol_events(
                symbol, calendar, current_date, days_ahead, soon_threshold_days
            )
        except Exception as exc:
            return [{"symbol": symbol, "error": str(exc)}]


def _sort_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort events by soonest first, then symbol, keeping errors last."""

    def sort_key(event: dict[str, Any]) -> tuple[int, int, str]:
        if "error" in event:
            return (1, 999_999, str(event.get("symbol", "")))
        days_until = event.get("days_until")
        days = days_until if isinstance(days_until, int) else 999_999
        return (0, days, str(event.get("symbol", "")))

    return sorted(events, key=sort_key)


def register_events_monitor_tools(mcp: FastMCP) -> None:
    """Register the upcoming-events monitoring tool."""

    @mcp.tool
    async def get_upcoming_events(
        days: int = DEFAULT_DAYS_AHEAD,
        symbols: list[str] | None = None,
        watchlist: list[str] | None = None,
        soon_threshold_days: int = EVENT_SOON_THRESHOLD_DAYS,
        ctx: Context | None = None,
    ) -> str:
        """
        Monitor upcoming earnings / ex-dividend events for holdings + watchlist.

        Aggregates near-term corporate events across portfolio holdings and an
        optional watchlist, flagging imminent ones (``EVENT_SOON``) so staged
        entry / exit decisions and ``/daily-check`` can react before the event.

        Args:
            days: Monitoring horizon in days (default: 14). Events further out
                than this are omitted.
            symbols: Base symbols to monitor. When omitted, holdings from the
                latest portfolio snapshot are used.
            watchlist: Additional non-held symbols to monitor alongside holdings.
            soon_threshold_days: Events within this many days are flagged
                ``EVENT_SOON`` (default: 3).
            ctx: MCP context for logging.

        Returns:
            JSON string with ``as_of``, ``days_ahead``, ``soon_threshold_days``,
            ``event_count``, ``event_soon_count``, ``events`` (flat, soonest
            first) and ``errors``. Each event has ``symbol``, ``event_type``
            (``"earnings"`` | ``"ex_dividend"``), ``event_date``, ``days_until``
            and ``flag``.

        Note:
            Interest-rate (macro) events are not yet sourced per-symbol; the
            ``event_type`` field is intentionally open for a future rate feed.
        """
        if days < 0:
            return json.dumps({"error": "days must be zero or greater"}, indent=2)
        if soon_threshold_days < 0:
            return json.dumps({"error": "soon_threshold_days must be zero or greater"}, indent=2)

        normalized_symbols, validation_errors = _collect_symbols(symbols, watchlist)

        if ctx:
            await ctx.info(
                f"Monitoring upcoming events for {len(normalized_symbols)} symbol(s)",
                extra={"days_ahead": days, "soon_threshold_days": soon_threshold_days},
            )

        current_date = _today()
        semaphore = asyncio.Semaphore(FETCH_CONCURRENCY_LIMIT)
        fetched = await asyncio.gather(
            *(
                _fetch_symbol_events(symbol, current_date, days, soon_threshold_days, semaphore)
                for symbol in normalized_symbols
            )
        )

        events: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = list(validation_errors)
        for records in fetched:
            for record in records:
                if "error" in record:
                    errors.append(record)
                else:
                    events.append(record)

        sorted_events = _sort_events(events)
        event_soon_count = sum(1 for event in sorted_events if event.get("flag") == EVENT_SOON_FLAG)

        if ctx:
            await ctx.info(
                f"Found {len(sorted_events)} upcoming event(s), "
                f"{event_soon_count} flagged {EVENT_SOON_FLAG}"
            )

        return json.dumps(
            {
                "as_of": current_date.isoformat(),
                "days_ahead": days,
                "soon_threshold_days": soon_threshold_days,
                "event_count": len(sorted_events),
                "event_soon_count": event_soon_count,
                "events": sorted_events,
                "errors": errors,
            },
            indent=2,
            default=str,
        )
