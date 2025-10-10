"""Market Comparison Tools

Stock performance comparison and analyst consensus tools.
"""

import asyncio
import json
from typing import Optional

import numpy as np
import pandas as pd
from fastmcp import Context, FastMCP

from ib_sec_mcp.mcp.exceptions import TimeoutError as IBTimeoutError
from ib_sec_mcp.mcp.exceptions import ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.validators import (
    validate_benchmark_symbol,
    validate_period,
    validate_symbol,
)

# Timeout constants (in seconds)
DEFAULT_TIMEOUT = 30


def register_market_comparison_tools(mcp: FastMCP) -> None:
    """Register market comparison tools"""

    @mcp.tool
    async def compare_with_benchmark(
        symbol: str,
        benchmark: str = "SPY",
        period: str = "1y",
        ctx: Optional[Context] = None,
    ) -> str:
        """
        Compare stock/fund performance with benchmark

        Args:
            symbol: Stock ticker symbol to compare
            benchmark: Benchmark symbol (default: SPY for S&P 500)
            period: Time period for comparison (1mo, 3mo, 6mo, 1y, 2y, 5y, max)
            ctx: MCP context for logging

        Returns:
            JSON string with performance comparison metrics

        Raises:
            ValidationError: If inputs are invalid
            YahooFinanceError: If data fetch fails
            TimeoutError: If operation times out
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)
            benchmark = validate_benchmark_symbol(benchmark)
            period = validate_period(period)

            if ctx:
                await ctx.info(f"Comparing {symbol} vs {benchmark} for {period}")

            import yfinance as yf

            # Fetch data with timeout
            async def fetch_data():
                stock = await asyncio.to_thread(lambda: yf.Ticker(symbol).history(period=period))
                bench = await asyncio.to_thread(lambda: yf.Ticker(benchmark).history(period=period))
                return stock, bench

            stock_data, bench_data = await asyncio.wait_for(fetch_data(), timeout=DEFAULT_TIMEOUT)

            if stock_data.empty or bench_data.empty:
                raise YahooFinanceError(
                    f"No data found for {symbol} or {benchmark} for period {period}"
                )

            # Calculate returns
            stock_return = (
                (stock_data["Close"].iloc[-1] - stock_data["Close"].iloc[0])
                / stock_data["Close"].iloc[0]
                * 100
            )
            bench_return = (
                (bench_data["Close"].iloc[-1] - bench_data["Close"].iloc[0])
                / bench_data["Close"].iloc[0]
                * 100
            )

            # Calculate daily returns for correlation and beta
            stock_daily = stock_data["Close"].pct_change().dropna()
            bench_daily = bench_data["Close"].pct_change().dropna()

            # Align dates
            aligned = pd.DataFrame({"stock": stock_daily, "benchmark": bench_daily}).dropna()

            # Calculate metrics
            correlation = aligned["stock"].corr(aligned["benchmark"])
            beta = aligned["stock"].cov(aligned["benchmark"]) / aligned["benchmark"].var()

            # Calculate alpha (excess return)
            alpha = stock_return - (beta * bench_return)

            # Volatility
            stock_vol = stock_daily.std() * np.sqrt(252) * 100  # Annualized
            bench_vol = bench_daily.std() * np.sqrt(252) * 100

            # Sharpe ratio (assuming 5% risk-free rate)
            risk_free = 5.0
            stock_sharpe = (stock_return - risk_free) / stock_vol if stock_vol != 0 else 0
            bench_sharpe = (bench_return - risk_free) / bench_vol if bench_vol != 0 else 0

            result = {
                "symbol": symbol,
                "benchmark": benchmark,
                "period": period,
                "performance": {
                    "stock_return_pct": round(stock_return, 2),
                    "benchmark_return_pct": round(bench_return, 2),
                    "outperformance_pct": round(stock_return - bench_return, 2),
                    "stock_volatility_pct": round(stock_vol, 2),
                    "benchmark_volatility_pct": round(bench_vol, 2),
                },
                "risk_metrics": {
                    "beta": round(beta, 3),
                    "alpha_pct": round(alpha, 2),
                    "correlation": round(correlation, 3),
                    "stock_sharpe_ratio": round(stock_sharpe, 3),
                    "benchmark_sharpe_ratio": round(bench_sharpe, 3),
                },
                "interpretation": {
                    "beta": (
                        "More volatile than benchmark"
                        if beta > 1
                        else "Less volatile than benchmark"
                    ),
                    "alpha": (
                        "Outperformed benchmark (positive alpha)"
                        if alpha > 0
                        else "Underperformed benchmark (negative alpha)"
                    ),
                    "sharpe": (
                        "Better risk-adjusted returns"
                        if stock_sharpe > bench_sharpe
                        else "Worse risk-adjusted returns"
                    ),
                },
            }

            return json.dumps(result, indent=2)

        except (ValidationError, YahooFinanceError, IBTimeoutError):
            raise
        except Exception as e:
            if ctx:
                await ctx.error(f"Unexpected error in compare_with_benchmark: {str(e)}")
            raise YahooFinanceError(f"Unexpected error: {str(e)}") from e

    @mcp.tool
    async def get_analyst_consensus(
        symbol: str,
        ctx: Optional[Context] = None,
    ) -> str:
        """
        Get analyst consensus and recommendations

        Args:
            symbol: Stock ticker symbol
            ctx: MCP context for logging

        Returns:
            JSON string with analyst ratings, target prices, and earnings estimates

        Raises:
            ValidationError: If symbol is invalid
            YahooFinanceError: If data fetch fails
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)

            if ctx:
                await ctx.info(f"Fetching analyst consensus for {symbol}")

            import yfinance as yf

            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Get recommendations
            recommendations = ticker.recommendations
            rec_summary = {}

            if recommendations is not None and not recommendations.empty:
                latest = recommendations.tail(1).iloc[0]
                strong_buy = int(latest.get("strongBuy", 0))
                buy = int(latest.get("buy", 0))
                hold = int(latest.get("hold", 0))
                sell = int(latest.get("sell", 0))
                strong_sell = int(latest.get("strongSell", 0))

                rec_summary = {
                    "period": str(latest.name) if hasattr(latest.name, "__str__") else "current",
                    "strong_buy": strong_buy,
                    "buy": buy,
                    "hold": hold,
                    "sell": sell,
                    "strong_sell": strong_sell,
                }

                total = strong_buy + buy + hold + sell + strong_sell
                if total > 0:
                    rec_summary["total_analysts"] = total
                    rec_summary["consensus"] = (
                        "Strong Buy"
                        if strong_buy > total * 0.5
                        else (
                            "Buy"
                            if (strong_buy + buy) > total * 0.5
                            else "Hold"
                            if hold > total * 0.3
                            else "Sell"
                        )
                    )

            # Target price
            target_price = {
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "target_mean": info.get("targetMeanPrice"),
                "target_high": info.get("targetHighPrice"),
                "target_low": info.get("targetLowPrice"),
                "target_median": info.get("targetMedianPrice"),
            }

            if target_price["current_price"] and target_price["target_mean"]:
                upside = (
                    (target_price["target_mean"] - target_price["current_price"])
                    / target_price["current_price"]
                    * 100
                )
                target_price["upside_potential_pct"] = round(upside, 2)

            # Earnings estimates (from calendar)
            calendar = ticker.calendar
            earnings_estimates = {}

            if calendar and isinstance(calendar, dict):
                earnings_estimates = {
                    "earnings_date": str(calendar.get("Earnings Date", ["N/A"])[0]),
                    "earnings_average": calendar.get("Earnings Average"),
                    "earnings_high": calendar.get("Earnings High"),
                    "earnings_low": calendar.get("Earnings Low"),
                    "revenue_average": calendar.get("Revenue Average"),
                    "revenue_high": calendar.get("Revenue High"),
                    "revenue_low": calendar.get("Revenue Low"),
                }

            result = {
                "symbol": symbol,
                "analyst_recommendations": rec_summary,
                "target_price": target_price,
                "earnings_estimates": earnings_estimates,
                "analyst_count": info.get("numberOfAnalystOpinions"),
            }

            return json.dumps(result, indent=2, default=str)

        except (ValidationError, YahooFinanceError, IBTimeoutError):
            raise
        except Exception as e:
            if ctx:
                await ctx.error(f"Unexpected error in get_analyst_consensus: {str(e)}")
            raise YahooFinanceError(f"Unexpected error: {str(e)}") from e


__all__ = ["register_market_comparison_tools"]
