"""Tests for the pure ETF swap calculation logic.

Covers ``ETFSwapCalculator`` (single + portfolio swaps) and ``validate_etf_price``.
All calculations are Decimal-based; these tests guard arithmetic correctness and
the payback-period edge cases (no benefit -> infinity).
"""

from decimal import Decimal

import pytest

from ib_sec_mcp.tools.etf_calculator import (
    ETFSwapCalculator,
    SwapCalculation,
    validate_etf_price,
)

# A realistic TLT -> IDTL swap (lower withholding tax, lower expense ratio).
SWAP_KWARGS = {
    "from_symbol": "TLT",
    "from_shares": 200,
    "from_price": Decimal("91.34"),
    "from_expense_ratio": Decimal("0.0015"),
    "from_dividend_yield": Decimal("0.0433"),
    "from_withholding_tax": Decimal("0.30"),
    "to_symbol": "IDTL",
    "to_price": Decimal("3.40"),
    "to_expense_ratio": Decimal("0.0007"),
    "to_dividend_yield": Decimal("0.0445"),
    "to_withholding_tax": Decimal("0.15"),
}


class TestCalculateSwap:
    def test_required_shares_rounded_half_up(self) -> None:
        calc = ETFSwapCalculator().calculate_swap(**SWAP_KWARGS)
        # from_total = 200 * 91.34 = 18268.00 ; 18268.00 / 3.40 = 5372.94 -> 5373
        assert calc.required_shares == 5373

    def test_purchase_amount_and_surplus_are_exact_decimal(self) -> None:
        calc = ETFSwapCalculator().calculate_swap(**SWAP_KWARGS)
        assert calc.purchase_amount == Decimal("18268.20")  # 5373 * 3.40
        assert calc.from_etf.total_value == Decimal("18268.00")  # 200 * 91.34
        assert calc.surplus_cash == Decimal("-0.20")  # from_total - purchase

    def test_positive_net_benefit_gives_finite_payback(self) -> None:
        calc = ETFSwapCalculator().calculate_swap(**SWAP_KWARGS)
        assert calc.annual_net_benefit > 0
        assert calc.payback_period_months != float("inf")
        assert calc.payback_period_months > 0

    def test_financial_fields_are_decimal(self) -> None:
        calc = ETFSwapCalculator().calculate_swap(**SWAP_KWARGS)
        assert isinstance(calc.purchase_amount, Decimal)
        assert isinstance(calc.surplus_cash, Decimal)
        assert isinstance(calc.annual_withholding_tax_savings, Decimal)
        assert isinstance(calc.annual_net_benefit, Decimal)

    def test_no_benefit_swap_returns_infinite_payback(self) -> None:
        """A swap into a worse ETF (higher tax + higher expense) yields no benefit."""
        calc = ETFSwapCalculator().calculate_swap(
            from_symbol="GOOD",
            from_shares=100,
            from_price=Decimal("100"),
            from_expense_ratio=Decimal("0.0003"),
            from_dividend_yield=Decimal("0.02"),
            from_withholding_tax=Decimal("0.00"),
            to_symbol="BAD",
            to_price=Decimal("100"),
            to_expense_ratio=Decimal("0.0015"),
            to_dividend_yield=Decimal("0.02"),
            to_withholding_tax=Decimal("0.30"),
        )
        assert calc.annual_net_benefit <= 0
        assert calc.payback_period_months == float("inf")

    def test_custom_trading_fee_changes_payback(self) -> None:
        cheap = ETFSwapCalculator(trading_fee_usd=Decimal("10")).calculate_swap(**SWAP_KWARGS)
        pricey = ETFSwapCalculator(trading_fee_usd=Decimal("150")).calculate_swap(**SWAP_KWARGS)
        # Higher trading fee => longer payback period.
        assert pricey.payback_period_months > cheap.payback_period_months


