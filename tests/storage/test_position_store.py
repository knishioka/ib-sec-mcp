"""Tests for PositionStore"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass
from ib_sec_mcp.storage.position_store import PositionStore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACCOUNT_ID = "U1234567"
SNAP_DATE_1 = date(2025, 1, 31)
SNAP_DATE_2 = date(2025, 2, 28)
FROM_DATE = date(2025, 1, 1)
TO_DATE = date(2025, 1, 31)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> PositionStore:
    store = PositionStore(tmp_path / "test_positions.db")
    yield store
    store.close()


def make_position(
    account_id: str = ACCOUNT_ID,
    symbol: str = "AAPL",
    asset_class: AssetClass = AssetClass.STOCK,
    quantity: str = "10",
    mark_price: str = "150.00",
    position_value: str = "1500.00",
    cost_basis: str = "1400.00",
    average_cost: str = "140.00",
    unrealized_pnl: str = "100.00",
    coupon_rate: str | None = None,
    maturity_date: date | None = None,
    ytm: str | None = None,
    duration: str | None = None,
) -> Position:
    return Position(
        account_id=account_id,
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
        coupon_rate=Decimal(coupon_rate) if coupon_rate else None,
        maturity_date=maturity_date,
        ytm=Decimal(ytm) if ytm else None,
        duration=Decimal(duration) if duration else None,
    )


def make_account(
    account_id: str = ACCOUNT_ID,
    positions: list[Position] | None = None,
    from_date: date = FROM_DATE,
    to_date: date = TO_DATE,
) -> Account:
    return Account(
        account_id=account_id,
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


# ---------------------------------------------------------------------------
# TestPositionStoreSaveSnapshot
# ---------------------------------------------------------------------------


class TestPositionStoreSaveSnapshot:
    def test_save_single_position(self, store: PositionStore) -> None:
        pos = make_position()
        account = make_account(positions=[pos])
        saved = store.save_snapshot(account, SNAP_DATE_1, "/data/2025-01.xml")
        assert saved == 1

    def test_save_multiple_positions(self, store: PositionStore) -> None:
        positions = [
            make_position(symbol="AAPL"),
            make_position(symbol="MSFT"),
            make_position(symbol="GOOG"),
        ]
        account = make_account(positions=positions)
        saved = store.save_snapshot(account, SNAP_DATE_1, "/data/2025-01.xml")
        assert saved == 3

    def test_save_with_bond_fields(self, store: PositionStore) -> None:
        bond = make_position(
            symbol="T 4.5 2030",
            asset_class=AssetClass.BOND,
            coupon_rate="4.5",
            maturity_date=date(2030, 1, 15),
            ytm="4.2",
            duration="4.8",
        )
        account = make_account(positions=[bond])
        saved = store.save_snapshot(account, SNAP_DATE_1, "/data/2025-01.xml")
        assert saved == 1

        # Retrieve and verify bond fields
        snapshot = store.get_portfolio_snapshot(ACCOUNT_ID, SNAP_DATE_1)
        assert len(snapshot) == 1
        bond_row = snapshot[0]
        assert bond_row["symbol"] == "T 4.5 2030"
        assert bond_row["coupon_rate"] == Decimal("4.5")
        assert bond_row["maturity_date"] == "2030-01-15"

    def test_save_snapshot_metadata(self, store: PositionStore) -> None:
        pos = make_position()
        account = make_account(positions=[pos])
        store.save_snapshot(account, SNAP_DATE_1, "/data/2025-01.xml")

        dates = store.get_available_dates(ACCOUNT_ID)
        assert SNAP_DATE_1.isoformat() in dates

    def test_save_duplicate_replaces(self, store: PositionStore) -> None:
        pos = make_position(position_value="1500")
        account = make_account(positions=[pos])
        store.save_snapshot(account, SNAP_DATE_1, "/data/2025-01.xml")

        # Save again with updated value
        pos2 = make_position(position_value="1600")
        account2 = make_account(positions=[pos2])
        store.save_snapshot(account2, SNAP_DATE_1, "/data/2025-01-updated.xml")

        snapshot = store.get_portfolio_snapshot(ACCOUNT_ID, SNAP_DATE_1)
        assert len(snapshot) == 1
        assert snapshot[0]["position_value"] == Decimal("1600")

    def test_decimal_precision_preserved(self, store: PositionStore) -> None:
        precise_value = "1234.56789012345"
        pos = make_position(position_value=precise_value)
        account = make_account(positions=[pos])
        store.save_snapshot(account, SNAP_DATE_1, "/data/2025-01.xml")

        history = store.get_position_history(ACCOUNT_ID, "AAPL", SNAP_DATE_1, SNAP_DATE_1)
        assert len(history) == 1
        assert history[0]["position_value"] == Decimal(precise_value)


# ---------------------------------------------------------------------------
# TestPositionStoreGetHistory
# ---------------------------------------------------------------------------


class TestPositionStoreGetHistory:
    def test_get_position_history_returns_ordered_by_date(self, store: PositionStore) -> None:
        pos1 = make_position(position_value="1500")
        account1 = make_account(positions=[pos1])
        store.save_snapshot(account1, SNAP_DATE_1, "/data/jan.xml")

        pos2 = make_position(position_value="1600")
        account2 = make_account(positions=[pos2], from_date=SNAP_DATE_2, to_date=SNAP_DATE_2)
        store.save_snapshot(account2, SNAP_DATE_2, "/data/feb.xml")

        history = store.get_position_history(ACCOUNT_ID, "AAPL", SNAP_DATE_1, SNAP_DATE_2)
        assert len(history) == 2
        # Ordered ASC by date
        assert history[0]["snapshot_date"] < history[1]["snapshot_date"]
        assert history[0]["position_value"] == Decimal("1500")
        assert history[1]["position_value"] == Decimal("1600")

    def test_get_position_history_empty_range(self, store: PositionStore) -> None:
        history = store.get_position_history(ACCOUNT_ID, "AAPL", SNAP_DATE_1, SNAP_DATE_1)
        assert history == []

    def test_get_position_history_filters_by_symbol(self, store: PositionStore) -> None:
        positions = [make_position(symbol="AAPL"), make_position(symbol="MSFT")]
        account = make_account(positions=positions)
        store.save_snapshot(account, SNAP_DATE_1, "/data/jan.xml")

        history = store.get_position_history(ACCOUNT_ID, "AAPL", SNAP_DATE_1, SNAP_DATE_1)
        assert len(history) == 1
        assert history[0]["symbol"] == "AAPL"


# ---------------------------------------------------------------------------
# TestPositionStoreGetPortfolioSnapshot
# ---------------------------------------------------------------------------


class TestPositionStoreGetPortfolioSnapshot:
    def test_get_portfolio_snapshot_all_positions(self, store: PositionStore) -> None:
        positions = [
            make_position(symbol="AAPL", position_value="1500"),
            make_position(symbol="MSFT", position_value="3000"),
        ]
        account = make_account(positions=positions)
        store.save_snapshot(account, SNAP_DATE_1, "/data/jan.xml")

        snapshot = store.get_portfolio_snapshot(ACCOUNT_ID, SNAP_DATE_1)
        assert len(snapshot) == 2

    def test_get_portfolio_snapshot_ordered_by_value_desc(self, store: PositionStore) -> None:
        positions = [
            make_position(symbol="AAPL", position_value="1000"),
            make_position(symbol="MSFT", position_value="5000"),
            make_position(symbol="GOOG", position_value="2000"),
        ]
        account = make_account(positions=positions)
        store.save_snapshot(account, SNAP_DATE_1, "/data/jan.xml")

        snapshot = store.get_portfolio_snapshot(ACCOUNT_ID, SNAP_DATE_1)
        values = [row["position_value"] for row in snapshot]
        assert values == sorted(values, reverse=True)

    def test_get_portfolio_snapshot_empty(self, store: PositionStore) -> None:
        snapshot = store.get_portfolio_snapshot(ACCOUNT_ID, SNAP_DATE_1)
        assert snapshot == []

    def test_get_portfolio_snapshot_bond_fields_nullable(self, store: PositionStore) -> None:
        pos = make_position(symbol="AAPL")  # No bond fields
        account = make_account(positions=[pos])
        store.save_snapshot(account, SNAP_DATE_1, "/data/jan.xml")

        snapshot = store.get_portfolio_snapshot(ACCOUNT_ID, SNAP_DATE_1)
        assert snapshot[0]["coupon_rate"] is None
        assert snapshot[0]["maturity_date"] is None


# ---------------------------------------------------------------------------
# TestPositionStoreCompare
# ---------------------------------------------------------------------------


class TestPositionStoreCompare:
    def test_compare_snapshots_basic(self, store: PositionStore) -> None:
        # Date 1: AAPL + MSFT
        positions_1 = [make_position(symbol="AAPL"), make_position(symbol="MSFT")]
        account_1 = make_account(positions=positions_1)
        store.save_snapshot(account_1, SNAP_DATE_1, "/data/jan.xml")

        # Date 2: AAPL + GOOG (MSFT removed, GOOG added)
        positions_2 = [
            make_position(symbol="AAPL", position_value="1800"),
            make_position(symbol="GOOG"),
        ]
        account_2 = make_account(positions=positions_2, from_date=SNAP_DATE_2, to_date=SNAP_DATE_2)
        store.save_snapshot(account_2, SNAP_DATE_2, "/data/feb.xml")

        comparison = store.compare_portfolio_snapshots(ACCOUNT_ID, SNAP_DATE_1, SNAP_DATE_2)
        assert "GOOG" in comparison["positions_added"]
        assert "MSFT" in comparison["positions_removed"]
        assert comparison["date1"] == SNAP_DATE_1.isoformat()
        assert comparison["date2"] == SNAP_DATE_2.isoformat()

    def test_compare_snapshots_value_changes(self, store: PositionStore) -> None:
        pos1 = make_position(symbol="AAPL", position_value="1000")
        account_1 = make_account(positions=[pos1])
        store.save_snapshot(account_1, SNAP_DATE_1, "/data/jan.xml")

        pos2 = make_position(symbol="AAPL", position_value="1200")
        account_2 = make_account(positions=[pos2], from_date=SNAP_DATE_2, to_date=SNAP_DATE_2)
        store.save_snapshot(account_2, SNAP_DATE_2, "/data/feb.xml")

        comparison = store.compare_portfolio_snapshots(ACCOUNT_ID, SNAP_DATE_1, SNAP_DATE_2)
        assert comparison["total_value_change"] == Decimal("200")
        assert comparison["total_value_change_pct"] == Decimal("20")
        assert len(comparison["positions_changed"]) == 1
        change = comparison["positions_changed"][0]
        assert change["symbol"] == "AAPL"
        assert change["value_change"] == Decimal("200")

    def test_compare_snapshots_empty_date(self, store: PositionStore) -> None:
        pos = make_position(symbol="AAPL")
        account = make_account(positions=[pos])
        store.save_snapshot(account, SNAP_DATE_1, "/data/jan.xml")

        comparison = store.compare_portfolio_snapshots(ACCOUNT_ID, SNAP_DATE_1, SNAP_DATE_2)
        # SNAP_DATE_2 has no data, so AAPL is "removed"
        assert "AAPL" in comparison["positions_removed"]


# ---------------------------------------------------------------------------
# TestPositionStoreStatistics
# ---------------------------------------------------------------------------


class TestPositionStoreStatistics:
    def test_get_position_statistics(self, store: PositionStore) -> None:
        pos1 = make_position(mark_price="100", position_value="1000", unrealized_pnl="50")
        account1 = make_account(positions=[pos1])
        store.save_snapshot(account1, SNAP_DATE_1, "/data/jan.xml")

        pos2 = make_position(mark_price="120", position_value="1200", unrealized_pnl="100")
        account2 = make_account(positions=[pos2], from_date=SNAP_DATE_2, to_date=SNAP_DATE_2)
        store.save_snapshot(account2, SNAP_DATE_2, "/data/feb.xml")

        stats = store.get_position_statistics(ACCOUNT_ID, "AAPL", SNAP_DATE_1, SNAP_DATE_2)
        assert stats["snapshot_count"] == 2
        assert stats["price_statistics"]["min"] == Decimal("100")
        assert stats["price_statistics"]["max"] == Decimal("120")
        assert stats["value_statistics"]["min"] == Decimal("1000")
        assert stats["value_statistics"]["max"] == Decimal("1200")

    def test_get_position_statistics_no_data(self, store: PositionStore) -> None:
        stats = store.get_position_statistics(ACCOUNT_ID, "AAPL", SNAP_DATE_1, SNAP_DATE_2)
        assert stats["snapshot_count"] == 0
        assert "price_statistics" not in stats


# ---------------------------------------------------------------------------
# TestPositionStoreAvailableDates
# ---------------------------------------------------------------------------


class TestPositionStoreAvailableDates:
    def test_get_available_dates(self, store: PositionStore) -> None:
        pos = make_position()
        account1 = make_account(positions=[pos])
        store.save_snapshot(account1, SNAP_DATE_1, "/data/jan.xml")

        pos2 = make_position()
        account2 = make_account(positions=[pos2], from_date=SNAP_DATE_2, to_date=SNAP_DATE_2)
        store.save_snapshot(account2, SNAP_DATE_2, "/data/feb.xml")

        dates = store.get_available_dates(ACCOUNT_ID)
        assert SNAP_DATE_1.isoformat() in dates
        assert SNAP_DATE_2.isoformat() in dates

    def test_get_available_dates_empty(self, store: PositionStore) -> None:
        dates = store.get_available_dates(ACCOUNT_ID)
        assert dates == []

    def test_get_available_dates_ordered_desc(self, store: PositionStore) -> None:
        pos = make_position()
        account1 = make_account(positions=[pos])
        store.save_snapshot(account1, SNAP_DATE_1, "/data/jan.xml")

        pos2 = make_position()
        account2 = make_account(positions=[pos2], from_date=SNAP_DATE_2, to_date=SNAP_DATE_2)
        store.save_snapshot(account2, SNAP_DATE_2, "/data/feb.xml")

        dates = store.get_available_dates(ACCOUNT_ID)
        # Should be ordered DESC (most recent first)
        assert dates[0] > dates[1]


# ---------------------------------------------------------------------------
# TestPositionStoreContextManager
# ---------------------------------------------------------------------------


class TestPositionStoreContextManager:
    def test_context_manager_opens_and_closes(self, tmp_path: Path) -> None:
        db_path = tmp_path / "ctx_test.db"
        with PositionStore(db_path) as store:
            pos = make_position()
            account = make_account(positions=[pos])
            saved = store.save_snapshot(account, SNAP_DATE_1, "/data/jan.xml")
            assert saved == 1
