"""Position data model"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from ib_sec_mcp.models.trade import AssetClass


class Position(BaseModel):
    """Current position"""

    account_id: str = Field(..., description="Account ID")
    symbol: str = Field(..., description="Trading symbol")
    description: str | None = Field(None, description="Security description")
    asset_class: AssetClass = Field(..., description="Asset class")

    cusip: str | None = Field(None, description="CUSIP")
    isin: str | None = Field(None, description="ISIN")

    quantity: Decimal = Field(..., description="Position quantity")
    multiplier: Decimal = Field(Decimal("1"), description="Contract multiplier")

    mark_price: Decimal = Field(..., description="Current market price")
    position_value: Decimal = Field(..., description="Current position value")

    average_cost: Decimal = Field(..., description="Average cost basis")
    cost_basis: Decimal = Field(..., description="Total cost basis")

    unrealized_pnl: Decimal = Field(Decimal("0"), description="Unrealized P&L")
    realized_pnl: Decimal = Field(Decimal("0"), description="Realized P&L to date")

    currency: str = Field("USD", description="Currency")
    fx_rate_to_base: Decimal = Field(Decimal("1.0"), description="FX rate to base currency")

    position_date: date = Field(..., description="Position as of date")

    # Bond-specific fields
    coupon_rate: Decimal | None = Field(None, description="Coupon rate (for bonds)")
    maturity_date: date | None = Field(None, description="Maturity date (for bonds)")
    ytm: Decimal | None = Field(None, description="Yield to maturity (for bonds)")
    duration: Decimal | None = Field(None, description="Duration (for bonds)")

    @field_validator("quantity", "mark_price", "position_value", mode="before")
    @classmethod
    def convert_to_decimal(cls, v: int | float | str | Decimal) -> Decimal:
        """Convert numeric fields to Decimal"""
        if isinstance(v, (int, float, str)):
            return Decimal(str(v))
        return v

    @property
    def market_value(self) -> Decimal:
        """Current market value (alias for position_value)"""
        return self.position_value

    @property
    def total_pnl(self) -> Decimal:
        """Total P&L (realized + unrealized)"""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def pnl_percentage(self) -> Decimal:
        """P&L as percentage of cost basis"""
        if self.cost_basis == 0:
            return Decimal("0")
        return (self.unrealized_pnl / self.cost_basis) * 100

    @property
    def is_long(self) -> bool:
        """Check if position is long"""
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        """Check if position is short"""
        return self.quantity < 0

    @property
    def is_bond(self) -> bool:
        """Check if position is a bond"""
        return self.asset_class == AssetClass.BOND

    class Config:
        """Pydantic config"""

        json_encoders = {
            date: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }
