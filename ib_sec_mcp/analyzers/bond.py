"""Bond-specific analyzer"""

from datetime import date
from decimal import Decimal
from typing import Any

from ib_sec_mcp.analyzers.base import AnalysisResult, BaseAnalyzer
from ib_sec_mcp.core.calculator import PerformanceCalculator
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass


class BondAnalyzer(BaseAnalyzer):
    """
    Analyze bond holdings and trades

    Focuses on zero-coupon bonds (STRIPS) analysis
    """

    def analyze(self) -> AnalysisResult:
        """
        Run bond analysis

        Returns:
            AnalysisResult with bond metrics
        """
        positions = self.get_positions()
        trades = self.get_trades()

        # Filter bond positions and trades
        bond_positions = [p for p in positions if p.asset_class == AssetClass.BOND]
        bond_trades = [t for t in trades if t.asset_class == AssetClass.BOND]

        if not bond_positions and not bond_trades:
            return self._create_result(
                has_bonds=False,
                message="No bond positions or trades found",
            )

        # Current holdings
        current_holdings = []
        for position in bond_positions:
            holding_info = self._analyze_bond_position(position)
            current_holdings.append(holding_info)

        # Completed trades
        completed_trades = []
        for trade in bond_trades:
            trade_info = {
                "symbol": trade.symbol,
                "description": trade.description,
                "trade_date": trade.trade_date.isoformat(),
                "buy_sell": trade.buy_sell.value,
                "quantity": str(trade.quantity),
                "price": str(trade.trade_price),
                "amount": str(trade.trade_money),
                "commission": str(trade.ib_commission),
                "realized_pnl": str(trade.fifo_pnl_realized),
            }
            completed_trades.append(trade_info)

        # Overall bond metrics
        total_bond_value = sum(p.position_value for p in bond_positions)
        total_bond_unrealized_pnl = sum(p.unrealized_pnl for p in bond_positions)
        total_bond_realized_pnl = sum(t.fifo_pnl_realized for t in bond_trades)

        return self._create_result(
            has_bonds=True,
            # Current holdings
            current_holdings_count=len(current_holdings),
            current_holdings=current_holdings,
            total_bond_value=str(total_bond_value),
            total_unrealized_pnl=str(total_bond_unrealized_pnl),
            # Completed trades
            completed_trades_count=len(completed_trades),
            completed_trades=completed_trades,
            total_realized_pnl=str(total_bond_realized_pnl),
            # Overall
            total_pnl=str(total_bond_unrealized_pnl + total_bond_realized_pnl),
        )

    def _analyze_bond_position(self, position: Position) -> dict[str, Any]:
        """Analyze individual bond position"""
        # Calculate years to maturity
        if position.maturity_date:
            years_to_maturity = Decimal((position.maturity_date - date.today()).days) / Decimal(
                "365.25"
            )
        else:
            years_to_maturity = Decimal("0")

        # Calculate YTM for zero-coupon bond
        if position.maturity_date and position.quantity > 0:
            face_value = abs(position.quantity)  # Face value
            current_price = position.mark_price * abs(position.quantity)

            ytm = PerformanceCalculator.calculate_ytm(face_value, current_price, years_to_maturity)

            # Duration (for zero-coupon = years to maturity)
            duration = PerformanceCalculator.calculate_bond_duration(years_to_maturity, ytm)
        else:
            ytm = Decimal("0")
            duration = Decimal("0")

        return {
            "symbol": position.symbol,
            "description": position.description,
            "cusip": position.cusip,
            "isin": position.isin,
            "quantity": str(position.quantity),
            "mark_price": str(position.mark_price),
            "position_value": str(position.position_value),
            "cost_basis": str(position.cost_basis),
            "unrealized_pnl": str(position.unrealized_pnl),
            "unrealized_pnl_pct": str(position.pnl_percentage),
            "maturity_date": position.maturity_date.isoformat() if position.maturity_date else None,
            "years_to_maturity": str(years_to_maturity),
            "ytm": str(ytm),
            "duration": str(duration),
            "coupon_rate": str(position.coupon_rate) if position.coupon_rate else "0",
        }
