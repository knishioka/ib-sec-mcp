"""Tests for PerformanceCalculator"""

from datetime import date
from decimal import Decimal

from ib_sec_mcp.core.calculator import PerformanceCalculator
from ib_sec_mcp.models.trade import AssetClass, BuySell, Trade


def _make_trade(pnl: Decimal) -> Trade:
    """Helper to create a trade with specific P&L."""
    return Trade(
        account_id="U1234567",
        trade_id="T001",
        trade_date=date(2025, 1, 15),
        symbol="AAPL",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.BUY,
        quantity=Decimal("10"),
        trade_price=Decimal("150.00"),
        trade_money=Decimal("-1500.00"),
        fifo_pnl_realized=pnl,
    )


class TestCalculateROI:
    """Tests for ROI calculation"""

    def test_positive_return(self) -> None:
        roi = PerformanceCalculator.calculate_roi(Decimal("1000"), Decimal("1100"))
        assert roi == Decimal("10")

    def test_negative_return(self) -> None:
        roi = PerformanceCalculator.calculate_roi(Decimal("1000"), Decimal("900"))
        assert roi == Decimal("-10")

    def test_zero_initial_value(self) -> None:
        roi = PerformanceCalculator.calculate_roi(Decimal("0"), Decimal("1000"))
        assert roi == Decimal("0")

    def test_no_change(self) -> None:
        roi = PerformanceCalculator.calculate_roi(Decimal("1000"), Decimal("1000"))
        assert roi == Decimal("0")

    def test_large_return(self) -> None:
        roi = PerformanceCalculator.calculate_roi(Decimal("100"), Decimal("1000"))
        assert roi == Decimal("900")


class TestCalculateCAGR:
    """Tests for CAGR calculation"""

    def test_normal_case(self) -> None:
        cagr = PerformanceCalculator.calculate_cagr(Decimal("1000"), Decimal("1100"), Decimal("1"))
        # (1100/1000)^(1/1) - 1 = 10%
        assert abs(cagr - Decimal("10")) < Decimal("0.01")

    def test_multi_year(self) -> None:
        cagr = PerformanceCalculator.calculate_cagr(Decimal("1000"), Decimal("1210"), Decimal("2"))
        # (1210/1000)^(1/2) - 1 = 10%
        assert abs(cagr - Decimal("10")) < Decimal("0.01")

    def test_zero_initial_value(self) -> None:
        cagr = PerformanceCalculator.calculate_cagr(Decimal("0"), Decimal("1000"), Decimal("1"))
        assert cagr == Decimal("0")

    def test_zero_years(self) -> None:
        cagr = PerformanceCalculator.calculate_cagr(Decimal("1000"), Decimal("1100"), Decimal("0"))
        assert cagr == Decimal("0")

    def test_fractional_years(self) -> None:
        cagr = PerformanceCalculator.calculate_cagr(
            Decimal("1000"), Decimal("1050"), Decimal("0.5")
        )
        assert cagr > Decimal("0")


class TestCalculateWinRate:
    """Tests for win rate calculation"""

    def test_mixed_trades(self) -> None:
        trades = [
            _make_trade(Decimal("100")),  # win
            _make_trade(Decimal("200")),  # win
            _make_trade(Decimal("-50")),  # loss
        ]
        win_rate, wins, losses = PerformanceCalculator.calculate_win_rate(trades)
        # 2/3 * 100 = 66.67%
        assert abs(win_rate - Decimal("66.67")) < Decimal("0.01")
        assert wins == 2
        assert losses == 1

    def test_all_wins(self) -> None:
        trades = [_make_trade(Decimal("100")), _make_trade(Decimal("200"))]
        win_rate, wins, losses = PerformanceCalculator.calculate_win_rate(trades)
        assert win_rate == Decimal("100")
        assert wins == 2
        assert losses == 0

    def test_all_losses(self) -> None:
        trades = [_make_trade(Decimal("-100")), _make_trade(Decimal("-50"))]
        win_rate, wins, losses = PerformanceCalculator.calculate_win_rate(trades)
        assert win_rate == Decimal("0")
        assert wins == 0
        assert losses == 2

    def test_empty_trades(self) -> None:
        win_rate, wins, losses = PerformanceCalculator.calculate_win_rate([])
        assert win_rate == Decimal("0")
        assert wins == 0
        assert losses == 0

    def test_zero_pnl_trades(self) -> None:
        trades = [_make_trade(Decimal("0")), _make_trade(Decimal("0"))]
        win_rate, wins, losses = PerformanceCalculator.calculate_win_rate(trades)
        assert win_rate == Decimal("0")
        assert wins == 0
        assert losses == 0


