#!/usr/bin/env python3
"""
Example usage of ib_analytics library

Demonstrates programmatic API usage
"""

from datetime import date
from decimal import Decimal

from ib_sec_mcp import FlexQueryClient
from ib_sec_mcp.analyzers import (
    BondAnalyzer,
    CostAnalyzer,
    PerformanceAnalyzer,
    RiskAnalyzer,
    TaxAnalyzer,
)
from ib_sec_mcp.core.parsers import CSVParser
from ib_sec_mcp.reports.console import ConsoleReport
from ib_sec_mcp.utils.config import Config


def main():
    """Run example analysis"""
    print("IB Analytics - Example Usage\n")
    print("=" * 80)

    # 1. Load configuration
    print("\n1. Loading configuration from .env file...")
    config = Config.load()
    credentials = config.get_credentials()
    print(f"   Found {len(credentials)} account(s)")

    # 2. Fetch data (optional - you can also load from existing CSV)
    print("\n2. Fetching data from IB API...")
    client = FlexQueryClient(credentials=credentials)

    # Fetch YTD data
    from_date = date(2025, 1, 1)
    to_date = date(2025, 10, 5)

    try:
        statement = client.fetch_statement(from_date, to_date)
        print(f"   ✓ Fetched data for account {statement.account_id}")

        # Save to file
        filename = f"data/raw/{statement.account_id}_{from_date}_{to_date}.csv"
        with open(filename, "w") as f:
            f.write(statement.raw_data)
        print(f"   ✓ Saved to {filename}")

        csv_data = statement.raw_data

    except Exception as e:
        print(f"   ✗ Error fetching data: {e}")
        print("   Loading from existing file instead...")

        # Load from existing file (replace with your actual file)
        filename = "data/raw/UXXXXXXXX_2025-01-01_2025-10-05.csv"
        with open(filename) as f:
            csv_data = f.read()

    # 3. Parse data
    print("\n3. Parsing CSV data...")
    account = CSVParser.to_account(csv_data, from_date, to_date)
    print(f"   ✓ Parsed account {account.account_id}")
    print(f"   - Trades: {len(account.trades)}")
    print(f"   - Positions: {len(account.positions)}")
    print(f"   - Cash: ${account.total_cash}")

    # 4. Run analyzers
    print("\n4. Running analysis...")

    analyzers = [
        PerformanceAnalyzer(account=account),
        CostAnalyzer(account=account),
        BondAnalyzer(account=account),
        TaxAnalyzer(account=account, tax_rate=Decimal("0.30")),
        RiskAnalyzer(account=account),
    ]

    results = []
    for analyzer in analyzers:
        print(f"   Running {analyzer.analyzer_name} analyzer...")
        result = analyzer.analyze()
        results.append(result)
        print(f"   ✓ {analyzer.analyzer_name} complete")

    # 5. Generate report
    print("\n5. Generating report...\n")
    print("=" * 80)

    report = ConsoleReport(results)
    report.render()

    # Save report
    report.save("data/processed/analysis_report.txt")
    print("\n" + "=" * 80)
    print("\n✓ Report saved to data/processed/analysis_report.txt")


if __name__ == "__main__":
    main()
