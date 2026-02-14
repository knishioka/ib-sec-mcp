"""Tests for IB Portfolio MCP tools"""

import json
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
    yield
    # Clean after
    if data_dir.exists():
        for f in data_dir.glob("*.csv"):
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
        # Create cached file
        data_dir = Path("data/raw")
        data_dir.mkdir(parents=True, exist_ok=True)
        cached_file = data_dir / "U12345678_2025-01-01_2025-01-31.csv"
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

            # Verify file was cached
            data_dir = Path("data/raw")
            cached_files = list(data_dir.glob("*_2025-01-01_2025-01-31.csv"))
            assert len(cached_files) == 1
            assert cached_files[0].read_text() == sample_csv_data

    @pytest.mark.asyncio
    async def test_use_cache_false_always_fetches(self, mock_env, sample_csv_data, clean_cache):
        """Test that use_cache=False always fetches from API"""
        # Create cached file
        data_dir = Path("data/raw")
        data_dir.mkdir(parents=True, exist_ok=True)
        cached_file = data_dir / "U12345678_2025-01-01_2025-01-31.csv"
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
        # Create cached file with different account ID
        data_dir = Path("data/raw")
        data_dir.mkdir(parents=True, exist_ok=True)
        cached_file = data_dir / "UXXX_2025-01-01_2025-01-31.csv"
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
            assert "single account supported" in warning_call

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
        with patch(
            "ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data"
        ) as mock_fetch:
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
        with patch(
            "ib_sec_mcp.mcp.tools.ib_portfolio._get_or_fetch_data"
        ) as mock_fetch:
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
                assert "fx_rate_to_base" in holding, (
                    f"{holding['symbol']} missing fx_rate_to_base"
                )

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