class TestFormatCalculationResult:
    def test_format_includes_symbols_and_shares(self) -> None:
        calc = ETFSwapCalculator().calculate_swap(**SWAP_KWARGS)
        out = ETFSwapCalculator().format_calculation_result(calc)
        assert "TLT" in out
        assert "IDTL" in out
        assert "5,373" in out  # required shares, formatted with thousands separator

    def test_format_infinite_payback_message(self) -> None:
        calc = ETFSwapCalculator().calculate_swap(
            from_symbol="GOOD",
            from_shares=100,
            from_price=Decimal("100"),
            from_expense_ratio=Decimal("0.0003"),
            from_dividend_yield=Decimal("0.02"),
            from_withholding_tax=Decimal("0.00"),
            to_symbol="BAD",
            to_price=Decimal("100"),
            to_expense_ratio=Decimal("0.0015"),
            to_dividend_yield=Decimal("0.02"),
            to_withholding_tax=Decimal("0.30"),
        )
        out = ETFSwapCalculator().format_calculation_result(calc)
        assert "メリットなし" in out


class TestCalculatePortfolioSwap:
    def test_summary_aggregates_individual_swaps(self) -> None:
        swaps = [
            {
                "from_symbol": "TLT",
                "from_shares": 200,
                "from_price": 91.34,
                "from_expense_ratio": 0.0015,
                "from_dividend_yield": 0.0433,
                "from_withholding_tax": 0.30,
                "to_symbol": "IDTL",
                "to_price": 3.40,
                "to_expense_ratio": 0.0007,
                "to_dividend_yield": 0.0445,
                "to_withholding_tax": 0.15,
            },
            {
                "from_symbol": "VOO",
                "from_shares": 40,
                "from_price": 607.39,
                "from_expense_ratio": 0.0003,
                "from_dividend_yield": 0.0115,
                "from_withholding_tax": 0.30,
                "to_symbol": "CSPX",
                "to_price": 714.78,
                "to_expense_ratio": 0.0007,
                "to_dividend_yield": 0.0115,
                "to_withholding_tax": 0.00,
            },
        ]
        result = ETFSwapCalculator().calculate_portfolio_swap(swaps)

        assert len(result["individual_results"]) == 2
        assert all(isinstance(c, SwapCalculation) for c in result["individual_results"])

        summary = result["summary"]
        assert summary["total_from_shares"] == 240  # 200 + 40
        assert summary["total_to_shares"] == (
            result["individual_results"][0].required_shares
            + result["individual_results"][1].required_shares
        )
        assert summary["trading_fee"] == 75.0
        # Net benefit should equal savings minus expense change.
        assert summary["annual_net_benefit"] == pytest.approx(
            summary["annual_withholding_savings"] - summary["annual_expense_change"]
        )

    def test_empty_portfolio_has_zero_totals_and_infinite_payback(self) -> None:
        result = ETFSwapCalculator().calculate_portfolio_swap([])
        assert result["individual_results"] == []
        assert result["summary"]["total_from_shares"] == 0
        assert result["summary"]["payback_period_months"] == float("inf")


class TestValidateEtfPrice:
    def test_normal_price_is_valid_no_warnings(self) -> None:
        result = validate_etf_price("CSPX", Decimal("700.00"))
        assert result["is_valid"] is True
        assert result["warnings"] == []

    def test_low_price_warns_and_is_invalid(self) -> None:
        result = validate_etf_price("PENNY", Decimal("0.50"))
        assert result["is_valid"] is False
        assert any("⚠️" in w for w in result["warnings"])

    def test_high_price_warns(self) -> None:
        result = validate_etf_price("EXPENSIVE", Decimal("1500.00"))
        assert result["is_valid"] is False
        assert any("⚠️" in w for w in result["warnings"])

    def test_reference_ratio_extreme_flags_error(self) -> None:
        # 200x the reference price -> data error warning (⚠️).
        result = validate_etf_price(
            "WEIRD",
            Decimal("200.00"),
            reference_symbol="REF",
            reference_price=Decimal("1.00"),
        )
        assert result["price_ratio"] == 200.0
        assert result["is_valid"] is False

    def test_reference_ratio_informational_only(self) -> None:
        # 0.3x ratio (different per-share design) -> informational (ℹ️) note, still valid.
        result = validate_etf_price(
            "DESIGN",
            Decimal("30.00"),
            reference_symbol="REF",
            reference_price=Decimal("100.00"),
        )
        assert result["is_valid"] is True
        assert any("ℹ️" in w for w in result["warnings"])
