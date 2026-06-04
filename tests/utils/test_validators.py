"""Tests for ib_sec_mcp.utils.validators.

Focus areas:
- parse_decimal_safe must return exact Decimal values with no float artifacts
  at the parse boundary (Issue #119).
- validate_xml_format guards that only XML is accepted.
"""

from datetime import date
from decimal import Decimal

import pytest

from ib_sec_mcp.utils.validators import (
    parse_decimal_safe,
    validate_account_id,
    validate_cusip,
    validate_date,
    validate_isin,
    validate_symbol,
    validate_xml_format,
)


class TestParseDecimalSafe:
    """parse_decimal_safe returns exact Decimal without float precision loss."""

    def test_returns_decimal_type(self) -> None:
        assert isinstance(parse_decimal_safe("100.50"), Decimal)

    @pytest.mark.parametrize(
        "raw",
        ["0.1", "0.2", "0.3", "1.005", "150.50", "12.34", "0.07", "19.99"],
    )
    def test_no_float_artifacts(self, raw: str) -> None:
        """Values that are inexact as binary floats must stay exact as Decimal."""
        # Exact: equals Decimal(str) of the literal.
        assert parse_decimal_safe(raw) == Decimal(raw)
        # And demonstrably free of the float artifact that the old impl produced.
        assert str(parse_decimal_safe(raw)) == raw

    def test_classic_float_error_case(self) -> None:
        """0.1 + 0.2 == 0.3 holds with Decimal parsing (would fail with float)."""
        result = parse_decimal_safe("0.1") + parse_decimal_safe("0.2")
        assert result == parse_decimal_safe("0.3")
        assert result == Decimal("0.3")

    def test_strips_commas_and_whitespace(self) -> None:
        assert parse_decimal_safe("  1,234,567.89  ") == Decimal("1234567.89")

    def test_negative_values(self) -> None:
        assert parse_decimal_safe("-25.50") == Decimal("-25.50")

    def test_int_input(self) -> None:
        result = parse_decimal_safe(100)
        assert result == Decimal("100")
        assert isinstance(result, Decimal)

    def test_float_input_routes_through_str(self) -> None:
        """A float input must not bake its binary artifact into the Decimal."""
        assert parse_decimal_safe(0.1) == Decimal("0.1")

    def test_decimal_input_returned_as_is(self) -> None:
        """An existing Decimal is returned unchanged (no str() round-trip)."""
        value = Decimal("123.456")
        result = parse_decimal_safe(value)
        assert result == value
        assert isinstance(result, Decimal)

    def test_decimal_input_preserves_high_precision(self) -> None:
        value = Decimal("1.000000000000000000001")
        assert parse_decimal_safe(value) == value

    def test_none_returns_default(self) -> None:
        assert parse_decimal_safe(None) == Decimal("0")

    def test_empty_string_returns_default(self) -> None:
        assert parse_decimal_safe("") == Decimal("0")

    def test_whitespace_only_returns_default(self) -> None:
        assert parse_decimal_safe("   ") == Decimal("0")

    def test_invalid_string_returns_default(self) -> None:
        assert parse_decimal_safe("not-a-number") == Decimal("0")

    def test_custom_default(self) -> None:
        assert parse_decimal_safe("", default=Decimal("1")) == Decimal("1")
        assert parse_decimal_safe("bad", default=Decimal("-1")) == Decimal("-1")

    def test_default_is_decimal_type(self) -> None:
        result = parse_decimal_safe(None, default=Decimal("5"))
        assert isinstance(result, Decimal)


class TestValidateXmlFormat:
    """validate_xml_format raises on non-XML input."""

    def test_valid_xml(self) -> None:
        # Should not raise.
        validate_xml_format("<FlexQueryResponse/>")

    def test_xml_with_declaration(self) -> None:
        validate_xml_format('<?xml version="1.0"?><root/>')

    def test_xml_with_leading_whitespace(self) -> None:
        validate_xml_format("  \n  <root/>")

    @pytest.mark.parametrize(
        "data",
        [
            "AccountId,Symbol,Quantity\nU123,AAPL,100",  # CSV
            "",  # empty
            "   \n  ",  # whitespace only
            '{"key": "value"}',  # JSON
        ],
    )
    def test_non_xml_raises(self, data: str) -> None:
        with pytest.raises(ValueError, match="Only XML format is supported"):
            validate_xml_format(data)

    def test_returns_none(self) -> None:
        assert validate_xml_format("<root/>") is None


class TestIdentifierValidators:
    """Regression coverage for the identifier/symbol validators."""

    def test_valid_cusip(self) -> None:
        # 037833100 = Apple Inc. (valid check digit)
        assert validate_cusip("037833100") is True

    def test_invalid_cusip_check_digit(self) -> None:
        assert validate_cusip("037833101") is False

    def test_cusip_wrong_length(self) -> None:
        assert validate_cusip("0378331") is False

    def test_isin_wrong_length(self) -> None:
        assert validate_isin("US037833100") is False

    def test_isin_non_alpha_country_code(self) -> None:
        assert validate_isin("120378331005") is False

    def test_isin_non_digit_check(self) -> None:
        assert validate_isin("US037833100X") is False

    def test_valid_account_id(self) -> None:
        assert validate_account_id("U1234567") is True
        assert validate_account_id("U12345678") is True

    def test_invalid_account_id(self) -> None:
        assert validate_account_id("X1234567") is False
        assert validate_account_id("U123") is False
        assert validate_account_id("") is False

    def test_valid_symbol(self) -> None:
        assert validate_symbol("AAPL") is True
        assert validate_symbol("BTC-USD") is True
        assert validate_symbol("USDJPY=X") is True

    def test_invalid_symbol(self) -> None:
        assert validate_symbol("") is False
        assert validate_symbol("   ") is False
        assert validate_symbol("TOOLONGSYMBOL123") is False


class TestValidateDate:
    """Coverage for validate_date."""

    def test_parse_string(self) -> None:
        assert validate_date("2025-01-15") == date(2025, 1, 15)

    def test_passthrough_date(self) -> None:
        d = date(2025, 6, 1)
        assert validate_date(d) == d

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date("15-01-2025")
