"""Curated macro interest-rate event calendar (issue #152).

yfinance exposes per-symbol corporate calendars (earnings, ex-dividend) but has
no macro feed for central-bank rate decisions. Those decision dates are,
however, published a year or more in advance, so a small **curated, offline
calendar** is the reliable and deterministic data source — no network call, no
flaky third-party endpoint, and trivially testable.

Design decisions (issue #152):

* **Global, not per-symbol.** A rate decision moves all risk assets, not just
  same-currency holdings, so each event is emitted **once** with ``symbol:
  None`` rather than duplicated against every monitored ticker. Consumers that
  want to filter by currency / asset class can do so using the
  ``central_bank`` / ``region`` / ``currency`` metadata carried on each record.
* **Same record shape as corporate events.** Records mirror
  :func:`ib_sec_mcp.mcp.tools.events_monitor.build_symbol_events` output
  (``event_type``, ``event_date``, ``days_until``, ``flag``) so they merge
  cleanly into ``get_upcoming_events`` and ``evaluate_position`` event risk.

Only the FOMC is curated today; the :class:`RateEvent` structure and
:data:`RATE_EVENTS` tuple are intentionally open so other central banks (ECB,
BoE, BoJ) can be appended without touching the builder.

To refresh: replace the dates from the Fed's published schedule at
https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm — use the
**second (announcement) day** of each two-day meeting, when the rate decision
is released.
"""

from __future__ import annotations

from datetime import date
from typing import Any, NamedTuple

# event_type emitted for macro rate-decision events.
RATE_EVENT_TYPE = "rate"

# Proximity flag for imminent events. Mirrors
# ``events_monitor.EVENT_SOON_FLAG``; duplicated here (rather than imported) to
# keep this module a dependency-free leaf and avoid an import cycle, since
# ``events_monitor`` imports *from* this module.
EVENT_SOON_FLAG = "EVENT_SOON"


class RateEvent(NamedTuple):
    """A single scheduled central-bank rate decision.

    Attributes:
        event_date: Announcement (decision) date — the second day of an FOMC
            meeting.
        central_bank: Short issuer label, e.g. ``"FOMC"``.
        region: Geographic region, e.g. ``"US"``.
        currency: ISO currency code primarily affected, e.g. ``"USD"``.
        description: Human-readable event label for notes / alerts.
    """

    event_date: date
    central_bank: str
    region: str
    currency: str
    description: str


def _fomc(event_date: date) -> RateEvent:
    """Build an FOMC rate-decision event for ``event_date``."""
    return RateEvent(
        event_date=event_date,
        central_bank="FOMC",
        region="US",
        currency="USD",
        description="FOMC interest rate decision",
    )


# FOMC rate-decision dates (announcement / second day of each two-day meeting).
# Source: federalreserve.gov FOMC calendars. Keep sorted ascending.
RATE_EVENTS: tuple[RateEvent, ...] = (
    # 2025
    _fomc(date(2025, 1, 29)),
    _fomc(date(2025, 3, 19)),
    _fomc(date(2025, 5, 7)),
    _fomc(date(2025, 6, 18)),
    _fomc(date(2025, 7, 30)),
    _fomc(date(2025, 9, 17)),
    _fomc(date(2025, 10, 29)),
    _fomc(date(2025, 12, 10)),
    # 2026
    _fomc(date(2026, 1, 28)),
    _fomc(date(2026, 3, 18)),
    _fomc(date(2026, 4, 29)),
    _fomc(date(2026, 6, 17)),
    _fomc(date(2026, 7, 29)),
    _fomc(date(2026, 9, 16)),
    _fomc(date(2026, 10, 28)),
    _fomc(date(2026, 12, 9)),
    # 2027
    _fomc(date(2027, 1, 27)),
    _fomc(date(2027, 3, 17)),
    _fomc(date(2027, 4, 28)),
    _fomc(date(2027, 6, 9)),
    _fomc(date(2027, 7, 28)),
    _fomc(date(2027, 9, 15)),
    _fomc(date(2027, 10, 27)),
    _fomc(date(2027, 12, 8)),
)


def build_rate_events(
    current_date: date,
    days_ahead: int,
    soon_threshold_days: int,
    calendar: tuple[RateEvent, ...] = RATE_EVENTS,
) -> list[dict[str, Any]]:
    """Build global rate-event records falling within the monitoring horizon.

    Pure transformation over the curated :data:`RATE_EVENTS` calendar. Only
    events in ``[current_date, current_date + days_ahead]`` are returned, each
    as a *global* record (``symbol: None``) so it is reported once rather than
    per held symbol.

    Args:
        current_date: Reference "today".
        days_ahead: Inclusive monitoring horizon in days.
        soon_threshold_days: Events within this many days are flagged
            ``EVENT_SOON``.
        calendar: Curated event source (overridable for testing).

    Returns:
        List of rate-event records sorted soonest-first. Each record has
        ``symbol`` (``None``), ``event_type`` (``"rate"``), ``event_date``
        (ISO string), ``days_until``, ``flag`` (``"EVENT_SOON"`` or ``None``),
        and macro metadata (``central_bank``, ``region``, ``currency``,
        ``description``).
    """
    records: list[dict[str, Any]] = []
    for event in calendar:
        days_until = (event.event_date - current_date).days
        if not 0 <= days_until <= days_ahead:
            continue
        records.append(
            {
                "symbol": None,
                "event_type": RATE_EVENT_TYPE,
                "event_date": event.event_date.isoformat(),
                "days_until": days_until,
                "flag": EVENT_SOON_FLAG if days_until <= soon_threshold_days else None,
                "central_bank": event.central_bank,
                "region": event.region,
                "currency": event.currency,
                "description": event.description,
            }
        )
    records.sort(key=lambda record: record["days_until"])
    return records
