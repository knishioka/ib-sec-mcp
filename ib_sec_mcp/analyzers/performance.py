"""Performance analyzer"""

from collections import defaultdict
from decimal import Decimal
from typing import Any

from ib_sec_mcp.analyzers.base import AnalysisResult, BaseAnalyzer
from ib_sec_mcp.core.calculator import PerformanceCalculator
from ib_sec_mcp.models.trade import Trade


class PerformanceAnalyzer(BaseAnalyzer):
    """
    Analyze trading performance

    Calculates metrics like win rate, profit factor, ROI, etc.
    """

    def analyze(self) -> AnalysisResult:
        """
        Run performance analysis

        Returns:
            AnalysisResult with performance metrics
        """
        trades = self.get_trades()
        positions = self.get_positions()

        # Overall metrics
        total_realized_pnl: Decimal = sum((t.fifo_pnl_realized for t in trades), Decimal("0"))
        total_unrealized_pnl: Decimal = sum((p.unrealized_pnl for p in positions), Decimal("0"))
        total_pnl = total_realized_pnl + total_unrealized_pnl

        total_commissions: Decimal = sum((abs(t.ib_commission) for t in trades), Decimal("0"))
        total_volume: Decimal = sum((abs(t.trade_money) for t in trades), Decimal("0"))

        # Win rate and profit factor
        win_rate, winning_trades, losing_trades = PerformanceCalculator.calculate_win_rate(trades)
        profit_factor = PerformanceCalculator.calculate_profit_factor(trades)

        # Average win/loss
        wins = [t.fifo_pnl_realized for t in trades if t.fifo_pnl_realized > 0]
        losses = [abs(t.fifo_pnl_realized) for t in trades if t.fifo_pnl_realized < 0]

        avg_win: Decimal = sum(wins, Decimal("0")) / len(wins) if wins else Decimal("0")
        avg_loss: Decimal = sum(losses, Decimal("0")) / len(losses) if losses else Decimal("0")

        # Risk/reward
        risk_reward = PerformanceCalculator.calculate_risk_reward_ratio(avg_win, avg_loss)

        # Largest win/loss
        largest_win = max(wins) if wins else Decimal("0")
        largest_loss = max(losses) if losses else Decimal("0")

        # Commission rate
        commission_rate = PerformanceCalculator.calculate_commission_rate(
            total_commissions, total_volume
        )

        # Trading frequency
        if trades:
            first_trade_date = min(t.trade_date for t in trades)
            last_trade_date = max(t.trade_date for t in trades)
            trading_days = (last_trade_date - first_trade_date).days + 1
            trades_per_day = (
                Decimal(len(trades)) / Decimal(trading_days) if trading_days > 0 else Decimal("0")
            )
        else:
            first_trade_date = None
            last_trade_date = None
            trading_days = 0
            trades_per_day = Decimal("0")

        # By symbol analysis
        by_symbol = self._analyze_by_symbol(trades)

        return self._create_result(
            # Overall metrics
            total_trades=len(trades),
            total_positions=len(positions),
            total_realized_pnl=str(total_realized_pnl),
            total_unrealized_pnl=str(total_unrealized_pnl),
            total_pnl=str(total_pnl),
            # Win metrics
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=str(win_rate),
            profit_factor=str(profit_factor),
            # Average metrics
            avg_win=str(avg_win),
            avg_loss=str(avg_loss),
            risk_reward_ratio=str(risk_reward),
            # Extreme values
            largest_win=str(largest_win),
            largest_loss=str(largest_loss),
            # Cost metrics
            total_commissions=str(total_commissions),
            total_volume=str(total_volume),
            commission_rate=str(commission_rate),
            # Trading frequency
            first_trade_date=first_trade_date.isoformat() if first_trade_date else None,
            last_trade_date=last_trade_date.isoformat() if last_trade_date else None,
            trading_days=trading_days,
            trades_per_day=str(trades_per_day),
            # By symbol
            by_symbol=by_symbol,
        )

    def _analyze_by_symbol(self, trades: list[Trade]) -> dict[str, dict[str, Any]]:
        """Analyze performance by symbol"""
        by_symbol: dict[str, list[Trade]] = defaultdict(list)

        for trade in trades:
            by_symbol[trade.symbol].append(trade)

        results = {}

        for symbol, symbol_trades in by_symbol.items():
            realized_pnl = sum(t.fifo_pnl_realized for t in symbol_trades)
            commissions = sum(abs(t.ib_commission) for t in symbol_trades)
            volume = sum(abs(t.trade_money) for t in symbol_trades)

            win_rate, wins, losses = PerformanceCalculator.calculate_win_rate(symbol_trades)
            profit_factor = PerformanceCalculator.calculate_profit_factor(symbol_trades)

            # Quantity analysis
            buys = [t for t in symbol_trades if t.is_buy]
            sells = [t for t in symbol_trades if t.is_sell]

            qty_bought = sum(abs(t.quantity) for t in buys)
            qty_sold = sum(abs(t.quantity) for t in sells)

            avg_buy_price = sum(t.trade_price for t in buys) / len(buys) if buys else Decimal("0")
            avg_sell_price = (
                sum(t.trade_price for t in sells) / len(sells) if sells else Decimal("0")
            )

            results[symbol] = {
                "trade_count": len(symbol_trades),
                "buy_count": len(buys),
                "sell_count": len(sells),
                "qty_bought": str(qty_bought),
                "qty_sold": str(qty_sold),
                "avg_buy_price": str(avg_buy_price),
                "avg_sell_price": str(avg_sell_price),
                "realized_pnl": str(realized_pnl),
                "commissions": str(commissions),
                "volume": str(volume),
                "win_rate": str(win_rate),
                "profit_factor": str(profit_factor),
                "winning_trades": wins,
                "losing_trades": losses,
            }

        return results
