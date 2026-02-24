# Financial Calculators

This document describes the financial calculation formulas used in IB Analytics, with references to their implementation locations.

Calculations use Python's `Decimal` type for inputs, outputs, and most arithmetic. Some operations requiring exponentiation or square roots (YTM, CAGR, Sharpe Ratio) temporarily convert to `float` for `math` library compatibility, then convert the result back to `Decimal`. See [architecture.md](architecture.md) for where these fit in the system.

## Bond Calculations

### YTM (Yield to Maturity)

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_ytm()`

Calculates YTM for **zero-coupon bonds** using the standard formula:

```
YTM = (FV / PV)^(1/n) - 1
```

| Variable | Description                           | Type      |
| -------- | ------------------------------------- | --------- |
| FV       | Face value (par value)                | `Decimal` |
| PV       | Current market price (purchase price) | `Decimal` |
| n        | Years to maturity                     | `Decimal` |

**Returns**: YTM as percentage (e.g., `4.5` for 4.5%)

**Notes**:

- Only applicable to zero-coupon bonds (no coupon payments)
- Returns `0` if current price or years to maturity is zero
- Used internally by `calculate_phantom_income()` for OID calculation

### Duration (Macaulay Duration)

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_bond_duration()`

For **zero-coupon bonds**, Macaulay duration equals time to maturity:

```
Duration = n (years to maturity)
```

For coupon-bearing bonds, the general formula is:

```
D = (1/P) * sum(t * CF_t / (1 + y)^t, t=1..n)
```

| Variable | Description                 |
| -------- | --------------------------- |
| P        | Bond price                  |
| CF_t     | Cash flow at time t         |
| y        | Yield to maturity (decimal) |
| n        | Number of periods           |

**Notes**:

- Current implementation supports zero-coupon bonds only
- Duration is used as input for bond price change estimation (DV01)

### Bond Price Change / DV01

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_bond_price_change()`

Estimates new bond price using modified duration approximation:

```
dP/P = -D * dy
New Price = P + P * (-D * dy/100)
```

| Variable | Description                       | Type      |
| -------- | --------------------------------- | --------- |
| P        | Current bond price                | `Decimal` |
| D        | Bond duration (years)             | `Decimal` |
| dy       | Yield change in percentage points | `Decimal` |

**Returns**: Estimated new price after yield change

**DV01** (Dollar Value of 01) can be derived by setting `yield_change = 0.01` (1 basis point):

```python
dv01 = current_price - calculate_bond_price_change(current_price, duration, Decimal("0.01"))
```

**Notes**:

- Linear approximation; accuracy decreases for large yield changes
- Does not account for convexity

### Phantom Income (OID)

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_phantom_income()`

Calculates phantom income for zero-coupon bonds using the **constant yield method** per IRS Publication 1212:

```
YTM_decimal = (FV/PV)^(1/n) - 1
fraction = days_held / 365.25
growth_factor = (1 + YTM_decimal)^fraction
phantom_income = PV * (growth_factor - 1)
```

| Variable  | Description                 | Type      |
| --------- | --------------------------- | --------- |
| PV        | Purchase price (cost basis) | `Decimal` |
| FV        | Face value                  | `Decimal` |
| n         | Total years to maturity     | `Decimal` |
| days_held | Days held in the tax year   | `int`     |

**Returns**: Phantom income (OID accrual) for the period

**Used by**: `ib_sec_mcp/analyzers/tax.py` - `TaxAnalyzer._analyze_phantom_income()`

**Notes**:

