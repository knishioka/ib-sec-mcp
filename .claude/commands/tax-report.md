---
description: Generate comprehensive tax report with optimization strategies and market timing
allowed-tools: Task, Write
argument-hint: [--year YYYY|--ytd|--save]
---

Generate detailed tax analysis report including capital gains, phantom income, and optimization strategies with market timing recommendations.

## Task

Create comprehensive tax report combining deep tax analysis (tax-optimizer) with market timing (market-analyst) for optimal tax-loss harvesting and holding period strategies.

### Report Scope

**Year Selection**:

- If $ARGUMENTS contains `--year YYYY`: Specific tax year
- If $ARGUMENTS contains `--ytd`: Year-to-date
- Otherwise: Current calendar year

**Output Options**:

- If $ARGUMENTS contains `--save`: Save to `data/processed/tax_report_YYYY.txt`
- Otherwise: Display to console only

### Orchestration Process

```
Use both tax-optimizer and market-analyst subagents:

1. Tax Analysis Phase (tax-optimizer):
   - Calculate capital gains/losses (short-term, long-term)
   - Identify phantom income (OID) for bonds
   - Check for wash sale violations
   - Find tax-loss harvesting candidates
   - Calculate current tax liability

2. Market Timing Analysis (market-analyst):
   - For loss harvesting candidates:
     - Analyze technical outlook
     - Recommend optimal exit timing
     - Suggest re-entry strategy after 31 days
     - Identify alternative securities (avoid wash sale)

   - For positions approaching long-term:
     - Analyze technical support levels
     - Risk of holding until long-term qualification
     - Recommend hold vs sell decision

   - For positions with gains:
     - Check technical levels for profit-taking
     - Suggest covered call strategies to defer gains
     - Identify rebalancing opportunities

3. Integrated Tax Strategy:
   - Combine tax savings with market timing
   - Prioritize by tax savings × probability of success
   - Consider technical risk of holding positions
   - Suggest options strategies for tax deferral

4. Action Plan:
   - Urgent: Execute before year-end or wash sale period
   - High Priority: Optimal tax timing with good technicals
   - Monitor: Positions to watch for tax opportunities

$ARGUMENTS
```

### Analysis Components

The integration of **tax-optimizer** and **market-analyst** will provide:

### Expected Output

