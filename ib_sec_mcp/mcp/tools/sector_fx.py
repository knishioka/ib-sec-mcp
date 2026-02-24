"""Sector Allocation and FX Exposure Analysis Tools

MCP tools for analyzing portfolio sector concentration risk
and currency exposure.
"""

import json
from decimal import Decimal

from fastmcp import Context, FastMCP

from ib_sec_mcp.analyzers.fx import FXExposureAnalyzer
from ib_sec_mcp.analyzers.sector import SectorAnalyzer
from ib_sec_mcp.core.parsers import XMLParser, detect_format
from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.mcp.tools.ib_portfolio import _get_or_fetch_data
from ib_sec_mcp.mcp.validators import validate_account_index


def register_sector_fx_tools(mcp: FastMCP) -> None:
    """Register sector allocation and FX exposure analysis tools."""

    @mcp.tool
    async def analyze_sector_allocation(
        start_date: str,
        end_date: str | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Analyze portfolio sector allocation and concentration risk.

        Fetches sector/industry data from Yahoo Finance for equity positions
        and categorizes non-equity positions (bonds, options, etc.) separately.
        Calculates Herfindahl-Hirschman Index (HHI) for concentration risk.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON string with sector allocation analysis including:
            - Sector breakdown with values and percentages
            - Per-sector position list
            - Concentration risk score (HHI) and assessment
            - Equity vs non-equity breakdown

        Raises:
            ValidationError: If input validation fails
            ConfigurationError: If credentials are missing
            APIError: If IB API call fails

        Example:
            >>> result = await analyze_sector_allocation("2025-01-01")
        """
        validate_account_index(account_index)

        if ctx:
            await ctx.info(f"Analyzing sector allocation for {start_date} to {end_date or 'today'}")

        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )

        detect_format(data)
        accounts = XMLParser.to_accounts(data, from_date, to_date)

        if not accounts:
            raise ValidationError("No accounts found in data")

        account_list = list(accounts.values())
        if account_index >= len(account_list):
            raise ValidationError(
                f"account_index {account_index} out of range (0-{len(account_list) - 1})"
            )

        account = account_list[account_index]

        if ctx:
            await ctx.info(f"Found {len(account.positions)} positions, fetching sector data...")

        analyzer = SectorAnalyzer(account=account)
        result = await analyzer.analyze_async()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def analyze_fx_exposure(
        start_date: str,
        end_date: str | None = None,
        account_index: int = 0,
        fx_scenario_pct: float = 10.0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Analyze portfolio FX (foreign exchange) exposure.

        Calculates currency-level exposure from positions and cash balances,
        simulates FX fluctuation impact (+/- scenario percentage), and provides
        hedge recommendations based on concentration thresholds.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            account_index: Account index (0 for first account, 1 for second, etc.)
            fx_scenario_pct: FX fluctuation percentage for scenario simulation
                (default: 10.0 for +/-10%)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON string with FX exposure analysis including:
            - Currency breakdown with position values and percentages
            - FX scenario simulation results (+/- configured percentage)
            - Aggregate portfolio impact
            - Hedge recommendations based on exposure levels

        Raises:
            ValidationError: If input validation fails
            ConfigurationError: If credentials are missing
            APIError: If IB API call fails

        Example:
            >>> result = await analyze_fx_exposure("2025-01-01", fx_scenario_pct=15.0)
        """
        validate_account_index(account_index)

        if fx_scenario_pct <= 0 or fx_scenario_pct > 100:
            raise ValidationError(
                "fx_scenario_pct must be between 0 and 100",
                field="fx_scenario_pct",
            )

        if ctx:
            await ctx.info(
                f"Analyzing FX exposure for {start_date} to {end_date or 'today'} "
                f"with +/-{fx_scenario_pct}% scenario"
            )

        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )

        detect_format(data)
        accounts = XMLParser.to_accounts(data, from_date, to_date)

        if not accounts:
            raise ValidationError("No accounts found in data")

        account_list = list(accounts.values())
        if account_index >= len(account_list):
            raise ValidationError(
                f"account_index {account_index} out of range (0-{len(account_list) - 1})"
            )

        account = account_list[account_index]
        base_currency = account.base_currency

        if ctx:
            await ctx.info(
                f"Found {len(account.positions)} positions, base currency: {base_currency}"
            )

        analyzer = FXExposureAnalyzer(
            account=account,
            fx_scenario_pct=Decimal(str(fx_scenario_pct)),
            base_currency=base_currency,
        )
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)
