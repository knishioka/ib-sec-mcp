---
description: Daily portfolio monitoring with memory file auto-updates
allowed-tools: Read, Write, Edit, mcp__ib-sec-mcp__sync_daily_snapshot, mcp__ib-sec-mcp__get_sync_status, mcp__ib-sec-mcp__get_current_price, mcp__ib-sec-mcp__analyze_consolidated_portfolio, mcp__ib-sec-mcp__analyze_market_sentiment
argument-hint: [--skip-sync|--manual]
---

# Daily Portfolio Check

Fetch latest portfolio data, update memory files per auto-update rules, and flag actionable alerts.

**Memory File Path**: Auto-detected from the current project's `memory/` directory (Claude Code resolves this automatically).

## Arguments

- `$ARGUMENTS` may contain:
  - `--skip-sync`: Skip IB API sync, use cached data only
  - `--manual`: Tag update source as "manual" instead of "scheduled"

## Steps

### Step 1: Read Current Memory Files

Read the following files to understand current state:

1. `memory/investment-strategy.md` — current limit orders and holdings
2. `memory/daily-snapshot.md` — previous snapshot for comparison
3. `memory/portfolio-decisions.md` — existing decision log (for append)
4. `memory/investment-policy.md` — read-only reference (NEVER modify)

Extract from `investment-strategy.md`:

- All pending limit orders (symbol, limit price, shares, tranche info)
- Completed purchases table
- Deployment plan status
- Key holdings list

### Step 2: Fetch Current Data

Unless `--skip-sync` is specified:

1. Call `sync_daily_snapshot` MCP tool to fetch latest IB data. Capture the returned `xml_file_path` from the result.
2. Call `analyze_consolidated_portfolio` with the `file_path` from step 1 for current positions and values. (Note: `get_portfolio_summary` is deprecated; use `analyze_consolidated_portfolio` instead.)

Then for each symbol with a pending limit order, call `get_current_price` to get real-time prices.

If sync fails, proceed with `get_current_price` calls only and note "API sync failed" in snapshot.

### Step 3: Generate Alerts

For each pending limit order, calculate distance to current price and assign alert flags:

| Condition                               | Flag          | Meaning                                  |
| --------------------------------------- | ------------- | ---------------------------------------- |
| `current_price <= limit_price` (BUY)    | `FILL_CHECK`  | Order may have filled — verify in broker |
| `distance < 1%` above limit             | `URGENT`      | Very close to filling                    |
| `distance < 3%` above limit             | `APPROACHING` | Getting close, monitor                   |
| `abs(daily_change) > 5%` on any holding | `VOLATILITY`  | Significant move on a holding            |

**Fill detection logic** (BUY orders):

- If `current_price < limit_price`: flag `FILL_CHECK`
- If `current_price == limit_price`: flag `FILL_CHECK`
- Distance formula: `((current_price - limit_price) / limit_price) * 100`

Optionally call `analyze_market_sentiment` for SPY to get market context.

### Step 4: Update daily-snapshot.md (OVERWRITE — every run)

**Method**: Use `Write` tool to overwrite the entire file.

**Format**:

```markdown
# Daily Snapshot

**Last Updated**: {YYYY-MM-DDTHH:mm} {timezone}
**Updated By**: {scheduled|manual}

## Price Check

| Symbol   | Price   | Prev Close   | Change    | vs Limit Order      |
| -------- | ------- | ------------ | --------- | ------------------- |
| {symbol} | {price} | {prev_close} | {change%} | {alert_or_distance} |

...

## Alerts

{If any FILL_CHECK, URGENT, APPROACHING, or VOLATILITY flags:}

- **FILL_CHECK**: {symbol} at {price} — limit was {limit_price}. Verify fill in broker.
- **URGENT**: {symbol} at {price} — only {distance}% above limit {limit_price}
- **APPROACHING**: {symbol} at {price} — {distance}% above limit {limit_price}
- **VOLATILITY**: {symbol} moved {change}% today

{If no alerts:}

- None currently. All limit orders still above current prices.

## Market Sentiment

- SPY: {sentiment_description} ({score})
- {Other relevant context}

## Next Actions

- {Prioritized list based on alerts}
- {Standing items: monitor limit orders, research tasks, etc.}
```

### Step 5: Update investment-strategy.md (CONDITIONAL — only on triggers)

**Method**: Use `Edit` tool for surgical updates. NEVER rewrite the whole file.

**Trigger 1: Order Filled** (`FILL_CHECK` detected)

When `current_price <= limit_price` for a BUY order:

