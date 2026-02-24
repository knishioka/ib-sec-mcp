---
description: Analyze portfolio currency exposure (USD/JPY/EUR/GBP) and simulate impact of exchange rate moves
allowed-tools: mcp__ib-sec-mcp__analyze_fx_exposure, mcp__ib-sec-mcp__get_positions
argument-hint: [--start YYYY-MM-DD] [--scenario-pct 10] [--account N]
---

Analyze how much of your portfolio is exposed to each currency (USD, JPY, EUR, GBP, etc.) and simulate how your portfolio value would change if exchange rates moved by a given percentage.

**When to use this command**:

- You want to know your portfolio's currency breakdown
- You want to stress-test: "what happens if JPY weakens by 10%?"
- You're worried about over-concentration in one currency

## Task

### Step 1: Parse Arguments

From `$ARGUMENTS`, extract:

- `start_date`: Look for `--start YYYY-MM-DD`. Also accept natural language: "2024年から" → "2024-01-01", "今年" → current year Jan 1. Default: `"2025-01-01"`.
- `fx_scenario_pct`: Look for `--scenario-pct N`. Also accept natural language like "10%動いたら" → 10, "20%変動" → 20. Default: `10.0`.
- `account_index`: Look for `--account N`. Default: `0`.

### Step 2: Fetch FX Exposure Data

Call the MCP tool with the following parameters:

```
mcp__ib-sec-mcp__analyze_fx_exposure(
  start_date=<start_date>,
  fx_scenario_pct=<fx_scenario_pct>,
  account_index=<account_index>
)
```

### Step 3: Present Report

Format the JSON response. Note: the "base currency" (typically USD or the account's home currency) is excluded from scenario simulation because it cannot move relative to itself.

### Expected Output

```
=== FX Exposure Analysis ===
Period: {start_date} to today
Account: {account_id}
Scenario: exchange rates move by +/-{fx_scenario_pct}%

📊 CURRENCY BREAKDOWN

Currency | Value (USD) | Weight  | # Positions | Note
---------|-------------|---------|-------------|------
USD      | $120,000    | 65.2%   | 15          | Base currency
JPY      | $35,000     | 19.0%   | 5           |
EUR      | $18,000     | 9.8%    | 3           |
GBP      | $11,000     | 6.0%    | 2           |

Total Portfolio Value: ${total_value}

📈 SCENARIO: What if exchange rates move by +/-{fx_scenario_pct}%?

(Base currency excluded — only foreign currency positions shown)

Currency | Current Value | If rates rise +{pct}% | If rates fall -{pct}%
---------|---------------|------------------------|----------------------
JPY      | $35,000       | +$3,500                | -$3,500
EUR      | $18,000       | +$1,800                | -$1,800
GBP      | $11,000       | +$1,100                | -$1,100

Portfolio-Level Impact:
  Best case  (all foreign currencies rise {pct}%):  +${best_case}  (+{best_pct}%)
  Worst case (all foreign currencies fall {pct}%):  -${worst_case} (-{worst_pct}%)

⚠️ CONCENTRATION RISK

{If any single non-base currency > 30% of portfolio}:
  ⚠️ {currency}: {weight}% — HIGH FX CONCENTRATION
     Consider currency-hedged ETF alternatives

{If well-distributed}:
  ✅ No single foreign currency exceeds 30%. FX risk is manageable.

🛡️ HEDGE RECOMMENDATIONS

{Based on concentration levels}:

1. {If non-base currency > 50%}:
   ❌ HIGH RISK: {currency} at {weight}%
   → Consider FX hedging instruments or currency-hedged ETF variants
   → Example: CSPX (USD unhedged) → IUSP (GBP-hedged equivalent)

2. {If non-base currency 30–50%}:
   ⚠️ MODERATE: {currency} at {weight}%
   → Monitor FX trends; consider partial hedge

3. {If all foreign currencies < 30%}:
   ✅ FX exposure is well-diversified — no immediate action needed

=== NEXT STEPS ===
→ Review which sectors drive the FX exposure (/sector-analysis)
→ Check dividend impact from foreign holdings (/dividend-analysis)
→ Full portfolio optimization (/optimize-portfolio)
```

### Error Handling

- **No positions found**: Print "No positions found in account {account_index}. Try `/fetch-latest` to load data."
- **Invalid scenario_pct (e.g., 0 or >100)**: Print "Scenario percentage must be between 1 and 100. Example: `--scenario-pct 10` for a +/-10% simulation."
- **MCP tool fails**: Print the error, then suggest `/mcp-status` and `/debug-api`.

### Examples

```
/fx-exposure
/fx-exposure --start 2024-01-01
/fx-exposure --scenario-pct 15
/fx-exposure --account 1
/fx-exposure 今年 --scenario-pct 20
/fx-exposure 円が10%動いたらどうなる
```
