"""Tests for IB Portfolio MCP tools"""

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
