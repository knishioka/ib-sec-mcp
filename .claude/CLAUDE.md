# CLAUDE.md - Claude Code Development Guide

**Scope**: Claude Code-specific development (sub-agents, slash commands, settings)

> **Note**: For general project guidance (MCP tools, analyzers, usage modes), see `/CLAUDE.md` in repo root.

---

## Quick Reference

### Project Context
- **IB Analytics**: Portfolio analytics library for Interactive Brokers
- **Tech Stack**: Python 3.9+, Pydantic v2, pandas, FastMCP
- **Mode 3**: Advanced development workflow automation

### Key Files
- **README.md**: User documentation, 3 usage modes
- **/CLAUDE.md**: General development guide, usage mode design
- **.claude/CLAUDE.md**: This file (Claude Code extensions)
- **.claude/SUB_AGENTS.md**: Detailed sub-agent development guide
- **.claude/SLASH_COMMANDS.md**: Detailed slash command development guide
- **.claude/README.md**: Complete feature list

---

## Sub-Agents (7 specialized experts)

### Quick List
1. **data-analyzer** 📊 - Financial data analysis
2. **test-runner** 🧪 - Testing & QA
3. **code-implementer** 💻 - Feature implementation (TDD)
4. **code-reviewer** 📝 - Code quality enforcement
5. **performance-optimizer** ⚡ - Profiling & optimization
6. **api-debugger** 🔧 - IB API troubleshooting
7. **issue-analyzer** 🔍 - GitHub issue analysis

### When to Create
- ✅ Specialized domain knowledge required
- ✅ Repeated frequently (3+ times)
- ✅ Benefits from context isolation
- ❌ One-off operations
- ❌ Requires full project context

### File Structure
**Location**: `.claude/agents/{agent-name}.md`

```yaml
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
```

**Detailed Guide**: See `.claude/SUB_AGENTS.md`

---

## Slash Commands (12 automated workflows)

### Quick List
**Analysis**: `/optimize-portfolio`, `/compare-periods`, `/tax-report`, `/validate-data`
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

### Code Quality
```bash
# Format
ruff format ib_sec_mcp tests

# Lint
ruff check ib_sec_mcp tests --fix

# Type check
mypy ib_sec_mcp

# Test
pytest --cov=ib_sec_mcp
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
- ❌ Never modify legacy scripts

### API & Data
- IB Flex Query API has rate limits (3 retries, 5s delay)
- CSV has multiple sections (detect by `ClientAccountID`)
- Single Flex Query can return multiple accounts
- Bond maturity dates may be missing

### Testing
- Tests not yet fully implemented (TODO)
- Use `pytest` with fixtures in `tests/fixtures/`
- Mock API calls with `pytest-asyncio`

---

## Settings Configuration

**File**: `.claude/settings.local.json` (gitignored)

```json
{
  "permissions": {
    "allow": [
      "Bash(pytest:*)",
      "Read",
      "Write",
      "mcp__ib-sec-mcp__*"
    ],
    "deny": [],
    "ask": []
  },
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["ib-sec-mcp"]
}
```

---

## Resources

- **.claude/README.md**: Complete feature list (7 sub-agents, 12 commands)
- **.claude/SUB_AGENTS.md**: Detailed sub-agent development guide
- **.claude/SLASH_COMMANDS.md**: Detailed slash command development guide
- **/CLAUDE.md**: General project development guide
- **README.md**: User documentation and usage modes

---

**Last Updated**: 2025-10-11
**Version**: 0.1.0
**Maintainer**: Kenichiro Nishioka

**Note**: Keep this file concise. Detailed guides are in separate files to minimize token consumption.
