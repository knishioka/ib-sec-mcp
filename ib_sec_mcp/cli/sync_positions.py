"""CLI tool to sync XML position data to SQLite"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import defusedxml.ElementTree as ET

from ib_sec_mcp.core.parsers import XMLParser
from ib_sec_mcp.storage import PositionStore


class SyncError(Exception):
    """Raised when a sync operation fails"""


def _extract_snapshot_dates(xml_data: str) -> dict[str, date]:
    """
    Extract toDate per account from XML FlexStatement attributes.

    Args:
        xml_data: Raw XML string

    Returns:
        Dict mapping account_id to toDate from the FlexStatement
    """
    root = ET.fromstring(xml_data)
    dates: dict[str, date] = {}
    for stmt in root.findall(".//FlexStatement"):
        account_id = stmt.get("accountId", "")
        to_date_str = stmt.get("toDate", "")
        if account_id and to_date_str:
            dates[account_id] = datetime.strptime(to_date_str, "%Y%m%d").date()
    return dates


def sync_xml_file(xml_path: Path, db_path: Path, snapshot_date: date | None = None) -> int:
    """
    Sync single XML file to SQLite

    Args:
        xml_path: Path to XML file
        db_path: Path to SQLite database
        snapshot_date: Date for snapshot (defaults to file's toDate from XML)

    Returns:
        Number of positions saved

    Raises:
        SyncError: If file not found or parsing fails
    """
    if not xml_path.exists():
        raise SyncError(f"XML file not found: {xml_path}")

    print(f"Processing: {xml_path.name}")

    # Read XML file
    xml_data = xml_path.read_text()

    # Extract per-account snapshot dates from XML before parsing
    try:
        xml_dates = _extract_snapshot_dates(xml_data)
    except Exception:
        xml_dates = {}

    # Parse to Account models
    try:
        accounts = XMLParser.to_accounts(xml_data, date(2000, 1, 1), date.today())
    except Exception as e:
        raise SyncError(f"Error parsing {xml_path.name}: {e}") from e

    if not accounts:
        print("  No accounts found in file")
        return 0

    # Initialize store
    store = PositionStore(db_path)

    # Save each account
    total_positions = 0
    try:
        for account_id, account in accounts.items():
            # Priority: CLI --date > XML toDate > fallback to today
            snap_date = snapshot_date or xml_dates.get(account_id) or account.to_date

            positions_saved = store.save_snapshot(
                account=account, snapshot_date=snap_date, xml_file_path=str(xml_path)
            )

            print(f"  Account {account_id}: {positions_saved} positions saved for {snap_date}")
            total_positions += positions_saved
    finally:
        store.close()

    print(f"Total: {total_positions} positions saved")
    return total_positions


def sync_directory(
    directory: Path, db_path: Path, pattern: str = "*.xml", snapshot_date: date | None = None
) -> tuple[int, int, int]:
    """
    Sync all XML files in directory to SQLite

    Args:
        directory: Directory containing XML files
        db_path: Path to SQLite database
        pattern: Glob pattern for XML files (default: *.xml)
        snapshot_date: Date for snapshots (defaults to each file's to_date)

    Returns:
        Tuple of (files_succeeded, files_failed, total_positions)
    """
    if not directory.exists():
        print(f"Error: Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)

    xml_files = list(directory.glob(pattern))

    if not xml_files:
        print(f"No XML files found in {directory} matching {pattern}")
        return (0, 0, 0)

    print(f"Found {len(xml_files)} XML files")

    files_succeeded = 0
    files_failed = 0
    total_positions = 0
    errors: list[str] = []

    for xml_file in sorted(xml_files):
        try:
            positions = sync_xml_file(xml_file, db_path, snapshot_date)
            total_positions += positions
            files_succeeded += 1
        except SyncError as e:
            print(f"  SKIPPED: {e}", file=sys.stderr)
            files_failed += 1
            errors.append(str(e))
        print()

    # Print summary
    print("=" * 50)
    print(f"Summary: {files_succeeded}/{len(xml_files)} files synced successfully")
    print(f"Total positions saved: {total_positions}")
    if errors:
        print(f"\nFailed files ({files_failed}):")
        for error in errors:
            print(f"  - {error}")

    return (files_succeeded, files_failed, total_positions)


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
        try:
            sync_xml_file(args.xml_file, args.db_path, snapshot_date)
        except SyncError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        succeeded, failed, _ = sync_directory(
            args.directory, args.db_path, args.pattern, snapshot_date
        )
        if succeeded == 0 and failed > 0:
            sys.exit(1)

    print("\nSync complete!")


if __name__ == "__main__":
    main()
