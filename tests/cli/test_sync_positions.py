"""Tests for sync_positions CLI"""

from datetime import date
from pathlib import Path

import defusedxml.ElementTree as ET
import pytest

from ib_sec_mcp.cli.sync_positions import (
    SyncError,
    _extract_snapshot_dates,
    sync_directory,
    sync_xml_file,
)
from ib_sec_mcp.storage.position_store import PositionStore

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="1">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20250131">
      <AccountInformation accountId="U1234567" acctAlias="Test Account" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="10000" endingCash="10000" endingSettledCash="10000"
          deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
          commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="AAPL" description="APPLE INC"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US0378331005" position="10" markPrice="150.00"
          positionValue="1500" costBasisMoney="1400" fifoPnlUnrealized="100"
          reportDate="20250131" multiplier="1" />
        <OpenPosition symbol="MSFT" description="MICROSOFT CORP"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US5949181045" position="5" markPrice="300.00"
          positionValue="1500" costBasisMoney="1200" fifoPnlUnrealized="300"
          reportDate="20250131" multiplier="1" />
      </OpenPositions>
      <Trades />
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

SAMPLE_XML_MULTI_ACCOUNT = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="2">
    <FlexStatement accountId="U1111111" fromDate="20250201" toDate="20250228">
      <AccountInformation accountId="U1111111" acctAlias="Account 1" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="5000" endingCash="5000" endingSettledCash="5000"
          deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
          commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="GOOG" description="ALPHABET INC"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US02079K3059" position="3" markPrice="200.00"
          positionValue="600" costBasisMoney="500" fifoPnlUnrealized="100"
          reportDate="20250228" multiplier="1" />
      </OpenPositions>
      <Trades />
    </FlexStatement>
    <FlexStatement accountId="U7654321" fromDate="20250201" toDate="20250228">
      <AccountInformation accountId="U7654321" acctAlias="Account 2" />
      <CashReport>
        <CashReportCurrency currency="BASE_SUMMARY"
          startingCash="3000" endingCash="3000" endingSettledCash="3000"
          deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
          commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" />
      </CashReport>
      <OpenPositions>
        <OpenPosition symbol="TSLA" description="TESLA INC"
          assetCategory="STK" currency="USD" fxRateToBase="1"
          isin="US88160R1014" position="2" markPrice="250.00"
          positionValue="500" costBasisMoney="400" fifoPnlUnrealized="100"
          reportDate="20250228" multiplier="1" />
      </OpenPositions>
      <Trades />
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""

CSV_NOT_XML = "ClientAccountID,AssetClass,Symbol\nU1234567,STK,AAPL\n"


# ---------------------------------------------------------------------------
# _extract_snapshot_dates
# ---------------------------------------------------------------------------


