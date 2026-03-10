---
description: Daily portfolio monitoring for scheduled tasks (no user interaction)
allowed-tools: Read, Write, Edit, mcp__ib-sec-mcp__sync_daily_snapshot, mcp__ib-sec-mcp__get_current_price, mcp__ib-sec-mcp__check_order_proximity, mcp__ib-sec-mcp__get_pending_orders, mcp__ib-sec-mcp__analyze_consolidated_portfolio
argument-hint: [--verbose]
---

# Daily Portfolio Check

Automated daily monitoring designed for Claude Desktop scheduled tasks. Completes in under 3 minutes with no user interaction.

**CRITICAL**: Do NOT use `AskUserQuestion` at any point. This command runs unattended.

## Steps

### Step 1: Data Sync

Call `sync_daily_snapshot` to fetch latest data and sync to SQLite.

```
sync_daily_snapshot()
```

Record the `sync_date`, `status`, and `comparison_summary` from the result. If status is `failure`, note the error but continue with cached data.

### Step 2: Get Portfolio Positions

Call `analyze_consolidated_portfolio` to get current holdings list. Use a rolling 1-year lookback for `start_date` to ensure comprehensive position coverage.

```
analyze_consolidated_portfolio(use_cache=true, start_date="{one year ago in YYYY-MM-DD format}")
```

Compute the start_date as today minus 1 year (e.g., if today is 2026-03-10, use "2025-03-10").

Extract the list of symbols from positions. These are needed for price checks.

### Step 3: Price Check (Parallel)

Call `get_current_price` for ALL portfolio symbols in parallel (multiple tool calls in one message).

```
get_current_price(symbol="CSPX.L")
get_current_price(symbol="NDIA.L")
get_current_price(symbol="VUAG.L")
... (all symbols from Step 2)
```

Record for each symbol: `current_price`, `previous_close`, `day_change_percent`.

If a price fetch fails (e.g., delisted symbol), note as "N/A" and continue.

### Step 4: Limit Order Status

Call `get_pending_orders` to get all pending limit orders.

```
get_pending_orders()
```

Then call `check_order_proximity` with default 5% threshold to get proximity alerts.

```
check_order_proximity(threshold_pct=5.0)
```

For any symbols in pending orders that were NOT in portfolio positions, fetch their current prices too (parallel `get_current_price` calls).

### Step 5: Alert Generation

Generate alerts based on these thresholds:

| Condition                                    | Alert Level      | Label       |
| -------------------------------------------- | ---------------- | ----------- |
| Limit order distance <= 3%                   | URGENT ALERT     | URGENT      |
| Limit order distance <= 5% (but > 3%)        | ALERT            | APPROACHING |
| Daily price change > +/-3%                   | VOLATILITY ALERT | VOLATILE    |
| Current price <= limit price (likely filled) | FILL CHECK       | FILL CHECK  |

Classification logic:

- Use `distance_pct` from `check_order_proximity` results for order alerts
- Use `day_change_percent` from `get_current_price` results for volatility alerts
- If current price is at or below the buy limit price, flag as FILL CHECK

### Step 6: Memory Update — daily-snapshot.md (OVERWRITE — every run)

**Always** overwrite `memory/daily-snapshot.md` with the output using the `Write` tool.

The file path is the auto-memory directory (Claude Code resolves this automatically from the project context).

Write in this format:

```markdown
# Daily Snapshot - {YYYY-MM-DD}

Updated: {YYYY-MM-DDTHH:mm} {timezone}
Source: /daily-check (automated)
Sync Status: {status from Step 1}

## Price Summary

| Symbol | Current  | Prev Close | Change     | Alert        |
| ------ | -------- | ---------- | ---------- | ------------ |
| {sym}  | ${price} | ${prev}    | {+/-X.XX%} | {alert or —} |

## Limit Order Status

| Symbol | Limit    | Current    | Distance | Alert        |
| ------ | -------- | ---------- | -------- | ------------ |
| {sym}  | ${limit} | ${current} | {X.X%}   | {level or —} |

## Active Alerts

- {ALERT_LEVEL}: {description}
  (or "None" if no alerts)

## Market Status

{Open/Closed}. Prices as of {time/date}.
```

### Step 7: Memory Update — investment-strategy.md (CONDITIONAL — only on triggers)

**Method**: Use `Edit` tool for surgical updates. NEVER rewrite the whole file.

**Only if** URGENT ALERT or FILL CHECK alerts exist:

