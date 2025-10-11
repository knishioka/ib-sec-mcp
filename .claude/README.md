# .claude/ Directory

This directory contains Claude Code configuration, custom commands, and specialized sub-agents for the IB Analytics project.

## 📁 Directory Structure

```
.claude/
├── CLAUDE.md              # Main project context (auto-loaded)
├── README.md              # This file
├── settings.local.json    # Local settings (gitignored)
├── agents/                # Specialized sub-agents (7 agents)
│   ├── test-runner.md
│   ├── data-analyzer.md
│   ├── api-debugger.md
│   ├── code-reviewer.md
│   ├── performance-optimizer.md
│   ├── issue-analyzer.md      # NEW: GitHub issue analysis
│   └── code-implementer.md    # NEW: Code implementation
└── commands/              # Custom slash commands (12 commands)
    ├── fetch-latest.md
    ├── debug-api.md
    ├── test.md
    ├── quality-check.md
    ├── optimize-portfolio.md
    ├── compare-periods.md
    ├── tax-report.md
    ├── add-test.md
    ├── benchmark.md
    ├── validate-data.md
    ├── mcp-status.md
    └── resolve-gh-issue.md    # NEW: Complete GitHub issue resolution
```

## 🤖 Sub-Agents (Context Isolation)

Specialized AI assistants that handle specific tasks in their own context window, keeping the main conversation focused.

### Available Sub-Agents

#### **test-runner** 🧪
**Purpose**: Testing specialist for pytest, coverage, and quality assurance
**When to use**: After code changes, before commits, for coverage analysis
**Tools**: pytest, pytest-cov, Read, Write, Grep
**Auto-activates**: On test-related queries

#### **data-analyzer** 📊
**Purpose**: Financial data analysis specialist for IB trading data
**When to use**: Deep portfolio analysis, performance metrics, tax planning
**Tools**: All MCP analysis tools, Python, Read
**Auto-activates**: On portfolio/analysis queries

#### **api-debugger** 🔧
**Purpose**: IB Flex Query API troubleshooting specialist
**When to use**: API connectivity issues, credential validation, debugging
**Tools**: curl, Python, grep, MCP fetch tools
**Auto-activates**: On API error queries

#### **code-reviewer** 📝
**Purpose**: Code quality and standards enforcement
**When to use**: Before commits, PR reviews, quality checks
**Tools**: black, ruff, mypy, Read, Grep
**Auto-activates**: PROACTIVE before commits

#### **performance-optimizer** ⚡
**Purpose**: Performance analysis and optimization
**When to use**: Profiling, benchmarking, bottleneck identification
**Tools**: cProfile, timeit, tracemalloc, Read
**Auto-activates**: On performance queries

#### **issue-analyzer** 🔍 (NEW!)
**Purpose**: GitHub issue analysis and requirement extraction
**When to use**: Analyzing GitHub issues, extracting acceptance criteria, planning implementation
**Tools**: gh CLI, Read, WebSearch, TodoWrite, Grep
**Model**: opus (for high precision)
**Auto-activates**: Via `/resolve-gh-issue` command

**Key Features**:
- Extracts structured requirements from GitHub issues
- Identifies acceptance criteria and technical scope
- Flags financial code requirements (Decimal precision, etc.)
- Generates implementation checklists
- Never hallucinates - always uses actual GitHub data

#### **code-implementer** 💻 (NEW!)
**Purpose**: Python implementation specialist with financial software expertise
**When to use**: Implementing features, writing analyzers, TDD development
**Tools**: Edit, MultiEdit, Write, Read, WebSearch, TodoWrite, Python tools
**Model**: opus (for complex implementations)
**Auto-activates**: Via `/resolve-gh-issue` command

**Key Features**:
- Follows existing codebase patterns
- Enforces Decimal precision for financial calculations
- Implements Pydantic v2 models correctly
- Writes comprehensive docstrings
- Test-Driven Development (TDD) workflow
- WebSearch for best practices research

### How Sub-Agents Work

**Automatic Delegation**:
```
You: "Run tests with coverage"
Claude: [Delegates to test-runner sub-agent]
test-runner: [Executes pytest in isolated context]
test-runner: [Returns results to main thread]
Claude: [Presents formatted results]
```

**Explicit Invocation**:
```
You: "Use the data-analyzer subagent to analyze my portfolio"
Claude: [Explicitly delegates to data-analyzer]
```

**Benefits**:
- ✅ **Context Isolation**: Each sub-agent has dedicated context window
- ✅ **Specialization**: Expert knowledge for specific domains
- ✅ **Parallel Work**: Multiple sub-agents can work simultaneously
- ✅ **Clean Main Thread**: Main conversation stays focused on high-level tasks

## 📋 Slash Commands (Quick Workflows)

Pre-configured prompts for common operations. Type `/` in Claude Code to see all available commands.

### Development Commands

#### `/test [--coverage|--verbose|--failed|pattern]`
Run pytest test suite with coverage reporting
Delegates to: **test-runner** sub-agent

```bash
/test                  # Full test suite with coverage
/test --verbose        # Verbose output
/test --coverage       # Quick coverage check
/test --failed         # Re-run failed tests only
/test performance      # Run tests matching "performance"
```

#### `/quality-check [--fix|--strict]`
Run full quality gate: format, lint, type, test
Delegates to: **code-reviewer** sub-agent

```bash
/quality-check         # Check all quality gates
/quality-check --fix   # Auto-fix issues
/quality-check --strict # Strict mode for CI/CD
```

#### `/add-test module-name [--analyzer|--parser|--model]`
Create comprehensive test file for module
Delegates to: **test-runner** sub-agent

```bash
/add-test performance --analyzer
/add-test csv_parser --parser
/add-test Trade --model
```

#### `/benchmark [--full|--quick|module-name]`
Performance benchmarking and profiling
Delegates to: **performance-optimizer** sub-agent

```bash
/benchmark             # Quick benchmark
/benchmark --full      # Full benchmark suite
/benchmark bond        # Benchmark specific module
```

### Analysis Commands

#### `/optimize-portfolio [csv-file-path]`
Comprehensive portfolio analysis with recommendations
Delegates to: **data-analyzer** sub-agent

```bash
/optimize-portfolio                              # Use latest CSV
/optimize-portfolio data/raw/U1234567_*.csv    # Specific file
```

#### `/compare-periods period1-start period1-end period2-start period2-end`
Compare performance across two time periods
Delegates to: **data-analyzer** sub-agent

```bash
/compare-periods 2025-01-01 2025-03-31 2025-04-01 2025-06-30
/compare-periods --ytd          # Compare YTD vs previous YTD
/compare-periods --quarter      # Current vs previous quarter
/compare-periods --month        # Current vs previous month
```

#### `/tax-report [--year YYYY|--ytd|--save]`
Generate comprehensive tax analysis report
Delegates to: **data-analyzer** sub-agent

```bash
/tax-report                # Current year
/tax-report --year 2024    # Specific year
/tax-report --ytd          # Year-to-date
/tax-report --save         # Save to file
```

#### `/validate-data [csv-file-path|--latest]`
Data integrity and format validation

```bash
/validate-data                        # Validate all CSVs
/validate-data --latest              # Latest file only
/validate-data data/raw/file.csv     # Specific file
```

### Utility Commands

#### `/mcp-status [--verbose|--test]`
Check MCP server health and tool availability

```bash
/mcp-status            # Basic health check
/mcp-status --verbose  # Detailed output
/mcp-status --test     # Run functionality tests
```

#### `/debug-api [--verbose|--test-credentials]`
Troubleshoot IB API connectivity
Delegates to: **api-debugger** sub-agent

```bash
/debug-api                    # Full diagnostic
/debug-api --verbose          # Detailed output
/debug-api --test-credentials # Test credentials only
```

### GitHub Workflow Commands (NEW!)

#### `/resolve-gh-issue issue-number [--skip-checks|--skip-tests|--dry-run]`
Complete GitHub issue resolution workflow with TDD
Orchestrates: **issue-analyzer**, **test-runner**, **code-implementer**, **code-reviewer** sub-agents

```bash
/resolve-gh-issue 42                   # Full workflow for issue #42
/resolve-gh-issue 42 --dry-run         # Show plan without executing
/resolve-gh-issue 42 --skip-checks     # Skip quality checks (not recommended)
/resolve-gh-issue 42 --skip-tests      # Create tests but don't run
```

**Complete 10-Phase Workflow**:
1. **Issue Analysis** - Extract requirements from GitHub issue (issue-analyzer)
2. **Planning** - Create task breakdown and branch (TodoWrite + git)
3. **Test Creation** - Write failing tests first (TDD via test-runner)
4. **Implementation** - Implement solution (code-implementer)
5. **Quality Assurance** - Run all quality checks (code-reviewer)
6. **Documentation** - Update docstrings and CHANGELOG
7. **Commit** - Create structured commit with issue reference
8. **Pull Request** - Generate PR with comprehensive description
9. **CI Monitoring** - Watch CI checks for failures
10. **Issue Closure** - Automatic closure when PR merges

**Quality Gates**:
- ✅ All acceptance criteria met
- ✅ Tests created and passing (≥80% coverage)
- ✅ Black formatting applied
- ✅ Ruff linting passed
- ✅ Mypy type checking strict mode
- ✅ Financial code validation (Decimal precision)
- ✅ Documentation complete

**Example Output**:
```
[1/10] Analyzing Issue #42...
✓ Requirements extracted
✓ Acceptance criteria: 4 items
✓ Financial code: YES (Decimal required)

[2/10] Creating task breakdown...
✓ 6 tasks created in TodoList

[3/10] Creating tests (TDD)...
✓ Test file: tests/test_analyzers/test_performance_sharpe.py
✓ 8 tests created (failing as expected)

[4/10] Implementing solution...
✓ Method: calculate_sharpe_ratio() implemented
✓ All tests passing: 8/8 ✓

[5/10] Running quality checks...
✓ black, ruff, mypy all passed

[6/10] Creating PR #123...
✓ URL: https://github.com/user/repo/pull/123

✅ Issue #42 resolved successfully!
```

### Legacy Commands

This command is still available for manual data fetching:

- `/fetch-latest [--multi-account|--start-date|--end-date]` - Fetch IB data manually

**Note**: For new features, use `/resolve-gh-issue` which provides a complete workflow from issue to PR.

## 🏗️ Architecture Overview

### System Architecture

The IB Analytics project follows a modular, layered architecture optimized for financial data processing:

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Layer                                │
│  (ib-sec-fetch, ib-sec-analyze, ib-sec-report)                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     MCP Server Layer                            │
│  (FastMCP - Model Context Protocol for Claude Desktop)         │
│  • 7 Tools (fetch, analyze_*, get_portfolio_summary)           │
│  • 6 Resources (portfolio URIs, account data)                  │
│  • 5 Prompts (analysis templates)                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   Core Analysis Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Analyzers   │  │  Aggregator  │  │  Calculator  │         │
│  │ • Performance│  │ • Multi-acct │  │ • YTM        │         │
│  │ • Cost       │  │ • Rollup     │  │ • Duration   │         │
│  │ • Bond       │  │ • Reporting  │  │ • Tax        │         │
│  │ • Tax        │  └──────────────┘  └──────────────┘         │
│  │ • Risk       │                                              │
│  └──────────────┘                                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Data Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Parsers     │  │  Models      │  │  API Client  │         │
│  │ • CSV        │  │ • Trade      │  │ • FlexQuery  │         │
│  │ • XML        │  │ • Position   │  │ • Async      │         │
│  │ • Multi-sect │  │ • Account    │  │ • Retry      │         │
│  └──────────────┘  │ • Portfolio  │  └──────────────┘         │
│                    │ (Pydantic v2)│                            │
│                    └──────────────┘                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  External Services                              │
│  • IB Flex Query API (Interactive Brokers)                     │
│  • GitHub API (via gh CLI)                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Data Ingestion**: Flex Query API → CSV Parser → Pydantic Models
2. **Analysis**: Models → Analyzers → AnalysisResult
3. **Reporting**: AnalysisResult → Report Renderer → Console/File
4. **Integration**: MCP Server → Claude Desktop → User Interaction

### Key Design Principles

- **Type Safety**: Pydantic v2 models with strict validation
- **Financial Accuracy**: Decimal precision throughout (never float)
- **Modularity**: Pluggable analyzers and reports
- **Async Support**: Async API client for multi-account operations
- **Error Handling**: Custom exceptions with detailed context

### Claude Code Integration

```
User Query → Claude Code → MCP Server → IB Analytics Library → Results
     │                          │
     └──────────────────────────┴→ Sub-Agents:
                                   • issue-analyzer (GitHub)
                                   • code-implementer (TDD)
                                   • test-runner (pytest)
                                   • code-reviewer (quality)
                                   • data-analyzer (portfolio)
                                   • api-debugger (diagnostics)
                                   • performance-optimizer (profiling)
```

## 🚀 Quick Start Guide

### 1. First-Time Setup

```bash
# Verify MCP server
/mcp-status

# Fetch latest data
/fetch-latest

# Run quality check
/quality-check
```

### 2. Daily Development Workflow

```bash
# Before coding
/quality-check              # Ensure clean baseline

# During coding
# [Make changes]

# Before commit
/quality-check --fix        # Auto-fix issues
/test                       # Run tests
```

### 3. Portfolio Analysis Workflow

```bash
# Get latest data
/fetch-latest

# Validate data
/validate-data --latest

# Comprehensive analysis
/optimize-portfolio

# Tax planning
/tax-report --save
```

### 4. Performance Optimization Workflow

```bash
# Benchmark current state
/benchmark --full

# Profile specific module
/benchmark bond

# [Make optimizations]

# Verify improvements
/benchmark --full
```

## 📚 Best Practices

### Using Sub-Agents

**When to delegate to sub-agents**:
- ✅ Complex, specialized tasks (testing, profiling, analysis)
- ✅ Tasks requiring isolated context (prevent main thread pollution)
- ✅ Repetitive workflows that benefit from expertise

**When NOT to delegate**:
- ❌ Simple one-off tasks
- ❌ Tasks requiring main context awareness
- ❌ Quick questions or clarifications

### Using Slash Commands

**Create new commands when**:
- ✅ Repeating the same workflow 3+ times
- ✅ Task has consistent structure and arguments
- ✅ Team members would benefit from standardization

**Don't create commands for**:
- ❌ One-time operations
- ❌ Highly variable workflows
- ❌ Tasks that need human judgment

### Context Management

**Project Context** (`.claude/CLAUDE.md`):
- Project-specific conventions
- Architecture decisions
- Common workflows
- Team standards

**User Context** (`~/.claude/CLAUDE.md`):
- Personal preferences
- Global coding style
- Cross-project patterns

**Sub-Agent Context** (`.claude/agents/*.md`):
- Specialized knowledge
- Domain expertise
- Tool configurations

## 🔧 Maintenance

### Regular Updates

**Weekly**:
- Review sub-agent performance
- Update command arguments if needed

**Monthly**:
- Review CLAUDE.md for accuracy
- Add new commands for emerging patterns
- Archive unused commands

**After Major Changes**:
- Update CLAUDE.md with new conventions
- Add commands for new workflows
- Update sub-agent tools/permissions

### Quality Checks

```bash
# Verify all commands work
/mcp-status

# Test sub-agents
/test --verbose
/quality-check
/benchmark --quick

# Validate data pipeline
/validate-data --latest
```

## 📖 Additional Resources

### Documentation
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Sub-Agents Guide](https://docs.claude.com/en/docs/claude-code/sub-agents)
- [Slash Commands Guide](https://docs.claude.com/en/docs/claude-code/slash-commands)

### Examples
- See `WORKFLOWS.md` for complete workflow examples
- Check individual command files for usage examples
- Review sub-agent files for specialization details

---

**Last Updated**: 2025-10-11
**Maintained By**: Development Team

**New in this version (v2.1)** - Cleaned & Streamlined:
- ✨ 7 specialized sub-agents (issue-analyzer, code-implementer added)
- 📋 12 slash commands (removed 3 obsolete, added /resolve-gh-issue)
- 🏗️ Architecture overview section added
- 🎯 Enhanced test-runner and code-reviewer with issue validation
- 🔄 Complete Test-Driven Development (TDD) workflow
- 🐙 GitHub integration: issue → branch → tests → code → PR → CI
- 🧹 Cleaned up redundant documentation

**Version v2.0** (Previous):
- 7 sub-agents, 15 slash commands
- Initial GitHub workflow integration

**Version v1.0**:
- 5 sub-agents, 14 slash commands
- Basic portfolio analysis tools