1. Remove the filled order line from the "Pending Limit Orders" section
2. Add a row to the "Completed Purchases" table:
   ```
   | {YYYY-MM-DD} | {SYMBOL} | {shares} | ~${limit_price} | ~${amount} |
   ```
3. Update "Last Updated" date at top of file

**Trigger 2: Order Approaching** (`APPROACHING` or `URGENT`)

1. Update the "Current:" price line under the relevant symbol in Pending Limit Orders
2. Update "Last Updated" date at top of file

**Trigger 3: Significant Market Move** (`VOLATILITY` on a holding)

1. Add a note to the "Strategy Notes" section:
   ```
   - {YYYY-MM-DD}: {SYMBOL} moved {change}% — {brief context}
   ```
2. Update "Last Updated" date at top of file

**Trigger 4: All Orders Filled for a Tranche**

1. Update the relevant row in "Deployment Plan" from "Pending" to "Completed"
2. Update "Last Updated" date at top of file

**If no triggers fire**: Do NOT modify this file.

### Step 6: Update portfolio-decisions.md (APPEND — only on triggers)

**Method**: Read current content, then use `Write` tool to write back with new entry appended.

**CRITICAL**: NEVER overwrite existing entries. Always append to the end.

**Trigger 1: Order Filled** (`FILL_CHECK` detected)

Append:

```markdown
## {YYYY-MM-DD}: Order Filled — {SYMBOL}

- **Action**: BUY {shares} shares at ~${price}
- **Amount**: ~${total}
- **Tranche**: {tranche info, e.g., "Tranche 1 of 4"}
- **Context**: {market conditions at time of fill}
```

**Trigger 2: Strategy Change Recommended**

Append when a significant market event warrants strategy discussion:

```markdown
## {YYYY-MM-DD}: Strategy Note — {topic}

- **Trigger**: {what happened, e.g., "CSPX dropped 5% in one day"}
- **Suggestion**: {recommended action}
- **Status**: Pending review
```

**If no triggers fire**: Do NOT modify this file.

### Step 7: Verify Updates

After all updates, verify:

1. `daily-snapshot.md` was written with current timestamp
2. `investment-strategy.md` was only modified if triggers fired
3. `portfolio-decisions.md` was only appended to if triggers fired
4. `investment-policy.md` was NOT touched (confirm by not reading/writing it after Step 1)
5. `MEMORY.md` was NOT touched

### Step 8: Output Summary

Display a summary to the user:

```
Daily Check Complete ({timestamp})
Source: {scheduled|manual}

Prices: {count} symbols checked
Alerts: {count} ({list of flags})
Files Updated: {list of files that were modified}

{If alerts exist, show them prominently}
{If FILL_CHECK, emphasize: "ACTION REQUIRED: Verify order fill in broker"}
```

## Auto-Update Rules Reference

| File                     | Mode        | Tool       | When                                                                |
| ------------------------ | ----------- | ---------- | ------------------------------------------------------------------- |
| `daily-snapshot.md`      | OVERWRITE   | Write      | Every run                                                           |
| `investment-strategy.md` | CONDITIONAL | Edit       | Order filled, approaching (<3%), volatility (>5%), tranche complete |
| `portfolio-decisions.md` | APPEND      | Read+Write | Order filled, strategy change recommended                           |
| `investment-policy.md`   | NEVER       | —          | Only explicit user request                                          |
| `MEMORY.md`              | RARELY      | Edit       | New memory file created, protocol/preference changes                |

## Timestamp Format

All timestamps use ISO 8601: `YYYY-MM-DDTHH:mm` with timezone (e.g., `2026-03-10T09:30 JST`).

"Last Updated" fields in file headers use date only: `YYYY-MM-DD`.

## Error Handling

- **MCP sync fails**: Continue with `get_current_price` calls. Note in snapshot.
- **Price fetch fails for a symbol**: Show "N/A" in price column, skip alert calc for that symbol.
- **Memory file not found**: Create it with default template (except `investment-policy.md`).
- **Edit conflict**: If `Edit` tool fails (non-unique string), read file again and retry with more context.

## Example Scenarios

### Normal Day (no alerts)

- Only `daily-snapshot.md` updated
- Other files untouched

### Order Approaching

- `daily-snapshot.md` updated with APPROACHING flag
- `investment-strategy.md` updated with current price
- `portfolio-decisions.md` untouched

### Order Filled

- `daily-snapshot.md` updated with FILL_CHECK flag
- `investment-strategy.md` updated: order moved to Completed, deployment plan updated
- `portfolio-decisions.md` appended: new fill entry
