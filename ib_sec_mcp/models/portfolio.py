"""Portfolio data model (multi-account aggregation)"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from ib_sec_mcp.models.account import Account
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import Trade


class Portfolio(BaseModel):
    """
    Portfolio containing multiple accounts

    Provides aggregated view across all accounts
    """

    accounts: list[Account] = Field(..., description="List of accounts")
    base_currency: str = Field("USD", description="Base currency for reporting")
    from_date: date = Field(..., description="Portfolio start date")
    to_date: date = Field(..., description="Portfolio end date")

    @property
    def account_count(self) -> int:
        """Number of accounts"""
        return len(self.accounts)

    @property
    def total_value(self) -> Decimal:
        """Total portfolio value across all accounts"""
        total: Decimal = sum((account.total_value for account in self.accounts), Decimal("0"))
        return total

    @property
    def total_cash(self) -> Decimal:
        """Total cash across all accounts"""
        total: Decimal = sum((account.total_cash for account in self.accounts), Decimal("0"))
        return total

    @property
    def total_position_value(self) -> Decimal:
        """Total position value across all accounts"""
        total: Decimal = sum(
            (account.total_position_value for account in self.accounts), Decimal("0")
        )
        return total

    @property
    def total_unrealized_pnl(self) -> Decimal:
        """Total unrealized P&L across all accounts"""
        total: Decimal = sum(
            (account.total_unrealized_pnl for account in self.accounts), Decimal("0")
        )
        return total

    @property
    def total_realized_pnl(self) -> Decimal:
        """Total realized P&L across all accounts"""
        total: Decimal = sum(
            (account.total_realized_pnl for account in self.accounts), Decimal("0")
        )
        return total

    @property
    def total_commissions(self) -> Decimal:
        """Total commissions across all accounts"""
        total: Decimal = sum((account.total_commissions for account in self.accounts), Decimal("0"))
        return total

    @property
    def total_trades(self) -> int:
        """Total number of trades across all accounts"""
        return sum(account.trade_count for account in self.accounts)

    @property
    def total_positions(self) -> int:
        """Total number of positions across all accounts"""
        return sum(account.position_count for account in self.accounts)

    @property
    def all_trades(self) -> list[Trade]:
        """All trades across all accounts"""
        trades = []
        for account in self.accounts:
            trades.extend(account.trades)
        return trades

    @property
    def all_positions(self) -> list[Position]:
        """All positions across all accounts"""
        positions = []
        for account in self.accounts:
            positions.extend(account.positions)
        return positions

    def get_account(self, account_id: str) -> Optional[Account]:
        """Get specific account by ID"""
        for account in self.accounts:
            if account.account_id == account_id:
                return account
        return None

    def get_positions_by_symbol(self, symbol: str) -> list[Position]:
        """Get all positions for a symbol across all accounts"""
        positions = []
        for account in self.accounts:
            position = account.get_position_by_symbol(symbol)
            if position:
                positions.append(position)
        return positions

    def get_trades_by_symbol(self, symbol: str) -> list[Trade]:
        """Get all trades for a symbol across all accounts"""
        trades = []
        for account in self.accounts:
            trades.extend(account.get_trades_by_symbol(symbol))
        return trades

    def get_symbols(self) -> list[str]:
        """Get unique symbols across all accounts"""
        symbols = set()
        for account in self.accounts:
            for position in account.positions:
                symbols.add(position.symbol)
            for trade in account.trades:
                symbols.add(trade.symbol)
        return sorted(symbols)

    def aggregate_positions_by_symbol(self) -> dict[str, Decimal]:
        """
        Aggregate position quantities by symbol across all accounts

        Returns:
            Dict mapping symbol to total quantity
        """
        aggregated: dict[str, Decimal] = {}
        for account in self.accounts:
            for position in account.positions:
                if position.symbol in aggregated:
                    aggregated[position.symbol] += position.quantity
                else:
                    aggregated[position.symbol] = position.quantity
        return aggregated

    @classmethod
    def from_accounts(
        cls,
        accounts: list[Account],
        base_currency: str = "USD",
    ) -> "Portfolio":
        """
        Create portfolio from list of accounts

        Args:
            accounts: List of Account objects
            base_currency: Base currency for reporting

        Returns:
            Portfolio instance
        """
        if not accounts:
            raise ValueError("At least one account is required")

        # Use earliest from_date and latest to_date
        from_date = min(account.from_date for account in accounts)
        to_date = max(account.to_date for account in accounts)

        return cls(
            accounts=accounts,
            base_currency=base_currency,
            from_date=from_date,
            to_date=to_date,
        )

    class Config:
        """Pydantic config"""

        json_encoders = {
            date: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }
