"""Options Analysis Tools

Yahoo Finance options chain and analysis tools.
"""

import json

from fastmcp import Context, FastMCP


def register_options_tools(mcp: FastMCP) -> None:
    """Register options analysis tools"""

    @mcp.tool
    async def get_options_chain(
        symbol: str,
        expiration_date: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """
        Get options chain data (calls and puts) for a stock

        Args:
            symbol: Stock ticker symbol (e.g., "VOO", "SPY")
            expiration_date: Expiration date in YYYY-MM-DD format (if None, uses nearest expiration)
            ctx: MCP context for logging

        Returns:
            JSON string with calls and puts data including strike, volume, open interest, implied volatility
        """
        if ctx:
            await ctx.info(f"Fetching options chain for {symbol}")

        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)

            # Get available expiration dates
            expirations = ticker.options
            if not expirations:
                return json.dumps({"error": f"No options data available for {symbol}"})

            # Use specified date or nearest expiration
            if expiration_date:
                if expiration_date not in expirations:
                    return json.dumps(
                        {"error": f"Invalid expiration date. Available dates: {list(expirations)}"}
                    )
                exp_date = expiration_date
            else:
                exp_date = expirations[0]

            # Get options chain
            opt = ticker.option_chain(exp_date)

            result = {
                "symbol": symbol,
                "expiration_date": exp_date,
                "available_expirations": list(expirations),
                "calls": opt.calls.to_dict(orient="records"),
                "puts": opt.puts.to_dict(orient="records"),
                "summary": {
                    "num_calls": len(opt.calls),
                    "num_puts": len(opt.puts),
                    "total_call_volume": int(opt.calls["volume"].sum()),
                    "total_put_volume": int(opt.puts["volume"].sum()),
                    "total_call_oi": int(opt.calls["openInterest"].sum()),
                    "total_put_oi": int(opt.puts["openInterest"].sum()),
                },
            }

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool
    async def calculate_put_call_ratio(
        symbol: str,
        expiration_date: str | None = None,
        ratio_type: str = "open_interest",
        ctx: Context | None = None,
    ) -> str:
        """
        Calculate Put/Call Ratio for a stock's options

        Args:
            symbol: Stock ticker symbol (e.g., "SPY", "QQQ")
            expiration_date: Expiration date in YYYY-MM-DD format (if None, uses nearest expiration)
            ratio_type: Type of ratio - "open_interest" (default) or "volume"
            ctx: MCP context for logging

        Returns:
            JSON string with put/call ratio and detailed breakdown
        """
        if ctx:
            await ctx.info(f"Calculating Put/Call Ratio for {symbol}")

        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)

            # Get available expiration dates
            expirations = ticker.options
            if not expirations:
                return json.dumps({"error": f"No options data available for {symbol}"})

            # Use specified date or nearest expiration
            if expiration_date:
                if expiration_date not in expirations:
                    return json.dumps(
                        {"error": f"Invalid expiration date. Available dates: {list(expirations)}"}
                    )
                exp_date = expiration_date
            else:
                exp_date = expirations[0]

            # Get options chain
            opt = ticker.option_chain(exp_date)

            # Calculate ratios
            if ratio_type == "volume":
                put_total = opt.puts["volume"].sum()
                call_total = opt.calls["volume"].sum()
            else:  # open_interest
                put_total = opt.puts["openInterest"].sum()
                call_total = opt.calls["openInterest"].sum()

            if call_total == 0:
                return json.dumps({"error": "Call total is zero, cannot calculate ratio"})

            pcr = float(put_total / call_total)

            # Get current price for context
            info = ticker.info
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")

            result = {
                "symbol": symbol,
                "current_price": current_price,
                "expiration_date": exp_date,
                "ratio_type": ratio_type,
                "put_call_ratio": round(pcr, 4),
                "interpretation": (
                    "Bearish (PCR > 1.0)"
                    if pcr > 1.0
                    else ("Neutral (PCR ≈ 1.0)" if 0.7 <= pcr <= 1.3 else "Bullish (PCR < 0.7)")
                ),
                "details": {
                    "total_puts": int(put_total),
                    "total_calls": int(call_total),
                    "put_volume": int(opt.puts["volume"].sum()),
                    "call_volume": int(opt.calls["volume"].sum()),
                    "put_open_interest": int(opt.puts["openInterest"].sum()),
                    "call_open_interest": int(opt.calls["openInterest"].sum()),
                },
                "strike_distribution": {
                    "call_strikes": opt.calls["strike"].tolist(),
                    "put_strikes": opt.puts["strike"].tolist(),
                    "atm_strike": (
                        float(
                            opt.calls.iloc[
                                (opt.calls["strike"] - current_price).abs().argsort()[:1]
                            ]["strike"].iloc[0]
                        )
                        if current_price
                        else None
                    ),
                },
            }

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})


__all__ = ["register_options_tools"]