```
=== TAX REPORT 2025 ===
Generated: 2025-10-11
Account: U1234567

📊 CAPITAL GAINS SUMMARY

Short-Term Capital Gains (< 1 year):
  Total Gains: $12,345
  Total Losses: -$2,890
  Net Short-Term: $9,455
  Tax Rate: 37% (ordinary income)
  Estimated Tax: $3,498

Long-Term Capital Gains (≥ 1 year):
  Total Gains: $8,765
  Total Losses: -$1,234
  Net Long-Term: $7,531
  Tax Rate: 15% (qualified)
  Estimated Tax: $1,130

Combined Net Capital Gain: $16,986
Total Estimated Tax Liability: $4,628

💰 PHANTOM INCOME (OID - Original Issue Discount)

Zero-Coupon Bonds:
1. CUSIP 912810XX - 2030 Treasury STRIP
   - Purchase Date: 2024-03-15
   - Purchase Price: $82.50
   - Current Accrued OID: $2,340
   - 2025 OID Income: $1,890
   - Tax Impact: $700 (at 37%)

2. CUSIP 912810YY - 2028 Treasury STRIP
   - Purchase Date: 2024-08-20
   - Purchase Price: $88.20
   - Current Accrued OID: $1,560
   - 2025 OID Income: $1,245
   - Tax Impact: $461 (at 37%)

Total Phantom Income: $3,135
Total OID Tax Impact: $1,161

⚠️ Note: Phantom income is taxable even though no cash received

⚠️ WASH SALE ANALYSIS

Potential Violations:
1. Symbol ABC
   - Sold at loss: 2025-09-15 (-$890)
   - Repurchased: 2025-10-01
   - Days apart: 16 days
   - Status: ⚠️ WASH SALE (within 30 days)
   - Disallowed Loss: $890
   - Action: Loss added to basis of new position

2. Symbol XYZ
   - Sold at loss: 2025-08-10 (-$450)
   - Repurchased: 2025-09-20
   - Days apart: 41 days
   - Status: ✅ ALLOWED (> 30 days)

Total Disallowed Losses: $890

💡 TAX OPTIMIZATION STRATEGIES

🎯 IMMEDIATE ACTIONS (Before Year End):

1. Harvest Tax Losses (High Priority)
   Positions with Unrealized Losses:
   - Symbol DEF: -$1,234 (current value: $8,766)
     → Sell to offset short-term gains
     → Estimated tax savings: $456 (at 37%)
     → Can repurchase after 31 days to avoid wash sale

   - Symbol GHI: -$678 (current value: $4,322)
     → Sell to offset long-term gains
     → Estimated tax savings: $102 (at 15%)

   Total Potential Savings: $558

2. Hold for Long-Term Treatment
   Positions Approaching 1-Year:
   - Symbol JKL: Hold until 2026-01-15 (47 days)
     → Current gain: $2,345
     → Tax savings if held: $515 (37% → 15%)

   - Symbol MNO: Hold until 2025-12-20 (70 days)
     → Current gain: $890
     → Tax savings if held: $196

3. Avoid Wash Sales
   Recently Sold (30-day watch period):
   - Symbol ABC: Avoid repurchase until 2025-10-16
   - Symbol PQR: Avoid repurchase until 2025-11-02

📈 STRATEGIC PLANNING (Next Year):

1. Municipal Bonds for Tax-Free Income
   - Current taxable bond income: $5,000/year
   - Tax on bond income: $1,850 (at 37%)
   - Consider tax-free municipal bonds (effective yield: 4.2% → 6.7% taxable equivalent)

2. Tax-Advantaged Accounts
   - Consider maxing IRA contributions ($7,000 if <50, $8,000 if 50+)
   - Potential tax deduction: $2,590 (at 37%)

3. Qualified Small Business Stock (QSBS)
   - If applicable: Up to $10M gain exclusion
   - Hold period: 5 years minimum

4. Capital Loss Carryforward
   - Current year losses: $890 (disallowed wash sale)
   - Can carry forward indefinitely
   - Apply against future gains

📋 RECORD KEEPING CHECKLIST

For Tax Filing:
✅ IRS Form 1099-B (broker will provide)
✅ Form 8949 (capital gains/losses)
✅ Schedule D (summary of capital gains)
✅ Form 1099-OID (phantom income)
✅ Wash sale adjustments documented

Documents to Save:
✅ Trade confirmations for all transactions
✅ Cost basis records (including adjustments)
✅ Wash sale tracking spreadsheet
✅ Bond purchase documentation (OID calculations)

💡 PRO TIPS

1. Tax-Loss Harvesting Window
   - Best time: November-December
   - Avoid: Last week of December (market volatility)
   - Remember: 30-day wash sale rule

2. Estimated Tax Payments
   - Q4 payment due: January 15, 2026
   - Recommended payment: $1,157 (25% of total liability)
   - Avoid underpayment penalty

3. Quarterly Review
   - Track gains/losses throughout year
   - Adjust strategy based on tax brackets
   - Plan harvesting opportunities

4. Professional Advice
   - Consider CPA review for:
     - High net worth ($500K+ annual income)
     - Complex OID calculations
     - Business income interactions
     - Estate planning considerations

=== TAX LIABILITY SUMMARY ===

Total Capital Gains Tax: $4,628
  - Short-Term (37%): $3,498
  - Long-Term (15%): $1,130

Phantom Income Tax (OID): $1,161

Total Estimated Tax: $5,789

Potential Savings (if optimized): $558
  - Tax-loss harvesting: $558
  - Hold for long-term: $711 (if positions held)

Net Tax After Optimization: $4,520

=== NEXT STEPS ===

⏰ URGENT (Within 30 Days):
1. Review tax-loss harvesting candidates
2. Plan year-end trades to optimize liability
3. Ensure no wash sale violations

📅 QUARTERLY (Every 3 Months):
1. Track capital gains/losses
2. Monitor wash sale periods
3. Adjust estimated tax payments

📚 ANNUAL (Year-End):
1. Gather all tax documents
2. Review with CPA/tax advisor
3. File Schedule D and Form 8949
4. Document OID calculations

---
This report is for planning purposes only.
Consult a qualified tax professional for personalized advice.
```

### Examples

```
/tax-report
/tax-report --year 2024
/tax-report --ytd
/tax-report --save
/tax-report --year 2024 --save
```

Report will be saved to `data/processed/tax_report_YYYY.txt` if `--save` flag is used.
