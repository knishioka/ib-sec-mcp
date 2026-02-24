"""Tests for sector allocation analyzer"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from ib_sec_mcp.analyzers.sector import (
    SectorAnalyzer,
    assess_concentration,
    calculate_hhi,
    fetch_sector_info,
)
from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass


@pytest.fixture
def sample_positions() -> list[Position]:
    """Multi-sector equity positions."""
    return [
        Position(
            account_id="U1234567",
            symbol="AAPL",
            description="Apple Inc",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("10"),
            mark_price=Decimal("150"),
            position_value=Decimal("1500"),
            average_cost=Decimal("120"),
            cost_basis=Decimal("1200"),
            unrealized_pnl=Decimal("300"),
            currency="USD",
            fx_rate_to_base=Decimal("1"),
            position_date=date(2025, 1, 31),
        ),
        Position(
            account_id="U1234567",
            symbol="JPM",
            description="JPMorgan Chase",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("20"),
            mark_price=Decimal("200"),
            position_value=Decimal("4000"),
            average_cost=Decimal("180"),
            cost_basis=Decimal("3600"),
            unrealized_pnl=Decimal("400"),
            currency="USD",
            fx_rate_to_base=Decimal("1"),
            position_date=date(2025, 1, 31),
        ),
        Position(
            account_id="U1234567",
            symbol="JNJ",
            description="Johnson & Johnson",
            asset_class=AssetClass.STOCK,
            quantity=Decimal("15"),
            mark_price=Decimal("160"),
            position_value=Decimal("2400"),
            average_cost=Decimal("140"),
            cost_basis=Decimal("2100"),
            unrealized_pnl=Decimal("300"),
            currency="USD",
            fx_rate_to_base=Decimal("1"),
            position_date=date(2025, 1, 31),
        ),
    ]


@pytest.fixture
def mixed_positions(sample_positions: list[Position]) -> list[Position]:
    """Positions with both equity and bond."""
    bond = Position(
        account_id="U1234567",
        symbol="US912810TD00",
        description="US Treasury Bond",
        asset_class=AssetClass.BOND,
        quantity=Decimal("10000"),
        mark_price=Decimal("98"),
        position_value=Decimal("9800"),
        average_cost=Decimal("100"),
        cost_basis=Decimal("10000"),
        unrealized_pnl=Decimal("-200"),
        currency="USD",
        fx_rate_to_base=Decimal("1"),
        position_date=date(2025, 1, 31),
    )
    return [*sample_positions, bond]


@pytest.fixture
def sample_account(sample_positions: list[Position]) -> Account:
    """Account with multi-sector positions."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        positions=sample_positions,
        cash_balances=[
            CashBalance(
                currency="BASE_SUMMARY",
                starting_cash=Decimal("10000"),
                ending_cash=Decimal("10000"),
                ending_settled_cash=Decimal("10000"),
            ),
        ],
    )


@pytest.fixture
def mixed_account(mixed_positions: list[Position]) -> Account:
    """Account with equity and bond positions."""
    return Account(
        account_id="U1234567",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 1, 31),
        positions=mixed_positions,
        cash_balances=[
            CashBalance(
                currency="BASE_SUMMARY",
                starting_cash=Decimal("10000"),
                ending_cash=Decimal("10000"),
                ending_settled_cash=Decimal("10000"),
            ),
        ],
    )


@pytest.fixture
def mock_sector_info():
    """Mock Yahoo Finance sector info."""
    return {
        "AAPL": {"sector": "Technology", "industry": "Consumer Electronics"},
        "JPM": {"sector": "Financial Services", "industry": "Banks—Diversified"},
        "JNJ": {"sector": "Healthcare", "industry": "Drug Manufacturers—General"},
    }


class TestCalculateHHI:
    """Tests for HHI calculation."""

    def test_single_sector(self):
        """100% in one sector = max concentration."""
        result = calculate_hhi({"Technology": Decimal("100")})
        assert result == Decimal("10000")

    def test_equal_split(self):
        """Equal split across sectors."""
        allocations = {
            "Technology": Decimal("25"),
            "Finance": Decimal("25"),
            "Healthcare": Decimal("25"),
            "Energy": Decimal("25"),
        }
        result = calculate_hhi(allocations)
        assert result == Decimal("2500")

    def test_empty(self):
        """No allocations."""
        result = calculate_hhi({})
        assert result == Decimal("0")


class TestAssessConcentration:
    """Tests for concentration assessment."""

    def test_low(self):
        assert assess_concentration(Decimal("1000")) == "LOW"

    def test_moderate(self):
        assert assess_concentration(Decimal("2000")) == "MODERATE"

    def test_high(self):
        assert assess_concentration(Decimal("3000")) == "HIGH"

    def test_boundary_low_moderate(self):
        assert assess_concentration(Decimal("1499")) == "LOW"
        assert assess_concentration(Decimal("1500")) == "MODERATE"

    def test_boundary_moderate_high(self):
        assert assess_concentration(Decimal("2499")) == "MODERATE"
        assert assess_concentration(Decimal("2500")) == "HIGH"


