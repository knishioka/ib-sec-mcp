"""Tests for MCP validators"""

from datetime import date

import pytest

from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.mcp.validators import (
    validate_account_index,
    validate_date_range,
    validate_date_string,
    validate_indicators,
    validate_interval,
    validate_period,
    validate_symbol,
)


class TestDateValidation:
    """Test date validation functions"""

    def test_valid_date_string(self):
        result = validate_date_string("2025-01-15")
        assert result == date(2025, 1, 15)

    def test_invalid_date_format(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_date_string("15-01-2025")
        assert "Invalid date format" in str(exc_info.value)

    def test_valid_date_range(self):
        from_date = date(2025, 1, 1)
        to_date = date(2025, 12, 31)
        result_from, result_to = validate_date_range(from_date, to_date)
        assert result_from == from_date
        assert result_to == to_date

    def test_invalid_date_range(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_date_range(date(2025, 12, 31), date(2025, 1, 1))
        assert "cannot be after" in str(exc_info.value)


class TestSymbolValidation:
    """Test stock symbol validation"""

    def test_valid_symbol(self):
        assert validate_symbol("AAPL") == "AAPL"
        assert validate_symbol("voo") == "VOO"
        assert validate_symbol("BRK.B") == "BRK.B"

    def test_invalid_symbol(self):
        with pytest.raises(ValidationError):
            validate_symbol("")

        with pytest.raises(ValidationError):
            validate_symbol("VERYLONGSYMBOL")


class TestPeriodValidation:
    """Test period validation"""

    def test_valid_periods(self):
        assert validate_period("1mo") == "1mo"
        assert validate_period("1y") == "1y"
        assert validate_period("max") == "max"

    def test_invalid_period(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_period("invalid")
        assert "Invalid period" in str(exc_info.value)


class TestIntervalValidation:
    """Test interval validation"""

    def test_valid_intervals(self):
        assert validate_interval("1d") == "1d"
        assert validate_interval("1h") == "1h"
        assert validate_interval("1wk") == "1wk"

    def test_invalid_interval(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_interval("2d")
        assert "Invalid interval" in str(exc_info.value)


class TestIndicatorValidation:
    """Test indicator validation"""

    def test_valid_indicators(self):
        result = validate_indicators("sma_20,rsi,macd")
        assert result == ["sma_20", "rsi", "macd"]

    def test_custom_sma_ema(self):
        result = validate_indicators("sma_100,ema_50")
        assert result == ["sma_100", "ema_50"]

    def test_invalid_indicator(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_indicators("unknown_indicator")
        assert "Unknown indicator" in str(exc_info.value)

    def test_invalid_sma_period(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_indicators("sma_1000")
        assert "must be between 1 and 500" in str(exc_info.value)


class TestAccountIndexValidation:
    """Test account index validation"""

    def test_valid_index(self):
        assert validate_account_index(0) == 0
        assert validate_account_index(5) == 5

    def test_negative_index(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_account_index(-1)
        assert "must be non-negative" in str(exc_info.value)

    def test_index_too_large(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_account_index(20)
        assert "exceeds maximum" in str(exc_info.value)
