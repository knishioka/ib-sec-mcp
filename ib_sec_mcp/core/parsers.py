"""CSV and XML parsers for IB Flex Query data"""

import contextlib
import csv
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from typing import Any, Optional

from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass, BuySell, Trade
from ib_sec_mcp.utils.validators import parse_decimal_safe


class CSVParser:
    """
    Parser for IB Flex Query CSV format

    The CSV format contains multiple sections with different headers:
    - Account Information
    - Cash Report
    - Open Positions
    - Trades
    """

    @staticmethod
    def parse(csv_data: str, account_id: Optional[str] = None) -> dict[str, list[dict[str, str]]]:
        """
        Parse CSV data into sections

        Args:
            csv_data: Raw CSV string
            account_id: Account ID (optional, extracted if not provided)

        Returns:
            Dict with sections: account_info, cash_summary, positions, trades
        """
        sections: dict[str, list[dict[str, str]]] = {
            "account_info": [],
            "cash_summary": [],
            "positions": [],
            "trades": [],
        }

        current_section: Optional[str] = None
        headers: list[str] = []

        reader = csv.reader(StringIO(csv_data))

        for row in reader:
            if not row or not row[0]:
                continue

            # Detect section by first column
            if row[0] == "ClientAccountID":
                headers = row

                # Determine section type from headers
                if "Name" in headers:
                    current_section = "account_info"
                elif "StartingCash" in headers and "EndingCash" in headers:
                    current_section = "cash_summary"
                elif "Quantity" in headers and "MarkPrice" in headers:
                    current_section = "positions"
                elif "TradeID" in headers:
                    current_section = "trades"
                else:
                    current_section = None

            elif current_section and headers:
                # Parse data row
                row_dict = dict(zip(headers, row))
                sections[current_section].append(row_dict)

        return sections

    @staticmethod
    def parse_account_info(rows: list[dict[str, str]]) -> dict[str, Any]:
        """Parse account information section"""
        if not rows:
            return {}

        row = rows[0]
        return {
            "account_id": row.get("ClientAccountID", ""),
            "account_alias": row.get("AccountAlias"),
            "account_type": row.get("AccountType"),
            "ib_entity": row.get("IBEntity"),
        }

    @staticmethod
    def parse_cash_summary(rows: list[dict[str, str]]) -> list[CashBalance]:
        """Parse cash summary section"""
        balances = []

        for row in rows:
            balance = CashBalance(
                currency=row.get("Currency", "USD"),
                starting_cash=Decimal(parse_decimal_safe(row.get("StartingCash", "0"))),
                ending_cash=Decimal(parse_decimal_safe(row.get("EndingCash", "0"))),
                ending_settled_cash=Decimal(parse_decimal_safe(row.get("EndingSettledCash", "0"))),
                deposits=Decimal(parse_decimal_safe(row.get("Deposits", "0"))),
                withdrawals=Decimal(parse_decimal_safe(row.get("Withdrawals", "0"))),
                dividends=Decimal(parse_decimal_safe(row.get("Dividends", "0"))),
                interest=Decimal(parse_decimal_safe(row.get("Interest", "0"))),
                commissions=Decimal(parse_decimal_safe(row.get("Commissions", "0"))),
                fees=Decimal(parse_decimal_safe(row.get("OtherFees", "0"))),
                net_trades_sales=Decimal(parse_decimal_safe(row.get("NetTradesSales", "0"))),
                net_trades_purchases=Decimal(
                    parse_decimal_safe(row.get("NetTradesPurchases", "0"))
                ),
            )
            balances.append(balance)

        return balances

    @staticmethod
    def parse_positions(rows: list[dict[str, str]], account_id: str) -> list[Position]:
        """Parse positions section"""
        positions = []

        for row in rows:
            # Map asset class
            asset_class_str = row.get("AssetClass", "OTHER")
            try:
                asset_class = AssetClass(asset_class_str)
            except ValueError:
                asset_class = AssetClass.OTHER

            # Parse dates
            position_date_str = row.get("ReportDate", "")
            try:
                position_date = datetime.strptime(position_date_str, "%Y%m%d").date()
            except (ValueError, TypeError):
                position_date = date.today()

            maturity_date = None
            if row.get("Maturity"):
                with contextlib.suppress(ValueError, TypeError):
                    maturity_date = datetime.strptime(row.get("Maturity", ""), "%Y%m%d").date()

            position = Position(
                account_id=account_id,
                symbol=row.get("Symbol", ""),
                description=row.get("Description"),
                asset_class=asset_class,
                cusip=row.get("CUSIP"),
                isin=row.get("ISIN"),
                quantity=Decimal(parse_decimal_safe(row.get("Quantity", "0"))),
                multiplier=Decimal(parse_decimal_safe(row.get("Multiplier", "1"))),
                mark_price=Decimal(parse_decimal_safe(row.get("MarkPrice", "0"))),
                position_value=Decimal(parse_decimal_safe(row.get("PositionValue", "0"))),
                average_cost=Decimal(parse_decimal_safe(row.get("CostBasis", "0")))
                / Decimal(parse_decimal_safe(row.get("Quantity", "1"))),
                cost_basis=Decimal(parse_decimal_safe(row.get("CostBasis", "0"))),
                unrealized_pnl=Decimal(parse_decimal_safe(row.get("UnrealizedPnl", "0"))),
                realized_pnl=Decimal(parse_decimal_safe(row.get("RealizedPnl", "0"))),
                currency=row.get("Currency", "USD"),
                position_date=position_date,
                coupon_rate=(
                    Decimal(parse_decimal_safe(row.get("Coupon", "0")))
                    if row.get("Coupon")
                    else None
                ),
                maturity_date=maturity_date,
            )
            positions.append(position)

        return positions

    @staticmethod
    def parse_trades(rows: list[dict[str, str]], account_id: str) -> list[Trade]:
        """Parse trades section"""
        trades = []

        for row in rows:
            # Map asset class
            asset_class_str = row.get("AssetClass", "OTHER")
            try:
                asset_class = AssetClass(asset_class_str)
            except ValueError:
                asset_class = AssetClass.OTHER

            # Map buy/sell
            buy_sell_str = row.get("Buy/Sell", "BUY")
            try:
                buy_sell = BuySell(buy_sell_str)
            except ValueError:
                buy_sell = BuySell.BUY

            # Parse dates
            trade_date = CSVParser._parse_date(row.get("TradeDate", ""))
            settle_date = CSVParser._parse_date(row.get("SettleDateTarget"))
            order_time = CSVParser._parse_datetime(row.get("OrderTime"))

            trade = Trade(
                account_id=account_id,
                trade_id=row.get("TradeID", ""),
                trade_date=trade_date,
                settle_date=settle_date,
                symbol=row.get("Symbol", ""),
                description=row.get("Description"),
                asset_class=asset_class,
                cusip=row.get("CUSIP"),
                isin=row.get("ISIN"),
                buy_sell=buy_sell,
                quantity=Decimal(parse_decimal_safe(row.get("Quantity", "0"))),
                trade_price=Decimal(parse_decimal_safe(row.get("TradePrice", "0"))),
                trade_money=Decimal(parse_decimal_safe(row.get("TradeMoney", "0"))),
                currency=row.get("Currency", "USD"),
                fx_rate_to_base=Decimal(parse_decimal_safe(row.get("FXRateToBase", "1.0"))),
                ib_commission=Decimal(parse_decimal_safe(row.get("IBCommission", "0"))),
                ib_commission_currency=row.get("IBCommissionCurrency", "USD"),
                fifo_pnl_realized=Decimal(parse_decimal_safe(row.get("FifoPnlRealized", "0"))),
                mtm_pnl=Decimal(parse_decimal_safe(row.get("MtmPnl", "0"))),
                order_id=row.get("OrderID"),
                execution_id=row.get("ExecutionID"),
                order_time=order_time,
                notes=row.get("Notes"),
            )
            trades.append(trade)

        return trades

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> date:
        """Parse date string in YYYYMMDD format"""
        if not date_str:
            return date.today()

        try:
            return datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return date.today()

    @staticmethod
    def _parse_datetime(datetime_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string"""
        if not datetime_str:
            return None

        formats = [
            "%Y%m%d;%H%M%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def to_account(
        csv_data: str,
        from_date: date,
        to_date: date,
        account_id: Optional[str] = None,
    ) -> Account:
        """
        Convert CSV data to Account model

        Args:
            csv_data: Raw CSV string
            from_date: Statement start date
            to_date: Statement end date
            account_id: Account ID (extracted if not provided)

        Returns:
            Account instance
        """
        sections = CSVParser.parse(csv_data, account_id)

        # Parse account info
        account_info = CSVParser.parse_account_info(sections["account_info"])
        acc_id = account_id or account_info.get("account_id", "UNKNOWN")

        # Parse sections
        cash_balances = CSVParser.parse_cash_summary(sections["cash_summary"])
        positions = CSVParser.parse_positions(sections["positions"], acc_id)
        trades = CSVParser.parse_trades(sections["trades"], acc_id)

        return Account(
            account_id=acc_id,
            account_alias=account_info.get("account_alias"),
            account_type=account_info.get("account_type"),
            from_date=from_date,
            to_date=to_date,
            cash_balances=cash_balances,
            positions=positions,
            trades=trades,
            ib_entity=account_info.get("ib_entity"),
        )


class XMLParser:
    """
    Parser for IB Flex Query XML format

    TODO: Implement XML parsing (future enhancement)
    """

    @staticmethod
    def parse(xml_data: str) -> dict[str, Any]:
        """Parse XML data (not yet implemented)"""
        raise NotImplementedError("XML parsing not yet implemented")

    @staticmethod
    def to_account(xml_data: str, from_date: date, to_date: date) -> Account:
        """Convert XML data to Account model (not yet implemented)"""
        raise NotImplementedError("XML parsing not yet implemented")
