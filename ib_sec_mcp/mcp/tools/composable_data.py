"""Composable Data Tools for Investment Strategy Collaboration

Provides fine-grained data access tools that sub-agents can compose for
custom investment analysis and strategy development.
"""

import json
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from fastmcp import Context, FastMCP

from ib_sec_mcp.core.calculator import PerformanceCalculator
from ib_sec_mcp.core.parsers import XMLParser, detect_format
from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.mcp.tools.ib_portfolio import _get_or_fetch_data
from ib_sec_mcp.models.account import Account
from ib_sec_mcp.models.trade import AssetClass
from ib_sec_mcp.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_account_by_index(
    data: str, from_date: date, to_date: date, account_index: int
) -> Account:
    """
    Parse data and extract account by index

    Args:
        data: Raw XML data string
        from_date: Start date
        to_date: End date
        account_index: Account index (0 for first, 1 for second, etc.)

    Returns:
        Account instance for the specified index

    Raises:
        ValidationError: If account_index is out of range or data is not XML
    """
    # Validate XML format and parse all accounts
    detect_format(data)  # Raises ValueError if not XML
    accounts = XMLParser.to_accounts(data, from_date, to_date)

    # Select account by index
    if not accounts:
        raise ValidationError("No accounts found in data")

    account_list = list(accounts.values())
    if account_index >= len(account_list):
        raise ValidationError(
            f"account_index {account_index} out of range (0-{len(account_list) - 1})"
        )

    return account_list[account_index]


