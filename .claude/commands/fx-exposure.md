---
description: Analyze currency exposure and FX risk with scenario simulation
allowed-tools: mcp__ib-sec-mcp__analyze_fx_exposure
argument-hint: [--start YYYY-MM-DD] [--scenario-pct 10] [--account N]
---

Analyze portfolio FX (foreign exchange) exposure, simulate currency fluctuation impact, and provide hedge recommendations.

## Task

Call `analyze_fx_exposure` MCP tool and present results in a structured report.

### Argument Parsing

- If $ARGUMENTS contains `--start YYYY-MM-DD`: Use as start_date
- If $ARGUMENTS contains `--scenario-pct N`: Use N as fx_scenario_pct (default: 10.0 for +/-10%)
- If $ARGUMENTS contains `--account N`: Use N as account_index
- Default start_date: `2025-01-01`
- Default fx_scenario_pct: `10.0`
- Default account_index: `0`

### Steps

1. **Fetch FX Exposure Data**

Call `mcp__ib-sec-mcp__analyze_fx_exposure` with parsed arguments.

2. **Present Report**

Format the JSON response into the output format below.

### Expected Output

```
=== FX Exposure Analysis ===
Period: {start_date} to {end_date}
Account: {account_id}
Scenario: +/-{fx_scenario_pct}%

📊 CURRENCY BREAKDOWN

Currency | Value       | Weight  | # Positions | Category
---------|-------------|---------|-------------|----------
USD      | $120,000    | 65.2%   | 15          | Base
EUR      | $35,000     | 19.0%   | 5           | Major
GBP      | $18,000     | 9.8%    | 3           | Major
JPY      | $11,000     | 6.0%    | 2           | Major

Total Portfolio Value: ${total_value}

📈 FX SCENARIO SIMULATION (+/-{fx_scenario_pct}%)

Currency | Current Value | +{pct}% Impact  | -{pct}% Impact
---------|---------------|-----------------|----------------
USD      | $120,000      | +$12,000        | -$12,000
EUR      | $35,000       | +$3,500         | -$3,500
GBP      | $18,000       | +$1,800         | -$1,800
JPY      | $11,000       | +$1,100         | -$1,100

Aggregate Portfolio Impact:
  Best case (+{pct}% all):  +${best_case}  (+{best_pct}%)
  Worst case (-{pct}% all): -${worst_case} (-{worst_pct}%)

⚠️ CONCENTRATION RISK

{Currencies with weight > 30%}:
  - {currency}: {weight}% ← {HIGH CONCENTRATION if >50%, MODERATE if >30%}

FX Diversification Score: {score}/10

🛡️ HEDGE RECOMMENDATIONS

{Based on exposure levels}:

1. {If single currency > 50%}:
   ⚠️ HIGH RISK: {currency} at {weight}%
   → Consider FX hedging or currency-hedged ETFs
   → Example: CSPX (unhedged) → IUSP (GBP-hedged)

2. {If non-base currency > 30%}:
   ⚠️ MODERATE RISK: {currency} at {weight}%
   → Monitor FX trends
   → Consider gradual rebalancing

3. {If well-diversified}:
   ✅ FX exposure is well-diversified
   → No immediate hedging needed
   → Review quarterly

💡 FX RISK MITIGATION STRATEGIES

Short-Term:
  - Use currency-hedged ETF variants
  - FX forward contracts (for large exposures)

Long-Term:
  - Natural hedge through geographic diversification
  - Match currency of assets to currency of liabilities
  - Regular rebalancing to target currency weights

=== NEXT STEPS ===

→ Review sector exposure for geographic context (/sector-analysis)
→ Check dividend impact by currency (/dividend-analysis)
→ Full portfolio optimization (/optimize-portfolio)
```

### Error Handling

- If no positions found: Report "No positions found in account."
- If invalid scenario_pct: Report "Invalid scenario percentage. Use a value between 1 and 100, e.g., --scenario-pct 10 for +/-10%"
- If MCP tool fails: Report error and suggest `/debug-api` for troubleshooting

### Examples

```
/fx-exposure
/fx-exposure --start 2024-01-01
/fx-exposure --scenario-pct 15
/fx-exposure --account 1
/fx-exposure --start 2025-01-01 --scenario-pct 20 --account 0
```
