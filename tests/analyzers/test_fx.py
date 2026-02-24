"""Tests for FX exposure analyzer"""

from datetime import date
from decimal import Decimal

import pytest

from ib_sec_mcp.analyzers.fx import (
    FXExposureAnalyzer,
)
from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass


@pytest.fixture
def multi_currency_positions() -> list[Position]:
    """Positions in multiple currencies."""
    return [
        Position(
            account_id="U1234567",
            symbol="CSPX",
            description="ISHARES CORE S&P 500",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("10"),
            mark_price=Decimal("735"),
            position_value=Decimal("7350"),
            average_cost=Decimal("600"),
            cost_basis=Decimal("6000"),
            unrealized_pnl=Decimal("1350"),
            currency="USD",
            fx_rate_to_base=Decimal("1"),
            position_date=date(2025, 1, 31),
        ),
        Position(
            account_id="U1234567",
            symbol="9433.T",
            description="KDDI CORPORATION",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("100"),
            mark_price=Decimal("5000"),
            position_value=Decimal("3273.50"),
            average_cost=Decimal("4500"),
            cost_basis=Decimal("2946.15"),
            unrealized_pnl=Decimal("327.35"),
            currency="JPY",
            fx_rate_to_base=Decimal("0.006547"),
            position_date=date(2025, 1, 31),
        ),
        Position(
            account_id="U1234567",
            symbol="IDTL",
            description="ISHARES USD TRES 20PLUS YR",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("100"),
            mark_price=Decimal("3.20"),
            position_value=Decimal("406.40"),
            average_cost=Decimal("3.00"),
            cost_basis=Decimal("381"),
            unrealized_pnl=Decimal("25.40"),
            currency="GBP",
            fx_rate_to_base=Decimal("1.27"),
            position_date=date(2025, 1, 31),
        ),
    ]


@pytest.fixture
def multi_currency_cash() -> list[CashBalance]:
    """Cash balances in multiple currencies."""
    return [
        CashBalance(
            currency="BASE_SUMMARY",
            starting_cash=Decimal("10000"),
            ending_cash=Decimal("10000"),
            ending_settled_cash=Decimal("10000"),
        ),
        CashBalance(
            currency="USD",
            starting_cash=Decimal("5000"),
            ending_cash=Decimal("5000"),
            ending_settled_cash=Decimal("5000"),
        ),
        CashBalance(
            currency="JPY",
            starting_cash=Decimal("100000"),
            ending_cash=Decimal("100000"),
            ending_settled_cash=Decimal("100000"),
        ),
    ]


