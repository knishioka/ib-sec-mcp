# CLAUDE.md - Claude Code Development Guide

**Scope**: Claude Code-specific development (sub-agents, slash commands, settings)

> **Note**: For general project guidance (MCP tools, analyzers, usage modes), see `/CLAUDE.md` in repo root.

---

## Quick Reference

### Project Context

- **IB Analytics**: Portfolio analytics library for Interactive Brokers
- **Tech Stack**: Python 3.12+, Pydantic v2, pandas, FastMCP
- **Mode 3**: Advanced development workflow automation

### Key Files

- **README.md**: User documentation, 3 usage modes
- **/CLAUDE.md**: General development guide, usage mode design
- **.claude/CLAUDE.md**: This file (Claude Code extensions)
- **.claude/SUB_AGENTS.md**: Detailed sub-agent development guide
- **.claude/SLASH_COMMANDS.md**: Detailed slash command development guide
- **.claude/README.md**: Complete feature list

---

## Sub-Agents (11 specialized experts)

### Quick List

1. **data-analyzer** 📊 - Financial data analysis
2. **tax-optimizer** 💰 - Tax optimization (Malaysia tax resident)
3. **test-runner** 🧪 - Testing & QA
4. **code-implementer** 💻 - Feature implementation (TDD)
5. **code-reviewer** 📝 - Code quality enforcement
6. **performance-optimizer** ⚡ - Code profiling & optimization
7. **api-debugger** 🔧 - IB API troubleshooting
8. **issue-analyzer** 🔍 - GitHub issue analysis
9. **market-analyst** 📈 - Stock/options market analysis
10. **strategy-coordinator** 🎯 - Investment strategy orchestration
11. **portfolio-risk-analyst** ⚠️ - Portfolio risk analysis (concentration, VaR, correlation)

### When to Create

- ✅ Specialized domain knowledge required
- ✅ Repeated frequently (3+ times)
- ✅ Benefits from context isolation
- ❌ One-off operations
- ❌ Requires full project context

### File Structure

**Location**: `.claude/agents/{agent-name}.md`

````yaml
---
name: agent-name
description: When to use. Add "Use PROACTIVELY" for auto-activation.
tools: Read, Write, Bash(pytest:*)  # Minimal required only
model: sonnet  # sonnet | opus | haiku
---

You are a [role] with expertise in:
- Area 1
- Area 2

## Responsibilities
1. Primary task
2. Quality assurance

## Workflow
Step-by-step process

## Tools Usage
```bash
command --flags
```

## Quality Checklist

- [ ] Check 1
- [ ] Check 2
````

**Detailed Guide**: See `.claude/SUB_AGENTS.md`

---

## Slash Commands (21 automated workflows)

### Quick List

**Analysis**: `/optimize-portfolio`, `/compare-periods`, `/tax-report`, `/validate-data`, `/rebalance-portfolio`
**Investment**: `/investment-strategy`, `/analyze-symbol`, `/options-strategy`
**Portfolio**: `/dividend-analysis`, `/sector-analysis`, `/wash-sale-check`, `/fx-exposure`
**Monitoring**: `/daily-check`
**Development**: `/test`, `/quality-check`, `/add-test`, `/benchmark`
**Utility**: `/mcp-status`, `/debug-api`, `/resolve-gh-issue`, `/fetch-latest`

### When to Create

- ✅ Repeated 3+ times
- ✅ Consistent structure
- ✅ Clear, predictable arguments
- ❌ One-time operations
- ❌ Requires human judgment

### File Structure

**Location**: `.claude/commands/{command-name}.md`

```yaml
---
description: One-line description
allowed-tools: Read, Write, mcp__ib-sec-mcp__*
argument-hint: [expected-args]
---

Brief description.

**Arguments**:
- `$ARGUMENTS` - Full string
- `$1`, `$2` - Positional args

**Steps**:
1. Action with tool
2. Delegate to sub-agent
3. Validate results

**Error Handling**:
- If X fails, do Y

**Expected Output**:
Format description
```

**Detailed Guide**: See `.claude/SLASH_COMMANDS.md`

---

## Development Essentials

### Python Conventions

- **Line Length**: 100 chars max
- **Type Hints**: Required, mypy strict mode
- **Docstrings**: Google-style, required for public APIs
- **Financial Math**: Always use `Decimal` (never `float`)

### Command Execution

**IMPORTANT**: Always use `uv run` to execute Python commands. Never use `.venv/bin/python` directly.

```bash
# ✅ Correct
uv run pytest tests/
uv run ruff check ib_sec_mcp
uv run mypy ib_sec_mcp

# ❌ Wrong - do not use .venv directly
.venv/bin/python -m pytest tests/
```

This applies to all contexts including worktrees and sub-agents.

### Code Quality

```bash
# Format
uv run ruff format ib_sec_mcp tests

# Lint
uv run ruff check ib_sec_mcp tests --fix

# Type check
uv run mypy ib_sec_mcp

# Test
uv run pytest --cov=ib_sec_mcp
```

### Repository Etiquette

