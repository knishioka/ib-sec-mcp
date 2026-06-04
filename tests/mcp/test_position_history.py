"""Tests for the position history MCP tools (SQLite-backed).

Uses a real ``PositionStore`` populated at a temp DB path (per testing rules:
storage uses the real class, not mocks). Each tool is called with that same
``db_path`` so it reads what we wrote.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.mcp.tools.position_history import register_position_history_tools
from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass
from ib_sec_mcp.storage.position_store import PositionStore
from tests.mcp._fastmcp_helpers import call_tool_fn

ACCOUNT_ID = "U1234567"
SNAP_DATE_1 = date(2025, 1, 31)
SNAP_DATE_2 = date(2025, 2, 28)


def make_position(
    symbol: str = "AAPL",
    asset_class: AssetClass = AssetClass.STOCK,
    quantity: str = "10",
    mark_price: str = "150.00",
    position_value: str = "1500.00",
    cost_basis: str = "1400.00",
    average_cost: str = "140.00",
    unrealized_pnl: str = "100.00",
) -> Position:
    return Position(
        account_id=ACCOUNT_ID,
        symbol=symbol,
        description=f"{symbol} Inc",
        asset_class=asset_class,
        quantity=Decimal(quantity),
        mark_price=Decimal(mark_price),
        position_value=Decimal(position_value),
        average_cost=Decimal(average_cost),
        cost_basis=Decimal(cost_basis),
        unrealized_pnl=Decimal(unrealized_pnl),
        currency="USD",
        fx_rate_to_base=Decimal("1.0"),
        position_date=SNAP_DATE_1,
    )


def make_account(
    positions: list[Position] | None = None,
    from_date: date = SNAP_DATE_1,
    to_date: date = SNAP_DATE_1,
) -> Account:
    return Account(
        account_id=ACCOUNT_ID,
        from_date=from_date,
        to_date=to_date,
        cash_balances=[
            CashBalance(
                currency="USD",
                starting_cash=Decimal("1000"),
                ending_cash=Decimal("1000"),
                ending_settled_cash=Decimal("1000"),
            )
        ],
        positions=positions or [],
    )


@pytest.fixture()
def test_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_position_history_tools(mcp)
    return mcp


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    """Create a populated positions DB and return its path string."""
    path = tmp_path / "positions.db"
    store = PositionStore(path)
    # Two snapshots of AAPL + a second symbol on date 1.
    store.save_snapshot(
        make_account(
            positions=[
                make_position(symbol="AAPL", mark_price="150", position_value="1500"),
                make_position(symbol="MSFT", mark_price="300", position_value="3000"),
            ]
        ),
        SNAP_DATE_1,
        "/data/jan.xml",
    )
    store.save_snapshot(
        make_account(
            positions=[make_position(symbol="AAPL", mark_price="160", position_value="1600")],
            from_date=SNAP_DATE_2,
            to_date=SNAP_DATE_2,
        ),
        SNAP_DATE_2,
        "/data/feb.xml",
    )
    store.close()
    return str(path)


class TestGetPositionHistory:
    async def test_returns_snapshots_for_symbol(self, test_mcp: FastMCP, db_path: str) -> None:
        result = await call_tool_fn(
            test_mcp,
            "get_position_history",
            account_id=ACCOUNT_ID,
            symbol="AAPL",
            start_date="2025-01-01",
            end_date="2025-03-01",
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)
        assert data["snapshot_count"] == 2
        assert len(data["snapshots"]) == 2
        assert data["symbol"] == "AAPL"

    async def test_empty_range_returns_message(self, test_mcp: FastMCP, db_path: str) -> None:
        result = await call_tool_fn(
            test_mcp,
            "get_position_history",
            account_id=ACCOUNT_ID,
            symbol="NVDA",
            start_date="2025-01-01",
            end_date="2025-03-01",
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)
        assert data["snapshots"] == []
        assert "message" in data

    async def test_invalid_date_raises_validation_error(
        self, test_mcp: FastMCP, db_path: str
    ) -> None:
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp,
                "get_position_history",
                account_id=ACCOUNT_ID,
                symbol="AAPL",
                start_date="not-a-date",
                end_date="2025-03-01",
                db_path=db_path,
                ctx=None,
            )


class TestGetPortfolioSnapshot:
    async def test_returns_positions_and_totals(self, test_mcp: FastMCP, db_path: str) -> None:
        result = await call_tool_fn(
            test_mcp,
            "get_portfolio_snapshot",
            account_id=ACCOUNT_ID,
            snapshot_date="2025-01-31",
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)
        assert data["position_count"] == 2
        # total_value serialized as string via default=str; AAPL 1500 + MSFT 3000.
        assert Decimal(str(data["total_value"])) == Decimal("4500")

    async def test_invalid_date_raises(self, test_mcp: FastMCP, db_path: str) -> None:
        with pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp,
                "get_portfolio_snapshot",
                account_id=ACCOUNT_ID,
                snapshot_date="2025/01/31",
                db_path=db_path,
                ctx=None,
            )


class TestComparePortfolioSnapshots:
    async def test_compare_detects_removed_symbol(self, test_mcp: FastMCP, db_path: str) -> None:
        result = await call_tool_fn(
            test_mcp,
            "compare_portfolio_snapshots",
            account_id=ACCOUNT_ID,
            date1="2025-01-31",
            date2="2025-02-28",
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)
        # MSFT present on date1 only -> removed.
        assert "MSFT" in data["positions_removed"]


class TestGetPositionStatistics:
    async def test_statistics_min_max(self, test_mcp: FastMCP, db_path: str) -> None:
        result = await call_tool_fn(
            test_mcp,
            "get_position_statistics",
            account_id=ACCOUNT_ID,
            symbol="AAPL",
            start_date="2025-01-01",
            end_date="2025-03-01",
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)
        assert data["snapshot_count"] == 2
        assert Decimal(str(data["price_statistics"]["min"])) == Decimal("150")
        assert Decimal(str(data["price_statistics"]["max"])) == Decimal("160")


class TestGetAvailableSnapshotDates:
    async def test_lists_available_dates(self, test_mcp: FastMCP, db_path: str) -> None:
        result = await call_tool_fn(
            test_mcp,
            "get_available_snapshot_dates",
            account_id=ACCOUNT_ID,
            db_path=db_path,
            ctx=None,
        )
        data = json.loads(result)
        assert data["snapshot_count"] == 2
        assert "2025-01-31" in data["available_dates"]
        assert "2025-02-28" in data["available_dates"]