@pytest.fixture
def multi_currency_account(
    multi_currency_positions: list[Position],
    multi_currency_cash: list[CashBalance],
) -> Account:
    """Account with multi-currency positions and cash."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        positions=multi_currency_positions,
        cash_balances=multi_currency_cash,
        base_currency="USD",
    )


@pytest.fixture
def usd_only_account() -> Account:
    """Account with only USD positions."""
    positions = [
        Position(
            account_id="U1234567",
            symbol="AAPL",
            description="Apple Inc",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("10"),
            mark_price=Decimal("150"),
            position_value=Decimal("1500"),
            average_cost=Decimal("120"),
            cost_basis=Decimal("1200"),
            unrealized_pnl=Decimal("300"),
            currency="USD",
            fx_rate_to_base=Decimal("1"),
            position_date=date(2025, 1, 31),
        ),
    ]
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        positions=positions,
        cash_balances=[
            CashBalance(
                currency="USD",
                starting_cash=Decimal("5000"),
                ending_cash=Decimal("5000"),
                ending_settled_cash=Decimal("5000"),
            ),
        ],
        base_currency="USD",
    )


class TestFXExposureAnalyzer:
    """Tests for FXExposureAnalyzer."""

    def test_multi_currency_exposure(self, multi_currency_account):
        """Test FX exposure calculation for multi-currency portfolio."""
        analyzer = FXExposureAnalyzer(account=multi_currency_account)
        result = analyzer.analyze()

        assert result["analyzer"] == "FXExposure"
        exposures = result["currency_exposures"]
        assert "USD" in exposures
        assert "JPY" in exposures
        assert "GBP" in exposures

        # USD should be marked as base currency
        assert exposures["USD"]["is_base_currency"] is True
        assert exposures["JPY"]["is_base_currency"] is False
        assert exposures["GBP"]["is_base_currency"] is False

    def test_exposure_percentages_sum_to_100(self, multi_currency_account):
        """Test that exposure percentages approximately sum to 100."""
        analyzer = FXExposureAnalyzer(account=multi_currency_account)
        result = analyzer.analyze()

        total_pct = sum(
            Decimal(data["percentage"]) for data in result["currency_exposures"].values()
        )
        # Allow small rounding tolerance
        assert abs(total_pct - Decimal("100")) < Decimal("1")

    def test_fx_scenario_simulation(self, multi_currency_account):
        """Test +/-10% FX scenario simulation."""
        analyzer = FXExposureAnalyzer(account=multi_currency_account)
        result = analyzer.analyze()

        scenarios = result["scenarios"]
        assert "by_currency" in scenarios
        assert "aggregate" in scenarios

        # Base currency (USD) should not be in scenarios
        assert "USD" not in scenarios["by_currency"]

        # JPY and GBP should have scenarios
        assert "JPY" in scenarios["by_currency"]
        assert "GBP" in scenarios["by_currency"]

        # Check scenario structure
        jpy_scenario = scenarios["by_currency"]["JPY"]
        assert "+10%" in jpy_scenario
        assert "-10%" in jpy_scenario

    def test_custom_scenario_percentage(self, multi_currency_account):
        """Test custom FX scenario percentage."""
        analyzer = FXExposureAnalyzer(
            account=multi_currency_account,
            fx_scenario_pct=Decimal("15"),
        )
        result = analyzer.analyze()

        assert result["fx_scenario_pct"] == "15"
        scenarios = result["scenarios"]["by_currency"]
        if "JPY" in scenarios:
            assert "+15%" in scenarios["JPY"]
            assert "-15%" in scenarios["JPY"]

    def test_scenario_impact_calculation(self, multi_currency_account):
        """Test that scenario impact values are correct."""
        analyzer = FXExposureAnalyzer(
            account=multi_currency_account,
            fx_scenario_pct=Decimal("10"),
        )
        result = analyzer.analyze()

        # For JPY: exposure = 3273.50 (position) + cash_base
        jpy_scenario = result["scenarios"]["by_currency"]["JPY"]

        exposure = Decimal(jpy_scenario["exposure_base"])
        positive_impact = Decimal(jpy_scenario["+10%"]["impact_base"])
        negative_impact = Decimal(jpy_scenario["-10%"]["impact_base"])

        # +10% impact should be 10% of exposure
        assert positive_impact == exposure * Decimal("0.10")
        # -10% impact should be -10% of exposure
        assert negative_impact == exposure * Decimal("-0.10")

    def test_usd_only_portfolio(self, usd_only_account):
        """Test with only USD positions (no FX risk)."""
        analyzer = FXExposureAnalyzer(account=usd_only_account)
        result = analyzer.analyze()

        exposures = result["currency_exposures"]
        assert "USD" in exposures
        assert len(exposures) == 1

        # No non-base currency scenarios
        assert result["scenarios"]["by_currency"] == {}

        # Aggregate should be zero
        agg = result["scenarios"]["aggregate"]
        assert Decimal(agg["+10%"]["total_impact_base"]) == Decimal("0")

    def test_hedge_recommendations_high_exposure(self):
        """Test hedge recommendations for highly concentrated FX exposure."""
        positions = [
            Position(
                account_id="U1234567",
                symbol="9433.T",
                description="KDDI CORPORATION",
                asset_class=AssetClass.STOCK,
                quantity=Decimal("1000"),
                mark_price=Decimal("5000"),
                position_value=Decimal("32735"),
                average_cost=Decimal("4500"),
                cost_basis=Decimal("29461"),
                unrealized_pnl=Decimal("3274"),
                currency="JPY",
                fx_rate_to_base=Decimal("0.006547"),
                position_date=date(2025, 1, 31),
            ),
            Position(
                account_id="U1234567",
                symbol="AAPL",
                description="Apple Inc",
                asset_class=AssetClass.STOCK,
                quantity=Decimal("10"),
                mark_price=Decimal("150"),
                position_value=Decimal("1500"),
                average_cost=Decimal("120"),
                cost_basis=Decimal("1200"),
                unrealized_pnl=Decimal("300"),
                currency="USD",
                fx_rate_to_base=Decimal("1"),
                position_date=date(2025, 1, 31),
            ),
        ]
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            positions=positions,
            cash_balances=[],
            base_currency="USD",
        )
        analyzer = FXExposureAnalyzer(account=account)
        result = analyzer.analyze()

        recs = result["hedge_recommendations"]
        jpy_rec = next((r for r in recs if r["currency"] == "JPY"), None)
        assert jpy_rec is not None
        assert jpy_rec["risk_level"] == "HIGH"

    def test_hedge_recommendations_low_exposure(self, usd_only_account):
        """Test hedge recommendations when no FX exposure."""
        analyzer = FXExposureAnalyzer(account=usd_only_account)
        result = analyzer.analyze()

        recs = result["hedge_recommendations"]
        assert len(recs) == 1
        assert recs[0]["risk_level"] == "LOW"

    def test_empty_account(self):
        """Test with no positions or cash."""
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            positions=[],
            cash_balances=[],
            base_currency="USD",
        )
        analyzer = FXExposureAnalyzer(account=account)
        result = analyzer.analyze()

        assert result["currency_exposures"] == {}
        assert result["total_value"] == "0"

    def test_base_summary_excluded_from_cash(self, multi_currency_account):
        """Test that BASE_SUMMARY cash balance is excluded."""
        analyzer = FXExposureAnalyzer(account=multi_currency_account)
        result = analyzer.analyze()

        # BASE_SUMMARY should not appear as a currency
        assert "BASE_SUMMARY" not in result["currency_exposures"]

    def test_decimal_precision(self, multi_currency_account):
        """Test that all values use Decimal precision (no float artifacts)."""
        analyzer = FXExposureAnalyzer(account=multi_currency_account)
        result = analyzer.analyze()

        # Check that values can be parsed back to Decimal without precision issues
        for _currency, data in result["currency_exposures"].items():
            Decimal(data["position_value_base"])
            Decimal(data["percentage"])
            Decimal(data["fx_rate_to_base"])

    def test_includes_cash_in_exposure(self, multi_currency_account):
        """Test that cash balances are included in currency exposure."""
        analyzer = FXExposureAnalyzer(account=multi_currency_account)
        result = analyzer.analyze()

        jpy = result["currency_exposures"]["JPY"]
        # JPY has position (3273.50 in base) and cash (100000 local)
        assert Decimal(jpy["cash_value_local"]) == Decimal("100000")
        assert Decimal(jpy["position_value_base"]) == Decimal("3273.50")
        # Cash converted to base: 100000 * 0.006547 = 654.70
        cash_base = Decimal(jpy["cash_value_base"])
        assert cash_base == Decimal("100000") * Decimal("0.006547")
        total = Decimal(jpy["total_exposure_base"])
        assert total == Decimal("3273.50") + cash_base
