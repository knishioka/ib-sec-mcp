"""ETF Comparison Tools

Compare multiple ETFs with dividend-adjusted performance for investment strategy.
"""

import asyncio
import json
from datetime import datetime

import numpy as np
import pandas as pd
from fastmcp import Context, FastMCP

from ib_sec_mcp.mcp.exceptions import IBTimeoutError, ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.validators import validate_period, validate_symbol

# Timeout constants (in seconds)
DEFAULT_TIMEOUT = 30


def register_etf_comparison_tools(mcp: FastMCP) -> None:
    """Register ETF comparison tools"""

    @mcp.tool
    async def compare_etf_performance(
        symbols: str,
        period: str = "1y",
        ctx: Context | None = None,
    ) -> str:
        """
        Compare multiple ETFs with dividend-adjusted performance for investment strategy

        投資戦略立案のために複数ETFを配当込みで比較

        Args:
            symbols: Comma-separated symbols (e.g., "IDTL,TLT,VWRA,CSPX,VOO")
            period: Time period - valid values: 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, max
            ctx: MCP context for logging

        Returns:
            JSON string with comprehensive comparison including:
            - Total returns (dividend-adjusted)
            - Annualized returns (CAGR)
            - Volatility & Sharpe ratio
            - Dividend yields
            - Expense ratios
            - Max drawdown
            - Correlation matrix
            - Investment insights

        Raises:
            ValidationError: If input validation fails
            YahooFinanceError: If Yahoo Finance API call fails
            IBTimeoutError: If operation times out
        """
        try:
            # Validate period
            period = validate_period(period)

            # Parse and validate symbols
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            if not symbol_list:
                raise ValidationError("At least one symbol is required")

            if len(symbol_list) > 10:
                raise ValidationError("Maximum 10 symbols allowed for comparison")

            # Validate each symbol
            for symbol in symbol_list:
                validate_symbol(symbol)

            if ctx:
                await ctx.info(
                    f"Comparing {len(symbol_list)} ETFs: {', '.join(symbol_list)}",
                    extra={
                        "symbols": symbol_list,
                        "period": period,
                    },
                )

            # Fetch data for all symbols in parallel
            import yfinance as yf

            async def fetch_etf_data(symbol: str) -> tuple[str, dict | None]:
                """Fetch comprehensive ETF data"""
                try:
                    ticker = yf.Ticker(symbol)

                    # Fetch historical data with timeout
                    hist_task = asyncio.to_thread(
                        lambda: ticker.history(period=period, auto_adjust=True)
                    )
                    info_task = asyncio.to_thread(lambda: ticker.info)

                    hist, info = await asyncio.gather(
                        asyncio.wait_for(hist_task, timeout=DEFAULT_TIMEOUT),
                        asyncio.wait_for(info_task, timeout=DEFAULT_TIMEOUT),
                    )

                    if hist.empty:
                        if ctx:
                            await ctx.warning(f"No data found for {symbol}")
                        return symbol, None

                    # Calculate returns (already dividend-adjusted with auto_adjust=True)
                    returns = hist["Close"].pct_change().dropna()

                    # Calculate metrics
                    total_return = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100

                    # Annualized return (CAGR)
                    years = len(hist) / 252  # Approximate trading days
                    if years > 0:
                        annualized_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100
                    else:
                        annualized_return = 0

                    # Volatility (annualized)
                    volatility = returns.std() * np.sqrt(252) * 100

                    # Sharpe Ratio (assuming 5% risk-free rate)
                    risk_free_rate = 0.05
                    sharpe_ratio = (
                        (annualized_return / 100 - risk_free_rate) / (volatility / 100)
                        if volatility != 0
                        else 0
                    )

                    # Sortino Ratio
                    downside_returns = returns[returns < 0]
                    downside_std = downside_returns.std() * np.sqrt(252)
                    sortino_ratio = (
                        (annualized_return / 100 - risk_free_rate) / downside_std
                        if downside_std != 0
                        else 0
                    )

                    # Maximum Drawdown
                    cumulative = (1 + returns).cumprod()
                    running_max = cumulative.expanding().max()
                    drawdown = (cumulative - running_max) / running_max
                    max_drawdown = drawdown.min() * 100

                    # Calmar Ratio
                    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

                    # Best/Worst month
                    monthly_returns = hist["Close"].resample("ME").last().pct_change().dropna()
                    best_month = monthly_returns.max() * 100 if not monthly_returns.empty else 0
                    worst_month = monthly_returns.min() * 100 if not monthly_returns.empty else 0

                    # Year-to-date return
                    ytd_start = hist[hist.index >= f"{datetime.now().year}-01-01"]
                    if not ytd_start.empty:
                        ytd_return = (
                            ytd_start["Close"].iloc[-1] / ytd_start["Close"].iloc[0] - 1
                        ) * 100
                    else:
                        ytd_return = 0

                    # Get SPY for beta calculation
                    spy = yf.Ticker("SPY")
                    spy_hist = await asyncio.to_thread(
                        lambda: spy.history(period=period, auto_adjust=True)
                    )
                    spy_returns = spy_hist["Close"].pct_change().dropna()

                    # Align data and calculate beta
                    aligned = pd.DataFrame({"etf": returns, "spy": spy_returns}).dropna()
                    beta = (
                        aligned["etf"].cov(aligned["spy"]) / aligned["spy"].var()
                        if not aligned.empty
                        else 1.0
                    )

                    return symbol, {
                        "returns": {
                            "total_return_pct": round(total_return, 2),
                            "annualized_return_pct": round(annualized_return, 2),
                            "ytd_return_pct": round(ytd_return, 2),
                            "best_month_pct": round(best_month, 2),
                            "worst_month_pct": round(worst_month, 2),
                        },
                        "risk": {
                            "volatility_pct": round(volatility, 2),
                            "sharpe_ratio": round(sharpe_ratio, 3),
                            "sortino_ratio": round(sortino_ratio, 3),
                            "max_drawdown_pct": round(max_drawdown, 2),
                            "calmar_ratio": round(calmar_ratio, 3),
                        },
                        "dividends": {
                            "yield_pct": info.get("dividendYield", 0) * 100
                            if info.get("dividendYield")
                            else 0,
                            "annual_dividend": info.get("dividendRate", 0),
                            "trailing_annual_dividend_yield": info.get(
                                "trailingAnnualDividendYield", 0
                            )
                            * 100
                            if info.get("trailingAnnualDividendYield")
                            else 0,
                        },
                        "costs": {
                            "expense_ratio_pct": info.get("annualReportExpenseRatio", 0) * 100
                            if info.get("annualReportExpenseRatio")
                            else 0,
                            "estimated_annual_cost_per_10k": round(
                                info.get("annualReportExpenseRatio", 0) * 10000, 2
                            )
                            if info.get("annualReportExpenseRatio")
                            else 0,
                        },
                        "market_metrics": {
                            "beta_vs_spy": round(beta, 3),
                            "current_price": info.get("currentPrice")
                            or info.get("regularMarketPrice", 0),
                            "52w_high": info.get("fiftyTwoWeekHigh", 0),
                            "52w_low": info.get("fiftyTwoWeekLow", 0),
                        },
                        "info": {
                            "long_name": info.get("longName", symbol),
                            "category": info.get("category", "N/A"),
                        },
                        "_returns_series": returns,  # Keep for correlation calculation
                    }

                except TimeoutError:
                    if ctx:
                        await ctx.error(f"Timeout fetching data for {symbol}")
                    return symbol, None
                except Exception as e:
                    if ctx:
                        await ctx.error(f"Error fetching {symbol}: {str(e)}")
                    return symbol, None

            # Fetch all ETF data in parallel
            results = await asyncio.gather(*[fetch_etf_data(s) for s in symbol_list])

            # Filter out failed fetches
            performance_data = {symbol: data for symbol, data in results if data is not None}

            if not performance_data:
                raise YahooFinanceError("Could not fetch data for any symbol")

            if len(performance_data) < len(symbol_list):
                failed_symbols = set(symbol_list) - set(performance_data.keys())
                if ctx:
                    await ctx.warning(f"Failed to fetch data for: {', '.join(failed_symbols)}")

            # Calculate correlation matrix
            returns_dict = {
                symbol: data["_returns_series"] for symbol, data in performance_data.items()
            }
            # Use outer join to align different trading calendars, then drop rows with any NaN
            returns_df = pd.DataFrame(returns_dict)

            # Check if we have enough overlapping data points
            overlapping_rows = returns_df.dropna()
            if len(overlapping_rows) < 20:  # Need at least 20 common trading days
                # Fall back to pairwise correlation with maximum available data
                corr_matrix = returns_df.corr(method="pearson", min_periods=20)
            else:
                # Use only rows with data for all symbols
                returns_df = overlapping_rows
                corr_matrix = returns_df.corr()

            # Convert correlation matrix to dict
            corr_dict = {}
            for symbol1 in corr_matrix.index:
                corr_dict[symbol1] = {}
                for symbol2 in corr_matrix.columns:
                    corr_dict[symbol1][symbol2] = round(corr_matrix.loc[symbol1, symbol2], 3)

            # Find high correlation pairs
            high_corr_pairs = []
            for i, symbol1 in enumerate(corr_matrix.index):
                for j, symbol2 in enumerate(corr_matrix.columns):
                    if i < j:
                        corr_value = corr_matrix.loc[symbol1, symbol2]
                        if abs(corr_value) > 0.7:
                            high_corr_pairs.append(
                                {
                                    "symbol1": symbol1,
                                    "symbol2": symbol2,
                                    "correlation": round(corr_value, 3),
                                }
                            )

            # Remove _returns_series from output (was only for correlation)
            for data in performance_data.values():
                data.pop("_returns_series", None)

            # Generate insights
            best_performer = max(
                performance_data.items(),
                key=lambda x: x[1]["returns"]["total_return_pct"],
            )
            lowest_volatility = min(
                performance_data.items(),
                key=lambda x: x[1]["risk"]["volatility_pct"],
            )
            best_risk_adjusted = max(
                performance_data.items(),
                key=lambda x: x[1]["risk"]["sharpe_ratio"],
            )
            highest_dividend = max(
                performance_data.items(),
                key=lambda x: x[1]["dividends"]["yield_pct"],
            )

            # Build recommendations
            recommendations = []
            for symbol, data in performance_data.items():
                sharpe = data["risk"]["sharpe_ratio"]
                div_yield = data["dividends"]["yield_pct"]
                volatility = data["risk"]["volatility_pct"]
                total_return = data["returns"]["total_return_pct"]

                if div_yield > 3 and volatility < 10:
                    recommendations.append(
                        f"{symbol}: Best for income-focused investors "
                        f"({div_yield:.1f}% yield, {volatility:.1f}% volatility)"
                    )
                elif total_return > 10 and sharpe > 1:
                    recommendations.append(
                        f"{symbol}: Best for growth-focused investors "
                        f"({total_return:.1f}% return, {sharpe:.2f} Sharpe ratio)"
                    )
                elif volatility < 8:
                    recommendations.append(
                        f"{symbol}: Best for conservative investors ({volatility:.1f}% volatility)"
                    )

            # Add correlation warnings
            for pair in high_corr_pairs:
                recommendations.append(
                    f"{pair['symbol1']} and {pair['symbol2']}: High correlation "
                    f"({pair['correlation']:.2f}) - consider diversifying with one or the other"
                )

            result = {
                "comparison_summary": {
                    "symbols": list(performance_data.keys()),
                    "period": period,
                    "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                    "num_symbols_analyzed": len(performance_data),
                    "best_performer": {
                        "symbol": best_performer[0],
                        "total_return": best_performer[1]["returns"]["total_return_pct"],
                        "annualized_return": best_performer[1]["returns"]["annualized_return_pct"],
                    },
                    "lowest_volatility": {
                        "symbol": lowest_volatility[0],
                        "volatility": lowest_volatility[1]["risk"]["volatility_pct"],
                    },
                    "best_risk_adjusted": {
                        "symbol": best_risk_adjusted[0],
                        "sharpe_ratio": best_risk_adjusted[1]["risk"]["sharpe_ratio"],
                    },
                    "highest_dividend": {
                        "symbol": highest_dividend[0],
                        "dividend_yield": highest_dividend[1]["dividends"]["yield_pct"],
                    },
                },
                "performance_comparison": performance_data,
                "correlation_analysis": {
                    "matrix": corr_dict,
                    "high_correlation_pairs": high_corr_pairs,
                },
                "investment_insights": {
                    "best_total_return": f"{best_performer[0]} "
                    f"({best_performer[1]['returns']['total_return_pct']:.2f}%)",
                    "best_risk_adjusted": f"{best_risk_adjusted[0]} "
                    f"(Sharpe: {best_risk_adjusted[1]['risk']['sharpe_ratio']:.2f})",
                    "lowest_volatility": f"{lowest_volatility[0]} "
                    f"({lowest_volatility[1]['risk']['volatility_pct']:.2f}%)",
                    "highest_dividend": f"{highest_dividend[0]} "
                    f"({highest_dividend[1]['dividends']['yield_pct']:.2f}%)",
                    "recommendations": recommendations
                    if recommendations
                    else [
                        "All ETFs show similar characteristics - consider diversification strategy"
                    ],
                },
            }

            if ctx:
                await ctx.info(
                    f"Successfully compared {len(performance_data)} ETFs",
                    extra={
                        "symbols": list(performance_data.keys()),
                        "best_performer": best_performer[0],
                    },
                )

            return json.dumps(result, indent=2, default=str)

        except (ValidationError, YahooFinanceError, IBTimeoutError):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            # Catch any unexpected errors
            if ctx:
                await ctx.error(
                    f"Unexpected error: {str(e)}",
                    extra={"error_type": type(e).__name__},
                )
            raise YahooFinanceError(f"Unexpected error while comparing ETFs: {str(e)}") from e


__all__ = ["register_etf_comparison_tools"]
