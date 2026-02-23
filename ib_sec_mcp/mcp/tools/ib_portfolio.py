"""IB Portfolio Analysis Tools

Interactive Brokers portfolio analysis and data fetching tools.
"""

import asyncio
import json
import warnings
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from fastmcp import Context, FastMCP

from ib_sec_mcp.analyzers.bond import BondAnalyzer
from ib_sec_mcp.analyzers.cost import CostAnalyzer
from ib_sec_mcp.analyzers.performance import PerformanceAnalyzer
from ib_sec_mcp.analyzers.risk import RiskAnalyzer
from ib_sec_mcp.analyzers.tax import TaxAnalyzer
from ib_sec_mcp.api.client import FlexQueryAPIError, FlexQueryClient
from ib_sec_mcp.core.parsers import XMLParser, detect_format
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
    validate_file_path,
)
from ib_sec_mcp.utils.config import Config
from ib_sec_mcp.utils.logger import get_logger

logger = get_logger(__name__)

# Timeout constants (in seconds)
API_FETCH_TIMEOUT = 60
FILE_OPERATION_TIMEOUT = 10


def _extract_dates_from_filename(file_path: str) -> tuple[date, date]:
    """
    Extract from_date and to_date from XML filename

    Expected format: {account_id}_{from_date}_{to_date}.xml
    Example: UXXXXXXXX_2025-01-01_2025-10-07.xml
    """
    filename = Path(file_path).stem  # Remove .xml extension
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
    logger.debug(
        f"_get_or_fetch_data called: start_date={start_date}, end_date={end_date}, account_index={account_index}, use_cache={use_cache}"
    )

    # Validate inputs
    from_date = validate_date_string(start_date, "start_date")
    to_date = validate_date_string(end_date, "end_date") if end_date else date.today()
    from_date, to_date = validate_date_range(from_date, to_date)
    validate_account_index(account_index)

    logger.debug(f"Validated date range: {from_date} to {to_date}")

    # Check cache first
    if use_cache:
        logger.debug("Checking cache for existing data")
        # Try to find cached file
        try:
            data_dir = Path("data/raw")
            # We don't know exact account_id yet, so try pattern matching
            pattern = f"*_{from_date}_{to_date}.xml"
            logger.debug(f"Cache search pattern: {pattern} in {data_dir}")

            cached_files = list(data_dir.glob(pattern))
            logger.debug(f"Found {len(cached_files)} cached file(s)")

            if cached_files:
                cached_file = cached_files[0]  # Use first match
                logger.info(f"Using cached data from {cached_file}")
                if ctx:
                    await ctx.info(f"Using cached data from {cached_file}")

                with open(cached_file) as f:
                    data = f.read()

                logger.debug(f"Loaded {len(data)} bytes from cache")
                return data, from_date, to_date
            else:
                logger.debug("No cached files found, will fetch from API")
        except Exception as e:  # nosec B110
            # If cache lookup fails, proceed to fetch
            logger.warning(f"Cache lookup failed: {e}, proceeding to API fetch")
            pass
    else:
        logger.debug("Cache disabled (use_cache=False), will fetch from API")

    # No cache or cache disabled - fetch from API
    logger.info(f"Fetching fresh data from IB API for {from_date} to {to_date}")
    if ctx:
        await ctx.info(f"Fetching fresh data from IB API for {from_date} to {to_date}")

    # Load configuration
    try:
        logger.debug("Loading configuration and credentials")
        config = Config.load()
        credentials = config.get_credentials()

        # Note: account_index currently not supported (single account config)
        # Multi-account support requires config changes
        if account_index != 0:
            warning_msg = f"account_index {account_index} specified but only single account supported. Using default account."
            logger.warning(warning_msg)
            if ctx:
                await ctx.warning(warning_msg)
    except Exception as e:
        logger.error(f"Configuration error: {str(e)}", exc_info=True)
        if ctx:
            await ctx.error(f"Configuration error: {str(e)}")
        raise ConfigurationError(
            "Failed to load credentials. Ensure QUERY_ID and TOKEN are set in .env file"
        ) from e

    # Create client
    logger.debug("Creating FlexQueryClient")
    client = FlexQueryClient(
        query_id=credentials.query_id,
        token=credentials.token,
    )

    # Fetch statement with timeout
    try:
        logger.debug(f"Calling IB Flex Query API (timeout={API_FETCH_TIMEOUT}s)")
        if ctx:
            await ctx.debug(f"Calling IB Flex Query API (timeout={API_FETCH_TIMEOUT}s)")

        async def fetch_with_timeout():
            return await asyncio.to_thread(client.fetch_statement, from_date, to_date)

        statement = await asyncio.wait_for(fetch_with_timeout(), timeout=API_FETCH_TIMEOUT)
        logger.info(f"Successfully fetched data from IB API: {len(statement.raw_data)} bytes")

    except asyncio.TimeoutError as e:  # noqa: UP041
        logger.error(f"API call timed out after {API_FETCH_TIMEOUT}s")
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
        logger.error(f"IB API error: {str(e)}")
        if ctx:
            await ctx.error(f"IB API error: {str(e)}", extra={"error_type": "FlexQueryAPIError"})
        raise APIError(str(e)) from e

    # Save to cache
    try:
        data_dir = Path("data/raw")
        data_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{statement.account_id}_{from_date}_{to_date}.xml"
        filepath = data_dir / filename

        logger.debug(f"Saving data to cache: {filepath}")

        async def save_file():
            await asyncio.to_thread(filepath.write_text, statement.raw_data, encoding="utf-8")

        await asyncio.wait_for(save_file(), timeout=FILE_OPERATION_TIMEOUT)

        logger.info(f"Saved data to cache: {filepath} ({len(statement.raw_data)} bytes)")
        if ctx:
            await ctx.info(
                f"Saved data to {filepath}",
                extra={
                    "file_path": str(filepath),
                    "file_size_bytes": len(statement.raw_data),
                },
            )

    except asyncio.TimeoutError as e:  # noqa: UP041
        logger.error(f"File write timed out after {FILE_OPERATION_TIMEOUT}s")
        if ctx:
            await ctx.error(f"File write timed out after {FILE_OPERATION_TIMEOUT}s")
        raise IBTimeoutError(
            f"File write timed out after {FILE_OPERATION_TIMEOUT} seconds",
            operation="save_file",
        ) from e

    except Exception as e:
        logger.error(f"File operation failed: {str(e)}")
        if ctx:
            await ctx.error(f"File operation failed: {str(e)}")
        raise FileOperationError(f"Failed to save data to {filepath}: {str(e)}") from e

    logger.debug("_get_or_fetch_data completed successfully")
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
                        extra={
                            "timeout": API_FETCH_TIMEOUT,
                            "operation": "fetch_statement",
                        },
                    )
                raise IBTimeoutError(
                    f"IB API call timed out after {API_FETCH_TIMEOUT} seconds",
                    operation="fetch_statement",
                ) from e

            except FlexQueryAPIError as e:
                if ctx:
                    await ctx.error(
                        f"IB API error: {str(e)}",
                        extra={"error_type": "FlexQueryAPIError"},
                    )
                raise APIError(str(e)) from e

            # Save to file with timeout
            try:
                data_dir = Path("data/raw")
                data_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{statement.account_id}_{from_date}_{to_date}.xml"
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

            # Auto-sync to SQLite storage
            try:
                if ctx:
                    await ctx.info("Auto-syncing positions to SQLite database")

                # Import storage here to avoid circular dependency
                from ib_sec_mcp.storage import PositionStore

                # Parse accounts from XML
                accounts = XMLParser.to_accounts(statement.raw_data, from_date, to_date)

                # Save each account to SQLite
                store = PositionStore()
                total_positions_saved = 0
                for _account_id, account in accounts.items():
                    positions_saved = store.save_snapshot(
                        account=account, snapshot_date=to_date, xml_file_path=str(filepath)
                    )
                    total_positions_saved += positions_saved

                store.close()

                if ctx:
                    await ctx.info(
                        f"Auto-sync complete: {total_positions_saved} positions saved to SQLite",
                        extra={
                            "positions_saved": total_positions_saved,
                            "num_accounts": len(accounts),
                        },
                    )

            except Exception as e:
                # Log error but don't fail the entire operation
                # The XML file has been saved successfully
                logger.warning(f"Auto-sync to SQLite failed: {str(e)}", exc_info=True)
                if ctx:
                    await ctx.warning(
                        f"Auto-sync to SQLite failed: {str(e)}. XML file saved successfully."
                    )

            return {
                "account_id": statement.account_id,
                "date_range": {"from": str(from_date), "to": str(to_date)},
                "file_path": str(filepath),
                "status": "success",
            }

        except (
            ValidationError,
            ConfigurationError,
            APIError,
            FileOperationError,
            IBTimeoutError,
        ):
            # Re-raise our custom exceptions (they are already ToolErrors)
            raise

        except Exception as e:
            # Catch any unexpected errors
            if ctx:
                await ctx.error(
                    f"Unexpected error: {str(e)}",
                    extra={"error_type": type(e).__name__},
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

        # Validate XML format and parse all accounts
        detect_format(data)  # Raises ValueError if not XML
        accounts = XMLParser.to_accounts(data, from_date, to_date)

        # Select account by index
        if not accounts:
            raise ValidationError("No accounts found in data")

        account_list = list(accounts.values())
        if account_index >= len(account_list):
            raise ValidationError(
                f"account_index {account_index} out of range (0-{len(account_list) - 1})"
            )

        account = account_list[account_index]

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

        # Validate XML format and parse all accounts
        detect_format(data)  # Raises ValueError if not XML
        accounts = XMLParser.to_accounts(data, from_date, to_date)

        # Select account by index
        if not accounts:
            raise ValidationError("No accounts found in data")

        account_list = list(accounts.values())
        if account_index >= len(account_list):
            raise ValidationError(
                f"account_index {account_index} out of range (0-{len(account_list) - 1})"
            )

        account = account_list[account_index]

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

        # Validate XML format and parse all accounts
        detect_format(data)  # Raises ValueError if not XML
        accounts = XMLParser.to_accounts(data, from_date, to_date)

        # Select account by index
        if not accounts:
            raise ValidationError("No accounts found in data")

        account_list = list(accounts.values())
        if account_index >= len(account_list):
            raise ValidationError(
                f"account_index {account_index} out of range (0-{len(account_list) - 1})"
            )

        account = account_list[account_index]

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

        # Validate XML format and parse all accounts
        detect_format(data)  # Raises ValueError if not XML
        accounts = XMLParser.to_accounts(data, from_date, to_date)

        # Select account by index
        if not accounts:
            raise ValidationError("No accounts found in data")

        account_list = list(accounts.values())
        if account_index >= len(account_list):
            raise ValidationError(
                f"account_index {account_index} out of range (0-{len(account_list) - 1})"
            )

        account = account_list[account_index]

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

        # Validate XML format and parse all accounts
        detect_format(data)  # Raises ValueError if not XML
        accounts = XMLParser.to_accounts(data, from_date, to_date)

        # Select account by index
        if not accounts:
            raise ValidationError("No accounts found in data")

        account_list = list(accounts.values())
        if account_index >= len(account_list):
            raise ValidationError(
                f"account_index {account_index} out of range (0-{len(account_list) - 1})"
            )

        account = account_list[account_index]

        analyzer = RiskAnalyzer(account=account)
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def analyze_consolidated_portfolio(
        start_date: str | None = None,
        end_date: str | None = None,
        use_cache: bool = True,
        file_path: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """
        Analyze all accounts as a consolidated portfolio

        Supports two data sources:
        - API mode: Fetches data from IB API (with caching) using date parameters
        - File mode: Reads from a local XML file using file_path parameter

        Performs comprehensive analysis across all accounts, providing both
        consolidated metrics and per-account breakdown.

        Args:
            start_date: Start date in YYYY-MM-DD format (required for API mode)
            end_date: End date in YYYY-MM-DD format (defaults to today, API mode only)
            use_cache: Use cached data if available (default: True, API mode only)
            file_path: Path to IB Flex Query XML file (alternative to API mode).
                When provided, start_date/end_date/use_cache are ignored and dates
                are extracted from the filename.
            ctx: MCP context for logging

        Returns:
            JSON string with consolidated portfolio analysis including:
            - Total portfolio value and breakdown by account
            - Consolidated performance metrics
            - Holdings aggregated by symbol across accounts
            - Asset allocation and concentration risk
            - Tax summary across all accounts
            - Risk assessment for consolidated portfolio

        Raises:
            ValidationError: If input validation fails
            ConfigurationError: If credentials are missing
            APIError: If IB API call fails
            IBTimeoutError: If operation times out
        """
        if file_path:
            # File-based mode: read from local XML file
            if ctx:
                await ctx.info(f"Analyzing consolidated portfolio from file: {file_path}")

            validated_path = validate_file_path(file_path)
            with open(validated_path) as f:
                data = f.read()
            from_date, to_date = _extract_dates_from_filename(file_path)
        else:
            # API mode: fetch from IB API
            if not start_date:
                raise ValidationError(
                    "Either file_path or start_date must be provided",
                    field="start_date",
                )

            if ctx:
                await ctx.info(
                    f"Analyzing consolidated portfolio for {start_date} to {end_date or 'today'}"
                )

            # Get or fetch data
            data, from_date, to_date = await _get_or_fetch_data(
                start_date, end_date, account_index=0, use_cache=use_cache, ctx=ctx
            )

        # Validate XML format and parse all accounts
        detect_format(data)  # Raises ValueError if not XML
        accounts = XMLParser.to_accounts(data, from_date, to_date)

        if ctx:
            await ctx.info(f"Found {len(accounts)} account(s) to analyze")

        # Initialize consolidated metrics
        total_cash = Decimal("0")
        total_value = Decimal("0")
        total_trades = 0
        consolidated_positions_by_symbol = defaultdict(
            lambda: {
                "total_quantity": Decimal("0"),
                "total_value": Decimal("0"),
                "accounts": [],
                "position_metadata": None,  # Store first position's metadata
            }
        )
        account_summaries = []

        # Aggregate data across accounts
        for acc_id, account in accounts.items():
            total_cash += account.total_cash
            total_value += account.total_value
            total_trades += len(account.trades)

            # Aggregate positions by symbol
            for position in account.positions:
                symbol = position.symbol
                consolidated_positions_by_symbol[symbol]["total_quantity"] += position.quantity
                # Use position_value (market value) instead of cost_basis * quantity
                # This correctly handles bonds where quantity represents face value
                consolidated_positions_by_symbol[symbol]["total_value"] += position.position_value
                if acc_id not in consolidated_positions_by_symbol[symbol]["accounts"]:
                    consolidated_positions_by_symbol[symbol]["accounts"].append(acc_id)

                # Store metadata from first position (for identification purposes)
                if consolidated_positions_by_symbol[symbol]["position_metadata"] is None:
                    # Extract issuer country from ISIN (first 2 characters)
                    issuer_country = (
                        position.isin[:2] if position.isin and len(position.isin) >= 2 else None
                    )

                    consolidated_positions_by_symbol[symbol]["position_metadata"] = {
                        "asset_class": position.asset_class.value,
                        "description": position.description,
                        "isin": position.isin,
                        "cusip": position.cusip,
                        "issuer_country": issuer_country,
                        "maturity_date": str(position.maturity_date)
                        if position.maturity_date
                        else None,
                        "currency": position.currency,
                        "fx_rate_to_base": str(position.fx_rate_to_base),
                    }

            # Per-account summary
            account_summaries.append(
                {
                    "account_id": account.account_id,
                    "account_alias": account.account_alias or acc_id,
                    "cash": str(account.total_cash),
                    "value": str(account.total_value),
                    "percentage_of_total": str(
                        round(
                            ((account.total_value / total_value * 100) if total_value > 0 else 0),
                            2,
                        )
                    ),
                    "num_positions": len(account.positions),
                    "num_trades": len(account.trades),
                }
            )

        # Calculate consolidated holdings
        holdings_by_symbol = []
        for symbol, data in sorted(
            consolidated_positions_by_symbol.items(),
            key=lambda x: x[1]["total_value"],
            reverse=True,
        ):
            percentage = (
                round((data["total_value"] / total_value * 100), 2) if total_value > 0 else 0
            )

            # Build holding entry with metadata
            holding_entry = {
                "symbol": symbol,
                "total_quantity": str(data["total_quantity"]),
                "total_value": str(data["total_value"]),
                "percentage_of_portfolio": str(percentage),
                "num_accounts": len(data["accounts"]),
                "accounts": data["accounts"],
            }

            # Add metadata if available
            if data["position_metadata"]:
                metadata = data["position_metadata"]
                holding_entry["asset_class"] = metadata["asset_class"]

                # Generate enhanced description for bonds
                if metadata["asset_class"] == "BOND":
                    issuer_country = metadata.get("issuer_country", "")
                    maturity_date = metadata.get("maturity_date", "")

                    # US Treasury STRIPS: "US Treasury STRIPS 0% MM/DD/YYYY"
                    if issuer_country == "US" and "STRIP" in symbol.upper():
                        if maturity_date:
                            # Format: 2040-11-15 → 11/15/2040
                            try:
                                mat_date = datetime.strptime(maturity_date, "%Y-%m-%d")
                                formatted_date = mat_date.strftime("%m/%d/%Y")
                                enhanced_desc = f"US Treasury STRIPS 0% {formatted_date}"
                            except (ValueError, TypeError):
                                enhanced_desc = f"US Treasury STRIPS 0% {maturity_date}"
                        else:
                            enhanced_desc = "US Treasury STRIPS 0%"
                    # Other bonds: "{Country} Bond - {original description}"
                    else:
                        country_name = issuer_country if issuer_country else "Unknown"
                        enhanced_desc = f"{country_name} Bond - {metadata['description']}"

                    holding_entry["description"] = enhanced_desc
                    holding_entry["original_description"] = metadata["description"]
                else:
                    holding_entry["description"] = metadata["description"]

                if metadata["isin"]:
                    holding_entry["isin"] = metadata["isin"]
                if metadata["cusip"]:
                    holding_entry["cusip"] = metadata["cusip"]
                if metadata["issuer_country"]:
                    holding_entry["issuer_country"] = metadata["issuer_country"]
                if metadata["maturity_date"]:
                    holding_entry["maturity_date"] = metadata["maturity_date"]
                if metadata.get("currency"):
                    holding_entry["currency"] = metadata["currency"]
                if metadata.get("fx_rate_to_base"):
                    holding_entry["fx_rate_to_base"] = metadata["fx_rate_to_base"]

            holdings_by_symbol.append(holding_entry)

        # Calculate asset allocation
        stocks_value = Decimal("0")
        bonds_value = Decimal("0")
        bonds_by_country = defaultdict(Decimal)  # Track bonds by country

        for _symbol, data in consolidated_positions_by_symbol.items():
            # Use metadata for accurate classification
            metadata = data.get("position_metadata")
            if metadata and metadata.get("asset_class") == "BOND":
                bonds_value += data["total_value"]
                # Track by country
                issuer_country = metadata.get("issuer_country", "Unknown")
                bonds_by_country[issuer_country] += data["total_value"]
            else:
                stocks_value += data["total_value"]

        # Concentration risk
        largest_position_pct = (
            round((Decimal(holdings_by_symbol[0]["total_value"]) / total_value * 100), 2)
            if holdings_by_symbol and total_value > 0
            else 0
        )
        top_3_value = sum(
            Decimal(h["total_value"]) for h in holdings_by_symbol[:3] if holdings_by_symbol
        )
        top_3_pct = round((top_3_value / total_value * 100), 2) if total_value > 0 else 0

        # Build consolidated result
        result = {
            "analysis_period": {"from": str(from_date), "to": str(to_date)},
            "num_accounts": len(accounts),
            "total_portfolio_value": str(total_value),
            "total_cash": str(total_cash),
            "total_invested": str(total_value - total_cash),
            "cash_percentage": (
                str(round((total_cash / total_value * 100), 2)) if total_value > 0 else "0.0"
            ),
            "accounts": account_summaries,
            "consolidated_holdings": {
                "num_unique_symbols": len(consolidated_positions_by_symbol),
                "total_num_positions": sum(len(acc.positions) for acc in accounts.values()),
                "holdings_by_symbol": holdings_by_symbol,
            },
            "asset_allocation": {
                "stocks": {
                    "value": str(stocks_value),
                    "percentage": (
                        str(round((stocks_value / total_value * 100), 2))
                        if total_value > 0
                        else "0.0"
                    ),
                },
                "bonds": {
                    "value": str(bonds_value),
                    "percentage": (
                        str(round((bonds_value / total_value * 100), 2))
                        if total_value > 0
                        else "0.0"
                    ),
                    "by_country": {
                        country: {
                            "value": str(value),
                            "percentage": (
                                str(round((value / bonds_value * 100), 2))
                                if bonds_value > 0
                                else "0.0"
                            ),
                            "percentage_of_portfolio": (
                                str(round((value / total_value * 100), 2))
                                if total_value > 0
                                else "0.0"
                            ),
                        }
                        for country, value in sorted(
                            bonds_by_country.items(), key=lambda x: x[1], reverse=True
                        )
                    },
                },
                "cash": {
                    "value": str(total_cash),
                    "percentage": (
                        str(round((total_cash / total_value * 100), 2))
                        if total_value > 0
                        else "0.0"
                    ),
                },
            },
            "concentration_risk": {
                "largest_position_percentage": str(largest_position_pct),
                "largest_position_symbol": (
                    holdings_by_symbol[0]["symbol"] if holdings_by_symbol else None
                ),
                "top_3_positions_percentage": str(top_3_pct),
                "assessment": (
                    "HIGH"
                    if largest_position_pct > 15
                    else "MEDIUM"
                    if largest_position_pct > 10
                    else "LOW"
                ),
            },
            "trading_activity": {
                "total_trades": total_trades,
                "trades_per_account": {
                    summary["account_id"]: summary["num_trades"] for summary in account_summaries
                },
            },
        }

        if ctx:
            await ctx.info(
                f"Consolidated analysis complete: {len(accounts)} accounts, "
                f"{len(consolidated_positions_by_symbol)} unique symbols, "
                f"${total_value:,.2f} total value"
            )

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def get_portfolio_summary(file_path: str, ctx: Context | None = None) -> str:
        """
        Get comprehensive portfolio summary

        .. deprecated::
            Use ``analyze_consolidated_portfolio(file_path=...)`` instead.
            It provides richer analysis including holdings, asset allocation,
            and concentration risk.

        Args:
            file_path: Path to IB Flex Query XML file
            ctx: MCP context for logging

        Returns:
            JSON string with portfolio summary (includes all accounts if multiple)
        """
        warnings.warn(
            "get_portfolio_summary is deprecated. "
            "Use analyze_consolidated_portfolio(file_path=...) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if ctx:
            await ctx.info(
                "Note: get_portfolio_summary is deprecated. "
                "Use analyze_consolidated_portfolio(file_path=...) instead."
            )
            await ctx.info(f"Getting portfolio summary from {file_path}")

        with open(file_path) as f:
            data = f.read()

        from_date, to_date = _extract_dates_from_filename(file_path)

        # Validate XML format and parse all accounts
        detect_format(data)  # Raises ValueError if not XML
        accounts = XMLParser.to_accounts(data, from_date, to_date)

        # If multiple accounts, return aggregated summary
        if len(accounts) > 1:
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