class TestExtractSnapshotDates:
    def test_extracts_single_account_date(self) -> None:
        dates = _extract_snapshot_dates(SAMPLE_XML)
        assert dates == {"U1234567": date(2025, 1, 31)}

    def test_extracts_multi_account_dates(self) -> None:
        dates = _extract_snapshot_dates(SAMPLE_XML_MULTI_ACCOUNT)
        assert dates == {
            "U1111111": date(2025, 2, 28),
            "U7654321": date(2025, 2, 28),
        }

    def test_skips_malformed_todate_per_statement(self) -> None:
        """A single malformed toDate should not discard valid dates from other statements."""
        xml_with_bad_date = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
  <FlexStatements count="2">
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="BADDATE">
      <AccountInformation accountId="U1234567" acctAlias="Bad Date Account" />
      <CashReport><CashReportCurrency currency="BASE_SUMMARY"
        startingCash="0" endingCash="0" endingSettledCash="0"
        deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
        commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" /></CashReport>
      <OpenPositions /><Trades />
    </FlexStatement>
    <FlexStatement accountId="U7654321" fromDate="20250201" toDate="20250228">
      <AccountInformation accountId="U7654321" acctAlias="Good Date Account" />
      <CashReport><CashReportCurrency currency="BASE_SUMMARY"
        startingCash="0" endingCash="0" endingSettledCash="0"
        deposits="0" withdrawals="0" dividends="0" brokerInterest="0"
        commissions="0" otherFees="0" netTradesSales="0" netTradesPurchases="0" /></CashReport>
      <OpenPositions /><Trades />
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>"""
        dates = _extract_snapshot_dates(xml_with_bad_date)
        # Bad toDate for U1234567 should be skipped, U7654321 should still be extracted
        assert "U1234567" not in dates
        assert dates == {"U7654321": date(2025, 2, 28)}

    def test_raises_on_invalid_xml(self) -> None:
        with pytest.raises(ET.ParseError):
            _extract_snapshot_dates(CSV_NOT_XML)


# ---------------------------------------------------------------------------
# sync_xml_file
# ---------------------------------------------------------------------------


class TestSyncXmlFile:
    def test_sync_single_file(self, tmp_path: Path) -> None:
        xml_file = tmp_path / "test.xml"
        xml_file.write_text(SAMPLE_XML)
        db_path = tmp_path / "test.db"

        saved = sync_xml_file(xml_file, db_path)
        assert saved == 2

        # Verify data in DB
        store = PositionStore(db_path)
        dates = store.get_available_dates("U1234567")
        assert "2025-01-31" in dates
        store.close()

    def test_sync_uses_xml_todate_as_snapshot(self, tmp_path: Path) -> None:
        xml_file = tmp_path / "test.xml"
        xml_file.write_text(SAMPLE_XML)
        db_path = tmp_path / "test.db"

        sync_xml_file(xml_file, db_path)

        store = PositionStore(db_path)
        dates = store.get_available_dates("U1234567")
        # Should use toDate from XML (20250131), not today
        assert dates == ["2025-01-31"]
        store.close()

    def test_sync_with_override_date(self, tmp_path: Path) -> None:
        xml_file = tmp_path / "test.xml"
        xml_file.write_text(SAMPLE_XML)
        db_path = tmp_path / "test.db"

        override_date = date(2025, 6, 15)
        sync_xml_file(xml_file, db_path, snapshot_date=override_date)

        store = PositionStore(db_path)
        dates = store.get_available_dates("U1234567")
        assert dates == ["2025-06-15"]
        store.close()

    def test_sync_multi_account(self, tmp_path: Path) -> None:
        xml_file = tmp_path / "multi.xml"
        xml_file.write_text(SAMPLE_XML_MULTI_ACCOUNT)
        db_path = tmp_path / "test.db"

        saved = sync_xml_file(xml_file, db_path)
        assert saved == 2  # 1 per account

        store = PositionStore(db_path)
        assert store.get_available_dates("U1111111") == ["2025-02-28"]
        assert store.get_available_dates("U7654321") == ["2025-02-28"]
        store.close()

    def test_sync_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SyncError, match="XML file not found"):
            sync_xml_file(tmp_path / "missing.xml", tmp_path / "test.db")

    def test_sync_invalid_xml_raises(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "bad.xml"
        csv_file.write_text(CSV_NOT_XML)
        db_path = tmp_path / "test.db"

        with pytest.raises(SyncError, match="Error parsing"):
            sync_xml_file(csv_file, db_path)

    def test_sync_idempotent(self, tmp_path: Path) -> None:
        xml_file = tmp_path / "test.xml"
        xml_file.write_text(SAMPLE_XML)
        db_path = tmp_path / "test.db"

        saved1 = sync_xml_file(xml_file, db_path)
        saved2 = sync_xml_file(xml_file, db_path)
        assert saved1 == saved2

        # Verify no duplicates
        store = PositionStore(db_path)
        snapshot = store.get_portfolio_snapshot("U1234567", date(2025, 1, 31))
        assert len(snapshot) == 2  # Still only 2 positions
        store.close()


# ---------------------------------------------------------------------------
# sync_directory
# ---------------------------------------------------------------------------


class TestSyncDirectory:
    def test_sync_directory_multiple_files(self, tmp_path: Path) -> None:
        (tmp_path / "file1.xml").write_text(SAMPLE_XML)
        (tmp_path / "file2.xml").write_text(SAMPLE_XML_MULTI_ACCOUNT)
        db_path = tmp_path / "test.db"

        succeeded, failed, total = sync_directory(tmp_path, db_path)
        assert succeeded == 2
        assert failed == 0
        assert total == 4  # 2 from file1 + 2 from file2

    def test_sync_directory_skips_bad_files(self, tmp_path: Path) -> None:
        (tmp_path / "good.xml").write_text(SAMPLE_XML)
        (tmp_path / "bad.xml").write_text(CSV_NOT_XML)
        db_path = tmp_path / "test.db"

        succeeded, failed, total = sync_directory(tmp_path, db_path)
        assert succeeded == 1
        assert failed == 1
        assert total == 2

    def test_sync_directory_no_files(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        succeeded, failed, total = sync_directory(tmp_path, db_path)
        assert succeeded == 0
        assert failed == 0
        assert total == 0

    def test_sync_directory_custom_pattern(self, tmp_path: Path) -> None:
        (tmp_path / "data.xml").write_text(SAMPLE_XML)
        (tmp_path / "data.txt").write_text("not xml")
        db_path = tmp_path / "test.db"

        succeeded, _, _ = sync_directory(tmp_path, db_path, pattern="*.xml")
        assert succeeded == 1

    def test_sync_directory_nonexistent_exits(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            sync_directory(tmp_path / "nonexistent", tmp_path / "test.db")
