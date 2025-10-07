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

    @staticmethod
    def to_accounts(
        csv_data: str,
        from_date: date,
        to_date: date,
    ) -> dict[str, Account]:
        """
        Convert CSV data containing multiple accounts to Account models

        Args:
            csv_data: Raw CSV string potentially containing multiple accounts
            from_date: Statement start date
            to_date: Statement end date

        Returns:
            Dictionary mapping account_id to Account instance
        """
        from collections import defaultdict

        # Parse all sections
        sections = CSVParser.parse(csv_data)

        # Group rows by ClientAccountID
        accounts_data: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
            lambda: {
                "account_info": [],
                "cash_summary": [],
                "positions": [],
                "trades": [],
            }
        )

        # Group each section by account
        for section_name, rows in sections.items():
            for row in rows:
                account_id = row.get("ClientAccountID", "UNKNOWN")
                accounts_data[account_id][section_name].append(row)

        # Create Account object for each account
        accounts = {}
        for account_id, sections_by_account in accounts_data.items():
            if account_id == "UNKNOWN":
                continue

            # Parse account-specific data
            account_info = CSVParser.parse_account_info(sections_by_account["account_info"])
            cash_balances = CSVParser.parse_cash_summary(sections_by_account["cash_summary"])
            positions = CSVParser.parse_positions(sections_by_account["positions"], account_id)
            trades = CSVParser.parse_trades(sections_by_account["trades"], account_id)

            accounts[account_id] = Account(
                account_id=account_id,
                account_alias=account_info.get("account_alias"),
                account_type=account_info.get("account_type"),
                from_date=from_date,
                to_date=to_date,
                cash_balances=cash_balances,
                positions=positions,
                trades=trades,
                ib_entity=account_info.get("ib_entity"),
            )

        return accounts


