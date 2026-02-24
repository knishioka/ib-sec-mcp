"""FX exposure analyzer"""

from collections import defaultdict
from decimal import Decimal
from typing import Any

from ib_sec_mcp.analyzers.base import AnalysisResult, BaseAnalyzer
from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.portfolio import Portfolio
from ib_sec_mcp.models.position import Position

# Default scenario percentage for FX simulation
DEFAULT_FX_SCENARIO_PCT = Decimal("10")

# Hedge recommendation thresholds
HEDGE_THRESHOLD_HIGH = Decimal("30")
HEDGE_THRESHOLD_MODERATE = Decimal("15")


class FXExposureAnalyzer(BaseAnalyzer):
    """Analyze portfolio FX (foreign exchange) exposure.

    Calculates currency-level exposure from positions and cash balances,
    simulates FX fluctuation impact, and provides hedge recommendations.
    """

    def __init__(
        self,
        portfolio: Portfolio | None = None,
        account: Account | None = None,
        fx_scenario_pct: Decimal = DEFAULT_FX_SCENARIO_PCT,
        base_currency: str = "USD",
    ):
        """Initialize FX exposure analyzer.

        Args:
            portfolio: Portfolio to analyze (for multi-account)
            account: Single account to analyze
            fx_scenario_pct: FX fluctuation percentage for scenario simulation
            base_currency: Base currency for reporting
        """
        super().__init__(portfolio=portfolio, account=account)
        self.fx_scenario_pct = fx_scenario_pct
        self.base_currency = base_currency

    def analyze(self) -> AnalysisResult:
        """Run FX exposure analysis.

        Returns:
            AnalysisResult with FX exposure data including:
            - Currency breakdown with values and percentages
            - FX scenario simulations (+/- configured percentage)
            - Hedge recommendations
        """
        positions = self.get_positions()
        cash_balances = self._get_cash_balances()
        total_value = self.get_total_value()

        if total_value == Decimal("0"):
            return self._create_result(
                currency_exposures={},
                scenarios={},
                hedge_recommendations=[],
                total_value="0",
                base_currency=self.base_currency,
            )

        # Build currency exposure from positions
        currency_data = self._build_currency_exposure(positions, cash_balances, total_value)

        # Run FX scenarios
        scenarios = self._simulate_fx_scenarios(currency_data, total_value)

        # Generate hedge recommendations
        recommendations = self._generate_hedge_recommendations(currency_data)

        return self._create_result(
            currency_exposures=currency_data,
            scenarios=scenarios,
            hedge_recommendations=recommendations,
            total_value=str(total_value),
            base_currency=self.base_currency,
            fx_scenario_pct=str(self.fx_scenario_pct),
        )

    def _get_cash_balances(self) -> list[CashBalance]:
        """Get cash balances from portfolio or account."""
        if self.is_multi_account and self.portfolio:
            balances: list[CashBalance] = []
            for account in self.portfolio.accounts:
                balances.extend(account.cash_balances)
            return balances
        elif self.account:
            return self.account.cash_balances
        return []

    def _build_currency_exposure(
        self,
        positions: list[Position],
        cash_balances: list[CashBalance],
        total_value: Decimal,
    ) -> dict[str, Any]:
        """Build currency exposure breakdown.

        Position values are already converted to base currency by the parser.
        Cash balances are in local currency and need FX conversion.

        Args:
            positions: List of positions (position_value in base currency)
            cash_balances: List of cash balances (ending_cash in local currency)
            total_value: Total portfolio value in base currency

        Returns:
            Dict mapping currency code to exposure details
        """
        # Accumulate position values by currency (already in base currency)
        currency_position_value: dict[str, Decimal] = defaultdict(Decimal)
        currency_positions: dict[str, list[dict[str, str]]] = defaultdict(list)
        currency_fx_rates: dict[str, Decimal] = {}

        for pos in positions:
            currency_position_value[pos.currency] += pos.position_value
            currency_fx_rates[pos.currency] = pos.fx_rate_to_base
            currency_positions[pos.currency].append(
                {
                    "symbol": pos.symbol,
                    "value_base": str(pos.position_value),
                    "asset_class": pos.asset_class.value,
                }
            )

        # Accumulate cash balances by currency, converting to base currency
        # Cash amounts are in local currency; use FX rates from positions
        currency_cash_base: dict[str, Decimal] = defaultdict(Decimal)
        currency_cash_local: dict[str, Decimal] = defaultdict(Decimal)
        for cb in cash_balances:
            if cb.currency == "BASE_SUMMARY":
                continue
            fx_rate = currency_fx_rates.get(cb.currency, Decimal("1"))
            cash_base = cb.ending_cash * fx_rate
            currency_cash_base[cb.currency] += cash_base
            currency_cash_local[cb.currency] += cb.ending_cash

        # Compute total portfolio value from our own data for accurate percentages
        total_position_base = sum(currency_position_value.values(), Decimal("0"))
        total_cash_base = sum(currency_cash_base.values(), Decimal("0"))
        computed_total = total_position_base + total_cash_base

        # Use computed total for percentages (more accurate for multi-currency)
        denom = computed_total if computed_total > Decimal("0") else Decimal("1")

        # Combine into exposure data
        all_currencies = set(currency_position_value.keys()) | set(currency_cash_base.keys())
        result: dict[str, Any] = {}

        for currency in sorted(
            all_currencies,
            key=lambda c: (
                currency_position_value.get(c, Decimal("0"))
                + currency_cash_base.get(c, Decimal("0"))
            ),
            reverse=True,
        ):
            position_val = currency_position_value.get(currency, Decimal("0"))
            cash_val_base = currency_cash_base.get(currency, Decimal("0"))
            cash_val_local = currency_cash_local.get(currency, Decimal("0"))
            total_exposure = position_val + cash_val_base
            pct = (total_exposure / denom) * Decimal("100")
            fx_rate = currency_fx_rates.get(currency, Decimal("1"))

            result[currency] = {
                "position_value_base": str(position_val),
                "cash_value_local": str(cash_val_local),
                "cash_value_base": str(cash_val_base),
                "total_exposure_base": str(total_exposure),
                "percentage": str(pct),
                "fx_rate_to_base": str(fx_rate),
                "positions": currency_positions.get(currency, []),
                "is_base_currency": currency == self.base_currency,
            }

        return result

    def _simulate_fx_scenarios(
        self,
        currency_data: dict[str, Any],
        total_value: Decimal,
    ) -> dict[str, Any]:
        """Simulate FX fluctuation impact.

        For each non-base currency, calculates the portfolio impact of
        +/- fx_scenario_pct change in exchange rate.

        Args:
            currency_data: Currency exposure data
            total_value: Total portfolio value

        Returns:
            Dict with scenario results per currency and aggregate
        """
        pct_factor = self.fx_scenario_pct / Decimal("100")
        scenarios_by_currency: dict[str, Any] = {}
        total_positive_impact = Decimal("0")
        total_negative_impact = Decimal("0")

        for currency, data in currency_data.items():
            if data.get("is_base_currency"):
                continue

            exposure = Decimal(data["total_exposure_base"])
            if exposure == Decimal("0"):
                continue

            positive_impact = exposure * pct_factor
            negative_impact = exposure * (-pct_factor)

            total_positive_impact += positive_impact
            total_negative_impact += negative_impact

            scenarios_by_currency[currency] = {
                "exposure_base": str(exposure),
                f"+{self.fx_scenario_pct}%": {
                    "impact_base": str(positive_impact),
                    "new_value_base": str(exposure + positive_impact),
                },
                f"-{self.fx_scenario_pct}%": {
                    "impact_base": str(negative_impact),
                    "new_value_base": str(exposure + negative_impact),
                },
            }

        # Aggregate portfolio impact
        aggregate = {
            f"+{self.fx_scenario_pct}%": {
                "total_impact_base": str(total_positive_impact),
                "portfolio_impact_pct": str(
                    (total_positive_impact / total_value) * Decimal("100")
                    if total_value
                    else Decimal("0")
                ),
            },
            f"-{self.fx_scenario_pct}%": {
                "total_impact_base": str(total_negative_impact),
                "portfolio_impact_pct": str(
                    (total_negative_impact / total_value) * Decimal("100")
                    if total_value
                    else Decimal("0")
                ),
            },
        }

        return {
            "by_currency": scenarios_by_currency,
            "aggregate": aggregate,
        }

    def _generate_hedge_recommendations(
        self,
        currency_data: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Generate hedge recommendations based on currency exposure.

        Args:
            currency_data: Currency exposure data

        Returns:
            List of hedge recommendation dicts
        """
        recommendations: list[dict[str, str]] = []

        for currency, data in currency_data.items():
            if data.get("is_base_currency"):
                continue

            pct = Decimal(data["percentage"])

            if pct >= HEDGE_THRESHOLD_HIGH:
                recommendations.append(
                    {
                        "currency": currency,
                        "exposure_pct": str(pct),
                        "risk_level": "HIGH",
                        "recommendation": (
                            f"Consider hedging {currency} exposure ({pct:.1f}% of portfolio). "
                            f"Currency-hedged ETFs or FX forwards recommended."
                        ),
                    }
                )
            elif pct >= HEDGE_THRESHOLD_MODERATE:
                recommendations.append(
                    {
                        "currency": currency,
                        "exposure_pct": str(pct),
                        "risk_level": "MODERATE",
                        "recommendation": (
                            f"Monitor {currency} exposure ({pct:.1f}% of portfolio). "
                            f"Consider partial hedging if exposure grows."
                        ),
                    }
                )

        if not recommendations:
            recommendations.append(
                {
                    "currency": "ALL",
                    "exposure_pct": "N/A",
                    "risk_level": "LOW",
                    "recommendation": (
                        "No significant non-base currency exposure detected. "
                        "No hedging action required."
                    ),
                }
            )

        return recommendations
