"""Multi-account aggregation logic"""

from collections import defaultdict
from decimal import Decimal

from ib_sec_mcp.models.account import Account
from ib_sec_mcp.models.portfolio import Portfolio
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import Trade


class MultiAccountAggregator:
    """
    Aggregate data across multiple accounts

    Provides various aggregation methods for multi-account portfolios
    """

    @staticmethod
    def create_portfolio(
        accounts: list[Account],
        base_currency: str = "USD",
    ) -> Portfolio:
        """
        Create portfolio from accounts

        Args:
            accounts: List of Account objects
            base_currency: Base currency for reporting

        Returns:
            Portfolio instance
        """
        return Portfolio.from_accounts(accounts, base_currency)

    @staticmethod
    def aggregate_trades_by_symbol(
        portfolio: Portfolio,
    ) -> dict[str, list[Trade]]:
        """
        Aggregate all trades by symbol

        Args:
            portfolio: Portfolio instance

        Returns:
            Dict mapping symbol to list of trades
        """
        trades_by_symbol: dict[str, list[Trade]] = defaultdict(list)

        for trade in portfolio.all_trades:
            trades_by_symbol[trade.symbol].append(trade)

        return dict(trades_by_symbol)

    @staticmethod
    def aggregate_positions_by_symbol(
        portfolio: Portfolio,
    ) -> dict[str, list[Position]]:
        """
        Aggregate all positions by symbol

        Args:
            portfolio: Portfolio instance

        Returns:
            Dict mapping symbol to list of positions
        """
        positions_by_symbol: dict[str, list[Position]] = defaultdict(list)

        for position in portfolio.all_positions:
            positions_by_symbol[position.symbol].append(position)

        return dict(positions_by_symbol)

    @staticmethod
    def calculate_total_position_by_symbol(
        portfolio: Portfolio,
    ) -> dict[str, tuple[Decimal, Decimal, Decimal]]:
        """
        Calculate total position quantity, value, and P&L by symbol

        Args:
            portfolio: Portfolio instance

        Returns:
            Dict mapping symbol to (total_quantity, total_value, total_unrealized_pnl)
        """
        totals: dict[str, tuple[Decimal, Decimal, Decimal]] = {}

        positions_by_symbol = MultiAccountAggregator.aggregate_positions_by_symbol(portfolio)

        for symbol, positions in positions_by_symbol.items():
            total_qty = sum(p.quantity for p in positions)
            total_value = sum(p.position_value for p in positions)
            total_pnl = sum(p.unrealized_pnl for p in positions)

            totals[symbol] = (total_qty, total_value, total_pnl)

        return totals

    @staticmethod
    def calculate_total_trades_by_symbol(
        portfolio: Portfolio,
    ) -> dict[str, tuple[int, Decimal, Decimal]]:
        """
        Calculate total trade count, volume, and P&L by symbol

        Args:
            portfolio: Portfolio instance

        Returns:
            Dict mapping symbol to (trade_count, total_volume, total_realized_pnl)
        """
        totals: dict[str, tuple[int, Decimal, Decimal]] = {}

        trades_by_symbol = MultiAccountAggregator.aggregate_trades_by_symbol(portfolio)

        for symbol, trades in trades_by_symbol.items():
            trade_count = len(trades)
            total_volume = sum(abs(t.trade_money) for t in trades)
            total_pnl = sum(t.fifo_pnl_realized for t in trades)

            totals[symbol] = (trade_count, total_volume, total_pnl)

        return totals

    @staticmethod
    def aggregate_by_asset_class(
        portfolio: Portfolio,
    ) -> dict[str, dict[str, Decimal]]:
        """
        Aggregate positions and trades by asset class

        Args:
            portfolio: Portfolio instance

        Returns:
            Dict with asset class aggregations
        """
        aggregated: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {
                "position_value": Decimal("0"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
                "trade_count": Decimal("0"),
                "commissions": Decimal("0"),
            }
        )

        # Aggregate positions
        for position in portfolio.all_positions:
            asset_class = position.asset_class.value
            aggregated[asset_class]["position_value"] += position.position_value
            aggregated[asset_class]["unrealized_pnl"] += position.unrealized_pnl

        # Aggregate trades
        for trade in portfolio.all_trades:
            asset_class = trade.asset_class.value
            aggregated[asset_class]["realized_pnl"] += trade.fifo_pnl_realized
            aggregated[asset_class]["trade_count"] += 1
            aggregated[asset_class]["commissions"] += abs(trade.ib_commission)

        return dict(aggregated)

    @staticmethod
    def aggregate_by_account(
        portfolio: Portfolio,
    ) -> dict[str, dict[str, Decimal]]:
        """
        Aggregate metrics by account

        Args:
            portfolio: Portfolio instance

        Returns:
            Dict with per-account aggregations
        """
        aggregated: dict[str, dict[str, Decimal]] = {}

        for account in portfolio.accounts:
            aggregated[account.account_id] = {
                "total_value": account.total_value,
                "cash": account.total_cash,
                "position_value": account.total_position_value,
                "unrealized_pnl": account.total_unrealized_pnl,
                "realized_pnl": account.total_realized_pnl,
                "commissions": account.total_commissions,
                "trade_count": Decimal(account.trade_count),
                "position_count": Decimal(account.position_count),
            }

        return aggregated

    @staticmethod
    def calculate_account_allocation(
        portfolio: Portfolio,
    ) -> dict[str, Decimal]:
        """
        Calculate percentage allocation by account

        Args:
            portfolio: Portfolio instance

        Returns:
            Dict mapping account_id to allocation percentage
        """
        total_value = portfolio.total_value

        if total_value == 0:
            return {account.account_id: Decimal("0") for account in portfolio.accounts}

        allocation = {}
        for account in portfolio.accounts:
            allocation[account.account_id] = (account.total_value / total_value) * 100

        return allocation

    @staticmethod
    def calculate_symbol_allocation(
        portfolio: Portfolio,
    ) -> dict[str, Decimal]:
        """
        Calculate percentage allocation by symbol

        Args:
            portfolio: Portfolio instance

        Returns:
            Dict mapping symbol to allocation percentage
        """
        total_value = portfolio.total_position_value

        if total_value == 0:
            return {}

        allocation = {}
        symbol_totals = MultiAccountAggregator.calculate_total_position_by_symbol(portfolio)

        for symbol, (_, value, _) in symbol_totals.items():
            allocation[symbol] = (value / total_value) * 100

        return allocation
