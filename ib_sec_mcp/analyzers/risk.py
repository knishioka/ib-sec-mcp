"""Risk analyzer"""

from decimal import Decimal

from ib_sec_mcp.analyzers.base import AnalysisResult, BaseAnalyzer
from ib_sec_mcp.core.calculator import PerformanceCalculator
from ib_sec_mcp.models.trade import AssetClass


class RiskAnalyzer(BaseAnalyzer):
    """
    Analyze portfolio risk

    Focuses on interest rate risk for bond holdings
    """

    def analyze(self) -> AnalysisResult:
        """
        Run risk analysis

        Returns:
            AnalysisResult with risk metrics
        """
        positions = self.get_positions()

        # Interest rate risk (for bonds)
        bond_positions = [p for p in positions if p.asset_class == AssetClass.BOND]

        if bond_positions:
            rate_scenarios = self._analyze_interest_rate_scenarios(bond_positions)
        else:
            rate_scenarios = {}

        # Portfolio concentration risk
        total_value = self.get_total_value()
        concentration = self._analyze_concentration(positions, total_value)

        return self._create_result(
            # Interest rate risk
            has_bond_exposure=len(bond_positions) > 0,
            bond_count=len(bond_positions),
            interest_rate_scenarios=rate_scenarios,
            # Concentration risk
            concentration=concentration,
        )

    def _analyze_interest_rate_scenarios(self, bond_positions) -> dict:
        """Analyze interest rate scenarios for bonds"""
        scenarios = []

        # Define scenarios: -3%, -2%, -1%, 0%, +1%, +2%, +3%
        rate_changes = [
            Decimal("-3.0"),
            Decimal("-2.0"),
            Decimal("-1.0"),
            Decimal("0.0"),
            Decimal("1.0"),
            Decimal("2.0"),
            Decimal("3.0"),
        ]

        for rate_change in rate_changes:
            scenario_name = f"{rate_change:+.1f}%" if rate_change != 0 else "No Change"

            total_value_change = Decimal("0")
            position_details = []

            for position in bond_positions:
                if not position.maturity_date:
                    continue

                # Calculate duration
                current_price = position.position_value
                years_to_maturity = Decimal(
                    (position.maturity_date - position.position_date).days
                ) / Decimal("365.25")

                # Estimate new price
                new_price = PerformanceCalculator.calculate_bond_price_change(
                    current_price=current_price,
                    duration=years_to_maturity,
                    yield_change=rate_change,
                )

                price_change = new_price - current_price
                total_value_change += price_change

                position_details.append(
                    {
                        "symbol": position.symbol,
                        "current_value": str(current_price),
                        "new_value": str(new_price),
                        "change": str(price_change),
                        "change_pct": str(
                            (price_change / current_price * 100)
                            if current_price > 0
                            else Decimal("0")
                        ),
                    }
                )

            scenarios.append(
                {
                    "scenario": scenario_name,
                    "rate_change": str(rate_change),
                    "total_value_change": str(total_value_change),
                    "positions": position_details,
                }
            )

        return {"scenarios": scenarios}

    def _analyze_concentration(self, positions, total_value: Decimal) -> dict:
        """Analyze portfolio concentration"""
        if total_value == 0:
            return {
                "top_positions": [],
                "max_concentration": "0",
            }

        # Sort positions by value
        sorted_positions = sorted(positions, key=lambda p: p.position_value, reverse=True)

        top_positions = []
        for position in sorted_positions[:10]:  # Top 10
            allocation_pct = (position.position_value / total_value) * 100
            top_positions.append(
                {
                    "symbol": position.symbol,
                    "value": str(position.position_value),
                    "allocation_pct": str(allocation_pct),
                }
            )

        max_concentration = (
            (sorted_positions[0].position_value / total_value) * 100
            if sorted_positions
            else Decimal("0")
        )

        return {
            "top_positions": top_positions,
            "max_concentration": str(max_concentration),
        }
