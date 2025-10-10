"""Stock Data Tools

Yahoo Finance stock data retrieval tools for market data and company information.
"""

import asyncio
import json

from fastmcp import Context, FastMCP

from ib_sec_mcp.mcp.exceptions import IBTimeoutError, ValidationError, YahooFinanceError
from ib_sec_mcp.mcp.validators import (
    validate_indicators,
    validate_interval,
    validate_period,
    validate_symbol,
)

# Timeout constants (in seconds)
DEFAULT_TIMEOUT = 30


def register_stock_data_tools(mcp: FastMCP) -> None:
    """Register stock data retrieval tools"""

    @mcp.tool
    async def get_stock_data(
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
        indicators: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """
        Get historical stock price data with optional technical indicators

        Args:
            symbol: Stock ticker symbol (e.g., "VOO", "AAPL")
            period: Data period - valid values: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            interval: Data interval - valid values: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
            indicators: Comma-separated technical indicators (optional)
                       Available: sma_20, sma_50, sma_200, ema_12, ema_26, rsi, macd, bollinger, volume_ma
                       Example: "sma_20,rsi,macd"
            ctx: MCP context for logging

        Returns:
            JSON string with OHLCV data and optional technical indicators

        Raises:
            ValidationError: If input validation fails
            YahooFinanceError: If Yahoo Finance API call fails
            TimeoutError: If operation times out
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)
            period = validate_period(period)
            interval = validate_interval(interval)
            indicator_list = validate_indicators(indicators) if indicators else None

            if ctx:
                await ctx.info(
                    f"Fetching {symbol} data for period={period}, interval={interval}",
                    extra={
                        "symbol": symbol,
                        "period": period,
                        "interval": interval,
                        "indicators": indicator_list,
                    },
                )

            # Fetch data with timeout
            async def fetch_yf_data():
                import yfinance as yf

                return await asyncio.to_thread(
                    lambda: yf.Ticker(symbol).history(period=period, interval=interval)
                )

            try:
                hist = await asyncio.wait_for(fetch_yf_data(), timeout=DEFAULT_TIMEOUT)
            except TimeoutError as e:
                if ctx:
                    await ctx.error(f"Yahoo Finance API timed out after {DEFAULT_TIMEOUT}s")
                raise IBTimeoutError(
                    f"Yahoo Finance API timed out after {DEFAULT_TIMEOUT} seconds",
                    operation="fetch_stock_data",
                ) from e
            except Exception as e:
                if ctx:
                    await ctx.error(f"Yahoo Finance API error: {str(e)}")
                raise YahooFinanceError(f"Failed to fetch data for {symbol}: {str(e)}") from e

            if hist.empty:
                if ctx:
                    await ctx.warning(f"No data found for symbol {symbol}")
                raise YahooFinanceError(f"No data found for {symbol}")

            # Calculate technical indicators if requested
            import pandas as pd

            technical_data = {}
            if indicator_list:
                for indicator in indicator_list:
                    if indicator.startswith("sma_"):
                        period_val = int(indicator.split("_")[1])
                        hist[f"SMA_{period_val}"] = hist["Close"].rolling(window=period_val).mean()
                        technical_data[f"sma_{period_val}"] = {
                            "latest": (
                                float(hist[f"SMA_{period_val}"].iloc[-1])
                                if not pd.isna(hist[f"SMA_{period_val}"].iloc[-1])
                                else None
                            ),
                            "name": f"{period_val}-day Simple Moving Average",
                        }

                    elif indicator.startswith("ema_"):
                        period_val = int(indicator.split("_")[1])
                        hist[f"EMA_{period_val}"] = (
                            hist["Close"].ewm(span=period_val, adjust=False).mean()
                        )
                        technical_data[f"ema_{period_val}"] = {
                            "latest": (
                                float(hist[f"EMA_{period_val}"].iloc[-1])
                                if not pd.isna(hist[f"EMA_{period_val}"].iloc[-1])
                                else None
                            ),
                            "name": f"{period_val}-day Exponential Moving Average",
                        }

                    elif indicator == "rsi":
                        # Calculate RSI (14-period default)
                        delta = hist["Close"].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        hist["RSI"] = 100 - (100 / (1 + rs))
                        rsi_latest = (
                            float(hist["RSI"].iloc[-1])
                            if not pd.isna(hist["RSI"].iloc[-1])
                            else None
                        )
                        technical_data["rsi"] = {
                            "latest": rsi_latest,
                            "name": "Relative Strength Index (14-day)",
                            "interpretation": (
                                "Overbought (>70)"
                                if rsi_latest and rsi_latest > 70
                                else (
                                    "Oversold (<30)"
                                    if rsi_latest and rsi_latest < 30
                                    else "Neutral"
                                )
                            ),
                        }

                    elif indicator == "macd":
                        # Calculate MACD (12, 26, 9)
                        ema_12 = hist["Close"].ewm(span=12, adjust=False).mean()
                        ema_26 = hist["Close"].ewm(span=26, adjust=False).mean()
                        hist["MACD"] = ema_12 - ema_26
                        hist["MACD_Signal"] = hist["MACD"].ewm(span=9, adjust=False).mean()
                        hist["MACD_Histogram"] = hist["MACD"] - hist["MACD_Signal"]
                        macd_latest = (
                            float(hist["MACD"].iloc[-1])
                            if not pd.isna(hist["MACD"].iloc[-1])
                            else None
                        )
                        signal_latest = (
                            float(hist["MACD_Signal"].iloc[-1])
                            if not pd.isna(hist["MACD_Signal"].iloc[-1])
                            else None
                        )
                        histogram_latest = (
                            float(hist["MACD_Histogram"].iloc[-1])
                            if not pd.isna(hist["MACD_Histogram"].iloc[-1])
                            else None
                        )
                        technical_data["macd"] = {
                            "macd": macd_latest,
                            "signal": signal_latest,
                            "histogram": histogram_latest,
                            "name": "MACD (12, 26, 9)",
                            "interpretation": (
                                "Bullish"
                                if histogram_latest and histogram_latest > 0
                                else "Bearish"
                                if histogram_latest
                                else None
                            ),
                        }

                    elif indicator == "bollinger":
                        # Calculate Bollinger Bands (20-day, 2 std)
                        sma_20 = hist["Close"].rolling(window=20).mean()
                        std_20 = hist["Close"].rolling(window=20).std()
                        hist["BB_Upper"] = sma_20 + (std_20 * 2)
                        hist["BB_Middle"] = sma_20
                        hist["BB_Lower"] = sma_20 - (std_20 * 2)
                        upper_latest = (
                            float(hist["BB_Upper"].iloc[-1])
                            if not pd.isna(hist["BB_Upper"].iloc[-1])
                            else None
                        )
                        middle_latest = (
                            float(hist["BB_Middle"].iloc[-1])
                            if not pd.isna(hist["BB_Middle"].iloc[-1])
                            else None
                        )
                        lower_latest = (
                            float(hist["BB_Lower"].iloc[-1])
                            if not pd.isna(hist["BB_Lower"].iloc[-1])
                            else None
                        )
                        close_latest = float(hist["Close"].iloc[-1])
                        technical_data["bollinger"] = {
                            "upper": upper_latest,
                            "middle": middle_latest,
                            "lower": lower_latest,
                            "name": "Bollinger Bands (20, 2)",
                            "interpretation": (
                                "Above upper band"
                                if upper_latest and close_latest > upper_latest
                                else (
                                    "Below lower band"
                                    if lower_latest and close_latest < lower_latest
                                    else "Within bands"
                                )
                            ),
                        }

                    elif indicator == "volume_ma":
                        # Calculate Volume Moving Average (20-day)
                        hist["Volume_MA"] = hist["Volume"].rolling(window=20).mean()
                        vol_ma_latest = (
                            float(hist["Volume_MA"].iloc[-1])
                            if not pd.isna(hist["Volume_MA"].iloc[-1])
                            else None
                        )
                        vol_latest = float(hist["Volume"].iloc[-1])
                        technical_data["volume_ma"] = {
                            "latest": vol_ma_latest,
                            "current_volume": vol_latest,
                            "name": "20-day Volume Moving Average",
                            "interpretation": (
                                "High volume"
                                if vol_ma_latest and vol_latest > vol_ma_latest * 1.5
                                else (
                                    "Low volume"
                                    if vol_ma_latest and vol_latest < vol_ma_latest * 0.5
                                    else "Normal volume"
                                )
                            ),
                        }

            # Convert to JSON-friendly format
            result = {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "data": hist.reset_index().to_dict(orient="records"),
                "summary": {
                    "start_date": str(hist.index[0]),
                    "end_date": str(hist.index[-1]),
                    "num_records": len(hist),
                    "latest_close": float(hist["Close"].iloc[-1]),
                    "period_return": float(
                        (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100
                    ),
                },
            }

            if technical_data:
                result["technical_indicators"] = technical_data

            if ctx:
                await ctx.info(
                    f"Successfully fetched {symbol} data",
                    extra={
                        "symbol": symbol,
                        "data_points": len(hist),
                        "indicators_calculated": len(technical_data),
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
                    f"Unexpected error: {str(e)}", extra={"error_type": type(e).__name__}
                )
            raise YahooFinanceError(f"Unexpected error while fetching stock data: {str(e)}") from e

    @mcp.tool
    async def get_current_price(
        symbol: str,
        ctx: Context | None = None,
    ) -> str:
        """
        Get current/latest price and key metrics for a stock

        Args:
            symbol: Stock ticker symbol (e.g., "VOO", "AAPL")
            ctx: MCP context for logging

        Returns:
            JSON string with current price, volume, market cap, P/E, dividend yield, etc.
        """
        if ctx:
            await ctx.info(f"Fetching current data for {symbol}")

        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            info = ticker.info

            result = {
                "symbol": symbol,
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "previous_close": info.get("previousClose"),
                "day_change": info.get("regularMarketChange"),
                "day_change_percent": info.get("regularMarketChangePercent"),
                "volume": info.get("volume"),
                "avg_volume": info.get("averageVolume"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "dividend_yield": info.get("dividendYield"),
                "ex_dividend_date": info.get("exDividendDate"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "beta": info.get("beta"),
            }

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool
    async def get_stock_info(
        symbol: str,
        ctx: Context | None = None,
    ) -> str:
        """
        Get comprehensive company/fund information

        Args:
            symbol: Stock ticker symbol (e.g., "VOO", "AAPL", "TSLA")
            ctx: MCP context for logging

        Returns:
            JSON string with company info, financials, dividends, and key metrics
        """
        if ctx:
            await ctx.info(f"Fetching detailed info for {symbol}")

        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Get dividend history
            dividends = ticker.dividends
            dividend_history = []
            if not dividends.empty:
                dividend_history = [
                    {"date": str(date), "amount": float(amount)}
                    for date, amount in dividends.tail(10).items()
                ]

            result = {
                "symbol": symbol,
                "basic_info": {
                    "long_name": info.get("longName"),
                    "short_name": info.get("shortName"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "website": info.get("website"),
                    "description": info.get("longBusinessSummary"),
                },
                "price_info": {
                    "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                    "previous_close": info.get("previousClose"),
                    "open": info.get("open"),
                    "day_high": info.get("dayHigh"),
                    "day_low": info.get("dayLow"),
                    "52_week_high": info.get("fiftyTwoWeekHigh"),
                    "52_week_low": info.get("fiftyTwoWeekLow"),
                },
                "valuation_metrics": {
                    "market_cap": info.get("marketCap"),
                    "enterprise_value": info.get("enterpriseValue"),
                    "trailing_pe": info.get("trailingPE"),
                    "forward_pe": info.get("forwardPE"),
                    "price_to_book": info.get("priceToBook"),
                    "price_to_sales": info.get("priceToSalesTrailing12Months"),
                    "peg_ratio": info.get("pegRatio"),
                    "ev_to_ebitda": info.get("enterpriseToEbitda"),
                    "ev_to_revenue": info.get("enterpriseToRevenue"),
                },
                "profitability_metrics": {
                    "profit_margin": info.get("profitMargins"),
                    "operating_margin": info.get("operatingMargins"),
                    "gross_margin": info.get("grossMargins"),
                    "return_on_assets": info.get("returnOnAssets"),
                    "return_on_equity": info.get("returnOnEquity"),
                    "epsTrailing_12months": info.get("trailingEps"),
                    "eps_forward": info.get("forwardEps"),
                },
                "financial_health": {
                    "total_cash": info.get("totalCash"),
                    "total_debt": info.get("totalDebt"),
                    "debt_to_equity": info.get("debtToEquity"),
                    "current_ratio": info.get("currentRatio"),
                    "quick_ratio": info.get("quickRatio"),
                    "free_cash_flow": info.get("freeCashflow"),
                },
                "growth_metrics": {
                    "revenue_growth": info.get("revenueGrowth"),
                    "earnings_growth": info.get("earningsGrowth"),
                    "earnings_quarterly_growth": info.get("earningsQuarterlyGrowth"),
                },
                "dividend_info": {
                    "dividend_rate": info.get("dividendRate"),
                    "dividend_yield": info.get("dividendYield"),
                    "ex_dividend_date": info.get("exDividendDate"),
                    "payout_ratio": info.get("payoutRatio"),
                    "five_year_avg_dividend_yield": info.get("fiveYearAvgDividendYield"),
                    "recent_dividends": dividend_history,
                },
                "trading_info": {
                    "volume": info.get("volume"),
                    "average_volume": info.get("averageVolume"),
                    "average_volume_10days": info.get("averageVolume10days"),
                    "bid": info.get("bid"),
                    "ask": info.get("ask"),
                    "bid_size": info.get("bidSize"),
                    "ask_size": info.get("askSize"),
                },
                "risk_metrics": {
                    "beta": info.get("beta"),
                    "52_week_change": info.get("52WeekChange"),
                },
            }

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})


__all__ = ["register_stock_data_tools"]
