"""Portfolio Analytics Tools

Advanced portfolio performance metrics and correlation analysis.
"""

import asyncio
import json
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from fastmcp import Context, FastMCP

from ib_sec_mcp.core.parsers import CSVParser, XMLParser, detect_format
from ib_sec_mcp.mcp.exceptions import FileOperationError, ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.exceptions import TimeoutError as IBTimeoutError
from ib_sec_mcp.mcp.validators import (
    validate_benchmark_symbol,
    validate_file_path,
    validate_period,
    validate_risk_free_rate,
)


def register_portfolio_analytics_tools(mcp: FastMCP) -> None:
    """Register portfolio analytics tools"""

    @mcp.tool
    async def calculate_portfolio_metrics(
        csv_path: str,
        benchmark: str = "SPY",
        risk_free_rate: float = 0.05,
        period: str = "1y",
        ctx: Context | None = None,
    ) -> str:
        """
        Calculate advanced portfolio performance metrics

        Args:
            csv_path: Path to IB Flex Query CSV file
            benchmark: Benchmark symbol for comparison (default: SPY)
            risk_free_rate: Risk-free rate as decimal (default: 0.05 for 5%)
            period: Time period for analysis (1mo, 3mo, 6mo, 1y, 2y, 5y)
            ctx: MCP context for logging

        Returns:
            JSON string with portfolio metrics

        Raises:
            ValidationError: If inputs are invalid
            FileOperationError: If file operations fail
            YahooFinanceError: If data fetch fails
        """
        try:
            # Validate inputs
            csv_path_validated = validate_file_path(csv_path)
            benchmark = validate_benchmark_symbol(benchmark)
            risk_free_rate = validate_risk_free_rate(risk_free_rate)
            period = validate_period(period)

            if ctx:
                await ctx.info(f"Calculating portfolio metrics for {csv_path}")

            # Read file content
            with open(csv_path_validated) as f:
                file_content = f.read()

            # Detect format and extract dates from filename
            format_type = detect_format(file_content)
            filename = Path(csv_path_validated).stem
            parts = filename.split("_")
            if len(parts) >= 3:
                try:
                    from_date = datetime.strptime(parts[-2], "%Y-%m-%d").date()
                    to_date = datetime.strptime(parts[-1], "%Y-%m-%d").date()
                except ValueError:
                    from_date = date(date.today().year, 1, 1)
                    to_date = date.today()
            else:
                from_date = date(date.today().year, 1, 1)
                to_date = date.today()

            # Parse using static methods
            if format_type == "csv":
                account = await asyncio.to_thread(
                    CSVParser.to_account, file_content, from_date, to_date
                )
            else:
                account = await asyncio.to_thread(
                    XMLParser.to_account, file_content, from_date, to_date
                )

            # Get portfolio value history (simplified - use current positions)
            positions = account.positions
            if not positions:
                raise ValidationError("No positions found in portfolio")

            # Fetch historical data for all positions
            import yfinance as yf

            async def fetch_position_history(symbol: str):
                try:
                    ticker = yf.Ticker(symbol)
                    hist = await asyncio.to_thread(lambda: ticker.history(period=period))
                    return symbol, hist
                except Exception:
                    return symbol, None

            # Fetch all position histories
            tasks = [fetch_position_history(pos.symbol) for pos in positions]
            histories = await asyncio.gather(*tasks)

            # Calculate portfolio returns (weighted average)
            total_value = sum(float(pos.position_value) for pos in positions)
            portfolio_returns = []

            for pos in positions:
                symbol = pos.symbol
                weight = float(pos.position_value) / total_value

                # Find history for this symbol
                hist = next((h for s, h in histories if s == symbol), None)
                if hist is not None and not hist.empty:
                    returns = hist["Close"].pct_change().dropna()
                    portfolio_returns.append(returns * weight)

            if not portfolio_returns:
                raise ValidationError("Could not fetch historical data for any position")

            # Combine weighted returns
            portfolio_return_series = sum(portfolio_returns)

            # Calculate metrics
            total_return = (1 + portfolio_return_series).prod() - 1
            annualized_return = (
                (1 + total_return) ** (252 / len(portfolio_return_series)) - 1
            ) * 100

            volatility = portfolio_return_series.std() * np.sqrt(252) * 100  # Annualized

            # Sharpe Ratio
            sharpe = (
                (annualized_return / 100 - risk_free_rate) / (volatility / 100)
                if volatility != 0
                else 0
            )

            # Sortino Ratio (downside deviation)
            downside_returns = portfolio_return_series[portfolio_return_series < 0]
            downside_std = downside_returns.std() * np.sqrt(252)
            sortino = (
                (annualized_return / 100 - risk_free_rate) / downside_std
                if downside_std != 0
                else 0
            )

            # Maximum Drawdown
            cumulative = (1 + portfolio_return_series).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min() * 100

            # Calmar Ratio
            calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

            # Fetch benchmark for comparison
            bench_ticker = yf.Ticker(benchmark)
            bench_hist = await asyncio.to_thread(lambda: bench_ticker.history(period=period))
            bench_returns = bench_hist["Close"].pct_change().dropna()

            # Information Ratio
            aligned = pd.DataFrame(
                {"portfolio": portfolio_return_series, "benchmark": bench_returns}
            ).dropna()

            excess_returns = aligned["portfolio"] - aligned["benchmark"]
            tracking_error = excess_returns.std() * np.sqrt(252)
            information_ratio = (
                excess_returns.mean() * 252 / tracking_error if tracking_error != 0 else 0
            )

            # Beta and Treynor Ratio
            beta = aligned["portfolio"].cov(aligned["benchmark"]) / aligned["benchmark"].var()
            treynor = (annualized_return / 100 - risk_free_rate) / beta if beta != 0 else 0

            result = {
                "portfolio_summary": {
                    "total_value": round(total_value, 2),
                    "num_positions": len(positions),
                    "period": period,
                    "benchmark": benchmark,
                },
                "return_metrics": {
                    "total_return_pct": round(total_return * 100, 2),
                    "annualized_return_pct": round(annualized_return, 2),
                    "annualized_volatility_pct": round(volatility, 2),
                },
                "risk_adjusted_metrics": {
                    "sharpe_ratio": round(sharpe, 3),
                    "sortino_ratio": round(sortino, 3),
                    "calmar_ratio": round(calmar, 3),
                    "treynor_ratio": round(treynor, 3),
                    "information_ratio": round(information_ratio, 3),
                },
                "risk_metrics": {
                    "maximum_drawdown_pct": round(max_drawdown, 2),
                    "downside_deviation_pct": round(downside_std * 100, 2),
                    "beta": round(beta, 3),
                    "tracking_error_pct": round(tracking_error * 100, 2),
                },
                "interpretation": {
                    "sharpe": "Good" if sharpe > 1 else "Moderate" if sharpe > 0.5 else "Poor",
                    "sortino": "Good" if sortino > 1.5 else "Moderate" if sortino > 1 else "Poor",
                    "max_drawdown": (
                        "Low risk"
                        if max_drawdown > -10
                        else "Moderate risk"
                        if max_drawdown > -20
                        else "High risk"
                    ),
                },
            }

            return json.dumps(result, indent=2)

        except (ValidationError, FileOperationError, YahooFinanceError, IBTimeoutError):
            raise
        except Exception as e:
            if ctx:
                await ctx.error(f"Unexpected error in calculate_portfolio_metrics: {str(e)}")
            raise FileOperationError(f"Unexpected error: {str(e)}") from e

    @mcp.tool
    async def analyze_portfolio_correlation(
        csv_path: str,
        period: str = "1y",
        ctx: Context | None = None,
    ) -> str:
        """
        Analyze correlation between portfolio positions

        Args:
            csv_path: Path to IB Flex Query CSV file
            period: Time period for correlation analysis (1mo, 3mo, 6mo, 1y, 2y, 5y)
            ctx: MCP context for logging

        Returns:
            JSON string with correlation matrix and diversification analysis

        Raises:
            ValidationError: If inputs are invalid
            FileOperationError: If file operations fail
            YahooFinanceError: If data fetch fails
        """
        try:
            # Validate inputs
            csv_path_validated = validate_file_path(csv_path)
            period = validate_period(period)

            if ctx:
                await ctx.info(f"Analyzing portfolio correlation for {period}")

            # Read file content
            with open(csv_path_validated) as f:
                file_content = f.read()

            # Detect format and extract dates from filename
            format_type = detect_format(file_content)
            filename = Path(csv_path_validated).stem
            parts = filename.split("_")
            if len(parts) >= 3:
                try:
                    from_date = datetime.strptime(parts[-2], "%Y-%m-%d").date()
                    to_date = datetime.strptime(parts[-1], "%Y-%m-%d").date()
                except ValueError:
                    from_date = date(date.today().year, 1, 1)
                    to_date = date.today()
            else:
                from_date = date(date.today().year, 1, 1)
                to_date = date.today()

            # Parse using static methods
            if format_type == "csv":
                account = await asyncio.to_thread(
                    CSVParser.to_account, file_content, from_date, to_date
                )
            else:
                account = await asyncio.to_thread(
                    XMLParser.to_account, file_content, from_date, to_date
                )

            # Get positions
            positions = account.positions
            if not positions:
                raise ValidationError("No positions found in portfolio")

            if len(positions) < 2:
                return json.dumps(
                    {
                        "message": "Portfolio has only one position. Correlation analysis requires at least 2 positions.",
                        "num_positions": len(positions),
                    }
                )

            # Fetch historical data for all positions
            import yfinance as yf

            async def fetch_returns(symbol: str):
                try:
                    ticker = yf.Ticker(symbol)
                    hist = await asyncio.to_thread(lambda: ticker.history(period=period))
                    if not hist.empty:
                        returns = hist["Close"].pct_change().dropna()
                        return symbol, returns
                    return symbol, None
                except Exception:
                    return symbol, None

            tasks = [fetch_returns(pos.symbol) for pos in positions]
            results = await asyncio.gather(*tasks)

            # Build returns dataframe
            returns_dict = {symbol: returns for symbol, returns in results if returns is not None}

            if len(returns_dict) < 2:
                raise YahooFinanceError(
                    "Could not fetch sufficient historical data for correlation analysis"
                )

            returns_df = pd.DataFrame(returns_dict).dropna()

            # Calculate correlation matrix
            corr_matrix = returns_df.corr()

            # Convert to dict for JSON
            corr_dict = {}
            for symbol1 in corr_matrix.index:
                corr_dict[symbol1] = {}
                for symbol2 in corr_matrix.columns:
                    corr_dict[symbol1][symbol2] = round(corr_matrix.loc[symbol1, symbol2], 3)

            # Identify high correlation pairs (>0.7, excluding self)
            high_corr_pairs = []
            for i, symbol1 in enumerate(corr_matrix.index):
                for j, symbol2 in enumerate(corr_matrix.columns):
                    if i < j:  # Avoid duplicates
                        corr_value = corr_matrix.loc[symbol1, symbol2]
                        if abs(corr_value) > 0.7:
                            high_corr_pairs.append(
                                {
                                    "symbol1": symbol1,
                                    "symbol2": symbol2,
                                    "correlation": round(corr_value, 3),
                                    "interpretation": (
                                        "High positive" if corr_value > 0.7 else "High negative"
                                    ),
                                }
                            )

            # Calculate portfolio beta (weighted average vs SPY)
            spy = yf.Ticker("SPY")
            spy_hist = await asyncio.to_thread(lambda: spy.history(period=period))
            spy_returns = spy_hist["Close"].pct_change().dropna()

            # Calculate weights
            total_value = sum(float(pos.position_value) for pos in positions)
            weights = {pos.symbol: float(pos.position_value) / total_value for pos in positions}

            # Portfolio beta
            portfolio_returns = sum(
                returns_df[symbol] * weights[symbol]
                for symbol in returns_df.columns
                if symbol in weights
            )

            aligned = pd.DataFrame({"portfolio": portfolio_returns, "spy": spy_returns}).dropna()

            portfolio_beta = aligned["portfolio"].cov(aligned["spy"]) / aligned["spy"].var()

            # Diversification score (inverse of average correlation)
            avg_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean()
            diversification_score = 1 - avg_corr  # Higher is better

            result = {
                "summary": {
                    "num_positions": len(positions),
                    "period": period,
                    "portfolio_beta": round(portfolio_beta, 3),
                    "average_correlation": round(avg_corr, 3),
                    "diversification_score": round(diversification_score, 3),
                },
                "correlation_matrix": corr_dict,
                "high_correlation_pairs": high_corr_pairs,
                "position_weights": {
                    symbol: round(weight * 100, 2) for symbol, weight in weights.items()
                },
                "interpretation": {
                    "diversification": (
                        "Well diversified"
                        if diversification_score > 0.7
                        else (
                            "Moderately diversified"
                            if diversification_score > 0.4
                            else "Poorly diversified"
                        )
                    ),
                    "beta": (
                        "More volatile than market"
                        if portfolio_beta > 1.1
                        else (
                            "Less volatile than market"
                            if portfolio_beta < 0.9
                            else "Market-like volatility"
                        )
                    ),
                    "avg_correlation": (
                        "Low correlation (good)"
                        if avg_corr < 0.3
                        else (
                            "Moderate correlation"
                            if avg_corr < 0.6
                            else "High correlation (poor diversification)"
                        )
                    ),
                },
            }

            return json.dumps(result, indent=2)

        except (ValidationError, FileOperationError, YahooFinanceError, IBTimeoutError):
            raise
        except Exception as e:
            if ctx:
                await ctx.error(f"Unexpected error in analyze_portfolio_correlation: {str(e)}")
            raise FileOperationError(f"Unexpected error: {str(e)}") from e


__all__ = ["register_portfolio_analytics_tools"]
