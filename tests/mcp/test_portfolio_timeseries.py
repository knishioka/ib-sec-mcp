"""Tests for the portfolio time-series MCP tool.

Uses a real :class:`PositionStore` at a temp DB path (per testing rules:
storage uses the real class, not mocks) and a symbol-dispatching fake for
yfinance so the benchmark fetch is network-independent.

``get_portfolio_timeseries`` imports ``yfinance`` lazily inside a helper, so the
patch target is the real ``yfinance.Ticker`` attribute.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fastmcp import FastMCP

from ib_sec_mcp.analyzers.timeseries import (
    cumulative_index,
    cumulative_twr,
    max_drawdown,
    simple_returns,
)
from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.mcp.tools.portfolio_timeseries import register_portfolio_timeseries_tools
from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass
from ib_sec_mcp.storage.position_store import PositionStore
from tests.mcp._fastmcp_helpers import call_tool_fn

ACCOUNT_ID = "U1234567"
PATCH_TARGET = "yfinance.Ticker"

# Three NAV observations: 1500 -> 1600 -> 1440 (cash held constant at 1000).
SNAP_DATES = [date(2025, 1, 31), date(2025, 2, 28), date(2025, 3, 31)]
POSITION_VALUES = ["1500.00", "1600.00", "1440.00"]


def make_account(position_value: str, snap_date: date) -> Account:
    position = Position(
        account_id=ACCOUNT_ID,
        symbol="AAPL",
        description="AAPL Inc",
        asset_class=AssetClass.STOCK,
        quantity=Decimal("10"),
        mark_price=Decimal(position_value) / Decimal("10"),
        position_value=Decimal(position_value),
        average_cost=Decimal("140.00"),
        cost_basis=Decimal("1400.00"),
        unrealized_pnl=Decimal("100.00"),
        currency="USD",
        fx_rate_to_base=Decimal("1.0"),
        position_date=snap_date,
    )
    return Account(
        account_id=ACCOUNT_ID,
        from_date=snap_date,
        to_date=snap_date,
        cash_balances=[
            CashBalance(
                currency="USD",
                starting_cash=Decimal("1000"),
                ending_cash=Decimal("1000"),
                ending_settled_cash=Decimal("1000"),
            )
        ],
        positions=[position],
    )


class FakeTicker:
    """yfinance ticker fake returning a date-indexed Close DataFrame."""

    histories: dict[str, Any] = {}

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, start: str | None = None, end: str | None = None, **_: Any) -> Any:
        value = self.histories[self.symbol]
        if isinstance(value, Exception):
            raise value
        return value


def _make_history(dates: list[date], closes: list[float]) -> pd.DataFrame:
    index = pd.DatetimeIndex([pd.Timestamp(d) for d in dates])
    return pd.DataFrame({"Close": closes}, index=index)


@pytest.fixture()
def test_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_portfolio_timeseries_tools(mcp)
    return mcp


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    """Create a populated positions DB with a 3-point NAV series."""
    path = tmp_path / "positions.db"
    store = PositionStore(path)
    for value, snap_date in zip(POSITION_VALUES, SNAP_DATES, strict=True):
        store.save_snapshot(make_account(value, snap_date), snap_date, f"/data/{snap_date}.xml")
    store.close()
    return str(path)


@pytest.fixture()
def patch_yf(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch yfinance.Ticker with a benchmark that rises 100 -> 110 -> 121."""
    FakeTicker.histories = {
        "SPY": _make_history(SNAP_DATES, [100.0, 110.0, 121.0]),
    }
    monkeypatch.setattr(PATCH_TARGET, FakeTicker)


class TestPureMath:
    def test_simple_returns(self) -> None:
        navs = [Decimal(v) for v in POSITION_VALUES]
        # NAV here equals position value + 1000 cash in the tool; the math
        # helper is tested directly on a known series.
        returns = simple_returns([Decimal("100"), Decimal("110"), Decimal("99")])
        assert returns[0] == Decimal("0.1")
        assert returns[1] == Decimal("-0.1")
        # cumulative chained TWR: 1.1 * 0.9 - 1 = -0.01
        assert cumulative_twr(returns) == Decimal("-0.01")
        # navs unused beyond construction; keep reference for clarity
        assert len(navs) == 3

    def test_zero_begin_value_is_safe(self) -> None:
        assert simple_returns([Decimal("0"), Decimal("100")]) == [Decimal("0")]

    def test_max_drawdown(self) -> None:
        index = cumulative_index(simple_returns([Decimal("100"), Decimal("120"), Decimal("90")]))
        # peak 1.2 -> trough 0.9: drawdown = 0.9/1.2 - 1 = -0.25
        assert max_drawdown(index) == Decimal("-0.25")

    def test_no_drawdown_on_monotonic_increase(self) -> None:
        index = cumulative_index(simple_returns([Decimal("100"), Decimal("110"), Decimal("120")]))
        assert max_drawdown(index) == Decimal("0")


