"""Tests for risk analyzer"""

from datetime import date
from decimal import Decimal

import pytest

from ib_sec_mcp.analyzers.risk import RiskAnalyzer
from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass


@pytest.fixture
def bond_position_with_maturity():
    """Bond position with a maturity date for interest rate scenarios."""
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
def bond_position_no_maturity():
    """Bond position without maturity date (skipped in rate scenarios)."""
    return Position(
        account_id="U1234567",
        symbol="UNKNOWN_BOND",
        description="BOND NO MATURITY",
        asset_class=AssetClass.BOND,
        quantity=Decimal("5000"),
        mark_price=Decimal("80"),
        position_value=Decimal("4000"),
        average_cost=Decimal("75"),
        cost_basis=Decimal("3750"),
        unrealized_pnl=Decimal("250"),
        currency="USD",
        fx_rate_to_base=Decimal("1"),
        position_date=date(2025, 1, 31),
        maturity_date=None,
    )


@pytest.fixture
def stock_position_large():
    """A large stock position for concentration tests."""
    return Position(
        account_id="U1234567",
        symbol="AAPL",
        description="Apple Inc",
        asset_class=AssetClass.STOCK,
        quantity=Decimal("100"),
        mark_price=Decimal("150"),
        position_value=Decimal("15000"),
        average_cost=Decimal("120"),
        cost_basis=Decimal("12000"),
        unrealized_pnl=Decimal("3000"),
        currency="USD",
        fx_rate_to_base=Decimal("1"),
        position_date=date(2025, 1, 31),
    )


@pytest.fixture
def stock_position_small():
    """A small stock position for concentration tests."""
    return Position(
        account_id="U1234567",
        symbol="MSFT",
        description="Microsoft Corp",
        asset_class=AssetClass.STOCK,
        quantity=Decimal("10"),
        mark_price=Decimal("400"),
        position_value=Decimal("4000"),
        average_cost=Decimal("350"),
        cost_basis=Decimal("3500"),
        unrealized_pnl=Decimal("500"),
        currency="USD",
        fx_rate_to_base=Decimal("1"),
        position_date=date(2025, 1, 31),
    )


@pytest.fixture
def bond_account(bond_position_with_maturity):
    """Account with a single bond position."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        positions=[bond_position_with_maturity],
        trades=[],
    )


@pytest.fixture
def mixed_account(bond_position_with_maturity, stock_position_large, stock_position_small):
    """Account with bonds and stocks."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        positions=[
            bond_position_with_maturity,
            stock_position_large,
            stock_position_small,
        ],
        trades=[],
    )


@pytest.fixture
def empty_account():
    """Account with no positions."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        positions=[],
        trades=[],
    )


@pytest.fixture
def stock_only_account(stock_position_large, stock_position_small):
    """Account with only stock positions (no bonds)."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        positions=[stock_position_large, stock_position_small],
        trades=[],
    )


