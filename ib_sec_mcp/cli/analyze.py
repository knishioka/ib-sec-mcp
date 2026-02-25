"""CLI for running analysis"""

import typer
from rich.console import Console

from ib_sec_mcp.analyzers import (
    BondAnalyzer,
    CostAnalyzer,
    PerformanceAnalyzer,
    RiskAnalyzer,
    TaxAnalyzer,
)
from ib_sec_mcp.core.parsers import XMLParser, detect_format
from ib_sec_mcp.reports.console import ConsoleReport
from ib_sec_mcp.utils.config import Config

app = typer.Typer(help="Run portfolio analysis")
console = Console()


@app.command()
def analyze(
    data_file: str = typer.Argument(..., help="Path to XML data file"),
    analyzers: list[str] | None = typer.Option(
        None,
        "--analyzer",
        "-a",
        help="Specific analyzer to run (performance, cost, bond, tax, risk). Can specify multiple times.",
    ),
    all_analyzers: bool = typer.Option(
        False,
        "--all",
        help="Run all available analyzers",
    ),
    tax_rate: float = typer.Option(
        0.30,
        "--tax-rate",
        "-t",
        help="Tax rate for estimates (default: 0.30)",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Save report to file",
    ),
) -> None:
    """
    Analyze trading data

    Examples:
        # Run all analyzers
        ib-analyze data.xml --all

        # Run specific analyzer
        ib-analyze data.xml --analyzer performance

        # Run multiple analyzers
        ib-analyze data.xml -a performance -a cost -a bond
    """
    # Load config
    Config.load()

    # Read data file
    console.print(f"\n📂 Loading data from {data_file}...\n", style="bold blue")

    try:
        with open(data_file) as f:
            xml_data = f.read()
    except FileNotFoundError as e:
        console.print(f"✗ File not found: {data_file}", style="bold red")
        raise typer.Exit(code=1) from e

    # Parse data
    console.print("📊 Parsing XML data...\n", style="bold blue")

    # Extract dates from filename or use defaults
    from datetime import date

    from_date = date(2025, 1, 1)
    to_date = date.today()

    try:
        # Validate XML format
        detect_format(xml_data)  # Raises ValueError if not XML

        # Parse XML data
        accounts = XMLParser.to_accounts(xml_data, from_date, to_date)
        if not accounts:
            raise ValueError("No accounts found in XML file")

        account = next(iter(accounts.values()))  # Use first account
        console.print(f"✓ Loaded account {account.account_id}\n", style="green")
    except Exception as e:
        console.print(f"✗ Error parsing data: {e}", style="bold red")
        raise typer.Exit(code=1) from e

    # Determine which analyzers to run
    if all_analyzers:
        analyzer_names = ["performance", "cost", "bond", "tax", "risk"]
    elif analyzers:
        analyzer_names = analyzers
    else:
        # Default: run performance analyzer
        analyzer_names = ["performance"]

    console.print(f"🔍 Running analyzers: {', '.join(analyzer_names)}\n", style="bold blue")

    # Run analyzers
    results = []

    for analyzer_name in analyzer_names:
        console.print(f"Running {analyzer_name} analyzer...", style="cyan")

        try:
            analyzer: PerformanceAnalyzer | CostAnalyzer | BondAnalyzer | TaxAnalyzer | RiskAnalyzer
            if analyzer_name == "performance":
                analyzer = PerformanceAnalyzer(account=account)
            elif analyzer_name == "cost":
                analyzer = CostAnalyzer(account=account)
            elif analyzer_name == "bond":
                analyzer = BondAnalyzer(account=account)
            elif analyzer_name == "tax":
                from decimal import Decimal

                analyzer = TaxAnalyzer(account=account, tax_rate=Decimal(str(tax_rate)))
            elif analyzer_name == "risk":
                analyzer = RiskAnalyzer(account=account)
            else:
                console.print(f"  ✗ Unknown analyzer: {analyzer_name}", style="yellow")
                continue

            result = analyzer.analyze()
            results.append(result)
            console.print(f"  ✓ {analyzer_name} complete", style="green")

        except Exception as e:
            console.print(f"  ✗ Error: {e}", style="red")

    # Generate report
    console.print("\n" + "=" * 80 + "\n", style="bold")

    report = ConsoleReport(results)
    report.render()

    # Save if requested
    if output:
        report.save(output)
        console.print(f"\n💾 Report saved to {output}", style="bold green")


if __name__ == "__main__":
    app()
