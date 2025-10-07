"""Trade data model"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BuySell(str, Enum):
    """Buy/Sell indicator"""

    BUY = "BUY"
    SELL = "SELL"


class AssetClass(str, Enum):
    """Asset class types"""

    STOCK = "STK"
    BOND = "BOND"
    OPTION = "OPT"
    FUTURE = "FUT"
    FOREX = "CASH"
    FUND = "FUND"
    OTHER = "OTHER"


class Trade(BaseModel):
    """Trade record"""

    account_id: str = Field(..., description="Account ID")
    trade_id: str = Field(..., description="Unique trade ID")
    trade_date: date = Field(..., description="Trade execution date")
    settle_date: Optional[date] = Field(None, description="Settlement date")

    symbol: str = Field(..., description="Trading symbol")
    description: Optional[str] = Field(None, description="Security description")
    asset_class: AssetClass = Field(..., description="Asset class")
    cusip: Optional[str] = Field(None, description="CUSIP")
    isin: Optional[str] = Field(None, description="ISIN")

    buy_sell: BuySell = Field(..., description="Buy or Sell")
    quantity: Decimal = Field(..., description="Trade quantity")
    trade_price: Decimal = Field(..., description="Execution price")
    trade_money: Decimal = Field(..., description="Trade proceeds (negative for buys)")

    currency: str = Field("USD", description="Currency")
    fx_rate_to_base: Decimal = Field(Decimal("1.0"), description="FX rate to base currency")

    ib_commission: Decimal = Field(Decimal("0"), description="IB commission")
    ib_commission_currency: str = Field("USD", description="Commission currency")

    fifo_pnl_realized: Decimal = Field(Decimal("0"), description="Realized P&L (FIFO)")
    mtm_pnl: Decimal = Field(Decimal("0"), description="Mark-to-market P&L")

    order_id: Optional[str] = Field(None, description="Order ID")
    execution_id: Optional[str] = Field(None, description="Execution ID")
    order_time: Optional[datetime] = Field(None, description="Order time")

    notes: Optional[str] = Field(None, description="Additional notes")

    @field_validator("quantity", "trade_price", mode="before")
    @classmethod
    def convert_to_decimal(cls, v):
        """Convert numeric fields to Decimal"""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v

    @property
    def gross_amount(self) -> Decimal:
        """Gross trade amount (before commissions)"""
        return abs(self.trade_money)

    @property
    def net_amount(self) -> Decimal:
        """Net trade amount (after commissions)"""
        return abs(self.trade_money) - abs(self.ib_commission)

    @property
    def is_buy(self) -> bool:
        """Check if trade is a buy"""
        return self.buy_sell == BuySell.BUY

    @property
    def is_sell(self) -> bool:
        """Check if trade is a sell"""
        return self.buy_sell == BuySell.SELL

    @property
    def commission_rate(self) -> Decimal:
        """Commission as percentage of trade value"""
        if self.gross_amount == 0:
            return Decimal("0")
        return abs(self.ib_commission) / self.gross_amount * 100

    class Config:
        """Pydantic config"""

        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }
