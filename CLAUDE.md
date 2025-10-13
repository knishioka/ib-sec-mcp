# IB Analytics - Development Guide

**Scope**: General project development (MCP tools, analyzers, usage modes)

> **Note**: For Claude Code-specific development (sub-agents, slash commands), see `.claude/CLAUDE.md`

---

## Project Mission

Enable systematic analysis of trading performance across multiple IB accounts with type-safe, modular, and extensible architecture.

---

## Usage Modes

IB Analytics supports **three distinct usage modes** optimized for different user types:

### Mode 1: Claude Desktop (Conversational Analysis)

**Target**: Investors, portfolio managers, financial analysts

**Characteristics**:
- Natural language queries
- Zero coding required
- Complete analysis from single question
- Automated data fetching

**Example**:
```
"Analyze my portfolio and suggest tax optimization strategies"
→ Claude Desktop → MCP Server → Complete Analysis + Recommendations
```

**Development Focus**:
- Coarse-grained MCP tools (self-contained, complete analysis)
- User-friendly error messages
- Rich, actionable output
- Prompt templates for guided analysis

---

### Mode 2: Claude Code + MCP (Custom Analysis)

**Target**: Data scientists, quantitative analysts, developers

**Characteristics**:
- Direct MCP tool composition
- Fine-grained data access
- Custom analysis workflows
- Programmatic approach

**Example**:
```python
trades = get_trades(symbol="AAPL", start_date="2025-01-01", end_date="2025-03-31")
win_rate = calculate_metric(metric_name="win_rate", asset_class="BOND")
comparison = compare_periods("2025-01-01", "2025-03-31", "2025-04-01", "2025-06-30")
```

**Development Focus**:
- Fine-grained composable tools
- Flexible filtering (symbol, asset_class, date_range)
- Strategy resources for algorithm context
- JSON-serializable return types

---

### Mode 3: Claude Code + Repository (Advanced Development)

**Target**: Developers, DevOps engineers, power users

**Characteristics**:
- Specialized sub-agents (7 experts)
- Custom slash commands (12 workflows)
- GitHub integration (Issue → PR)
- Automated quality gates

**Example**:
```bash
/resolve-gh-issue 42
# Automated workflow: Issue analysis → Tests → Implementation → Quality checks → PR
# Result: 80 minutes → 8 minutes (90% time savings)
```

**Development Focus**:
- Sub-agent architecture (domain expertise, context isolation)
- Slash command reusability (repeated workflows)
- GitHub API integration
- TDD workflow enforcement

---

## Development Decision Framework

When adding new features, consider which usage modes it supports:

### Adding Analysis Capability

| Mode | Implementation |
|------|---------------|
| **Mode 1** | Create coarse-grained MCP tool (e.g., `analyze_sharpe_ratio`) + prompt template |
| **Mode 2** | Add composable tool (e.g., `calculate_metric(metric_name="sharpe_ratio")`) |
| **Mode 3** | Create slash command (e.g., `/sharpe-analysis`) + integrate with sub-agent |

### Adding Data Source

| Mode | Implementation |
|------|---------------|
| **Mode 1** | Integrate into existing analysis tools seamlessly |
| **Mode 2** | Expose as composable data access tool with flexible filtering |
| **Mode 3** | Create dedicated sub-agent if complex + slash command for common workflows |

### Adding Quality Check

| Mode | Implementation |
|------|---------------|
| **Mode 1** | N/A (users don't see code quality) |
| **Mode 2** | Expose as optional validation step |
| **Mode 3** | Add to code-reviewer sub-agent + integrate into `/quality-check` command |

---

## Architecture Principles by Mode

### Mode 1: User-Centric Design
- **Completeness**: One tool = complete analysis
- **Clarity**: Results must be self-explanatory
- **Safety**: Robust error handling with recovery
- **Guidance**: Prompts lead users through complexity

### Mode 2: Composability
- **Modularity**: Fine-grained tools for flexibility
- **Consistency**: Uniform data models across tools
- **Extensibility**: Easy to combine tools
- **Type Safety**: Strongly-typed interfaces

### Mode 3: Automation
- **Orchestration**: Tools coordinate seamlessly
- **Specialization**: Sub-agents have deep expertise
- **Efficiency**: Commands eliminate repetition
- **Quality**: Automated gates ensure standards

---

## Implementation Guidelines

### MCP Tools

**Coarse-Grained (Mode 1)**:
```python
@mcp.tool()
def analyze_performance(start_date: str, end_date: str = None) -> str:
    """Complete analysis with interpretation"""
    # Fetch, analyze, format → rich human-readable report
```

**Fine-Grained (Mode 2)**:
```python
@mcp.tool()
def calculate_metric(metric_name: str, start_date: str, symbol: str = None) -> str:
    """Single metric calculation"""
    # Return structured JSON for programmatic use
```

### Sub-Agents (Mode 3)

**File**: `.claude/agents/{name}.md`

```yaml
---
name: agent-name
description: When to use (be specific)
tools: Minimal required tools only
model: sonnet  # sonnet | opus | haiku
---

You are a [role] with expertise in:
- Domain knowledge

## Responsibilities
[List primary tasks]

## Workflow
[Step-by-step process]

## Quality Checklist
- [ ] Standards to enforce
```

### Slash Commands (Mode 3)

**File**: `.claude/commands/{name}.md`

```yaml
---
description: One-line description
allowed-tools: Required tools
argument-hint: [expected-args]
---

**Steps**:
1. Action with tool
2. Delegate to sub-agent
3. Validate results

**Error Handling**:
[Recovery strategies]
```

---

## Performance Targets by Mode

| Mode | Metric | Target |
|------|--------|--------|
| **Mode 1** | Tool Response | < 5s for most analysis |
| **Mode 2** | Batch Operations | Support parallel tool calls |
| **Mode 3** | Issue → PR | < 10 minutes (target: 8min) |
| **Mode 3** | Quality Gates | < 2 minutes for full check |

---

## Security Considerations by Mode

| Mode | Focus | Requirements |
|------|-------|--------------|
| **Mode 1** | User Safety | Error masking, input validation, rate limiting |
| **Mode 2** | Data Integrity | Type safety (Pydantic), path traversal prevention |
| **Mode 3** | Code Quality | Automated security scans (bandit, safety), secret detection |

---

## Testing Strategy by Mode

| Mode | Test Type | Focus |
|------|-----------|-------|
| **Mode 1** | Integration | End-to-end workflows, user scenarios, error handling |
| **Mode 2** | Unit + Composition | Individual tool correctness, multi-tool workflows |
| **Mode 3** | Sub-Agent + Workflow | Context isolation, GitHub integration, quality gates |

---

## Quick Decision Checklist

**New Feature?**
1. Which modes should support it? (1, 2, 3, or combination)
2. Mode 1: Create coarse-grained MCP tool + prompt
3. Mode 2: Create fine-grained composable tool
4. Mode 3: Create sub-agent or slash command
5. Test appropriate to each mode
6. Document in relevant files (README.md, .claude/CLAUDE.md)

**Unsure?**
- If users need complete analysis → Mode 1 (coarse-grained)
- If developers need flexibility → Mode 2 (fine-grained)
- If workflow is repeated → Mode 3 (slash command)
- If expertise is specialized → Mode 3 (sub-agent)

---

## File Organization

| File | Scope | Audience |
|------|-------|----------|
| **README.md** | User documentation | End users |
| **CLAUDE.md** (this file) | General development | All developers |
| **.claude/CLAUDE.md** | Claude Code extensions | Claude Code developers |
| **.claude/SUB_AGENTS.md** | Sub-agent development | Mode 3 developers |
| **.claude/SLASH_COMMANDS.md** | Slash command development | Mode 3 developers |

---

## Data Storage Guidelines

**IMPORTANT**: Analysis results, planning documents, and working files must **NEVER** be committed to git.

### Gitignored Locations

| Directory | Purpose | Examples |
|-----------|---------|----------|
| `analysis/` | Analysis reports, comparative studies | ETF comparisons, portfolio reallocation plans |
| `notes/` | Planning documents, research notes | Investment strategies, decision journals |
| `data/raw/` | Raw CSV/XML from IB API | Account statements, trade history |
| `data/processed/` | Processed analysis results | JSON reports, computed metrics |

### File Naming Conventions

**Analysis Files** (in `analysis/`):
```
{symbol}_{analysis_type}_{date}.md
- PG_stock_analysis_2025-10-13.md
- ETF_comparison_IDTL_vs_TLT_2025-10-13.md
- portfolio_reallocation_plan_2025-10-13.md
```

**Notes** (in `notes/`):
```
{topic}_{date}.md
- investment_thesis_PG_2025-10-13.md
- market_outlook_tech_sector_2025-10.md
- trading_journal_2025-10-13.md
```

### What to Save Where

| Content Type | Location | Commit to Git? |
|--------------|----------|----------------|
| Code, analyzers | `ib_sec_mcp/` | ✅ Yes |
| Tests | `tests/` | ✅ Yes |
| Documentation | `README.md`, `CLAUDE.md` | ✅ Yes |
| **Analysis reports** | `analysis/` | ❌ No (gitignored) |
| **Planning documents** | `notes/` | ❌ No (gitignored) |
| **Account data** | `data/raw/` | ❌ No (gitignored) |
| **Processed results** | `data/processed/` | ❌ No (gitignored) |

### Security Best Practices

❌ **NEVER commit**:
- Account numbers (even obfuscated)
- Personal financial data
- Analysis containing real positions/amounts
- Planning documents with account IDs

✅ **Always use gitignored locations**:
- Save all analysis to `analysis/`
- Save all planning to `notes/`
- Let Claude Code/Desktop save files there automatically

### Example Workflow

```bash
# Claude Code analysis session
User: "Analyze P&G stock and create a buy/sell plan"

# Claude saves to gitignored location
→ analysis/PG_stock_analysis_2025-10-13.md
→ analysis/PG_entry_strategy_2025-10-13.md

# Files are automatically ignored by git
$ git status
# No new files shown
```

---

## Common Pitfalls

### Financial Code
- ❌ Never use `float` for money calculations
- ✅ Always use `Decimal` for precision

### Mode Selection
- ❌ Don't create Mode 3 sub-agent for one-off tasks
- ✅ Create Mode 2 composable tool for flexibility

### Documentation
- ❌ Don't duplicate content across files
- ✅ Reference detailed guides from main files

### Token Usage
- ❌ Don't add extensive content without iterating
- ✅ Keep CLAUDE.md files concise and human-readable

---

## Resources

- **README.md**: 3 usage modes, setup, basic usage
- **.claude/CLAUDE.md**: Sub-agents, slash commands, Claude Code development
- **.claude/SUB_AGENTS.md**: Detailed sub-agent guide with examples
- **.claude/SLASH_COMMANDS.md**: Detailed slash command guide with examples
- **.claude/README.md**: Complete feature list

---

**Last Updated**: 2025-10-11
**Version**: 0.1.0
**Maintainer**: Kenichiro Nishioka

**Note**: This file focuses on usage mode design and high-level architecture. For implementation details, see `.claude/` directory.
