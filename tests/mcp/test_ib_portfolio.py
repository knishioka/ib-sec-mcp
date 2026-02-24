"""Tests for IB Portfolio MCP tools"""

import json
import warnings
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.mcp.tools.ib_portfolio import _get_or_fetch_data


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv("QUERY_ID", "test_query_id")
    monkeypatch.setenv("TOKEN", "test_token")


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing"""
    return """ClientAccountID,AssetClass,Symbol,Quantity,Price
U12345678,STK,AAPL,100,150.00
U12345678,STK,MSFT,50,300.00"""


@pytest.fixture
def clean_cache():
    """Clean cache before and after test"""
    data_dir = Path("data/raw")
    # Clean before
    if data_dir.exists():
        for f in data_dir.glob("*.csv"):
            f.unlink()
        for f in data_dir.glob("*.xml"):
            f.unlink()
    yield
    # Clean after
    if data_dir.exists():
        for f in data_dir.glob("*.csv"):
            f.unlink()
        for f in data_dir.glob("*.xml"):
            f.unlink()


class TestGetOrFetchData:
    """Tests for _get_or_fetch_data helper function"""

    @pytest.mark.asyncio
    async def test_validate_date_string_invalid(self):
        """Test that invalid date string raises ValidationError"""
        with pytest.raises(ValidationError, match="Invalid date format"):
            await _get_or_fetch_data(start_date="invalid-date")

    @pytest.mark.asyncio
    async def test_validate_date_range_invalid(self):
        """Test that invalid date range raises ValidationError"""
        with pytest.raises(ValidationError, match="cannot be after end date"):
            await _get_or_fetch_data(start_date="2025-12-31", end_date="2025-01-01")

    @pytest.mark.asyncio
    async def test_validate_account_index_negative(self):
        """Test that negative account_index raises ValidationError"""
        with pytest.raises(ValidationError, match="must be non-negative"):
            await _get_or_fetch_data(start_date="2025-01-01", account_index=-1)

    @pytest.mark.asyncio
    async def test_cache_hit(self, mock_env, sample_csv_data, clean_cache):
        """Test that cached file is used when available"""
        # Create cached file (must be .xml to match cache pattern)
        data_dir = Path("data/raw")
        data_dir.mkdir(parents=True, exist_ok=True)
        cached_file = data_dir / "U12345678_2025-01-01_2025-01-31.xml"
        cached_file.write_text(sample_csv_data)

        # Fetch should use cache
        data, from_date, to_date = await _get_or_fetch_data(
            start_date="2025-01-01", end_date="2025-01-31", use_cache=True
        )

        assert data == sample_csv_data
        assert from_date == date(2025, 1, 1)
        assert to_date == date(2025, 1, 31)

    @pytest.mark.asyncio
    async def test_cache_miss_fetches_from_api(self, mock_env, sample_csv_data, clean_cache):
        """Test that API is called when cache misses"""
        # Mock FlexQueryClient
        mock_statement = MagicMock()
        mock_statement.raw_data = sample_csv_data
        mock_statement.account_id = "U12345678"

        with patch("ib_sec_mcp.mcp.tools.ib_portfolio.FlexQueryClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.fetch_statement.return_value = mock_statement
            mock_client_class.return_value = mock_client

            # Fetch should call API
            data, from_date, to_date = await _get_or_fetch_data(
                start_date="2025-01-01", end_date="2025-01-31", use_cache=True
            )

            # Verify API was called
            mock_client.fetch_statement.assert_called_once()

            # Verify data
            assert data == sample_csv_data
            assert from_date == date(2025, 1, 1)
            assert to_date == date(2025, 1, 31)

            # Verify file was cached (implementation saves as .xml)
            data_dir = Path("data/raw")
            cached_files = list(data_dir.glob("*_2025-01-01_2025-01-31.xml"))
            assert len(cached_files) == 1
            assert cached_files[0].read_text() == sample_csv_data

    @pytest.mark.asyncio
    async def test_use_cache_false_always_fetches(self, mock_env, sample_csv_data, clean_cache):
        """Test that use_cache=False always fetches from API"""
        # Create cached file (must be .xml to match cache pattern)
        data_dir = Path("data/raw")
        data_dir.mkdir(parents=True, exist_ok=True)
        cached_file = data_dir / "U12345678_2025-01-01_2025-01-31.xml"
        cached_file.write_text("old_data")

        # Mock FlexQueryClient
        mock_statement = MagicMock()
        mock_statement.raw_data = sample_csv_data
        mock_statement.account_id = "U12345678"

        with patch("ib_sec_mcp.mcp.tools.ib_portfolio.FlexQueryClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.fetch_statement.return_value = mock_statement
            mock_client_class.return_value = mock_client

            # Fetch with use_cache=False should call API
            data, from_date, to_date = await _get_or_fetch_data(
                start_date="2025-01-01", end_date="2025-01-31", use_cache=False
            )

            # Verify API was called
            mock_client.fetch_statement.assert_called_once()

            # Verify new data was fetched
            assert data == sample_csv_data
            assert data != "old_data"

    @pytest.mark.asyncio
    async def test_cache_pattern_matching(self, mock_env, sample_csv_data, clean_cache):
        """Test that cache lookup uses glob pattern matching"""
        # Create cached file with different account ID (must be .xml to match pattern)
        data_dir = Path("data/raw")
        data_dir.mkdir(parents=True, exist_ok=True)
        cached_file = data_dir / "UXXX_2025-01-01_2025-01-31.xml"
        cached_file.write_text(sample_csv_data)

        # Fetch should find file by date pattern, regardless of account ID
        data, from_date, to_date = await _get_or_fetch_data(
            start_date="2025-01-01", end_date="2025-01-31", use_cache=True
        )

        assert data == sample_csv_data
        assert from_date == date(2025, 1, 1)
        assert to_date == date(2025, 1, 31)

    @pytest.mark.asyncio
    async def test_account_index_warning(self, mock_env, sample_csv_data, clean_cache):
        """Test that non-zero account_index triggers warning"""
        # Mock FlexQueryClient
        mock_statement = MagicMock()
        mock_statement.raw_data = sample_csv_data
        mock_statement.account_id = "U12345678"

        # Mock context to capture warnings
        mock_ctx = AsyncMock()

        with patch("ib_sec_mcp.mcp.tools.ib_portfolio.FlexQueryClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.fetch_statement.return_value = mock_statement
            mock_client_class.return_value = mock_client

            # Fetch with account_index != 0
            await _get_or_fetch_data(
                start_date="2025-01-01",
                end_date="2025-01-31",
                account_index=1,
                use_cache=False,
                ctx=mock_ctx,
            )

            # Verify warning was called
            mock_ctx.warning.assert_called_once()
            warning_call = mock_ctx.warning.call_args[0][0]
            assert "account_index 1 specified" in warning_call
            assert "single Flex Query" in warning_call

    @pytest.mark.asyncio
    async def test_default_end_date_is_today(self, mock_env, sample_csv_data, clean_cache):
        """Test that end_date defaults to today when not specified"""
        mock_statement = MagicMock()
        mock_statement.raw_data = sample_csv_data
        mock_statement.account_id = "U12345678"

        with patch("ib_sec_mcp.mcp.tools.ib_portfolio.FlexQueryClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.fetch_statement.return_value = mock_statement
            mock_client_class.return_value = mock_client

            # Fetch without end_date
            data, from_date, to_date = await _get_or_fetch_data(
                start_date="2025-01-01", use_cache=False
            )

            # Verify end_date is today
            assert to_date == date.today()


# XML fixture for consolidated portfolio tests
SAMPLE_XML_MULTI_CURRENCY = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="10000" endingCash="10000" endingSettledCash="10000"
          deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
          commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="CSPX" description="ISHARES CORE S&amp;P 500"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="IE00B5BMR087" position="10" markPrice="735.00"
          positionValue="7350" costBasisMoney="6000" fifoPnlUnrealized="1350"
          reportDate="20250131" multiplier="1" />
        <OpenPosition symbol="9433.T" description="KDDI CORPORATION"
          assetCategory="STK" currency="JPY" fxRateToBase="0.006547"
          isin="JP3496400007" position="100" markPrice="5000"
          positionValue="500000" costBasisMoney="450000" fifoPnlUnrealized="50000"
          reportDate="20250131" multiplier="1" />
        <OpenPosition symbol="IDTL" description="ISHARES USD TRES 20PLUS YR"
          assetCategory="STK" currency="GBP" fxRateToBase="1.27"
          isin="IE00BSKRJZ44" position="100" markPrice="3.20"
          positionValue="320" costBasisMoney="300" fifoPnlUnrealized="20"
          reportDate="20250131" multiplier="1" />
      </OpenPositions>
      <Trades />
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""


class TestConsolidatedPortfolioCurrency:
    """Tests for currency and fx_rate_to_base fields in analyze_consolidated_portfolio"""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("QUERY_ID", "test_query_id")
        monkeypatch.setenv("TOKEN", "test_token")

    @pytest.fixture
    def tool_registry(self):
        """Register tools with a capture MCP and return tool functions"""
        from ib_sec_mcp.mcp.tools.ib_portfolio import register_ib_portfolio_tools

        tools = {}

        class CaptureMCP:
            def tool(self, fn):
                tools[fn.__name__] = fn
                return fn

        register_ib_portfolio_tools(CaptureMCP())
        return tools

    @pytest.mark.asyncio
    async def test_parser_extracts_currency_fields(self, mock_env):
        """Test that the XML parser correctly extracts currency and fx_rate_to_base"""
        from decimal import Decimal

        from ib_sec_mcp.core.parsers import XMLParser, detect_format

        data = SAMPLE_XML_MULTI_CURRENCY
        detect_format(data)
        accounts = XMLParser.to_accounts(data, date(2025, 1, 1), date(2025, 1, 31))
        account = list(accounts.values())[0]

        # Verify all positions have currency info
        for pos in account.positions:
            assert hasattr(pos, "currency")
            assert hasattr(pos, "fx_rate_to_base")

        positions_by_symbol = {p.symbol: p for p in account.positions}

        # Verify currencies parsed correctly
        assert positions_by_symbol["CSPX"].currency == "USD"
        assert positions_by_symbol["9433.T"].currency == "JPY"
        assert positions_by_symbol["IDTL"].currency == "GBP"

        # Verify fx_rate precision (Decimal from string, no float artifacts)
        assert positions_by_symbol["CSPX"].fx_rate_to_base == Decimal("1")
        assert positions_by_symbol["9433.T"].fx_rate_to_base == Decimal("0.006547")
        assert positions_by_symbol["IDTL"].fx_rate_to_base == Decimal("1.27")

    @pytest.mark.asyncio
    async def test_jpy_position_value_converted_to_usd(self, mock_env):
        """Test that JPY position values are correctly converted to USD"""
        from decimal import Decimal

        from ib_sec_mcp.core.parsers import XMLParser, detect_format

        data = SAMPLE_XML_MULTI_CURRENCY
        detect_format(data)
        accounts = XMLParser.to_accounts(data, date(2025, 1, 1), date(2025, 1, 31))
        account = list(accounts.values())[0]

        jpy_position = next(p for p in account.positions if p.symbol == "9433.T")
        assert jpy_position.currency == "JPY"
        assert jpy_position.fx_rate_to_base == Decimal("0.006547")

        # position_value should be local value * fx_rate (500000 * 0.006547 = 3273.5)
        expected_usd = Decimal("500000") * Decimal("0.006547")
        assert jpy_position.position_value == expected_usd

    @pytest.mark.asyncio
    async def test_consolidated_output_includes_currency(self, mock_env, tool_registry):
        """Test that analyze_consolidated_portfolio JSON output includes currency fields"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (
                SAMPLE_XML_MULTI_CURRENCY,
                date(2025, 1, 1),
                date(2025, 1, 31),
            )

            result_json = await tool_registry["analyze_consolidated_portfolio"](
                start_date="2025-01-01", end_date="2025-01-31", use_cache=True
            )
            result = json.loads(result_json)

            # Verify currency fields in consolidated holdings
            holdings = result["consolidated_holdings"]["holdings_by_symbol"]
            holdings_by_symbol = {h["symbol"]: h for h in holdings}

            assert holdings_by_symbol["CSPX"]["currency"] == "USD"
            assert holdings_by_symbol["CSPX"]["fx_rate_to_base"] == "1"

            assert holdings_by_symbol["9433.T"]["currency"] == "JPY"
            assert holdings_by_symbol["9433.T"]["fx_rate_to_base"] == "0.006547"

            assert holdings_by_symbol["IDTL"]["currency"] == "GBP"
            assert holdings_by_symbol["IDTL"]["fx_rate_to_base"] == "1.27"

    @pytest.mark.asyncio
    async def test_holding_entry_includes_currency(self, mock_env, tool_registry):
        """Test that every holding entry includes currency and fx_rate_to_base"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (
                SAMPLE_XML_MULTI_CURRENCY,
                date(2025, 1, 1),
                date(2025, 1, 31),
            )

            result_json = await tool_registry["analyze_consolidated_portfolio"](
                start_date="2025-01-01", end_date="2025-01-31", use_cache=True
            )
            result = json.loads(result_json)

            for holding in result["consolidated_holdings"]["holdings_by_symbol"]:
                assert "currency" in holding, f"{holding['symbol']} missing currency"
                assert "fx_rate_to_base" in holding, f"{holding['symbol']} missing fx_rate_to_base"

    @pytest.mark.asyncio
    async def test_usd_positions_have_fx_rate_1(self, mock_env):
        """Test that USD-denominated positions have fx_rate_to_base of 1"""
        from decimal import Decimal

        from ib_sec_mcp.core.parsers import XMLParser, detect_format

        data = SAMPLE_XML_MULTI_CURRENCY
        detect_format(data)
        accounts = XMLParser.to_accounts(data, date(2025, 1, 1), date(2025, 1, 31))
        account = list(accounts.values())[0]

        usd_position = next(p for p in account.positions if p.symbol == "CSPX")
        assert usd_position.currency == "USD"
        assert usd_position.fx_rate_to_base == Decimal("1")
        # USD position value should equal local value (no conversion)
        assert usd_position.position_value == Decimal("7350")


class TestAnalyzeConsolidatedPortfolioFilePath:
    """
    Tests for Issue #17: file_path parameter in analyze_consolidated_portfolio

    Acceptance Criteria:
    - When file_path is provided, read from local XML file (no API call)
    - Dates are extracted from filename convention {account}_{from}_{to}.xml
    - Invalid file_path raises ValidationError
    - API mode still works with start_date (backward compatibility)
    - Both file_path and start_date absent raises ValidationError
    """

    @pytest.fixture
    def tool_registry(self):
        """Register tools with a CaptureMCP and return tool functions"""
        from ib_sec_mcp.mcp.tools.ib_portfolio import register_ib_portfolio_tools

        tools = {}

        class CaptureMCP:
            def tool(self, fn):
                tools[fn.__name__] = fn
                return fn

        register_ib_portfolio_tools(CaptureMCP())
        return tools

    @pytest.fixture
    def xml_temp_file(self, tmp_path):
        """Write SAMPLE_XML_MULTI_CURRENCY to a temp file with naming convention"""
        xml_file = tmp_path / "U1234567_2025-01-01_2025-01-31.xml"
        xml_file.write_text(SAMPLE_XML_MULTI_CURRENCY)
        return xml_file

    @pytest.mark.asyncio
    async def test_file_path_mode_reads_from_file(self, tool_registry, xml_temp_file):
        """
        Acceptance Criterion: When file_path is provided, data is read from file
        without calling _get_or_fetch_data.
        """
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            result_json = await tool_registry["analyze_consolidated_portfolio"](
                file_path=str(xml_temp_file)
            )

        # _get_or_fetch_data must NOT be called in file mode
        mock_fetch.assert_not_called()

        result = json.loads(result_json)

        # Verify result has expected top-level structure
        assert "num_accounts" in result
        assert "consolidated_holdings" in result
        assert "analysis_period" in result
        assert "total_portfolio_value" in result

        # The sample XML has 1 account with 3 positions
        assert result["num_accounts"] == 1
        assert result["consolidated_holdings"]["num_unique_symbols"] == 3

    @pytest.mark.asyncio
    async def test_file_path_mode_extracts_dates_from_filename(self, tool_registry, xml_temp_file):
        """
        Acceptance Criterion: analysis_period in result reflects dates from filename.

        Filename: U1234567_2025-01-01_2025-01-31.xml
        Expected period: from=2025-01-01, to=2025-01-31
        """
        result_json = await tool_registry["analyze_consolidated_portfolio"](
            file_path=str(xml_temp_file)
        )
        result = json.loads(result_json)

        assert result["analysis_period"]["from"] == "2025-01-01"
        assert result["analysis_period"]["to"] == "2025-01-31"

    @pytest.mark.asyncio
    async def test_file_path_validates_path(self, tool_registry, tmp_path):
        """
        Acceptance Criterion: A non-existent file_path raises ValidationError.
        """
        non_existent = tmp_path / "U9999999_2025-01-01_2025-01-31.xml"
        # File does not exist - validate_file_path should raise ValidationError

        with pytest.raises(ValidationError):
            await tool_registry["analyze_consolidated_portfolio"](file_path=str(non_existent))

    @pytest.mark.asyncio
    async def test_api_mode_still_works(self, tool_registry):
        """
        Acceptance Criterion: API mode (start_date provided, no file_path) still works.
        Backward compatibility must be maintained.
        """
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (
                SAMPLE_XML_MULTI_CURRENCY,
                date(2025, 1, 1),
                date(2025, 1, 31),
            )

            result_json = await tool_registry["analyze_consolidated_portfolio"](
                start_date="2025-01-01", end_date="2025-01-31", use_cache=False
            )

        # _get_or_fetch_data MUST be called in API mode
        mock_fetch.assert_called_once()

        result = json.loads(result_json)
        assert result["num_accounts"] == 1
        assert "consolidated_holdings" in result

    @pytest.mark.asyncio
    async def test_neither_file_path_nor_start_date_raises_error(self, tool_registry):
        """
        Acceptance Criterion: When both file_path and start_date are absent (None),
        a ValidationError is raised with a clear message.
        """
        with pytest.raises(
            ValidationError, match="Either file_path or start_date must be provided"
        ):
            await tool_registry["analyze_consolidated_portfolio"]()


# XML fixture with unrealized losses and trades for tax loss harvesting tests
SAMPLE_XML_TLH = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250630">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="5000" endingCash="5000" endingSettledCash="5000"
          deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
          commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="INDA" description="ISHARES MSCI INDIA ETF"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US46429B5984" position="100" markPrice="45.00"
          positionValue="4500" costBasisMoney="6000" fifoPnlUnrealized="-1500"
          reportDate="20250630" multiplier="1" />
        <OpenPosition symbol="SPY" description="SPDR S&amp;P 500 ETF"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US78462F1030" position="50" markPrice="500.00"
          positionValue="25000" costBasisMoney="20000" fifoPnlUnrealized="5000"
          reportDate="20250630" multiplier="1" />
        <OpenPosition symbol="EEM" description="ISHARES MSCI EMERGING MARKETS"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US4642872349" position="200" markPrice="38.00"
          positionValue="7600" costBasisMoney="9000" fifoPnlUnrealized="-1400"
          reportDate="20250630" multiplier="1" />
      </OpenPositions>
      <Trades>
        <Trade tradeID="T001" accountId="U1234567" symbol="INDA"
          description="ISHARES MSCI INDIA ETF" assetCategory="STK"
          currency="USD" fxRateToBase="1"
          buySell="BUY" quantity="100" tradePrice="60.00"
          tradeMoney="-6000" ibCommission="-1.00" ibCommissionCurrency="USD"
          tradeDate="20250301" settleDate="20250303"
          fifoPnlRealized="0" mtmPnl="0" multiplier="1"
          orderID="O001" execID="E001" />
        <Trade tradeID="T002" accountId="U1234567" symbol="EEM"
          description="ISHARES MSCI EMERGING MARKETS" assetCategory="STK"
          currency="USD" fxRateToBase="1"
          buySell="BUY" quantity="200" tradePrice="45.00"
          tradeMoney="-9000" ibCommission="-1.00" ibCommissionCurrency="USD"
          tradeDate="20250115" settleDate="20250117"
          fifoPnlRealized="0" mtmPnl="0" multiplier="1"
          orderID="O002" execID="E002" />
      </Trades>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

# XML fixture with wash sale scenario (recent buy within 30 days of today)
SAMPLE_XML_WASH_SALE = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250630">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="5000" endingCash="5000" endingSettledCash="5000"
          deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
          commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="INDA" description="ISHARES MSCI INDIA ETF"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US46429B5984" position="100" markPrice="45.00"
          positionValue="4500" costBasisMoney="6000" fifoPnlUnrealized="-1500"
          reportDate="20250630" multiplier="1" />
      </OpenPositions>
      <Trades>
        <Trade tradeID="T001" accountId="U1234567" symbol="INDA"
          description="ISHARES MSCI INDIA ETF" assetCategory="STK"
          currency="USD" fxRateToBase="1"
          buySell="BUY" quantity="50" tradePrice="50.00"
          tradeMoney="-2500" ibCommission="-1.00" ibCommissionCurrency="USD"
          tradeDate="{recent_buy_date}" settleDate="{recent_buy_date}"
          fifoPnlRealized="0" mtmPnl="0" multiplier="1"
          orderID="O001" execID="E001" />
      </Trades>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

# XML fixture with historical wash sale violation
SAMPLE_XML_HISTORICAL_WASH = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250630">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="5000" endingCash="5000" endingSettledCash="5000"
          deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
          commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="INDA" description="ISHARES MSCI INDIA ETF"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US46429B5984" position="100" markPrice="45.00"
          positionValue="4500" costBasisMoney="6000" fifoPnlUnrealized="-1500"
          reportDate="20250630" multiplier="1" />
      </OpenPositions>
      <Trades>
        <Trade tradeID="T001" accountId="U1234567" symbol="INDA"
          description="ISHARES MSCI INDIA ETF" assetCategory="STK"
          currency="USD" fxRateToBase="1"
          buySell="SELL" quantity="-50" tradePrice="40.00"
          tradeMoney="2000" ibCommission="-1.00" ibCommissionCurrency="USD"
          tradeDate="20250301" settleDate="20250303"
          fifoPnlRealized="-500" mtmPnl="0" multiplier="1"
          orderID="O001" execID="E001" />
        <Trade tradeID="T002" accountId="U1234567" symbol="INDA"
          description="ISHARES MSCI INDIA ETF" assetCategory="STK"
          currency="USD" fxRateToBase="1"
          buySell="BUY" quantity="100" tradePrice="42.00"
          tradeMoney="-4200" ibCommission="-1.00" ibCommissionCurrency="USD"
          tradeDate="20250315" settleDate="20250317"
          fifoPnlRealized="0" mtmPnl="0" multiplier="1"
          orderID="O002" execID="E002" />
      </Trades>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

# XML fixture with no loss positions (all gains)
SAMPLE_XML_NO_LOSSES = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250630">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="5000" endingCash="5000" endingSettledCash="5000"
          deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
          commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="SPY" description="SPDR S&amp;P 500 ETF"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US78462F1030" position="50" markPrice="500.00"
          positionValue="25000" costBasisMoney="20000" fifoPnlUnrealized="5000"
          reportDate="20250630" multiplier="1" />
      </OpenPositions>
      <Trades />
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""


class TestCalculateTaxLossHarvesting:
    """Tests for calculate_tax_loss_harvesting MCP tool"""

    @pytest.fixture
    def tool_registry(self):
        """Register tools with a CaptureMCP and return tool functions"""
        from ib_sec_mcp.mcp.tools.ib_portfolio import register_ib_portfolio_tools

        tools = {}

        class CaptureMCP:
            def tool(self, fn):
                tools[fn.__name__] = fn
                return fn

        register_ib_portfolio_tools(CaptureMCP())
        return tools

    @pytest.mark.asyncio
    async def test_identifies_loss_positions(self, tool_registry):
        """Positions with unrealized losses should be included in results"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_TLH, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        # Should find INDA (-1500) and EEM (-1400), not SPY (+5000)
        assert result["summary"]["total_positions_with_loss"] == 2
        symbols = [p["symbol"] for p in result["loss_positions"]]
        assert "INDA" in symbols
        assert "EEM" in symbols
        assert "SPY" not in symbols

    @pytest.mark.asyncio
    async def test_excludes_gain_positions(self, tool_registry):
        """Positions with unrealized gains should NOT be included"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_TLH, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        symbols = [p["symbol"] for p in result["loss_positions"]]
        assert "SPY" not in symbols

    @pytest.mark.asyncio
    async def test_tax_savings_calculation(self, tool_registry):
        """Tax savings should be unrealized_loss * tax_rate using Decimal"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_TLH, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30", tax_rate="0.20"
            )
            result = json.loads(result_json)

        from decimal import Decimal

        positions_by_symbol = {p["symbol"]: p for p in result["loss_positions"]}

        # INDA: abs(-1500) * 0.20 = 300
        assert Decimal(positions_by_symbol["INDA"]["potential_tax_savings"]) == Decimal("300.00")
        # EEM: abs(-1400) * 0.20 = 280
        assert Decimal(positions_by_symbol["EEM"]["potential_tax_savings"]) == Decimal("280.00")

        # Total: abs(-2900) * 0.20 = 580
        assert Decimal(result["summary"]["total_potential_tax_savings"]) == Decimal("580.00")
        assert result["summary"]["tax_rate"] == "0.20"

    @pytest.mark.asyncio
    async def test_zero_tax_rate(self, tool_registry):
        """Zero tax rate (e.g. Malaysia) should produce zero tax savings"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_TLH, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30", tax_rate="0"
            )
            result = json.loads(result_json)

        from decimal import Decimal

        assert Decimal(result["summary"]["total_potential_tax_savings"]) == Decimal("0")
        assert "No capital gains tax" in result["summary"]["tax_regime"]

    @pytest.mark.asyncio
    async def test_wash_sale_risk_detected(self, tool_registry):
        """Positions with recent buy (within 30 days of analysis end) should flag wash sale risk"""
        # Use a buy date 10 days before the analysis end_date (2025-06-30)
        # 2025-06-20 is within 30 days of 2025-06-30
        xml_data = SAMPLE_XML_WASH_SALE.replace("{recent_buy_date}", "20250620")

        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (xml_data, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        inda_position = result["loss_positions"][0]
        assert inda_position["symbol"] == "INDA"
        assert inda_position["wash_sale_risk"] is True
        assert inda_position["wash_sale_detail"] is not None
        assert "wash sale" in inda_position["wash_sale_detail"].lower()

    @pytest.mark.asyncio
    async def test_no_wash_sale_when_no_recent_trades(self, tool_registry):
        """No wash sale risk when there are no recent buys within 30 days"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_TLH, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        # Trades in SAMPLE_XML_TLH are from 2025-03 and 2025-01 - not within 30 days of today
        for position in result["loss_positions"]:
            assert position["wash_sale_risk"] is False

    @pytest.mark.asyncio
    async def test_historical_wash_sale_warnings(self, tool_registry):
        """Historical sell-at-loss + rebuy within 30 days should generate warning"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (
                SAMPLE_XML_HISTORICAL_WASH,
                date(2025, 1, 1),
                date(2025, 6, 30),
            )

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        # INDA was sold at loss on 2025-03-01 and rebought on 2025-03-15 (14 days)
        assert len(result["wash_sale_warnings"]) >= 1
        warning = result["wash_sale_warnings"][0]
        assert warning["symbol"] == "INDA"
        assert warning["sell_date"] == "2025-03-01"
        assert warning["buy_date"] == "2025-03-15"
        assert int(warning["days_between"]) == 14

    @pytest.mark.asyncio
    async def test_alternative_etf_suggestions(self, tool_registry):
        """Known ETFs should have Ireland-domiciled alternatives suggested"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_TLH, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        positions_by_symbol = {p["symbol"]: p for p in result["loss_positions"]}

        # INDA -> NDIA.L
        assert positions_by_symbol["INDA"]["suggested_alternative"] == "NDIA.L"
        # EEM -> IEEM.L
        assert positions_by_symbol["EEM"]["suggested_alternative"] == "IEEM.L"

    @pytest.mark.asyncio
    async def test_no_alternative_for_unknown_symbol(self, tool_registry):
        """Unknown symbols should have None as suggested_alternative"""
        # SAMPLE_XML_TLH doesn't have unknown symbols in loss positions
        # but SPY (gain) won't appear. Let's verify in a custom fixture
        xml_data = SAMPLE_XML_TLH.replace('symbol="INDA"', 'symbol="OBSCURE_ETF"').replace(
            'symbol="EEM"', 'symbol="ANOTHER_OBSCURE"'
        )
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (xml_data, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        for position in result["loss_positions"]:
            assert position["suggested_alternative"] is None

    @pytest.mark.asyncio
    async def test_empty_loss_positions(self, tool_registry):
        """Portfolio with only gains should return empty loss_positions"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_NO_LOSSES, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        assert result["loss_positions"] == []
        assert result["summary"]["total_positions_with_loss"] == 0
        assert result["summary"]["total_unrealized_loss"] == "0"

    @pytest.mark.asyncio
    async def test_invalid_tax_rate(self, tool_registry):
        """Invalid tax rate should raise ValidationError"""
        with pytest.raises(ValidationError, match="Invalid tax_rate"):
            await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", tax_rate="not_a_number"
            )

    @pytest.mark.asyncio
    async def test_tax_rate_out_of_range(self, tool_registry):
        """Tax rate > 1 should raise ValidationError"""
        with pytest.raises(ValidationError, match="finite number between 0 and 1"):
            await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", tax_rate="1.5"
            )

    @pytest.mark.asyncio
    async def test_result_includes_disclaimer(self, tool_registry):
        """Result should include a tax disclaimer"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_TLH, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        assert "disclaimer" in result
        assert "informational" in result["disclaimer"].lower()

    @pytest.mark.asyncio
    async def test_loss_positions_sorted_by_loss(self, tool_registry):
        """Loss positions should be sorted by unrealized loss (largest loss first)"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_TLH, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        from decimal import Decimal

        losses = [Decimal(p["unrealized_loss"]) for p in result["loss_positions"]]
        assert losses == sorted(losses)  # Ascending = most negative first

    @pytest.mark.asyncio
    async def test_holding_period_classification(self, tool_registry):
        """Positions should be classified as short_term, long_term, or unknown"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_TLH, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        for position in result["loss_positions"]:
            assert position["holding_period_type"] in ("short_term", "long_term", "unknown")
            assert position["holding_period_days"] is None or isinstance(
                position["holding_period_days"], int
            )

    @pytest.mark.asyncio
    async def test_decimal_precision(self, tool_registry):
        """All financial values should use Decimal precision (no float artifacts)"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_TLH, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        from decimal import Decimal, InvalidOperation

        for position in result["loss_positions"]:
            # All these fields should be valid Decimal strings
            for field in [
                "cost_basis",
                "current_value",
                "unrealized_loss",
                "potential_tax_savings",
            ]:
                try:
                    Decimal(position[field])
                except InvalidOperation:
                    pytest.fail(f"{field}='{position[field]}' is not a valid Decimal string")

    @pytest.mark.asyncio
    async def test_nan_tax_rate_rejected(self, tool_registry):
        """NaN, Infinity, -Infinity should be rejected as tax_rate"""
        for bad_rate in ["NaN", "Infinity", "-Infinity"]:
            with pytest.raises(ValidationError, match="finite number"):
                await tool_registry["calculate_tax_loss_harvesting"](
                    start_date="2025-01-01", tax_rate=bad_rate
                )

    @pytest.mark.asyncio
    async def test_unknown_holding_period_when_no_buy_trades(self, tool_registry):
        """Positions without buy trades in period should have 'unknown' holding period"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_NO_LOSSES, date(2025, 1, 1), date(2025, 6, 30))

            # Use custom XML with a loss position but no trades
            xml_with_loss_no_trades = SAMPLE_XML_NO_LOSSES.replace(
                'fifoPnlUnrealized="5000"', 'fifoPnlUnrealized="-1000"'
            ).replace('costBasisMoney="20000"', 'costBasisMoney="26000"')
            mock_fetch.return_value = (
                xml_with_loss_no_trades,
                date(2025, 1, 1),
                date(2025, 6, 30),
            )

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        assert len(result["loss_positions"]) == 1
        assert result["loss_positions"][0]["holding_period_days"] is None
        assert result["loss_positions"][0]["holding_period_type"] == "unknown"

    @pytest.mark.asyncio
    async def test_analysis_uses_end_date_not_today(self, tool_registry):
        """Wash sale window and holding period should use to_date, not date.today()"""
        # Use SAMPLE_XML_WASH_SALE with a buy date within 30 days of to_date (2025-06-30)
        # but far from today, proving we use to_date not today
        xml_data = SAMPLE_XML_WASH_SALE.replace("{recent_buy_date}", "20250620")

        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (xml_data, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        # The buy on 2025-06-20 is within 30 days of to_date 2025-06-30
        # If using date.today(), this wouldn't be flagged since it's far in the past
        assert result["loss_positions"][0]["wash_sale_risk"] is True

    @pytest.mark.asyncio
    async def test_backward_wash_sale_detection(self, tool_registry):
        """Buying within 30 days BEFORE a loss sale should also trigger wash sale warning"""
        # SAMPLE_XML_HISTORICAL_WASH has:
        # T002: BUY on 2025-03-15, T001: SELL at loss on 2025-03-01
        # Forward: sell(03-01) -> buy(03-15) = 14 days (caught before)
        # Backward: buy(03-15) was before sell... wait, the order is sell first then buy
        # Let's create a scenario: buy on 02-15, sell at loss on 03-01 = 14 days
        xml_backward = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250630">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="5000" endingCash="5000" endingSettledCash="5000"
          deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
          commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="INDA" description="ISHARES MSCI INDIA ETF"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US46429B5984" position="100" markPrice="45.00"
          positionValue="4500" costBasisMoney="6000" fifoPnlUnrealized="-1500"
          reportDate="20250630" multiplier="1" />
      </OpenPositions>
      <Trades>
        <Trade tradeID="T001" accountId="U1234567" symbol="INDA"
          description="ISHARES MSCI INDIA ETF" assetCategory="STK"
          currency="USD" fxRateToBase="1"
          buySell="BUY" quantity="50" tradePrice="50.00"
          tradeMoney="-2500" ibCommission="-1.00" ibCommissionCurrency="USD"
          tradeDate="20250215" settleDate="20250217"
          fifoPnlRealized="0" mtmPnl="0" multiplier="1"
          orderID="O001" execID="E001" />
        <Trade tradeID="T002" accountId="U1234567" symbol="INDA"
          description="ISHARES MSCI INDIA ETF" assetCategory="STK"
          currency="USD" fxRateToBase="1"
          buySell="SELL" quantity="-50" tradePrice="40.00"
          tradeMoney="2000" ibCommission="-1.00" ibCommissionCurrency="USD"
          tradeDate="20250301" settleDate="20250303"
          fifoPnlRealized="-500" mtmPnl="0" multiplier="1"
          orderID="O002" execID="E002" />
      </Trades>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (xml_backward, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        # Should detect backward wash sale: bought 02-15, sold at loss 03-01 (14 days)
        assert len(result["wash_sale_warnings"]) >= 1
        backward_warning = [
            w for w in result["wash_sale_warnings"] if w["buy_date"] == "2025-02-15"
        ]
        assert len(backward_warning) == 1
        assert backward_warning[0]["sell_date"] == "2025-03-01"
        assert int(backward_warning[0]["days_between"]) == 14

    @pytest.mark.asyncio
    async def test_result_structure(self, tool_registry):
        """Result JSON should have the expected top-level structure"""
        with patch("ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data") as mock_fetch:
            mock_fetch.return_value = (SAMPLE_XML_TLH, date(2025, 1, 1), date(2025, 6, 30))

            result_json = await tool_registry["calculate_tax_loss_harvesting"](
                start_date="2025-01-01", end_date="2025-06-30"
            )
            result = json.loads(result_json)

        assert "analysis_period" in result
        assert "account_id" in result
        assert "loss_positions" in result
        assert "wash_sale_warnings" in result
        assert "summary" in result
        assert "disclaimer" in result

        # Summary fields
        summary = result["summary"]
        assert "total_positions_with_loss" in summary
        assert "total_unrealized_loss" in summary
        assert "total_potential_tax_savings" in summary
        assert "tax_rate" in summary
        assert "tax_regime" in summary


class TestGetPortfolioSummaryDeprecation:
    """
    Tests for Issue #17: DeprecationWarning on get_portfolio_summary

    Acceptance Criteria:
    - DeprecationWarning is emitted when get_portfolio_summary is called
    - ctx.info() is called with the deprecation message
    - The function still returns a valid JSON summary despite the deprecation
    """

    @pytest.fixture
    def tool_registry(self):
        """Register tools with a CaptureMCP and return tool functions"""
        from ib_sec_mcp.mcp.tools.ib_portfolio import register_ib_portfolio_tools

        tools = {}

        class CaptureMCP:
            def tool(self, fn):
                tools[fn.__name__] = fn
                return fn

        register_ib_portfolio_tools(CaptureMCP())
        return tools

    @pytest.fixture
    def xml_temp_file(self, tmp_path):
        """Write SAMPLE_XML_MULTI_CURRENCY to a temp file with naming convention"""
        xml_file = tmp_path / "U1234567_2025-01-01_2025-01-31.xml"
        xml_file.write_text(SAMPLE_XML_MULTI_CURRENCY)
        return xml_file

    @pytest.mark.asyncio
    async def test_deprecation_warning_emitted(self, tool_registry, xml_temp_file):
        """
        Acceptance Criterion: Calling get_portfolio_summary must emit a DeprecationWarning.

        The warning message must reference the replacement function
        analyze_consolidated_portfolio.
        """
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await tool_registry["get_portfolio_summary"](file_path=str(xml_temp_file))

        deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1

        warning_message = str(deprecation_warnings[0].message)
        assert "get_portfolio_summary" in warning_message
        assert "analyze_consolidated_portfolio" in warning_message

    @pytest.mark.asyncio
    async def test_deprecation_notice_logged_to_context(self, tool_registry, xml_temp_file):
        """
        Acceptance Criterion: When a ctx is provided, ctx.info() is called with the
        deprecation notice before normal logging.
        """
        mock_ctx = AsyncMock()

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            await tool_registry["get_portfolio_summary"](file_path=str(xml_temp_file), ctx=mock_ctx)

        # ctx.info must have been called at least once
        assert mock_ctx.info.called

        # At least one call must mention the deprecation
        all_info_messages = [call.args[0] for call in mock_ctx.info.call_args_list]
        deprecation_logged = any(
            "deprecated" in msg.lower() or "get_portfolio_summary" in msg
            for msg in all_info_messages
        )
        assert deprecation_logged, (
            f"No deprecation notice found in ctx.info calls: {all_info_messages}"
        )

    @pytest.mark.asyncio
    async def test_still_returns_valid_summary(self, tool_registry, xml_temp_file):
        """
        Acceptance Criterion: Despite the deprecation warning, get_portfolio_summary
        must return a valid JSON summary with the expected structure.
        """
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result_json = await tool_registry["get_portfolio_summary"](file_path=str(xml_temp_file))

        result = json.loads(result_json)

        # Core summary fields must be present
        assert "num_accounts" in result
        assert "total_cash" in result
        assert "total_value" in result
        assert "date_range" in result

        # Date range must be populated from filename
        assert result["date_range"]["from"] == "2025-01-01"
        assert result["date_range"]["to"] == "2025-01-31"

        # Single account in sample XML
        assert result["num_accounts"] == 1
