# Slash Command Development Guide

Detailed guide for creating reusable workflow templates in Claude Code.

## Current Slash Commands (20)

**Analysis Commands**:

- `/optimize-portfolio` - Comprehensive portfolio analysis
- `/compare-periods` - Period-over-period comparison
- `/tax-report` - Tax planning report generation
- `/validate-data` - Data integrity validation
- `/rebalance-portfolio` - Portfolio rebalancing with target profiles

**Investment Commands**:

- `/investment-strategy` - Comprehensive investment strategy planning
- `/analyze-symbol` - Symbol analysis (stocks, ETFs, crypto, forex)
- `/options-strategy` - Options strategy analysis with Greeks and IV

**Portfolio Commands**:

- `/dividend-analysis` - Dividend income and Ireland ETF tax efficiency
- `/sector-analysis` - Sector allocation and concentration risk (HHI)
- `/wash-sale-check` - Wash sale detection and tax loss harvesting
- `/fx-exposure` - Currency exposure and FX risk simulation

**Development Commands**:

- `/test` - Run pytest test suite
- `/quality-check` - Full quality gate (black, ruff, mypy, pytest)
- `/add-test` - Create test file for module
- `/benchmark` - Performance profiling

**Utility Commands**:

- `/mcp-status` - MCP server health check
- `/debug-api` - IB API troubleshooting
- `/resolve-gh-issue` - Complete GitHub issue workflow
- `/fetch-latest` - Manual data fetching (legacy)

## When to Create New Slash Commands

Create a new slash command when:

- ✅ Workflow is **repeated 3+ times**
- ✅ Operation has **consistent structure**
- ✅ Team members would benefit from **standardization**
- ✅ Command has **clear, predictable arguments**
- ✅ Operation **coordinates multiple tools/sub-agents**

Do NOT create commands for:

- ❌ One-time operations
- ❌ Highly variable workflows
- ❌ Tasks requiring human judgment
- ❌ Simple single-tool invocations

## File Structure

**Location**: `.claude/commands/{command-name}.md`

**Required Frontmatter**:

```yaml
---
description: One-line command description (shows in menu)
allowed-tools: Read, Write, mcp__ib-sec-mcp__* # Optional tool permissions
argument-hint: [expected-args] # Optional argument guide
---
```

**Command Body Structure**:

```markdown
Brief description of what this command does.

**Arguments**: (if applicable)

- `$ARGUMENTS` - Full argument string
- `$1`, `$2`, `$3` - Positional arguments

**Steps**:

1. First step with tool usage
2. Second step with sub-agent delegation
3. Third step with validation
4. Final step with output format

**Error Handling**:

- If X fails, do Y
- If no data found, suggest Z

**Expected Output**:
Format of final result
```

## Development Example: Regression Testing

**File**: `.claude/commands/regression-test.md`

````markdown
---
description: Run regression tests with performance comparison
allowed-tools: Read, Bash(pytest:*), Bash(python3:*), mcp__ib-sec-mcp__get_trades
argument-hint: [baseline-version]
---

Run regression tests comparing current implementation against baseline version.

**Arguments**:

- `$ARGUMENTS` - Baseline git tag or commit hash (e.g., v1.0.0)
- If no arguments, compare against HEAD~1 (previous commit)

**Prerequisites**:

- [ ] All tests passing on current branch
- [ ] Baseline version tag exists
- [ ] Performance benchmark data available

**Steps**:

1. **Validate baseline version**
   ```bash
   git rev-parse --verify $ARGUMENTS
   ```
````

If invalid, suggest: `git tag -l` to list available tags

2. **Run current tests** (delegate to test-runner sub-agent)

   ```bash
   pytest --benchmark-only --benchmark-json=current.json
   ```

3. **Checkout baseline and run tests**

   ```bash
   git stash
   git checkout $ARGUMENTS
   pytest --benchmark-only --benchmark-json=baseline.json
   git checkout -
   git stash pop
   ```

4. **Compare results** (delegate to performance-optimizer sub-agent)
   - Parse both JSON files
   - Calculate performance delta (%)
   - Identify regressions (>10% slower)
   - Generate comparison report

5. **Quality gate**
   - ✅ All tests pass on both versions
   - ✅ No regressions >10%
   - ✅ Memory usage not increased >5%
   - ⚠️ Warn if any regression detected
   - ❌ Fail if critical regression (>20%)

**Error Handling**:

- If baseline tests fail: Report but continue (may be expected)
- If current tests fail: Stop immediately, report failures
- If git operations fail: Suggest clean working directory
- If benchmark data missing: Run regular tests instead

**Expected Output**:

```
Regression Test Report
======================
Baseline: v1.0.0 (abc1234)
Current:  feature/new-analyzer (def5678)

Performance Comparison:
  ✅ analyze_performance: 1.23s → 1.15s (-6.5%)
  ✅ analyze_tax:         0.89s → 0.87s (-2.2%)
  ⚠️  analyze_bonds:      0.45s → 0.52s (+15.6%) [REGRESSION]
  ✅ calculate_ytm:       0.12s → 0.11s (-8.3%)

Memory Usage:
  ✅ Peak RSS: 245MB → 238MB (-2.9%)

Result: ⚠️ WARNING - 1 performance regression detected
```

**Follow-up Actions**:

- If regressions detected, suggest: `/benchmark analyze_bonds` for profiling
- Create GitHub issue automatically if regression >20%

````

## Best Practices

### Argument Handling
- Use `$ARGUMENTS` for full argument string
- Use `$1`, `$2`, `$3` for positional arguments
- Always provide default values
- Validate arguments before execution

### Sub-Agent Delegation
- Delegate to appropriate sub-agent for specialized tasks
- Specify expected sub-agent output format
- Handle sub-agent errors gracefully

### Tool Permissions
- List all required tools in `allowed-tools`
- Use wildcards for flexibility: `Bash(pytest:*)`
- Include MCP tools: `mcp__ib-sec-mcp__*`

### Error Handling
- Anticipate common failure modes
- Provide recovery suggestions
- Never fail silently

### Output Format
- Use consistent formatting (tables, sections)
- Include success/warning/error indicators (✅⚠️❌)
- Provide actionable follow-up suggestions

## Orchestration Patterns

### Sequential Steps (each depends on previous)
```markdown
1. Fetch data (must succeed)
2. Validate data (must succeed)
3. Run analysis (proceed even if warnings)
4. Generate report (must succeed)
````

### Parallel Operations (independent)

```markdown
1. Launch multiple sub-agents in parallel:
   - test-runner for unit tests
   - code-reviewer for quality checks
   - performance-optimizer for benchmarks
2. Aggregate results when all complete
```

### Conditional Execution

```markdown
1. Check if data exists
   - If yes: Use cached data
   - If no: Fetch from IB API
2. Run analysis
3. If errors detected:
   - Delegate to api-debugger
   - Retry with different parameters
```

## Testing

**Manual Testing**:

```bash
# Test with arguments
/regression-test v1.0.0

# Test without arguments (should use default)
/regression-test

# Test error handling (invalid argument)
/regression-test invalid-tag
```

**Verification Checklist**:

- [ ] Command appears in slash command menu
- [ ] Description is clear and concise
- [ ] Arguments are parsed correctly
- [ ] Default values work as expected
- [ ] Error messages are helpful
- [ ] Output format is consistent
- [ ] Sub-agent delegation works
- [ ] Tool permissions are sufficient
