"""Tests for LimitOrderStore"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ib_sec_mcp.storage.limit_order_store import LimitOrderStore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TODAY = date(2025, 10, 1)
SYMBOL_CSPX = "CSPX"
SYMBOL_VWRA = "VWRA"
MARKET_LSE = "LSE"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> LimitOrderStore:
    s = LimitOrderStore(tmp_path / "test_limit_orders.db")
    yield s
    s.close()


def add_sample_order(
    store: LimitOrderStore,
    symbol: str = SYMBOL_CSPX,
    market: str = MARKET_LSE,
    order_type: str = "BUY",
    limit_price: str = "700.00",
    tranche_number: int = 1,
    quantity: str | None = "10",
    amount_usd: str | None = "7000",
    rationale: str = "SMA200 support",
) -> int:
    """Helper to add a sample order"""
    return store.add_order(
        symbol=symbol,
        market=market,
        order_type=order_type,
        limit_price=Decimal(limit_price),
        created_date=TODAY,
        quantity=Decimal(quantity) if quantity else None,
        amount_usd=Decimal(amount_usd) if amount_usd else None,
        tranche_number=tranche_number,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# Tests: Add Order
# ---------------------------------------------------------------------------


class TestAddOrder:
    def test_add_single_order(self, store: LimitOrderStore) -> None:
        order_id = add_sample_order(store)
        assert order_id is not None
        assert order_id > 0

    def test_add_order_returns_correct_data(self, store: LimitOrderStore) -> None:
        order_id = add_sample_order(store)
        order = store.get_order_by_id(order_id)

        assert order is not None
        assert order["symbol"] == SYMBOL_CSPX
        assert order["market"] == MARKET_LSE
        assert order["order_type"] == "BUY"
        assert order["limit_price"] == Decimal("700.00")
        assert order["quantity"] == Decimal("10")
        assert order["amount_usd"] == Decimal("7000")
        assert order["tranche_number"] == 1
        assert order["rationale"] == "SMA200 support"
        assert order["status"] == "PENDING"

    def test_add_multiple_orders(self, store: LimitOrderStore) -> None:
        id1 = add_sample_order(store, tranche_number=1, limit_price="700.00")
        id2 = add_sample_order(store, tranche_number=2, limit_price="685.00")
        id3 = add_sample_order(store, tranche_number=3, limit_price="660.00")

        assert id1 != id2 != id3
        orders = store.get_pending_orders(symbol=SYMBOL_CSPX)
        assert len(orders) == 3

    def test_add_order_without_quantity(self, store: LimitOrderStore) -> None:
        order_id = store.add_order(
            symbol="IDTL",
            market="LSE",
            order_type="BUY",
            limit_price=Decimal("3.15"),
            created_date=TODAY,
            amount_usd=Decimal("5000"),
        )
        order = store.get_order_by_id(order_id)
        assert order is not None
        assert order["quantity"] is None
        assert order["amount_usd"] == Decimal("5000")

    def test_add_order_invalid_type(self, store: LimitOrderStore) -> None:
        with pytest.raises(ValueError, match="Invalid order_type"):
            store.add_order(
                symbol="TEST",
                market="NYSE",
                order_type="LIMIT",
                limit_price=Decimal("100"),
                created_date=TODAY,
            )

    def test_unique_constraint(self, store: LimitOrderStore) -> None:
        """Same symbol + tranche_number + status should fail"""
        add_sample_order(store, tranche_number=1)
        with pytest.raises(Exception, match="UNIQUE constraint failed"):
            add_sample_order(store, tranche_number=1)

    def test_different_status_allows_same_tranche(self, store: LimitOrderStore) -> None:
        """After cancelling, same symbol+tranche can be re-added as PENDING"""
        order_id = add_sample_order(store, tranche_number=1)
        store.update_order(order_id, status="CANCELLED")

        # Should succeed because old order is CANCELLED, new is PENDING
        new_id = add_sample_order(store, tranche_number=1, limit_price="690.00")
        assert new_id != order_id


# ---------------------------------------------------------------------------
# Tests: Decimal Precision
# ---------------------------------------------------------------------------


class TestDecimalPrecision:
    def test_price_round_trip(self, store: LimitOrderStore) -> None:
        """Decimal precision must be preserved through TEXT storage"""
        order_id = store.add_order(
            symbol="TEST",
            market="NYSE",
            order_type="BUY",
            limit_price=Decimal("123.456789"),
            created_date=TODAY,
            quantity=Decimal("0.001"),
            amount_usd=Decimal("99999.99"),
        )
        order = store.get_order_by_id(order_id)
        assert order is not None
        assert order["limit_price"] == Decimal("123.456789")
        assert order["quantity"] == Decimal("0.001")
        assert order["amount_usd"] == Decimal("99999.99")

    def test_filled_price_precision(self, store: LimitOrderStore) -> None:
        order_id = add_sample_order(store)
        store.update_order(
            order_id,
            status="FILLED",
            filled_price=Decimal("699.5432"),
            filled_date=TODAY,
        )
        order = store.get_order_by_id(order_id)
        assert order is not None
        assert order["filled_price"] == Decimal("699.5432")


# ---------------------------------------------------------------------------
# Tests: Update Order
# ---------------------------------------------------------------------------


class TestUpdateOrder:
    def test_fill_order(self, store: LimitOrderStore) -> None:
        order_id = add_sample_order(store)
        result = store.update_order(
            order_id,
            status="FILLED",
            filled_price=Decimal("700.00"),
            filled_date=TODAY,
        )
        assert result is True

        order = store.get_order_by_id(order_id)
        assert order is not None
        assert order["status"] == "FILLED"
        assert order["filled_price"] == Decimal("700.00")
        assert order["filled_date"] == TODAY.isoformat()

    def test_cancel_order(self, store: LimitOrderStore) -> None:
        order_id = add_sample_order(store)
        result = store.update_order(order_id, status="CANCELLED")
        assert result is True

        order = store.get_order_by_id(order_id)
        assert order is not None
        assert order["status"] == "CANCELLED"

    def test_expire_order(self, store: LimitOrderStore) -> None:
        order_id = add_sample_order(store)
        result = store.update_order(order_id, status="EXPIRED")
        assert result is True

        order = store.get_order_by_id(order_id)
        assert order is not None
        assert order["status"] == "EXPIRED"

    def test_update_nonexistent(self, store: LimitOrderStore) -> None:
        result = store.update_order(9999, status="FILLED")
        assert result is False

    def test_reject_reverse_transition(self, store: LimitOrderStore) -> None:
        """Cannot go from FILLED -> PENDING"""
        order_id = add_sample_order(store)
        store.update_order(
            order_id, status="FILLED", filled_price=Decimal("700"), filled_date=TODAY
        )

        with pytest.raises(ValueError, match="Terminal statuses cannot be changed"):
            store.update_order(order_id, status="PENDING")

    def test_reject_cancelled_to_filled(self, store: LimitOrderStore) -> None:
        """Cannot go from CANCELLED -> FILLED"""
        order_id = add_sample_order(store)
        store.update_order(order_id, status="CANCELLED")

        with pytest.raises(ValueError, match="Terminal statuses cannot be changed"):
            store.update_order(order_id, status="FILLED")

    def test_update_limit_price(self, store: LimitOrderStore) -> None:
        order_id = add_sample_order(store)
        store.update_order(order_id, limit_price=Decimal("690.00"))

        order = store.get_order_by_id(order_id)
        assert order is not None
        assert order["limit_price"] == Decimal("690.00")

    def test_update_quantity(self, store: LimitOrderStore) -> None:
        order_id = add_sample_order(store)
        store.update_order(order_id, quantity=Decimal("20"))

        order = store.get_order_by_id(order_id)
        assert order is not None
        assert order["quantity"] == Decimal("20")

    def test_update_notes(self, store: LimitOrderStore) -> None:
        order_id = add_sample_order(store)
        store.update_order(order_id, notes="Updated strategy")

        order = store.get_order_by_id(order_id)
        assert order is not None
        assert order["notes"] == "Updated strategy"

    def test_invalid_status(self, store: LimitOrderStore) -> None:
        order_id = add_sample_order(store)
        with pytest.raises(ValueError, match="Invalid status"):
            store.update_order(order_id, status="INVALID")

    def test_reject_transition_to_pending(self, store: LimitOrderStore) -> None:
        """Cannot set status back to PENDING"""
        order_id = add_sample_order(store)
        # Even from PENDING -> PENDING should be rejected
        with pytest.raises(ValueError, match="Cannot transition back to PENDING"):
            store.update_order(order_id, status="PENDING")


# ---------------------------------------------------------------------------
# Tests: Get Pending Orders
# ---------------------------------------------------------------------------


class TestGetPendingOrders:
    def test_get_all_pending(self, store: LimitOrderStore) -> None:
        add_sample_order(store, symbol="CSPX", tranche_number=1)
        add_sample_order(store, symbol="VWRA", tranche_number=1, limit_price="165.00")

        orders = store.get_pending_orders()
        assert len(orders) == 2

    def test_filter_by_symbol(self, store: LimitOrderStore) -> None:
        add_sample_order(store, symbol="CSPX", tranche_number=1)
        add_sample_order(store, symbol="VWRA", tranche_number=1, limit_price="165.00")

        orders = store.get_pending_orders(symbol="CSPX")
        assert len(orders) == 1
        assert orders[0]["symbol"] == "CSPX"

    def test_filter_by_market(self, store: LimitOrderStore) -> None:
        add_sample_order(store, symbol="CSPX", market="LSE", tranche_number=1)
        add_sample_order(store, symbol="1329.T", market="TSE", tranche_number=1, limit_price="5400")

        orders = store.get_pending_orders(market="TSE")
        assert len(orders) == 1
        assert orders[0]["symbol"] == "1329.T"

    def test_excludes_non_pending(self, store: LimitOrderStore) -> None:
        id1 = add_sample_order(store, tranche_number=1)
        add_sample_order(store, tranche_number=2, limit_price="685.00")

        store.update_order(id1, status="FILLED", filled_price=Decimal("700"), filled_date=TODAY)

        orders = store.get_pending_orders()
        assert len(orders) == 1
        assert orders[0]["tranche_number"] == 2

    def test_empty_result(self, store: LimitOrderStore) -> None:
        orders = store.get_pending_orders()
        assert orders == []


# ---------------------------------------------------------------------------
# Tests: Get Order History
# ---------------------------------------------------------------------------


class TestGetOrderHistory:
    def test_returns_all_statuses(self, store: LimitOrderStore) -> None:
        id1 = add_sample_order(store, tranche_number=1)
        add_sample_order(store, tranche_number=2, limit_price="685.00")
        id3 = add_sample_order(store, tranche_number=3, limit_price="660.00")

        store.update_order(id1, status="FILLED", filled_price=Decimal("700"), filled_date=TODAY)
        store.update_order(id3, status="CANCELLED")

        history = store.get_order_history()
        assert len(history) == 3

        statuses = {o["status"] for o in history}
        assert statuses == {"FILLED", "PENDING", "CANCELLED"}

    def test_filter_by_symbol(self, store: LimitOrderStore) -> None:
        add_sample_order(store, symbol="CSPX", tranche_number=1)
        add_sample_order(store, symbol="VWRA", tranche_number=1, limit_price="165.00")

        history = store.get_order_history(symbol="CSPX")
        assert len(history) == 1

    def test_empty_history(self, store: LimitOrderStore) -> None:
        history = store.get_order_history()
        assert history == []


# ---------------------------------------------------------------------------
# Tests: Context Manager
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_context_manager(self, tmp_path: Path) -> None:
        with LimitOrderStore(tmp_path / "test.db") as store:
            order_id = add_sample_order(store)
            assert order_id > 0

    def test_close(self, tmp_path: Path) -> None:
        store = LimitOrderStore(tmp_path / "test.db")
        add_sample_order(store)
        store.close()
        # After close, operations should fail
        with pytest.raises(Exception, match="Cannot operate on a closed"):
            store.get_pending_orders()