class TestRiskAnalyzer:
    """Tests for RiskAnalyzer."""

    def test_analyzer_name(self, bond_account):
        analyzer = RiskAnalyzer(account=bond_account)
        result = analyzer.analyze()
        assert result["analyzer"] == "Risk"

    def test_has_bond_exposure_true(self, bond_account):
        analyzer = RiskAnalyzer(account=bond_account)
        result = analyzer.analyze()

        assert result["has_bond_exposure"] is True
        assert result["bond_count"] == 1

    def test_has_bond_exposure_false(self, stock_only_account):
        analyzer = RiskAnalyzer(account=stock_only_account)
        result = analyzer.analyze()

        assert result["has_bond_exposure"] is False
        assert result["bond_count"] == 0
        assert result["interest_rate_scenarios"] == {}

    def test_interest_rate_scenarios_structure(self, bond_account):
        analyzer = RiskAnalyzer(account=bond_account)
        result = analyzer.analyze()

        scenarios = result["interest_rate_scenarios"]
        assert "scenarios" in scenarios

        scenario_list = scenarios["scenarios"]
        assert len(scenario_list) == 7  # -3%, -2%, -1%, 0%, +1%, +2%, +3%

        rate_changes = [s["rate_change"] for s in scenario_list]
        assert rate_changes == ["-3.0", "-2.0", "-1.0", "0.0", "1.0", "2.0", "3.0"]

    def test_interest_rate_scenario_names(self, bond_account):
        analyzer = RiskAnalyzer(account=bond_account)
        result = analyzer.analyze()

        scenarios = result["interest_rate_scenarios"]["scenarios"]
        scenario_names = [s["scenario"] for s in scenarios]
        assert "No Change" in scenario_names
        assert "-3.0%" in scenario_names
        assert "+1.0%" in scenario_names
        assert "+3.0%" in scenario_names

    def test_no_change_scenario_zero_impact(self, bond_account):
        analyzer = RiskAnalyzer(account=bond_account)
        result = analyzer.analyze()

        scenarios = result["interest_rate_scenarios"]["scenarios"]
        no_change = next(s for s in scenarios if s["scenario"] == "No Change")

        assert Decimal(no_change["total_value_change"]) == Decimal("0")

    def test_positive_rate_change_negative_price(self, bond_account):
        """Rising rates should decrease bond prices."""
        analyzer = RiskAnalyzer(account=bond_account)
        result = analyzer.analyze()

        scenarios = result["interest_rate_scenarios"]["scenarios"]
        plus_1 = next(s for s in scenarios if s["rate_change"] == "1.0")

        assert Decimal(plus_1["total_value_change"]) < Decimal("0")

    def test_negative_rate_change_positive_price(self, bond_account):
        """Falling rates should increase bond prices."""
        analyzer = RiskAnalyzer(account=bond_account)
        result = analyzer.analyze()

        scenarios = result["interest_rate_scenarios"]["scenarios"]
        minus_1 = next(s for s in scenarios if s["rate_change"] == "-1.0")

        assert Decimal(minus_1["total_value_change"]) > Decimal("0")

    def test_rate_scenario_position_details(self, bond_account):
        analyzer = RiskAnalyzer(account=bond_account)
        result = analyzer.analyze()

        scenarios = result["interest_rate_scenarios"]["scenarios"]
        plus_1 = next(s for s in scenarios if s["rate_change"] == "1.0")

        positions = plus_1["positions"]
        assert len(positions) == 1
        assert positions[0]["symbol"] == "US912810SJ88"
        assert "current_value" in positions[0]
        assert "new_value" in positions[0]
        assert "change" in positions[0]
        assert "change_pct" in positions[0]

    def test_bond_without_maturity_skipped_in_scenarios(
        self, bond_position_with_maturity, bond_position_no_maturity
    ):
        """Bonds without maturity date are skipped in rate scenarios."""
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            positions=[bond_position_with_maturity, bond_position_no_maturity],
            trades=[],
        )
        analyzer = RiskAnalyzer(account=account)
        result = analyzer.analyze()

        # Both are bond positions
        assert result["bond_count"] == 2

        # But only the one with maturity shows up in scenario details
        scenarios = result["interest_rate_scenarios"]["scenarios"]
        plus_1 = next(s for s in scenarios if s["rate_change"] == "1.0")
        assert len(plus_1["positions"]) == 1
        assert plus_1["positions"][0]["symbol"] == "US912810SJ88"

    def test_rate_scenario_price_change_calculation(self, bond_account):
        """Verify price change formula: new = cur + cur * (-dur * dy/100)."""
        analyzer = RiskAnalyzer(account=bond_account)
        result = analyzer.analyze()

        scenarios = result["interest_rate_scenarios"]["scenarios"]
        plus_2 = next(s for s in scenarios if s["rate_change"] == "2.0")

        pos = plus_2["positions"][0]
        current_value = Decimal(pos["current_value"])
        new_value = Decimal(pos["new_value"])
        change = Decimal(pos["change"])

        # maturity: 2035-01-15, position_date: 2025-01-31
        # years_to_maturity = (2035-01-15 - 2025-01-31).days / 365.25
        days = (date(2035, 1, 15) - date(2025, 1, 31)).days
        years = Decimal(days) / Decimal("365.25")
        # new_price = current + current * (-years * 2.0/100)
        expected_change = current_value * (-years * (Decimal("2.0") / Decimal("100")))
        expected_new = current_value + expected_change

        assert new_value == expected_new
        assert change == expected_change

    def test_concentration_top_positions(self, mixed_account):
        analyzer = RiskAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        concentration = result["concentration"]
        top_positions = concentration["top_positions"]

        # Should be sorted by value descending
        assert len(top_positions) == 3
        # Largest first: AAPL (15000), then bond (6550), then MSFT (4000)
        assert top_positions[0]["symbol"] == "AAPL"
        assert top_positions[1]["symbol"] == "US912810SJ88"
        assert top_positions[2]["symbol"] == "MSFT"

    def test_concentration_allocation_pct(self, mixed_account):
        analyzer = RiskAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        concentration = result["concentration"]
        top_positions = concentration["top_positions"]

        # total_value = total_cash(0) + total_position_value(15000+6550+4000=25550)
        total_value = Decimal("25550")

        aapl_pct = Decimal(top_positions[0]["allocation_pct"])
        expected_aapl = (Decimal("15000") / total_value) * 100
        assert aapl_pct == expected_aapl

    def test_concentration_max(self, mixed_account):
        analyzer = RiskAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        concentration = result["concentration"]
        max_conc = Decimal(concentration["max_concentration"])

        total_value = Decimal("25550")
        expected_max = (Decimal("15000") / total_value) * 100
        assert max_conc == expected_max

    def test_concentration_empty_portfolio(self, empty_account):
        analyzer = RiskAnalyzer(account=empty_account)
        result = analyzer.analyze()

        concentration = result["concentration"]
        assert concentration["top_positions"] == []
        assert concentration["max_concentration"] == "0"

    def test_concentration_with_cash(self, stock_position_large):
        """Cash included in total_value via account.total_value."""
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            positions=[stock_position_large],
            cash_balances=[
                CashBalance(
                    currency="USD",
                    starting_cash=Decimal("5000"),
                    ending_cash=Decimal("5000"),
                    ending_settled_cash=Decimal("5000"),
                ),
            ],
            trades=[],
        )
        analyzer = RiskAnalyzer(account=account)
        result = analyzer.analyze()

        concentration = result["concentration"]
        top = concentration["top_positions"]
        # total_value = 5000 (cash) + 15000 (position) = 20000
        total_value = Decimal("20000")
        aapl_pct = Decimal(top[0]["allocation_pct"])
        expected = (Decimal("15000") / total_value) * 100
        assert aapl_pct == expected

    def test_concentration_top_10_limit(self):
        """Only top 10 positions returned even with more."""
        positions = [
            Position(
                account_id="U1234567",
                symbol=f"SYM{i:02d}",
                description=f"Symbol {i}",
                asset_class=AssetClass.STOCK,
                quantity=Decimal("10"),
                mark_price=Decimal(str(100 + i)),
                position_value=Decimal(str(1000 + i * 100)),
                average_cost=Decimal("90"),
                cost_basis=Decimal("900"),
                unrealized_pnl=Decimal(str(100 + i * 100)),
                currency="USD",
                fx_rate_to_base=Decimal("1"),
                position_date=date(2025, 1, 31),
            )
            for i in range(15)
        ]
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            positions=positions,
            trades=[],
        )
        analyzer = RiskAnalyzer(account=account)
        result = analyzer.analyze()

        assert len(result["concentration"]["top_positions"]) == 10

    def test_decimal_precision(self, mixed_account):
        analyzer = RiskAnalyzer(account=mixed_account)
        result = analyzer.analyze()

        # Check scenario values
        scenarios = result["interest_rate_scenarios"]["scenarios"]
        for scenario in scenarios:
            Decimal(scenario["total_value_change"])
            Decimal(scenario["rate_change"])
            for pos in scenario["positions"]:
                value_str = pos["change"]
                parsed = Decimal(value_str)
                reparsed = str(parsed)
                assert "000000001" not in reparsed

        # Check concentration values
        for pos in result["concentration"]["top_positions"]:
            Decimal(pos["value"])
            parsed = Decimal(pos["allocation_pct"])
            reparsed = str(parsed)
            assert "000000001" not in reparsed

    def test_single_position_concentration(self, stock_position_large):
        """Single position should be 100% concentration."""
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            positions=[stock_position_large],
            trades=[],
        )
        analyzer = RiskAnalyzer(account=account)
        result = analyzer.analyze()

        concentration = result["concentration"]
        assert len(concentration["top_positions"]) == 1
        assert Decimal(concentration["max_concentration"]) == Decimal("100")
        assert Decimal(concentration["top_positions"][0]["allocation_pct"]) == Decimal("100")

    def test_metadata_fields(self, bond_account):
        analyzer = RiskAnalyzer(account=bond_account)
        result = analyzer.analyze()

        assert result["account_id"] == "U1234567"
        assert result["from_date"] == "2025-01-01"
        assert result["to_date"] == "2025-01-31"
        assert result["is_multi_account"] is False

    def test_no_account_raises(self):
        with pytest.raises(ValueError, match="Either portfolio or account"):
            RiskAnalyzer()
