"""Tests for the reconcile_positions_view MCP tool.

Uses a real ``PositionStore`` at a temp DB path (per testing rules: storage
uses the real class) and mocks the CP Gateway client for live positions.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.api.cp_client import CPAuthenticationError, CPConnectionError
from ib_sec_mcp.api.cp_models import CPPosition
from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.mcp.tools.position_reconcile import register_position_reconcile_tools
from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass
from ib_sec_mcp.storage.position_store import PositionStore
from tests.mcp._fastmcp_helpers import call_tool_fn

ACCOUNT_ID = "U1234567"
SNAP_DATE = date(2026, 6, 1)

CP_CLIENT_PATH = "ib_sec_mcp.mcp.tools.position_reconcile.CPClient"


def make_position(
    symbol: str,
    quantity: str,
    position_value: str,
    unrealized_pnl: str = "0",
) -> Position:
    return Position(
        account_id=ACCOUNT_ID,
        symbol=symbol,
        description=f"{symbol} Inc",
        asset_class=AssetClass.STOCK,
        quantity=Decimal(quantity),
        mark_price=Decimal("100"),
        position_value=Decimal(position_value),
        average_cost=Decimal("90"),
        cost_basis=Decimal("9000"),
        unrealized_pnl=Decimal(unrealized_pnl),
        currency="USD",
        fx_rate_to_base=Decimal("1.0"),
        position_date=SNAP_DATE,
    )


def make_account(positions: list[Position]) -> Account:
    return Account(
        account_id=ACCOUNT_ID,
        from_date=SNAP_DATE,
        to_date=SNAP_DATE,
        cash_balances=[
            CashBalance(
                currency="USD",
                starting_cash=Decimal("1000"),
                ending_cash=Decimal("1000"),
                ending_settled_cash=Decimal("1000"),
            )
        ],
        positions=positions,
    )


def _cp(symbol: str, qty: str, mv: str, pnl: str = "0", conid: int = 1) -> CPPosition:
    return CPPosition(
        acctId=ACCOUNT_ID,
        conid=conid,
        symbol=symbol,
        position=Decimal(qty),
        mktValue=Decimal(mv),
        unrealizedPnl=Decimal(pnl),
    )


def _mock_cp_client(
    positions: list[CPPosition] | None = None,
    accounts: list[str] | None = None,
) -> MagicMock:
    """Build a CPClient mock that works as an async context manager."""
    client = AsyncMock()
    client.get_positions = AsyncMock(return_value=positions or [])
    client.get_accounts = AsyncMock(return_value=accounts if accounts is not None else [ACCOUNT_ID])
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.fixture()
def test_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_position_reconcile_tools(mcp)
    return mcp


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    """Snapshot DB with AAPL (100) and PG (10) on SNAP_DATE."""
    path = tmp_path / "positions.db"
    store = PositionStore(path)
    store.save_snapshot(
        make_account(
            positions=[
                make_position("AAPL", "100", "15000", "500"),
                make_position("PG", "10", "1500", "10"),
            ]
        ),
        SNAP_DATE,
        "/data/jun.xml",
    )
    store.close()
    return str(path)


class TestReconcileHappyPath:
    async def test_live_vs_snapshot(self, test_mcp: FastMCP, db_path: str) -> None:
        # Live: AAPL grew to 150, PG closed, MSFT newly opened.
        live = [
            _cp("AAPL", "150", "24000", "1500", conid=1),
            _cp("MSFT", "20", "8000", "100", conid=2),
        ]
        with patch(CP_CLIENT_PATH, return_value=_mock_cp_client(positions=live)):
            result = await call_tool_fn(
                test_mcp,
                "reconcile_positions_view",
                account_id=ACCOUNT_ID,
                db_path=db_path,
                ctx=None,
            )
        data = json.loads(result)

        assert data["live_available"] is True
        assert data["degraded"] is False
        assert data["snapshot_date"] == SNAP_DATE.isoformat()

        by_symbol = {p["symbol"]: p for p in data["positions"]}
        assert by_symbol["AAPL"]["status"] == "quantity_changed"
        assert by_symbol["AAPL"]["quantity_diff"] == "50"
        assert by_symbol["MSFT"]["status"] == "new"
        assert by_symbol["PG"]["status"] == "closed"

        assert data["summary"]["new_count"] == 1
        assert data["summary"]["closed_count"] == 1
        assert data["summary"]["quantity_changed_count"] == 1

    async def test_auto_resolves_account_from_gateway(
        self, test_mcp: FastMCP, db_path: str
    ) -> None:
        live = [_cp("AAPL", "100", "15000", "500")]
        with patch(
            CP_CLIENT_PATH,
            return_value=_mock_cp_client(positions=live, accounts=[ACCOUNT_ID]),
        ):
            result = await call_tool_fn(
                test_mcp,
                "reconcile_positions_view",
                account_id=None,
                db_path=db_path,
                ctx=None,
            )
        data = json.loads(result)
        assert data["account_id"] == ACCOUNT_ID
        assert data["live_available"] is True


class TestGracefulDegradation:
    async def test_gateway_unreachable_falls_back_to_snapshot(
        self, test_mcp: FastMCP, db_path: str
    ) -> None:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=CPConnectionError("unreachable"))
        cm.__aexit__ = AsyncMock(return_value=False)
        with patch(CP_CLIENT_PATH, return_value=cm):
            result = await call_tool_fn(
                test_mcp,
                "reconcile_positions_view",
                account_id=ACCOUNT_ID,
                db_path=db_path,
                ctx=None,
            )
        data = json.loads(result)

        assert data["live_available"] is False
        assert data["degraded"] is True
        assert data["summary"]["snapshot_only_count"] == 2
        for pos in data["positions"]:
            assert pos["status"] == "snapshot_only"

    async def test_session_expired_degrades(self, test_mcp: FastMCP, db_path: str) -> None:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=CPAuthenticationError("expired"))
        cm.__aexit__ = AsyncMock(return_value=False)
        with patch(CP_CLIENT_PATH, return_value=cm):
            result = await call_tool_fn(
                test_mcp,
                "reconcile_positions_view",
                account_id=ACCOUNT_ID,
                db_path=db_path,
                ctx=None,
            )
        data = json.loads(result)
        assert data["degraded"] is True


class TestValidationAndEdgeCases:
    async def test_invalid_snapshot_date_raises(self, test_mcp: FastMCP, db_path: str) -> None:
        with (
            patch(CP_CLIENT_PATH, return_value=_mock_cp_client()),
            pytest.raises(ValidationError),
        ):
            await call_tool_fn(
                test_mcp,
                "reconcile_positions_view",
                account_id=ACCOUNT_ID,
                snapshot_date="not-a-date",
                db_path=db_path,
                ctx=None,
            )

    async def test_no_account_and_gateway_down_raises(
        self, test_mcp: FastMCP, db_path: str
    ) -> None:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=CPConnectionError("unreachable"))
        cm.__aexit__ = AsyncMock(return_value=False)
        with patch(CP_CLIENT_PATH, return_value=cm), pytest.raises(ValidationError):
            await call_tool_fn(
                test_mcp,
                "reconcile_positions_view",
                account_id=None,
                db_path=db_path,
                ctx=None,
            )

    async def test_no_snapshot_all_live_are_new(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        empty_db = str(tmp_path / "empty.db")
        live = [_cp("AAPL", "100", "15000", "0")]
        with patch(CP_CLIENT_PATH, return_value=_mock_cp_client(positions=live)):
            result = await call_tool_fn(
                test_mcp,
                "reconcile_positions_view",
                account_id=ACCOUNT_ID,
                db_path=empty_db,
                ctx=None,
            )
        data = json.loads(result)
        assert data["snapshot_date"] is None
        assert data["positions"][0]["status"] == "new"

    async def test_response_is_valid_json_with_expected_keys(
        self, test_mcp: FastMCP, db_path: str
    ) -> None:
        with patch(CP_CLIENT_PATH, return_value=_mock_cp_client(positions=[])):
            result = await call_tool_fn(
                test_mcp,
                "reconcile_positions_view",
                account_id=ACCOUNT_ID,
                db_path=db_path,
                ctx=None,
            )
        data = json.loads(result)
        assert {"account_id", "live_available", "degraded", "positions", "summary"} <= set(data)
