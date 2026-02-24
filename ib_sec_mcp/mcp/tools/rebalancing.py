"""Portfolio Rebalancing Tools

Calculate rebalancing trades and simulate rebalancing outcomes.
"""

import json
from decimal import ROUND_DOWN, Decimal

from fastmcp import Context, FastMCP

from ib_sec_mcp.mcp.exceptions import ValidationError
from ib_sec_mcp.mcp.tools.composable_data import _parse_account_by_index
from ib_sec_mcp.mcp.tools.ib_portfolio import _get_or_fetch_data
from ib_sec_mcp.utils.logger import get_logger

logger = get_logger(__name__)

# Estimated commission rates per asset class
COMMISSION_RATES: dict[str, Decimal] = {
    "STK": Decimal("0.005"),  # $0.005 per share (IB US stock)
    "BOND": Decimal("0.001"),  # 0.1% of face value
    "OPT": Decimal("0.65"),  # $0.65 per contract
    "FUT": Decimal("2.25"),  # $2.25 per contract
    "CASH": Decimal("0.00002"),  # 0.002% of trade value (forex)
}

# Default commission rate for unknown asset classes
DEFAULT_COMMISSION_RATE = Decimal("0.001")


def _estimate_commission(
    symbol: str,
    asset_class: str,
    trade_value: Decimal,
    quantity: Decimal,
) -> Decimal:
    """Estimate trading commission for a rebalancing trade.

    Args:
        symbol: Trading symbol
        asset_class: Asset class (STK, BOND, OPT, FUT, CASH)
        trade_value: Absolute trade value
        quantity: Absolute quantity to trade

    Returns:
        Estimated commission amount
    """
    rate = COMMISSION_RATES.get(asset_class, DEFAULT_COMMISSION_RATE)

    if asset_class == "STK":
        # Per-share commission with minimum
        commission = abs(quantity) * rate
        return max(commission, Decimal("1.00"))  # IB minimum
    elif asset_class in ("OPT", "FUT"):
        # Per-contract commission
        return abs(quantity) * rate
    else:
        # Percentage of trade value
        return abs(trade_value) * rate


