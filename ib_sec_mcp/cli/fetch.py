"""CLI for data fetching"""

from datetime import date, datetime
from pathlib import Path

import typer
from rich.console import Console

from ib_sec_mcp.api.client import FlexQueryClient
from ib_sec_mcp.utils.config import Config

app = typer.Typer(help="Fetch data from IB Flex Query API")
console = Console()


@app.command()
def fetch(
    start_date: str | None = typer.Option(
        None,
        "--start-date",
        "-s",
        help="Start date (YYYY-MM-DD). Defaults to beginning of current year",
    ),
    end_date: str | None = typer.Option(
        None,
        "--end-date",
        "-e",
        help="End date (YYYY-MM-DD). Defaults to today",
    ),
    split_accounts: bool = typer.Option(
        False,
        "--split-accounts",
        "-s",
        help="Split CSV into separate files by account (if multiple accounts in query)",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (defaults to data/raw)",
    ),
) -> None:
    """
    Fetch trading data from Interactive Brokers

    Examples:
        # Fetch YTD data
        ib-sec-fetch

        # Fetch data for specific date range
        ib-sec-fetch --start-date 2025-01-01 --end-date 2025-10-05

        # Split CSV by account (if query contains multiple accounts)
        ib-sec-fetch --split-accounts
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
        query_id=credentials.query_id,
        token=credentials.token,
        timeout=config.api_timeout,
        max_retries=config.api_max_retries,
        retry_delay=config.api_retry_delay,
    )

    try:
        # Fetch data
        statement = client.fetch_statement(from_date, to_date)

        if split_accounts:
            # Check if CSV contains multiple accounts
            from ib_sec_mcp.core.parsers import CSVParser

            accounts = CSVParser.to_accounts(statement.raw_data, from_date, to_date)

            if len(accounts) > 1:
                console.print(f"Found {len(accounts)} accounts in query result\n")

                # Save separate files for each account
                for account_id, _account in accounts.items():
                    filename = f"{account_id}_{from_date}_{to_date}.xml"
                    filepath = out_dir / filename

                    # Filter CSV data for this account only
                    # (For now, save the original CSV - can be enhanced later)
                    with open(filepath, "w") as f:
                        f.write(statement.raw_data)

                    console.print(f"✓ Saved account {account_id} to {filepath}", style="green")

                console.print(
                    f"\n✓ Successfully saved {len(accounts)} accounts", style="bold green"
                )
            else:
                # Only one account, save normally
                account_id = list(accounts.keys())[0]
                filename = f"{account_id}_{from_date}_{to_date}.xml"
                filepath = out_dir / filename

                with open(filepath, "w") as f:
                    f.write(statement.raw_data)

                console.print(f"✓ Saved to {filepath}", style="bold green")
        else:
            # Save single CSV file
            account_id = statement.account_id
            filename = f"{account_id}_{from_date}_{to_date}.xml"
            filepath = out_dir / filename

            with open(filepath, "w") as f:
                f.write(statement.raw_data)

            console.print(f"✓ Saved to {filepath}", style="bold green")

    except Exception as e:
        console.print(f"\n✗ Error: {e}", style="bold red")
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
