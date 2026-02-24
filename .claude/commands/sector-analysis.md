---
description: Analyze portfolio sector allocation, concentration risk (HHI score), and diversification quality
allowed-tools: mcp__ib-sec-mcp__analyze_sector_allocation, mcp__ib-sec-mcp__get_positions
argument-hint: [--start YYYY-MM-DD] [--account N]
---

Analyze how your portfolio is distributed across sectors (Technology, Healthcare, Financials, etc.), calculate concentration risk using the HHI score, and identify if you are over-exposed to any single sector.

**When to use this command**:

- You want to see which sectors dominate your portfolio
- You're concerned about over-concentration in one industry (e.g., too much Tech)
- You want a diversification quality score

## Task

### Step 1: Parse Arguments

From `$ARGUMENTS`, extract:

- `start_date`: Look for `--start YYYY-MM-DD`. Also accept natural language: "2024年から" → "2024-01-01", "今年" → current year Jan 1, "去年" → last year Jan 1. Default: `"2025-01-01"`.
- `account_index`: Look for `--account N`. Default: `0`.

### Step 2: Fetch Sector Data

Call the MCP tool with the following parameters:

```
mcp__ib-sec-mcp__analyze_sector_allocation(
  start_date=<start_date>,
  account_index=<account_index>
)
```

### Step 3: Present Report

Format the JSON response. The HHI (Herfindahl-Hirschman Index) measures concentration:

- Below 1500 = well-diversified ✅
- 1500–2500 = moderate concentration ⚠️
- Above 2500 = high concentration risk ❌

### Expected Output

```
=== Sector Allocation Analysis ===
Period: {start_date} to today
Account: {account_id}

📊 SECTOR BREAKDOWN

Sector              | Value       | Weight  | # Positions
--------------------|-------------|---------|------------
Technology          | $45,000     | 32.1%   | 5
Healthcare          | $28,000     | 20.0%   | 3
Financial Services  | $18,000     | 12.9%   | 4
Consumer Defensive  | $15,000     | 10.7%   | 2
...

📈 EQUITY vs NON-EQUITY

Equity Positions:    {equity_count} positions ({equity_pct}% of portfolio)
Non-Equity (Bonds, Cash, etc.): {non_equity_count} positions ({non_equity_pct}%)
Total:               {position_count} positions

⚠️ CONCENTRATION RISK (HHI Score)

HHI Score:   {hhi}
Assessment:  {LOW ✅ / MODERATE ⚠️ / HIGH ❌}

  LOW  (HHI < 1500): Portfolio is well-diversified
  MOD  (HHI 1500–2500): Some concentration, monitor top sectors
  HIGH (HHI > 2500): Significant concentration risk, consider rebalancing

Top Sector Weights:
  1. {sector}: {pct}% {← HIGH if >40%}
  2. {sector}: {pct}%
  3. {sector}: {pct}%

📋 POSITIONS BY SECTOR

Technology (32.1%):
  - AAPL: $15,000 (10.7%)
  - MSFT: $12,000 (8.6%)
  ...

Healthcare (20.0%):
  - JNJ: $15,000 (10.7%)
  ...

💡 RECOMMENDATIONS

{If HIGH concentration}:
  ⚠️ Consider reducing {top_sector} exposure. It represents {pct}% of equity portfolio.
  → Options: Sell partial {symbol}, add positions in underrepresented sectors

{If MODERATE}:
  → Monitor {top_sector} weight. Aim to keep any single sector below 30%.

{If LOW}:
  ✅ Portfolio is well-diversified. No immediate action needed.

=== NEXT STEPS ===
→ Check currency exposure by region (/fx-exposure)
→ Review dividend income by sector (/dividend-analysis)
→ Full portfolio optimization (/optimize-portfolio)
```

### Error Handling

- **No positions found**: Print "No positions found in account {account_index}. Try `/fetch-latest` to load data."
- **Sector data unavailable for some tickers**: Show what is available; mark missing as "Unknown sector". Do not abort.
- **MCP tool fails**: Print the error, then suggest `/mcp-status` and `/debug-api`.

### Examples

```
/sector-analysis
/sector-analysis --start 2024-01-01
/sector-analysis --account 1
/sector-analysis 今年
/sector-analysis 2024年から --account 0
```