- **Branches**: `feature/`, `fix/`, `refactor/`, `docs/`
- **Commits**: `type: description` (feat, fix, refactor, docs, test, chore)
- **PRs**: Include motivation, changes, testing notes
- **Merge**: Squash and merge for features

---

## MCP Server Quick Reference

### Analysis Tools (7 coarse-grained)

`fetch_ib_data`, `analyze_performance`, `analyze_costs`, `analyze_bonds`, `analyze_tax`, `analyze_risk`, `get_portfolio_summary`

### Composable Tools (5 fine-grained)

`get_trades`, `get_positions`, `get_account_summary`, `calculate_metric`, `compare_periods`

### Resources (6 URI patterns)

`ib://portfolio/list`, `ib://portfolio/latest`, `ib://accounts/{id}`, `ib://trades/recent`, `ib://positions/current`

### Strategy Resources (3 URI patterns)

`ib://strategy/tax-context`, `ib://strategy/rebalancing-context`, `ib://strategy/risk-context`

---

## Common Tasks

### Adding New Analyzer

1. Create `ib_sec_mcp/analyzers/{name}.py`
2. Inherit from `BaseAnalyzer`
3. Implement `analyze()` → `AnalysisResult`
4. Add to `__init__.py` exports
5. Update `ConsoleReport` rendering
6. Add CLI option in `analyze.py`

### Adding MCP Tool

1. Add function in `ib_sec_mcp/mcp/tools.py`
2. Use `@mcp.tool()` decorator
3. Type hints + docstring required
4. Return JSON-serializable data
5. Test with Claude Desktop

### Creating Sub-Agent

1. Create `.claude/agents/{name}.md`
2. Add frontmatter (name, description, tools, model)
3. Write system prompt with expertise
4. Include workflow + quality checklist
5. Test explicit and auto-activation

### Creating Slash Command

1. Create `.claude/commands/{name}.md`
2. Add frontmatter (description, tools, argument-hint)
3. Define steps + error handling
4. Test with/without arguments

---

## Important Warnings

### Financial Code Requirements

- ✅ Always use `Decimal` for money
- ✅ Validate all user inputs
- ✅ Handle missing data gracefully
- ❌ Never use `float` for calculations
- ❌ Never commit `.env` files

### API & Data

- IB Flex Query API has rate limits (3 retries, 5s delay)
- CSV has multiple sections (detect by `ClientAccountID`)
- Single Flex Query can return multiple accounts
- Bond maturity dates may be missing

### Testing

- Tests not yet fully implemented (TODO)
- Always run tests via `uv run pytest` (never `.venv/bin/python -m pytest`)
- Use fixtures in `tests/fixtures/`
- Mock API calls with `pytest-asyncio`

---

## Settings Configuration

**File**: `.claude/settings.local.json` (gitignored)

```json
{
  "permissions": {
    "allow": ["Bash(pytest:*)", "Read", "Write", "mcp__ib-sec-mcp__*"],
    "deny": [],
    "ask": []
  },
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["ib-sec-mcp"]
}
```

## Timeout Configuration

**Critical**: Claude Code has a 10-minute hard timeout. Configure appropriate timeouts to ensure operations complete reliably.

**Recommended settings** for `~/.claude/settings.json`:

```json
{
  "env": {
    "BASH_DEFAULT_TIMEOUT_MS": "1800000", // 30 minutes (for long operations)
    "BASH_MAX_TIMEOUT_MS": "7200000", // 120 minutes (absolute max)
    "MCP_TIMEOUT": "300000" // 5 minutes (MCP server startup)
  }
}
```

**Why these values**:

- **Investment strategy**: 6-8 min target with 2+ min safety margin
- **MCP server startup**: IB Flex Query API can be slow initially
- **Development workflows**: Complex operations need headroom
- **Batch processing**: Multiple parallel agents need buffer time

**Operation Time Targets**:
| Operation | Target Time | Max Time | Safety Margin |
|-----------|-------------|----------|---------------|
| `/investment-strategy` | 6-8 min | 10 min | 2+ min |
| `/analyze-symbol` | 30-60s | 2 min | 1 min |
| `/options-strategy` | 45-90s | 3 min | 1.5 min |
| `/optimize-portfolio` | 2-3 min | 5 min | 2 min |
| `/resolve-gh-issue` | 5-8 min | 10 min | 2 min |

**Monitoring Best Practices**:

1. Check elapsed time at major checkpoints
2. Abort non-critical operations if approaching timeout
3. Generate partial results rather than failing completely
4. Log timeout warnings for debugging

---

---

## Resources

- **.claude/README.md**: Complete feature list (11 sub-agents, 20 commands)
- **.claude/SUB_AGENTS.md**: Detailed sub-agent development guide
- **.claude/SLASH_COMMANDS.md**: Detailed slash command development guide
- **/CLAUDE.md**: General project development guide
- **README.md**: User documentation and usage modes

---

**Last Updated**: 2025-10-11
**Version**: 0.1.0
**Maintainer**: Kenichiro Nishioka

**Note**: Keep this file concise. Detailed guides are in separate files to minimize token consumption.