class TestFetchSectorInfo:
    """Tests for Yahoo Finance sector info fetching."""

    @pytest.mark.asyncio
    async def test_fetch_returns_sector_data(self):
        """Test that fetch returns sector and industry data."""
        with patch("ib_sec_mcp.analyzers.sector.asyncio.to_thread") as mock_thread:
            mock_thread.return_value = {
                "sector": "Technology",
                "industry": "Consumer Electronics",
            }
            result = await fetch_sector_info(["AAPL"])
            assert "AAPL" in result
            assert result["AAPL"]["sector"] == "Technology"

    @pytest.mark.asyncio
    async def test_fetch_handles_error(self):
        """Test that fetch handles Yahoo Finance errors gracefully."""
        with patch("ib_sec_mcp.analyzers.sector.asyncio.to_thread") as mock_thread:
            mock_thread.return_value = {"sector": "Unknown", "industry": "Unknown"}
            result = await fetch_sector_info(["INVALID"])
            assert result["INVALID"]["sector"] == "Unknown"

    @pytest.mark.asyncio
    async def test_fetch_empty_list(self):
        """Test with empty symbol list."""
        result = await fetch_sector_info([])
        assert result == {}


class TestSectorAnalyzer:
    """Tests for SectorAnalyzer."""

    @pytest.mark.asyncio
    async def test_equity_positions_with_sectors(self, sample_account, mock_sector_info):
        """Test sector allocation for equity positions."""
        with patch(
            "ib_sec_mcp.analyzers.sector.fetch_sector_info",
            new_callable=AsyncMock,
            return_value=mock_sector_info,
        ):
            analyzer = SectorAnalyzer(account=sample_account)
            result = await analyzer.analyze_async()

        assert result["analyzer"] == "Sector"
        assert "sectors" in result
        sectors = result["sectors"]
        assert "Technology" in sectors
        assert "Financial Services" in sectors
        assert "Healthcare" in sectors

        # Check values
        assert sectors["Technology"]["value"] == "1500"
        assert sectors["Financial Services"]["value"] == "4000"

        # Cash is included as a sector category
        assert "Cash & Equivalents" in sectors

        # Check percentages add up to ~100
        total_pct = sum(Decimal(s["percentage"]) for s in sectors.values())
        assert abs(total_pct - Decimal("100")) < Decimal("1")

    @pytest.mark.asyncio
    async def test_mixed_positions(self, mixed_account, mock_sector_info):
        """Test with both equity and bond positions."""
        with patch(
            "ib_sec_mcp.analyzers.sector.fetch_sector_info",
            new_callable=AsyncMock,
            return_value=mock_sector_info,
        ):
            analyzer = SectorAnalyzer(account=mixed_account)
            result = await analyzer.analyze_async()

        sectors = result["sectors"]
        assert "Fixed Income" in sectors
        assert sectors["Fixed Income"]["value"] == "9800"
        assert result["equity_count"] == 3
        assert result["non_equity_count"] == 1

    @pytest.mark.asyncio
    async def test_empty_account(self):
        """Test with no positions."""
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            positions=[],
            cash_balances=[],
        )
        analyzer = SectorAnalyzer(account=account)
        result = await analyzer.analyze_async()

        assert result["sectors"] == {}
        assert result["position_count"] == 0
        assert result["concentration_risk"]["assessment"] == "LOW"

    @pytest.mark.asyncio
    async def test_concentration_risk_calculated(self, sample_account, mock_sector_info):
        """Test that HHI and assessment are included."""
        with patch(
            "ib_sec_mcp.analyzers.sector.fetch_sector_info",
            new_callable=AsyncMock,
            return_value=mock_sector_info,
        ):
            analyzer = SectorAnalyzer(account=sample_account)
            result = await analyzer.analyze_async()

        risk = result["concentration_risk"]
        assert "hhi" in risk
        assert "assessment" in risk
        assert risk["assessment"] in ("LOW", "MODERATE", "HIGH")

    @pytest.mark.asyncio
    async def test_highly_concentrated_portfolio(self):
        """Test HHI assessment for highly concentrated portfolio."""
        positions = [
            Position(
                account_id="U1234567",
                symbol="AAPL",
                description="Apple Inc",
                asset_class=AssetClass.STOCK,
                quantity=Decimal("100"),
                mark_price=Decimal("150"),
                position_value=Decimal("15000"),
                average_cost=Decimal("120"),
                cost_basis=Decimal("12000"),
                unrealized_pnl=Decimal("3000"),
                currency="USD",
                fx_rate_to_base=Decimal("1"),
                position_date=date(2025, 1, 31),
            ),
        ]
        account = Account(
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            positions=positions,
            cash_balances=[],
        )
        with patch(
            "ib_sec_mcp.analyzers.sector.fetch_sector_info",
            new_callable=AsyncMock,
            return_value={"AAPL": {"sector": "Technology", "industry": "Consumer Electronics"}},
        ):
            analyzer = SectorAnalyzer(account=account)
            result = await analyzer.analyze_async()

        assert result["concentration_risk"]["assessment"] == "HIGH"
        assert Decimal(result["concentration_risk"]["hhi"]) == Decimal("10000")