1. Read `memory/investment-strategy.md`
2. Check if any triggered alerts affect the current strategy

**Trigger 1: Order Filled** (`FILL CHECK` detected)

When `current_price <= limit_price` for a BUY order:

1. Remove the filled order line from the "Pending Limit Orders" section
2. Add a row to the "Completed Purchases" table:
   ```
   | {YYYY-MM-DD} | {SYMBOL} | {shares} | ~${limit_price} | ~${amount} |
   ```
3. Update "Last Updated" date at top of file

**Trigger 2: Order Approaching** (`URGENT` only, not APPROACHING)

1. Update the "Current:" price line under the relevant symbol in Pending Limit Orders
2. Update "Last Updated" date at top of file

**Trigger 3: All Orders Filled for a Tranche**

1. Update the relevant row in "Deployment Plan" from "Pending" to "Completed"
2. Update "Last Updated" date at top of file

**If only APPROACHING or VOLATILITY alerts**: Do NOT update strategy file.

### Step 8: Memory Update — portfolio-decisions.md (APPEND — only on triggers)

**Method**: Read current content, then use `Write` tool to write back with new entry appended.

**CRITICAL**: NEVER overwrite existing entries. Always append to the end.

**Only if** FILL CHECK alerts exist:

Append:

```markdown
## {YYYY-MM-DD}: Order Filled — {SYMBOL}

- **Action**: BUY {shares} shares at ~${price}
- **Amount**: ~${total}
- **Tranche**: {tranche info, e.g., "Tranche 1 of 4"}
- **Context**: {market conditions at time of fill}
```

**If no FILL CHECK**: Do NOT modify this file.

### Step 9: Files NEVER Modified

- `memory/investment-policy.md` — NEVER touched by automated process
- `memory/MEMORY.md` — RARELY touched (only on new file creation or protocol changes)

## Output Format

Display the following to the conversation:

```
## Daily Portfolio Check - {YYYY-MM-DD}

### Sync Status
{status} - {positions_count} positions across {accounts_synced} accounts

### Price Summary
| Symbol | Current | Prev Close | Change | Alert |
|--------|---------|------------|--------|-------|
| ... | ... | ... | ... | ... |

### Limit Order Status
| Symbol | Limit | Current | Distance | Alert |
|--------|-------|---------|----------|-------|
| ... | ... | ... | ... | ... |

### Alerts
- {ALERT_LEVEL}: {description}
(or "No alerts today")

### Recommended Actions
- {action items based on alerts, or "No action required today"}

### Memory Updated
- daily-snapshot.md: Updated
- investment-strategy.md: {Updated / No change needed}
- portfolio-decisions.md: {Appended / No change needed}
```

## Auto-Update Rules Reference

| File                     | Mode        | Tool       | When                                                 |
| ------------------------ | ----------- | ---------- | ---------------------------------------------------- |
| `daily-snapshot.md`      | OVERWRITE   | Write      | Every run                                            |
| `investment-strategy.md` | CONDITIONAL | Edit       | Order filled, urgent (<3%), tranche complete         |
| `portfolio-decisions.md` | APPEND      | Read+Write | Order filled                                         |
| `investment-policy.md`   | NEVER       | —          | Only explicit user request                           |
| `MEMORY.md`              | RARELY      | Edit       | New memory file created, protocol/preference changes |

## Verbose Mode

If $ARGUMENTS contains `--verbose`:

- Include full portfolio breakdown from `analyze_consolidated_portfolio`
- Show detailed sync comparison (positions added/removed, value changes)
- Show all limit order details including rationale
- Show 52-week high/low for each symbol from `get_current_price` results

## Error Handling

- **MCP server unavailable**: Report error in output, write "ALERT: MCP server down" to daily-snapshot.md
- **API rate limit**: Use cached data, note staleness in output
- **Market closed**: Proceed normally; note "Market closed" in Market Status section. Prices will reflect last close.
- **No pending orders**: Skip Steps 4-5 order proximity checks, still do price checks
- **Partial failures**: Continue with available data, note failures in output
- **Edit conflict**: If `Edit` tool fails (non-unique string), read file again and retry with more context

## Timestamp Format

All timestamps use ISO 8601: `YYYY-MM-DDTHH:mm` with timezone (e.g., `2026-03-10T09:30 JST`).

"Last Updated" fields in file headers use date only: `YYYY-MM-DD`.

## Examples

```
/daily-check
/daily-check --verbose
```
