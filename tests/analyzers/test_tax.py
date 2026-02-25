"""Tests for tax analyzer"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from ib_sec_mcp.analyzers.tax import TaxAnalyzer
from ib_sec_mcp.models.account import Account
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass, BuySell, Trade


@pytest.fixture
def short_term_gain_trade():
    """Trade with short-term gain (trade_date - open_date < 365 days)."""
    return Trade(
        account_id="U1234567",
        trade_id="ST1",
        trade_date=date(2025, 1, 10),
        settle_date=date(2025, 1, 12),
        open_date=date(2024, 8, 1),  # ~162 days before trade_date
        symbol="AAPL",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.SELL,
        quantity=Decimal("10"),
        trade_price=Decimal("160"),
        trade_money=Decimal("1600"),
        ib_commission=Decimal("-1.50"),
        fifo_pnl_realized=Decimal("200"),
    )


@pytest.fixture
def long_term_gain_trade():
    """Trade with long-term gain (trade_date - open_date >= 365 days)."""
    return Trade(
        account_id="U1234567",
        trade_id="LT1",
        trade_date=date(2025, 2, 15),
        settle_date=date(2025, 2, 18),
        open_date=date(2024, 1, 10),  # 401 days before trade_date
        symbol="MSFT",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.SELL,
        quantity=Decimal("5"),
        trade_price=Decimal("400"),
        trade_money=Decimal("2000"),
        ib_commission=Decimal("-2.00"),
        fifo_pnl_realized=Decimal("500"),
    )


@pytest.fixture
def loss_trade():
    """Trade with realized loss."""
    return Trade(
        account_id="U1234567",
        trade_id="LOSS1",
        trade_date=date(2025, 1, 15),
        settle_date=date(2025, 1, 17),
        symbol="GOOG",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.SELL,
        quantity=Decimal("3"),
        trade_price=Decimal("170"),
        trade_money=Decimal("510"),
        ib_commission=Decimal("-1.00"),
        fifo_pnl_realized=Decimal("-80"),
    )


@pytest.fixture
def zero_coupon_bond_position():
    """Zero-coupon bond position (for phantom income)."""
    return Position(
        account_id="U1234567",
        symbol="US912810SJ88",
        description="US T-BOND STRIPS 2035",
        asset_class=AssetClass.BOND,
        quantity=Decimal("10000"),
        mark_price=Decimal("65.50"),
        position_value=Decimal("6550"),
        average_cost=Decimal("60"),
        cost_basis=Decimal("6000"),
        unrealized_pnl=Decimal("550"),
        currency="USD",
        fx_rate_to_base=Decimal("1"),
        position_date=date(2025, 1, 31),
        maturity_date=date(2035, 1, 15),
        coupon_rate=None,
    )


@pytest.fixture
def coupon_bond_position():
    """Bond with a coupon rate (should be skipped for phantom income)."""
    return Position(
        account_id="U1234567",
        symbol="US912828ZZ19",
        description="US T-NOTE 2.5% 2030",
        asset_class=AssetClass.BOND,
        quantity=Decimal("5000"),
        mark_price=Decimal("95"),
        position_value=Decimal("4750"),
        average_cost=Decimal("98"),
        cost_basis=Decimal("4900"),
        unrealized_pnl=Decimal("-150"),
        currency="USD",
        fx_rate_to_base=Decimal("1"),
        position_date=date(2025, 1, 31),
        maturity_date=date(2030, 6, 15),
        coupon_rate=Decimal("2.5"),
    )


@pytest.fixture
def bond_no_maturity():
    """Bond position without maturity date (should be skipped)."""
    return Position(
        account_id="U1234567",
        symbol="UNKNOWN_BOND",
        description="BOND WITHOUT MATURITY",
        asset_class=AssetClass.BOND,
        quantity=Decimal("1000"),
        mark_price=Decimal("80"),
        position_value=Decimal("800"),
        average_cost=Decimal("75"),
        cost_basis=Decimal("750"),
        unrealized_pnl=Decimal("50"),
        currency="USD",
        fx_rate_to_base=Decimal("1"),
        position_date=date(2025, 1, 31),
        maturity_date=None,
        coupon_rate=None,
    )


@pytest.fixture
def mixed_tax_account(
    short_term_gain_trade,
    long_term_gain_trade,
    loss_trade,
    zero_coupon_bond_position,
):
    """Account with mixed gains/losses and a zero-coupon bond."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        trades=[short_term_gain_trade, long_term_gain_trade, loss_trade],
        positions=[zero_coupon_bond_position],
    )


