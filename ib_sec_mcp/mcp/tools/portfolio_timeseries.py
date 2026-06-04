"""Portfolio time-series MCP tools.

Computes time-weighted return (TWR), cumulative return, and drawdown for a
portfolio from stored daily snapshots, and tracks performance relative to a
market benchmark fetched from Yahoo Finance.

External cash-flow policy
-------------------------
TWR is derived from the portfolio NAV series alone and assumes **no external
cash flows** (deposits/withdrawals) between snapshots. See
``ib_sec_mcp.analyzers.timeseries`` for the full rationale; the limitation is
surfaced in the tool response under ``methodology``.
"""

import asyncio
import json
from datetime import date
from decimal import Decimal
from typing import Any

from fastmcp import Context, FastMCP

from ib_sec_mcp.analyzers.timeseries import (
    align_benchmark_index,
    cumulative_index,
    cumulative_twr,
    max_drawdown,
    simple_returns,
)
from ib_sec_mcp.mcp.exceptions import ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.validators import validate_benchmark_symbol
from ib_sec_mcp.storage import PositionStore

# Timeout for benchmark price fetch (seconds)
DEFAULT_TIMEOUT = 30


def _to_pct(value: Decimal) -> str:
    """Format a fractional return as a percentage string (e.g. ``"10.50%"``)."""
    return f"{value * Decimal('100'):.2f}%"


async def _fetch_benchmark_closes(
    benchmark: str, start: date, end: date
) -> list[tuple[str, Decimal]]:
    """Fetch benchmark daily closes over ``[start, end]`` from Yahoo Finance.

    Returns a list of ``(iso_date, close)`` tuples ordered by date. The end date
    is made inclusive by extending the yfinance ``end`` bound by one day.

    Raises:
        YahooFinanceError: If no data is returned for the benchmark/range.
    """
    import yfinance as yf

    # yfinance treats ``end`` as exclusive; extend by a day to include it.
    end_exclusive = date.fromordinal(end.toordinal() + 1)

    def _history() -> Any:
        return yf.Ticker(benchmark).history(start=start.isoformat(), end=end_exclusive.isoformat())

    data = await asyncio.wait_for(asyncio.to_thread(_history), timeout=DEFAULT_TIMEOUT)

    if data is None or data.empty or "Close" not in data.columns:
        raise YahooFinanceError(
            f"No benchmark data found for {benchmark} between {start} and {end}"
        )

    closes: list[tuple[str, Decimal]] = []
    # Drop NaN closes (holidays/missing data); Decimal("NaN") would later raise
    # InvalidOperation in fixed-point formatting and break benchmark tracking.
    for ts, close in data["Close"].dropna().items():
        iso = ts.date().isoformat() if hasattr(ts, "date") else str(ts)[:10]
        closes.append((iso, Decimal(str(close))))
    return closes


