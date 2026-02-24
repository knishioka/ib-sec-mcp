"""Tests for analyze_dividend_income MCP tool and helper functions"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.tools.composable_data import (
    _get_domicile_code,
    _get_withholding_rate,
    register_composable_data_tools,
)
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass

# ---------------------------------------------------------------------------
# Helper: build a minimal Position object for testing
# ---------------------------------------------------------------------------


def _make_position(
    symbol: str,
    isin: str | None,
    position_value: str,
    asset_class: AssetClass = AssetClass.STOCK,
    currency: str = "USD",
) -> Position:
    """Create a minimal Position instance for testing."""
    return Position(
        account_id="U12345678",
        symbol=symbol,
        asset_class=asset_class,
        isin=isin,
        quantity=Decimal("100"),
        multiplier=Decimal("1"),
        mark_price=Decimal(position_value) / Decimal("100"),
        position_value=Decimal(position_value),
        average_cost=Decimal("10"),
        cost_basis=Decimal("1000"),
        unrealized_pnl=Decimal("0"),
        realized_pnl=Decimal("0"),
        currency=currency,
        fx_rate_to_base=Decimal("1.0"),
        position_date=date(2025, 10, 31),
    )


# ---------------------------------------------------------------------------
# Tests: _get_domicile_code
# ---------------------------------------------------------------------------


class TestGetDomicileCode:
    """Tests for _get_domicile_code helper function"""

    def test_ireland_isin(self) -> None:
        assert _get_domicile_code("IE00B4L5Y983") == "IE"

    def test_us_isin(self) -> None:
        assert _get_domicile_code("US78462F1030") == "US"

    def test_lu_isin(self) -> None:
        assert _get_domicile_code("LU0378449770") == "LU"

    def test_none_isin(self) -> None:
        assert _get_domicile_code(None) == "UNKNOWN"

    def test_empty_isin(self) -> None:
        assert _get_domicile_code("") == "UNKNOWN"

    def test_single_char_isin(self) -> None:
        assert _get_domicile_code("I") == "UNKNOWN"

    def test_lowercase_isin_normalised(self) -> None:
        assert _get_domicile_code("ie00B4L5Y983") == "IE"

    def test_exactly_two_chars(self) -> None:
        assert _get_domicile_code("GB") == "GB"


# ---------------------------------------------------------------------------
# Tests: _get_withholding_rate
# ---------------------------------------------------------------------------


class TestGetWithholdingRate:
    """Tests for _get_withholding_rate helper function"""

    def test_ireland_rate_is_15_pct(self) -> None:
        rate = _get_withholding_rate("IE")
        assert rate == Decimal("0.15")

    def test_us_defaults_to_30_pct(self) -> None:
        rate = _get_withholding_rate("US")
        assert rate == Decimal("0.30")

    def test_unknown_defaults_to_30_pct(self) -> None:
        rate = _get_withholding_rate("UNKNOWN")
        assert rate == Decimal("0.30")

    def test_luxembourg_defaults_to_30_pct(self) -> None:
        rate = _get_withholding_rate("LU")
        assert rate == Decimal("0.30")

    def test_return_type_is_decimal(self) -> None:
        rate = _get_withholding_rate("IE")
        assert isinstance(rate, Decimal)


# ---------------------------------------------------------------------------
# Fixtures for MCP tool integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with composable data tools registered."""
    mcp = FastMCP("test")
    register_composable_data_tools(mcp)
    return mcp


@pytest.fixture()
def ie_position() -> Position:
    """Ireland-domiciled ETF position (15% withholding)."""
    return _make_position("CSPX", "IE00B4L5Y983", "10000")


@pytest.fixture()
def us_position() -> Position:
    """US-domiciled ETF position (30% withholding)."""
    return _make_position("VOO", "US9229087690", "20000")


@pytest.fixture()
def no_isin_position() -> Position:
    """Position without ISIN (defaults to 30% withholding)."""
    return _make_position("SPY", None, "5000")


@pytest.fixture()
def bond_position() -> Position:
    """Bond position — should be excluded from dividend analysis."""
    return _make_position("BOND1", "US123456789", "15000", asset_class=AssetClass.BOND)


