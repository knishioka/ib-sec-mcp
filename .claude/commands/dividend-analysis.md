---
description: Analyze dividend income and Ireland-domiciled ETF tax efficiency
allowed-tools: mcp__ib-sec-mcp__analyze_dividend_income
argument-hint: [--start YYYY-MM-DD] [--account N]
---

Analyze dividend income for held equity positions, including withholding tax by domicile and potential tax savings from restructuring to Ireland-domiciled ETFs.

## Task

Call `analyze_dividend_income` MCP tool and present results in a structured report.

### Argument Parsing

- If $ARGUMENTS contains `--start YYYY-MM-DD`: Use as start_date
- If $ARGUMENTS contains `--account N`: Use N as account_index
- Default start_date: `2025-01-01`
- Default account_index: `0`

### Steps

1. **Fetch Dividend Data**

Call `mcp__ib-sec-mcp__analyze_dividend_income` with parsed arguments.

2. **Present Report**

Format the JSON response into the output format below.

### Expected Output

```
=== Dividend Income Analysis ===
Period: {start_date} to {end_date}
Account: {account_id}

📊 PORTFOLIO DIVIDEND SUMMARY

Total Annual Dividend (Gross): ${total_annual_dividend}
Total Withholding Tax:         -${total_withholding_tax}
Total Net Receipt:             ${total_net_receipt}
Portfolio Yield:               {weighted_avg_yield}%

💰 POTENTIAL TAX SAVINGS (US → Ireland Restructuring)

Total Potential Savings:       ${total_potential_ie_savings}/year
  - IE domicile withholding:   15% (treaty rate)
  - US domicile withholding:   30% (default rate)

📈 POSITIONS BY DIVIDEND YIELD (Descending)

Rank | Symbol | Yield | Annual Div | WHT Rate | Net Receipt | Domicile
-----|--------|-------|------------|----------|-------------|--------
1    | VYM    | 3.2%  | $1,200     | 30%      | $840        | US
2    | VHYL   | 2.8%  | $980       | 15%      | $833        | IE ✅
...

🏷️ DOMICILE BREAKDOWN

Ireland-Domiciled (IE):
  - Positions: N
  - WHT Rate: 15%
  - Total Dividends: $X,XXX

US-Domiciled:
  - Positions: N
  - WHT Rate: 30%
  - Total Dividends: $X,XXX

💡 RESTRUCTURING RECOMMENDATIONS

Positions with highest IE savings potential:
1. {symbol}: Switch to IE equivalent → Save ${savings}/year
2. {symbol}: Switch to IE equivalent → Save ${savings}/year

=== NEXT STEPS ===

→ Review IE-domiciled alternatives for US ETFs
→ Consider tax-loss harvesting before restructuring (/wash-sale-check)
→ Check sector impact of restructuring (/sector-analysis)
```

### Error Handling

- If no equity positions found: Report "No equity positions found. Dividend analysis requires stock/ETF positions."
- If MCP tool fails: Report error and suggest `/debug-api` for troubleshooting
- If Yahoo Finance data unavailable for some positions: Show available data with warning for missing positions

### Examples

```
/dividend-analysis
/dividend-analysis --start 2024-01-01
/dividend-analysis --account 1
/dividend-analysis --start 2025-01-01 --account 0
```
