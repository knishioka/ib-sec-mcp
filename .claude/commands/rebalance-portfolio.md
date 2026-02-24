---
description: Calculate specific buy/sell trades to rebalance portfolio toward a target allocation profile (balanced/growth/conservative/income)
allowed-tools: mcp__ib-sec-mcp__generate_rebalancing_trades, mcp__ib-sec-mcp__simulate_rebalancing, mcp__ib-sec-mcp__get_positions, mcp__ib-sec-mcp__get_account_summary, ReadMcpResourceTool
argument-hint: [--profile balanced|growth|conservative|income] [--dry-run]
---

Compare your current portfolio allocation with a target profile and output a specific list of buy/sell trades (which symbol, how many shares, estimated amount) needed to reach the target. Optionally simulate the tax and commission impact before executing.

**When to use this command**:

- You want to know exactly "what should I buy and sell to rebalance?"
- Your cash allocation is too high and you want to deploy it efficiently
- You want to shift from a balanced to a more aggressive (growth) or defensive (conservative) portfolio
- You want to see the tax cost of rebalancing before committing

## Task

### Step 1: Parse Arguments

From `$ARGUMENTS`, extract:

- `profile`: Look for `--profile NAME`. Valid values: `balanced`, `growth`, `conservative`, `income`.
  - Also accept natural language: "積極的" / "リスク高め" → `growth`, "安全重視" / "守り" → `conservative`, "配当重視" → `income`, "バランス型" → `balanced`.
  - Default: `balanced`.
- `dry_run`: True if `--dry-run` is present, or if user wrote "シミュレーション" / "試算" / "仮計算". Default: False.

If an unrecognized profile name is given, respond with:
"Unknown profile. Available profiles: `balanced`, `growth`, `conservative`, `income`. Please retry with one of these."

### Profile Target Allocations

| Profile        | Stocks (STK) | Bonds (BOND) | Cash | Focus                          |
| -------------- | ------------ | ------------ | ---- | ------------------------------ |
| `balanced`     | 50%          | 40%          | 10%  | Diversification, moderate risk |
| `growth`       | 75%          | 15%          | 10%  | Capital gains, higher risk     |
| `conservative` | 25%          | 60%          | 15%  | Capital preservation, low risk |
| `income`       | 40%          | 50%          | 10%  | Dividends, yields, stability   |

### Step 2: Get Current Portfolio State

Read the rebalancing context resource — this provides the current allocation breakdown and drift from any target:

```
ReadMcpResourceTool(server="ib-sec-mcp", uri="ib://strategy/rebalancing-context")
```

From the result, extract:

- Current total portfolio value
- Current value of each position (symbol, asset_class, current_value_usd)
- Asset class totals (STK total, BOND total, CASH total)

### Step 3: Build the Target Allocation Dictionary

You must build a `target_allocation` dict mapping **every symbol in the portfolio** to its target weight (as a percentage, 0–100). The weights must sum to exactly 100.

**Algorithm**:

1. Get the profile's target percentages: `profile_stk_pct`, `profile_bond_pct`, `profile_cash_pct`
2. For each asset class (STK, BOND, CASH), identify all positions in that class from the portfolio data
3. Within each asset class, distribute the profile's target percentage proportionally to current values:
   ```
   symbol_target_pct = profile_asset_class_pct × (symbol_current_value / asset_class_total_value)
   ```
4. Include ALL positions (equities, bonds, cash) in the dict
5. Verify the sum = 100.0 (adjust by rounding correction if needed)

**Example** (balanced profile: 50% STK, 40% BOND, 10% CASH):

- Portfolio: CSPX=$30k (STK), INDA=$20k (STK), STRIPS-2040=$40k (BOND), USD.CASH=$10k (CASH)
- STK total = $50k: CSPX → 50% × (30/50) = 30%, INDA → 50% × (20/50) = 20%
- BOND total = $40k: STRIPS-2040 → 40% × (40/40) = 40%
- CASH total = $10k: USD.CASH → 10% × (10/10) = 10%
- target_allocation = {"CSPX": 30, "INDA": 20, "STRIPS-2040": 40, "USD.CASH": 10} → sum = 100 ✅

