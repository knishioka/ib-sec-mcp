"""MCP Tools for IB Analytics

Exposes IB Analytics functionality as MCP tools callable by LLMs.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastmcp import Context, FastMCP

from ib_sec_mcp.analyzers.bond import BondAnalyzer
from ib_sec_mcp.analyzers.cost import CostAnalyzer
from ib_sec_mcp.analyzers.performance import PerformanceAnalyzer
from ib_sec_mcp.analyzers.risk import RiskAnalyzer
from ib_sec_mcp.analyzers.tax import TaxAnalyzer
from ib_sec_mcp.api.client import FlexQueryClient
from ib_sec_mcp.core.parsers import CSVParser
from ib_sec_mcp.utils.config import Config


def register_tools(mcp: FastMCP) -> None:
    """Register all IB Analytics tools with MCP server"""

    @mcp.tool
    async def fetch_ib_data(
        start_date: str,
        end_date: Optional[str] = None,
        account_index: int = 0,
        ctx: Optional[Context] = None,
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
        """
        if ctx:
            await ctx.info(f"Fetching IB data from {start_date} to {end_date or 'today'}")

        # Parse dates
        from_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        to_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()

        # Load config and fetch
        config = Config.load()
        credentials = config.get_credentials()

        if account_index >= len(credentials):
            raise ValueError(
                f"Account index {account_index} out of range (have {len(credentials)} accounts)"
            )

        client = FlexQueryClient(credentials=credentials)
        statement = client.fetch_statement(from_date, to_date, account_index)

        # Save to file
        data_dir = Path("data/raw")
        data_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{statement.account_id}_{from_date}_{to_date}.csv"
        filepath = data_dir / filename

        with open(filepath, "w") as f:
            f.write(statement.raw_data)

        if ctx:
            await ctx.info(f"Saved data to {filepath}")

        return {
            "account_id": statement.account_id,
            "date_range": {"from": str(from_date), "to": str(to_date)},
            "file_path": str(filepath),
            "status": "success",
        }

    @mcp.tool
    async def analyze_performance(csv_path: str, ctx: Optional[Context] = None) -> str:
        """
        Analyze trading performance from CSV data

        Args:
            csv_path: Path to IB Flex Query CSV file
            ctx: MCP context for logging

        Returns:
            JSON string with performance metrics
        """
        if ctx:
            await ctx.info(f"Analyzing performance from {csv_path}")

        # Parse CSV
        with open(csv_path) as f:
            csv_data = f.read()

        account = CSVParser.to_account(csv_data)

        # Run analysis
        analyzer = PerformanceAnalyzer(account=account)
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def analyze_costs(csv_path: str, ctx: Optional[Context] = None) -> str:
        """
        Analyze trading costs and commissions from CSV data

        Args:
            csv_path: Path to IB Flex Query CSV file
            ctx: MCP context for logging

        Returns:
            JSON string with cost analysis
        """
        if ctx:
            await ctx.info(f"Analyzing costs from {csv_path}")

        with open(csv_path) as f:
            csv_data = f.read()

        account = CSVParser.to_account(csv_data)
        analyzer = CostAnalyzer(account=account)
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def analyze_bonds(csv_path: str, ctx: Optional[Context] = None) -> str:
        """
        Analyze zero-coupon bonds (STRIPS) from CSV data

        Args:
            csv_path: Path to IB Flex Query CSV file
            ctx: MCP context for logging

        Returns:
            JSON string with bond analysis including YTM, duration, etc.
        """
        if ctx:
            await ctx.info(f"Analyzing bonds from {csv_path}")

        with open(csv_path) as f:
            csv_data = f.read()

        account = CSVParser.to_account(csv_data)
        analyzer = BondAnalyzer(account=account)
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def analyze_tax(csv_path: str, ctx: Optional[Context] = None) -> str:
        """
        Analyze tax implications including Phantom Income (OID) for bonds

        Args:
            csv_path: Path to IB Flex Query CSV file
            ctx: MCP context for logging

        Returns:
            JSON string with tax analysis
        """
        if ctx:
            await ctx.info(f"Analyzing tax from {csv_path}")

        with open(csv_path) as f:
            csv_data = f.read()

        account = CSVParser.to_account(csv_data)
        analyzer = TaxAnalyzer(account=account)
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def analyze_risk(
        csv_path: str,
        interest_rate_change: float = 0.01,
        ctx: Optional[Context] = None,
    ) -> str:
        """
        Analyze portfolio risk including interest rate scenarios

        Args:
            csv_path: Path to IB Flex Query CSV file
            interest_rate_change: Interest rate change for scenario (default: 0.01 = 1%)
            ctx: MCP context for logging

        Returns:
            JSON string with risk analysis
        """
        if ctx:
            await ctx.info(
                f"Analyzing risk from {csv_path} with {interest_rate_change*100:.2f}% rate change"
            )

        with open(csv_path) as f:
            csv_data = f.read()

        account = CSVParser.to_account(csv_data)
        analyzer = RiskAnalyzer(account=account)
        result = analyzer.analyze()

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def get_portfolio_summary(csv_path: str, ctx: Optional[Context] = None) -> str:
        """
        Get comprehensive portfolio summary

        Args:
            csv_path: Path to IB Flex Query CSV file
            ctx: MCP context for logging

        Returns:
            JSON string with portfolio summary
        """
        if ctx:
            await ctx.info(f"Getting portfolio summary from {csv_path}")

        with open(csv_path) as f:
            csv_data = f.read()

        account = CSVParser.to_account(csv_data)

        summary = {
            "account_id": account.account_id,
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
