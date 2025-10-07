"""Performance calculation engine"""

import math
from decimal import Decimal

from ib_sec_mcp.models.trade import Trade


class PerformanceCalculator:
    """
    Calculate various performance metrics

    Supports both single-account and multi-account portfolios
    """

    @staticmethod
    def calculate_roi(
        initial_value: Decimal,
        final_value: Decimal,
    ) -> Decimal:
        """
        Calculate Return on Investment (ROI)

        Args:
            initial_value: Starting value
            final_value: Ending value

        Returns:
            ROI as percentage
        """
        if initial_value == 0:
            return Decimal("0")

        return ((final_value - initial_value) / initial_value) * 100

    @staticmethod
    def calculate_cagr(
        initial_value: Decimal,
        final_value: Decimal,
        years: Decimal,
    ) -> Decimal:
        """
        Calculate Compound Annual Growth Rate (CAGR)

        Args:
            initial_value: Starting value
            final_value: Ending value
            years: Investment period in years

        Returns:
            CAGR as percentage
        """
        if initial_value == 0 or years == 0:
            return Decimal("0")

        ratio = float(final_value / initial_value)
        power = 1.0 / float(years)
        cagr = (math.pow(ratio, power) - 1) * 100

        return Decimal(str(cagr))

    @staticmethod
    def calculate_win_rate(trades: list[Trade]) -> tuple[Decimal, int, int]:
        """
        Calculate win rate from trades

        Args:
            trades: List of trades

        Returns:
            Tuple of (win_rate, winning_trades, losing_trades)
        """
        if not trades:
            return Decimal("0"), 0, 0

        winning = [t for t in trades if t.fifo_pnl_realized > 0]
        losing = [t for t in trades if t.fifo_pnl_realized < 0]

        total_with_pnl = len(winning) + len(losing)
        if total_with_pnl == 0:
            return Decimal("0"), 0, 0

        win_rate = (Decimal(len(winning)) / Decimal(total_with_pnl)) * 100

        return win_rate, len(winning), len(losing)

    @staticmethod
    def calculate_profit_factor(trades: list[Trade]) -> Decimal:
        """
        Calculate profit factor (gross profit / gross loss)

        Args:
            trades: List of trades

        Returns:
            Profit factor
        """
        if not trades:
            return Decimal("0")

        gross_profit = sum(t.fifo_pnl_realized for t in trades if t.fifo_pnl_realized > 0)
        gross_loss = abs(sum(t.fifo_pnl_realized for t in trades if t.fifo_pnl_realized < 0))

        if gross_loss == 0:
            return Decimal("999.99") if gross_profit > 0 else Decimal("0")

        return gross_profit / gross_loss

    @staticmethod
    def calculate_sharpe_ratio(
        returns: list[Decimal],
        risk_free_rate: Decimal = Decimal("0.03"),
    ) -> Decimal:
        """
        Calculate Sharpe Ratio

        Args:
            returns: List of period returns
            risk_free_rate: Risk-free rate (annual)

        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return Decimal("0")

        # Calculate mean return
        mean_return = sum(returns) / len(returns)

        # Calculate standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = Decimal(str(math.sqrt(float(variance))))

        if std_dev == 0:
            return Decimal("0")

        # Annualized Sharpe ratio
        excess_return = mean_return - risk_free_rate
        sharpe = excess_return / std_dev

        return sharpe

    @staticmethod
    def calculate_max_drawdown(values: list[Decimal]) -> tuple[Decimal, int, int]:
        """
        Calculate maximum drawdown

        Args:
            values: List of portfolio values over time

        Returns:
            Tuple of (max_drawdown_pct, peak_index, trough_index)
        """
        if not values or len(values) < 2:
            return Decimal("0"), 0, 0

        max_drawdown = Decimal("0")
        peak = values[0]
        peak_idx = 0
        trough_idx = 0

        for i, value in enumerate(values):
            if value > peak:
                peak = value
                peak_idx = i

            drawdown = ((peak - value) / peak) * 100 if peak > 0 else Decimal("0")

            if drawdown > max_drawdown:
                max_drawdown = drawdown
                trough_idx = i

        return max_drawdown, peak_idx, trough_idx

    @staticmethod
    def calculate_ytm(
        face_value: Decimal,
        current_price: Decimal,
        years_to_maturity: Decimal,
    ) -> Decimal:
        """
        Calculate Yield to Maturity (YTM) for zero-coupon bonds

        Args:
            face_value: Bond face value
            current_price: Current market price
            years_to_maturity: Years until maturity

        Returns:
            YTM as percentage
        """
        if current_price == 0 or years_to_maturity == 0:
            return Decimal("0")

        ratio = float(face_value / current_price)
        power = 1.0 / float(years_to_maturity)
        ytm = (math.pow(ratio, power) - 1) * 100

        return Decimal(str(ytm))

    @staticmethod
    def calculate_bond_duration(
        years_to_maturity: Decimal,
        ytm: Decimal,
    ) -> Decimal:
        """
        Calculate Macaulay duration for zero-coupon bond

        For zero-coupon bonds, duration equals time to maturity

        Args:
            years_to_maturity: Years until maturity
            ytm: Yield to maturity

        Returns:
            Duration in years
        """
        # For zero-coupon bonds, duration = time to maturity
        return years_to_maturity

    @staticmethod
    def calculate_bond_price_change(
        current_price: Decimal,
        duration: Decimal,
        yield_change: Decimal,
    ) -> Decimal:
        """
        Calculate bond price change for yield change

        Args:
            current_price: Current bond price
            duration: Bond duration
            yield_change: Change in yield (in percentage points)

        Returns:
            Estimated new price
        """
        # Modified duration approximation: ΔP/P ≈ -D × Δy
        price_change_pct = -duration * (yield_change / 100)
        price_change = current_price * price_change_pct
        new_price = current_price + price_change

        return new_price

    @staticmethod
    def calculate_phantom_income(
        purchase_price: Decimal,
        face_value: Decimal,
        years_to_maturity: Decimal,
        days_held: int,
    ) -> Decimal:
        """
        Calculate phantom income (OID) for zero-coupon bond

        Uses constant yield method per IRS Publication 1212

        Args:
            purchase_price: Purchase price (cost basis)
            face_value: Bond face value
            years_to_maturity: Total years to maturity
            days_held: Days held in tax year

        Returns:
            Phantom income for the period
        """
        if years_to_maturity == 0:
            return Decimal("0")

        # Calculate yield to maturity
        ytm_decimal = (
            PerformanceCalculator.calculate_ytm(face_value, purchase_price, years_to_maturity) / 100
        )

        # Calculate accrued interest using constant yield method
        fraction_of_year = Decimal(days_held) / Decimal("365.25")
        growth_factor = (Decimal("1") + ytm_decimal) ** fraction_of_year
        accrued_interest = purchase_price * (growth_factor - Decimal("1"))

        return accrued_interest

    @staticmethod
    def calculate_commission_rate(
        total_commissions: Decimal,
        total_volume: Decimal,
    ) -> Decimal:
        """
        Calculate commission rate as percentage of volume

        Args:
            total_commissions: Total commissions paid
            total_volume: Total trading volume

        Returns:
            Commission rate as percentage
        """
        if total_volume == 0:
            return Decimal("0")

        return (total_commissions / total_volume) * 100

    @staticmethod
    def calculate_risk_reward_ratio(
        average_win: Decimal,
        average_loss: Decimal,
    ) -> Decimal:
        """
        Calculate risk/reward ratio

        Args:
            average_win: Average winning trade
            average_loss: Average losing trade (absolute value)

        Returns:
            Risk/reward ratio
        """
        if average_loss == 0:
            return Decimal("999.99") if average_win > 0 else Decimal("0")

        return average_win / abs(average_loss)
