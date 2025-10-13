"""Options Analysis Tools

Yahoo Finance options chain and analysis tools with advanced Greeks,
IV metrics, and Max Pain calculations.
"""

import json
from datetime import datetime

import numpy as np
import pandas as pd
from fastmcp import Context, FastMCP
from scipy import stats


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

    @mcp.tool
    async def calculate_greeks(
        symbol: str,
        expiration_date: str | None = None,
        risk_free_rate: float = 0.05,
        ctx: Context | None = None,
    ) -> str:
        """
        Calculate Options Greeks (Delta, Gamma, Theta, Vega, Rho)

        Uses Black-Scholes model to calculate Greeks for all strikes.
        Returns pre-computed Greeks for efficient analysis.

        Args:
            symbol: Stock ticker symbol (e.g., "SPY", "AAPL")
            expiration_date: Expiration date in YYYY-MM-DD format (if None, uses nearest)
            risk_free_rate: Risk-free interest rate (default: 0.05 = 5%)
            ctx: MCP context for logging

        Returns:
            JSON string with Greeks for ATM and key strikes:
            - Delta: Price sensitivity (0-1 for calls, -1-0 for puts)
            - Gamma: Delta change rate
            - Theta: Time decay (daily)
            - Vega: IV sensitivity
            - Rho: Interest rate sensitivity

        Raises:
            Error if no options data available
        """
        if ctx:
            await ctx.info(f"Calculating Greeks for {symbol}")

        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            expirations = ticker.options

            if not expirations:
                return json.dumps({"error": f"No options data available for {symbol}"})

            exp_date = expiration_date if expiration_date in expirations else expirations[0]
            opt = ticker.option_chain(exp_date)

            # Get current price
            info = ticker.info
            S = info.get("currentPrice") or info.get("regularMarketPrice")  # noqa: N806

            if not S:
                return json.dumps({"error": "Could not fetch current stock price"})

            # Calculate time to expiration (in years)
            exp_datetime = datetime.strptime(exp_date, "%Y-%m-%d")
            today = datetime.now()
            T = (exp_datetime - today).days / 365.0  # noqa: N806

            if T <= 0:
                return json.dumps({"error": "Expiration date is in the past"})

            # Calculate Greeks for calls and puts
            def calculate_option_greeks(row, option_type):
                K = row["strike"]  # noqa: N806
                IV = row.get("impliedVolatility", 0.3)  # Default to 30% if missing  # noqa: N806

                if IV == 0 or pd.isna(IV):
                    IV = 0.3  # noqa: N806

                # Black-Scholes calculations
                d1 = (np.log(S / K) + (risk_free_rate + 0.5 * IV**2) * T) / (IV * np.sqrt(T))
                d2 = d1 - IV * np.sqrt(T)

                if option_type == "call":
                    delta = stats.norm.cdf(d1)
                    theta = (
                        -S * stats.norm.pdf(d1) * IV / (2 * np.sqrt(T))
                        - risk_free_rate * K * np.exp(-risk_free_rate * T) * stats.norm.cdf(d2)
                    ) / 365  # Daily theta
                else:  # put
                    delta = stats.norm.cdf(d1) - 1
                    theta = (
                        -S * stats.norm.pdf(d1) * IV / (2 * np.sqrt(T))
                        + risk_free_rate * K * np.exp(-risk_free_rate * T) * stats.norm.cdf(-d2)
                    ) / 365

                # Gamma and Vega are same for calls and puts
                gamma = stats.norm.pdf(d1) / (S * IV * np.sqrt(T))
                vega = S * stats.norm.pdf(d1) * np.sqrt(T) / 100  # Per 1% change in IV

                # Rho
                if option_type == "call":
                    rho = K * T * np.exp(-risk_free_rate * T) * stats.norm.cdf(d2) / 100
                else:
                    rho = -K * T * np.exp(-risk_free_rate * T) * stats.norm.cdf(-d2) / 100

                return {
                    "strike": float(K),
                    "delta": round(float(delta), 4),
                    "gamma": round(float(gamma), 6),
                    "theta": round(float(theta), 4),
                    "vega": round(float(vega), 4),
                    "rho": round(float(rho), 4),
                    "implied_volatility": round(float(IV), 4),
                }

            # Calculate for calls and puts
            call_greeks = [calculate_option_greeks(row, "call") for _, row in opt.calls.iterrows()]
            put_greeks = [calculate_option_greeks(row, "put") for _, row in opt.puts.iterrows()]

            # Find ATM strike
            atm_idx = (opt.calls["strike"] - S).abs().argsort()[:1].iloc[0]
            atm_strike = float(opt.calls.iloc[atm_idx]["strike"])

            result = {
                "symbol": symbol,
                "current_price": float(S),
                "expiration_date": exp_date,
                "days_to_expiration": int((exp_datetime - today).days),
                "risk_free_rate": risk_free_rate,
                "atm_strike": atm_strike,
                "atm_greeks": {
                    "call": call_greeks[atm_idx],
                    "put": put_greeks[atm_idx],
                },
                "all_strikes": {
                    "calls": call_greeks,
                    "puts": put_greeks,
                },
                "summary": {
                    "total_call_delta": round(
                        sum(
                            g["delta"] * opt.calls.iloc[i]["openInterest"]
                            for i, g in enumerate(call_greeks)
                        ),
                        2,
                    ),
                    "total_put_delta": round(
                        sum(
                            g["delta"] * opt.puts.iloc[i]["openInterest"]
                            for i, g in enumerate(put_greeks)
                        ),
                        2,
                    ),
                    "net_delta": round(
                        sum(
                            g["delta"] * opt.calls.iloc[i]["openInterest"]
                            for i, g in enumerate(call_greeks)
                        )
                        + sum(
                            g["delta"] * opt.puts.iloc[i]["openInterest"]
                            for i, g in enumerate(put_greeks)
                        ),
                        2,
                    ),
                },
            }

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool
    async def calculate_iv_metrics(
        symbol: str,
        lookback_days: int = 252,
        ctx: Context | None = None,
    ) -> str:
        """
        Calculate IV Rank and IV Percentile for options

        IV Rank: Where current IV sits in its 52-week range (0-100)
        IV Percentile: Percentage of days current IV was lower (0-100)

        Args:
            symbol: Stock ticker symbol (e.g., "SPY", "AAPL")
            lookback_days: Historical period for IV calculation (default: 252 = 1 year)
            ctx: MCP context for logging

        Returns:
            JSON string with IV metrics:
            - Current IV (ATM options)
            - IV Rank (0-100, higher = more expensive options)
            - IV Percentile (0-100, higher = historically high IV)
            - 52-week IV high/low
            - Interpretation for options strategies

        Raises:
            Error if insufficient historical data
        """
        if ctx:
            await ctx.info(f"Calculating IV metrics for {symbol}")

        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            expirations = ticker.options

            if not expirations:
                return json.dumps({"error": f"No options data available for {symbol}"})

            # Get current IV from ATM options
            opt = ticker.option_chain(expirations[0])
            info = ticker.info
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")

            if not current_price:
                return json.dumps({"error": "Could not fetch current stock price"})

            # Find ATM strike
            atm_idx = (opt.calls["strike"] - current_price).abs().argsort()[:1].iloc[0]
            current_iv = float(opt.calls.iloc[atm_idx].get("impliedVolatility", 0))

            if current_iv == 0:
                return json.dumps({"error": "Could not fetch current implied volatility"})

            # Get historical data for IV calculation
            hist = ticker.history(period=f"{lookback_days}d")

            if hist.empty or len(hist) < 20:
                return json.dumps({"error": "Insufficient historical data"})

            # Calculate historical volatility as proxy for IV history
            # (Note: True IV history requires historical options data which yfinance doesn't provide)
            returns = hist["Close"].pct_change().dropna()
            rolling_vol = returns.rolling(window=20).std() * np.sqrt(252)  # Annualized
            rolling_vol = rolling_vol.dropna()

            if len(rolling_vol) == 0:
                return json.dumps({"error": "Could not calculate historical volatility"})

            # Calculate IV Rank and Percentile
            iv_min = float(rolling_vol.min())
            iv_max = float(rolling_vol.max())
            iv_rank = ((current_iv - iv_min) / (iv_max - iv_min) * 100) if iv_max > iv_min else 50

            # IV Percentile: percentage of days where IV was lower than current
            iv_percentile = (rolling_vol < current_iv).sum() / len(rolling_vol) * 100

            # Interpretation
            if iv_rank > 75:
                interpretation = (
                    "Very High IV - Consider selling options (credit spreads, covered calls)"
                )
            elif iv_rank > 50:
                interpretation = "High IV - Good for selling premium"
            elif iv_rank > 25:
                interpretation = "Moderate IV - Neutral strategies"
            else:
                interpretation = "Low IV - Consider buying options (long calls/puts, debit spreads)"

            result = {
                "symbol": symbol,
                "current_price": float(current_price),
                "current_iv": round(current_iv * 100, 2),  # Convert to percentage
                "iv_rank": round(float(iv_rank), 2),
                "iv_percentile": round(float(iv_percentile), 2),
                "iv_52week_high": round(float(iv_max) * 100, 2),
                "iv_52week_low": round(float(iv_min) * 100, 2),
                "iv_52week_mean": round(float(rolling_vol.mean()) * 100, 2),
                "interpretation": interpretation,
                "lookback_days": len(rolling_vol),
                "note": "IV metrics based on historical volatility as proxy (true IV history not available via yfinance)",
            }

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool
    async def calculate_max_pain(
        symbol: str,
        expiration_date: str | None = None,
        ctx: Context | None = None,
    ) -> str:
        """
        Calculate Max Pain price for options expiration

        Max Pain: Strike price where option holders lose most money
        (where market makers have least payout). Stock tends to gravitate
        toward Max Pain at expiration.

        Args:
            symbol: Stock ticker symbol (e.g., "SPY", "AAPL")
            expiration_date: Expiration date in YYYY-MM-DD format (if None, uses nearest)
            ctx: MCP context for logging

        Returns:
            JSON string with:
            - Max Pain strike price
            - Total pain at each strike
            - Current price vs Max Pain
            - Expected move based on options OI
            - Trading strategy suggestion

        Raises:
            Error if no options data available
        """
        if ctx:
            await ctx.info(f"Calculating Max Pain for {symbol}")

        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            expirations = ticker.options

            if not expirations:
                return json.dumps({"error": f"No options data available for {symbol}"})

            exp_date = expiration_date if expiration_date in expirations else expirations[0]
            opt = ticker.option_chain(exp_date)

            # Get current price
            info = ticker.info
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")

            if not current_price:
                return json.dumps({"error": "Could not fetch current stock price"})

            # Get all strikes
            all_strikes = sorted(set(opt.calls["strike"].tolist() + opt.puts["strike"].tolist()))

            # Calculate pain at each strike
            pain_by_strike = {}

            for strike in all_strikes:
                call_pain = 0
                put_pain = 0

                # Calculate call pain (ITM calls lose money for option writers)
                for _, call_row in opt.calls.iterrows():
                    call_strike = call_row["strike"]
                    call_oi = call_row["openInterest"]
                    if strike > call_strike:  # ITM
                        call_pain += (
                            (strike - call_strike) * call_oi * 100
                        )  # 100 shares per contract

                # Calculate put pain (ITM puts lose money for option writers)
                for _, put_row in opt.puts.iterrows():
                    put_strike = put_row["strike"]
                    put_oi = put_row["openInterest"]
                    if strike < put_strike:  # ITM
                        put_pain += (put_strike - strike) * put_oi * 100

                pain_by_strike[float(strike)] = call_pain + put_pain

            # Find Max Pain (minimum total pain)
            max_pain_strike = min(pain_by_strike, key=pain_by_strike.get)
            max_pain_value = pain_by_strike[max_pain_strike]

            # Calculate expected move based on ATM straddle
            atm_idx = (opt.calls["strike"] - current_price).abs().argsort()[:1].iloc[0]
            atm_call_price = opt.calls.iloc[atm_idx].get("lastPrice", 0)
            atm_put_price = opt.puts.iloc[atm_idx].get("lastPrice", 0)
            expected_move = (
                (atm_call_price + atm_put_price) if atm_call_price and atm_put_price else None
            )

            # Trading interpretation
            distance_to_max_pain = abs(current_price - max_pain_strike)
            percent_to_max_pain = (distance_to_max_pain / current_price) * 100

            if percent_to_max_pain < 2:
                interpretation = "Price near Max Pain - expect consolidation"
            elif current_price > max_pain_strike:
                interpretation = (
                    f"Price ${distance_to_max_pain:.2f} above Max Pain - bearish pressure expected"
                )
            else:
                interpretation = (
                    f"Price ${distance_to_max_pain:.2f} below Max Pain - bullish pressure expected"
                )

            result = {
                "symbol": symbol,
                "current_price": float(current_price),
                "expiration_date": exp_date,
                "max_pain_strike": float(max_pain_strike),
                "max_pain_value": float(max_pain_value),
                "distance_to_max_pain": round(float(distance_to_max_pain), 2),
                "percent_to_max_pain": round(float(percent_to_max_pain), 2),
                "expected_move": round(float(expected_move), 2) if expected_move else None,
                "interpretation": interpretation,
                "pain_by_strike": {str(k): float(v) for k, v in sorted(pain_by_strike.items())},
                "top_pain_strikes": [
                    {"strike": float(k), "pain": float(v)}
                    for k, v in sorted(pain_by_strike.items(), key=lambda x: x[1])[:5]
                ],
            }

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})


__all__ = ["register_options_tools"]
