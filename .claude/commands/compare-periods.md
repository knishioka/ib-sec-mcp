---
description: Compare portfolio performance across two time periods
allowed-tools: Read, Glob, Bash(python:*), mcp__ib-sec-mcp__analyze_performance, mcp__ib-sec-mcp__get_portfolio_summary
argument-hint: period1-start period1-end period2-start period2-end
---

Compare trading performance and metrics between two time periods to identify trends and changes.

## Task

Analyze and compare portfolio performance across two periods. Arguments format:

**$ARGUMENTS Format**:
- `YYYY-MM-DD YYYY-MM-DD YYYY-MM-DD YYYY-MM-DD` (period1-start period1-end period2-start period2-end)
- Or: `--ytd` (compare current YTD vs previous YTD)
- Or: `--quarter` (compare current quarter vs previous quarter)
- Or: `--month` (compare current month vs previous month)

### Analysis Steps

**1. Determine Periods**
- Parse $ARGUMENTS for date ranges
- Or use preset comparisons (YTD, quarter, month)

**2. Load Data for Both Periods**
```python
# Period 1
perf1 = mcp__ib-sec-mcp__analyze_performance(
    start_date="YYYY-MM-DD",
    end_date="YYYY-MM-DD"
)

# Period 2
perf2 = mcp__ib-sec-mcp__analyze_performance(
    start_date="YYYY-MM-DD",
    end_date="YYYY-MM-DD"
)
```

**3. Calculate Deltas**
For each metric:
- Absolute change: `metric2 - metric1`
- Percentage change: `((metric2 - metric1) / metric1) * 100`
- Trend: `IMPROVING` or `DEGRADING`

**4. Attribution Analysis**
Identify what changed:
- New positions
- Closed positions
- Strategy shifts
- Cost changes

### Expected Output

```
=== Period Comparison Analysis ===

📅 PERIOD 1: 2025-01-01 to 2025-03-31 (Q1)
📅 PERIOD 2: 2025-04-01 to 2025-06-30 (Q2)

📊 PERFORMANCE COMPARISON

Metric                | Period 1    | Period 2    | Change      | Trend
---------------------|-------------|-------------|-------------|-------------
Total P&L            | $5,234      | $6,789      | +$1,555     | ↗ IMPROVING
                     |             |             | (+29.7%)    |
Win Rate             | 62.5%       | 68.3%       | +5.8 pp     | ↗ IMPROVING
Profit Factor        | 1.45        | 1.68        | +0.23       | ↗ IMPROVING
                     |             |             | (+15.9%)    |
Avg Win              | $342        | $398        | +$56        | ↗ IMPROVING
                     |             |             | (+16.4%)    |
Avg Loss             | -$198       | -$165       | +$33        | ↗ IMPROVING
                     |             |             | (-16.7%)    |
Total Trades         | 48          | 52          | +4          | →
                     |             |             | (+8.3%)     |
ROI                  | 5.2%        | 6.8%        | +1.6 pp     | ↗ IMPROVING

💰 COST COMPARISON

Total Commissions    | $143        | $156        | +$13        | ↘ DEGRADING
                     |             |             | (+9.1%)     |
Cost per Trade       | $2.98       | $3.00       | +$0.02      | → STABLE
Commission %         | 0.29%       | 0.31%       | +0.02 pp    | ↘ DEGRADING

🎯 KEY CHANGES

What Improved:
✅ Win rate increased 5.8 percentage points
✅ Average win size up 16.4%
✅ Profit factor improved from 1.45 to 1.68
✅ Smaller average losses (-16.7%)

What Degraded:
⚠️ Higher total commissions (+9.1%)
⚠️ Commission percentage increased slightly

What Stayed Stable:
→ Cost per trade remained consistent
→ Trade frequency similar

📈 ATTRIBUTION ANALYSIS

New Positions (Period 2):
- Symbol ABC: 3 trades, +$890 P&L
- Symbol XYZ: 2 trades, +$234 P&L

Closed Positions (from Period 1):
- Symbol OLD: No longer traded
- May account for improved metrics

Strategy Changes:
💡 Increased selectivity (higher win rate, fewer trades)
💡 Better risk management (smaller losses)
⚠️ Higher commission % suggests smaller position sizes

🔍 INSIGHTS & RECOMMENDATIONS

Positive Trends:
1. ✅ Trading discipline improving (win rate, profit factor up)
2. ✅ Risk management effective (reduced average loss)
3. ✅ Consistent profitability across both periods

Areas to Monitor:
1. ⚠️ Commission percentage creeping up - review trade sizing
2. 💡 Consider bulk trades to optimize fees
3. 👀 Continue current strategy - showing clear improvement

Overall Assessment: 📈 IMPROVING PERFORMANCE
- Period 2 shows meaningful improvement in key metrics
- Risk-adjusted returns are trending positively
- Minor cost efficiency concerns, but overall strong progress
```

### Preset Comparisons

**Year-to-Date** (`/compare-periods --ytd`):
- Period 1: Jan 1 to Current Date (Previous Year)
- Period 2: Jan 1 to Current Date (Current Year)

**Quarter-over-Quarter** (`/compare-periods --quarter`):
- Period 1: Previous Quarter
- Period 2: Current Quarter

**Month-over-Month** (`/compare-periods --month`):
- Period 1: Previous Month
- Period 2: Current Month

### Examples

```
/compare-periods 2025-01-01 2025-03-31 2025-04-01 2025-06-30
/compare-periods --ytd
/compare-periods --quarter
/compare-periods --month
```

Delegate to **data-analyzer** subagent for detailed metric analysis and trend identification.
