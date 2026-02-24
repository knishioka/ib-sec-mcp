# MCP Tools Reference

Complete reference for all MCP tools, resources, and prompts provided by the IB Analytics MCP server.

## Overview

IB Analytics provides **45 tools**, **9 resources**, and **5 prompts** across two usage modes:

- **Mode 1 (Claude Desktop)**: Coarse-grained tools for complete, self-contained analysis
- **Mode 2 (Claude Code + MCP)**: Fine-grained tools for composable, custom workflows

## Quick Reference

| Category                                        | Tools | Mode   | Description                                      |
| ----------------------------------------------- | ----- | ------ | ------------------------------------------------ |
| [IB Portfolio Analysis](#ib-portfolio-analysis) | 9     | Mode 1 | Complete portfolio analysis with IB API          |
| [Composable Data](#composable-data-access)      | 6     | Mode 2 | Fine-grained data access, metrics, and dividends |
| [Rebalancing](#rebalancing)                     | 2     | Mode 1 | Portfolio rebalancing trades and simulation      |
| [Sector & FX Analysis](#sector--fx-analysis)    | 2     | Mode 1 | Sector allocation and currency exposure          |
| [Stock Data](#stock-data)                       | 3     | Both   | Price data and company information               |
| [Stock News](#stock-news)                       | 1     | Both   | News article retrieval                           |
| [Options Analysis](#options-analysis)           | 5     | Both   | Options chain, Greeks, IV, Max Pain              |
| [Portfolio Analytics](#portfolio-analytics)     | 2     | Both   | Advanced metrics and correlation                 |
| [Market Comparison](#market-comparison)         | 2     | Both   | Benchmark comparison and analyst consensus       |
| [ETF Comparison](#etf-comparison)               | 1     | Both   | Multi-ETF performance comparison                 |
| [Technical Analysis](#technical-analysis)       | 2     | Both   | Technical indicators and signals                 |
| [Position History](#position-history)           | 5     | Mode 2 | SQLite-based position tracking                   |
| [ETF Calculator](#etf-calculator)               | 3     | Both   | ETF swap calculations                            |
| [Sentiment Analysis](#sentiment-analysis)       | 2     | Both   | Market sentiment from multiple sources           |

---

## IB Portfolio Analysis

Coarse-grained tools that automatically fetch data from the IB Flex Query API (with caching) and perform complete analysis. **Recommended for Mode 1 (Claude Desktop)**.

### `fetch_ib_data`

Fetch Interactive Brokers data from Flex Query API and save to local cache.

| Parameter       | Type  | Required | Default | Description                                                                                 |
| --------------- | ----- | -------- | ------- | ------------------------------------------------------------------------------------------- |
| `start_date`    | `str` | Yes      | -       | Start date in YYYY-MM-DD format                                                             |
| `end_date`      | `str` | No       | today   | End date in YYYY-MM-DD format                                                               |
| `account_index` | `int` | No       | `0`     | Index to select among accounts returned by the Flex Query (0 for first, 1 for second, etc.) |

**Returns**: Dict with `account_id`, `date_range`, `file_path`, and `status`.

**Side effects**: Saves XML to `data/raw/` and auto-syncs positions to SQLite database.

```
>>> result = await fetch_ib_data("2025-01-01", "2025-06-30")
# Returns: {"account_id": "U1234567", "date_range": {...}, "file_path": "data/raw/U1234567_2025-01-01_2025-06-30.xml", "status": "success"}
```

### `analyze_performance`

Analyze trading performance including win rate, profit factor, and P&L breakdown.

| Parameter       | Type   | Required | Default | Description                     |
| --------------- | ------ | -------- | ------- | ------------------------------- |
| `start_date`    | `str`  | Yes      | -       | Start date in YYYY-MM-DD format |
| `end_date`      | `str`  | No       | today   | End date in YYYY-MM-DD format   |
| `account_index` | `int`  | No       | `0`     | Account selection index         |
| `use_cache`     | `bool` | No       | `true`  | Use cached data if available    |

**Returns**: JSON with performance metrics (win rate, profit factor, average win/loss, etc.).

```
>>> result = await analyze_performance("2025-01-01", "2025-06-30")
```

### `analyze_costs`

Analyze trading costs and commissions by symbol and asset class.

| Parameter       | Type   | Required | Default | Description                     |
| --------------- | ------ | -------- | ------- | ------------------------------- |
| `start_date`    | `str`  | Yes      | -       | Start date in YYYY-MM-DD format |
| `end_date`      | `str`  | No       | today   | End date in YYYY-MM-DD format   |
| `account_index` | `int`  | No       | `0`     | Account selection index         |
| `use_cache`     | `bool` | No       | `true`  | Use cached data if available    |

**Returns**: JSON with cost analysis (commissions by symbol, asset class breakdown).

### `analyze_bonds`

Analyze zero-coupon bonds (STRIPS) including YTM, duration, and maturity profile.

| Parameter       | Type   | Required | Default | Description                     |
| --------------- | ------ | -------- | ------- | ------------------------------- |
| `start_date`    | `str`  | Yes      | -       | Start date in YYYY-MM-DD format |
| `end_date`      | `str`  | No       | today   | End date in YYYY-MM-DD format   |
| `account_index` | `int`  | No       | `0`     | Account selection index         |
| `use_cache`     | `bool` | No       | `true`  | Use cached data if available    |

**Returns**: JSON with bond analysis (YTM, duration, maturity ladder).

### `analyze_tax`

Analyze tax implications including Phantom Income (OID) for bonds.

| Parameter       | Type   | Required | Default | Description                     |
| --------------- | ------ | -------- | ------- | ------------------------------- |
| `start_date`    | `str`  | Yes      | -       | Start date in YYYY-MM-DD format |
| `end_date`      | `str`  | No       | today   | End date in YYYY-MM-DD format   |
| `account_index` | `int`  | No       | `0`     | Account selection index         |
| `use_cache`     | `bool` | No       | `true`  | Use cached data if available    |

**Returns**: JSON with tax analysis (realized gains, phantom income, estimated tax liability).

### `analyze_risk`

Analyze portfolio risk including interest rate scenarios.

| Parameter              | Type    | Required | Default | Description                                   |
| ---------------------- | ------- | -------- | ------- | --------------------------------------------- |
| `start_date`           | `str`   | Yes      | -       | Start date in YYYY-MM-DD format               |
| `end_date`             | `str`   | No       | today   | End date in YYYY-MM-DD format                 |
| `account_index`        | `int`   | No       | `0`     | Account selection index                       |
| `interest_rate_change` | `float` | No       | `0.01`  | Interest rate change for scenario (0.01 = 1%) |
| `use_cache`            | `bool`  | No       | `true`  | Use cached data if available                  |

**Returns**: JSON with risk analysis (concentration risk, interest rate sensitivity, scenarios).

### `analyze_consolidated_portfolio`

Analyze all accounts as a consolidated portfolio. Supports both API mode and file mode.

| Parameter    | Type   | Required    | Default | Description                                |
| ------------ | ------ | ----------- | ------- | ------------------------------------------ |
| `start_date` | `str`  | Conditional | -       | Start date (required for API mode)         |
| `end_date`   | `str`  | No          | today   | End date (API mode only)                   |
| `use_cache`  | `bool` | No          | `true`  | Use cached data (API mode only)            |
| `file_path`  | `str`  | Conditional | -       | Path to IB Flex Query XML file (file mode) |

**Returns**: JSON with consolidated analysis including per-account breakdown, holdings aggregated by symbol, asset allocation, concentration risk, and trading activity.

```
>>> # API mode
>>> result = await analyze_consolidated_portfolio(start_date="2025-01-01")

>>> # File mode
>>> result = await analyze_consolidated_portfolio(file_path="data/raw/U1234567_2025-01-01_2025-06-30.xml")
```

### `calculate_tax_loss_harvesting`

Identify unrealized loss positions eligible for tax loss harvesting. Detects wash sale violations (30-day rule) and suggests Ireland-domiciled ETF alternatives to maintain exposure during the waiting period.

| Parameter       | Type  | Required | Default  | Description                                       |
| --------------- | ----- | -------- | -------- | ------------------------------------------------- |
| `start_date`    | `str` | Yes      | -        | Start date in YYYY-MM-DD format                   |
| `end_date`      | `str` | No       | today    | End date in YYYY-MM-DD format                     |
| `account_index` | `int` | No       | `0`      | Account selection index                           |
| `tax_rate`      | `str` | No       | `"0.30"` | Tax rate as decimal string (e.g., `"0.30"` = 30%) |

**Returns**: JSON with `wash_sale_violations` (symbol, sell_date, buy_date, days_apart, status, disallowed_loss), `harvesting_opportunities` (symbol, unrealized_loss, potential_tax_savings, wash_sale_risk, ie_alternative), and `summary` (total_unrealized_losses, potential_total_savings).

```
>>> result = await calculate_tax_loss_harvesting("2025-01-01", tax_rate="0.20")
```

### `get_portfolio_summary`

Get a lightweight portfolio summary from a saved XML or CSV file (no API call). Useful for quick checks without re-fetching from IB.

| Parameter   | Type  | Required | Default | Description                        |
| ----------- | ----- | -------- | ------- | ---------------------------------- |
| `file_path` | `str` | Yes      | -       | Path to IB Flex Query XML/CSV file |

**Returns**: JSON with account summary, position list, and basic P&L totals.

---

## Composable Data Access

Fine-grained tools for custom analysis. **Recommended for Mode 2 (Claude Code + MCP)**.

### `get_trades`

Get filtered trade data for custom analysis.

| Parameter       | Type   | Required | Default | Description                                      |
| --------------- | ------ | -------- | ------- | ------------------------------------------------ |
| `start_date`    | `str`  | Yes      | -       | Start date in YYYY-MM-DD format                  |
| `end_date`      | `str`  | No       | today   | End date in YYYY-MM-DD format                    |
| `symbol`        | `str`  | No       | -       | Filter by symbol (e.g., "AAPL")                  |
| `asset_class`   | `str`  | No       | -       | Filter by asset class: STK, BOND, OPT, FUT, CASH |
| `account_index` | `int`  | No       | `0`     | Account selection index                          |
| `use_cache`     | `bool` | No       | `true`  | Use cached data if available                     |

**Returns**: JSON with `trade_count`, `date_range`, `filters`, and list of `trades`.

```
>>> trades = await get_trades("2025-01-01", symbol="AAPL")
>>> bond_trades = await get_trades("2025-01-01", asset_class="BOND")
```

### `get_positions`

Get current positions with optional filtering.

| Parameter       | Type   | Required | Default | Description                                      |
| --------------- | ------ | -------- | ------- | ------------------------------------------------ |
| `start_date`    | `str`  | Yes      | -       | Start date in YYYY-MM-DD format                  |
| `end_date`      | `str`  | No       | today   | End date in YYYY-MM-DD format                    |
| `symbol`        | `str`  | No       | -       | Filter by symbol                                 |
| `asset_class`   | `str`  | No       | -       | Filter by asset class: STK, BOND, OPT, FUT, CASH |
| `account_index` | `int`  | No       | `0`     | Account selection index                          |
| `use_cache`     | `bool` | No       | `true`  | Use cached data if available                     |

**Returns**: JSON with `position_count`, `totals` (total_value, unrealized_pnl, realized_pnl), and list of `positions`.

```
>>> positions = await get_positions("2025-01-01", asset_class="BOND")
```

### `get_account_summary`

Get account-level summary information.

| Parameter       | Type   | Required | Default | Description                     |
| --------------- | ------ | -------- | ------- | ------------------------------- |
| `start_date`    | `str`  | Yes      | -       | Start date in YYYY-MM-DD format |
| `end_date`      | `str`  | No       | today   | End date in YYYY-MM-DD format   |
| `account_index` | `int`  | No       | `0`     | Account selection index         |
| `use_cache`     | `bool` | No       | `true`  | Use cached data if available    |

**Returns**: JSON with `account_id`, `cash` (by currency), `positions` (total value, unrealized P&L), `trades` (count, realized P&L, commissions), and `account_value`.

### `calculate_metric`

Calculate individual performance metrics.

| Parameter       | Type      | Required | Default | Description                          |
| --------------- | --------- | -------- | ------- | ------------------------------------ |
| `metric_name`   | `Literal` | Yes      | -       | Metric to calculate (see list below) |
| `start_date`    | `str`     | Yes      | -       | Start date in YYYY-MM-DD format      |
| `end_date`      | `str`     | No       | today   | End date in YYYY-MM-DD format        |
| `symbol`        | `str`     | No       | -       | Filter by symbol                     |
| `account_index` | `int`     | No       | `0`     | Account selection index              |
| `use_cache`     | `bool`    | No       | `true`  | Use cached data if available         |

**Available metrics**:

| Metric              | Description                              |
| ------------------- | ---------------------------------------- |
| `win_rate`          | Percentage of winning trades             |
| `profit_factor`     | Gross profit / gross loss ratio          |
| `commission_rate`   | Commission as % of trading volume        |
| `risk_reward_ratio` | Average win / average loss               |
| `total_pnl`         | Realized + unrealized P&L                |
| `realized_pnl`      | Total realized P&L from closed trades    |
| `unrealized_pnl`    | Total unrealized P&L from open positions |
| `avg_win`           | Average winning trade amount             |
| `avg_loss`          | Average losing trade amount              |
| `largest_win`       | Largest single winning trade             |
| `largest_loss`      | Largest single losing trade              |
| `trade_frequency`   | Average trades per day                   |

**Returns**: JSON with `metric_name`, `metric_value`, and `calculation_details`.

```
>>> result = await calculate_metric("win_rate", "2025-01-01")
>>> result = await calculate_metric("profit_factor", "2025-01-01", symbol="AAPL")
```

### `compare_periods`

Compare metrics across two time periods.

| Parameter       | Type        | Required | Default    | Description                  |
| --------------- | ----------- | -------- | ---------- | ---------------------------- |
| `period1_start` | `str`       | Yes      | -          | Period 1 start date          |
| `period1_end`   | `str`       | Yes      | -          | Period 1 end date            |
| `period2_start` | `str`       | Yes      | -          | Period 2 start date          |
| `period2_end`   | `str`       | Yes      | -          | Period 2 end date            |
| `metrics`       | `list[str]` | No       | common set | Metrics to compare           |
| `account_index` | `int`       | No       | `0`        | Account selection index      |
| `use_cache`     | `bool`      | No       | `true`     | Use cached data if available |

**Default metrics**: `win_rate`, `profit_factor`, `realized_pnl`, `commission_rate`, `trade_frequency`

**Returns**: JSON with period details, side-by-side metric comparison with percentage changes, and improvement summary.

```
>>> comparison = await compare_periods(
...     "2025-01-01", "2025-06-30",
...     "2025-07-01", "2025-12-31",
...     metrics=["win_rate", "realized_pnl"]
... )
```

### `analyze_dividend_income`

Analyze dividend income from held equity positions and compare Ireland-domiciled vs US-domiciled ETF tax efficiency.

| Parameter       | Type  | Required | Default | Description                     |
| --------------- | ----- | -------- | ------- | ------------------------------- |
| `start_date`    | `str` | Yes      | -       | Start date in YYYY-MM-DD format |
| `end_date`      | `str` | No       | today   | End date in YYYY-MM-DD format   |
| `account_index` | `int` | No       | `0`     | Account selection index         |

**Returns**: JSON with `positions` (symbol, domicile, yield, annual_dividend, withholding_rate, net_receipt), `portfolio_summary` (total_gross, total_withholding, total_net, weighted_yield), and `ie_savings_analysis` (potential_annual_savings per position).

**Note**: Ireland-domiciled ETFs (IE ISIN prefix) are subject to 15% withholding tax vs 30% for US-domiciled ETFs. This tool identifies restructuring opportunities.

```
>>> result = await analyze_dividend_income("2025-01-01")
```

---

## Rebalancing

Tools for generating and simulating portfolio rebalancing trades. Typically invoked via `/rebalance-portfolio`.

### `generate_rebalancing_trades`

Calculate specific buy/sell trades required to move from current allocation to a target allocation.

| Parameter           | Type               | Required | Default | Description                                 |
| ------------------- | ------------------ | -------- | ------- | ------------------------------------------- |
| `target_allocation` | `dict[str, float]` | Yes      | -       | Target weights per symbol (must sum to 100) |
| `start_date`        | `str`              | Yes      | -       | Start date in YYYY-MM-DD format             |
| `end_date`          | `str`              | No       | today   | End date in YYYY-MM-DD format               |
| `account_index`     | `int`              | No       | `0`     | Account selection index                     |

**Returns**: JSON with `trades` list (symbol, direction BUY/SELL, amount_usd, estimated_shares, commission, drift_pct), `summary` (total_buy, total_sell, net_cash, total_commission), and `warnings`.

```
>>> result = await generate_rebalancing_trades(
...     target_allocation={"CSPX": 30, "INDA": 20, "STRIPS-2040": 40, "USD.CASH": 10},
...     start_date="2025-01-01"
... )
```

### `simulate_rebalancing`

Simulate rebalancing and calculate the tax and commission impact before executing trades.

| Parameter           | Type               | Required | Default | Description                                 |
| ------------------- | ------------------ | -------- | ------- | ------------------------------------------- |
| `target_allocation` | `dict[str, float]` | Yes      | -       | Target weights per symbol (must sum to 100) |
| `start_date`        | `str`              | Yes      | -       | Start date in YYYY-MM-DD format             |
| `end_date`          | `str`              | No       | today   | End date in YYYY-MM-DD format               |
| `account_index`     | `int`              | No       | `0`     | Account selection index                     |

**Returns**: Same as `generate_rebalancing_trades` plus `tax_impact` (estimated_taxable_gains, estimated_tax_losses, net_tax_impact).

---

## Sector & FX Analysis

Tools for portfolio diversification analysis across sectors and currencies.

### `analyze_sector_allocation`

Analyze portfolio sector breakdown and concentration risk using the Herfindahl-Hirschman Index (HHI).

| Parameter       | Type  | Required | Default | Description                     |
| --------------- | ----- | -------- | ------- | ------------------------------- |
| `start_date`    | `str` | Yes      | -       | Start date in YYYY-MM-DD format |
| `end_date`      | `str` | No       | today   | End date in YYYY-MM-DD format   |
| `account_index` | `int` | No       | `0`     | Account selection index         |

**Returns**: JSON with `sectors` (name, value, weight, positions), `concentration_risk` (hhi, assessment: LOW/MODERATE/HIGH), `equity_vs_non_equity` breakdown, and `recommendations`.

**HHI interpretation**: < 1500 = well-diversified; 1500–2500 = moderate concentration; > 2500 = high concentration risk.

### `analyze_fx_exposure`

Analyze currency exposure across all portfolio positions and simulate exchange rate scenario impact.

| Parameter         | Type    | Required | Default | Description                              |
| ----------------- | ------- | -------- | ------- | ---------------------------------------- |
| `start_date`      | `str`   | Yes      | -       | Start date in YYYY-MM-DD format          |
| `end_date`        | `str`   | No       | today   | End date in YYYY-MM-DD format            |
| `account_index`   | `int`   | No       | `0`     | Account selection index                  |
| `fx_scenario_pct` | `float` | No       | `10.0`  | % move to simulate for all non-base CCYs |

**Returns**: JSON with `currencies` (currency, value_usd, weight, positions), `scenario_impact` (best_case, worst_case per currency), `concentration_risk`, and `hedge_recommendations`.

---

## Stock Data

Yahoo Finance stock data retrieval tools.

### `get_stock_data`

Get historical stock price data with optional technical indicators.

| Parameter      | Type      | Required | Default | Description                                                                                                 |
| -------------- | --------- | -------- | ------- | ----------------------------------------------------------------------------------------------------------- |
| `symbol`       | `str`     | Yes      | -       | Stock ticker symbol (e.g., "AAPL")                                                                          |
| `period`       | `Literal` | No       | `"1mo"` | `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`                                      |
| `interval`     | `Literal` | No       | `"1d"`  | `1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m`, `1h`, `1d`, `5d`, `1wk`, `1mo`, `3mo`                         |
| `indicators`   | `str`     | No       | -       | Comma-separated: `sma_20`, `sma_50`, `sma_200`, `ema_12`, `ema_26`, `rsi`, `macd`, `bollinger`, `volume_ma` |
| `limit`        | `int`     | No       | -       | Return only latest N data points                                                                            |
| `summary_only` | `bool`    | No       | `false` | Return only summary statistics (no data points)                                                             |

**Returns**: JSON with OHLCV data, summary statistics, and optional technical indicators.

```
>>> data = await get_stock_data("AAPL", period="6mo", indicators="sma_20,rsi,macd")
>>> summary = await get_stock_data("VOO", period="1y", summary_only=True)
```

### `get_current_price`

Get current/latest price and key metrics for a stock.

| Parameter | Type  | Required | Default | Description         |
| --------- | ----- | -------- | ------- | ------------------- |
| `symbol`  | `str` | Yes      | -       | Stock ticker symbol |

**Returns**: JSON with `current_price`, `previous_close`, `day_change`, `volume`, `market_cap`, `pe_ratio`, `dividend_yield`, `52_week_high`, `52_week_low`, `beta`.

```
>>> price = await get_current_price("AAPL")
```

### `get_stock_info`

Get comprehensive company/fund information.

| Parameter | Type  | Required | Default | Description         |
| --------- | ----- | -------- | ------- | ------------------- |
| `symbol`  | `str` | Yes      | -       | Stock ticker symbol |

**Returns**: JSON with `basic_info` (name, sector, description), `price_info`, `valuation_metrics` (P/E, P/B, PEG, EV/EBITDA), `profitability_metrics` (margins, ROE, ROA), `financial_health` (debt, cash, current ratio), `growth_metrics`, `dividend_info` (yield, payout ratio, history), `trading_info`, `risk_metrics`.

```
>>> info = await get_stock_info("AAPL")
```

---

## Stock News

### `get_stock_news`

Get latest news articles for a stock symbol.

| Parameter | Type  | Required | Default | Description                   |
| --------- | ----- | -------- | ------- | ----------------------------- |
| `symbol`  | `str` | Yes      | -       | Stock ticker symbol           |
| `limit`   | `int` | No       | `10`    | Max articles to return (1-50) |

**Returns**: JSON with `news_count` and list of `articles` (title, publisher, link, publish_time, summary).

```
>>> news = await get_stock_news("AAPL", limit=5)
```

---

## Options Analysis

### `get_options_chain`

Get options chain data (calls and puts) for a stock.

| Parameter         | Type  | Required | Default | Description                          |
| ----------------- | ----- | -------- | ------- | ------------------------------------ |
| `symbol`          | `str` | Yes      | -       | Stock ticker symbol                  |
| `expiration_date` | `str` | No       | nearest | Expiration date in YYYY-MM-DD format |

**Returns**: JSON with `available_expirations`, `calls`, `puts`, and `summary` (volume and open interest totals).

```
>>> chain = await get_options_chain("SPY", expiration_date="2025-03-21")
```

### `calculate_put_call_ratio`

Calculate Put/Call Ratio for sentiment analysis.

| Parameter         | Type  | Required | Default           | Description                          |
| ----------------- | ----- | -------- | ----------------- | ------------------------------------ |
| `symbol`          | `str` | Yes      | -                 | Stock ticker symbol                  |
| `expiration_date` | `str` | No       | nearest           | Expiration date in YYYY-MM-DD format |
| `ratio_type`      | `str` | No       | `"open_interest"` | `"open_interest"` or `"volume"`      |

**Returns**: JSON with `put_call_ratio`, `interpretation` (Bullish/Neutral/Bearish), and detailed breakdown.

```
>>> pcr = await calculate_put_call_ratio("SPY", ratio_type="volume")
```

### `calculate_greeks`

Calculate Options Greeks using Black-Scholes model.

| Parameter         | Type    | Required | Default        | Description                          |
| ----------------- | ------- | -------- | -------------- | ------------------------------------ |
| `symbol`          | `str`   | Yes      | -              | Stock ticker symbol                  |
| `expiration_date` | `str`   | No       | nearest future | Expiration date in YYYY-MM-DD format |
| `risk_free_rate`  | `float` | No       | `0.05`         | Risk-free interest rate (5%)         |

**Returns**: JSON with ATM Greeks (`delta`, `gamma`, `theta`, `vega`, `rho`), all-strike Greeks, and net delta summary.

```
>>> greeks = await calculate_greeks("AAPL")
```

### `calculate_iv_metrics`

Calculate IV Rank and IV Percentile.

| Parameter       | Type  | Required | Default | Description                      |
| --------------- | ----- | -------- | ------- | -------------------------------- |
| `symbol`        | `str` | Yes      | -       | Stock ticker symbol              |
| `lookback_days` | `int` | No       | `252`   | Historical period (trading days) |

**Returns**: JSON with `current_iv`, `iv_rank` (0-100), `iv_percentile` (0-100), 52-week IV range, and `interpretation` (strategy suggestion).

```
>>> iv = await calculate_iv_metrics("AAPL")
# iv_rank > 75 → "Consider selling options"
# iv_rank < 25 → "Consider buying options"
```

### `calculate_max_pain`

Calculate Max Pain price for options expiration.

| Parameter         | Type  | Required | Default        | Description                          |
| ----------------- | ----- | -------- | -------------- | ------------------------------------ |
| `symbol`          | `str` | Yes      | -              | Stock ticker symbol                  |
| `expiration_date` | `str` | No       | nearest future | Expiration date in YYYY-MM-DD format |

**Returns**: JSON with `max_pain_strike`, `distance_to_max_pain`, `expected_move`, `interpretation`, and pain distribution by strike.

```
>>> max_pain = await calculate_max_pain("SPY")
```

---

## Portfolio Analytics

Advanced portfolio performance metrics. Requires an IB Flex Query XML file.

### `calculate_portfolio_metrics`

Calculate advanced risk-adjusted performance metrics.

| Parameter        | Type    | Required | Default | Description                           |
| ---------------- | ------- | -------- | ------- | ------------------------------------- |
| `file_path`      | `str`   | Yes      | -       | Path to IB Flex Query XML file        |
| `benchmark`      | `str`   | No       | `"SPY"` | Benchmark symbol                      |
| `risk_free_rate` | `float` | No       | `0.05`  | Risk-free rate (5%)                   |
| `period`         | `str`   | No       | `"1y"`  | `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y` |

**Returns**: JSON with `return_metrics` (total/annualized return, volatility), `risk_adjusted_metrics` (Sharpe, Sortino, Calmar, Treynor, Information Ratio), `risk_metrics` (max drawdown, beta, tracking error), and `interpretation`.

```
>>> metrics = await calculate_portfolio_metrics(
...     file_path="data/raw/U1234567_2025-01-01_2025-06-30.xml",
...     benchmark="SPY",
...     period="1y"
... )
```

### `analyze_portfolio_correlation`

Analyze correlation between portfolio positions.

| Parameter   | Type  | Required | Default | Description                           |
| ----------- | ----- | -------- | ------- | ------------------------------------- |
| `file_path` | `str` | Yes      | -       | Path to IB Flex Query XML file        |
| `period`    | `str` | No       | `"1y"`  | `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y` |

**Returns**: JSON with `correlation_matrix`, `high_correlation_pairs` (>0.7), `position_weights`, `diversification_score`, and `interpretation`.

```
>>> correlation = await analyze_portfolio_correlation(
...     file_path="data/raw/U1234567_2025-01-01_2025-06-30.xml"
... )
```

---

## Market Comparison

### `compare_with_benchmark`

Compare stock/fund performance against a benchmark.

| Parameter   | Type  | Required | Default | Description                                  |
| ----------- | ----- | -------- | ------- | -------------------------------------------- |
| `symbol`    | `str` | Yes      | -       | Stock ticker symbol to compare               |
| `benchmark` | `str` | No       | `"SPY"` | Benchmark symbol                             |
| `period`    | `str` | No       | `"1y"`  | `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `max` |

**Returns**: JSON with `performance` (returns, outperformance, volatility), `risk_metrics` (beta, alpha, correlation, Sharpe), and `interpretation`.

```
>>> result = await compare_with_benchmark("VOO", benchmark="SPY", period="1y")
```

### `get_analyst_consensus`

Get analyst consensus and recommendations.

| Parameter | Type  | Required | Default | Description         |
| --------- | ----- | -------- | ------- | ------------------- |
| `symbol`  | `str` | Yes      | -       | Stock ticker symbol |

**Returns**: JSON with `analyst_recommendations` (buy/sell/hold counts, consensus), `target_price` (mean, high, low, upside potential), and `earnings_estimates`.

```
>>> consensus = await get_analyst_consensus("AAPL")
```

---

## ETF Comparison

### `compare_etf_performance`

Compare multiple ETFs with dividend-adjusted performance.

| Parameter | Type  | Required | Default | Description                                             |
| --------- | ----- | -------- | ------- | ------------------------------------------------------- |
| `symbols` | `str` | Yes      | -       | Comma-separated symbols (max 10), e.g., "VOO,CSPX,VWRA" |
| `period`  | `str` | No       | `"1y"`  | `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `max`     |

**Returns**: JSON with per-ETF `returns` (total, annualized, YTD, best/worst month), `risk` (volatility, Sharpe, Sortino, max drawdown, Calmar), `dividends` (yield, annual amount), `costs` (expense ratio), `market_metrics` (beta, 52-week range), `correlation_analysis`, and `investment_insights` (recommendations).

```
>>> comparison = await compare_etf_performance("VOO,CSPX,VWRA,IDTL,TLT", period="1y")
```

---

## Technical Analysis

### `get_stock_analysis`

Get comprehensive technical analysis with actionable signals.

| Parameter       | Type  | Required | Default | Description                                   |
| --------------- | ----- | -------- | ------- | --------------------------------------------- |
| `symbol`        | `str` | Yes      | -       | Stock ticker symbol                           |
| `timeframe`     | `str` | No       | `"1d"`  | `1d` (daily), `1wk` (weekly), `1mo` (monthly) |
| `lookback_days` | `int` | No       | `252`   | Historical data period (~1 year)              |

**Returns**: JSON with `support_resistance` (levels with strength), `trend_analysis` (short/medium/long term), `technical_indicators` (RSI, MACD, ADX, ATR), `pivot_points` (classic, Fibonacci), `volume_analysis`, and `trading_signals` (recommendation, confidence, entry/exit zones, risk/reward).

```
>>> analysis = await get_stock_analysis("AAPL", timeframe="1d")
```

### `get_multi_timeframe_analysis`

Analyze stock across daily, weekly, and monthly timeframes for confluence.

| Parameter | Type  | Required | Default | Description         |
| --------- | ----- | -------- | ------- | ------------------- |
| `symbol`  | `str` | Yes      | -       | Stock ticker symbol |

**Returns**: JSON with individual timeframe analyses and `confluence_analysis` (score, trend alignment, divergences, recommendation).

```
>>> mtf = await get_multi_timeframe_analysis("AAPL")
```

---

## Position History

SQLite-based position tracking tools. Requires data synced via `fetch_ib_data`.

### `get_position_history`

Get position history for a symbol over a date range.

| Parameter    | Type  | Required | Default                         | Description                     |
| ------------ | ----- | -------- | ------------------------------- | ------------------------------- |
| `account_id` | `str` | Yes      | -                               | Account ID (e.g., "U1234567")   |
| `symbol`     | `str` | Yes      | -                               | Trading symbol                  |
| `start_date` | `str` | Yes      | -                               | Start date in YYYY-MM-DD format |
| `end_date`   | `str` | Yes      | -                               | End date in YYYY-MM-DD format   |
| `db_path`    | `str` | No       | `"data/processed/positions.db"` | Path to SQLite database         |

**Returns**: JSON with daily position snapshots (dates, quantities, prices, P&L).

```
>>> history = await get_position_history("U1234567", "PG", "2025-01-01", "2025-10-15")
```

### `get_portfolio_snapshot`

Get all positions for an account on a specific date.

| Parameter       | Type  | Required | Default                         | Description               |
| --------------- | ----- | -------- | ------------------------------- | ------------------------- |
| `account_id`    | `str` | Yes      | -                               | Account ID                |
| `snapshot_date` | `str` | Yes      | -                               | Date in YYYY-MM-DD format |
| `db_path`       | `str` | No       | `"data/processed/positions.db"` | Path to SQLite database   |

**Returns**: JSON with all positions on that date, total value, and total unrealized P&L.

### `compare_portfolio_snapshots`

Compare portfolio composition between two dates.

| Parameter    | Type  | Required | Default                         | Description                      |
| ------------ | ----- | -------- | ------------------------------- | -------------------------------- |
| `account_id` | `str` | Yes      | -                               | Account ID                       |
| `date1`      | `str` | Yes      | -                               | First date in YYYY-MM-DD format  |
| `date2`      | `str` | Yes      | -                               | Second date in YYYY-MM-DD format |
| `db_path`    | `str` | No       | `"data/processed/positions.db"` | Path to SQLite database          |

**Returns**: JSON with added, removed, and changed positions between the two dates.

### `get_position_statistics`

Get statistical summary for a position over a date range.

| Parameter    | Type  | Required | Default                         | Description                     |
| ------------ | ----- | -------- | ------------------------------- | ------------------------------- |
| `account_id` | `str` | Yes      | -                               | Account ID                      |
| `symbol`     | `str` | Yes      | -                               | Trading symbol                  |
| `start_date` | `str` | Yes      | -                               | Start date in YYYY-MM-DD format |
| `end_date`   | `str` | Yes      | -                               | End date in YYYY-MM-DD format   |
| `db_path`    | `str` | No       | `"data/processed/positions.db"` | Path to SQLite database         |

**Returns**: JSON with min/max/average statistics for price, value, and P&L.

### `get_available_snapshot_dates`

List all dates with position snapshots stored in the database.

| Parameter    | Type  | Required | Default                         | Description             |
| ------------ | ----- | -------- | ------------------------------- | ----------------------- |
| `account_id` | `str` | Yes      | -                               | Account ID              |
| `db_path`    | `str` | No       | `"data/processed/positions.db"` | Path to SQLite database |

**Returns**: JSON with list of available dates in descending order.

---

## ETF Calculator

Deterministic ETF swap calculation tools. All arithmetic is performed in Python to prevent LLM calculation errors.

### `calculate_etf_swap`

Calculate ETF swap requirements with exact share counts.

| Parameter              | Type    | Required | Default  | Description                                  |
| ---------------------- | ------- | -------- | -------- | -------------------------------------------- |
| `from_symbol`          | `str`   | Yes      | -        | Symbol of ETF to sell                        |
| `from_shares`          | `int`   | Yes      | -        | Number of shares to sell                     |
| `from_price`           | `float` | Yes      | -        | Current price of from_symbol                 |
| `from_expense_ratio`   | `float` | Yes      | -        | Expense ratio as decimal (e.g., 0.0003)      |
| `from_dividend_yield`  | `float` | Yes      | -        | Dividend yield as decimal (e.g., 0.0115)     |
| `from_withholding_tax` | `float` | Yes      | -        | Withholding tax rate as decimal (e.g., 0.30) |
| `to_symbol`            | `str`   | Yes      | -        | Symbol of ETF to buy                         |
| `to_price`             | `float` | Yes      | -        | Current price of to_symbol                   |
| `to_expense_ratio`     | `float` | Yes      | -        | Expense ratio as decimal                     |
| `to_dividend_yield`    | `float` | Yes      | -        | Dividend yield as decimal                    |
| `to_withholding_tax`   | `float` | Yes      | -        | Withholding tax rate as decimal              |
| `trading_fee_usd`      | `float` | No       | env/75.0 | Trading fee in USD                           |

**Returns**: JSON with required shares, purchase amount, surplus/deficit cash, annual tax savings, expense changes, and payback period in months.

```
>>> result = calculate_etf_swap(
...     from_symbol="TLT", from_shares=200, from_price=91.34,
...     from_expense_ratio=0.0015, from_dividend_yield=0.0433,
...     from_withholding_tax=0.30,
...     to_symbol="IDTL", to_price=3.40,
...     to_expense_ratio=0.0007, to_dividend_yield=0.0445,
...     to_withholding_tax=0.15
... )
```

### `calculate_portfolio_swap`

Calculate multiple ETF swaps for portfolio restructuring.

| Parameter         | Type    | Required | Default  | Description                                  |
| ----------------- | ------- | -------- | -------- | -------------------------------------------- |
| `swaps`           | `str`   | Yes      | -        | JSON string with list of swap specifications |
| `trading_fee_usd` | `float` | No       | env/75.0 | Trading fee in USD                           |

**Returns**: JSON with individual swap calculations and portfolio-wide summary (total tax savings, total payback period).

### `validate_etf_price_mcp`

Validate ETF price for potential errors before calculations.

| Parameter          | Type    | Required | Default | Description                       |
| ------------------ | ------- | -------- | ------- | --------------------------------- |
| `symbol`           | `str`   | Yes      | -       | ETF symbol to validate            |
| `price`            | `float` | Yes      | -       | Price to validate                 |
| `reference_symbol` | `str`   | No       | -       | Reference ETF symbol (same index) |
| `reference_price`  | `float` | No       | -       | Reference ETF price               |

**Returns**: JSON with `is_valid`, `warnings`, and `price_ratio` (if reference provided).

---

## Sentiment Analysis

### `analyze_market_sentiment`

Analyze market sentiment from multiple sources.

| Parameter       | Type      | Required | Default  | Description                                 |
| --------------- | --------- | -------- | -------- | ------------------------------------------- |
| `symbol`        | `str`     | Yes      | -        | Stock ticker symbol                         |
| `lookback_days` | `int`     | No       | `7`      | Historical period (1-365 days)              |
| `sources`       | `Literal` | No       | `"news"` | `news`, `options`, `technical`, `composite` |

**Returns**: JSON with `sentiment_score` (-1.0 bearish to +1.0 bullish), `confidence` (0-1), `key_themes`, `risk_factors`, `interpretation` (Strong Bullish/Bearish/Neutral).

```
>>> sentiment = await analyze_market_sentiment("AAPL", sources="composite")
```

### `get_news_sentiment`

Convenience function for news-only sentiment analysis.

| Parameter | Type  | Required | Default | Description         |
| --------- | ----- | -------- | ------- | ------------------- |
| `symbol`  | `str` | Yes      | -       | Stock ticker symbol |

**Returns**: JSON with news sentiment score, confidence, key themes, and risk factors.

---

## Resources

Read-only data access via URI patterns. Resources automatically use the most recent data file.

| URI                                 | Description                                                                       |
| ----------------------------------- | --------------------------------------------------------------------------------- |
| `ib://portfolio/list`               | List all available portfolio XML files                                            |
| `ib://portfolio/latest`             | Summary of most recent portfolio file                                             |
| `ib://accounts/{account_id}`        | Data for a specific account ID                                                    |
| `ib://trades/recent`                | Most recent 10 trades                                                             |
| `ib://positions/current`            | Current positions from latest file                                                |
| `ib://strategy/tax-context`         | Tax planning context (gains/losses, harvesting opportunities, wash sale warnings) |
| `ib://strategy/rebalancing-context` | Rebalancing context (allocation, drift, suggested actions)                        |
| `ib://strategy/risk-context`        | Risk assessment (duration, scenarios, concentration, liquidity, maturity ladder)  |
| `ib://user/profile`                 | User investment profile from `notes/investor-profile.yaml`                        |

---

## Prompts

Reusable prompt templates for common analysis workflows. Each prompt generates a structured request for the LLM.

### `analyze_portfolio`

Comprehensive portfolio analysis covering performance, costs, bonds, tax, and risk.

| Parameter  | Type  | Description                    |
| ---------- | ----- | ------------------------------ |
| `csv_path` | `str` | Path to IB Flex Query CSV file |

### `tax_planning`

Tax analysis focused on realized gains, phantom income (OID), and optimization strategies.

| Parameter  | Type  | Description                    |
| ---------- | ----- | ------------------------------ |
| `csv_path` | `str` | Path to IB Flex Query CSV file |

### `risk_assessment`

Portfolio risk assessment with concentration, interest rate, and liquidity analysis.

| Parameter   | Type  | Description                                         |
| ----------- | ----- | --------------------------------------------------- |
| `csv_path`  | `str` | Path to IB Flex Query CSV file                      |
| `scenarios` | `str` | Interest rate scenarios (default: "1% up, 1% down") |

### `bond_portfolio_analysis`

Specialized zero-coupon bond (STRIPS) portfolio analysis with YTM, maturity profile, and tax impact.

| Parameter  | Type  | Description                    |
| ---------- | ----- | ------------------------------ |
| `csv_path` | `str` | Path to IB Flex Query CSV file |

### `monthly_performance_review`

Monthly trading performance review with best/worst trades, metrics, and action items.

| Parameter  | Type  | Description                       |
| ---------- | ----- | --------------------------------- |
| `csv_path` | `str` | Path to IB Flex Query CSV file    |
| `month`    | `str` | Month to review (e.g., "2025-01") |

---

## Tool Combinations

### Mode 1: Complete Analysis Workflow

```
1. fetch_ib_data("2025-01-01") → saves XML + syncs to SQLite
2. analyze_performance("2025-01-01") → trading performance
3. analyze_tax("2025-01-01") → tax implications
4. analyze_consolidated_portfolio("2025-01-01") → consolidated view
```

### Mode 2: Custom Analysis Workflow

```
1. get_trades("2025-01-01", asset_class="BOND") → filtered trades
2. calculate_metric("win_rate", "2025-01-01") → specific metric
3. compare_periods("2025-01-01", "2025-06-30", "2025-07-01", "2025-12-31") → period comparison
4. get_stock_data("AAPL", indicators="rsi,macd") → technical data
5. compare_etf_performance("VOO,CSPX,VWRA") → ETF comparison
```

### Investment Decision Workflow

```
1. get_stock_analysis("AAPL") → technical analysis
2. get_analyst_consensus("AAPL") → fundamental view
3. analyze_market_sentiment("AAPL", sources="composite") → sentiment
4. get_options_chain("AAPL") + calculate_iv_metrics("AAPL") → options context
5. calculate_max_pain("AAPL") → options market structure
```
