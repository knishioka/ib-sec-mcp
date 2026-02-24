---
description: Analyze sector allocation and concentration risk
allowed-tools: mcp__ib-sec-mcp__analyze_sector_allocation
argument-hint: [--start YYYY-MM-DD] [--account N]
---

Analyze portfolio sector allocation, concentration risk (HHI), and equity vs non-equity breakdown.

## Task

Call `analyze_sector_allocation` MCP tool and present results in a structured report.

### Argument Parsing

- If $ARGUMENTS contains `--start YYYY-MM-DD`: Use as start_date
- If $ARGUMENTS contains `--account N`: Use N as account_index
- Default start_date: `2025-01-01`
- Default account_index: `0`

### Steps

1. **Fetch Sector Data**

Call `mcp__ib-sec-mcp__analyze_sector_allocation` with parsed arguments.

2. **Present Report**

Format the JSON response into the output format below.

### Expected Output

```
=== Sector Allocation Analysis ===
Period: {start_date} to {end_date}
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

Equity Positions:    ${equity_value} ({equity_pct}%)
Non-Equity:          ${non_equity_value} ({non_equity_pct}%)
  - Bonds:           ${bond_value}
  - Cash:            ${cash_value}
  - Other:           ${other_value}

⚠️ CONCENTRATION RISK

HHI Score: {hhi_value}
Assessment: {LOW|MODERATE|HIGH}
  - LOW (< 1500): Well-diversified
  - MODERATE (1500-2500): Moderate concentration
  - HIGH (> 2500): High concentration risk

Top Sector Concentration:
  1. {sector}: {pct}% ← {assessment}
  2. {sector}: {pct}%
  3. {sector}: {pct}%

📋 PER-SECTOR POSITIONS

Technology (32.1%):
  - AAPL: $15,000 (10.7%)
  - MSFT: $12,000 (8.6%)
  - GOOGL: $10,000 (7.1%)
  - ...

Healthcare (20.0%):
  - JNJ: $15,000 (10.7%)
  - ...

💡 RECOMMENDATIONS

{Based on HHI assessment}:
- If HIGH: Consider diversifying away from {top_sector}
- If MODERATE: Monitor {top_sector} weight
- If LOW: Portfolio is well-diversified

=== NEXT STEPS ===

→ Check currency exposure (/fx-exposure)
→ Review dividend impact by sector (/dividend-analysis)
→ Full portfolio optimization (/optimize-portfolio)
```

### Error Handling

- If no positions found: Report "No positions found in account."
- If sector data unavailable for some positions: Show available data with "Unknown" sector for missing
- If MCP tool fails: Report error and suggest `/debug-api` for troubleshooting

### Examples

```
/sector-analysis
/sector-analysis --start 2024-01-01
/sector-analysis --account 1
/sector-analysis --start 2025-01-01 --account 0
```
