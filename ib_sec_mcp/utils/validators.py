"""Data validators and helper functions"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def validate_date(
    value: str | date | datetime,
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


def parse_decimal_safe(
    value: str | int | float | Decimal | None,
    default: Decimal = Decimal("0"),
) -> Decimal:
    """
    Safely parse a value into a ``Decimal`` without float precision loss.

    Financial values must be created from a string (``Decimal(str(value))``)
    rather than from a ``float``, otherwise binary floating-point artifacts are
    baked in at the parse boundary. For example ``Decimal(0.1)`` yields
    ``Decimal('0.1000000000000000055511151231257827021181583404541015625')``
    whereas ``Decimal("0.1")`` is exact. This helper guarantees the latter for
    every code path so callers never need to wrap the result in ``Decimal``.

    Args:
        value: Value to parse (string, int, float, Decimal, or None)
        default: Default ``Decimal`` returned when the input is empty or invalid

    Returns:
        Parsed ``Decimal`` value, or ``default`` on empty/invalid input
    """
    if value is None or value == "":
        return default

    # Already a Decimal: return as-is, avoiding a redundant str() round-trip.
    if isinstance(value, Decimal):
        return value

    try:
        if isinstance(value, str):
            # Remove thousands separators and surrounding whitespace
            cleaned = value.replace(",", "").strip()
            if not cleaned:
                return default
            return Decimal(cleaned)
        # int/float: route through str() so float binary artifacts are not
        # propagated into the resulting Decimal.
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def validate_xml_format(data: str) -> None:
    """
    Validate that ``data`` is XML.

    IB Flex Query API returns data in XML format only (CSV support has been
    removed), so this is a guard rather than a multi-format detector.

    Args:
        data: Raw data string

    Raises:
        ValueError: If ``data`` is not valid XML (does not start with ``<``)
    """
    # Find the first non-whitespace character without copying/splitting the
    # whole payload (XML statements can be large): O(1) for well-formed input.
    first_char = next((char for char in data if not char.isspace()), "")

    if first_char != "<":
        raise ValueError(
            "Invalid data format. Only XML format is supported. "
            "CSV support has been removed. "
            "IB Flex Query API returns XML data."
        )


def validate_symbol(symbol: str) -> bool:
    """
    Validate trading symbol format

    Supports:
    - US stocks: AAPL, TSLA, VOO
    - Cryptocurrencies: BTC-USD, ETH-USD
    - Forex pairs: USDJPY=X, EURUSD=X
    - ETFs and other securities

    Args:
        symbol: Symbol string

    Returns:
        True if valid, False otherwise
    """
    if not symbol or not symbol.strip():
        return False

    # Extended validation: 1-12 characters, allow dots, hyphens, equals
    # Supports forex (=X suffix) and crypto (-USD suffix)
    pattern = r"^[A-Z0-9.\-=]{1,12}$"
    return bool(re.match(pattern, symbol.upper()))
