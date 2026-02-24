"""Tests for XMLParser and detect_format"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import defusedxml.ElementTree as ET  # noqa: N817
import pytest

from ib_sec_mcp.core.parsers import XMLParser, detect_format
from ib_sec_mcp.models.trade import AssetClass, BuySell

MINIMAL_XML = """\
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U1234567" acctAlias="TestAlias"/>
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="10000" endingCash="11000" endingSettledCash="10500"
          deposits="2000" withdrawals="500" dividends="100"
          brokerInterest="50" commissions="-25" otherFees="-10"
          netTradesSales="5000" netTradesPurchases="-4000"/>
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="AAPL" description="APPLE INC" assetCategory="STK"
          position="100" markPrice="150.50" positionValue="15050"
          costBasisMoney="12000" fifoPnlUnrealized="3050"
          reportDate="20250131" multiplier="1" currency="USD"
          fxRateToBase="1"/>
      </OpenPositions>
      <Trades>
        <Trade tradeID="T001" symbol="AAPL" description="APPLE INC"
          assetCategory="STK" buySell="BUY" quantity="100"
          tradePrice="120.00" tradeMoney="-12000" tradeDate="20250115"
          settleDateTarget="20250117" currency="USD" fxRateToBase="1.0"
          ibCommission="-1.50" ibCommissionCurrency="USD"
          fifoPnlRealized="0" mtmPnl="3050"
          orderID="O001" executionID="E001"
          orderTime="20250115;103000"/>
      </Trades>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

MULTI_ACCOUNT_XML = """\
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1111111" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U1111111" acctAlias="Account1"/>
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="5000" endingCash="6000" endingSettledCash="6000"/>
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="AAPL" assetCategory="STK" position="50"
          markPrice="150" positionValue="7500" costBasisMoney="6000"
          fifoPnlUnrealized="1500" reportDate="20250131" multiplier="1"
          currency="USD" fxRateToBase="1"/>
      </OpenPositions>
      <Trades/>
    </FlexStatement>
    <FlexStatement accountId="U2222222" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U2222222" acctAlias="Account2"/>
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="3000" endingCash="4000" endingSettledCash="4000"/>
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="TSLA" assetCategory="STK" position="20"
          markPrice="200" positionValue="4000" costBasisMoney="3500"
          fifoPnlUnrealized="500" reportDate="20250131" multiplier="1"
          currency="USD" fxRateToBase="1"/>
      </OpenPositions>
      <Trades/>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

BOND_POSITION_XML = """\
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U1234567"/>
      <CashReport/>
      <OpenPositions>
        <OpenPosition symbol="US912810TD00" description="T-BOND 30Y"
          assetCategory="BOND" position="10000" markPrice="95.50"
          positionValue="9550" costBasisMoney="9000"
          fifoPnlUnrealized="550" reportDate="20250131" multiplier="1"
          currency="USD" fxRateToBase="1" coupon="4.5"
          maturity="20301231"/>
      </OpenPositions>
      <Trades/>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

NO_ACCOUNT_INFO_XML = """\
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U9999999" fromDate="20250101" toDate="20250131">
      <CashReport/>
      <OpenPositions/>
      <Trades/>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

NO_STATEMENTS_XML = """\
<FlexQueryResponse>
  <FlexStatements/>
</FlexQueryResponse>"""

FX_RATE_XML = """\
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U1234567"/>
      <CashReport/>
      <OpenPositions>
        <OpenPosition symbol="9433.T" assetCategory="STK" position="100"
          markPrice="5000" positionValue="500000" costBasisMoney="450000"
          fifoPnlUnrealized="50000" reportDate="20250131" multiplier="1"
          currency="JPY" fxRateToBase="0.006547"/>
      </OpenPositions>
      <Trades/>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