class XMLParser:
    """
    Parser for IB Flex Query XML format

    IB Flex Query API returns data in XML format with structure:
    <FlexQueryResponse>
      <FlexStatements>
        <FlexStatement accountId="..." fromDate="..." toDate="...">
          <AccountInformation />
          <CashReport><CashReportCurrency /></CashReport>
          <OpenPositions><OpenPosition /></OpenPositions>
          <Trades><Trade /></Trades>
        </FlexStatement>
      </FlexStatements>
    </FlexQueryResponse>
    """

    @staticmethod
    def parse(xml_data: str) -> dict[str, Any]:
        """
        Parse XML data into structured format

        Args:
            xml_data: Raw XML string from IB Flex Query

        Returns:
            Dict with parsed statements
        """
        import defusedxml.ElementTree as ET  # noqa: N817

        root = ET.fromstring(xml_data)
        statements = root.findall(".//FlexStatement")

        return {"statements": statements}

    @staticmethod
    def _parse_date_yyyymmdd(date_str: Optional[str]) -> date:
        """Parse date string in YYYYMMDD format"""
        if not date_str:
            return date.today()

        try:
            return datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            return date.today()

    @staticmethod
    def _parse_account_info(stmt_elem: Any) -> dict[str, Any]:
        """Parse account information from FlexStatement element"""
        account_info_elem = stmt_elem.find(".//AccountInformation")

        if account_info_elem is not None:
            return {
                "account_id": account_info_elem.get("accountId", ""),
                "account_alias": account_info_elem.get("acctAlias"),
                "account_type": None,  # Not in XML
                "ib_entity": None,  # Not in XML
            }

        return {
            "account_id": stmt_elem.get("accountId", "UNKNOWN"),
            "account_alias": None,
            "account_type": None,
            "ib_entity": None,
        }

    @staticmethod
    def _parse_cash_balances(stmt_elem: Any) -> list[CashBalance]:
        """
        Parse cash report from FlexStatement element

        For XML format, use BASE_SUMMARY which contains USD-converted total cash.
        Individual currency reports (JPY, USD) don't have FX rates in CashReport,
        so using them would require manual FX conversion and lead to incorrect totals.
        """
        balances = []
        cash_reports = stmt_elem.findall(".//CashReportCurrency")

        # For XML format, always use BASE_SUMMARY as it's already in USD
        base_summary_report = None
        for report in cash_reports:
            if report.get("currency") == "BASE_SUMMARY":
                base_summary_report = report
                break

        if base_summary_report is not None:
            # Use BASE_SUMMARY (already converted to USD)
            balance = CashBalance(
                currency="USD",
                starting_cash=Decimal(
                    parse_decimal_safe(base_summary_report.get("startingCash", "0"))
                ),
                ending_cash=Decimal(parse_decimal_safe(base_summary_report.get("endingCash", "0"))),
                ending_settled_cash=Decimal(
                    parse_decimal_safe(base_summary_report.get("endingSettledCash", "0"))
                ),
                deposits=Decimal(parse_decimal_safe(base_summary_report.get("deposits", "0"))),
                withdrawals=Decimal(
                    parse_decimal_safe(base_summary_report.get("withdrawals", "0"))
                ),
                dividends=Decimal(parse_decimal_safe(base_summary_report.get("dividends", "0"))),
                interest=Decimal(
                    parse_decimal_safe(base_summary_report.get("brokerInterest", "0"))
                ),
                commissions=Decimal(
                    parse_decimal_safe(base_summary_report.get("commissions", "0"))
                ),
                fees=Decimal(parse_decimal_safe(base_summary_report.get("otherFees", "0"))),
                net_trades_sales=Decimal(
                    parse_decimal_safe(base_summary_report.get("netTradesSales", "0"))
                ),
                net_trades_purchases=Decimal(
                    parse_decimal_safe(base_summary_report.get("netTradesPurchases", "0"))
                ),
            )
            balances.append(balance)
        else:
            # Fallback: no BASE_SUMMARY found (shouldn't happen with XML format)
            for report in cash_reports:
                currency = report.get("currency", "USD")

                balance = CashBalance(
                    currency=currency,
                    starting_cash=Decimal(parse_decimal_safe(report.get("startingCash", "0"))),
                    ending_cash=Decimal(parse_decimal_safe(report.get("endingCash", "0"))),
                    ending_settled_cash=Decimal(
                        parse_decimal_safe(report.get("endingSettledCash", "0"))
                    ),
                    deposits=Decimal(parse_decimal_safe(report.get("deposits", "0"))),
                    withdrawals=Decimal(parse_decimal_safe(report.get("withdrawals", "0"))),
                    dividends=Decimal(parse_decimal_safe(report.get("dividends", "0"))),
                    interest=Decimal(parse_decimal_safe(report.get("brokerInterest", "0"))),
                    commissions=Decimal(parse_decimal_safe(report.get("commissions", "0"))),
                    fees=Decimal(parse_decimal_safe(report.get("otherFees", "0"))),
                    net_trades_sales=Decimal(parse_decimal_safe(report.get("netTradesSales", "0"))),
                    net_trades_purchases=Decimal(
                        parse_decimal_safe(report.get("netTradesPurchases", "0"))
                    ),
                )
                balances.append(balance)

        return balances

    @staticmethod
    def _parse_positions_xml(stmt_elem: Any, account_id: str) -> list[Position]:
        """Parse open positions from FlexStatement element"""
        positions = []
        position_elems = stmt_elem.findall(".//OpenPosition")

        for pos_elem in position_elems:
            # Map asset class
            asset_class_str = pos_elem.get("assetCategory", "OTHER")
            try:
                asset_class = AssetClass(asset_class_str)
            except ValueError:
                asset_class = AssetClass.OTHER

            # Parse dates
            report_date_str = pos_elem.get("reportDate", "")
            position_date = XMLParser._parse_date_yyyymmdd(report_date_str)

            maturity_date = None
            if pos_elem.get("maturity"):
                maturity_date = XMLParser._parse_date_yyyymmdd(pos_elem.get("maturity"))

            # Parse quantity and calculate average cost
            quantity = Decimal(parse_decimal_safe(pos_elem.get("position", "0")))
            cost_basis = Decimal(parse_decimal_safe(pos_elem.get("costBasisMoney", "0")))

            # Get FX rate to convert to base currency (USD)
            fx_rate = Decimal(parse_decimal_safe(pos_elem.get("fxRateToBase", "1")))

            # Apply FX rate to convert values to USD
            position_value_local = Decimal(parse_decimal_safe(pos_elem.get("positionValue", "0")))
            position_value_usd = position_value_local * fx_rate

            unrealized_pnl_local = Decimal(
                parse_decimal_safe(pos_elem.get("fifoPnlUnrealized", "0"))
            )
            unrealized_pnl_usd = unrealized_pnl_local * fx_rate

            cost_basis_usd = cost_basis * fx_rate

            # Avoid division by zero
            average_cost = cost_basis_usd / quantity if quantity != 0 else Decimal("0")

            position = Position(
                account_id=account_id,
                symbol=pos_elem.get("symbol", ""),
                description=pos_elem.get("description"),
                asset_class=asset_class,
                cusip=pos_elem.get("cusip"),
                isin=pos_elem.get("isin"),
                quantity=quantity,
                multiplier=Decimal(parse_decimal_safe(pos_elem.get("multiplier", "1"))),
                mark_price=Decimal(parse_decimal_safe(pos_elem.get("markPrice", "0"))),
                position_value=position_value_usd,
                average_cost=average_cost,
                cost_basis=cost_basis_usd,
                unrealized_pnl=unrealized_pnl_usd,
                realized_pnl=Decimal("0"),  # Not in OpenPosition
                currency=pos_elem.get("currency", "USD"),
                position_date=position_date,
                coupon_rate=(
                    Decimal(parse_decimal_safe(pos_elem.get("coupon", "0")))
                    if pos_elem.get("coupon")
                    else None
                ),
                maturity_date=maturity_date,
            )
            positions.append(position)

        return positions

    @staticmethod
    def _parse_trades_xml(stmt_elem: Any, account_id: str) -> list[Trade]:
        """Parse trades from FlexStatement element"""
        trades = []
        trade_elems = stmt_elem.findall(".//Trade")

        for trade_elem in trade_elems:
            # Map asset class
            asset_class_str = trade_elem.get("assetCategory", "OTHER")
            try:
                asset_class = AssetClass(asset_class_str)
            except ValueError:
                asset_class = AssetClass.OTHER

            # Map buy/sell
            buy_sell_str = trade_elem.get("buySell", "BUY")
            try:
                buy_sell = BuySell(buy_sell_str)
            except ValueError:
                buy_sell = BuySell.BUY

            # Parse dates
            trade_date = XMLParser._parse_date_yyyymmdd(trade_elem.get("tradeDate"))
            settle_date = XMLParser._parse_date_yyyymmdd(trade_elem.get("settleDateTarget"))

            # Parse order time (if present)
            order_time = None
            order_time_str = trade_elem.get("orderTime")
            if order_time_str:
                # Try parsing orderTime (format: YYYYMMDD;HHMMSS)
                with contextlib.suppress(ValueError):
                    order_time = datetime.strptime(order_time_str, "%Y%m%d;%H%M%S")

            trade = Trade(
                account_id=account_id,
                trade_id=trade_elem.get("tradeID", ""),
                trade_date=trade_date,
                settle_date=settle_date,
                symbol=trade_elem.get("symbol", ""),
                description=trade_elem.get("description"),
                asset_class=asset_class,
                cusip=trade_elem.get("cusip"),
                isin=trade_elem.get("isin"),
                buy_sell=buy_sell,
                quantity=Decimal(parse_decimal_safe(trade_elem.get("quantity", "0"))),
                trade_price=Decimal(parse_decimal_safe(trade_elem.get("tradePrice", "0"))),
                trade_money=Decimal(parse_decimal_safe(trade_elem.get("tradeMoney", "0"))),
                currency=trade_elem.get("currency", "USD"),
                fx_rate_to_base=Decimal(parse_decimal_safe(trade_elem.get("fxRateToBase", "1.0"))),
                ib_commission=Decimal(parse_decimal_safe(trade_elem.get("ibCommission", "0"))),
                ib_commission_currency=trade_elem.get("ibCommissionCurrency", "USD"),
                fifo_pnl_realized=Decimal(
                    parse_decimal_safe(trade_elem.get("fifoPnlRealized", "0"))
                ),
                mtm_pnl=Decimal(parse_decimal_safe(trade_elem.get("mtmPnl", "0"))),
                order_id=trade_elem.get("orderID"),
                execution_id=trade_elem.get("executionID"),
                order_time=order_time,
                notes=trade_elem.get("notes"),
            )
            trades.append(trade)

        return trades

    @staticmethod
    def to_account(
        xml_data: str,
        from_date: date,
        to_date: date,
        account_id: Optional[str] = None,
    ) -> Account:
        """
        Convert XML data to Account model

        Args:
            xml_data: Raw XML string from IB Flex Query
            from_date: Statement start date
            to_date: Statement end date
            account_id: Account ID to extract (uses first if not specified)

        Returns:
            Account instance
        """
        import defusedxml.ElementTree as ET  # noqa: N817

        root = ET.fromstring(xml_data)
        statements = root.findall(".//FlexStatement")

        if not statements:
            raise ValueError("No FlexStatement found in XML data")

        # Find statement for specified account_id, or use first
        target_stmt = None
        if account_id:
            for stmt in statements:
                if stmt.get("accountId") == account_id:
                    target_stmt = stmt
                    break
            if not target_stmt:
                raise ValueError(f"Account {account_id} not found in XML data")
        else:
            target_stmt = statements[0]

        # Parse sections
        account_info = XMLParser._parse_account_info(target_stmt)
        acc_id = account_info.get("account_id", "UNKNOWN")
        cash_balances = XMLParser._parse_cash_balances(target_stmt)
        positions = XMLParser._parse_positions_xml(target_stmt, acc_id)
        trades = XMLParser._parse_trades_xml(target_stmt, acc_id)

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


def detect_format(data: str) -> str:
    """
    Auto-detect data format (XML or CSV)

    Args:
        data: Raw data string

    Returns:
        "xml" or "csv"
    """
    first_line = data.strip().split("\n")[0] if data.strip() else ""

    if first_line.startswith("<"):
        return "xml"
    elif "," in first_line or "ClientAccountID" in first_line:
        return "csv"
    else:
        # Default to XML as IB Flex Query primarily returns XML
        return "xml"
