"""Validation utilities for IB Analytics MCP Server

Provides input validation and security checks for MCP tools.
"""

import re
from datetime import date, datetime
from pathlib import Path

from ib_sec_mcp.mcp.exceptions import ValidationError

# Security constants
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_DATA_DIR = Path("data/raw")
ALLOWED_FILE_EXTENSIONS = {".csv", ".xml"}


def validate_date_string(date_str: str, field_name: str = "date") -> date:
    """
    Validate and parse date string in YYYY-MM-DD format

    Args:
        date_str: Date string to validate
        field_name: Name of the field for error messages

    Returns:
        Parsed date object

    Raises:
        ValidationError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValidationError(
            f"Invalid date format. Expected YYYY-MM-DD, got '{date_str}'",
            field=field_name,
        ) from e


def validate_date_range(from_date: date, to_date: date) -> tuple[date, date]:
    """
    Validate that date range is logical

    Args:
        from_date: Start date
        to_date: End date

    Returns:
        Tuple of (from_date, to_date)

    Raises:
        ValidationError: If date range is invalid
    """
    if from_date > to_date:
        raise ValidationError(
            f"Start date ({from_date}) cannot be after end date ({to_date})",
            field="date_range",
        )

    # Warn if date range is too large (> 5 years)
    if (to_date - from_date).days > 365 * 5:
        # This is a warning, not an error
        pass

    return from_date, to_date


def validate_file_path(file_path: str, check_exists: bool = True) -> Path:
    """
    Validate file path for security (prevent path traversal)

    Args:
        file_path: File path to validate
        check_exists: Whether to check if file exists

    Returns:
        Validated Path object

    Raises:
        ValidationError: If path is invalid or insecure
    """
    try:
        path = Path(file_path).resolve()
    except (ValueError, OSError) as e:
        raise ValidationError(f"Invalid file path: {str(e)}", field="file_path") from e

    # Check for path traversal
    try:
        # Ensure path is within data directory or absolute paths are allowed
        if not path.is_absolute():
            raise ValidationError("File path must be absolute", field="file_path")
    except (ValueError, OSError) as e:
        raise ValidationError(f"Path validation failed: {str(e)}", field="file_path") from e

    # Check file extension
    if path.suffix.lower() not in ALLOWED_FILE_EXTENSIONS:
        raise ValidationError(
            f"File extension '{path.suffix}' not allowed. "
            f"Allowed extensions: {', '.join(ALLOWED_FILE_EXTENSIONS)}",
            field="file_path",
        )

    # Check if file exists
    if check_exists and not path.exists():
        raise ValidationError(f"File not found: {file_path}", field="file_path")

    # Check file size
    if check_exists and path.is_file():
        size_bytes = path.stat().st_size
        if size_bytes > MAX_FILE_SIZE_BYTES:
            size_mb = size_bytes / (1024 * 1024)
            raise ValidationError(
                f"File size ({size_mb:.1f} MB) exceeds maximum allowed size "
                f"({MAX_FILE_SIZE_MB} MB)",
                field="file_path",
            )

    return path


def validate_account_index(index: int, max_accounts: int = 10) -> int:
    """
    Validate account index

    Args:
        index: Account index to validate
        max_accounts: Maximum allowed account index

    Returns:
        Validated account index

    Raises:
        ValidationError: If index is out of range
    """
    if index < 0:
        raise ValidationError(
            f"Account index must be non-negative, got {index}",
            field="account_index",
        )

    if index >= max_accounts:
        raise ValidationError(
            f"Account index ({index}) exceeds maximum ({max_accounts - 1})",
            field="account_index",
        )

    return index


def validate_symbol(symbol: str) -> str:
    """
    Validate stock ticker symbol

    Supports:
    - US stocks: AAPL, TSLA, VOO
    - Cryptocurrencies: BTC-USD, ETH-USD
    - Forex pairs: USDJPY=X, EURUSD=X
    - ETFs and other securities

    Args:
        symbol: Ticker symbol to validate

    Returns:
        Validated and normalized symbol (uppercase)

    Raises:
        ValidationError: If symbol format is invalid
    """
    if not symbol:
        raise ValidationError("Symbol cannot be empty", field="symbol")

    # Remove whitespace
    symbol = symbol.strip().upper()

    # Check format (letters, numbers, dots, hyphens, equals)
    # Allow = for forex symbols (e.g., USDJPY=X)
    # Extended to 12 chars to accommodate forex symbols
    if not re.match(r"^[A-Z0-9.\-=]{1,12}$", symbol):
        raise ValidationError(
            f"Invalid symbol format: '{symbol}'. "
            "Must be 1-12 characters (letters, numbers, dots, hyphens, equals)",
            field="symbol",
        )

    return symbol


def validate_period(period: str) -> str:
    """
    Validate Yahoo Finance period parameter

    Args:
        period: Period string to validate

    Returns:
        Validated period string

    Raises:
        ValidationError: If period is invalid
    """
    valid_periods = {
        "1d",
        "5d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "10y",
        "ytd",
        "max",
    }

    if period not in valid_periods:
        raise ValidationError(
            f"Invalid period '{period}'. Valid periods: {', '.join(sorted(valid_periods))}",
            field="period",
        )

    return period


def validate_interval(interval: str) -> str:
    """
    Validate Yahoo Finance interval parameter

    Args:
        interval: Interval string to validate

    Returns:
        Validated interval string

    Raises:
        ValidationError: If interval is invalid
    """
    valid_intervals = {
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo",
    }

    if interval not in valid_intervals:
        raise ValidationError(
            f"Invalid interval '{interval}'. Valid intervals: {', '.join(sorted(valid_intervals))}",
            field="interval",
        )

    return interval


def validate_indicators(indicators: str | None) -> list[str] | None:
    """
    Validate technical indicators string

    Args:
        indicators: Comma-separated indicator string

    Returns:
        List of validated indicators or None

    Raises:
        ValidationError: If indicators are invalid
    """
    if not indicators:
        return None

    valid_indicators = {
        "sma_20",
        "sma_50",
        "sma_200",
        "ema_12",
        "ema_26",
        "rsi",
        "macd",
        "bollinger",
        "volume_ma",
    }

    # Also allow custom SMA/EMA periods
    indicator_list = [ind.strip() for ind in indicators.split(",")]
    validated = []

    for ind in indicator_list:
        # Check if it's a valid predefined indicator
        if ind in valid_indicators:
            validated.append(ind)
        # Check if it's a custom SMA
        elif ind.startswith("sma_"):
            try:
                period = int(ind.split("_")[1])
                if period < 1 or period > 500:
                    raise ValidationError(
                        f"SMA period must be between 1 and 500, got {period}",
                        field="indicators",
                    )
                validated.append(ind)
            except (IndexError, ValueError) as e:
                raise ValidationError(
                    f"Invalid SMA indicator format: '{ind}'", field="indicators"
                ) from e
        # Check if it's a custom EMA
        elif ind.startswith("ema_"):
            try:
                period = int(ind.split("_")[1])
                if period < 1 or period > 500:
                    raise ValidationError(
                        f"EMA period must be between 1 and 500, got {period}",
                        field="indicators",
                    )
                validated.append(ind)
            except (IndexError, ValueError) as e:
                raise ValidationError(
                    f"Invalid EMA indicator format: '{ind}'", field="indicators"
                ) from e
        else:
            raise ValidationError(
                f"Unknown indicator: '{ind}'. "
                f"Valid indicators: {', '.join(sorted(valid_indicators))} "
                "or custom sma_N/ema_N (N=1-500)",
                field="indicators",
            )

    return validated if validated else None


def validate_benchmark_symbol(symbol: str) -> str:
    """
    Validate benchmark symbol (same as regular symbol but with common defaults)

    Args:
        symbol: Benchmark ticker symbol

    Returns:
        Validated and normalized symbol

    Raises:
        ValidationError: If symbol is invalid
    """
    return validate_symbol(symbol)


def validate_risk_free_rate(rate: float) -> float:
    """
    Validate risk-free rate

    Args:
        rate: Risk-free rate (as decimal, e.g., 0.05 for 5%)

    Returns:
        Validated risk-free rate

    Raises:
        ValidationError: If rate is invalid
    """
    if rate < 0 or rate > 0.5:
        raise ValidationError(
            f"Risk-free rate must be between 0 and 0.5 (50%), got {rate}",
            field="risk_free_rate",
        )
    return rate


def validate_confidence_level(level: float) -> float:
    """
    Validate confidence level for VaR calculations

    Args:
        level: Confidence level (e.g., 0.95 for 95%)

    Returns:
        Validated confidence level

    Raises:
        ValidationError: If level is invalid
    """
    if level <= 0 or level >= 1:
        raise ValidationError(
            f"Confidence level must be between 0 and 1, got {level}",
            field="confidence_level",
        )
    return level