FALLBACK_CASH_XML = """\
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U1234567"/>
      <CashReport>
        <CashReportCurrency currency="USD"
          startingCash="5000" endingCash="6000" endingSettledCash="5500"/>
        <CashReportCurrency currency="JPY"
          startingCash="100000" endingCash="120000" endingSettledCash="110000"/>
      </CashReport>
      <OpenPositions/>
      <Trades/>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""


class TestXMLParserParse:
    """Tests for XMLParser.parse()"""

    def test_parse_returns_statements(self) -> None:
        result = XMLParser.parse(MINIMAL_XML)
        assert "statements" in result
        assert len(result["statements"]) == 1

    def test_parse_multi_account(self) -> None:
        result = XMLParser.parse(MULTI_ACCOUNT_XML)
        assert len(result["statements"]) == 2

    def test_parse_invalid_xml_raises(self) -> None:
        with pytest.raises(ET.ParseError):
            XMLParser.parse("not xml data")


class TestParseDateYYYYMMDD:
    """Tests for XMLParser._parse_date_yyyymmdd()"""

    def test_valid_date(self) -> None:
        result = XMLParser._parse_date_yyyymmdd("20250115")
        assert result == date(2025, 1, 15)

    def test_empty_string(self) -> None:
        with patch("ib_sec_mcp.core.parsers.date") as mock_date:
            mock_date.today.return_value = date(2025, 1, 1)
            result = XMLParser._parse_date_yyyymmdd("")
            assert result == date(2025, 1, 1)

    def test_none(self) -> None:
        with patch("ib_sec_mcp.core.parsers.date") as mock_date:
            mock_date.today.return_value = date(2025, 1, 1)
            result = XMLParser._parse_date_yyyymmdd(None)
            assert result == date(2025, 1, 1)

    def test_invalid_format(self) -> None:
        with patch("ib_sec_mcp.core.parsers.date") as mock_date:
            mock_date.today.return_value = date(2025, 1, 1)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            result = XMLParser._parse_date_yyyymmdd("2025-01-15")
            assert result == date(2025, 1, 1)


class TestParseAccountInfo:
    """Tests for XMLParser._parse_account_info()"""

    def test_with_account_information(self) -> None:
        root = ET.fromstring(MINIMAL_XML)
        stmt = root.findall(".//FlexStatement")[0]
        info = XMLParser._parse_account_info(stmt)
        assert info["account_id"] == "U1234567"
        assert info["account_alias"] == "TestAlias"

    def test_without_account_information(self) -> None:
        root = ET.fromstring(NO_ACCOUNT_INFO_XML)
        stmt = root.findall(".//FlexStatement")[0]
        info = XMLParser._parse_account_info(stmt)
        assert info["account_id"] == "U9999999"
        assert info["account_alias"] is None


class TestParseCashBalances:
    """Tests for XMLParser._parse_cash_balances()"""

    def test_base_summary(self) -> None:
        root = ET.fromstring(MINIMAL_XML)
        stmt = root.findall(".//FlexStatement")[0]
        balances = XMLParser._parse_cash_balances(stmt)
        assert len(balances) == 1
        assert balances[0].currency == "USD"
        assert balances[0].starting_cash == Decimal("10000")
        assert balances[0].ending_cash == Decimal("11000")
        assert balances[0].dividends == Decimal("100")

    def test_fallback_no_base_summary(self) -> None:
        root = ET.fromstring(FALLBACK_CASH_XML)
        stmt = root.findall(".//FlexStatement")[0]
        balances = XMLParser._parse_cash_balances(stmt)
        assert len(balances) == 2
        currencies = {b.currency for b in balances}
        assert "USD" in currencies
        assert "JPY" in currencies

    def test_empty_cash_report(self) -> None:
        root = ET.fromstring(NO_ACCOUNT_INFO_XML)
        stmt = root.findall(".//FlexStatement")[0]
        balances = XMLParser._parse_cash_balances(stmt)
        assert balances == []


class TestParsePositionsXML:
    """Tests for XMLParser._parse_positions_xml()"""

    def test_stock_position(self) -> None:
        root = ET.fromstring(MINIMAL_XML)
        stmt = root.findall(".//FlexStatement")[0]
        positions = XMLParser._parse_positions_xml(stmt, "U1234567")
        assert len(positions) == 1
        pos = positions[0]
        assert pos.symbol == "AAPL"
        assert pos.asset_class == AssetClass.STOCK
        assert pos.quantity == Decimal("100")
        assert pos.account_id == "U1234567"

    def test_bond_position_with_maturity(self) -> None:
        root = ET.fromstring(BOND_POSITION_XML)
        stmt = root.findall(".//FlexStatement")[0]
        positions = XMLParser._parse_positions_xml(stmt, "U1234567")
        assert len(positions) == 1
        pos = positions[0]
        assert pos.asset_class == AssetClass.BOND
        assert pos.coupon_rate == Decimal("4.5")
        assert pos.maturity_date == date(2030, 12, 31)

    def test_fx_rate_conversion(self) -> None:
        root = ET.fromstring(FX_RATE_XML)
        stmt = root.findall(".//FlexStatement")[0]
        positions = XMLParser._parse_positions_xml(stmt, "U1234567")
        assert len(positions) == 1
        pos = positions[0]
        assert pos.fx_rate_to_base == Decimal("0.006547")
        # Position value should be converted: 500000 * 0.006547
        expected_value = Decimal("500000") * Decimal("0.006547")
        assert abs(pos.position_value - expected_value) < Decimal("0.01")

    def test_zero_quantity(self) -> None:
        xml = """\
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <OpenPositions>
        <OpenPosition symbol="AAPL" assetCategory="STK" position="0"
          markPrice="150" positionValue="0" costBasisMoney="0"
          fifoPnlUnrealized="0" reportDate="20250131" multiplier="1"
          currency="USD" fxRateToBase="1"/>
      </OpenPositions>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

        root = ET.fromstring(xml)
        stmt = root.findall(".//FlexStatement")[0]
        positions = XMLParser._parse_positions_xml(stmt, "U1234567")
        assert positions[0].average_cost == Decimal("0")

    def test_invalid_asset_class(self) -> None:
        xml = """\
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <OpenPositions>
        <OpenPosition symbol="XXX" assetCategory="UNKNOWN_TYPE" position="10"
          markPrice="100" positionValue="1000" costBasisMoney="900"
          fifoPnlUnrealized="100" reportDate="20250131" multiplier="1"
          currency="USD" fxRateToBase="1"/>
      </OpenPositions>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

        root = ET.fromstring(xml)
        stmt = root.findall(".//FlexStatement")[0]
        positions = XMLParser._parse_positions_xml(stmt, "U1234567")
        assert positions[0].asset_class == AssetClass.OTHER

    def test_empty_positions(self) -> None:
        root = ET.fromstring(NO_ACCOUNT_INFO_XML)
        stmt = root.findall(".//FlexStatement")[0]
        positions = XMLParser._parse_positions_xml(stmt, "U1234567")
        assert positions == []


class TestParseTradesXML:
    """Tests for XMLParser._parse_trades_xml()"""

    def test_trade_parsing(self) -> None:
        root = ET.fromstring(MINIMAL_XML)
        stmt = root.findall(".//FlexStatement")[0]
        trades = XMLParser._parse_trades_xml(stmt, "U1234567")
        assert len(trades) == 1
        trade = trades[0]
        assert trade.trade_id == "T001"
        assert trade.symbol == "AAPL"
        assert trade.buy_sell == BuySell.BUY
        assert trade.asset_class == AssetClass.STOCK
        assert trade.quantity == Decimal("100")
        assert trade.trade_price == Decimal("120.00")
        assert trade.trade_date == date(2025, 1, 15)
        assert trade.settle_date == date(2025, 1, 17)

    def test_order_time_parsing(self) -> None:
        root = ET.fromstring(MINIMAL_XML)
        stmt = root.findall(".//FlexStatement")[0]
        trades = XMLParser._parse_trades_xml(stmt, "U1234567")
        trade = trades[0]
        assert trade.order_time is not None
        assert trade.order_time.hour == 10
        assert trade.order_time.minute == 30

    def test_sell_trade(self) -> None:
        xml = """\
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <Trades>
        <Trade tradeID="T002" symbol="AAPL" assetCategory="STK" buySell="SELL"
          quantity="-100" tradePrice="160.00" tradeMoney="16000"
          tradeDate="20250120" currency="USD" fxRateToBase="1.0"
          ibCommission="-1.50" fifoPnlRealized="4000" mtmPnl="0"/>
      </Trades>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

        root = ET.fromstring(xml)
        stmt = root.findall(".//FlexStatement")[0]
        trades = XMLParser._parse_trades_xml(stmt, "U1234567")
        assert trades[0].buy_sell == BuySell.SELL

    def test_invalid_buy_sell(self) -> None:
        xml = """\
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <Trades>
        <Trade tradeID="T003" symbol="AAPL" assetCategory="STK" buySell="INVALID"
          quantity="100" tradePrice="150.00" tradeMoney="-15000"
          tradeDate="20250120" currency="USD" fxRateToBase="1.0"
          ibCommission="0" fifoPnlRealized="0" mtmPnl="0"/>
      </Trades>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

        root = ET.fromstring(xml)
        stmt = root.findall(".//FlexStatement")[0]
        trades = XMLParser._parse_trades_xml(stmt, "U1234567")
        assert trades[0].buy_sell == BuySell.BUY  # fallback

    def test_empty_trades(self) -> None:
        root = ET.fromstring(NO_ACCOUNT_INFO_XML)
        stmt = root.findall(".//FlexStatement")[0]
        trades = XMLParser._parse_trades_xml(stmt, "U1234567")
        assert trades == []


class TestToAccount:
    """Tests for XMLParser.to_account()"""

    def test_single_account(self) -> None:
        account = XMLParser.to_account(
            MINIMAL_XML, from_date=date(2025, 1, 1), to_date=date(2025, 1, 31)
        )
        assert account.account_id == "U1234567"
        assert account.account_alias == "TestAlias"
        assert len(account.positions) == 1
        assert len(account.trades) == 1
        assert len(account.cash_balances) == 1

    def test_specific_account_id(self) -> None:
        account = XMLParser.to_account(
            MULTI_ACCOUNT_XML,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            account_id="U2222222",
        )
        assert account.account_id == "U2222222"
        assert account.positions[0].symbol == "TSLA"

    def test_missing_account_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Account U9999999 not found"):
            XMLParser.to_account(
                MINIMAL_XML,
                from_date=date(2025, 1, 1),
                to_date=date(2025, 1, 31),
                account_id="U9999999",
            )

    def test_no_statements_raises(self) -> None:
        with pytest.raises(ValueError, match="No FlexStatement found"):
            XMLParser.to_account(
                NO_STATEMENTS_XML,
                from_date=date(2025, 1, 1),
                to_date=date(2025, 1, 31),
            )

    def test_uses_first_statement_when_no_id(self) -> None:
        account = XMLParser.to_account(
            MULTI_ACCOUNT_XML,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )
        assert account.account_id == "U1111111"


class TestToAccounts:
    """Tests for XMLParser.to_accounts()"""

    def test_multi_account(self) -> None:
        accounts = XMLParser.to_accounts(
            MULTI_ACCOUNT_XML,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )
        assert len(accounts) == 2
        assert "U1111111" in accounts
        assert "U2222222" in accounts

    def test_single_account(self) -> None:
        accounts = XMLParser.to_accounts(
            MINIMAL_XML,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )
        assert len(accounts) == 1
        assert "U1234567" in accounts

    def test_no_statements_raises(self) -> None:
        with pytest.raises(ValueError, match="No FlexStatement found"):
            XMLParser.to_accounts(
                NO_STATEMENTS_XML,
                from_date=date(2025, 1, 1),
                to_date=date(2025, 1, 31),
            )

    def test_skips_unknown_account(self) -> None:
        xml = """\
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement fromDate="20250101" toDate="20250131">
      <CashReport/>
      <OpenPositions/>
      <Trades/>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""
        accounts = XMLParser.to_accounts(
            xml,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )
        # Account with UNKNOWN id is skipped (no AccountInformation, fallback is UNKNOWN)
        assert len(accounts) == 0


class TestDetectFormat:
    """Tests for detect_format()"""

    def test_valid_xml(self) -> None:
        assert detect_format("<FlexQueryResponse/>") == "xml"

    def test_xml_with_declaration(self) -> None:
        assert detect_format('<?xml version="1.0"?><root/>') == "xml"

    def test_csv_raises(self) -> None:
        with pytest.raises(ValueError, match="Only XML format is supported"):
            detect_format("AccountId,Symbol,Quantity\nU123,AAPL,100")

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="Only XML format is supported"):
            detect_format("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="Only XML format is supported"):
            detect_format("   \n  ")

    def test_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Only XML format is supported"):
            detect_format('{"key": "value"}')