def register_portfolio_timeseries_tools(mcp: FastMCP) -> None:
    """Register portfolio time-series tools."""

    @mcp.tool
    async def get_portfolio_timeseries(
        account_id: str,
        start_date: str,
        end_date: str,
        benchmark: str = "SPY",
        db_path: str = "data/processed/positions.db",
        ctx: Context | None = None,
    ) -> str:
        """
        Compute portfolio time-series performance and benchmark-relative tracking.

        Builds a Net Asset Value (NAV) series from stored daily snapshots and
        derives a time-weighted return (TWR), a cumulative growth index, period
        returns, and maximum drawdown — all with Decimal precision. The same
        window is compared against a market benchmark (Yahoo Finance) so the
        relative (excess) return is reported.

        External cash-flow policy: TWR assumes no external deposits/withdrawals
        occur between snapshots (NAV changes are attributed to market moves).
        See ``methodology`` in the response.

        Args:
            account_id: Account ID (e.g., "U1234567")
            start_date: Start date in YYYY-MM-DD format (inclusive)
            end_date: End date in YYYY-MM-DD format (inclusive)
            benchmark: Benchmark ticker for relative tracking (default: "SPY")
            db_path: Path to SQLite database (default: data/processed/positions.db)
            ctx: MCP context for logging

        Returns:
            JSON string with the portfolio time-series, benchmark series, and
            relative performance summary.

        Example:
            >>> series = await get_portfolio_timeseries(
            ...     account_id="U1234567",
            ...     start_date="2025-01-01",
            ...     end_date="2025-10-15",
            ...     benchmark="SPY",
            ... )
        """
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}") from e

        if start > end:
            raise ValidationError(
                f"start_date ({start_date}) must not be after end_date ({end_date})"
            )

        benchmark = validate_benchmark_symbol(benchmark)

        if ctx:
            await ctx.info(
                f"Computing portfolio time-series for {account_id} "
                f"from {start_date} to {end_date} vs {benchmark}"
            )

        # Load NAV series from snapshots.
        store = PositionStore(db_path)
        try:
            series = store.get_value_series(account_id, start, end)
        finally:
            store.close()

        if len(series) < 2:
            return json.dumps(
                {
                    "account_id": account_id,
                    "date_range": {"from": start_date, "to": end_date},
                    "benchmark": benchmark,
                    "snapshot_count": len(series),
                    "message": (
                        "At least two snapshots in the date range are required to "
                        "compute time-series performance."
                    ),
                },
                indent=2,
                default=str,
            )

        dates = [row["snapshot_date"] for row in series]
        navs = [row["nav"] for row in series]

        returns = simple_returns(navs)
        port_index = cumulative_index(returns)
        port_twr = cumulative_twr(returns)
        port_drawdown = max_drawdown(port_index)

        portfolio_points = [
            {
                "date": dates[i],
                "nav": navs[i],
                "period_return": returns[i - 1] if i > 0 else Decimal("0"),
                "cumulative_return": port_index[i] - Decimal("1"),
            }
            for i in range(len(dates))
        ]

        # Benchmark-relative tracking (best-effort; degrade gracefully).
        benchmark_block: dict[str, Any]
        relative_block: dict[str, Any] | None = None
        try:
            # Align the benchmark window to the actual snapshot range so the
            # portfolio TWR (computed over available snapshots) and benchmark TWR
            # cover the same period — comparing over the full requested range
            # would skew the excess return when snapshots span a narrower window.
            actual_start = date.fromisoformat(dates[0])
            actual_end = date.fromisoformat(dates[-1])
            closes = await _fetch_benchmark_closes(benchmark, actual_start, actual_end)
            if len(closes) < 2:
                raise YahooFinanceError(f"Insufficient benchmark data for {benchmark} in range")
            bench_dates = [c[0] for c in closes]
            bench_closes = [c[1] for c in closes]
            bench_index = align_benchmark_index(bench_closes)
            bench_twr = bench_index[-1] - Decimal("1")
            bench_drawdown = max_drawdown(bench_index)

            benchmark_block = {
                "symbol": benchmark,
                "observation_count": len(closes),
                "twr": bench_twr,
                "twr_pct": _to_pct(bench_twr),
                "max_drawdown": bench_drawdown,
                "max_drawdown_pct": _to_pct(bench_drawdown),
                "series": [
                    {
                        "date": bench_dates[i],
                        "close": bench_closes[i],
                        "cumulative_return": bench_index[i] - Decimal("1"),
                    }
                    for i in range(len(closes))
                ],
            }
            excess = port_twr - bench_twr
            relative_block = {
                "excess_return": excess,
                "excess_return_pct": _to_pct(excess),
                "outperformed": excess > Decimal("0"),
            }
        except Exception as e:
            # Benchmark tracking is best-effort: any fetch/parse failure degrades
            # to portfolio-only metrics rather than failing the whole tool.
            if ctx:
                await ctx.warning(f"Benchmark data unavailable: {e!s}")
            benchmark_block = {
                "symbol": benchmark,
                "error": "Benchmark data unavailable; portfolio metrics still returned.",
            }

        result: dict[str, Any] = {
            "account_id": account_id,
            "date_range": {"from": start_date, "to": end_date},
            "snapshot_count": len(series),
            "portfolio": {
                "twr": port_twr,
                "twr_pct": _to_pct(port_twr),
                "max_drawdown": port_drawdown,
                "max_drawdown_pct": _to_pct(port_drawdown),
                "start_nav": navs[0],
                "end_nav": navs[-1],
                "series": portfolio_points,
            },
            "benchmark": benchmark_block,
            "relative_performance": relative_block,
            "methodology": {
                "return_type": "time-weighted (geometrically chained sub-period returns)",
                "nav_definition": "total_value from snapshot (cash + position value)",
                "external_cash_flows": (
                    "Assumed none between snapshots; deposits/withdrawals are not "
                    "adjusted and would bias TWR."
                ),
            },
        }

        return json.dumps(result, indent=2, default=str)


__all__ = ["register_portfolio_timeseries_tools"]
