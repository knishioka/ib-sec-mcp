"""MCP Resources for IB Analytics

Provides read-only access to portfolio data via URI patterns.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TypedDict

import yaml
from fastmcp import FastMCP

from ib_sec_mcp.analyzers.risk import RiskAnalyzer
from ib_sec_mcp.analyzers.tax import TaxAnalyzer
from ib_sec_mcp.core.parsers import XMLParser, detect_format
from ib_sec_mcp.models.account import Account
from ib_sec_mcp.models.trade import AssetClass, BuySell

# --- TypedDicts for resource handler return structures ---


class FileInfo(TypedDict):
    filename: str
    path: str
    size_bytes: int
    modified: float


class LossHarvestingOpportunity(TypedDict):
    symbol: str
    unrealized_loss: str
    holding_period_days: int
    potential_tax_savings: str


class TaxLotSummary(TypedDict):
    total_lots: int
    long_term_lots: int
    short_term_lots: int


class WashSaleWarning(TypedDict):
    symbol: str
    message: str


class TaxContext(TypedDict):
    short_term_gains: str
    long_term_gains: str
    total_realized_gains: str
    bond_oid_income: str
    estimated_tax_liability: str
    tax_loss_harvesting_opportunities: list[LossHarvestingOpportunity]
    tax_lot_summary: TaxLotSummary
    wash_sale_warnings: list[WashSaleWarning]


class AllocationEntry(TypedDict):
    percentage: str
    value: str


class DriftEntry(TypedDict):
    drift: str
    status: str


class SuggestedAction(TypedDict):
    action: str
    asset_class: str
    amount: str
    reason: str


class TopHolding(TypedDict):
    symbol: str
    percentage: str


class ConcentrationRisk(TypedDict):
    top_holdings: list[TopHolding]
    max_position_size: str
    diversification_score: str


class RebalancingContext(TypedDict):
    current_allocation: dict[str, AllocationEntry]
    target_allocation: dict[str, str]
    drift_analysis: dict[str, DriftEntry]
    rebalancing_needed: bool
    suggested_actions: list[SuggestedAction]
    concentration_risk: ConcentrationRisk


class MaturityYearInfo(TypedDict):
    value: Decimal
    count: int


# Resource URI constants
RESOURCE_PORTFOLIO_LIST = "ib://portfolio/list"
RESOURCE_PORTFOLIO_LATEST = "ib://portfolio/latest"
RESOURCE_ACCOUNTS = "ib://accounts/{account_id}"
RESOURCE_TRADES_RECENT = "ib://trades/recent"
RESOURCE_POSITIONS_CURRENT = "ib://positions/current"
RESOURCE_STRATEGY_TAX = "ib://strategy/tax-context"
RESOURCE_STRATEGY_REBALANCING = "ib://strategy/rebalancing-context"
RESOURCE_STRATEGY_RISK = "ib://strategy/risk-context"
RESOURCE_USER_PROFILE = "ib://user/profile"


def _parse_xml_file(file_path: Path) -> Account:
    """
    Parse XML file and return first account with date range

    Args:
        file_path: Path to XML file

    Returns:
        Account object from first account in file
    """
    from datetime import datetime

    # Extract dates from filename (format: {account_id}_{from_date}_{to_date}.xml)
    filename = file_path.stem
    parts = filename.split("_")

    if len(parts) >= 3:
        try:
            from_date = datetime.strptime(parts[-2], "%Y-%m-%d").date()
            to_date = datetime.strptime(parts[-1], "%Y-%m-%d").date()
        except ValueError:
            # Fallback to current year
            from_date = date(date.today().year, 1, 1)
            to_date = date.today()
    else:
        # Fallback to current year
        from_date = date(date.today().year, 1, 1)
        to_date = date.today()

    # Read and parse XML
    with open(file_path) as f:
        xml_data = f.read()

    # Validate XML format
    detect_format(xml_data)  # Raises ValueError if not XML

    # Parse all accounts and return first one
    accounts = XMLParser.to_accounts(xml_data, from_date, to_date)
    if not accounts:
        raise ValueError(f"No accounts found in {file_path}")

    return list(accounts.values())[0]


def register_resources(mcp: FastMCP) -> None:
    """Register all IB Analytics resources with MCP server"""

    @mcp.resource(RESOURCE_PORTFOLIO_LIST)
    def list_portfolio_files() -> str:
        """
        List all available portfolio XML files

        Returns:
            JSON string with list of available files
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"files": [], "message": "No data directory found"})

        files: list[FileInfo] = []
        for xml_file in data_dir.glob("*.xml"):
            files.append(
                {
                    "filename": xml_file.name,
                    "path": str(xml_file),
                    "size_bytes": xml_file.stat().st_size,
                    "modified": xml_file.stat().st_mtime,
                }
            )

        files.sort(key=lambda x: float(x["modified"]), reverse=True)
        return json.dumps({"files": files, "count": len(files)}, indent=2)

    @mcp.resource(RESOURCE_PORTFOLIO_LATEST)
    def get_latest_portfolio() -> str:
        """
        Get summary of the most recently modified portfolio file

        Returns:
            JSON string with latest portfolio summary
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"error": "No data directory found"})

        xml_files = list(data_dir.glob("*.xml"))
        if not xml_files:
            return json.dumps({"error": "No XML files found"})

        # Get most recent file
        latest_file = max(xml_files, key=lambda f: f.stat().st_mtime)

        # Parse XML file
        account = _parse_xml_file(latest_file)

        summary = {
            "file": latest_file.name,
            "account_id": account.account_id,
            "base_currency": account.base_currency,
            "total_cash": str(account.total_cash),
            "total_value": str(account.total_value),
            "num_trades": len(account.trades),
            "num_positions": len(account.positions),
            "date_range": {
                "from": str(account.from_date),
                "to": str(account.to_date),
            },
        }

        return json.dumps(summary, indent=2)

    @mcp.resource(RESOURCE_ACCOUNTS)
    def get_account_data(account_id: str) -> str:
        """
        Get data for a specific account ID

        Args:
            account_id: IB account ID (e.g., U12345678)

        Returns:
            JSON string with account data
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"error": "No data directory found"})

        # Find file matching account ID
        matching_files = [f for f in data_dir.glob("*.xml") if account_id in f.name]

        if not matching_files:
            return json.dumps({"error": f"No files found for account {account_id}"})

        # Use most recent file
        latest_file = max(matching_files, key=lambda f: f.stat().st_mtime)

        # Parse XML file
        account = _parse_xml_file(latest_file)

        # Basic account info
        account_data = {
            "account_id": account.account_id,
            "base_currency": account.base_currency,
            "total_cash": str(account.total_cash),
            "total_value": str(account.total_value),
            "date_range": {
                "from": str(account.from_date),
                "to": str(account.to_date),
            },
            "file": latest_file.name,
        }

        return json.dumps(account_data, indent=2)

    @mcp.resource(RESOURCE_TRADES_RECENT)
    def get_recent_trades() -> str:
        """
        Get most recent trades from latest portfolio file

        Returns:
            JSON string with recent trades (last 10)
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"error": "No data directory found"})

        xml_files = list(data_dir.glob("*.xml"))
        if not xml_files:
            return json.dumps({"error": "No XML files found"})

        latest_file = max(xml_files, key=lambda f: f.stat().st_mtime)

        # Parse XML file
        account = _parse_xml_file(latest_file)

        # Sort trades by date descending
        sorted_trades = sorted(account.trades, key=lambda t: t.trade_date, reverse=True)

        # Get last 10 trades
        recent = sorted_trades[:10]

        trades_data = [
            {
                "date": str(t.trade_date),
                "symbol": t.symbol,
                "buy_sell": t.buy_sell.value,
                "quantity": str(t.quantity),
                "price": str(t.trade_price),
                "commission": str(t.ib_commission),
                "pnl": str(t.fifo_pnl_realized),
            }
            for t in recent
        ]

        return json.dumps({"trades": trades_data, "count": len(trades_data)}, indent=2)

    @mcp.resource(RESOURCE_POSITIONS_CURRENT)
    def get_current_positions() -> str:
        """
        Get current positions from latest portfolio file

        Returns:
            JSON string with current positions
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"error": "No data directory found"})

        xml_files = list(data_dir.glob("*.xml"))
        if not xml_files:
            return json.dumps({"error": "No XML files found"})

        latest_file = max(xml_files, key=lambda f: f.stat().st_mtime)

        # Parse XML file
        account = _parse_xml_file(latest_file)

        positions_data = [
            {
                "symbol": p.symbol,
                "description": p.description,
                "quantity": str(p.quantity),
                "cost_basis": str(p.cost_basis),
                "market_value": str(p.position_value),
                "unrealized_pnl": str(p.unrealized_pnl),
                "asset_class": p.asset_class.value if p.asset_class else None,
            }
            for p in account.positions
        ]

        return json.dumps({"positions": positions_data, "count": len(positions_data)}, indent=2)

    @mcp.resource(RESOURCE_STRATEGY_TAX)
    def get_tax_context() -> str:
        """
        Get tax planning context with gains/losses and opportunities

        Provides comprehensive tax information for investment decisions including
        realized gains, estimated tax liability, loss harvesting opportunities,
        and wash sale warnings.

        Returns:
            JSON string with tax context data
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"error": "No data directory found"})

        xml_files = list(data_dir.glob("*.xml"))
        if not xml_files:
            return json.dumps({"error": "No XML files found"})

        latest_file = max(xml_files, key=lambda f: f.stat().st_mtime)

        # Parse XML file
        account = _parse_xml_file(latest_file)

        # Run tax analysis
        analyzer = TaxAnalyzer(account=account)
        tax_result = analyzer.analyze()

        # Calculate short-term vs long-term gains from trades
        today = date.today()
        short_term_gains = Decimal("0")
        long_term_gains = Decimal("0")

        for trade in account.trades:
            if trade.fifo_pnl_realized > 0:
                # TODO: Holding period calculation requires tracking acquisition dates
                # Current limitation: Trade model doesn't track original purchase date for SELL trades
                # Workaround: Classify all realized gains as short-term (conservative approach)
                # Proper fix: Extend data model to track cost basis lots with acquisition dates
                short_term_gains += trade.fifo_pnl_realized
                # Note: long_term_gains will remain 0 until proper holding period tracking is implemented

        total_realized_gains = short_term_gains + long_term_gains

        # Find tax loss harvesting opportunities
        loss_harvesting_opportunities: list[LossHarvestingOpportunity] = []
        for position in account.positions:
            if position.unrealized_pnl < 0:
                # Find earliest trade for this position to calculate holding period
                position_trades = [
                    t
                    for t in account.trades
                    if t.symbol == position.symbol and t.buy_sell == BuySell.BUY
                ]
                if position_trades:
                    earliest_trade = min(position_trades, key=lambda t: t.trade_date)
                    holding_period_days = (today - earliest_trade.trade_date).days
                else:
                    holding_period_days = 0

                potential_tax_savings = abs(position.unrealized_pnl) * Decimal("0.30")
                loss_harvesting_opportunities.append(
                    {
                        "symbol": position.symbol,
                        "unrealized_loss": str(position.unrealized_pnl),
                        "holding_period_days": holding_period_days,
                        "potential_tax_savings": str(potential_tax_savings),
                    }
                )

        # Tax lot summary
        long_term_lots = sum(
            1
            for t in account.trades
            if t.buy_sell == BuySell.BUY and (today - t.trade_date).days >= 365
        )
        short_term_lots = sum(
            1
            for t in account.trades
            if t.buy_sell == BuySell.BUY and (today - t.trade_date).days < 365
        )
        total_lots = long_term_lots + short_term_lots

        # Wash sale warnings (simplified - check if any symbol was sold at loss and rebought within 30 days)
        wash_sale_warnings: list[WashSaleWarning] = []
        for symbol in {t.symbol for t in account.trades}:
            symbol_trades = [t for t in account.trades if t.symbol == symbol]
            symbol_trades.sort(key=lambda t: t.trade_date)

            for i, trade in enumerate(symbol_trades):
                if trade.buy_sell == BuySell.SELL and trade.fifo_pnl_realized < 0:
                    # Check if rebought within 30 days
                    for future_trade in symbol_trades[i + 1 :]:
                        if future_trade.buy_sell == BuySell.BUY:
                            days_between = (future_trade.trade_date - trade.trade_date).days
                            if days_between <= 30:
                                wash_sale_warnings.append(
                                    {
                                        "symbol": symbol,
                                        "message": f"Potential wash sale: sold at loss on {trade.trade_date}, rebought on {future_trade.trade_date}",
                                    }
                                )
                                break

        # Extract OID income from tax result
        bond_oid_income = Decimal(tax_result.get("phantom_income_total", "0"))
        estimated_tax_liability = Decimal(tax_result.get("total_estimated_tax", "0"))

        tax_context: TaxContext = {
            "short_term_gains": str(short_term_gains),
            "long_term_gains": str(long_term_gains),
            "total_realized_gains": str(total_realized_gains),
            "bond_oid_income": str(bond_oid_income),
            "estimated_tax_liability": str(estimated_tax_liability),
            "tax_loss_harvesting_opportunities": loss_harvesting_opportunities,
            "tax_lot_summary": {
                "total_lots": total_lots,
                "long_term_lots": long_term_lots,
                "short_term_lots": short_term_lots,
            },
            "wash_sale_warnings": wash_sale_warnings,
        }

        return json.dumps(tax_context, indent=2, default=str)

    @mcp.resource(RESOURCE_STRATEGY_REBALANCING)
    def get_rebalancing_context() -> str:
        """
        Get portfolio rebalancing context with allocation and drift analysis

        Provides portfolio allocation, target allocations, drift analysis,
        and suggested rebalancing actions.

        Returns:
            JSON string with rebalancing context data
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"error": "No data directory found"})

        xml_files = list(data_dir.glob("*.xml"))
        if not xml_files:
            return json.dumps({"error": "No XML files found"})

        latest_file = max(xml_files, key=lambda f: f.stat().st_mtime)

        # Parse XML file
        account = _parse_xml_file(latest_file)

        # Calculate current allocation
        total_value = account.total_value
        if total_value == 0:
            return json.dumps({"error": "No portfolio value found"})

        # Calculate asset class values
        bond_value = sum(
            p.position_value for p in account.positions if p.asset_class == AssetClass.BOND
        )
        stock_value = sum(
            p.position_value for p in account.positions if p.asset_class == AssetClass.STOCK
        )
        cash_value = account.total_cash

        # Current allocation percentages (using Decimal for precision)
        bond_pct = (
            ((bond_value / total_value) * Decimal("100")).quantize(Decimal("0.1"))
            if total_value > 0
            else Decimal("0.0")
        )
        stock_pct = (
            ((stock_value / total_value) * Decimal("100")).quantize(Decimal("0.1"))
            if total_value > 0
            else Decimal("0.0")
        )
        cash_pct = (
            ((cash_value / total_value) * Decimal("100")).quantize(Decimal("0.1"))
            if total_value > 0
            else Decimal("0.0")
        )

        current_allocation: dict[str, AllocationEntry] = {
            "BOND": {"percentage": str(bond_pct), "value": str(bond_value)},
            "STK": {"percentage": str(stock_pct), "value": str(stock_value)},
            "CASH": {"percentage": str(cash_pct), "value": str(cash_value)},
        }

        # Target allocation (TODO: Make configurable via config file or tool parameter)
        # Default conservative allocation (60/35/5)
        target_allocation = {
            "BOND": Decimal("60.0"),
            "STK": Decimal("35.0"),
            "CASH": Decimal("5.0"),
        }

        # Drift analysis
        bond_drift = bond_pct - target_allocation["BOND"]
        stock_drift = stock_pct - target_allocation["STK"]
        cash_drift = cash_pct - target_allocation["CASH"]

        drift_analysis: dict[str, DriftEntry] = {
            "BOND": {
                "drift": str(bond_drift.quantize(Decimal("0.1"))),
                "status": (
                    "overweight"
                    if bond_drift > 0
                    else "underweight"
                    if bond_drift < 0
                    else "balanced"
                ),
            },
            "STK": {
                "drift": str(stock_drift.quantize(Decimal("0.1"))),
                "status": (
                    "overweight"
                    if stock_drift > 0
                    else "underweight"
                    if stock_drift < 0
                    else "balanced"
                ),
            },
            "CASH": {
                "drift": str(cash_drift.quantize(Decimal("0.1"))),
                "status": (
                    "overweight"
                    if cash_drift > 0
                    else "underweight"
                    if cash_drift < 0
                    else "balanced"
                ),
            },
        }

        # Check if rebalancing is needed (if any drift > ±5%)
        rebalancing_needed = (
            abs(bond_drift) > Decimal("5")
            or abs(stock_drift) > Decimal("5")
            or abs(cash_drift) > Decimal("5")
        )

        # Suggested actions
        suggested_actions: list[SuggestedAction] = []

        if rebalancing_needed:
            # Calculate target values
            target_bond_value = total_value * (target_allocation["BOND"] / Decimal("100"))
            target_stock_value = total_value * (target_allocation["STK"] / Decimal("100"))

            # Bond rebalancing
            bond_diff = bond_value - target_bond_value
            if abs(bond_diff) > Decimal("1000"):  # Only suggest if difference > $1000
                if bond_diff > 0:
                    suggested_actions.append(
                        {
                            "action": "sell",
                            "asset_class": "BOND",
                            "amount": str(abs(bond_diff)),
                            "reason": f"Reduce from {bond_pct}% to {target_allocation['BOND']}% target",
                        }
                    )
                else:
                    suggested_actions.append(
                        {
                            "action": "buy",
                            "asset_class": "BOND",
                            "amount": str(abs(bond_diff)),
                            "reason": f"Increase from {bond_pct}% to {target_allocation['BOND']}% target",
                        }
                    )

            # Stock rebalancing
            stock_diff = stock_value - target_stock_value
            if abs(stock_diff) > Decimal("1000"):
                if stock_diff > 0:
                    suggested_actions.append(
                        {
                            "action": "sell",
                            "asset_class": "STK",
                            "amount": str(abs(stock_diff)),
                            "reason": f"Reduce from {stock_pct}% to {target_allocation['STK']}% target",
                        }
                    )
                else:
                    suggested_actions.append(
                        {
                            "action": "buy",
                            "asset_class": "STK",
                            "amount": str(abs(stock_diff)),
                            "reason": f"Increase from {stock_pct}% to {target_allocation['STK']}% target",
                        }
                    )

        # Concentration risk
        top_holdings: list[TopHolding] = []
        sorted_positions = sorted(account.positions, key=lambda p: p.position_value, reverse=True)
        max_position_size = Decimal("0")

        for position in sorted_positions[:2]:  # Top 2 holdings
            position_pct = (
                ((position.position_value / total_value) * Decimal("100")).quantize(Decimal("0.1"))
                if total_value > 0
                else Decimal("0.0")
            )
            top_holdings.append({"symbol": position.symbol, "percentage": str(position_pct)})
            max_position_size = max(max_position_size, position_pct)

        # Diversification score
        if max_position_size < Decimal("15"):
            diversification_score = "good"
        elif max_position_size <= Decimal("25"):
            diversification_score = "moderate"
        else:
            diversification_score = "poor"

        rebalancing_context: RebalancingContext = {
            "current_allocation": current_allocation,
            "target_allocation": {
                "BOND": str(target_allocation["BOND"]),
                "STK": str(target_allocation["STK"]),
                "CASH": str(target_allocation["CASH"]),
            },
            "drift_analysis": drift_analysis,
            "rebalancing_needed": rebalancing_needed,
            "suggested_actions": suggested_actions,
            "concentration_risk": {
                "top_holdings": top_holdings,
                "max_position_size": str(max_position_size),
                "diversification_score": diversification_score,
            },
        }

        return json.dumps(rebalancing_context, indent=2, default=str)

    @mcp.resource(RESOURCE_STRATEGY_RISK)
    def get_risk_context() -> str:
        """
        Get comprehensive risk assessment context

        Provides portfolio risk metrics, interest rate scenarios,
        concentration risk, liquidity risk, and maturity ladder.

        Returns:
            JSON string with risk context data
        """
        data_dir = Path("data/raw")
        if not data_dir.exists():
            return json.dumps({"error": "No data directory found"})

        xml_files = list(data_dir.glob("*.xml"))
        if not xml_files:
            return json.dumps({"error": "No XML files found"})

        latest_file = max(xml_files, key=lambda f: f.stat().st_mtime)

        # Parse XML file
        account = _parse_xml_file(latest_file)

        # Portfolio risk metrics
        total_value = account.total_value
        if total_value == 0:
            return json.dumps({"error": "No portfolio value found"})

        # Asset class percentages
        bond_value = sum(
            p.position_value for p in account.positions if p.asset_class == AssetClass.BOND
        )
        stock_value = sum(
            p.position_value for p in account.positions if p.asset_class == AssetClass.STOCK
        )
        cash_value = account.total_cash

        cash_percentage = (
            ((cash_value / total_value) * Decimal("100")).quantize(Decimal("0.1"))
            if total_value > 0
            else Decimal("0.0")
        )
        equity_percentage = (
            ((stock_value / total_value) * Decimal("100")).quantize(Decimal("0.1"))
            if total_value > 0
            else Decimal("0.0")
        )
        fixed_income_percentage = (
            ((bond_value / total_value) * Decimal("100")).quantize(Decimal("0.1"))
            if total_value > 0
            else Decimal("0.0")
        )

        # Calculate bond portfolio duration and maturity
        bond_positions = [p for p in account.positions if p.asset_class == AssetClass.BOND]

        # Calculate average duration and maturity
        total_duration = Decimal("0")
        total_maturity_years = Decimal("0")
        bond_count = 0

        for position in bond_positions:
            if position.maturity_date:
                years_to_maturity = Decimal((position.maturity_date - date.today()).days) / Decimal(
                    "365.25"
                )
                total_maturity_years += years_to_maturity
                # For zero-coupon bonds, duration equals time to maturity (exact, not approximation)
                # Note: For coupon-bearing bonds, use Macaulay/Modified duration instead
                total_duration += years_to_maturity
                bond_count += 1

        avg_duration = str(total_duration / bond_count) if bond_count > 0 else "0"
        avg_maturity = str(total_maturity_years / bond_count) if bond_count > 0 else "0"

        # Interest rate scenarios using RiskAnalyzer
        risk_analyzer = RiskAnalyzer(account=account)
        risk_result = risk_analyzer.analyze()

        # Extract specific scenarios for ±1% rate changes
        interest_rate_impact_1pct_rise = Decimal("0")
        interest_rate_impact_1pct_fall = Decimal("0")

        if (
            "interest_rate_scenarios" in risk_result
            and "scenarios" in risk_result["interest_rate_scenarios"]
        ):
            for scenario in risk_result["interest_rate_scenarios"]["scenarios"]:
                if scenario["rate_change"] == "1.0":
                    interest_rate_impact_1pct_rise = Decimal(scenario["total_value_change"])
                elif scenario["rate_change"] == "-1.0":
                    interest_rate_impact_1pct_fall = Decimal(scenario["total_value_change"])

        interest_rate_scenarios = {
            "1_percent_rise": {
                "estimated_impact": str(interest_rate_impact_1pct_rise),
                "new_portfolio_value": str(total_value + interest_rate_impact_1pct_rise),
                "percentage_change": str(
                    ((interest_rate_impact_1pct_rise / total_value) * Decimal("100")).quantize(
                        Decimal("0.1")
                    )
                    if total_value > 0
                    else Decimal("0.0")
                ),
            },
            "1_percent_fall": {
                "estimated_impact": str(interest_rate_impact_1pct_fall),
                "new_portfolio_value": str(total_value + interest_rate_impact_1pct_fall),
                "percentage_change": str(
                    ((interest_rate_impact_1pct_fall / total_value) * Decimal("100")).quantize(
                        Decimal("0.1")
                    )
                    if total_value > 0
                    else Decimal("0.0")
                ),
            },
        }

        # Concentration risk
        asset_class_concentration = {
            "bonds": (
                "high"
                if fixed_income_percentage > 60
                else "moderate"
                if fixed_income_percentage > 40
                else "low"
            ),
            "stocks": (
                "high"
                if equity_percentage > 60
                else "moderate"
                if equity_percentage > 40
                else "low"
            ),
        }

        # Find max single position
        max_position = None
        max_position_pct = Decimal("0.0")
        if account.positions:
            sorted_positions = sorted(
                account.positions, key=lambda p: p.position_value, reverse=True
            )
            max_position = sorted_positions[0]
            max_position_pct = (
                ((max_position.position_value / total_value) * Decimal("100")).quantize(
                    Decimal("0.1")
                )
                if total_value > 0
                else Decimal("0.0")
            )

        single_security_risk = {
            "max_position": {
                "symbol": max_position.symbol if max_position else None,
                "percentage": str(max_position_pct),
            },
            "risk_level": (
                "high"
                if max_position_pct > Decimal("25")
                else "moderate"
                if max_position_pct > Decimal("15")
                else "low"
            ),
        }

        # Liquidity risk
        today = date.today()
        liquid_positions = 0
        illiquid_positions = 0

        for position in account.positions:
            if position.asset_class == AssetClass.STOCK:
                liquid_positions += 1
            elif position.asset_class == AssetClass.BOND:
                # Bonds maturing within 1 year are considered less liquid
                if position.maturity_date:
                    days_to_maturity = (position.maturity_date - today).days
                    if days_to_maturity < 365:
                        illiquid_positions += 1
                    else:
                        liquid_positions += 1
                else:
                    liquid_positions += 1

        total_positions = liquid_positions + illiquid_positions
        liquidity_ratio = liquid_positions / total_positions if total_positions > 0 else 0.0

        liquidity_risk = {
            "liquid_positions": liquid_positions,
            "illiquid_positions": illiquid_positions,
            "liquidity_ratio": round(liquidity_ratio, 2),
        }

        # Maturity ladder
        maturity_ladder = []
        maturity_by_year: dict[int, MaturityYearInfo] = {}

        for position in bond_positions:
            if position.maturity_date:
                maturity_year = position.maturity_date.year
                if maturity_year not in maturity_by_year:
                    maturity_by_year[maturity_year] = {
                        "value": Decimal("0"),
                        "count": 0,
                    }
                maturity_by_year[maturity_year]["value"] += position.position_value
                maturity_by_year[maturity_year]["count"] += 1

        for year in sorted(maturity_by_year.keys())[:3]:  # Next 3 maturity years
            maturity_ladder.append(
                {
                    "year": year,
                    "value": str(maturity_by_year[year]["value"]),
                    "count": maturity_by_year[year]["count"],
                }
            )

        risk_context = {
            "portfolio_risk_metrics": {
                "total_value": str(total_value),
                "cash_percentage": str(cash_percentage),
                "equity_percentage": str(equity_percentage),
                "fixed_income_percentage": str(fixed_income_percentage),
                "portfolio_duration": avg_duration,
                "average_maturity_years": avg_maturity,
            },
            "interest_rate_scenarios": interest_rate_scenarios,
            "concentration_risk": {
                "asset_class_concentration": asset_class_concentration,
                "single_security_risk": single_security_risk,
            },
            "liquidity_risk": liquidity_risk,
            "maturity_ladder": maturity_ladder,
        }

        return json.dumps(risk_context, indent=2, default=str)

    @mcp.resource(RESOURCE_USER_PROFILE)
    def get_user_profile() -> str:
        """
        Get user investment profile and preferences

        Returns:
            JSON string with user profile including:
            - Residency and tax implications
            - Investment profile (growth/income/preservation/balanced)
            - Investment horizon (short/medium/long)
            - Allocation targets (stocks/bonds/cash percentages)
            - ETF preferences (domicile, preferred symbols)
            - External holdings (other accounts, total value)
            - Personal notes on strategy

        Example:
            >>> profile = get_user_profile()
            >>> data = json.loads(profile)
            >>> print(data["residency"]["country"])
            Malaysia
        """
        profile_path = Path("notes/investor-profile.yaml")

        if not profile_path.exists():
            return json.dumps(
                {
                    "error": "Profile not found",
                    "path": str(profile_path),
                    "hint": "Create notes/investor-profile.yaml with your investment preferences",
                },
                indent=2,
            )

        try:
            with open(profile_path) as f:
                profile = yaml.safe_load(f)

            return json.dumps(profile, indent=2, default=str)
        except yaml.YAMLError as e:
            return json.dumps(
                {"error": "Failed to parse YAML", "path": str(profile_path), "details": str(e)},
                indent=2,
            )
