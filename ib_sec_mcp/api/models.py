"""API response models using Pydantic v2"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class FlexQueryStatus(str, Enum):
    """Flex Query request status"""

    SUCCESS = "Success"
    WARN = "Warn"
    FAIL = "Fail"


class FlexQueryResponse(BaseModel):
    """Response from SendRequest API call"""

    status: FlexQueryStatus = Field(..., description="Request status")
    reference_code: str | None = Field(None, description="Reference code for GetStatement")
    url: str | None = Field(None, description="URL to fetch statement")
    error_code: str | None = Field(None, description="Error code if failed")
    error_message: str | None = Field(None, description="Error message if failed")

    @field_validator("reference_code", mode="before")
    @classmethod
    def validate_reference_code(cls, v: str | None) -> str | None:
        """Validate reference code format"""
        if v and not v.isdigit():
            raise ValueError(f"Invalid reference code format: {v}")
        return v


class FlexStatement(BaseModel):
    """Parsed Flex Statement data"""

    query_id: str = Field(..., description="Query ID used")
    account_id: str = Field(..., description="Account ID")
    from_date: date = Field(..., description="Statement start date")
    to_date: date = Field(..., description="Statement end date")
    when_generated: datetime = Field(..., description="Statement generation timestamp")
    raw_data: str = Field(..., description="Raw XML/CSV data")

    class Config:
        """Pydantic config"""

        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
        }


class AccountInfo(BaseModel):
    """Account information section"""

    account_id: str = Field(..., alias="ClientAccountID")
    account_alias: str | None = Field(None, alias="AccountAlias")
    account_type: str | None = Field(None, alias="AccountType")
    customer_type: str | None = Field(None, alias="CustomerType")
    account_capabilities: str | None = Field(None, alias="AccountCapabilities")
    trading_permissions: str | None = Field(None, alias="TradingPermissions")
    date_opened: date | None = Field(None, alias="DateOpened")
    date_funded: date | None = Field(None, alias="DateFunded")
    date_closed: date | None = Field(None, alias="DateClosed")
    master_name: str | None = Field(None, alias="MasterName")
    ib_entity: str | None = Field(None, alias="IBEntity")
    primary_email: str | None = Field(None, alias="PrimaryEmail")
    street: str | None = Field(None, alias="Street")
    city: str | None = Field(None, alias="City")
    state: str | None = Field(None, alias="State")
    country: str | None = Field(None, alias="Country")
    postal_code: str | None = Field(None, alias="PostalCode")

    class Config:
        """Pydantic config"""

        populate_by_name = True


class CashSummary(BaseModel):
    """Cash summary section"""

    account_id: str = Field(..., alias="ClientAccountID")
    acct_alias: str | None = Field(None, alias="AcctAlias")
    model: str | None = Field(None, alias="Model")
    currency: str = Field(..., alias="Currency")
    from_date: date = Field(..., alias="FromDate")
    to_date: date = Field(..., alias="ToDate")
    starting_cash: Decimal = Field(..., alias="StartingCash")
    starting_cash_sec: Decimal = Field(Decimal("0"), alias="StartingCashSec")
    client_fees: Decimal = Field(Decimal("0"), alias="ClientFees")
    commissions: Decimal = Field(Decimal("0"), alias="Commissions")
    deposits_withdrawals: Decimal = Field(Decimal("0"), alias="DepositsWithdrawals")
    deposits: Decimal = Field(Decimal("0"), alias="Deposits")
    withdrawals: Decimal = Field(Decimal("0"), alias="Withdrawals")
    account_transfers: Decimal = Field(Decimal("0"), alias="AccountTransfers")
    internal_transfers: Decimal = Field(Decimal("0"), alias="InternalTransfers")
    dividends: Decimal = Field(Decimal("0"), alias="Dividends")
    change_in_dividend_accruals: Decimal = Field(Decimal("0"), alias="ChangeInDividendAccruals")
    interest: Decimal = Field(Decimal("0"), alias="Interest")
    change_in_interest_accruals: Decimal = Field(Decimal("0"), alias="ChangeInInterestAccruals")
    soft_dollars: Decimal = Field(Decimal("0"), alias="SoftDollars")
    net_trades_sales: Decimal = Field(Decimal("0"), alias="NetTradesSales")
    net_trades_purchases: Decimal = Field(Decimal("0"), alias="NetTradesPurchases")
    other_fees: Decimal = Field(Decimal("0"), alias="OtherFees")
    ending_cash: Decimal = Field(..., alias="EndingCash")
    ending_cash_sec: Decimal = Field(Decimal("0"), alias="EndingCashSec")
    ending_settled_cash: Decimal = Field(..., alias="EndingSettledCash")

    class Config:
        """Pydantic config"""

        populate_by_name = True


class APICredentials(BaseModel):
    """API credentials for a single account"""

    query_id: str = Field(..., description="Flex Query ID")
    token: str = Field(..., description="Flex Query Token")
    account_id: str | None = Field(None, description="Account ID (optional identifier)")
    account_alias: str | None = Field(None, description="Human-readable account name")

    @field_validator("query_id", "token")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate credentials are not empty"""
        if not v or not v.strip():
            raise ValueError("Credentials cannot be empty")
        return v.strip()
