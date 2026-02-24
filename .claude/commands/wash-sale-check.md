---
description: Check wash sale rule violations (30-day window) and find tax loss harvesting opportunities with Ireland ETF alternatives
allowed-tools: mcp__ib-sec-mcp__calculate_tax_loss_harvesting, mcp__ib-sec-mcp__get_positions
argument-hint: [--start YYYY-MM-DD] [--tax-rate 0.30] [--account N]
---

Detect wash sale violations (selling at a loss then repurchasing within 30 days), identify positions where you could harvest tax losses, and suggest Ireland-domiciled ETF alternatives that maintain market exposure during the 31-day waiting period.

**When to use this command**:

- You want to reduce this year's capital gains tax by harvesting losses
- You want to check if any recent trades violated the wash sale rule
- You're planning to sell a losing position and want to know the safest alternative to hold during the 31-day window
- Tax year-end planning (typically October–December)

## Task

### Step 1: Parse Arguments

From `$ARGUMENTS`, extract:

- `start_date`: Look for `--start YYYY-MM-DD`. Also accept: "2024年から" → "2024-01-01", "今年" → current year Jan 1, "去年" → last year Jan 1. Default: `"2025-01-01"`.
- `tax_rate`: Look for `--tax-rate X.XX` (decimal, e.g., `0.30` = 30%). Also accept "30%" → 0.30, "20%" → 0.20. Default: `"0.30"` (Malaysia: capital gains tax 0%, but use this for withholding tax calculations).
- `account_index`: Look for `--account N`. Default: `0`.

### Step 2: Fetch Tax Loss Harvesting Data

Call the MCP tool with the following parameters:

```
mcp__ib-sec-mcp__calculate_tax_loss_harvesting(
  start_date=<start_date>,
  tax_rate=<tax_rate as string, e.g., "0.30">,
  account_index=<account_index>
)
```

### Step 3: Present Report

Format the JSON response. Emphasize wash sale warnings prominently — these are violations that reduce your deductible losses.

### Expected Output

```
=== Wash Sale & Tax Loss Harvesting Report ===
Period: {start_date} to today
Account: {account_id}
Tax Rate Used: {tax_rate * 100}%

⚠️ WASH SALE VIOLATIONS

{If violations found}:
Symbol | Sold Date  | Repurchased | Days Apart | Status       | Disallowed Loss
-------|------------|-------------|------------|--------------|----------------
ABC    | 2025-09-15 | 2025-10-01  | 16 days    | ⚠️ VIOLATION  | $890
XYZ    | 2025-08-10 | 2025-09-20  | 41 days    | ✅ OK (>30d)  | $0

{If no violations}: ✅ No wash sale violations detected.

Forward-Looking Risk (positions sold at a loss in the last 30 days):
  {symbol}: Sold {date} at a loss — avoid repurchasing until {date + 31 days}

Backward-Looking Risk (positions bought in the last 30 days with a prior loss):
  {symbol}: Bought {date} — the earlier loss on {prior_sale_date} may be disallowed

💰 TAX LOSS HARVESTING OPPORTUNITIES

Total Unrealized Losses Available: -${total_unrealized_loss}
Potential Tax Savings:             ${potential_tax_savings} (at {tax_rate * 100}% rate)

Rank | Symbol | Unrealized Loss | Tax Savings | Wash Sale Risk | Suggested IE Alternative
-----|--------|-----------------|-------------|----------------|-------------------------
1    | VTI    | -$2,500         | $750        | ✅ Safe now    | IWDA.L (IE-domiciled)
2    | QQQ    | -$1,200         | $360        | ⚠️ Wait 12d    | CNDX.L (IE-domiciled)
...

🏷️ IRELAND-DOMICILED ALTERNATIVES

Switching to Ireland ETFs during the 31-day window gives you:
  ✅ Maintains market exposure (avoids missing a potential rebound)
  ✅ Avoids "substantially identical security" rule (Ireland ≠ US version)
  ✅ Lower withholding tax (15%) vs US ETFs (30%)

Common substitutions:
  VTI / VTSAX → IWDA.L or SWRD.L (MSCI World, IE-domiciled)
  QQQ / QQQM  → CNDX.L (Nasdaq 100, IE-domiciled)
  SPY / VOO   → CSPX.L (S&P 500, IE-domiciled)

💡 PRIORITY HARVESTING ACTIONS

{For each top opportunity}:
1. 🎯 {symbol}: Harvest -${loss} → Est. tax saving: ${savings}
   - Action: Sell {symbol}, buy {ie_alternative} immediately
   - Repurchase window: Can buy back {symbol} after {date + 31 days}

⏰ TIMING NOTES
  - Settlement: T+1 (stocks); T+2 (bonds/ETFs on some exchanges)
  - Repurchase window: 31 days from settlement date (not trade date)
  - Year-end deadline: Complete trades by last trading day of {current_year}

=== NEXT STEPS ===
→ Review dividend impact before selling (/dividend-analysis)
→ Check sector exposure changes after restructuring (/sector-analysis)
→ Full tax report with capital gains summary (/tax-report)
```

### Error Handling

- **No unrealized loss positions**: Print "No unrealized loss positions found. Your portfolio is fully in gain — no harvesting needed right now."
- **Invalid tax_rate format**: Print "Tax rate must be a decimal between 0 and 1. Examples: `--tax-rate 0.30` (30%) or `--tax-rate 0.20` (20%)."
- **MCP tool fails**: Print the error, then suggest `/mcp-status` and `/debug-api`.

### Examples

```
/wash-sale-check
/wash-sale-check --start 2024-01-01
/wash-sale-check --tax-rate 0.20
/wash-sale-check --account 1
/wash-sale-check 今年 --tax-rate 0.30
/wash-sale-check 年末に向けて損出しできる銘柄を確認したい
```