- Phantom income is taxable even though no cash is received
- The tax analyzer applies a configurable tax rate (default 30%) to compute estimated tax liability
- Current implementation assumes position held for the entire tax year (simplified)
- Reference: [IRS Publication 1212](https://www.irs.gov/publications/p1212)

## Performance Metrics

### ROI (Return on Investment)

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_roi()`

```
ROI = ((Final Value - Initial Value) / Initial Value) * 100
```

**Returns**: ROI as percentage

### CAGR (Compound Annual Growth Rate)

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_cagr()`

```
CAGR = ((FV / IV)^(1/years) - 1) * 100
```

| Variable | Description                |
| -------- | -------------------------- |
| FV       | Final value                |
| IV       | Initial value              |
| years    | Investment period in years |

**Returns**: CAGR as percentage

### Sharpe Ratio

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_sharpe_ratio()`

```
Sharpe = (R_mean - R_f) / sigma
```

| Variable | Description                            | Default                |
| -------- | -------------------------------------- | ---------------------- |
| R_mean   | Mean period return                     | -                      |
| R_f      | Risk-free rate (annual)                | 3% (`Decimal("0.03")`) |
| sigma    | Standard deviation of returns (sample) | -                      |

**Returns**: Sharpe ratio (not annualized beyond the input frequency)

**Notes**:

- Requires at least 2 return periods
- Uses sample standard deviation (N-1 denominator)
- Returns `0` if standard deviation is zero

### Sortino Ratio

**Implementation**: `ib_sec_mcp/mcp/tools/portfolio_analytics.py` (MCP tool layer, uses numpy/pandas)

The Sortino Ratio is a variation of the Sharpe Ratio that only penalizes downside volatility:

```
Sortino = (R_annual - R_f) / sigma_downside
```

| Variable       | Description                            |
| -------------- | -------------------------------------- |
| R_annual       | Annualized portfolio return            |
| R_f            | Risk-free rate (annual)                |
| sigma_downside | Annualized downside standard deviation |

Where downside deviation uses only negative returns:

```
sigma_downside = std(returns[returns < 0]) * sqrt(252)
```

**Notes**:

- Not yet implemented in the core `PerformanceCalculator` class
- Computed in the MCP tools layer using Yahoo Finance historical data
- Also computed in `ib_sec_mcp/mcp/tools/etf_comparison.py` for ETF comparison

### Max Drawdown

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_max_drawdown()`

```
Drawdown_t = (Peak_t - Value_t) / Peak_t * 100
Max Drawdown = max(Drawdown_t) for all t
```

**Returns**: Tuple of `(max_drawdown_pct, peak_index, trough_index)`

**Notes**:

- Tracks running peak and measures percentage decline from that peak
- Returns both the percentage and the indices of peak/trough for time analysis

### Win Rate

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_win_rate()`

```
Win Rate = (Winning Trades / Total Trades with P&L) * 100
```

**Returns**: Tuple of `(win_rate_pct, winning_count, losing_count)`

**Notes**:

- Only considers trades with non-zero realized P&L
- Trades with zero P&L are excluded from the calculation

### Profit Factor

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_profit_factor()`

```
Profit Factor = Gross Profit / Gross Loss
```

**Returns**: Ratio (values > 1.0 indicate net profitability)

**Notes**:

- Returns `999.99` if there are profits but no losses
- Returns `0` if there are no trades or no profits

### Risk/Reward Ratio

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_risk_reward_ratio()`

```
Risk/Reward = Average Win / |Average Loss|
```

**Returns**: Ratio (higher is better)

### Commission Rate

**Implementation**: `ib_sec_mcp/core/calculator.py` - `PerformanceCalculator.calculate_commission_rate()`

```
Commission Rate = (Total Commissions / Total Volume) * 100
```

**Returns**: Commission rate as percentage of trading volume

## Known Limitations

| Limitation                    | Location                                       | Details                                                                                                                                                         |
| ----------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Zero-coupon bonds only        | `calculate_ytm()`, `calculate_bond_duration()` | YTM and duration assume zero-coupon bonds. Coupon-bearing bond support not yet implemented.                                                                     |
| Holding period classification | `analyzers/tax.py:43`                          | Uses `settle_date - trade_date` (settlement delay ~2 days) instead of actual acquisition-to-sale holding period. Almost all gains are classified as short-term. |
| Linear price approximation    | `calculate_bond_price_change()`                | Does not account for convexity; less accurate for large yield changes.                                                                                          |
| Sortino not in core           | `mcp/tools/portfolio_analytics.py`             | Sortino Ratio is only available via MCP tools (Yahoo Finance data), not in `PerformanceCalculator`.                                                             |

## References

- [IRS Publication 1212 - Guide to OID Instruments](https://www.irs.gov/publications/p1212)
- [Investopedia - Sharpe Ratio](https://www.investopedia.com/terms/s/sharperatio.asp)
- [Investopedia - Sortino Ratio](https://www.investopedia.com/terms/s/sortinoratio.asp)
- [Investopedia - Yield to Maturity](https://www.investopedia.com/terms/y/yieldtomaturity.asp)
- [Investopedia - Duration](https://www.investopedia.com/terms/d/duration.asp)
