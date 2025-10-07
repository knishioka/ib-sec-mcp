"""Account data model"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import Trade


class CashBalance(BaseModel):
    """Cash balance for a specific currency"""

    currency: str = Field(..., description="Currency code")
    starting_cash: Decimal = Field(..., description="Starting cash balance")
    ending_cash: Decimal = Field(..., description="Ending cash balance")
    ending_settled_cash: Decimal = Field(..., description="Ending settled cash")

    deposits: Decimal = Field(Decimal("0"), description="Deposits")
    withdrawals: Decimal = Field(Decimal("0"), description="Withdrawals")

    dividends: Decimal = Field(Decimal("0"), description="Dividends received")
    interest: Decimal = Field(Decimal("0"), description="Interest received")

    commissions: Decimal = Field(Decimal("0"), description="Total commissions")
    fees: Decimal = Field(Decimal("0"), description="Total fees")

    net_trades_sales: Decimal = Field(Decimal("0"), description="Net from sales")
    net_trades_purchases: Decimal = Field(Decimal("0"), description="Net from purchases")

    @field_validator(
        "starting_cash",
        "ending_cash",
        "ending_settled_cash",
        "deposits",
        "withdrawals",
        mode="before",
    )
    @classmethod
    def convert_to_decimal(cls, v):
        """Convert numeric fields to Decimal"""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v

    @property
    def net_change(self) -> Decimal:
        """Net change in cash balance"""
        return self.ending_cash - self.starting_cash

    @property
    def total_deposits_withdrawals(self) -> Decimal:
        """Net deposits/withdrawals"""
        return self.deposits - self.withdrawals

    class Config:
        """Pydantic config"""

        json_encoders = {
            Decimal: lambda v: str(v),
        }


class Account(BaseModel):
    """Account information and data"""

    account_id: str = Field(..., description="Account ID")
    account_alias: Optional[str] = Field(None, description="Account alias")
    account_type: Optional[str] = Field(None, description="Account type")

    from_date: date = Field(..., description="Statement start date")
    to_date: date = Field(..., description="Statement end date")

    cash_balances: list[CashBalance] = Field(
        default_factory=list, description="Cash balances by currency"
    )
    positions: list[Position] = Field(default_factory=list, description="Current positions")
    trades: list[Trade] = Field(default_factory=list, description="Trades in period")

    # Metadata
    base_currency: str = Field("USD", description="Base currency for reporting")
    ib_entity: Optional[str] = Field(None, description="IB entity")

    @property
    def total_cash(self) -> Decimal:
        """Total cash in base currency"""
        return sum(balance.ending_cash for balance in self.cash_balances)

    @property
    def total_position_value(self) -> Decimal:
        """Total position value in base currency"""
        return sum(position.position_value for position in self.positions)

    @property
    def total_value(self) -> Decimal:
        """Total account value (cash + positions)"""
        return self.total_cash + self.total_position_value

    @property
    def total_unrealized_pnl(self) -> Decimal:
        """Total unrealized P&L"""
        return sum(position.unrealized_pnl for position in self.positions)

    @property
    def total_realized_pnl(self) -> Decimal:
        """Total realized P&L from trades"""
        return sum(trade.fifo_pnl_realized for trade in self.trades)

    @property
    def total_commissions(self) -> Decimal:
        """Total commissions paid"""
        return sum(abs(trade.ib_commission) for trade in self.trades)

    @property
    def trade_count(self) -> int:
        """Number of trades"""
        return len(self.trades)

    @property
    def position_count(self) -> int:
        """Number of positions"""
        return len(self.positions)

    def get_trades_by_symbol(self, symbol: str) -> list[Trade]:
        """Get all trades for a specific symbol"""
        return [trade for trade in self.trades if trade.symbol == symbol]

    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        for position in self.positions:
            if position.symbol == symbol:
                return position
        return None

    def get_cash_balance(self, currency: str = "USD") -> Optional[CashBalance]:
        """Get cash balance for a specific currency"""
        for balance in self.cash_balances:
            if balance.currency == currency:
                return balance
        return None

    class Config:
        """Pydantic config"""

        json_encoders = {
            date: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }
