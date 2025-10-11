"""IB Portfolio Analysis Tools

Interactive Brokers portfolio analysis and data fetching tools.
"""

import asyncio
import json
from datetime import date, datetime
from pathlib import Path

from fastmcp import Context, FastMCP

from ib_sec_mcp.analyzers.bond import BondAnalyzer
from ib_sec_mcp.analyzers.cost import CostAnalyzer
from ib_sec_mcp.analyzers.performance import PerformanceAnalyzer
from ib_sec_mcp.analyzers.risk import RiskAnalyzer
from ib_sec_mcp.analyzers.tax import TaxAnalyzer
from ib_sec_mcp.api.client import FlexQueryAPIError, FlexQueryClient
from ib_sec_mcp.core.parsers import CSVParser, XMLParser, detect_format
from ib_sec_mcp.mcp.exceptions import (
    APIError,
    ConfigurationError,
    FileOperationError,
    IBTimeoutError,
    ValidationError,
)
from ib_sec_mcp.mcp.validators import (
    validate_account_index,
    validate_date_range,
    validate_date_string,
)
from ib_sec_mcp.utils.config import Config

# Timeout constants (in seconds)
API_FETCH_TIMEOUT = 60
FILE_OPERATION_TIMEOUT = 10


def _extract_dates_from_filename(csv_path: str) -> tuple[date, date]:
    """
    Extract from_date and to_date from CSV filename

    Expected format: {account_id}_{from_date}_{to_date}.csv
    Example: UXXXXXXXX_2025-01-01_2025-10-07.csv
    """
    filename = Path(csv_path).stem  # Remove .csv extension
    parts = filename.split("_")

    if len(parts) >= 3:
        # Try to parse dates from filename
        try:
            from_date = datetime.strptime(parts[-2], "%Y-%m-%d").date()
            to_date = datetime.strptime(parts[-1], "%Y-%m-%d").date()
            return from_date, to_date
        except ValueError:
            pass

    # Fallback: use current year
    return date(date.today().year, 1, 1), date.today()


async def _get_or_fetch_data(
    start_date: str,
    end_date: str | None = None,
    account_index: int = 0,
    use_cache: bool = True,
    ctx: Context | None = None,
) -> tuple[str, date, date]:
    """
    Get data from cache or fetch from IB API

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (defaults to today)
        account_index: Account index (0 for first account, 1 for second, etc.)
        use_cache: Use cached data if available (default: True)
        ctx: MCP context for logging

    Returns:
        Tuple of (data_string, from_date, to_date)

    Raises:
        ValidationError: If input validation fails
        ConfigurationError: If credentials are missing
        APIError: If IB API call fails
        FileOperationError: If file operations fail
        IBTimeoutError: If operation times out
    """
    # Validate inputs
    from_date = validate_date_string(start_date, "start_date")
    to_date = validate_date_string(end_date, "end_date") if end_date else date.today()
    from_date, to_date = validate_date_range(from_date, to_date)
    validate_account_index(account_index)

    # Check cache first
    if use_cache:
        # Try to find cached file
        try:
            data_dir = Path("data/raw")
            # We don't know exact account_id yet, so try pattern matching
            pattern = f"*_{from_date}_{to_date}.csv"
            cached_files = list(data_dir.glob(pattern))

            if cached_files:
                cached_file = cached_files[0]  # Use first match
                if ctx:
                    await ctx.info(f"Using cached data from {cached_file}")

                with open(cached_file) as f:
                    data = f.read()
                return data, from_date, to_date
        except Exception:  # nosec B110
            # If cache lookup fails, proceed to fetch
            pass

    # No cache or cache disabled - fetch from API
    if ctx:
        await ctx.info(f"Fetching fresh data from IB API for {from_date} to {to_date}")

    # Load configuration
    try:
        config = Config.load()
        credentials = config.get_credentials()
        # Note: account_index currently not supported (single account config)
        # Multi-account support requires config changes
        if account_index != 0 and ctx:
            await ctx.warning(
                f"account_index {account_index} specified but only single account supported. Using default account."
            )
    except Exception as e:
        if ctx:
            await ctx.error(f"Configuration error: {str(e)}")
        raise ConfigurationError(
            "Failed to load credentials. Ensure QUERY_ID and TOKEN are set in .env file"
        ) from e

    # Create client
    client = FlexQueryClient(
        query_id=credentials.query_id,
        token=credentials.token,
    )

    # Fetch statement with timeout
    try:
        if ctx:
            await ctx.debug(f"Calling IB Flex Query API (timeout={API_FETCH_TIMEOUT}s)")

        async def fetch_with_timeout():
            return await asyncio.to_thread(client.fetch_statement, from_date, to_date)

        statement = await asyncio.wait_for(fetch_with_timeout(), timeout=API_FETCH_TIMEOUT)

    except asyncio.TimeoutError as e:  # noqa: UP041
        if ctx:
            await ctx.error(
                f"API call timed out after {API_FETCH_TIMEOUT}s",
                extra={"timeout": API_FETCH_TIMEOUT, "operation": "fetch_statement"},
            )
        raise IBTimeoutError(
            f"IB API call timed out after {API_FETCH_TIMEOUT} seconds",
            operation="fetch_statement",
        ) from e

    except FlexQueryAPIError as e:
        if ctx:
            await ctx.error(f"IB API error: {str(e)}", extra={"error_type": "FlexQueryAPIError"})
        raise APIError(str(e)) from e

    # Save to cache
    try:
        data_dir = Path("data/raw")
        data_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{statement.account_id}_{from_date}_{to_date}.csv"
        filepath = data_dir / filename

        async def save_file():
            await asyncio.to_thread(filepath.write_text, statement.raw_data, encoding="utf-8")

        await asyncio.wait_for(save_file(), timeout=FILE_OPERATION_TIMEOUT)

        if ctx:
            await ctx.info(
                f"Saved data to {filepath}",
                extra={
                    "file_path": str(filepath),
                    "file_size_bytes": len(statement.raw_data),
                },
            )

    except asyncio.TimeoutError as e:  # noqa: UP041
        if ctx:
            await ctx.error(f"File write timed out after {FILE_OPERATION_TIMEOUT}s")
        raise IBTimeoutError(
            f"File write timed out after {FILE_OPERATION_TIMEOUT} seconds",
            operation="save_file",
        ) from e

    except Exception as e:
        if ctx:
            await ctx.error(f"File operation failed: {str(e)}")
        raise FileOperationError(f"Failed to save data to {filepath}: {str(e)}") from e

    return statement.raw_data, from_date, to_date


