"""Cost efficiency analyzer"""

from collections import defaultdict
from decimal import Decimal

from ib_sec_mcp.analyzers.base import AnalysisResult, BaseAnalyzer
from ib_sec_mcp.core.calculator import PerformanceCalculator
from ib_sec_mcp.models.trade import AssetClass, Trade


class CostAnalyzer(BaseAnalyzer):
    """
    Analyze cost efficiency

    Calculates commission rates and cost impact on performance
    """

    def analyze(self) -> AnalysisResult:
        """
        Run cost analysis

        Returns:
            AnalysisResult with cost metrics
        """
        trades = self.get_trades()

        if not trades:
            return self._create_result(
                total_commissions="0",
                total_volume="0",
                commission_rate="0",
                by_asset_class={},
                by_symbol={},
            )

        # Overall metrics
        total_commissions = sum(abs(t.ib_commission) for t in trades)
        total_volume = sum(abs(t.trade_money) for t in trades)
        overall_rate = PerformanceCalculator.calculate_commission_rate(
            total_commissions, total_volume
        )

        # Impact on P&L
        total_realized_pnl = sum(t.fifo_pnl_realized for t in trades)
        commission_impact_pct = (
            (total_commissions / abs(total_realized_pnl)) * 100
            if total_realized_pnl != 0
            else Decimal("0")
        )

        # By asset class
        by_asset = self._analyze_by_asset_class(trades)

        # By symbol
        by_symbol = self._analyze_by_symbol(trades)

        # Average commission per trade
        avg_commission = total_commissions / len(trades)

        # Commission distribution
        small_trades = [t for t in trades if abs(t.trade_money) < 5000]
        medium_trades = [t for t in trades if 5000 <= abs(t.trade_money) < 50000]
        large_trades = [t for t in trades if abs(t.trade_money) >= 50000]

        return self._create_result(
            # Overall metrics
            total_commissions=str(total_commissions),
            total_volume=str(total_volume),
            commission_rate=str(overall_rate),
            avg_commission_per_trade=str(avg_commission),
            # Impact
            total_realized_pnl=str(total_realized_pnl),
            commission_impact_pct=str(commission_impact_pct),
            # Distribution
            small_trades_count=len(small_trades),
            medium_trades_count=len(medium_trades),
            large_trades_count=len(large_trades),
            small_trades_avg_commission=str(
                sum(abs(t.ib_commission) for t in small_trades) / len(small_trades)
                if small_trades
                else Decimal("0")
            ),
            medium_trades_avg_commission=str(
                sum(abs(t.ib_commission) for t in medium_trades) / len(medium_trades)
                if medium_trades
                else Decimal("0")
            ),
            large_trades_avg_commission=str(
                sum(abs(t.ib_commission) for t in large_trades) / len(large_trades)
                if large_trades
                else Decimal("0")
            ),
            # Breakdowns
            by_asset_class=by_asset,
            by_symbol=by_symbol,
        )

    def _analyze_by_asset_class(self, trades: list[Trade]) -> dict[str, dict]:
        """Analyze costs by asset class"""
        by_asset: dict[AssetClass, list[Trade]] = defaultdict(list)

        for trade in trades:
            by_asset[trade.asset_class].append(trade)

        results = {}

        for asset_class, asset_trades in by_asset.items():
            commissions = sum(abs(t.ib_commission) for t in asset_trades)
            volume = sum(abs(t.trade_money) for t in asset_trades)
            rate = PerformanceCalculator.calculate_commission_rate(commissions, volume)

            results[asset_class.value] = {
                "trade_count": len(asset_trades),
                "total_commissions": str(commissions),
                "total_volume": str(volume),
                "commission_rate": str(rate),
            }

        return results

    def _analyze_by_symbol(self, trades: list[Trade]) -> dict[str, dict]:
        """Analyze costs by symbol"""
        by_symbol: dict[str, list[Trade]] = defaultdict(list)

        for trade in trades:
            by_symbol[trade.symbol].append(trade)

        results = {}

        for symbol, symbol_trades in by_symbol.items():
            commissions = sum(abs(t.ib_commission) for t in symbol_trades)
            volume = sum(abs(t.trade_money) for t in symbol_trades)
            rate = PerformanceCalculator.calculate_commission_rate(commissions, volume)

            results[symbol] = {
                "trade_count": len(symbol_trades),
                "total_commissions": str(commissions),
                "total_volume": str(volume),
                "commission_rate": str(rate),
            }

        return results
