"""Console report generator"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ib_sec_mcp.analyzers.base import AnalysisResult
from ib_sec_mcp.reports.base import BaseReport


class ConsoleReport(BaseReport):
    """
    Generate formatted console report using Rich

    Provides beautiful console output with tables and formatting
    """

    def __init__(self, results: list[AnalysisResult]):
        """Initialize console report"""
        super().__init__(results)
        self.console = Console()

    def render(self) -> str:
        """Render report to console"""

        for result in self.results:
            analyzer_name = result.get("analyzer", "Unknown")

            # Create section header
            header = f"📊 {analyzer_name.upper()} ANALYSIS"
            self.console.print(f"\n{'=' * 80}", style="bold blue")
            self.console.print(header, style="bold blue")
            self.console.print(f"{'=' * 80}\n", style="bold blue")

            # Render based on analyzer type
            if analyzer_name == "Performance":
                self._render_performance(result)
            elif analyzer_name == "Cost":
                self._render_cost(result)
            elif analyzer_name == "Bond":
                self._render_bond(result)
            elif analyzer_name == "Tax":
                self._render_tax(result)
            elif analyzer_name == "Risk":
                self._render_risk(result)
            else:
                self._render_generic(result)

        return ""

    def save(self, filepath: str) -> None:
        """Save report to file"""
        # Use Rich's export to HTML or text
        with open(filepath, "w") as f:
            # For now, just write a simple text version
            f.write("IB Analytics Report\n")
            f.write("=" * 80 + "\n\n")
            for result in self.results:
                f.write(f"{result.get('analyzer', 'Unknown')} Analysis\n")
                f.write("-" * 80 + "\n")
                for key, value in result.items():
                    if key not in ["analyzer", "timestamp"]:
                        f.write(f"{key}: {value}\n")
                f.write("\n")

    def _render_performance(self, result: AnalysisResult) -> None:
        """Render performance analysis"""
        # Overall metrics table
        table = Table(title="Overall Performance Metrics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Trades", str(result.get("total_trades", 0)))
        table.add_row("Total Positions", str(result.get("total_positions", 0)))
        table.add_row("Realized P&L", f"${result.get('total_realized_pnl', '0')}")
        table.add_row("Unrealized P&L", f"${result.get('total_unrealized_pnl', '0')}")
        table.add_row("Total P&L", f"${result.get('total_pnl', '0')}")
        table.add_row("", "")
        table.add_row("Win Rate", f"{result.get('win_rate', '0')}%")
        table.add_row("Winning Trades", str(result.get("winning_trades", 0)))
        table.add_row("Losing Trades", str(result.get("losing_trades", 0)))
        table.add_row("Profit Factor", result.get("profit_factor", "0"))
        table.add_row("", "")
        table.add_row("Average Win", f"${result.get('avg_win', '0')}")
        table.add_row("Average Loss", f"${result.get('avg_loss', '0')}")
        table.add_row("Risk/Reward Ratio", result.get("risk_reward_ratio", "0"))

        self.console.print(table)

        # By symbol breakdown
        by_symbol = result.get("by_symbol", {})
        if by_symbol:
            self.console.print("\n📈 Performance by Symbol\n", style="bold")
            for symbol, data in by_symbol.items():
                self.console.print(f"\n[bold]{symbol}[/bold]")
                self.console.print(f"  Trades: {data['trade_count']}")
                self.console.print(f"  Win Rate: {data['win_rate']}%")
                self.console.print(f"  Profit Factor: {data['profit_factor']}")
                self.console.print(f"  Realized P&L: ${data['realized_pnl']}")

    def _render_cost(self, result: AnalysisResult) -> None:
        """Render cost analysis"""
        table = Table(title="Cost Analysis", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Total Commissions", f"${result.get('total_commissions', '0')}")
        table.add_row("Total Volume", f"${result.get('total_volume', '0')}")
        table.add_row("Commission Rate", f"{result.get('commission_rate', '0')}%")
        table.add_row("Avg Commission/Trade", f"${result.get('avg_commission_per_trade', '0')}")
        table.add_row("", "")
        table.add_row("Commission Impact on P&L", f"{result.get('commission_impact_pct', '0')}%")

        self.console.print(table)

    def _render_bond(self, result: AnalysisResult) -> None:
        """Render bond analysis"""
        if not result.get("has_bonds"):
            self.console.print("No bond positions or trades found.", style="yellow")
            return

        # Current holdings
        holdings = result.get("current_holdings", [])
        if holdings:
            self.console.print("\n[bold]Current Bond Holdings[/bold]\n")
            for holding in holdings:
                panel = Panel(
                    f"Symbol: {holding['symbol']}\n"
                    f"Description: {holding.get('description', 'N/A')}\n"
                    f"Value: ${holding['position_value']}\n"
                    f"Unrealized P&L: ${holding['unrealized_pnl']} ({holding['unrealized_pnl_pct']}%)\n"
                    f"Maturity: {holding.get('maturity_date', 'N/A')}\n"
                    f"YTM: {holding['ytm']}%\n"
                    f"Duration: {holding['duration']} years",
                    title=holding["symbol"],
                    border_style="green",
                )
                self.console.print(panel)

    def _render_tax(self, result: AnalysisResult) -> None:
        """Render tax analysis"""
        table = Table(title=f"Tax Analysis (Rate: {result.get('tax_rate', '0')})", show_header=True)
        table.add_column("Item", style="cyan")
        table.add_column("Amount", style="red")

        table.add_row("Realized P&L", f"${result.get('total_realized_pnl', '0')}")
        table.add_row(
            "Estimated Capital Gains Tax", f"${result.get('estimated_capital_gains_tax', '0')}"
        )
        table.add_row("", "")
        table.add_row("Phantom Income (OID)", f"${result.get('phantom_income_total', '0')}")
        table.add_row(
            "Estimated Phantom Income Tax", f"${result.get('estimated_phantom_income_tax', '0')}"
        )
        table.add_row("", "")
        table.add_row(
            "[bold]Total Estimated Tax[/bold]",
            f"[bold]${result.get('total_estimated_tax', '0')}[/bold]",
        )

        self.console.print(table)
        self.console.print(f"\n⚠️  {result.get('disclaimer', '')}", style="yellow italic")

    def _render_risk(self, result: AnalysisResult) -> None:
        """Render risk analysis"""
        if result.get("has_bond_exposure"):
            self.console.print("\n[bold]Interest Rate Risk Scenarios[/bold]\n")
            scenarios = result.get("interest_rate_scenarios", {}).get("scenarios", [])

            for scenario in scenarios:
                self.console.print(f"\n{scenario['scenario']}: {scenario['total_value_change']}")

        # Concentration
        concentration = result.get("concentration", {})
        if concentration.get("top_positions"):
            self.console.print("\n[bold]Portfolio Concentration[/bold]\n")
            self.console.print(
                f"Max Concentration: {concentration.get('max_concentration', '0')}%\n"
            )

            table = Table(show_header=True)
            table.add_column("Symbol")
            table.add_column("Value", justify="right")
            table.add_column("Allocation", justify="right")

            for pos in concentration["top_positions"][:5]:
                table.add_row(
                    pos["symbol"],
                    f"${pos['value']}",
                    f"{pos['allocation_pct']}%",
                )

            self.console.print(table)

    def _render_generic(self, result: AnalysisResult) -> None:
        """Render generic result"""
        for key, value in result.items():
            if key not in ["analyzer", "timestamp", "is_multi_account"]:
                self.console.print(f"{key}: {value}")
