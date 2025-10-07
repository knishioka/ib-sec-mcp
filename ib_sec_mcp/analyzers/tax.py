"""Tax liability analyzer"""

from datetime import date
from decimal import Decimal

from ib_sec_mcp.analyzers.base import AnalysisResult, BaseAnalyzer
from ib_sec_mcp.core.calculator import PerformanceCalculator
from ib_sec_mcp.models.trade import AssetClass


class TaxAnalyzer(BaseAnalyzer):
    """
    Analyze tax liabilities

    Focuses on phantom income (OID) for zero-coupon bonds
    """

    def __init__(self, tax_rate: Decimal = Decimal("0.30"), **kwargs):
        """
        Initialize tax analyzer

        Args:
            tax_rate: Marginal tax rate (default 30%)
            **kwargs: Passed to BaseAnalyzer
        """
        super().__init__(**kwargs)
        self.tax_rate = tax_rate

    def analyze(self) -> AnalysisResult:
        """
        Run tax analysis

        Returns:
            AnalysisResult with tax metrics
        """
        trades = self.get_trades()
        positions = self.get_positions()

        # Realized gains/losses (capital gains tax)
        total_realized_pnl = sum(t.fifo_pnl_realized for t in trades)
        short_term_gains = sum(
            t.fifo_pnl_realized
            for t in trades
            if t.fifo_pnl_realized > 0
            and t.settle_date
            and (t.settle_date - t.trade_date).days <= 365
        )
        long_term_gains = sum(
            t.fifo_pnl_realized
            for t in trades
            if t.fifo_pnl_realized > 0
            and t.settle_date
            and (t.settle_date - t.trade_date).days > 365
        )

        # Phantom income (OID) for zero-coupon bonds
        bond_positions = [p for p in positions if p.asset_class == AssetClass.BOND]
        phantom_income_analysis = self._analyze_phantom_income(bond_positions)

        # Estimated tax liabilities
        capital_gains_tax = (
            total_realized_pnl * self.tax_rate if total_realized_pnl > 0 else Decimal("0")
        )
        phantom_income_tax = phantom_income_analysis["total_phantom_income"] * self.tax_rate

        total_estimated_tax = capital_gains_tax + phantom_income_tax

        return self._create_result(
            tax_rate=str(self.tax_rate),
            # Capital gains
            total_realized_pnl=str(total_realized_pnl),
            short_term_gains=str(short_term_gains),
            long_term_gains=str(long_term_gains),
            estimated_capital_gains_tax=str(capital_gains_tax),
            # Phantom income
            phantom_income_total=str(phantom_income_analysis["total_phantom_income"]),
            phantom_income_by_position=phantom_income_analysis["by_position"],
            estimated_phantom_income_tax=str(phantom_income_tax),
            # Total
            total_estimated_tax=str(total_estimated_tax),
            # Disclaimer
            disclaimer=(
                "This is an estimate only. Tax treatment depends on your residency, "
                "filing status, and applicable tax treaties. Consult a tax professional."
            ),
        )

    def _analyze_phantom_income(self, bond_positions) -> dict:
        """Analyze phantom income for zero-coupon bonds"""
        total_phantom_income = Decimal("0")
        by_position = []

        current_year = date.today().year

        for position in bond_positions:
            if not position.maturity_date or position.coupon_rate and position.coupon_rate > 0:
                # Not a zero-coupon bond
                continue

            # Calculate days held this year
            year_start = date(current_year, 1, 1)
            year_end = date(current_year, 12, 31)

            # Assume position held for entire year (simplified)
            # In practice, need to track purchase date
            days_held = (year_end - year_start).days + 1

            # Calculate phantom income
            face_value = abs(position.quantity)
            years_to_maturity = Decimal((position.maturity_date - date.today()).days) / Decimal(
                "365.25"
            )

            phantom_income = PerformanceCalculator.calculate_phantom_income(
                purchase_price=position.cost_basis,
                face_value=face_value,
                years_to_maturity=years_to_maturity,
                days_held=days_held,
            )

            total_phantom_income += phantom_income

            by_position.append(
                {
                    "symbol": position.symbol,
                    "description": position.description,
                    "face_value": str(face_value),
                    "cost_basis": str(position.cost_basis),
                    "maturity_date": position.maturity_date.isoformat(),
                    "years_to_maturity": str(years_to_maturity),
                    "days_held_this_year": days_held,
                    "phantom_income": str(phantom_income),
                    "estimated_tax": str(phantom_income * self.tax_rate),
                }
            )

        return {
            "total_phantom_income": total_phantom_income,
            "by_position": by_position,
        }
