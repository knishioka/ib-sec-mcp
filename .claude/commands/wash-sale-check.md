---
description: Detect wash sale violations and tax loss harvesting opportunities
allowed-tools: mcp__ib-sec-mcp__calculate_tax_loss_harvesting
argument-hint: [--start YYYY-MM-DD] [--tax-rate 0.30] [--account N]
---

Check for wash sale rule violations (30-day window), identify tax loss harvesting opportunities, and suggest Ireland-domiciled alternative ETFs.

## Task

Call `calculate_tax_loss_harvesting` MCP tool and present results in a structured report.

### Argument Parsing

- If $ARGUMENTS contains `--start YYYY-MM-DD`: Use as start_date
- If $ARGUMENTS contains `--tax-rate X.XX`: Use as tax_rate (decimal string, e.g., "0.30")
- If $ARGUMENTS contains `--account N`: Use N as account_index
- Default start_date: `2025-01-01`
- Default tax_rate: `"0.30"` (30%)
- Default account_index: `0`

### Steps

1. **Fetch Tax Loss Harvesting Data**

Call `mcp__ib-sec-mcp__calculate_tax_loss_harvesting` with parsed arguments.

2. **Present Report**

Format the JSON response into the output format below, with emphasis on wash sale warnings.

### Expected Output

```
=== Wash Sale & Tax Loss Harvesting Report ===
Period: {start_date} to {end_date}
Account: {account_id}
Tax Rate: {tax_rate}%

⚠️ WASH SALE WARNINGS

{If wash sale violations found}:
Symbol | Sell Date  | Buy Date   | Days Apart | Status      | Disallowed Loss
-------|------------|------------|------------|-------------|----------------
ABC    | 2025-09-15 | 2025-10-01 | 16 days    | ⚠️ VIOLATION | $890
XYZ    | 2025-08-10 | 2025-09-20 | 41 days    | ✅ CLEAR     | $0

Forward-Looking Wash Sale Risk:
  Positions sold at loss in last 30 days:
  - {symbol}: Sold {date}, avoid repurchase until {date + 31 days}

Backward-Looking Wash Sale Risk:
  Positions purchased in last 30 days with prior loss:
  - {symbol}: Bought {date}, loss on {prior_sale_date} may be disallowed

{If no violations}: ✅ No wash sale violations detected.

💰 TAX LOSS HARVESTING OPPORTUNITIES

Total Unrealized Losses: -${total_unrealized_loss}
Potential Tax Savings:   ${potential_tax_savings} (at {tax_rate}% rate)

Rank | Symbol | Unrealized Loss | Tax Savings | Wash Sale Risk | Alternative
-----|--------|-----------------|-------------|----------------|------------
1    | VTI    | -$2,500         | $750        | ✅ Safe        | IWDA (IE)
2    | QQQ    | -$1,200         | $360        | ⚠️ 30-day wait | CNDX (IE)
...

🏷️ IRELAND-DOMICILED ALTERNATIVES

For each loss position, suggested IE-domiciled ETF to maintain exposure:
1. VTI → IWDA (IE00B4L5Y983) - MSCI World
2. QQQ → CNDX (IE00B53SZB19) - Nasdaq 100
3. SPY → CSPX (IE00B5BMR087) - S&P 500

Benefits of IE-domiciled switch:
  - Lower withholding tax: 30% → 15%
  - Maintains market exposure during 31-day wash sale window
  - Avoids substantially identical security rule

💡 HARVESTING STRATEGY

Priority Actions:
1. 🎯 {symbol}: Harvest -${loss} → Save ${savings} in taxes
   - Sell and replace with {ie_alternative}
   - Wait 31 days before repurchasing original

2. 🎯 {symbol}: Harvest -${loss} → Save ${savings} in taxes
   - Safe to harvest (no recent wash sale risk)

⏰ Timing Considerations:
  - Settlement: T+1 for stocks, T+2 for bonds
  - Repurchase window: 31 days from settlement date
  - Year-end deadline: Last trading day of {year}

=== NEXT STEPS ===

→ Review dividend impact before selling (/dividend-analysis)
→ Check sector impact of restructuring (/sector-analysis)
→ Full tax report (/tax-report)
```

### Error Handling

- If no loss positions found: Report "No unrealized loss positions found. Portfolio is fully in gain."
- If invalid tax_rate: Report "Invalid tax rate. Use decimal format, e.g., --tax-rate 0.30 for 30%"
- If MCP tool fails: Report error and suggest `/debug-api` for troubleshooting

### Examples

```
/wash-sale-check
/wash-sale-check --start 2024-01-01
/wash-sale-check --tax-rate 0.20
/wash-sale-check --account 1
/wash-sale-check --start 2025-01-01 --tax-rate 0.30 --account 0
```
