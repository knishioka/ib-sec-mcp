---
description: Analyze dividend income from portfolio positions and compare Ireland vs US ETF tax efficiency
allowed-tools: mcp__ib-sec-mcp__analyze_dividend_income, mcp__ib-sec-mcp__get_positions
argument-hint: [--start YYYY-MM-DD] [--account N]
---

Analyze dividend income for all held equity positions. Shows annual dividend estimates, withholding tax by country of domicile, and how much tax you could save by switching from US-domiciled to Ireland-domiciled ETFs.

**When to use this command**:

- You want to see how much dividend income your portfolio generates
- You want to compare Ireland ETFs (15% withholding tax) vs US ETFs (30% withholding tax)
- You're planning to restructure your ETF holdings for better tax efficiency

## Task

### Step 1: Parse Arguments

From `$ARGUMENTS`, extract:

- `start_date`: Look for `--start YYYY-MM-DD`. Also accept natural language like "2024年から" → "2024-01-01", "今年" → current year Jan 1, "去年" → last year Jan 1. Default: `"2025-01-01"`.
- `account_index`: Look for `--account N`. Default: `0`.

### Step 2: Fetch Dividend Data

Call the MCP tool with the following parameters:

```
mcp__ib-sec-mcp__analyze_dividend_income(
  start_date=<start_date>,
  account_index=<account_index>
)
```

### Step 3: Present Report

Format the JSON response into the structure below. All monetary values in USD unless the response indicates otherwise.

### Expected Output

```
=== Dividend Income Analysis ===
Period: {start_date} to today
Account: {account_id}

📊 PORTFOLIO DIVIDEND SUMMARY

Total Annual Dividend (Gross): ${total_annual_dividend}
Total Withholding Tax:         -${total_withholding_tax}
Total Net Receipt:             ${total_net_receipt}
Portfolio Yield:               {weighted_avg_yield}%

💰 POTENTIAL TAX SAVINGS (Switch US → Ireland-domiciled ETFs)

Total Potential Annual Savings: ${total_potential_ie_savings}
  Reason: Ireland ETFs: 15% withholding tax vs US ETFs: 30%

📈 ALL DIVIDEND POSITIONS (sorted by annual dividend, highest first)

Rank | Symbol | Yield | Annual Div | WHT Rate | Net Receipt | Domicile
-----|--------|-------|------------|----------|-------------|--------
1    | VYM    | 3.2%  | $1,200     | 30%      | $840        | US ← consider switching to IE
2    | VHYL   | 2.8%  | $980       | 15%      | $833        | IE ✅
...

🏷️ DOMICILE BREAKDOWN

Ireland-Domiciled (IE): {N} positions, WHT 15%, Total dividends ${X}
US-Domiciled (US):      {N} positions, WHT 30%, Total dividends ${X}

💡 RESTRUCTURING RECOMMENDATIONS

Top savings opportunities (switch to Ireland equivalent):
1. {symbol}: Estimated savings ${savings}/year → consider {ie_alternative}
2. {symbol}: Estimated savings ${savings}/year → consider {ie_alternative}

=== NEXT STEPS ===
→ Check wash sale risk before selling (/wash-sale-check)
→ Review sector impact of restructuring (/sector-analysis)
→ Full portfolio optimization (/optimize-portfolio)
```

### Error Handling

- **No equity positions found**: Print "No equity positions found. This analysis requires stock or ETF positions with dividend data."
- **Yahoo Finance data unavailable for some positions**: Show available data and note "[Yahoo Finance data unavailable]" for missing positions. Do not abort.
- **MCP tool fails**: Print the error message, then suggest running `/mcp-status` to check server health and `/debug-api` for connection issues.

### Examples

```
/dividend-analysis
/dividend-analysis --start 2024-01-01
/dividend-analysis --account 1
/dividend-analysis 2024年から
/dividend-analysis 今年
```
