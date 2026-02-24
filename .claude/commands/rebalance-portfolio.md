---
description: Calculate portfolio rebalancing trades with target allocation profiles
allowed-tools: mcp__ib-sec-mcp__generate_rebalancing_trades, mcp__ib-sec-mcp__simulate_rebalancing, mcp__ib-sec-mcp__get_portfolio_summary, ReadMcpResourceTool
argument-hint: [--profile balanced|growth|conservative|income] [--dry-run]
---

Compare current portfolio allocation with a target allocation profile and output specific buy/sell actions.

## Task

Generate portfolio rebalancing trades based on an investment profile. Compares current holdings against target asset-class weights and produces actionable trade list.

### Command Usage

```bash
# Default (balanced profile)
/rebalance-portfolio

# Use specific investment profile
/rebalance-portfolio --profile growth

# Dry run (show simulation with tax/cost impact, no trade generation)
/rebalance-portfolio --dry-run

# Combined
/rebalance-portfolio --profile conservative --dry-run
```

### Investment Profiles

| Profile              | Stocks | Bonds | Cash | Focus                          |
| -------------------- | ------ | ----- | ---- | ------------------------------ |
| `balanced` (default) | 50%    | 40%   | 10%  | Diversification, moderate risk |
| `growth`             | 75%    | 15%   | 10%  | Capital gains, higher risk     |
| `conservative`       | 25%    | 60%   | 15%  | Capital preservation, low risk |
| `income`             | 40%    | 50%   | 10%  | Dividends, yields, stability   |

### Argument Parsing

Parse `$ARGUMENTS` for:

- `--profile <name>`: Select investment profile (default: `balanced`)
- `--dry-run`: Use `simulate_rebalancing` instead of `generate_rebalancing_trades`

If an unrecognized profile is provided, list available profiles and exit.

### Rebalancing Steps

**Step 1: Get Current Portfolio**

Read the rebalancing context resource to understand current allocation and drift:

```
ReadMcpResourceTool: ib://strategy/rebalancing-context
```

Also call `get_portfolio_summary` for latest position details:

```
mcp__ib-sec-mcp__get_portfolio_summary(start_date="2025-01-01")
```

**Step 2: Classify Positions by Asset Class**

From current positions, group holdings:

- **Stocks (STK)**: All equity positions
- **Bonds (BOND)**: All fixed-income positions
- **Cash (CASH)**: Cash balances and forex positions

**Step 3: Calculate Symbol-Level Target Allocation**

Map the profile's asset-class targets to per-symbol weights:

1. For each asset class (STK, BOND, CASH), determine the profile's target percentage
2. Within each asset class, maintain current proportional weights among symbols
3. Example: If profile targets 50% stocks, and current stock holdings are AAPL (60% of stocks) and MSFT (40% of stocks), then target: AAPL=30%, MSFT=20%

**Formula**:

```
symbol_target_pct = profile_asset_class_pct * (symbol_value / asset_class_total_value)
```

Ensure all symbol weights sum to exactly 100 (excluding cash, which is the remainder).

**Step 4: Call Rebalancing Tool**

If `--dry-run`:

```
mcp__ib-sec-mcp__simulate_rebalancing(
    target_allocation={symbol: weight for each symbol},
    start_date="2025-01-01"
)
```

Otherwise:

```
mcp__ib-sec-mcp__generate_rebalancing_trades(
    target_allocation={symbol: weight for each symbol},
    start_date="2025-01-01"
)
```

**Step 5: Format Output**

### Expected Output Format

```
=== Portfolio Rebalancing Report ===
Profile: balanced (50% Stocks / 40% Bonds / 10% Cash)
Mode: [LIVE | DRY RUN]

📊 CURRENT ALLOCATION
Asset Class      | Current %  | Target %  | Drift
-----------------|------------|-----------|--------
Stocks (STK)     | 35.2%      | 50.0%     | -14.8% UNDERWEIGHT
Bonds (BOND)     | 52.1%      | 40.0%     | +12.1% OVERWEIGHT
Cash             | 12.7%      | 10.0%     | +2.7%  OVERWEIGHT

📋 REBALANCING TRADES (sorted by priority)
Priority | Symbol  | Direction | Amount      | Est. Shares | Commission
---------|---------|-----------|-------------|-------------|----------
1        | BOND-A  | SELL      | $12,345.00  | 12          | $12.35
2        | STK-X   | BUY       | $8,900.00   | 45          | $1.00
3        | STK-Y   | BUY       | $5,678.00   | 23          | $1.00
...

💰 TRADE SUMMARY
Total Trades: N
Total Buy Value: $XX,XXX
Total Sell Value: $XX,XXX
Net Cash Flow: $X,XXX
Est. Total Commission: $XX.XX

[DRY RUN ONLY]
💵 TAX IMPACT
Estimated Taxable Gains: $X,XXX
Estimated Tax Losses: $X,XXX
Net Tax Impact: $X,XXX

⚠️ WARNINGS
- [Any warnings from the tool]

🎯 EXECUTION PRIORITY
1. Execute SELL orders first (to free cash)
2. Execute BUY orders by drift magnitude (largest underweight first)
3. Review tax impact before executing (especially near year-end)
```

### Trade Priority Rules

Sort trades in this order:

1. **SELL** orders first (to generate cash for buys)
2. Within sells: largest drift magnitude first
3. **BUY** orders second
4. Within buys: largest drift magnitude first (most underweight first)

### Error Handling

- **No positions found**: "No portfolio positions found. Run `/fetch-latest` to load data."
- **Invalid profile**: "Unknown profile '{name}'. Available: balanced, growth, conservative, income"
- **MCP tool error**: Display the error and suggest `/mcp-status` to check server health
- **All positions in one asset class**: Warn that rebalancing requires diversified holdings

### Examples

```bash
# Quick rebalancing check with default profile
/rebalance-portfolio

# Growth-oriented rebalancing
/rebalance-portfolio --profile growth

# Preview tax impact before rebalancing
/rebalance-portfolio --profile conservative --dry-run

# Income-focused allocation
/rebalance-portfolio --profile income
```

### Related Commands

- `/optimize-portfolio` - Comprehensive portfolio analysis with recommendations
- `/investment-strategy` - Full investment strategy with market analysis
- `/tax-report` - Detailed tax analysis and optimization