@pytest.fixture
def empty_account():
    """Account with no trades or positions."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        trades=[],
        positions=[],
    )


def _mock_date_today(target_date):
    """Create a mock for date.today() in the tax analyzer module."""
    mock_date = MagicMock(wraps=date)
    mock_date.today.return_value = target_date
    mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
    return mock_date


class TestTaxAnalyzer:
    """Tests for TaxAnalyzer."""

    def test_analyzer_name(self, mixed_tax_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=mixed_tax_account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()
        assert result["analyzer"] == "Tax"

    def test_default_tax_rate(self, empty_account):
        analyzer = TaxAnalyzer(account=empty_account)
        result = analyzer.analyze()
        assert Decimal(result["tax_rate"]) == Decimal("0.30")

    def test_custom_tax_rate(self, empty_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.15"), account=empty_account)
        result = analyzer.analyze()
        assert Decimal(result["tax_rate"]) == Decimal("0.15")

    def test_total_realized_pnl(self, mixed_tax_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=mixed_tax_account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        # 200 + 500 + (-80) = 620
        assert Decimal(result["total_realized_pnl"]) == Decimal("620")

    def test_short_term_gains(self, mixed_tax_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=mixed_tax_account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        # short_term_gain_trade: trade(2025-01-10) - open(2024-08-01) = 162 days < 365
        # pnl=200 > 0 => short_term
        assert Decimal(result["short_term_gains"]) == Decimal("200")

    def test_long_term_gains(self, mixed_tax_account):
        """Test long-term gain classification using open_date-based holding period."""
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=mixed_tax_account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        # long_term_gain_trade: trade(2025-02-15) - open(2024-01-10) = 401 days >= 365
        # pnl=500 > 0 => long_term
        assert Decimal(result["long_term_gains"]) == Decimal("500")

    def test_capital_gains_tax_positive_pnl(self, mixed_tax_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=mixed_tax_account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        # total_realized_pnl = 620 > 0, so tax = 620 * 0.30 = 186
        assert Decimal(result["estimated_capital_gains_tax"]) == Decimal("186.0")

    def test_capital_gains_tax_negative_pnl(self):
        """No capital gains tax when total realized PnL is negative."""
        loss_only_trades = [
            Trade(
                account_id="U1234567",
                trade_id="LOSS_ONLY",
                trade_date=date(2025, 1, 10),
                settle_date=date(2025, 1, 12),
                symbol="AAPL",
                asset_class=AssetClass.STOCK,
                buy_sell=BuySell.SELL,
                quantity=Decimal("10"),
                trade_price=Decimal("140"),
                trade_money=Decimal("1400"),
                ib_commission=Decimal("-1.00"),
                fifo_pnl_realized=Decimal("-100"),
            ),
        ]
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=loss_only_trades,
            positions=[],
        )
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=account)
        result = analyzer.analyze()

        assert Decimal(result["estimated_capital_gains_tax"]) == Decimal("0")

    def test_phantom_income_zero_coupon_bond(self, mixed_tax_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=mixed_tax_account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        phantom_total = Decimal(result["phantom_income_total"])
        assert phantom_total > Decimal("0")

        by_position = result["phantom_income_by_position"]
        assert len(by_position) == 1
        assert by_position[0]["symbol"] == "US912810SJ88"
        assert Decimal(by_position[0]["phantom_income"]) > Decimal("0")

    def test_phantom_income_coupon_bond_skipped(self, coupon_bond_position):
        """Bonds with coupon rate > 0 should be skipped for phantom income."""
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=[],
            positions=[coupon_bond_position],
        )
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        assert Decimal(result["phantom_income_total"]) == Decimal("0")
        assert len(result["phantom_income_by_position"]) == 0

    def test_phantom_income_no_maturity_skipped(self, bond_no_maturity):
        """Bonds without maturity date should be skipped for phantom income."""
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=[],
            positions=[bond_no_maturity],
        )
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        assert Decimal(result["phantom_income_total"]) == Decimal("0")
        assert len(result["phantom_income_by_position"]) == 0

    def test_phantom_income_tax(self, mixed_tax_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=mixed_tax_account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        phantom_total = Decimal(result["phantom_income_total"])
        phantom_tax = Decimal(result["estimated_phantom_income_tax"])
        assert phantom_tax == phantom_total * Decimal("0.30")

    def test_total_estimated_tax(self, mixed_tax_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=mixed_tax_account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        capital_gains_tax = Decimal(result["estimated_capital_gains_tax"])
        phantom_tax = Decimal(result["estimated_phantom_income_tax"])
        total_tax = Decimal(result["total_estimated_tax"])
        assert total_tax == capital_gains_tax + phantom_tax

    def test_empty_account_no_tax(self, empty_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=empty_account)
        result = analyzer.analyze()

        assert Decimal(result["total_realized_pnl"]) == Decimal("0")
        assert Decimal(result["short_term_gains"]) == Decimal("0")
        assert Decimal(result["long_term_gains"]) == Decimal("0")
        assert Decimal(result["estimated_capital_gains_tax"]) == Decimal("0")
        assert Decimal(result["phantom_income_total"]) == Decimal("0")
        assert len(result["phantom_income_by_position"]) == 0
        assert Decimal(result["total_estimated_tax"]) == Decimal("0")

    def test_disclaimer_present(self, empty_account):
        analyzer = TaxAnalyzer(account=empty_account)
        result = analyzer.analyze()
        assert "disclaimer" in result
        assert "estimate" in result["disclaimer"].lower()

    def test_trade_without_open_date(self):
        """Trade with None open_date should not count as short or long term."""
        trade = Trade(
            account_id="U1234567",
            trade_id="NOOPEN",
            trade_date=date(2025, 1, 10),
            settle_date=date(2025, 1, 12),
            open_date=None,
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.SELL,
            quantity=Decimal("10"),
            trade_price=Decimal("160"),
            trade_money=Decimal("1600"),
            ib_commission=Decimal("-1.00"),
            fifo_pnl_realized=Decimal("300"),
        )
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=[trade],
            positions=[],
        )
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=account)
        result = analyzer.analyze()

        # total_realized_pnl includes it
        assert Decimal(result["total_realized_pnl"]) == Decimal("300")
        # but not classified as short or long term (no open_date)
        assert Decimal(result["short_term_gains"]) == Decimal("0")
        assert Decimal(result["long_term_gains"]) == Decimal("0")

    def test_phantom_income_by_position_details(self, mixed_tax_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=mixed_tax_account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        detail = result["phantom_income_by_position"][0]
        assert detail["symbol"] == "US912810SJ88"
        assert detail["description"] == "US T-BOND STRIPS 2035"
        assert Decimal(detail["face_value"]) == Decimal("10000")
        assert Decimal(detail["cost_basis"]) == Decimal("6000")
        assert detail["maturity_date"] == "2035-01-15"
        assert Decimal(detail["years_to_maturity"]) > Decimal("0")
        assert detail["days_held_this_year"] == 365
        assert Decimal(detail["estimated_tax"]) > Decimal("0")

    def test_decimal_precision(self, mixed_tax_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=mixed_tax_account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        numeric_keys = [
            "tax_rate",
            "total_realized_pnl",
            "short_term_gains",
            "long_term_gains",
            "estimated_capital_gains_tax",
            "phantom_income_total",
            "estimated_phantom_income_tax",
            "total_estimated_tax",
        ]
        for key in numeric_keys:
            value_str = result[key]
            parsed = Decimal(value_str)
            reparsed = str(parsed)
            assert "000000001" not in reparsed

    def test_multiple_bond_positions(
        self, zero_coupon_bond_position, coupon_bond_position, bond_no_maturity
    ):
        """Only zero-coupon bonds with maturity should generate phantom income."""
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            trades=[],
            positions=[
                zero_coupon_bond_position,
                coupon_bond_position,
                bond_no_maturity,
            ],
        )
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.25"), account=account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        # Only the zero-coupon bond with maturity should appear
        assert len(result["phantom_income_by_position"]) == 1
        assert result["phantom_income_by_position"][0]["symbol"] == "US912810SJ88"

    def test_zero_tax_rate(self, mixed_tax_account):
        analyzer = TaxAnalyzer(tax_rate=Decimal("0"), account=mixed_tax_account)
        mock_date = _mock_date_today(date(2025, 6, 15))
        with patch("ib_sec_mcp.analyzers.tax.date", mock_date):
            result = analyzer.analyze()

        assert Decimal(result["estimated_capital_gains_tax"]) == Decimal("0")
        assert Decimal(result["estimated_phantom_income_tax"]) == Decimal("0")
        assert Decimal(result["total_estimated_tax"]) == Decimal("0")

    @pytest.mark.parametrize(
        ("holding_days", "expected_short", "expected_long"),
        [
            (364, Decimal("400"), Decimal("0")),  # 364 days < 365 => short-term
            (365, Decimal("0"), Decimal("400")),  # exactly 365 days >= 365 => long-term
            (366, Decimal("0"), Decimal("400")),  # 366 days >= 365 => long-term
        ],
        ids=["364d-short-term", "365d-long-term", "366d-long-term"],
    )
    def test_holding_period_boundary(self, holding_days, expected_short, expected_long):
        """Test holding period boundary classification around 365-day threshold."""
        trade_date = date(2026, 1, 10)
        open_date = trade_date - timedelta(days=holding_days)
        trade = Trade(
            account_id="U1234567",
            trade_id="BOUNDARY",
            trade_date=trade_date,
            settle_date=date(2026, 1, 12),
            open_date=open_date,
            symbol="AAPL",
            asset_class=AssetClass.STOCK,
            buy_sell=BuySell.SELL,
            quantity=Decimal("10"),
            trade_price=Decimal("180"),
            trade_money=Decimal("1800"),
            ib_commission=Decimal("-1.00"),
            fifo_pnl_realized=Decimal("400"),
        )
        account = Account(
            account_id="U1234567",
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
            trades=[trade],
            positions=[],
        )
        analyzer = TaxAnalyzer(tax_rate=Decimal("0.30"), account=account)
        result = analyzer.analyze()

        assert Decimal(result["short_term_gains"]) == expected_short
        assert Decimal(result["long_term_gains"]) == expected_long

    def test_no_account_raises(self):
        with pytest.raises(ValueError, match="Either portfolio or account"):
            TaxAnalyzer(tax_rate=Decimal("0.30"))