def register_rebalancing_tools(mcp: FastMCP) -> None:
    """Register portfolio rebalancing tools"""

    @mcp.tool
    async def generate_rebalancing_trades(
        target_allocation: dict[str, float],
        start_date: str,
        end_date: str | None = None,
        total_portfolio_value: float | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Generate specific buy/sell actions to rebalance portfolio toward target allocation.

        Calculates the trades needed to move from current portfolio allocation to
        target weights. Considers current positions, mark prices, and estimated
        trading commissions.

        Args:
            target_allocation: Target allocation as {symbol: weight} where weights
                are percentages (e.g., {"AAPL": 30.0, "MSFT": 20.0, "VOO": 50.0}).
                Weights must sum to 100.
            start_date: Start date in YYYY-MM-DD format for data fetch
            end_date: End date in YYYY-MM-DD format (defaults to today)
            total_portfolio_value: Override total portfolio value for calculation.
                If not provided, uses actual portfolio value (cash + positions).
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON string with rebalancing trades including symbol, direction,
            amount, estimated shares, and commission estimates

        Raises:
            ValidationError: If target allocation is invalid

        Example:
            >>> result = await generate_rebalancing_trades(
            ...     {"AAPL": 30.0, "MSFT": 20.0, "VOO": 50.0},
            ...     "2025-01-01"
            ... )
        """
        if ctx:
            await ctx.info("Generating rebalancing trades")

        # Validate target allocation
        if not target_allocation:
            raise ValidationError("target_allocation cannot be empty")

        target_weights: dict[str, Decimal] = {}
        for symbol, weight in target_allocation.items():
            if not symbol or not symbol.strip():
                raise ValidationError("Symbol cannot be empty in target_allocation")
            w = Decimal(str(weight))
            if w < Decimal("0"):
                raise ValidationError(f"Weight for {symbol} must be non-negative, got {weight}")
            target_weights[symbol.strip().upper()] = w

        total_weight = sum(target_weights.values())
        if abs(total_weight - Decimal("100")) > Decimal("0.01"):
            raise ValidationError(f"Target allocation weights must sum to 100, got {total_weight}")

        # Fetch portfolio data
        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )
        account = _parse_account_by_index(data, from_date, to_date, account_index)

        # Calculate current portfolio value
        portfolio_value: Decimal
        if total_portfolio_value is not None:
            portfolio_value = Decimal(str(total_portfolio_value))
            if portfolio_value <= Decimal("0"):
                raise ValidationError(
                    f"total_portfolio_value must be positive, got {total_portfolio_value}"
                )
        else:
            portfolio_value = account.total_value

        if portfolio_value <= Decimal("0"):
            raise ValidationError("Portfolio value must be positive for rebalancing")

        # Build current allocation from positions
        current_positions: dict[str, dict[str, Decimal]] = {}
        for pos in account.positions:
            sym = pos.symbol.upper()
            current_positions[sym] = {
                "value": pos.position_value,
                "quantity": pos.quantity,
                "mark_price": pos.mark_price,
                "asset_class": Decimal("0"),  # placeholder
            }

        # Store asset class strings separately
        asset_classes: dict[str, str] = {}
        for pos in account.positions:
            asset_classes[pos.symbol.upper()] = pos.asset_class.value

        # Calculate current weights
        current_weights: dict[str, Decimal] = {}
        for sym, pos_data in current_positions.items():
            if portfolio_value > Decimal("0"):
                current_weights[sym] = (pos_data["value"] / portfolio_value) * Decimal("100")
            else:
                current_weights[sym] = Decimal("0")

        cash_value = account.total_cash

        # Generate trades
        trades = []
        total_commission = Decimal("0")
        total_buy_value = Decimal("0")
        total_sell_value = Decimal("0")

        all_symbols = set(target_weights.keys()) | set(current_positions.keys())

        for symbol in sorted(all_symbols):
            target_pct = target_weights.get(symbol, Decimal("0"))
            current_pct = current_weights.get(symbol, Decimal("0"))
            diff_pct = target_pct - current_pct

            target_value = portfolio_value * target_pct / Decimal("100")
            current_value = current_positions.get(symbol, {}).get("value", Decimal("0"))
            trade_value = target_value - current_value

            # Skip if trade is negligible (less than $1)
            if abs(trade_value) < Decimal("1"):
                continue

            # Determine direction
            direction = "BUY" if trade_value > Decimal("0") else "SELL"

            # Calculate shares
            mark_price = current_positions.get(symbol, {}).get("mark_price", Decimal("0"))
            estimated_shares = Decimal("0")

            if mark_price > Decimal("0"):
                estimated_shares = (abs(trade_value) / mark_price).quantize(
                    Decimal("1"), rounding=ROUND_DOWN
                )
            else:
                # No current price available (new position)
                estimated_shares = Decimal("0")

            # Estimate commission
            ac = asset_classes.get(symbol, "STK")
            commission = _estimate_commission(symbol, ac, abs(trade_value), estimated_shares)
            total_commission += commission

            if direction == "BUY":
                total_buy_value += abs(trade_value)
            else:
                total_sell_value += abs(trade_value)

            trades.append(
                {
                    "symbol": symbol,
                    "direction": direction,
                    "current_weight_pct": str(current_pct.quantize(Decimal("0.01"))),
                    "target_weight_pct": str(target_pct.quantize(Decimal("0.01"))),
                    "weight_change_pct": str(diff_pct.quantize(Decimal("0.01"))),
                    "current_value": str(current_value.quantize(Decimal("0.01"))),
                    "target_value": str(target_value.quantize(Decimal("0.01"))),
                    "trade_value": str(abs(trade_value).quantize(Decimal("0.01"))),
                    "estimated_shares": str(estimated_shares),
                    "mark_price": str(mark_price) if mark_price > Decimal("0") else "N/A",
                    "estimated_commission": str(commission.quantize(Decimal("0.01"))),
                }
            )

        result = {
            "portfolio_summary": {
                "total_value": str(portfolio_value.quantize(Decimal("0.01"))),
                "cash": str(cash_value.quantize(Decimal("0.01"))),
                "positions_value": str(account.total_position_value.quantize(Decimal("0.01"))),
                "position_count": len(account.positions),
                "date_range": {"from": str(from_date), "to": str(to_date)},
            },
            "rebalancing_trades": trades,
            "trade_summary": {
                "total_trades": len(trades),
                "total_buy_value": str(total_buy_value.quantize(Decimal("0.01"))),
                "total_sell_value": str(total_sell_value.quantize(Decimal("0.01"))),
                "total_estimated_commission": str(total_commission.quantize(Decimal("0.01"))),
                "net_cash_flow": str(
                    (total_sell_value - total_buy_value).quantize(Decimal("0.01"))
                ),
            },
        }

        return json.dumps(result, indent=2)

    @mcp.tool
    async def simulate_rebalancing(
        target_allocation: dict[str, float],
        start_date: str,
        end_date: str | None = None,
        total_portfolio_value: float | None = None,
        account_index: int = 0,
        use_cache: bool = True,
        ctx: Context | None = None,
    ) -> str:
        """
        Simulate rebalancing without executing trades (dry run).

        Shows the expected new allocation, estimated costs (commissions),
        and tax impact from selling positions with gains/losses.

        Args:
            target_allocation: Target allocation as {symbol: weight} where weights
                are percentages (e.g., {"AAPL": 30.0, "MSFT": 20.0, "VOO": 50.0}).
                Weights must sum to 100.
            start_date: Start date in YYYY-MM-DD format for data fetch
            end_date: End date in YYYY-MM-DD format (defaults to today)
            total_portfolio_value: Override total portfolio value for calculation.
                If not provided, uses actual portfolio value (cash + positions).
            account_index: Account index (0 for first account, 1 for second, etc.)
            use_cache: Use cached data if available (default: True)
            ctx: MCP context for logging

        Returns:
            JSON string with simulation results including new allocation,
            commission costs, and tax impact estimates

        Raises:
            ValidationError: If target allocation is invalid

        Example:
            >>> result = await simulate_rebalancing(
            ...     {"AAPL": 30.0, "MSFT": 20.0, "VOO": 50.0},
            ...     "2025-01-01"
            ... )
        """
        if ctx:
            await ctx.info("Simulating rebalancing")

        # Validate target allocation
        if not target_allocation:
            raise ValidationError("target_allocation cannot be empty")

        target_weights: dict[str, Decimal] = {}
        for symbol, weight in target_allocation.items():
            if not symbol or not symbol.strip():
                raise ValidationError("Symbol cannot be empty in target_allocation")
            w = Decimal(str(weight))
            if w < Decimal("0"):
                raise ValidationError(f"Weight for {symbol} must be non-negative, got {weight}")
            target_weights[symbol.strip().upper()] = w

        total_weight = sum(target_weights.values())
        if abs(total_weight - Decimal("100")) > Decimal("0.01"):
            raise ValidationError(f"Target allocation weights must sum to 100, got {total_weight}")

        # Fetch portfolio data
        data, from_date, to_date = await _get_or_fetch_data(
            start_date, end_date, account_index, use_cache, ctx
        )
        account = _parse_account_by_index(data, from_date, to_date, account_index)

        # Calculate portfolio value
        portfolio_value: Decimal
        if total_portfolio_value is not None:
            portfolio_value = Decimal(str(total_portfolio_value))
            if portfolio_value <= Decimal("0"):
                raise ValidationError(
                    f"total_portfolio_value must be positive, got {total_portfolio_value}"
                )
        else:
            portfolio_value = account.total_value

        if portfolio_value <= Decimal("0"):
            raise ValidationError("Portfolio value must be positive for rebalancing")

        # Build current state
        position_map: dict[str, dict[str, Decimal | str]] = {}
        for pos in account.positions:
            sym = pos.symbol.upper()
            position_map[sym] = {
                "value": pos.position_value,
                "quantity": pos.quantity,
                "mark_price": pos.mark_price,
                "cost_basis": pos.cost_basis,
                "average_cost": pos.average_cost,
                "unrealized_pnl": pos.unrealized_pnl,
                "asset_class": pos.asset_class.value,
            }

        # Calculate current and target allocations
        current_allocation: list[dict[str, str]] = []
        new_allocation: list[dict[str, str]] = []
        tax_impact: list[dict[str, str]] = []
        total_commission = Decimal("0")
        total_taxable_gain = Decimal("0")
        total_tax_loss = Decimal("0")

        all_symbols = set(target_weights.keys()) | set(position_map.keys())

        for symbol in sorted(all_symbols):
            current_value = Decimal(str(position_map.get(symbol, {}).get("value", Decimal("0"))))
            current_pct = (
                (current_value / portfolio_value) * Decimal("100")
                if portfolio_value > Decimal("0")
                else Decimal("0")
            )

            target_pct = target_weights.get(symbol, Decimal("0"))
            target_value = portfolio_value * target_pct / Decimal("100")
            trade_value = target_value - current_value

            current_allocation.append(
                {
                    "symbol": symbol,
                    "value": str(current_value.quantize(Decimal("0.01"))),
                    "weight_pct": str(current_pct.quantize(Decimal("0.01"))),
                }
            )

            new_allocation.append(
                {
                    "symbol": symbol,
                    "value": str(target_value.quantize(Decimal("0.01"))),
                    "weight_pct": str(target_pct.quantize(Decimal("0.01"))),
                }
            )

            # Calculate commission for trades
            if abs(trade_value) >= Decimal("1"):
                mark_price = Decimal(
                    str(position_map.get(symbol, {}).get("mark_price", Decimal("0")))
                )
                quantity = Decimal("0")
                if mark_price > Decimal("0"):
                    quantity = (abs(trade_value) / mark_price).quantize(
                        Decimal("1"), rounding=ROUND_DOWN
                    )

                ac = str(position_map.get(symbol, {}).get("asset_class", "STK"))
                commission = _estimate_commission(symbol, ac, abs(trade_value), quantity)
                total_commission += commission

            # Calculate tax impact for sells
            if trade_value < Decimal("-1") and symbol in position_map:
                pos_data = position_map[symbol]
                unrealized_pnl = Decimal(str(pos_data.get("unrealized_pnl", Decimal("0"))))

                # Proportional PnL based on sell ratio
                if current_value > Decimal("0"):
                    sell_ratio = abs(trade_value) / current_value
                    # Cap at 100% (can't sell more than held)
                    sell_ratio = min(sell_ratio, Decimal("1"))
                    realized_from_sell = unrealized_pnl * sell_ratio
                else:
                    realized_from_sell = Decimal("0")

                if realized_from_sell > Decimal("0"):
                    total_taxable_gain += realized_from_sell
                else:
                    total_tax_loss += abs(realized_from_sell)

                tax_impact.append(
                    {
                        "symbol": symbol,
                        "sell_value": str(abs(trade_value).quantize(Decimal("0.01"))),
                        "estimated_realized_pnl": str(realized_from_sell.quantize(Decimal("0.01"))),
                        "type": "gain" if realized_from_sell > Decimal("0") else "loss",
                    }
                )

        # Cash position
        cash_value = account.total_cash
        cash_pct = (
            (cash_value / portfolio_value) * Decimal("100")
            if portfolio_value > Decimal("0")
            else Decimal("0")
        )
        cash_target_pct = Decimal("100") - sum(target_weights.values())

        # Build warnings
        warnings: list[str] = []
        if total_commission > portfolio_value * Decimal("0.01"):
            warnings.append("Estimated commissions exceed 1% of portfolio value")

        symbols_not_in_portfolio = [s for s in target_weights if s not in position_map]
        if symbols_not_in_portfolio:
            warnings.append(
                f"New positions to open: {', '.join(symbols_not_in_portfolio)}. "
                "Mark price unavailable; share estimates may be inaccurate."
            )

        symbols_to_close = [s for s in position_map if s not in target_weights]
        if symbols_to_close:
            warnings.append(f"Positions to fully close: {', '.join(symbols_to_close)}")

        result = {
            "simulation_summary": {
                "portfolio_value": str(portfolio_value.quantize(Decimal("0.01"))),
                "date_range": {"from": str(from_date), "to": str(to_date)},
                "is_dry_run": True,
            },
            "current_allocation": current_allocation,
            "projected_allocation": new_allocation,
            "cash_position": {
                "current_cash": str(cash_value.quantize(Decimal("0.01"))),
                "current_cash_pct": str(cash_pct.quantize(Decimal("0.01"))),
                "implied_target_cash_pct": str(cash_target_pct.quantize(Decimal("0.01"))),
            },
            "cost_analysis": {
                "total_estimated_commission": str(total_commission.quantize(Decimal("0.01"))),
                "commission_as_pct_of_portfolio": str(
                    ((total_commission / portfolio_value) * Decimal("100")).quantize(
                        Decimal("0.0001")
                    )
                ),
            },
            "tax_impact": {
                "positions_with_gains": [t for t in tax_impact if t["type"] == "gain"],
                "positions_with_losses": [t for t in tax_impact if t["type"] == "loss"],
                "total_estimated_taxable_gain": str(total_taxable_gain.quantize(Decimal("0.01"))),
                "total_estimated_tax_loss": str(total_tax_loss.quantize(Decimal("0.01"))),
                "net_tax_impact": str(
                    (total_taxable_gain - total_tax_loss).quantize(Decimal("0.01"))
                ),
            },
            "warnings": warnings,
        }

        return json.dumps(result, indent=2)


__all__ = ["register_rebalancing_tools"]
