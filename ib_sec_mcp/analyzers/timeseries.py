"""Portfolio time-series performance math (Decimal-precise).

Pure, side-effect-free helpers for turning a portfolio Net Asset Value (NAV)
series into time-weighted return (TWR), a cumulative growth index, period
returns, and maximum drawdown. All money math uses :class:`~decimal.Decimal`.

External cash-flow policy
-------------------------
These helpers operate on a NAV series alone and **assume no external cash
flows** (deposits/withdrawals) occur between consecutive observations. Each
sub-period return is computed as ``(V_end - V_begin) / V_begin`` and the
sub-period returns are geometrically chained ("time-weighted").

Because daily position snapshots do not record external contributions or
withdrawals, a deposit between two snapshots would inflate the measured return
and a withdrawal would depress it. Callers that know the flows can neutralise
them by passing a pre-adjusted NAV series (subtract net external flow from the
ending NAV of each affected sub-period before calling these helpers). The MCP
tool documents this limitation in its response.
"""

from __future__ import annotations

from decimal import Decimal
from itertools import pairwise

ZERO = Decimal("0")
ONE = Decimal("1")


def simple_returns(values: list[Decimal]) -> list[Decimal]:
    """Compute simple period returns between consecutive NAV observations.

    Args:
        values: NAV observations ordered by date (oldest first).

    Returns:
        List of sub-period returns with ``len(values) - 1`` elements. A
        sub-period whose beginning value is zero yields a return of ``0`` to
        avoid division by zero.
    """
    returns: list[Decimal] = []
    for begin, end in pairwise(values):
        if begin == ZERO:
            returns.append(ZERO)
        else:
            returns.append((end - begin) / begin)
    return returns


def cumulative_twr(returns: list[Decimal]) -> Decimal:
    """Geometrically chain sub-period returns into a cumulative TWR.

    Args:
        returns: Sub-period returns (e.g. from :func:`simple_returns`).

    Returns:
        Cumulative time-weighted return as a fraction (``0.10`` == +10%).
        Returns ``0`` for an empty input.
    """
    growth = ONE
    for r in returns:
        growth *= ONE + r
    return growth - ONE


def cumulative_index(returns: list[Decimal], base: Decimal = ONE) -> list[Decimal]:
    """Build a cumulative growth index from sub-period returns.

    The index starts at ``base`` and is multiplied by ``(1 + r)`` for each
    sub-period return, producing a series with ``len(returns) + 1`` elements
    aligned to the original NAV observation dates.

    Args:
        returns: Sub-period returns (e.g. from :func:`simple_returns`).
        base: Starting index value (default ``1``).

    Returns:
        Growth index series, one element per observation date.
    """
    index = [base]
    for r in returns:
        index.append(index[-1] * (ONE + r))
    return index


def max_drawdown(index: list[Decimal]) -> Decimal:
    """Compute maximum drawdown of a cumulative value/index series.

    Drawdown is the largest peak-to-trough decline, expressed as a
    non-positive fraction (``-0.20`` == a 20% decline). Returns ``0`` when the
    series never declines or has fewer than two points.

    Args:
        index: Cumulative value or growth-index series ordered by date.

    Returns:
        Maximum drawdown as a non-positive ``Decimal``.
    """
    peak = None
    worst = ZERO
    for value in index:
        if peak is None or value > peak:
            peak = value
        if peak is not None and peak > ZERO:
            drawdown = (value - peak) / peak
            if drawdown < worst:
                worst = drawdown
    return worst


def align_benchmark_index(closes: list[Decimal]) -> list[Decimal]:
    """Build a cumulative growth index for a benchmark close series.

    Args:
        closes: Benchmark closing prices ordered by date (oldest first).

    Returns:
        Growth index normalised to ``1`` at the first close. Empty input
        yields an empty list.
    """
    if not closes:
        return []
    returns = simple_returns(closes)
    return cumulative_index(returns)


__all__ = [
    "align_benchmark_index",
    "cumulative_index",
    "cumulative_twr",
    "max_drawdown",
    "simple_returns",
]
