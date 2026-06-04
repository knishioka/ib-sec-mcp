"""Tests for the curated macro interest-rate event calendar."""

from datetime import date

from ib_sec_mcp.mcp.tools.rate_calendar import (
    RATE_EVENTS,
    RateEvent,
    build_rate_events,
)

# A small, deterministic calendar used for horizon/flag assertions.
SAMPLE_CALENDAR: tuple[RateEvent, ...] = (
    RateEvent(date(2026, 1, 3), "FOMC", "US", "USD", "FOMC interest rate decision"),
    RateEvent(date(2026, 1, 10), "FOMC", "US", "USD", "FOMC interest rate decision"),
    RateEvent(date(2026, 2, 1), "FOMC", "US", "USD", "FOMC interest rate decision"),
)


def test_build_rate_events_flags_and_filters() -> None:
    """Imminent events are flagged EVENT_SOON; out-of-horizon events dropped."""
    records = build_rate_events(date(2026, 1, 1), 14, 3, calendar=SAMPLE_CALENDAR)

    # 2026-02-01 (31 days) is beyond the 14-day horizon and excluded.
    assert [r["event_date"] for r in records] == ["2026-01-03", "2026-01-10"]

    by_date = {r["event_date"]: r for r in records}
    assert by_date["2026-01-03"]["days_until"] == 2
    assert by_date["2026-01-03"]["flag"] == "EVENT_SOON"  # within 3 days
    assert by_date["2026-01-10"]["days_until"] == 9
    assert by_date["2026-01-10"]["flag"] is None


def test_build_rate_events_are_global_with_metadata() -> None:
    """Rate events carry symbol=None plus macro metadata."""
    records = build_rate_events(date(2026, 1, 1), 14, 3, calendar=SAMPLE_CALENDAR)

    record = records[0]
    assert record["symbol"] is None
    assert record["event_type"] == "rate"
    assert record["central_bank"] == "FOMC"
    assert record["region"] == "US"
    assert record["currency"] == "USD"
    assert record["description"] == "FOMC interest rate decision"


def test_build_rate_events_sorted_soonest_first() -> None:
    """Records are returned sorted by days_until ascending."""
    unsorted_calendar = (SAMPLE_CALENDAR[1], SAMPLE_CALENDAR[0])
    records = build_rate_events(date(2026, 1, 1), 14, 3, calendar=unsorted_calendar)
    assert [r["days_until"] for r in records] == [2, 9]


def test_build_rate_events_empty_when_none_in_window() -> None:
    """No events within the horizon yields an empty list (not an error)."""
    assert build_rate_events(date(2026, 1, 1), 1, 3, calendar=SAMPLE_CALENDAR) == []


def test_build_rate_events_includes_today() -> None:
    """An event landing exactly today is in-horizon and flagged EVENT_SOON."""
    calendar = (RateEvent(date(2026, 1, 1), "FOMC", "US", "USD", "FOMC interest rate decision"),)
    records = build_rate_events(date(2026, 1, 1), 14, 3, calendar=calendar)
    assert records[0]["days_until"] == 0
    assert records[0]["flag"] == "EVENT_SOON"


def test_curated_fomc_calendar_is_sorted_and_well_formed() -> None:
    """The shipped FOMC calendar is ascending and uses the rate schema."""
    dates = [event.event_date for event in RATE_EVENTS]
    assert dates == sorted(dates)
    assert all(event.central_bank == "FOMC" for event in RATE_EVENTS)
    assert all(event.currency == "USD" for event in RATE_EVENTS)