class TestCalculateProfitFactor:
    """Tests for profit factor calculation"""

    def test_normal_case(self) -> None:
        trades = [
            _make_trade(Decimal("300")),
            _make_trade(Decimal("200")),
            _make_trade(Decimal("-100")),
        ]
        pf = PerformanceCalculator.calculate_profit_factor(trades)
        # 500 / 100 = 5.0
        assert pf == Decimal("5")

    def test_no_losses(self) -> None:
        trades = [_make_trade(Decimal("100")), _make_trade(Decimal("200"))]
        pf = PerformanceCalculator.calculate_profit_factor(trades)
        assert pf == Decimal("999.99")

    def test_no_profits(self) -> None:
        trades = [_make_trade(Decimal("-100")), _make_trade(Decimal("-200"))]
        pf = PerformanceCalculator.calculate_profit_factor(trades)
        assert pf == Decimal("0")

    def test_zero_pnl_no_losses(self) -> None:
        trades = [_make_trade(Decimal("0"))]
        pf = PerformanceCalculator.calculate_profit_factor(trades)
        # gross_profit=0, gross_loss=0 → sentinel 0
        assert pf == Decimal("0")

    def test_empty_trades(self) -> None:
        pf = PerformanceCalculator.calculate_profit_factor([])
        assert pf == Decimal("0")


class TestCalculateSharpeRatio:
    """Tests for Sharpe ratio calculation"""

    def test_normal_returns(self) -> None:
        returns = [Decimal("0.10"), Decimal("0.05"), Decimal("0.08"), Decimal("0.12")]
        sharpe = PerformanceCalculator.calculate_sharpe_ratio(returns, Decimal("0.02"))
        assert abs(sharpe - Decimal("2.26")) < Decimal("0.01")

    def test_single_return(self) -> None:
        sharpe = PerformanceCalculator.calculate_sharpe_ratio([Decimal("0.10")])
        assert sharpe == Decimal("0")

    def test_empty_returns(self) -> None:
        sharpe = PerformanceCalculator.calculate_sharpe_ratio([])
        assert sharpe == Decimal("0")

    def test_zero_variance(self) -> None:
        returns = [Decimal("0.05"), Decimal("0.05"), Decimal("0.05")]
        sharpe = PerformanceCalculator.calculate_sharpe_ratio(returns)
        assert sharpe == Decimal("0")

    def test_default_risk_free_rate(self) -> None:
        returns = [Decimal("0.10"), Decimal("0.05"), Decimal("0.08")]
        sharpe = PerformanceCalculator.calculate_sharpe_ratio(returns)
        assert isinstance(sharpe, Decimal)


class TestCalculateMaxDrawdown:
    """Tests for max drawdown calculation"""

    def test_clear_drawdown(self) -> None:
        values = [
            Decimal("100"),
            Decimal("110"),
            Decimal("90"),
            Decimal("95"),
            Decimal("105"),
        ]
        dd, peak_idx, trough_idx = PerformanceCalculator.calculate_max_drawdown(values)
        # Peak at 110 (idx 1), trough at 90 (idx 2)
        # Drawdown = (110-90)/110 * 100 = 18.18%
        assert abs(dd - Decimal("18.18")) < Decimal("0.01")
        assert peak_idx == 1
        assert trough_idx == 2

    def test_monotonically_increasing(self) -> None:
        values = [Decimal("100"), Decimal("110"), Decimal("120"), Decimal("130")]
        dd, _, _ = PerformanceCalculator.calculate_max_drawdown(values)
        assert dd == Decimal("0")

    def test_single_value(self) -> None:
        dd, peak_idx, trough_idx = PerformanceCalculator.calculate_max_drawdown([Decimal("100")])
        assert dd == Decimal("0")
        assert peak_idx == 0
        assert trough_idx == 0

    def test_empty_values(self) -> None:
        dd, peak_idx, trough_idx = PerformanceCalculator.calculate_max_drawdown([])
        assert dd == Decimal("0")

    def test_multiple_drawdowns(self) -> None:
        values = [
            Decimal("100"),
            Decimal("80"),  # -20%
            Decimal("120"),
            Decimal("90"),  # -25% from 120
        ]
        dd, _, _ = PerformanceCalculator.calculate_max_drawdown(values)
        # 25% drawdown from 120 to 90
        assert abs(dd - Decimal("25")) < Decimal("0.01")


class TestCalculateYTM:
    """Tests for Yield to Maturity calculation"""

    def test_normal_case(self) -> None:
        # Zero-coupon bond: face=100, price=95, 2 years
        ytm = PerformanceCalculator.calculate_ytm(Decimal("100"), Decimal("95"), Decimal("2"))
        # (100/95)^(1/2) - 1 ≈ 2.60%
        assert abs(ytm - Decimal("2.60")) < Decimal("0.1")
        assert isinstance(ytm, Decimal)

    def test_zero_price(self) -> None:
        ytm = PerformanceCalculator.calculate_ytm(Decimal("100"), Decimal("0"), Decimal("2"))
        assert ytm == Decimal("0")

    def test_zero_years(self) -> None:
        ytm = PerformanceCalculator.calculate_ytm(Decimal("100"), Decimal("95"), Decimal("0"))
        assert ytm == Decimal("0")

    def test_at_par(self) -> None:
        ytm = PerformanceCalculator.calculate_ytm(Decimal("100"), Decimal("100"), Decimal("5"))
        assert abs(ytm) < Decimal("0.01")


