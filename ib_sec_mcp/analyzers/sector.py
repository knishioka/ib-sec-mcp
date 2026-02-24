"""Sector allocation analyzer"""

import asyncio
import logging
from collections import defaultdict
from decimal import Decimal
from typing import Any

from ib_sec_mcp.analyzers.base import AnalysisResult, BaseAnalyzer
from ib_sec_mcp.models.trade import AssetClass

logger = logging.getLogger(__name__)

# Asset classes that have GICS sector data (equity-like)
EQUITY_ASSET_CLASSES = {AssetClass.STOCK, AssetClass.FUND}

# Non-equity category labels
NON_EQUITY_CATEGORIES: dict[AssetClass, str] = {
    AssetClass.BOND: "Fixed Income",
    AssetClass.OPTION: "Derivatives",
    AssetClass.FUTURE: "Derivatives",
    AssetClass.FOREX: "Cash & FX",
    AssetClass.OTHER: "Other",
}


async def fetch_sector_info(symbols: list[str]) -> dict[str, dict[str, str]]:
    """Fetch sector and industry info from Yahoo Finance for multiple symbols.

    Args:
        symbols: List of ticker symbols

    Returns:
        Dict mapping symbol to {"sector": ..., "industry": ...}
    """
    import yfinance as yf

    result: dict[str, dict[str, str]] = {}

    async def _fetch_one(symbol: str) -> tuple[str, dict[str, str]]:
        def _get_info() -> dict[str, str]:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                return {
                    "sector": info.get("sector", "Unknown"),
                    "industry": info.get("industry", "Unknown"),
                }
            except Exception:
                logger.warning("Failed to fetch sector info for %s", symbol)
                return {"sector": "Unknown", "industry": "Unknown"}

        info = await asyncio.to_thread(_get_info)
        return symbol, info

    tasks = [_fetch_one(s) for s in symbols]
    for coro in asyncio.as_completed(tasks):
        symbol, info = await coro
        result[symbol] = info

    return result


def calculate_hhi(allocations: dict[str, Decimal]) -> Decimal:
    """Calculate Herfindahl-Hirschman Index for concentration measurement.

    HHI ranges from 0 to 10000:
    - < 1500: Low concentration
    - 1500-2500: Moderate concentration
    - > 2500: High concentration

    Args:
        allocations: Dict mapping category to percentage (0-100)

    Returns:
        HHI value
    """
    return sum((pct * pct for pct in allocations.values()), Decimal("0"))


def assess_concentration(hhi: Decimal) -> str:
    """Assess concentration level based on HHI.

    Args:
        hhi: Herfindahl-Hirschman Index value

    Returns:
        Assessment string: "LOW", "MODERATE", or "HIGH"
    """
    if hhi < Decimal("1500"):
        return "LOW"
    elif hhi < Decimal("2500"):
        return "MODERATE"
    else:
        return "HIGH"


class SectorAnalyzer(BaseAnalyzer):
    """Analyze portfolio sector allocation and concentration risk.

    Uses Yahoo Finance to fetch GICS sector/industry data for equity positions.
    Non-equity positions (bonds, options, futures, forex) are categorized separately.
    Cash is included as "Cash & Equivalents" for complete portfolio allocation.
    """

    def analyze(self) -> AnalysisResult:
        """Run sector allocation analysis (sync wrapper).

        Returns:
            AnalysisResult with sector allocation data
        """
        return asyncio.run(self.analyze_async())

    async def analyze_async(self) -> AnalysisResult:
        """Run sector allocation analysis.

        Returns:
            AnalysisResult with sector allocation and concentration metrics
        """
        positions = self.get_positions()
        cash = self.get_total_cash()

        # Use position value + cash for complete portfolio allocation
        position_total = sum((p.position_value for p in positions), Decimal("0"))
        total_value = position_total + cash

        if total_value == Decimal("0"):
            return self._create_result(
                sectors={},
                concentration_risk={"hhi": "0", "assessment": "LOW"},
                position_count=0,
            )

        # Separate equity and non-equity positions
        equity_positions = [p for p in positions if p.asset_class in EQUITY_ASSET_CLASSES]
        non_equity_positions = [p for p in positions if p.asset_class not in EQUITY_ASSET_CLASSES]

        # Fetch sector info for equity symbols
        equity_symbols = list({p.symbol for p in equity_positions})
        sector_info = await fetch_sector_info(equity_symbols) if equity_symbols else {}

        # Build sector allocation
        sector_values: dict[str, Decimal] = defaultdict(Decimal)
        sector_positions: dict[str, list[dict[str, Any]]] = defaultdict(list)

        # Process equity positions
        for pos in equity_positions:
            info = sector_info.get(pos.symbol, {"sector": "Unknown", "industry": "Unknown"})
            sector = info["sector"]
            sector_values[sector] += pos.position_value
            sector_positions[sector].append(
                {
                    "symbol": pos.symbol,
                    "description": pos.description,
                    "value": str(pos.position_value),
                    "industry": info["industry"],
                    "currency": pos.currency,
                }
            )

        # Process non-equity positions
        for pos in non_equity_positions:
            category = NON_EQUITY_CATEGORIES.get(pos.asset_class, "Other")
            sector_values[category] += pos.position_value
            sector_positions[category].append(
                {
                    "symbol": pos.symbol,
                    "description": pos.description,
                    "value": str(pos.position_value),
                    "asset_class": pos.asset_class.value,
                    "currency": pos.currency,
                }
            )

        # Include cash as a category if present
        if cash > Decimal("0"):
            sector_values["Cash & Equivalents"] = cash

        # Calculate percentages and build result
        sectors: dict[str, Any] = {}
        allocation_pcts: dict[str, Decimal] = {}

        for sector_name in sorted(
            sector_values.keys(), key=lambda s: sector_values[s], reverse=True
        ):
            value = sector_values[sector_name]
            pct = (value / total_value) * Decimal("100")
            allocation_pcts[sector_name] = pct
            sectors[sector_name] = {
                "value": str(value),
                "percentage": str(pct),
                "positions": sector_positions.get(sector_name, []),
                "position_count": len(sector_positions.get(sector_name, [])),
            }

        # Calculate concentration risk using HHI
        hhi = calculate_hhi(allocation_pcts)
        assessment = assess_concentration(hhi)

        return self._create_result(
            sectors=sectors,
            concentration_risk={
                "hhi": str(hhi),
                "assessment": assessment,
                "description": (
                    "Low sector concentration - well diversified"
                    if assessment == "LOW"
                    else (
                        "Moderate sector concentration - consider diversifying"
                        if assessment == "MODERATE"
                        else "High sector concentration - significant concentration risk"
                    )
                ),
            },
            position_count=len(positions),
            equity_count=len(equity_positions),
            non_equity_count=len(non_equity_positions),
        )