### Step 4: Call Rebalancing Tool

Use the current year for `start_date` (format: "YYYY-01-01").

**If `--dry-run`** (simulation mode):

```
mcp__ib-sec-mcp__simulate_rebalancing(
  target_allocation=<dict from Step 3>,
  start_date="<current_year>-01-01"
)
```

**Otherwise** (generate actual trades):

```
mcp__ib-sec-mcp__generate_rebalancing_trades(
  target_allocation=<dict from Step 3>,
  start_date="<current_year>-01-01"
)
```

### Step 5: Present Report

### Expected Output

```
=== Portfolio Rebalancing Report ===
Profile: {profile} ({stock_pct}% Stocks / {bond_pct}% Bonds / {cash_pct}% Cash)
Mode: [LIVE TRADE LIST | DRY RUN - Simulation]

📊 CURRENT vs TARGET ALLOCATION

Asset Class   | Current Value | Current % | Target % | Drift
--------------|---------------|-----------|----------|--------
Stocks (STK)  | $XXX,XXX      | 35.2%     | 50.0%    | -14.8% UNDERWEIGHT ⬆ need to buy
Bonds (BOND)  | $XXX,XXX      | 52.1%     | 40.0%    | +12.1% OVERWEIGHT  ⬇ need to sell
Cash          | $XXX,XXX      | 12.7%     | 10.0%    | +2.7%  OVERWEIGHT  ⬇ use for buys

📋 REQUIRED TRADES (execute in this order)

Priority | Action | Symbol     | Amount      | Est. Shares | Commission
---------|--------|------------|-------------|-------------|----------
1        | SELL   | STRIPS-40  | $12,345     | 12 units    | $12.35
2        | BUY    | CSPX       | $8,900      | 8 shares    | $1.00
3        | BUY    | INDA       | $5,678      | 23 shares   | $1.00

💰 TRADE SUMMARY

Total Trades:       {N}
Total to Sell:      ${sell_total}
Total to Buy:       ${buy_total}
Net Cash Movement:  ${net}
Est. Total Commission: ${total_commission}

[DRY RUN ONLY — Tax Impact Simulation]
Estimated Taxable Gains:  ${gains}
Estimated Tax Losses:     ${losses}
Net Tax Impact:            ${net_tax}

⚠️ WARNINGS (if any from tool)
- {Any warnings}

🎯 EXECUTION ORDER
1. Execute SELL orders first (to generate cash for buys)
2. Execute BUY orders in order of drift magnitude (most underweight first)
3. Review tax impact section before executing near year-end

=== NEXT STEPS ===
→ Simulate tax impact first: /rebalance-portfolio --profile {profile} --dry-run
→ Check wash sale risk: /wash-sale-check
→ Full strategy view: /investment-strategy
```

### Trade Priority Rules

Sort trades in this order before display:

1. SELL orders first (largest drift magnitude first within sells)
2. BUY orders second (largest drift magnitude first within buys)

### Error Handling

- **No positions found**: "No portfolio positions found. Run `/fetch-latest` to load trading data first."
- **MCP resource read fails**: Fall back to calling `mcp__ib-sec-mcp__get_positions` and `mcp__ib-sec-mcp__get_account_summary` directly to reconstruct position data.
- **All positions in one asset class** (e.g., 100% stocks): Warn "Rebalancing to this profile requires adding {BOND} positions. Currently no {BOND} holdings exist."
- **Target allocation sum ≠ 100**: Recalculate — apply rounding correction to the largest position weight.
- **MCP tool error**: Print the error, suggest `/mcp-status` to check server health.

### Examples

```
/rebalance-portfolio
/rebalance-portfolio --profile growth
/rebalance-portfolio --profile conservative --dry-run
/rebalance-portfolio --profile income
/rebalance-portfolio 積極的に
/rebalance-portfolio 守りのポートフォリオにしたい
/rebalance-portfolio 税金への影響を先に確認したい
```

### Related Commands

- `/optimize-portfolio` - Comprehensive portfolio analysis with broader recommendations
- `/investment-strategy` - Full investment strategy with market analysis
- `/wash-sale-check` - Check tax loss harvesting before executing sells
- `/tax-report` - Detailed tax analysis
