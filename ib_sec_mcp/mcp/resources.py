"""MCP Resources for IB Analytics

Provides read-only access to portfolio data via URI patterns.
"""

import json
from pathlib import Path

from fastmcp import FastMCP

from ib_sec_mcp.core.parsers import CSVParser


def register_resources(mcp: FastMCP) -> None:
    """Register all IB Analytics resources with MCP server"""

    @mcp.resource("ib://portfolio/list")
    def list_portfolio_files() -> str:
        """
        List all available portfolio CSV files

        Returns:
            JSON string with list of available files
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"files": [], "message": "No data directory found"})

        files = []
        for csv_file in data_dir.glob("*.csv"):
            files.append(
                {
                    "filename": csv_file.name,
                    "path": str(csv_file),
                    "size_bytes": csv_file.stat().st_size,
                    "modified": csv_file.stat().st_mtime,
                }
            )

        files.sort(key=lambda x: x["modified"], reverse=True)
        return json.dumps({"files": files, "count": len(files)}, indent=2)

    @mcp.resource("ib://portfolio/latest")
    def get_latest_portfolio() -> str:
        """
        Get summary of the most recently modified portfolio file

        Returns:
            JSON string with latest portfolio summary
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"error": "No data directory found"})

        csv_files = list(data_dir.glob("*.csv"))
        if not csv_files:
            return json.dumps({"error": "No CSV files found"})

        # Get most recent file
        latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)

        with open(latest_file) as f:
            csv_data = f.read()

        account = CSVParser.to_account(csv_data)

        summary = {
            "file": latest_file.name,
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

    @mcp.resource("ib://accounts/{account_id}")
    def get_account_data(account_id: str) -> str:
        """
        Get data for a specific account ID

        Args:
            account_id: IB account ID (e.g., U12345678)

        Returns:
            JSON string with account data
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"error": "No data directory found"})

        # Find file matching account ID
        matching_files = [f for f in data_dir.glob("*.csv") if account_id in f.name]

        if not matching_files:
            return json.dumps({"error": f"No files found for account {account_id}"})

        # Use most recent file
        latest_file = max(matching_files, key=lambda f: f.stat().st_mtime)

        with open(latest_file) as f:
            csv_data = f.read()

        account = CSVParser.to_account(csv_data)

        # Basic account info
        account_data = {
            "account_id": account.account_id,
            "base_currency": account.base_currency,
            "total_cash": str(account.total_cash),
            "total_value": str(account.total_value),
            "date_range": {
                "from": str(account.from_date),
                "to": str(account.to_date),
            },
            "file": latest_file.name,
        }

        return json.dumps(account_data, indent=2)

    @mcp.resource("ib://trades/recent")
    def get_recent_trades() -> str:
        """
        Get most recent trades from latest portfolio file

        Returns:
            JSON string with recent trades (last 10)
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"error": "No data directory found"})

        csv_files = list(data_dir.glob("*.csv"))
        if not csv_files:
            return json.dumps({"error": "No CSV files found"})

        latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)

        with open(latest_file) as f:
            csv_data = f.read()

        account = CSVParser.to_account(csv_data)

        # Sort trades by date descending
        sorted_trades = sorted(account.trades, key=lambda t: t.trade_date, reverse=True)

        # Get last 10 trades
        recent = sorted_trades[:10]

        trades_data = [
            {
                "date": str(t.trade_date),
                "symbol": t.symbol,
                "buy_sell": t.buy_sell.value,
                "quantity": str(t.quantity),
                "price": str(t.trade_price),
                "commission": str(t.ib_commission),
                "pnl": str(t.fifo_pnl_realized),
            }
            for t in recent
        ]

        return json.dumps({"trades": trades_data, "count": len(trades_data)}, indent=2)

    @mcp.resource("ib://positions/current")
    def get_current_positions() -> str:
        """
        Get current positions from latest portfolio file

        Returns:
            JSON string with current positions
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"error": "No data directory found"})

        csv_files = list(data_dir.glob("*.csv"))
        if not csv_files:
            return json.dumps({"error": "No CSV files found"})

        latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)

        with open(latest_file) as f:
            csv_data = f.read()

        account = CSVParser.to_account(csv_data)

        positions_data = [
            {
                "symbol": p.symbol,
                "description": p.description,
                "quantity": str(p.quantity),
                "cost_basis": str(p.cost_basis_money),
                "market_value": str(p.position_value),
                "unrealized_pnl": str(p.unrealized_pnl),
                "asset_class": p.asset_class.value if p.asset_class else None,
            }
            for p in account.positions
        ]

        return json.dumps({"positions": positions_data, "count": len(positions_data)}, indent=2)