def register_composable_data_tools(mcp: FastMCP) -> None:
    """Register composable data access tools"""

    @mcp.tool
    async def get_trades(
        start_date: str,
        end_date: str | None = None,
        symbol: str | None = None,
        asset_class: str | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Get filtered trade data

        Provides granular access to trade records for custom analysis.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            symbol: Filter by symbol (optional)
            asset_class: Filter by asset class - STK, BOND, OPT, FUT, CASH (optional)
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON string with list of trade records

        Example:
            >>> trades = await get_trades("2025-01-01", "2025-10-11", symbol="AAPL")
            >>> # Returns trades for AAPL only
        """
        if ctx:
            filters = []
            if symbol:
                filters.append(f"symbol={symbol}")
            if asset_class:
                filters.append(f"asset_class={asset_class}")
            filter_str = f" ({', '.join(filters)})" if filters else ""
            await ctx.info(f"Getting trades for {start_date} to {end_date or 'today'}{filter_str}")

        # Get data
        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )

        # Parse account by index
        account = _parse_account_by_index(data, from_date, to_date, account_index)

        # Filter trades
        trades = account.trades
        if symbol:
            trades = [t for t in trades if t.symbol == symbol]
        if asset_class:
            try:
                ac = AssetClass(asset_class)
                trades = [t for t in trades if t.asset_class == ac]
            except ValueError:
                if ctx:
                    await ctx.warning(f"Invalid asset_class: {asset_class}, ignoring filter")

        # Convert to JSON
        trades_data = [t.model_dump() for t in trades]

        result = {
            "trade_count": len(trades),
            "date_range": {"from": str(from_date), "to": str(to_date)},
            "filters": {
                "symbol": symbol,
                "asset_class": asset_class,
            },
            "trades": trades_data,
        }

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def get_positions(
        start_date: str,
        end_date: str | None = None,
        symbol: str | None = None,
        asset_class: str | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Get current positions

        Provides granular access to position records for custom analysis.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            symbol: Filter by symbol (optional)
            asset_class: Filter by asset class - STK, BOND, OPT, FUT, CASH (optional)
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON string with list of position records

        Example:
            >>> positions = await get_positions("2025-01-01", "2025-10-11", asset_class="BOND")
            >>> # Returns only bond positions
        """
        if ctx:
            filters = []
            if symbol:
                filters.append(f"symbol={symbol}")
            if asset_class:
                filters.append(f"asset_class={asset_class}")
            filter_str = f" ({', '.join(filters)})" if filters else ""
            await ctx.info(
                f"Getting positions for {start_date} to {end_date or 'today'}{filter_str}"
            )

        # Get data
        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )

        # Parse account by index
        account = _parse_account_by_index(data, from_date, to_date, account_index)

        # Filter positions
        positions = account.positions
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        if asset_class:
            try:
                ac = AssetClass(asset_class)
                positions = [p for p in positions if p.asset_class == ac]
            except ValueError:
                if ctx:
                    await ctx.warning(f"Invalid asset_class: {asset_class}, ignoring filter")

        # Convert to JSON
        positions_data = [p.model_dump() for p in positions]

        # Calculate totals
        total_value = sum((Decimal(p.position_value) for p in positions), Decimal("0"))
        total_unrealized_pnl = sum((Decimal(p.unrealized_pnl) for p in positions), Decimal("0"))
        total_realized_pnl = sum((Decimal(p.realized_pnl) for p in positions), Decimal("0"))

        result = {
            "position_count": len(positions),
            "date_range": {"from": str(from_date), "to": str(to_date)},
            "filters": {
                "symbol": symbol,
                "asset_class": asset_class,
            },
            "totals": {
                "total_value": str(total_value),
                "total_unrealized_pnl": str(total_unrealized_pnl),
                "total_realized_pnl": str(total_realized_pnl),
            },
            "positions": positions_data,
        }

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def get_account_summary(
        start_date: str,
        end_date: str | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Get account overview

        Provides account-level summary information for custom analysis.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON with account_id, total_cash, total_value, base_currency, date_range

        Example:
            >>> summary = await get_account_summary("2025-01-01", "2025-10-11")
            >>> # Returns account overview with cash and value totals
        """
        if ctx:
            await ctx.info(f"Getting account summary for {start_date} to {end_date or 'today'}")

        # Get data
        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )

        # Parse account by index
        account = _parse_account_by_index(data, from_date, to_date, account_index)

        # Build summary
        result = {
            "account_id": account.account_id,
            "account_alias": account.account_alias,
            "base_currency": account.base_currency,
            "date_range": {"from": str(from_date), "to": str(to_date)},
            "cash": {
                "total_cash": str(account.total_cash),
                "by_currency": [
                    {
                        "currency": cb.currency,
                        "ending_cash": str(cb.ending_cash),
                        "ending_settled_cash": str(cb.ending_settled_cash),
                    }
                    for cb in account.cash_balances
                ],
            },
            "positions": {
                "total_value": str(account.total_position_value),
                "total_unrealized_pnl": str(account.total_unrealized_pnl),
                "position_count": account.position_count,
            },
            "trades": {
                "trade_count": account.trade_count,
                "total_realized_pnl": str(account.total_realized_pnl),
                "total_commissions": str(account.total_commissions),
            },
            "account_value": {
                "total_value": str(account.total_value),  # cash + positions
                "breakdown": {
                    "cash": str(account.total_cash),
                    "positions": str(account.total_position_value),
                },
            },
        }

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def calculate_metric(
        metric_name: Literal[
            "win_rate",
            "profit_factor",
            "commission_rate",
            "risk_reward_ratio",
            "total_pnl",
            "realized_pnl",
            "unrealized_pnl",
            "avg_win",
            "avg_loss",
            "largest_win",
            "largest_loss",
            "trade_frequency",
        ],
        start_date: str,
        end_date: str | None = None,
        symbol: str | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Calculate individual performance metric

        Provides specific metric calculations for custom analysis strategies.

        Args:
            metric_name: Name of metric to calculate (see list above)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            symbol: Filter by symbol (optional)
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON with metric_name, metric_value, and calculation_details

        Available metrics:
            - win_rate: Percentage of winning trades
            - profit_factor: Gross profit / gross loss ratio
            - commission_rate: Commission as % of volume
            - risk_reward_ratio: Average win / average loss
            - total_pnl: Realized + unrealized P&L
            - realized_pnl: Total realized P&L from closed trades
            - unrealized_pnl: Total unrealized P&L from open positions
            - avg_win: Average winning trade amount
            - avg_loss: Average losing trade amount
            - largest_win: Largest winning trade
            - largest_loss: Largest losing trade
            - trade_frequency: Trades per day

        Example:
            >>> result = await calculate_metric("win_rate", "2025-01-01", "2025-10-11")
            >>> # Returns win rate percentage with trade counts
        """
        if ctx:
            filter_str = f" for {symbol}" if symbol else ""
            await ctx.info(
                f"Calculating {metric_name}{filter_str} from {start_date} to {end_date or 'today'}"
            )

        # Get data
        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )

        # Parse account by index
        account = _parse_account_by_index(data, from_date, to_date, account_index)

        # Filter by symbol if specified
        if symbol:
            trades = account.get_trades_by_symbol(symbol)
            position = account.get_position_by_symbol(symbol)
            positions = [position] if position else []
        else:
            trades = account.trades
            positions = account.positions

        # Calculate metric
        result: dict[str, Any] = {
            "metric_name": metric_name,
            "date_range": {"from": str(from_date), "to": str(to_date)},
            "filters": {"symbol": symbol},
        }

        if metric_name == "win_rate":
            win_rate, winning_trades, losing_trades = PerformanceCalculator.calculate_win_rate(
                trades
            )
            result["metric_value"] = str(win_rate)
            result["calculation_details"] = {
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "total_trades_with_pnl": winning_trades + losing_trades,
                "description": "Percentage of trades that were profitable",
            }

        elif metric_name == "profit_factor":
            profit_factor = PerformanceCalculator.calculate_profit_factor(trades)
            gross_profit = sum(
                (t.fifo_pnl_realized for t in trades if t.fifo_pnl_realized > 0),
                Decimal("0"),
            )
            gross_loss = abs(
                sum(
                    (t.fifo_pnl_realized for t in trades if t.fifo_pnl_realized < 0),
                    Decimal("0"),
                )
            )
            result["metric_value"] = str(profit_factor)
            result["calculation_details"] = {
                "gross_profit": str(gross_profit),
                "gross_loss": str(gross_loss),
                "description": "Ratio of gross profit to gross loss",
            }

        elif metric_name == "commission_rate":
            total_commissions = sum((abs(t.ib_commission) for t in trades), Decimal("0"))
            total_volume = sum((abs(t.trade_money) for t in trades), Decimal("0"))
            commission_rate = PerformanceCalculator.calculate_commission_rate(
                total_commissions, total_volume
            )
            result["metric_value"] = str(commission_rate)
            result["calculation_details"] = {
                "total_commissions": str(total_commissions),
                "total_volume": str(total_volume),
                "description": "Commission as percentage of trading volume",
            }

        elif metric_name == "risk_reward_ratio":
            wins = [t.fifo_pnl_realized for t in trades if t.fifo_pnl_realized > 0]
            losses = [abs(t.fifo_pnl_realized) for t in trades if t.fifo_pnl_realized < 0]
            avg_win = sum(wins, Decimal("0")) / len(wins) if wins else Decimal("0")
            avg_loss = sum(losses, Decimal("0")) / len(losses) if losses else Decimal("0")
            risk_reward = PerformanceCalculator.calculate_risk_reward_ratio(avg_win, avg_loss)
            result["metric_value"] = str(risk_reward)
            result["calculation_details"] = {
                "average_win": str(avg_win),
                "average_loss": str(avg_loss),
                "win_count": len(wins),
                "loss_count": len(losses),
                "description": "Ratio of average win to average loss",
            }

        elif metric_name == "total_pnl":
            realized_pnl = sum((t.fifo_pnl_realized for t in trades), Decimal("0"))
            unrealized_pnl = sum((p.unrealized_pnl for p in positions), Decimal("0"))
            total_pnl = realized_pnl + unrealized_pnl
            result["metric_value"] = str(total_pnl)
            result["calculation_details"] = {
                "realized_pnl": str(realized_pnl),
                "unrealized_pnl": str(unrealized_pnl),
                "description": "Total P&L (realized + unrealized)",
            }

        elif metric_name == "realized_pnl":
            realized_pnl = sum((t.fifo_pnl_realized for t in trades), Decimal("0"))
            result["metric_value"] = str(realized_pnl)
            result["calculation_details"] = {
                "trade_count": len(trades),
                "description": "Total realized P&L from closed trades",
            }

        elif metric_name == "unrealized_pnl":
            unrealized_pnl = sum((p.unrealized_pnl for p in positions), Decimal("0"))
            result["metric_value"] = str(unrealized_pnl)
            result["calculation_details"] = {
                "position_count": len(positions),
                "description": "Total unrealized P&L from open positions",
            }

        elif metric_name == "avg_win":
            wins = [t.fifo_pnl_realized for t in trades if t.fifo_pnl_realized > 0]
            avg_win = sum(wins, Decimal("0")) / len(wins) if wins else Decimal("0")
            result["metric_value"] = str(avg_win)
            result["calculation_details"] = {
                "winning_trade_count": len(wins),
                "total_profit": str(sum(wins, Decimal("0"))),
                "description": "Average profit per winning trade",
            }

        elif metric_name == "avg_loss":
            losses = [abs(t.fifo_pnl_realized) for t in trades if t.fifo_pnl_realized < 0]
            avg_loss = sum(losses, Decimal("0")) / len(losses) if losses else Decimal("0")
            result["metric_value"] = str(avg_loss)
            result["calculation_details"] = {
                "losing_trade_count": len(losses),
                "total_loss": str(sum(losses, Decimal("0"))),
                "description": "Average loss per losing trade",
            }

        elif metric_name == "largest_win":
            wins = [t.fifo_pnl_realized for t in trades if t.fifo_pnl_realized > 0]
            largest_win = max(wins) if wins else Decimal("0")
            result["metric_value"] = str(largest_win)
            if wins:
                winning_trade_list = [t for t in trades if t.fifo_pnl_realized > 0]
                largest_trade = max(winning_trade_list, key=lambda t: t.fifo_pnl_realized)
                result["calculation_details"] = {
                    "symbol": largest_trade.symbol,
                    "trade_date": str(largest_trade.trade_date),
                    "description": "Largest single winning trade",
                }
            else:
                result["calculation_details"] = {"description": "No winning trades"}

        elif metric_name == "largest_loss":
            losses = [abs(t.fifo_pnl_realized) for t in trades if t.fifo_pnl_realized < 0]
            largest_loss = max(losses) if losses else Decimal("0")
            result["metric_value"] = str(largest_loss)
            if losses:
                losing_trade_list = [t for t in trades if t.fifo_pnl_realized < 0]
                largest_trade = min(losing_trade_list, key=lambda t: t.fifo_pnl_realized)
                result["calculation_details"] = {
                    "symbol": largest_trade.symbol,
                    "trade_date": str(largest_trade.trade_date),
                    "actual_loss": str(largest_trade.fifo_pnl_realized),
                    "description": "Largest single losing trade",
                }
            else:
                result["calculation_details"] = {"description": "No losing trades"}

        elif metric_name == "trade_frequency":
            if trades:
                first_trade_date = min(t.trade_date for t in trades)
                last_trade_date = max(t.trade_date for t in trades)
                trading_days = (last_trade_date - first_trade_date).days + 1
                trades_per_day = (
                    Decimal(len(trades)) / Decimal(trading_days)
                    if trading_days > 0
                    else Decimal("0")
                )
            else:
                trades_per_day = Decimal("0")
                trading_days = 0
            result["metric_value"] = str(trades_per_day)
            result["calculation_details"] = {
                "total_trades": len(trades),
                "trading_days": trading_days,
                "description": "Average number of trades per day",
            }

        else:
            raise ValidationError(f"Unknown metric: {metric_name}")

        return json.dumps(result, indent=2, default=str)

    @mcp.tool
    async def compare_periods(
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str,
        metrics: list[str] | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Compare metrics across two time periods

        Enables period-over-period analysis for strategy development.

        Args:
            period1_start: Period 1 start date in YYYY-MM-DD format
            period1_end: Period 1 end date in YYYY-MM-DD format
            period2_start: Period 2 start date in YYYY-MM-DD format
            period2_end: Period 2 end date in YYYY-MM-DD format
            metrics: List of metrics to compare (defaults to common metrics)
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON comparing metrics side-by-side with percentage changes

        Default metrics compared:
            - win_rate
            - profit_factor
            - realized_pnl
            - commission_rate
            - trade_frequency

        Example:
            >>> comparison = await compare_periods(
            ...     "2025-01-01", "2025-06-30",  # First half
            ...     "2025-07-01", "2025-10-11",  # Second half
            ...     metrics=["win_rate", "realized_pnl"]
            ... )
        """
        if ctx:
            await ctx.info(
                f"Comparing periods: [{period1_start} to {period1_end}] vs [{period2_start} to {period2_end}]"
            )

        # Default metrics if none specified
        if not metrics:
            metrics = [
                "win_rate",
                "profit_factor",
                "realized_pnl",
                "commission_rate",
                "trade_frequency",
            ]

        # Get data for both periods
        data1, from_date1, to_date1 = await _get_or_fetch_data(
            period1_start, period1_end, account_index, use_cache, ctx
        )
        data2, from_date2, to_date2 = await _get_or_fetch_data(
            period2_start, period2_end, account_index, use_cache, ctx
        )

        # Parse both periods by account index
        account1 = _parse_account_by_index(data1, from_date1, to_date1, account_index)
        account2 = _parse_account_by_index(data2, from_date2, to_date2, account_index)

        # Calculate metrics for both periods
        def calculate_metrics(account: Account) -> dict[str, Any]:
            trades = account.trades
            positions = account.positions

            results = {}

            if "win_rate" in metrics:
                win_rate, _, _ = PerformanceCalculator.calculate_win_rate(trades)
                results["win_rate"] = win_rate

            if "profit_factor" in metrics:
                results["profit_factor"] = PerformanceCalculator.calculate_profit_factor(trades)

            if "realized_pnl" in metrics:
                results["realized_pnl"] = sum((t.fifo_pnl_realized for t in trades), Decimal("0"))

            if "unrealized_pnl" in metrics:
                results["unrealized_pnl"] = sum((p.unrealized_pnl for p in positions), Decimal("0"))

            if "total_pnl" in metrics:
                realized = sum((t.fifo_pnl_realized for t in trades), Decimal("0"))
                unrealized = sum((p.unrealized_pnl for p in positions), Decimal("0"))
                results["total_pnl"] = realized + unrealized

            if "commission_rate" in metrics:
                total_commissions = sum((abs(t.ib_commission) for t in trades), Decimal("0"))
                total_volume = sum((abs(t.trade_money) for t in trades), Decimal("0"))
                results["commission_rate"] = PerformanceCalculator.calculate_commission_rate(
                    total_commissions, total_volume
                )

            if "trade_frequency" in metrics:
                if trades:
                    first_date = min(t.trade_date for t in trades)
                    last_date = max(t.trade_date for t in trades)
                    days = (last_date - first_date).days + 1
                    results["trade_frequency"] = (
                        Decimal(len(trades)) / Decimal(days) if days > 0 else Decimal("0")
                    )
                else:
                    results["trade_frequency"] = Decimal("0")

            if "avg_win" in metrics:
                wins = [t.fifo_pnl_realized for t in trades if t.fifo_pnl_realized > 0]
                results["avg_win"] = sum(wins, Decimal("0")) / len(wins) if wins else Decimal("0")

            if "avg_loss" in metrics:
                losses = [abs(t.fifo_pnl_realized) for t in trades if t.fifo_pnl_realized < 0]
                results["avg_loss"] = (
                    sum(losses, Decimal("0")) / len(losses) if losses else Decimal("0")
                )

            return results

        metrics1 = calculate_metrics(account1)
        metrics2 = calculate_metrics(account2)

        # Build comparison
        comparison = {}
        for metric in metrics:
            if metric in metrics1 and metric in metrics2:
                val1 = metrics1[metric]
                val2 = metrics2[metric]

                # Calculate percentage change
                if val1 != 0:
                    pct_change = ((val2 - val1) / abs(val1)) * 100
                else:
                    pct_change = (
                        Decimal("100")
                        if val2 > 0
                        else Decimal("-100")
                        if val2 < 0
                        else Decimal("0")
                    )

                comparison[metric] = {
                    "period1_value": str(val1),
                    "period2_value": str(val2),
                    "absolute_change": str(val2 - val1),
                    "percentage_change": str(pct_change),
                    "improved": (val2 > val1 if metric != "commission_rate" else val2 < val1),
                }

        result = {
            "period1": {
                "start": str(from_date1),
                "end": str(to_date1),
                "trade_count": len(account1.trades),
                "position_count": len(account1.positions),
            },
            "period2": {
                "start": str(from_date2),
                "end": str(to_date2),
                "trade_count": len(account2.trades),
                "position_count": len(account2.positions),
            },
            "comparison": comparison,
            "summary": {
                "metrics_improved": sum(1 for m in comparison.values() if m["improved"]),
                "metrics_declined": sum(1 for m in comparison.values() if not m["improved"]),
                "total_metrics": len(comparison),
            },
        }

        return json.dumps(result, indent=2, default=str)


__all__ = ["register_composable_data_tools"]