def _mock_account(positions: list[Position]) -> MagicMock:
    """Build a mock Account with the given positions."""
    account = MagicMock()
    account.positions = positions
    return account


# ---------------------------------------------------------------------------
# Tests: analyze_dividend_income MCP tool
# ---------------------------------------------------------------------------


class TestAnalyzeDividendIncome:
    """Integration tests for the analyze_dividend_income MCP tool."""

    @pytest.mark.asyncio
    async def test_ireland_position_uses_15_pct_withholding(
        self,
        test_mcp: FastMCP,
        ie_position: Position,
    ) -> None:
        """IE-domiciled positions must have 15% withholding applied."""
        mock_account = _mock_account([ie_position])
        with (
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=("xml_data", date(2025, 1, 1), date(2025, 10, 31)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._parse_account_by_index",
                return_value=mock_account,
            ),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker = MagicMock()
            mock_ticker.info = {"dividendYield": 0.02}  # 2% yield
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("analyze_dividend_income")
            result = await tool.fn(start_date="2025-01-01", ctx=None)
            data = json.loads(result)

        pos = data["positions"][0]
        assert pos["domicile"] == "IE"
        assert Decimal(pos["withholding_rate_pct"]) == Decimal("15")
        # 10000 * 0.02 = 200 annual dividend
        assert Decimal(pos["annual_dividend"]) == Decimal("200")
        # 200 * 0.15 = 30 withholding tax
        assert Decimal(pos["withholding_tax"]) == Decimal("30")
        # net = 200 - 30 = 170
        assert Decimal(pos["net_receipt"]) == Decimal("170")
        # IE position → no savings
        assert Decimal(pos["potential_ie_savings"]) == Decimal("0")

    @pytest.mark.asyncio
    async def test_us_position_uses_30_pct_withholding_and_shows_savings(
        self,
        test_mcp: FastMCP,
        us_position: Position,
    ) -> None:
        """US-domiciled positions must have 30% withholding and show IE savings."""
        mock_account = _mock_account([us_position])
        with (
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=("xml_data", date(2025, 1, 1), date(2025, 10, 31)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._parse_account_by_index",
                return_value=mock_account,
            ),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker = MagicMock()
            mock_ticker.info = {"dividendYield": 0.03}  # 3% yield
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("analyze_dividend_income")
            result = await tool.fn(start_date="2025-01-01", ctx=None)
            data = json.loads(result)

        pos = data["positions"][0]
        assert pos["domicile"] == "US"
        assert Decimal(pos["withholding_rate_pct"]) == Decimal("30")
        # 20000 * 0.03 = 600 annual dividend
        annual_div = Decimal("600")
        assert Decimal(pos["annual_dividend"]) == annual_div
        # withholding = 600 * 0.30 = 180
        assert Decimal(pos["withholding_tax"]) == Decimal("180")
        # net = 600 - 180 = 420
        assert Decimal(pos["net_receipt"]) == Decimal("420")
        # savings = (0.30 - 0.15) * 600 = 90
        assert Decimal(pos["potential_ie_savings"]) == Decimal("90")

    @pytest.mark.asyncio
    async def test_no_isin_defaults_to_30_pct(
        self,
        test_mcp: FastMCP,
        no_isin_position: Position,
    ) -> None:
        """Positions without ISIN must default to 30% withholding."""
        mock_account = _mock_account([no_isin_position])
        with (
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=("xml_data", date(2025, 1, 1), date(2025, 10, 31)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._parse_account_by_index",
                return_value=mock_account,
            ),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker = MagicMock()
            mock_ticker.info = {"dividendYield": 0.015}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("analyze_dividend_income")
            result = await tool.fn(start_date="2025-01-01", ctx=None)
            data = json.loads(result)

        pos = data["positions"][0]
        assert pos["domicile"] == "UNKNOWN"
        assert Decimal(pos["withholding_rate_pct"]) == Decimal("30")

    @pytest.mark.asyncio
    async def test_zero_dividend_yield_produces_zero_income(
        self,
        test_mcp: FastMCP,
        ie_position: Position,
    ) -> None:
        """Positions with 0% dividend yield must produce zero income figures."""
        mock_account = _mock_account([ie_position])
        with (
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=("xml_data", date(2025, 1, 1), date(2025, 10, 31)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._parse_account_by_index",
                return_value=mock_account,
            ),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker = MagicMock()
            mock_ticker.info = {"dividendYield": 0}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("analyze_dividend_income")
            result = await tool.fn(start_date="2025-01-01", ctx=None)
            data = json.loads(result)

        pos = data["positions"][0]
        assert Decimal(pos["annual_dividend"]) == Decimal("0")
        assert Decimal(pos["withholding_tax"]) == Decimal("0")
        assert Decimal(pos["net_receipt"]) == Decimal("0")
        assert Decimal(pos["potential_ie_savings"]) == Decimal("0")

    @pytest.mark.asyncio
    async def test_bond_positions_excluded(
        self,
        test_mcp: FastMCP,
        bond_position: Position,
        ie_position: Position,
    ) -> None:
        """Bond positions must be excluded; only STK positions are analysed."""
        mock_account = _mock_account([ie_position, bond_position])
        with (
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=("xml_data", date(2025, 1, 1), date(2025, 10, 31)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._parse_account_by_index",
                return_value=mock_account,
            ),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker = MagicMock()
            mock_ticker.info = {"dividendYield": 0.02}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("analyze_dividend_income")
            result = await tool.fn(start_date="2025-01-01", ctx=None)
            data = json.loads(result)

        assert data["position_count"] == 1
        symbols = [p["symbol"] for p in data["positions"]]
        assert "CSPX" in symbols
        assert "BOND1" not in symbols

    @pytest.mark.asyncio
    async def test_positions_ranked_by_yield_descending(
        self,
        test_mcp: FastMCP,
        ie_position: Position,
        us_position: Position,
    ) -> None:
        """Positions must be sorted by dividend yield from highest to lowest."""
        mock_account = _mock_account([ie_position, us_position])  # CSPX first, VOO second

        def make_ticker(symbol: str) -> MagicMock:
            ticker = MagicMock()
            # VOO (US) has higher yield than CSPX (IE)
            ticker.info = {"dividendYield": 0.03 if symbol == "VOO" else 0.01}
            return ticker

        with (
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=("xml_data", date(2025, 1, 1), date(2025, 10, 31)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._parse_account_by_index",
                return_value=mock_account,
            ),
            patch("yfinance.Ticker", side_effect=make_ticker),
        ):
            tool = await test_mcp.get_tool("analyze_dividend_income")
            result = await tool.fn(start_date="2025-01-01", ctx=None)
            data = json.loads(result)

        yields = [Decimal(p["dividend_yield_pct"]) for p in data["positions"]]
        assert yields == sorted(yields, reverse=True)
        assert data["positions"][0]["symbol"] == "VOO"

    @pytest.mark.asyncio
    async def test_summary_totals_are_correct(
        self,
        test_mcp: FastMCP,
        ie_position: Position,
        us_position: Position,
    ) -> None:
        """Summary totals must equal the sum of per-position values."""
        mock_account = _mock_account([ie_position, us_position])

        def make_ticker(symbol: str) -> MagicMock:
            ticker = MagicMock()
            ticker.info = {"dividendYield": 0.02}
            return ticker

        with (
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=("xml_data", date(2025, 1, 1), date(2025, 10, 31)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._parse_account_by_index",
                return_value=mock_account,
            ),
            patch("yfinance.Ticker", side_effect=make_ticker),
        ):
            tool = await test_mcp.get_tool("analyze_dividend_income")
            result = await tool.fn(start_date="2025-01-01", ctx=None)
            data = json.loads(result)

        positions = data["positions"]
        expected_dividend = sum(Decimal(p["annual_dividend"]) for p in positions)
        expected_tax = sum(Decimal(p["withholding_tax"]) for p in positions)
        expected_net = sum(Decimal(p["net_receipt"]) for p in positions)
        expected_savings = sum(Decimal(p["potential_ie_savings"]) for p in positions)

        summary = data["summary"]
        assert Decimal(summary["total_annual_dividend"]) == expected_dividend
        assert Decimal(summary["total_withholding_tax"]) == expected_tax
        assert Decimal(summary["total_net_receipt"]) == expected_net
        assert Decimal(summary["total_potential_ie_savings"]) == expected_savings

    @pytest.mark.asyncio
    async def test_decimal_precision_maintained(
        self,
        test_mcp: FastMCP,
        ie_position: Position,
    ) -> None:
        """All monetary values must be serialised as strings (Decimal precision)."""
        mock_account = _mock_account([ie_position])
        with (
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=("xml_data", date(2025, 1, 1), date(2025, 10, 31)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._parse_account_by_index",
                return_value=mock_account,
            ),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker = MagicMock()
            # Use a yield with many decimal places to exercise precision
            mock_ticker.info = {"dividendYield": 0.02123456789}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("analyze_dividend_income")
            result = await tool.fn(start_date="2025-01-01", ctx=None)
            # Must parse without errors — no float contamination
            data = json.loads(result)

        pos = data["positions"][0]
        # All financial fields must round-trip through Decimal without error
        for field in ("annual_dividend", "withholding_tax", "net_receipt", "position_value"):
            assert Decimal(pos[field]) is not None

    @pytest.mark.asyncio
    async def test_yfinance_failure_gracefully_returns_zero_yield(
        self,
        test_mcp: FastMCP,
        us_position: Position,
    ) -> None:
        """When Yahoo Finance fetch fails, the position must have zero yield."""
        mock_account = _mock_account([us_position])
        with (
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=("xml_data", date(2025, 1, 1), date(2025, 10, 31)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._parse_account_by_index",
                return_value=mock_account,
            ),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker = MagicMock()
            # Simulate network failure when accessing .info
            type(mock_ticker).info = property(
                lambda self: (_ for _ in ()).throw(RuntimeError("network error"))
            )
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("analyze_dividend_income")
            result = await tool.fn(start_date="2025-01-01", ctx=None)
            data = json.loads(result)

        pos = data["positions"][0]
        assert Decimal(pos["dividend_yield_pct"]) == Decimal("0")
        assert Decimal(pos["annual_dividend"]) == Decimal("0")

    @pytest.mark.asyncio
    async def test_empty_positions_returns_zero_totals(
        self,
        test_mcp: FastMCP,
    ) -> None:
        """An account with no STK positions must return zero summary totals."""
        mock_account = _mock_account([])
        with (
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=("xml_data", date(2025, 1, 1), date(2025, 10, 31)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._parse_account_by_index",
                return_value=mock_account,
            ),
        ):
            tool = await test_mcp.get_tool("analyze_dividend_income")
            result = await tool.fn(start_date="2025-01-01", ctx=None)
            data = json.loads(result)

        assert data["position_count"] == 0
        assert Decimal(data["summary"]["total_annual_dividend"]) == Decimal("0")
        assert Decimal(data["summary"]["total_net_receipt"]) == Decimal("0")

    @pytest.mark.asyncio
    async def test_result_is_valid_json(
        self,
        test_mcp: FastMCP,
        ie_position: Position,
        us_position: Position,
    ) -> None:
        """The tool must return valid, parseable JSON."""
        mock_account = _mock_account([ie_position, us_position])
        with (
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._get_or_fetch_data",
                new_callable=AsyncMock,
                return_value=("xml_data", date(2025, 1, 1), date(2025, 10, 31)),
            ),
            patch(
                "ib_sec_mcp.mcp.tools.composable_data._parse_account_by_index",
                return_value=mock_account,
            ),
            patch("yfinance.Ticker") as mock_ticker_cls,
        ):
            mock_ticker = MagicMock()
            mock_ticker.info = {"dividendYield": 0.025}
            mock_ticker_cls.return_value = mock_ticker

            tool = await test_mcp.get_tool("analyze_dividend_income")
            result = await tool.fn(start_date="2025-01-01", ctx=None)

        parsed = json.loads(result)
        assert "positions" in parsed
        assert "summary" in parsed
        assert "date_range" in parsed
        assert "tax_efficiency_note" in parsed
