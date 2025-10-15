"""CLI tool to sync XML position data to SQLite"""

import argparse
import sys
from datetime import date
from pathlib import Path

from ib_sec_mcp.core.parsers import XMLParser
from ib_sec_mcp.storage import PositionStore


def sync_xml_file(xml_path: Path, db_path: Path, snapshot_date: date | None = None) -> None:
    """
    Sync single XML file to SQLite

    Args:
        xml_path: Path to XML file
        db_path: Path to SQLite database
        snapshot_date: Date for snapshot (defaults to file's to_date)
    """
    if not xml_path.exists():
        print(f"Error: XML file not found: {xml_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing: {xml_path.name}")

    # Read XML file
    xml_data = xml_path.read_text()

    # Parse to Account models
    try:
        accounts = XMLParser.to_accounts(xml_data, date(2000, 1, 1), date.today())
    except Exception as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize store
    store = PositionStore(db_path)

    # Save each account
    total_positions = 0
    for account_id, account in accounts.items():
        # Use provided snapshot_date or file's to_date
        snap_date = snapshot_date or account.to_date

        positions_saved = store.save_snapshot(
            account=account, snapshot_date=snap_date, xml_file_path=str(xml_path)
        )

        print(f"  Account {account_id}: {positions_saved} positions saved for {snap_date}")
        total_positions += positions_saved

    store.close()
    print(f"Total: {total_positions} positions saved")


def sync_directory(
    directory: Path, db_path: Path, pattern: str = "*.xml", snapshot_date: date | None = None
) -> None:
    """
    Sync all XML files in directory to SQLite

    Args:
        directory: Directory containing XML files
        db_path: Path to SQLite database
        pattern: Glob pattern for XML files (default: *.xml)
        snapshot_date: Date for snapshots (defaults to each file's to_date)
    """
    if not directory.exists():
        print(f"Error: Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)

    xml_files = list(directory.glob(pattern))

    if not xml_files:
        print(f"No XML files found in {directory} matching {pattern}")
        return

    print(f"Found {len(xml_files)} XML files")

    for xml_file in sorted(xml_files):
        sync_xml_file(xml_file, db_path, snapshot_date)
        print()


def main() -> None:
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Sync XML position data to SQLite database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync single XML file
  python -m ib_sec_mcp.cli.sync_positions --xml-file data/raw/U1234567_2025-01-01_2025-10-15.xml

  # Sync all XML files in directory
  python -m ib_sec_mcp.cli.sync_positions --directory data/raw/

  # Specify custom database path
  python -m ib_sec_mcp.cli.sync_positions --xml-file data/raw/latest.xml --db-path data/custom.db

  # Override snapshot date
  python -m ib_sec_mcp.cli.sync_positions --xml-file data/raw/latest.xml --date 2025-10-15
        """,
    )

    parser.add_argument("--xml-file", type=Path, help="Path to single XML file to sync")
    parser.add_argument(
        "--directory",
        type=Path,
        help="Directory containing XML files to sync (syncs all *.xml files)",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.xml",
        help="Glob pattern for XML files when using --directory (default: *.xml)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/processed/positions.db"),
        help="Path to SQLite database (default: data/processed/positions.db)",
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Override snapshot date (format: YYYY-MM-DD). By default, uses file's to_date.",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.xml_file and not args.directory:
        parser.error("Must specify either --xml-file or --directory")

    if args.xml_file and args.directory:
        parser.error("Cannot specify both --xml-file and --directory")

    # Parse snapshot date if provided
    snapshot_date = None
    if args.date:
        try:
            snapshot_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"Error: Invalid date format: {args.date}. Use YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)

    # Ensure database directory exists
    args.db_path.parent.mkdir(parents=True, exist_ok=True)

    # Execute sync
    if args.xml_file:
        sync_xml_file(args.xml_file, args.db_path, snapshot_date)
    else:
        sync_directory(args.directory, args.db_path, args.pattern, snapshot_date)

    print("\nSync complete!")


if __name__ == "__main__":
    main()
