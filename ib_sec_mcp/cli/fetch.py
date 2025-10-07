"""CLI for data fetching"""

import asyncio
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ib_sec_mcp.api.client import FlexQueryClient
from ib_sec_mcp.utils.config import Config

app = typer.Typer(help="Fetch data from IB Flex Query API")
console = Console()


@app.command()
def fetch(
    start_date: Optional[str] = typer.Option(
        None,
        "--start-date",
        "-s",
        help="Start date (YYYY-MM-DD). Defaults to beginning of current year",
    ),
    end_date: Optional[str] = typer.Option(
        None,
        "--end-date",
        "-e",
        help="End date (YYYY-MM-DD). Defaults to today",
    ),
    multi_account: bool = typer.Option(
        False,
        "--multi-account",
        "-m",
        help="Fetch data for all configured accounts",
    ),
    output_dir: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (defaults to data/raw)",
    ),
):
    """
    Fetch trading data from Interactive Brokers

    Examples:
        # Fetch YTD data for default account
        ib-fetch

        # Fetch data for specific date range
        ib-fetch --start-date 2025-01-01 --end-date 2025-10-05

        # Fetch data for all accounts
        ib-fetch --multi-account
    """
    # Load config
    config = Config.load()

    # Parse dates
    if start_date:
        from_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        from_date = date(date.today().year, 1, 1)

    to_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()

    # Set output directory
    out_dir = Path(output_dir) if output_dir else config.raw_data_dir

    out_dir.mkdir(parents=True, exist_ok=True)

    # Get credentials
    credentials = config.get_credentials()

    console.print(f"\n📊 Fetching data from {from_date} to {to_date}\n", style="bold blue")

    # Create client
    client = FlexQueryClient(
        credentials=credentials,
        timeout=config.api_timeout,
        max_retries=config.api_max_retries,
        retry_delay=config.api_retry_delay,
    )

    if multi_account or len(credentials) > 1:
        # Fetch all accounts
        console.print(f"Fetching data for {len(credentials)} accounts...\n")

        try:
            statements = asyncio.run(client.fetch_all_statements_async(from_date, to_date))

            for _i, statement in enumerate(statements):
                account_id = statement.account_id
                filename = f"{account_id}_{from_date}_{to_date}.csv"
                filepath = out_dir / filename

                with open(filepath, "w") as f:
                    f.write(statement.raw_data)

                console.print(f"✓ Saved account {account_id} to {filepath}", style="green")

            console.print(
                f"\n✓ Successfully fetched data for {len(statements)} accounts", style="bold green"
            )

        except Exception as e:
            console.print(f"\n✗ Error: {e}", style="bold red")
            raise typer.Exit(code=1) from e

    else:
        # Fetch single account
        console.print("Fetching data for single account...\n")

        try:
            statement = client.fetch_statement(from_date, to_date)

            account_id = statement.account_id
            filename = f"{account_id}_{from_date}_{to_date}.csv"
            filepath = out_dir / filename

            with open(filepath, "w") as f:
                f.write(statement.raw_data)

            console.print(f"✓ Saved to {filepath}", style="bold green")

        except Exception as e:
            console.print(f"\n✗ Error: {e}", style="bold red")
            raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
