"""IB Client Portal Gateway API response models using Pydantic v2"""

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CPAuthStatus(BaseModel):
    """Authentication status from Client Portal Gateway"""

    model_config = ConfigDict(populate_by_name=True)

    authenticated: bool = Field(..., description="Whether session is authenticated")
    competing: bool = Field(False, description="Whether competing session exists")
    connected: bool = Field(False, description="Whether connected to server")
    message: str = Field("", description="Status message")


class CPOrderSide(StrEnum):
    """Order side enumeration"""

    BUY = "BUY"
    SELL = "SELL"


class CPOrderStatus(StrEnum):
    """Order status enumeration"""

    SUBMITTED = "Submitted"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    INACTIVE = "Inactive"
    PENDING_SUBMIT = "PendingSubmit"
    PENDING_CANCEL = "PendingCancel"
    PRE_SUBMITTED = "PreSubmitted"


class CPOrder(BaseModel):
    """Order from Client Portal Gateway"""

    model_config = ConfigDict(populate_by_name=True)

    order_id: int = Field(..., alias="orderId", description="Order ID")
    symbol: str = Field(..., description="Trading symbol")
    side: CPOrderSide = Field(..., description="Order side (BUY/SELL)")
    quantity: Decimal = Field(..., alias="totalSize", description="Order quantity")
    price: Decimal = Field(Decimal("0"), alias="price", description="Limit price")
    avg_price: Decimal = Field(Decimal("0"), alias="avgPrice", description="Average fill price")
    status: CPOrderStatus = Field(..., description="Order status")
    order_type: str = Field("", alias="orderType", description="Order type")
    account_id: str = Field("", alias="acct", description="Account ID")


class CPAccountBalance(BaseModel):
    """Account balance summary from Client Portal Gateway"""

    model_config = ConfigDict(populate_by_name=True)

    account_id: str = Field(..., description="Account ID")
    net_liquidation: Decimal = Field(
        Decimal("0"),
        alias="netliquidation",
        description="Net liquidation value",
    )
    total_cash: Decimal = Field(
        Decimal("0"),
        alias="totalcashvalue",
        description="Total cash value",
    )
    buying_power: Decimal = Field(
        Decimal("0"),
        alias="buyingpower",
        description="Buying power",
    )
    gross_position_value: Decimal = Field(
        Decimal("0"),
        alias="grosspositionvalue",
        description="Gross position value",
    )


class CPPosition(BaseModel):
    """Position from Client Portal Gateway"""

    model_config = ConfigDict(populate_by_name=True)

    account_id: str = Field(..., alias="acctId", description="Account ID")
    contract_id: int = Field(..., alias="conid", description="Contract ID")
    symbol: str = Field("", description="Trading symbol")
    position: Decimal = Field(..., description="Position quantity")
    market_price: Decimal = Field(Decimal("0"), alias="mktPrice", description="Market price")
    market_value: Decimal = Field(Decimal("0"), alias="mktValue", description="Market value")
    avg_cost: Decimal = Field(Decimal("0"), alias="avgCost", description="Average cost")
    unrealized_pnl: Decimal = Field(
        Decimal("0"),
        alias="unrealizedPnl",
        description="Unrealized P&L",
    )
    currency: str = Field("USD", description="Currency")


class CPOrderType(StrEnum):
    """Order type enumeration"""

    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"
    STOP_LIMIT = "STP_LMT"


class CPOrderRequest(BaseModel):
    """Order placement request for Client Portal Gateway"""

    model_config = ConfigDict(populate_by_name=True)

    account_id: str = Field(..., alias="acctId", description="Account ID")
    contract_id: int = Field(..., alias="conid", description="Contract ID")
    side: CPOrderSide = Field(..., description="Order side (BUY/SELL)")
    quantity: Decimal = Field(..., description="Order quantity")
    order_type: CPOrderType = Field(..., alias="orderType", description="Order type")
    price: Decimal | None = Field(None, description="Limit price (required for LMT/STP_LMT)")
    tif: str = Field("GTC", description="Time in force (GTC, DAY, IOC)")

    def to_api_dict(self) -> dict[str, object]:
        """Convert to IB CP API request format."""
        d: dict[str, object] = {
            "acctId": self.account_id,
            "conid": self.contract_id,
            "side": self.side.value,
            "quantity": float(self.quantity),
            "orderType": self.order_type.value,
            "tif": self.tif,
        }
        if self.price is not None:
            d["price"] = float(self.price)
        return d


class CPOrderReply(BaseModel):
    """Order reply from Client Portal Gateway (confirmation step)"""

    model_config = ConfigDict(populate_by_name=True)

    order_id: str | None = Field(None, alias="order_id", description="Order ID after placement")
    order_status: str | None = Field(
        None, alias="order_status", description="Order status after placement"
    )
    message: list[str] | None = Field(None, description="Confirmation messages")
    reply_id: str | None = Field(None, alias="id", description="Reply ID for confirmation")
