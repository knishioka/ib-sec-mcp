"""Tests for the live-vs-snapshot position reconciler."""

from decimal import Decimal

from ib_sec_mcp.api.cp_models import CPPosition
from ib_sec_mcp.core.position_reconciler import (
    ReconcileStatus,
    normalize_symbol,
    reconcile_positions,
)


def _cp(symbol: str, qty: str, mv: str, pnl: str, conid: int = 1) -> CPPosition:
    return CPPosition(
        acctId="U1234567",
        conid=conid,
        symbol=symbol,
        position=Decimal(qty),
        mktValue=Decimal(mv),
        unrealizedPnl=Decimal(pnl),
    )


def _snap(symbol: str, qty: str, value: str, pnl: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "quantity": Decimal(qty),
        "position_value": Decimal(value),
        "unrealized_pnl": Decimal(pnl),
    }


class TestNormalizeSymbol:
    def test_uppercases_and_strips(self) -> None:
        assert normalize_symbol("  aapl ") == "AAPL"

    def test_handles_none_and_empty(self) -> None:
        assert normalize_symbol(None) == ""
        assert normalize_symbol("   ") == ""


class TestReconcile:
    def test_unchanged_position_reports_value_diff(self) -> None:
        live = [_cp("AAPL", "100", "16000", "1000")]
        snap = [_snap("AAPL", "100", "15000", "500")]

        result = reconcile_positions("U1234567", live, snap, snapshot_date="2026-06-01")

        assert result.live_available is True
        assert result.degraded is False
        assert len(result.positions) == 1
        pos = result.positions[0]
        assert pos.symbol == "AAPL"
        assert pos.status == ReconcileStatus.UNCHANGED
        assert pos.quantity_diff == Decimal("0")
        assert pos.market_value_diff == Decimal("1000")
        assert pos.unrealized_pnl_diff == Decimal("500")
        assert result.summary.unchanged_count == 1
        assert result.summary.total_market_value_diff == Decimal("1000")

    def test_new_position_live_only(self) -> None:
        live = [_cp("MSFT", "10", "4000", "0")]
        snap: list[dict[str, object]] = []

        result = reconcile_positions("U1234567", live, snap)

        pos = result.positions[0]
        assert pos.status == ReconcileStatus.NEW
        assert pos.in_live is True
        assert pos.in_snapshot is False
        assert pos.snapshot_quantity is None
        assert pos.quantity_diff == Decimal("10")
        assert result.summary.new_count == 1

    def test_closed_position_snapshot_only(self) -> None:
        live: list[CPPosition] = []
        snap = [_snap("TSLA", "5", "1000", "-50")]

        result = reconcile_positions("U1234567", live, snap)

        pos = result.positions[0]
        assert pos.status == ReconcileStatus.CLOSED
        assert pos.in_live is False
        assert pos.live_quantity is None
        assert pos.quantity_diff == Decimal("-5")
        assert result.summary.closed_count == 1
        # Closed positions are not "matched" so excluded from total mv diff.
        assert result.summary.total_market_value_diff == Decimal("0")

    def test_quantity_changed(self) -> None:
        live = [_cp("PG", "150", "22500", "300")]
        snap = [_snap("PG", "100", "15000", "200")]

        result = reconcile_positions("U1234567", live, snap)

        pos = result.positions[0]
        assert pos.status == ReconcileStatus.QUANTITY_CHANGED
        assert pos.quantity_diff == Decimal("50")
        assert pos.market_value_diff == Decimal("7500")
        assert result.summary.quantity_changed_count == 1

    def test_symbol_normalization_matches_across_sources(self) -> None:
        live = [_cp(" aapl ", "100", "16000", "0")]
        snap = [_snap("AAPL", "100", "16000", "0")]

        result = reconcile_positions("U1234567", live, snap)

        assert len(result.positions) == 1
        assert result.positions[0].status == ReconcileStatus.UNCHANGED

    def test_positions_sorted_by_symbol(self) -> None:
        live = [_cp("ZM", "1", "100", "0", conid=2), _cp("AAPL", "1", "100", "0", conid=3)]
        snap: list[dict[str, object]] = []

        result = reconcile_positions("U1234567", live, snap)

        assert [p.symbol for p in result.positions] == ["AAPL", "ZM"]

    def test_degraded_mode_snapshot_only(self) -> None:
        live = [_cp("AAPL", "100", "16000", "0")]  # ignored when degraded
        snap = [_snap("AAPL", "100", "15000", "500"), _snap("PG", "10", "1500", "10")]

        result = reconcile_positions(
            "U1234567", live, snap, snapshot_date="2026-06-01", live_available=False
        )

        assert result.live_available is False
        assert result.degraded is True
        assert len(result.positions) == 2
        for pos in result.positions:
            assert pos.status == ReconcileStatus.SNAPSHOT_ONLY
            assert pos.in_live is False
            assert pos.live_quantity is None
            assert pos.quantity_diff is None
            assert pos.market_value_diff is None
        assert result.summary.snapshot_only_count == 2

    def test_empty_inputs(self) -> None:
        result = reconcile_positions("U1234567", [], [])

        assert result.positions == []
        assert result.summary.total_symbols == 0

    def test_aggregates_duplicate_live_symbols(self) -> None:
        # Two live contracts normalizing to the same symbol must be summed,
        # not silently overwritten.
        live = [
            _cp("AAPL", "100", "16000", "1000", conid=1),
            _cp("AAPL", "50", "8000", "500", conid=2),
        ]
        snap = [_snap("AAPL", "150", "24000", "1500")]

        result = reconcile_positions("U1234567", live, snap)

        assert len(result.positions) == 1
        pos = result.positions[0]
        assert pos.live_quantity == Decimal("150")
        assert pos.live_market_value == Decimal("24000")
        assert pos.live_unrealized_pnl == Decimal("1500")
        assert pos.status == ReconcileStatus.UNCHANGED

    def test_aggregates_duplicate_snapshot_symbols(self) -> None:
        live: list[CPPosition] = []
        snap = [_snap("AAPL", "100", "16000", "1000"), _snap("AAPL", "50", "8000", "500")]

        result = reconcile_positions("U1234567", live, snap)

        assert len(result.positions) == 1
        pos = result.positions[0]
        assert pos.snapshot_quantity == Decimal("150")
        assert pos.snapshot_market_value == Decimal("24000")
        assert pos.status == ReconcileStatus.CLOSED

    def test_empty_symbol_falls_back_to_conid(self) -> None:
        # A genuinely empty symbol (no ticker available) keys by contract id so
        # distinct contracts are not merged into a single blank-symbol entry.
        live = [_cp("", "10", "100", "0", conid=111), _cp("", "20", "200", "0", conid=222)]

        result = reconcile_positions("U1234567", live, [])

        assert {p.symbol for p in result.positions} == {"CONID:111", "CONID:222"}

    def test_decimal_precision_preserved(self) -> None:
        live = [_cp("AAPL", "100", "16000.12", "0.33")]
        snap = [_snap("AAPL", "100", "15000.01", "0.11")]

        result = reconcile_positions("U1234567", live, snap)

        pos = result.positions[0]
        assert isinstance(pos.market_value_diff, Decimal)
        assert pos.market_value_diff == Decimal("1000.11")
        assert pos.unrealized_pnl_diff == Decimal("0.22")
