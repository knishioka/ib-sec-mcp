# Claude Desktop Scheduled Task Setup Guide

Set up Claude Desktop scheduled tasks to run `/daily-check` automatically on weekdays for hands-free portfolio monitoring.

## Prerequisites

Before setting up scheduled tasks, ensure:

1. **Claude Desktop** installed with Claude Code features enabled
2. **MCP server** configured and working — verify with `/mcp-status`
3. **IB Flex Query credentials** in `.env` file:
   ```
   QUERY_ID=your_query_id
   TOKEN=your_token
   ```
4. **Memory files** initialized — the `memory/` directory should contain:
   - `MEMORY.md` (auto-loaded context)
   - `investment-policy.md` (Layer 1)
   - `investment-strategy.md` (Layer 2)
   - `daily-snapshot.md` (Layer 3 — created on first run)
   - `portfolio-decisions.md` (Layer 3 — created on first run)
5. **Limit orders** seeded in SQLite — run `/fetch-latest` at least once

## Setting Up Scheduled Tasks

### Primary Task: Morning Check (TSE Open)

This task runs every weekday morning to check portfolio status when the Tokyo Stock Exchange opens.

**Configuration:**

| Setting         | Value                              |
| --------------- | ---------------------------------- |
| Name            | `portfolio-morning-check`          |
| Frequency       | Weekdays at 9:00 AM JST            |
| Permission mode | Auto accept                        |
| Worktree        | OFF (needs access to memory files) |
| Max turns       | 25 (default is sufficient)         |

**Prompt:**

```
Run /daily-check in the ib-sec-mcp project directory
```

**Step-by-step setup in Claude Desktop:**

1. Open Claude Desktop settings
2. Navigate to **Scheduled Tasks** (or **Projects** > your project > **Scheduled Tasks**)
3. Click **Add Task**
4. Enter the task name: `portfolio-morning-check`
5. Set the schedule: **Weekdays** at **9:00 AM**
6. Set permission mode to **Auto accept** — this allows the task to run without manual approval
7. Ensure **Worktree** is **OFF** — the `/daily-check` command needs direct access to `memory/` files
8. Paste the prompt text above
9. Save the task

### Optional Task: Evening Check (LSE Open)

For monitoring European ETFs when the London Stock Exchange opens.

**Configuration:**

| Setting         | Value                               |
| --------------- | ----------------------------------- |
| Name            | `portfolio-evening-check`           |
| Frequency       | Weekdays at 17:30 JST (8:30 AM GMT) |
| Permission mode | Auto accept                         |
| Worktree        | OFF                                 |

**Prompt:**

```
Run /daily-check in the ib-sec-mcp project directory. Focus on European ETFs: CSPX, VWRA, NDIA, IDTL, IB01, XNAS.
```

## Permission Configuration

The scheduled task needs specific permissions to run unattended. Add these to your project's `.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": ["mcp__ib-sec-mcp__*", "Read", "Write", "Edit"],
    "deny": [],
    "ask": []
  },
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["ib-sec-mcp"]
}
```

**Key points:**

- `mcp__ib-sec-mcp__*` — allows all MCP tools (price checks, order status, data sync)
- `Read`, `Write`, `Edit` — allows memory file updates (daily-snapshot, investment-strategy, portfolio-decisions)
- No `Bash` permissions needed — all operations use MCP tools
- Permission mode **Auto accept** in the task configuration handles tool approval at runtime

## What `/daily-check` Does

Each run executes these steps automatically (under 3 minutes):

1. **Data Sync** — fetches latest data via `sync_daily_snapshot`
2. **Portfolio Positions** — gets current holdings via `analyze_consolidated_portfolio`
3. **Price Checks** — fetches current prices for all symbols in parallel
4. **Limit Order Status** — checks pending orders and proximity to fill prices
5. **Alert Generation** — flags based on thresholds:

| Condition                    | Alert Level | Label       |
| ---------------------------- | ----------- | ----------- |
| Current price <= limit price | FILL CHECK  | FILL_CHECK  |
| Limit order distance <= 3%   | URGENT      | URGENT      |
| Limit order distance <= 5%   | APPROACHING | APPROACHING |
| Daily price change > +/-3%   | VOLATILE    | VOLATILE    |

6. **Memory Updates** — writes results to the 3-layer memory system

## 3-Layer Memory Architecture

Scheduled tasks interact with the memory system as follows:

```
Layer 1: investment-policy.md     ← NEVER modified by automation
Layer 2: investment-strategy.md   ← CONDITIONAL (order fills, urgent alerts)
Layer 3: daily-snapshot.md        ← OVERWRITE every run
         portfolio-decisions.md   ← APPEND on order fills
```

### Update Rules

| File                     | Mode        | When Updated                                       |
| ------------------------ | ----------- | -------------------------------------------------- |
| `daily-snapshot.md`      | OVERWRITE   | Every run                                          |
| `investment-strategy.md` | CONDITIONAL | Order filled, urgent alert (<3%), tranche complete |
| `portfolio-decisions.md` | APPEND      | Order filled only                                  |
| `investment-policy.md`   | NEVER       | Only explicit user request                         |
| `MEMORY.md`              | RARELY      | New file created, protocol changes                 |

### How to Read Alerts

When you open a new Claude Code session, check `daily-snapshot.md` first. If it contains alerts:

- **FILL_CHECK** — an order may have filled; verify in IB and update strategy
- **URGENT** — price is within 3% of your limit order; prepare for execution
- **APPROACHING** — price is within 5%; monitor more closely
- **VOLATILE** — significant daily move (>3%); review if action needed

## Troubleshooting

### MCP Server Not Starting

**Symptoms:** Task fails immediately, "MCP server unavailable" error.

**Solutions:**

1. Verify `.env` file exists with valid `QUERY_ID` and `TOKEN`
2. Run `/mcp-status` manually to check server health
3. Check that `enableAllProjectMcpServers: true` is set in `.claude/settings.local.json`
4. Restart Claude Desktop and try again

### API Rate Limits

**Symptoms:** `sync_daily_snapshot` returns stale data or timeout.

**Solutions:**

1. The fetch pipeline has built-in retry logic (3 retries, 5s delay)
2. If persistent, check IB Flex Query service status
3. The task will continue with cached data and note staleness in output

### Stale Data

**Symptoms:** `daily-snapshot.md` shows old prices or "cached" status.

**Solutions:**

1. Check `sync_daily_snapshot` result — look at `sync_date` field
2. Run `/fetch-latest` manually to force a fresh data pull
3. Verify IB Flex Query is returning recent data (check IB Account Management)

### Task Not Running

**Symptoms:** No updates to `daily-snapshot.md` on expected schedule.

**Solutions:**

1. Verify Claude Desktop is running (not just the menu bar icon)
2. Check system settings: "Keep computer awake" or prevent sleep during scheduled hours
3. Verify the task is enabled in Claude Desktop scheduled tasks list
4. Check that the project path in the task configuration is correct

### Memory Files Not Updating

**Symptoms:** Task completes but `daily-snapshot.md` is not updated.

**Solutions:**

1. Check file permissions on the `memory/` directory
2. Verify `Write` and `Edit` are in the allowed permissions list
3. Check that the memory directory path resolves correctly from the project context
4. Run `/daily-check` manually to see if errors appear in output