class TestCalculateBondDuration:
    """Tests for bond duration calculation"""

    def test_zero_coupon(self) -> None:
        # For zero-coupon bonds, duration = years to maturity
        duration = PerformanceCalculator.calculate_bond_duration(Decimal("5"), Decimal("0.04"))
        assert duration == Decimal("5")

    def test_any_ytm(self) -> None:
        # Duration is always years_to_maturity for this implementation
        duration = PerformanceCalculator.calculate_bond_duration(Decimal("10"), Decimal("0.10"))
        assert duration == Decimal("10")


class TestCalculateBondPriceChange:
    """Tests for bond price change estimation"""

    def test_yield_increase(self) -> None:
        # Price drops when yield increases
        new_price = PerformanceCalculator.calculate_bond_price_change(
            Decimal("100"), Decimal("5"), Decimal("1")
        )
        # ΔP/P = -5 * (1/100) = -0.05 → new_price = 100 - 5 = 95
        assert new_price == Decimal("95")

    def test_yield_decrease(self) -> None:
        # Price rises when yield decreases
        new_price = PerformanceCalculator.calculate_bond_price_change(
            Decimal("100"), Decimal("5"), Decimal("-1")
        )
        # ΔP/P = -5 * (-1/100) = 0.05 → new_price = 100 + 5 = 105
        assert new_price == Decimal("105")

    def test_no_change(self) -> None:
        new_price = PerformanceCalculator.calculate_bond_price_change(
            Decimal("100"), Decimal("5"), Decimal("0")
        )
        assert new_price == Decimal("100")


class TestCalculatePhantomIncome:
    """Tests for OID phantom income calculation"""

    def test_normal_case(self) -> None:
        phantom = PerformanceCalculator.calculate_phantom_income(
            purchase_price=Decimal("900"),
            face_value=Decimal("1000"),
            years_to_maturity=Decimal("10"),
            days_held=365,
        )
        assert abs(phantom - Decimal("9.52")) < Decimal("0.01")

    def test_zero_maturity(self) -> None:
        phantom = PerformanceCalculator.calculate_phantom_income(
            purchase_price=Decimal("900"),
            face_value=Decimal("1000"),
            years_to_maturity=Decimal("0"),
            days_held=365,
        )
        assert phantom == Decimal("0")

    def test_short_holding_period(self) -> None:
        phantom_short = PerformanceCalculator.calculate_phantom_income(
            purchase_price=Decimal("900"),
            face_value=Decimal("1000"),
            years_to_maturity=Decimal("10"),
            days_held=30,
        )
        phantom_long = PerformanceCalculator.calculate_phantom_income(
            purchase_price=Decimal("900"),
            face_value=Decimal("1000"),
            years_to_maturity=Decimal("10"),
            days_held=365,
        )
        assert phantom_short < phantom_long


class TestCalculateCommissionRate:
    """Tests for commission rate calculation"""

    def test_normal_case(self) -> None:
        rate = PerformanceCalculator.calculate_commission_rate(Decimal("10"), Decimal("10000"))
        # 10 / 10000 * 100 = 0.1%
        assert rate == Decimal("0.1")

    def test_zero_volume(self) -> None:
        rate = PerformanceCalculator.calculate_commission_rate(Decimal("10"), Decimal("0"))
        assert rate == Decimal("0")


class TestCalculateRiskRewardRatio:
    """Tests for risk/reward ratio calculation"""

    def test_normal_case(self) -> None:
        ratio = PerformanceCalculator.calculate_risk_reward_ratio(Decimal("200"), Decimal("100"))
        assert ratio == Decimal("2")

    def test_zero_loss(self) -> None:
        ratio = PerformanceCalculator.calculate_risk_reward_ratio(Decimal("200"), Decimal("0"))
        assert ratio == Decimal("999.99")

    def test_zero_win_zero_loss(self) -> None:
        ratio = PerformanceCalculator.calculate_risk_reward_ratio(Decimal("0"), Decimal("0"))
        assert ratio == Decimal("0")

    def test_negative_average_loss(self) -> None:
        # abs() is applied in the method
        ratio = PerformanceCalculator.calculate_risk_reward_ratio(Decimal("200"), Decimal("-100"))
        assert ratio == Decimal("2")