class TestGetPortfolioTimeseries:
    async def test_happy_path_with_benchmark(
        self, test_mcp: FastMCP, db_path: str, patch_yf: None
    ) -> None:
        result = await call_tool_fn(
            test_mcp,
            "get_portfolio_timeseries",
            account_id=ACCOUNT_ID,
            start_date="2025-01-01",
            end_date="2025-04-01",
            benchmark="SPY",
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)

        assert data["snapshot_count"] == 3
        # NAV = position value + 1000 cash: 2500 -> 2600 -> 2440
        assert Decimal(str(data["portfolio"]["start_nav"])) == Decimal("2500.00")
        assert Decimal(str(data["portfolio"]["end_nav"])) == Decimal("2440.00")
        # Portfolio TWR: (2600/2500) * (2440/2600) - 1 = -0.024
        assert Decimal(str(data["portfolio"]["twr"])) == Decimal("-0.024")
        # Series aligned to 3 dates.
        assert len(data["portfolio"]["series"]) == 3
        # Benchmark rises 100->110->121 => TWR = 0.21
        assert Decimal(str(data["benchmark"]["twr"])) == Decimal("0.21")
        # Relative performance present and negative (portfolio underperformed).
        assert data["relative_performance"]["outperformed"] is False
        assert "external_cash_flows" in data["methodology"]

    async def test_benchmark_nan_closes_are_dropped(
        self, test_mcp: FastMCP, db_path: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A NaN close (e.g. holiday/missing data) must not crash benchmark
        # tracking via Decimal("NaN") formatting; the NaN row is dropped.
        FakeTicker.histories = {
            "SPY": _make_history(SNAP_DATES, [100.0, float("nan"), 121.0]),
        }
        monkeypatch.setattr(PATCH_TARGET, FakeTicker)

        result = await call_tool_fn(
            test_mcp,
            "get_portfolio_timeseries",
            account_id=ACCOUNT_ID,
            start_date="2025-01-01",
            end_date="2025-04-01",
            benchmark="SPY",
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)
        # Two valid closes remain (100 -> 121): TWR = 0.21, no error block.
        assert "error" not in data["benchmark"]
        assert data["benchmark"]["observation_count"] == 2
        assert Decimal(str(data["benchmark"]["twr"])) == Decimal("0.21")

    async def test_decimal_precision_no_float(
        self, test_mcp: FastMCP, db_path: str, patch_yf: None
    ) -> None:
        result = await call_tool_fn(
            test_mcp,
            "get_portfolio_timeseries",
            account_id=ACCOUNT_ID,
            start_date="2025-01-01",
            end_date="2025-04-01",
            benchmark="SPY",
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)
        # Values serialized via default=str → exact Decimal strings, no float noise.
        navs = [pt["nav"] for pt in data["portfolio"]["series"]]
        assert navs == ["2500.00", "2600.00", "2440.00"]

    async def test_benchmark_failure_degrades_gracefully(
        self, test_mcp: FastMCP, db_path: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        FakeTicker.histories = {"SPY": RuntimeError("network down")}
        monkeypatch.setattr(PATCH_TARGET, FakeTicker)

        result = await call_tool_fn(
            test_mcp,
            "get_portfolio_timeseries",
            account_id=ACCOUNT_ID,
            start_date="2025-01-01",
            end_date="2025-04-01",
            benchmark="SPY",
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)
        # Portfolio metrics still returned; benchmark carries an error note.
        assert data["snapshot_count"] == 3
        assert "error" in data["benchmark"]
        assert data["relative_performance"] is None

    async def test_insufficient_snapshots_returns_message(
        self, test_mcp: FastMCP, tmp_path: Path, patch_yf: None
    ) -> None:
        path = tmp_path / "single.db"
        store = PositionStore(path)
        store.save_snapshot(make_account("1500.00", SNAP_DATES[0]), SNAP_DATES[0], "/x.xml")
        store.close()

        result = await call_tool_fn(
            test_mcp,
            "get_portfolio_timeseries",
            account_id=ACCOUNT_ID,
            start_date="2025-01-01",
            end_date="2025-04-01",
            benchmark="SPY",
            db_path=str(path),
            ctx=None,
        )
        data = json.loads(result)
        assert data["snapshot_count"] == 1
        assert "message" in data

    async def test_invalid_date_raises_validation_error(
        self, test_mcp: FastMCP, db_path: str
    ) -> None:
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp,
                "get_portfolio_timeseries",
                account_id=ACCOUNT_ID,
                start_date="not-a-date",
                end_date="2025-04-01",
                db_path=db_path,
                ctx=None,
            )

    async def test_start_after_end_raises(self, test_mcp: FastMCP, db_path: str) -> None:
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp,
                "get_portfolio_timeseries",
                account_id=ACCOUNT_ID,
                start_date="2025-04-01",
                end_date="2025-01-01",
                db_path=db_path,
                ctx=None,
            )