def register_ib_portfolio_tools(mcp: FastMCP) -> None:
    """Register IB portfolio analysis tools"""

    @mcp.tool
    async def fetch_ib_data(
        start_date: str,
        end_date: str | None = None,
        account_index: int = 0,
        ctx: Context | None = None,
    ) -> dict:
        """
        Fetch Interactive Brokers data from Flex Query API

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            account_index: Account index (0 for first account, 1 for second, etc.)
            ctx: MCP context for logging

        Returns:
            Dict with account_id, date_range, and file_path

        Raises:
            ValidationError: If input validation fails
            ConfigurationError: If credentials are missing or invalid
            APIError: If IB API call fails
            FileOperationError: If file operations fail
            IBTimeoutError: If operation times out
        """
        try:
            # Validate inputs
            from_date = validate_date_string(start_date, "start_date")
            to_date = validate_date_string(end_date, "end_date") if end_date else date.today()
            from_date, to_date = validate_date_range(from_date, to_date)
            validate_account_index(account_index)

            if ctx:
                await ctx.info(
                    f"Fetching IB data from {from_date} to {to_date}",
                    extra={
                        "start_date": str(from_date),
                        "end_date": str(to_date),
                        "account_index": account_index,
                    },
                )

            # Load and validate configuration
            try:
                config = Config.load()
                credentials = config.get_credentials()
            except Exception as e:
                if ctx:
                    await ctx.error(f"Configuration error: {str(e)}")
                raise ConfigurationError(
                    "Failed to load credentials. Ensure QUERY_ID and TOKEN are set in .env file"
                ) from e

            # Create client
            client = FlexQueryClient(
                query_id=credentials.query_id,
                token=credentials.token,
            )

            # Fetch statement with timeout
            try:
                if ctx:
                    await ctx.debug(f"Calling IB Flex Query API (timeout={API_FETCH_TIMEOUT}s)")

                # Run synchronous API call in thread pool with timeout
                async def fetch_with_timeout():
                    return await asyncio.to_thread(client.fetch_statement, from_date, to_date)

                statement = await asyncio.wait_for(fetch_with_timeout(), timeout=API_FETCH_TIMEOUT)

            except asyncio.TimeoutError as e:  # noqa: UP041
                if ctx:
                    await ctx.error(
                        f"API call timed out after {API_FETCH_TIMEOUT}s",
                        extra={"timeout": API_FETCH_TIMEOUT, "operation": "fetch_statement"},
                    )
                raise IBTimeoutError(
                    f"IB API call timed out after {API_FETCH_TIMEOUT} seconds",
                    operation="fetch_statement",
                ) from e

            except FlexQueryAPIError as e:
                if ctx:
                    await ctx.error(
                        f"IB API error: {str(e)}", extra={"error_type": "FlexQueryAPIError"}
                    )
                raise APIError(str(e)) from e

            # Save to file with timeout
            try:
                data_dir = Path("data/raw")
                data_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{statement.account_id}_{from_date}_{to_date}.csv"
                filepath = data_dir / filename

                async def save_file():
                    await asyncio.to_thread(
                        filepath.write_text, statement.raw_data, encoding="utf-8"
                    )

                await asyncio.wait_for(save_file(), timeout=FILE_OPERATION_TIMEOUT)

                if ctx:
                    await ctx.info(
                        f"Saved data to {filepath}",
                        extra={
                            "file_path": str(filepath),
                            "file_size_bytes": len(statement.raw_data),
                        },
                    )

            except asyncio.TimeoutError as e:  # noqa: UP041
                if ctx:
                    await ctx.error(f"File write timed out after {FILE_OPERATION_TIMEOUT}s")
                raise IBTimeoutError(
                    f"File write timed out after {FILE_OPERATION_TIMEOUT} seconds",
                    operation="save_file",
                ) from e

            except Exception as e:
                if ctx:
                    await ctx.error(f"File operation failed: {str(e)}")
                raise FileOperationError(f"Failed to save data to {filepath}: {str(e)}") from e

            return {
                "account_id": statement.account_id,
                "date_range": {"from": str(from_date), "to": str(to_date)},
                "file_path": str(filepath),
                "status": "success",
            }

        except (ValidationError, ConfigurationError, APIError, FileOperationError, IBTimeoutError):
            # Re-raise our custom exceptions (they are already ToolErrors)
            raise

        except Exception as e:
            # Catch any unexpected errors
            if ctx:
                await ctx.error(
                    f"Unexpected error: {str(e)}", extra={"error_type": type(e).__name__}
                )
            raise APIError(f"Unexpected error while fetching IB data: {str(e)}") from e

    @mcp.tool
    async def analyze_performance(
        start_date: str,
        end_date: str | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Analyze trading performance

        Automatically fetches data from IB API (with caching) and performs analysis.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON string with performance metrics

        Raises:
            ValidationError: If input validation fails
            ConfigurationError: If credentials are missing
            APIError: If IB API call fails
            IBTimeoutError: If operation times out
        """
        if ctx:
            await ctx.info(f"Analyzing performance for {start_date} to {end_date or 'today'}")

        # Get or fetch data
        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )

        # Auto-detect format and parse
        format_type = detect_format(data)
        if format_type == "xml":
            account = XMLParser.to_account(data, from_date, to_date)
        else:
            account = CSVParser.to_account(data, from_date, to_date)

        # Run analysis
        analyzer = PerformanceAnalyzer(account=account)
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def analyze_costs(
        start_date: str,
        end_date: str | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Analyze trading costs and commissions

        Automatically fetches data from IB API (with caching) and performs analysis.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON string with cost analysis
        """
        if ctx:
            await ctx.info(f"Analyzing costs for {start_date} to {end_date or 'today'}")

        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )

        format_type = detect_format(data)
        if format_type == "xml":
            account = XMLParser.to_account(data, from_date, to_date)
        else:
            account = CSVParser.to_account(data, from_date, to_date)

        analyzer = CostAnalyzer(account=account)
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def analyze_bonds(
        start_date: str,
        end_date: str | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Analyze zero-coupon bonds (STRIPS)

        Automatically fetches data from IB API (with caching) and performs analysis.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON string with bond analysis including YTM, duration, etc.
        """
        if ctx:
            await ctx.info(f"Analyzing bonds for {start_date} to {end_date or 'today'}")

        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )

        format_type = detect_format(data)
        if format_type == "xml":
            account = XMLParser.to_account(data, from_date, to_date)
        else:
            account = CSVParser.to_account(data, from_date, to_date)

        analyzer = BondAnalyzer(account=account)
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def analyze_tax(
        start_date: str,
        end_date: str | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Analyze tax implications including Phantom Income (OID) for bonds

        Automatically fetches data from IB API (with caching) and performs analysis.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON string with tax analysis
        """
        if ctx:
            await ctx.info(f"Analyzing tax for {start_date} to {end_date or 'today'}")

        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )

        format_type = detect_format(data)
        if format_type == "xml":
            account = XMLParser.to_account(data, from_date, to_date)
        else:
            account = CSVParser.to_account(data, from_date, to_date)

        analyzer = TaxAnalyzer(account=account)
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def analyze_risk(
        start_date: str,
        end_date: str | None = None,
        account_index: int = 0,
        interest_rate_change: float = 0.01,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Analyze portfolio risk including interest rate scenarios

        Automatically fetches data from IB API (with caching) and performs analysis.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            account_index: Account index (0 for first account, 1 for second, etc.)
            interest_rate_change: Interest rate change for scenario (default: 0.01 = 1%)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON string with risk analysis
        """
        if ctx:
            await ctx.info(
                f"Analyzing risk for {start_date} to {end_date or 'today'} with {interest_rate_change * 100:.2f}% rate change"
            )

        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )

        format_type = detect_format(data)
        if format_type == "xml":
            account = XMLParser.to_account(data, from_date, to_date)
        else:
            account = CSVParser.to_account(data, from_date, to_date)

        analyzer = RiskAnalyzer(account=account)
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def get_portfolio_summary(csv_path: str, ctx: Context | None = None) -> str:
        """
        Get comprehensive portfolio summary

        Args:
            csv_path: Path to IB Flex Query CSV/XML file
            ctx: MCP context for logging

        Returns:
            JSON string with portfolio summary (includes all accounts if multiple)
        """
        if ctx:
            await ctx.info(f"Getting portfolio summary from {csv_path}")

        with open(csv_path) as f:
            data = f.read()

        from_date, to_date = _extract_dates_from_filename(csv_path)

        # Auto-detect format and parse all accounts
        format_type = detect_format(data)
        if format_type == "xml":
            accounts = XMLParser.to_accounts(data, from_date, to_date)
        else:
            accounts = CSVParser.to_accounts(data, from_date, to_date)

        # If multiple accounts, return aggregated summary
        if len(accounts) > 1:
            from decimal import Decimal

            total_cash = Decimal("0")
            total_value = Decimal("0")
            total_positions = 0
            total_trades = 0

            account_details = []

            for _acc_id, account in accounts.items():
                total_cash += account.total_cash
                total_value += account.total_value
                total_positions += len(account.positions)
                total_trades += len(account.trades)

                account_details.append(
                    {
                        "account_id": account.account_id,
                        "account_alias": account.account_alias,
                        "cash": str(account.total_cash),
                        "value": str(account.total_value),
                        "num_positions": len(account.positions),
                        "num_trades": len(account.trades),
                    }
                )

            summary = {
                "num_accounts": len(accounts),
                "base_currency": "USD",
                "total_cash": str(total_cash),
                "total_value": str(total_value),
                "num_trades": total_trades,
                "num_positions": total_positions,
                "date_range": {
                    "from": str(from_date),
                    "to": str(to_date),
                },
                "accounts": account_details,
            }
        else:
            # Single account
            account = list(accounts.values())[0]
            summary = {
                "num_accounts": 1,
                "account_id": account.account_id,
                "account_alias": account.account_alias,
                "base_currency": account.base_currency,
                "total_cash": str(account.total_cash),
                "total_value": str(account.total_value),
                "num_trades": len(account.trades),
                "num_positions": len(account.positions),
                "date_range": {
                    "from": str(account.from_date),
                    "to": str(account.to_date),
                },
            }

        return json.dumps(summary, indent=2)


__all__ = ["register_ib_portfolio_tools"]
