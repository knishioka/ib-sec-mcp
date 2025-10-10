"""Data validators and helper functions"""

import re
from datetime import date, datetime
from typing import Union


def validate_date(
    value: Union[str, date, datetime],
    fmt: str = "%Y-%m-%d",
) -> date:
    """
    Validate and parse date

    Args:
        value: Date string, date, or datetime object
        fmt: Expected date format for string parsing

    Returns:
        date object

    Raises:
        ValueError: If date is invalid
    """
    if isinstance(value, date):
        return value

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, str):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError as e:
            raise ValueError(f"Invalid date format: {value} (expected {fmt})") from e

    raise ValueError(f"Invalid date type: {type(value)}")


def validate_cusip(cusip: str) -> bool:
    """
    Validate CUSIP format (9 characters: 8 alphanumeric + 1 check digit)

    Args:
        cusip: CUSIP string

    Returns:
        True if valid, False otherwise
    """
    if not cusip or len(cusip) != 9:
        return False

    # First 8 characters: alphanumeric
    if not cusip[:8].isalnum():
        return False

    # Last character: digit
    if not cusip[8].isdigit():
        return False

    # Calculate check digit
    total = 0
    for i, char in enumerate(cusip[:8]):
        value = int(char) if char.isdigit() else ord(char.upper()) - ord("A") + 10

        if i % 2 == 1:  # Double odd positions
            value *= 2

        total += value // 10 + value % 10

    check_digit = (10 - (total % 10)) % 10

    return int(cusip[8]) == check_digit


def validate_isin(isin: str) -> bool:
    """
    Validate ISIN format (12 characters: 2 country code + 9 identifier + 1 check digit)

    Args:
        isin: ISIN string

    Returns:
        True if valid, False otherwise
    """
    if not isin or len(isin) != 12:
        return False

    # First 2 characters: country code (letters)
    if not isin[:2].isalpha():
        return False

    # Characters 3-11: alphanumeric
    if not isin[2:11].isalnum():
        return False

    # Last character: digit
    if not isin[11].isdigit():
        return False

    # Luhn algorithm for check digit
    digits = []
    for char in isin[:11]:
        if char.isdigit():
            digits.append(char)
        else:
            # A=10, B=11, ..., Z=35
            value = str(ord(char.upper()) - ord("A") + 10)
            digits.extend(value)

    # Double every second digit from right
    total = 0
    reversed_digits = "".join(digits)[::-1]
    for i, digit in enumerate(reversed_digits):
        digit_value: int = int(digit)
        if i % 2 == 1:
            digit_value *= 2
            if digit_value > 9:
                digit_value = digit_value // 10 + digit_value % 10
        total += digit_value

    check_digit = (10 - (total % 10)) % 10

    return int(isin[11]) == check_digit


def validate_account_id(account_id: str) -> bool:
    """
    Validate IB account ID format (typically U followed by 7-8 digits)

    Args:
        account_id: Account ID string

    Returns:
        True if valid, False otherwise
    """
    if not account_id:
        return False

    # Pattern: U followed by 7-8 digits
    pattern = r"^U\d{7,8}$"
    return bool(re.match(pattern, account_id))


def parse_decimal_safe(value: Union[str, int, float], default: float = 0.0) -> float:
    """
    Safely parse decimal value

    Args:
        value: Value to parse
        default: Default value if parsing fails

    Returns:
        Parsed float value or default
    """
    if value is None or value == "":
        return default

    try:
        if isinstance(value, str):
            # Remove commas and whitespace
            cleaned = value.replace(",", "").strip()
            return float(cleaned)
        return float(value)
    except (ValueError, TypeError):
        return default


def validate_symbol(symbol: str) -> bool:
    """
    Validate trading symbol format

    Args:
        symbol: Symbol string

    Returns:
        True if valid, False otherwise
    """
    if not symbol or not symbol.strip():
        return False

    # Basic validation: 1-10 alphanumeric characters, may include dots
    pattern = r"^[A-Z0-9.]{1,10}$"
    return bool(re.match(pattern, symbol.upper()))
