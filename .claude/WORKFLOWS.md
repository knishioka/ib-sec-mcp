# Claude Code Workflows for IB Analytics

Complete workflow examples demonstrating how to use sub-agents and slash commands for common development and analysis tasks.

## 🚀 Development Workflows

### Workflow 1: Feature Development (TDD Approach)

**Scenario**: Adding a new "Sharpe Ratio" analyzer

```bash
# Step 1: Create test file first (TDD)
/add-test sharpe --analyzer

# Sub-agent: test-runner
# Creates: tests/test_analyzers/test_sharpe.py with fixtures and test cases

# Step 2: Run failing tests (should fail - no implementation yet)
/test sharpe

# Sub-agent: test-runner
# Output: Tests fail as expected (no SharpeAnalyzer exists)

# Step 3: Implement the analyzer
# [Manually code SharpeAnalyzer class in ib_sec_mcp/analyzers/sharpe.py]

# Step 4: Run tests again
/test sharpe --verbose

# Sub-agent: test-runner
# Output: Tests pass, coverage report shows 85%

# Step 5: Quality check before commit
/quality-check --fix

# Sub-agent: code-reviewer
# Runs: black (format) → ruff (lint) → mypy (types) → pytest (tests)
# Output: ✅ All checks passed, ready to commit
```

**Expected Time**: 15-20 minutes
**Sub-Agents Used**: test-runner (2x), code-reviewer (1x)

---

### Workflow 2: Bug Fix with Root Cause Analysis

**Scenario**: API fetch failing intermittently

```bash
# Step 1: Diagnose the issue
/debug-api --verbose

# Sub-agent: api-debugger
# Performs: Environment check → Config validation → API connectivity test
# Output: ⚠️ Found issue - Token has spaces, causing intermittent failures

# Step 2: Fix the issue
# [Edit .env file to remove spaces from TOKEN]

# Step 3: Verify fix
/debug-api --test

# Sub-agent: api-debugger
# Output: ✅ All tests pass, API connectivity confirmed

# Step 4: Fetch fresh data to confirm
/fetch-latest

# Output: ✅ Successfully fetched data for account U16231259

# Step 5: Validate data integrity
/validate-data --latest

# Output: ✅ Data validation passed, ready for analysis
```

**Expected Time**: 5-10 minutes
**Sub-Agents Used**: api-debugger (2x)

---

### Workflow 3: Performance Optimization

**Scenario**: BondAnalyzer is slow, need to optimize

```bash
# Step 1: Establish baseline
/benchmark bond

# Sub-agent: performance-optimizer
# Output: BondAnalyzer: 1.23s (⚠️ 23% over target of 1.0s)
#         Bottleneck: YTM calculation (890ms, 1,234 calls)

# Step 2: Implement caching
# [Add @lru_cache to calculate_ytm function]

from functools import lru_cache

@lru_cache(maxsize=256)
def calculate_ytm(face_value: Decimal, price: Decimal, years: Decimal) -> Decimal:
    # existing logic
    pass

# Step 3: Benchmark after optimization
/benchmark bond

# Sub-agent: performance-optimizer
# Output: BondAnalyzer: 0.67s (✅ 33% under target)
#         Improvement: 56% faster (1.23s → 0.67s)

# Step 4: Run full benchmark to check for regressions
/benchmark --full

# Sub-agent: performance-optimizer
# Output: All analyzers within targets, no regressions detected

# Step 5: Verify correctness with tests
/test bond

# Sub-agent: test-runner
# Output: ✅ All tests pass, optimization successful
```

**Expected Time**: 20-30 minutes
**Sub-Agents Used**: performance-optimizer (3x), test-runner (1x)

---

## 📊 Portfolio Analysis Workflows

### Workflow 4: Comprehensive Portfolio Review

**Scenario**: Monthly portfolio review and optimization

```bash
# Step 1: Fetch latest data
/fetch-latest

# Output: ✅ Fetched data for 2025-10-01 to 2025-10-11

# Step 2: Validate data quality
/validate-data --latest

# Output: ✅ Validation passed, 1,456 trades, 52 positions
#         ⚠️ 3 bonds missing maturity dates (acceptable)

# Step 3: Run comprehensive analysis
/optimize-portfolio

# Sub-agent: data-analyzer
# Analyzes: Performance, Costs, Bonds, Tax, Risk
# Output:
#   📊 Performance: Win rate 68%, Profit factor 1.85
#   💰 Costs: $234 commissions (0.31% of traded value)
#   🏦 Bonds: 12 holdings, Avg YTM 3.8%, Duration 4.2 years
#   💵 Tax: $12,450 short-term gains, $3,567 phantom income
#   ⚠️ Risk: Largest position 18% (moderate concentration)
#
# 🎯 Recommendations:
#   1. Harvest $1,890 in losses (Symbol DEF, GHI)
#   2. Trim largest position from 18% to 12%
#   3. Add 2028 bond maturity for ladder diversification

# Step 4: Generate tax report for planning
/tax-report --save

# Sub-agent: data-analyzer
# Output: Tax report saved to data/processed/tax_report_2025.txt
#         Estimated tax liability: $5,789
#         Potential savings with optimization: $711

# Step 5: Compare with previous period
/compare-periods --quarter

# Sub-agent: data-analyzer
# Output: Q3 vs Q2 comparison
#         Performance: ↗ IMPROVING (+15% win rate)
#         Costs: → STABLE
#         Tax efficiency: ↗ IMPROVING
```

**Expected Time**: 10-15 minutes
**Sub-Agents Used**: data-analyzer (3x)

---

### Workflow 5: Tax-Loss Harvesting Strategy

**Scenario**: Year-end tax optimization

```bash
# Step 1: Generate current tax report
/tax-report --ytd

# Sub-agent: data-analyzer
# Output: YTD capital gains: $16,986
#         Short-term: $9,455 (taxed at 37%)
#         Long-term: $7,531 (taxed at 15%)
#         Potential harvesting: $1,890 in losses available

# Step 2: Identify specific opportunities
# From report:
#   Symbol DEF: -$1,234 unrealized loss
#   Symbol GHI: -$678 unrealized loss
#   Potential tax savings: $558

# Step 3: Check wash sale implications
# From report:
#   ⚠️ Symbol ABC recently sold (watch until 2025-10-16)
#   ✅ DEF and GHI safe to sell (no recent transactions)

# Step 4: Execute tax-loss harvesting
# [Manually execute trades through IB]
# Sell DEF (-$1,234 loss) → Offset short-term gains
# Sell GHI (-$678 loss) → Offset long-term gains

# Step 5: Fetch updated data
/fetch-latest

# Step 6: Verify tax impact
/tax-report --ytd

# Sub-agent: data-analyzer
# Output: Updated tax liability: $5,078 (was $5,789)
#         Savings achieved: $711 ✅
#         No wash sales detected ✅
```

**Expected Time**: 30-45 minutes (including trade execution)
**Sub-Agents Used**: data-analyzer (2x)

---

## 🧪 Testing & Quality Workflows

### Workflow 6: Pre-Commit Quality Gate

**Scenario**: Before committing code changes

```bash
# Step 1: Quick quality check
/quality-check

# Sub-agent: code-reviewer
# Checks: Formatting → Linting → Type checking → Tests
# Output: ⚠️ 3 issues found
#         - 2 linting errors (unused imports)
#         - 1 missing docstring

# Step 2: Auto-fix what's possible
/quality-check --fix

# Sub-agent: code-reviewer
# Actions:
#   ✅ Formatted 2 files with black
#   ✅ Fixed 2 linting issues automatically
#   ⚠️ Manual fix needed: Add docstring to calculate_profit()

# Step 3: Add missing docstring manually
# [Add docstring to function]

# Step 4: Final quality check
/quality-check

# Sub-agent: code-reviewer
# Output: ✅ All checks passed
#         - Formatting: ✅
#         - Linting: ✅
#         - Type checking: ✅
#         - Tests: ✅ (coverage: 84%)

# Step 5: Ready to commit!
git add .
git commit -m "feat: add profit calculation to performance analyzer"
```

**Expected Time**: 3-5 minutes
**Sub-Agents Used**: code-reviewer (3x)

---

### Workflow 7: Full Test Suite with Coverage Analysis

**Scenario**: Comprehensive testing before release

```bash
# Step 1: Run full test suite with coverage
/test --verbose

# Sub-agent: test-runner
# Output:
#   ✅ 67 tests passed in 4.2s
#   📊 Coverage: 81% (target: 80%)
#
#   Coverage by module:
#   - analyzers/: 89% ✅
#   - core/parsers.py: 72% ⚠️ (below target)
#   - api/client.py: 85% ✅
#   - models/: 94% ✅

# Step 2: Add tests for low-coverage module
/add-test csv_parser --parser

# Sub-agent: test-runner
# Creates: tests/test_parsers/test_csv_parser.py
# With test cases for:
#   - Valid CSV parsing
#   - Invalid format handling
#   - Edge cases (empty sections, missing fields)

# Step 3: Implement missing tests
# [Write test implementations in generated file]

# Step 4: Run tests again
/test csv_parser

# Sub-agent: test-runner
# Output: ✅ 8 new tests pass
#         Coverage for parsers.py: 72% → 87% ✅

# Step 5: Final coverage check
/test --coverage

# Sub-agent: test-runner
# Output: Overall coverage: 84% ✅ (exceeded 80% target)
#         All modules above target ✅
```

**Expected Time**: 20-30 minutes
**Sub-Agents Used**: test-runner (4x)

---

## 🔧 Troubleshooting Workflows

### Workflow 8: MCP Server Issues

**Scenario**: MCP tools not responding

```bash
# Step 1: Check MCP server status
/mcp-status

# Output: ❌ MCP SERVER ERROR
#         Status: NOT RUNNING
#         Error: Connection refused

# Step 2: Check detailed diagnostics
/mcp-status --verbose

# Output: Troubleshooting steps:
#   1. Check Claude Desktop config
#   2. Verify Python path
#   3. Restart Claude Desktop
#   4. Check server logs

# Step 3: Verify configuration
# [Check ~/Library/Application Support/Claude/claude_desktop_config.json]
# Found issue: Incorrect Python path

# Step 4: Fix configuration
# [Update config with correct venv Python path]

# Step 5: Restart Claude Desktop
# [Quit and reopen Claude Desktop]

# Step 6: Verify fix
/mcp-status --test

# Output: ✅ MCP SERVER HEALTHY
#         Tools: 7/7 available
#         Test: API fetch successful (234ms)
#         Status: Ready for use ✅
```

**Expected Time**: 5-10 minutes
**Sub-Agents Used**: None (direct command)

---

## 📈 Advanced Workflows

### Workflow 9: Multi-Period Performance Attribution

**Scenario**: Understand performance trends over time

```bash
# Step 1: Compare Q1 vs Q2
/compare-periods 2025-01-01 2025-03-31 2025-04-01 2025-06-30

# Sub-agent: data-analyzer
# Output: Q1 → Q2
#         Win rate: 62.5% → 68.3% (↗ IMPROVING)
#         Profit factor: 1.45 → 1.68 (↗ IMPROVING)
#         Key change: Better risk management (smaller losses)

# Step 2: Compare Q2 vs Q3
/compare-periods 2025-04-01 2025-06-30 2025-07-01 2025-09-30

# Sub-agent: data-analyzer
# Output: Q2 → Q3
#         Win rate: 68.3% → 65.1% (↘ DEGRADING)
#         Profit factor: 1.68 → 1.52 (↘ DEGRADING)
#         Key change: Market volatility impact

# Step 3: Year-to-date comparison with previous year
/compare-periods --ytd

# Sub-agent: data-analyzer
# Output: 2024 YTD → 2025 YTD
#         Total P&L: $18,234 → $22,567 (↗ +24%)
#         ROI: 7.2% → 9.1% (↗ +26%)
#         Overall: Strong improvement year-over-year

# Step 4: Identify trends and patterns
# Analysis:
#   - Q1-Q2: Strategy refinement working
#   - Q2-Q3: Market volatility affecting results
#   - YTD: Overall strong performance despite Q3 headwinds
#
# Recommendations:
#   - Continue Q1-Q2 strategy during stable markets
#   - Develop volatility hedging for Q3-like conditions
#   - Maintain long-term focus (YTD trending positive)
```

**Expected Time**: 15-20 minutes
**Sub-Agents Used**: data-analyzer (3x)

---

### Workflow 10: Complete Release Preparation

**Scenario**: Preparing for production release

```bash
# Step 1: Quality gate
/quality-check --strict

# Sub-agent: code-reviewer
# Output: ✅ All quality checks passed (strict mode)

# Step 2: Full test suite
/test

# Sub-agent: test-runner
# Output: ✅ All tests pass, coverage: 84%

# Step 3: Performance benchmarks
/benchmark --full

# Sub-agent: performance-optimizer
# Output: ✅ All components within performance targets
#         No regressions detected

# Step 4: Data validation
/validate-data --latest

# Output: ✅ Data integrity verified
#         All business logic checks pass

# Step 5: MCP server health
/mcp-status --test

# Output: ✅ MCP server healthy
#         All tools functioning correctly

# Step 6: Generate release documentation
# [Create CHANGELOG.md entry]
# [Update version in pyproject.toml]

# Step 7: Final verification
git status
git diff

# Step 8: Create release
git add .
git commit -m "release: version 0.2.0"
git tag v0.2.0
git push origin main --tags
```

**Expected Time**: 15-20 minutes
**Sub-Agents Used**: code-reviewer (1x), test-runner (1x), performance-optimizer (1x)

---

## 💡 Pro Tips

### Combining Commands
```bash
# Chain multiple analyses
/validate-data --latest && /optimize-portfolio && /tax-report --save

# Quick quality + test
/quality-check --fix && /test
```

### Using Sub-Agents Directly
```
"Use the data-analyzer subagent to compare my bond holdings across all accounts"
"Ask the api-debugger subagent to test my production credentials"
"Have the performance-optimizer profile the entire analysis pipeline"
```

### Saving Reports
```bash
# Tax report
/tax-report --save
# → Saves to: data/processed/tax_report_2025.txt

# Benchmark results
/benchmark --full > benchmarks/baseline_2025-10-11.txt

# Test coverage
/test --coverage > reports/coverage_$(date +%Y%m%d).txt
```

---

## 🐙 GitHub Integration Workflows (NEW!)

### Workflow 11: Complete GitHub Issue Resolution with TDD

**Scenario**: Implementing feature from GitHub issue #42 "Add Sharpe Ratio to PerformanceAnalyzer"

**Command**: `/resolve-gh-issue 42`

```bash
# Single command orchestrates entire workflow
/resolve-gh-issue 42

# ===== Phase 1: Issue Analysis (2-3 min) =====
[1/10] Analyzing Issue #42...
→ Delegating to issue-analyzer subagent
→ Executing: gh issue view 42 --json number,title,body,labels,state

✓ Requirements extracted
✓ Acceptance criteria: 4 items
  - [ ] Calculate Sharpe ratio using returns and risk-free rate
  - [ ] Add to AnalysisResult metrics
  - [ ] Include in ConsoleReport output
  - [ ] Handle edge cases (zero variance, negative returns)
✓ Affected files: 2 files
  - ib_sec_mcp/analyzers/performance.py (modify)
  - ib_sec_mcp/reports/console.py (modify)
✓ Financial code: YES (Decimal precision required)

# ===== Phase 2: Planning & Task Breakdown (1 min) =====
[2/10] Creating task breakdown...
→ Using TodoWrite to track progress

✓ 6 tasks created in TodoList:
  1. Create test file with 8 test cases
  2. Implement calculate_sharpe_ratio() method
  3. Add sharpe_ratio to AnalysisResult
  4. Update ConsoleReport._render_performance()
  5. Run quality checks (black, ruff, mypy)
  6. Verify with sample data

# ===== Phase 3: Branch Creation (30 sec) =====
[3/10] Creating feature branch...
→ git checkout main
→ git pull origin main
→ git checkout -b feature/issue-42-add-sharpe-ratio

✓ Branch created: feature/issue-42-add-sharpe-ratio
✓ On main branch, up to date

# ===== Phase 4: Test Creation (TDD - 10 min) =====
[4/10] Creating tests (TDD)...
→ Delegating to test-runner subagent
→ Creating: tests/test_analyzers/test_performance_sharpe.py

✓ Test file created with 8 tests:
  1. test_sharpe_ratio_basic() - Core functionality
  2. test_sharpe_ratio_in_analysis_result() - Integration check
  3. test_sharpe_ratio_zero_variance() - Edge case
  4. test_sharpe_ratio_negative_returns() - Edge case
  5. test_sharpe_ratio_insufficient_data() - Error handling
  6. test_sharpe_ratio_decimal_precision() - Financial code
  7. test_sharpe_ratio_various_risk_free_rates() - Parametrized
  8. test_sharpe_ratio_console_output() - Report integration

→ Running tests to verify they fail (TDD red phase)
pytest tests/test_analyzers/test_performance_sharpe.py -v

❌ 8 tests failed (expected - no implementation yet)
✓ Tests properly written and ready for implementation

# ===== Phase 5: Implementation (20-30 min) =====
[5/10] Implementing solution...
→ Delegating to code-implementer subagent
→ Following existing codebase patterns

✓ Method implemented: calculate_sharpe_ratio()
  - Uses Decimal throughout
  - Handles edge cases (zero variance, empty data)
  - Comprehensive docstring with formula
  - Type hints complete

✓ Integration complete:
  - Added to AnalysisResult.metrics
  - Updated ConsoleReport rendering
  - Follows existing naming conventions

→ Running tests again
pytest tests/test_analyzers/test_performance_sharpe.py -v

✅ 8/8 tests passing
✓ TDD green phase achieved

# ===== Phase 6: Quality Assurance (5 min) =====
[6/10] Running quality checks...
→ Delegating to code-reviewer subagent

→ black ib_sec_mcp tests
✅ All files formatted (2 files reformatted)

→ ruff check ib_sec_mcp tests
✅ No issues found

→ mypy ib_sec_mcp
✅ No type errors (strict mode)

→ pytest --cov=ib_sec_mcp.analyzers.performance
✅ Coverage: 95% for new code (target: 80%)
✅ All 75 tests passing

# ===== Phase 7: Documentation (3 min) =====
[7/10] Updating documentation...

✓ Docstrings complete (Google style)
✓ CHANGELOG.md updated:
  ## [Unreleased]
  ### Added
  - Sharpe ratio calculation in PerformanceAnalyzer (#42)

# ===== Phase 8: Commit & Push (1 min) =====
[8/10] Committing and pushing...

→ git add .
→ git commit -m "feat: add Sharpe ratio calculation to PerformanceAnalyzer (#42)

Implements risk-adjusted return calculation using Sharpe ratio formula.
Includes comprehensive tests and proper Decimal precision handling.

Resolves #42"

→ git push origin feature/issue-42-add-sharpe-ratio

✓ Commit created: abc123d
✓ Pushed to remote

# ===== Phase 9: Pull Request Creation (2 min) =====
[9/10] Creating pull request...

→ gh pr create --title "feat: Add Sharpe ratio calculation (#42)" \
  --body "$(cat <<'EOF'
## Summary
Implements Sharpe ratio calculation for risk-adjusted portfolio returns.

## Changes
- Added `calculate_sharpe_ratio()` method to PerformanceAnalyzer
- Comprehensive test suite (8 tests) with edge cases
- Updated ConsoleReport to display Sharpe ratio
- All quality checks passing

## Testing
- ✅ Unit tests: 8 new tests, all passing
- ✅ Coverage: 95% for new code
- ✅ Manual testing: Verified with sample portfolio data
- ✅ Type checking: mypy strict mode passing

## Related
Resolves #42

## Checklist
- [x] Tests added and passing
- [x] Decimal precision verified
- [x] Docstrings complete
- [x] Quality checks passing (black, ruff, mypy)
- [x] No breaking changes
EOF
)"

✓ PR #123 created
✓ URL: https://github.com/user/repo/pull/123

# ===== Phase 10: CI Monitoring (2-5 min) =====
[10/10] Monitoring CI...

→ gh pr checks --watch

→ Formatting (black): ✓ Passed
→ Linting (ruff): ✓ Passed
→ Type checking (mypy): ✓ Passed
→ Tests (pytest): ✓ Passed (75/75)
→ Coverage (pytest-cov): ✓ Passed (84%)

✅ All CI checks passing
✓ Ready for review

# ===== Workflow Complete =====
🎉 Issue #42 resolved successfully!

Summary:
- ✅ PR #123 created and ready for review
- ✅ All acceptance criteria met
- ✅ All quality gates passed
- ✅ CI checks green
- ⏰ Total time: 45-60 minutes

Next steps:
1. Review PR: gh pr view 123
2. Request reviews: gh pr review 123 --request @reviewer
3. Merge when approved: gh pr merge 123 --squash
4. Issue #42 will auto-close on merge
```

**Expected Time**: 45-60 minutes end-to-end
**Sub-Agents Used**: issue-analyzer (1x), test-runner (2x), code-implementer (1x), code-reviewer (1x)

**Key Benefits**:
- ✅ **Automated Workflow**: Single command from issue to PR
- ✅ **TDD Approach**: Tests written before implementation
- ✅ **Quality Guaranteed**: All gates enforced automatically
- ✅ **Financial Safety**: Decimal precision validated
- ✅ **Comprehensive**: Full GitHub integration (issue → PR → CI)
- ✅ **Traceable**: TodoWrite tracks all steps
- ✅ **Repeatable**: Consistent process for all issues

**When to Use**:
- GitHub issues with clear acceptance criteria
- Features requiring TDD approach
- Changes needing financial code validation
- Team collaboration via pull requests
- CI/CD integration requirements

**Advanced Options**:
```bash
# Dry run to see plan without executing
/resolve-gh-issue 42 --dry-run

# Skip quality checks (not recommended)
/resolve-gh-issue 42 --skip-checks

# Create tests but don't run them
/resolve-gh-issue 42 --skip-tests
```

---

## 📊 Workflow Summary

| Workflow | Time | Sub-Agents | Best For |
|----------|------|------------|----------|
| Feature Development (TDD) | 15-20 min | test-runner, code-reviewer | New features |
| Bug Fix with RCA | 5-10 min | api-debugger | API issues |
| Performance Optimization | 20-30 min | performance-optimizer, test-runner | Speed improvements |
| Portfolio Review | 10-15 min | data-analyzer | Monthly analysis |
| Tax-Loss Harvesting | 30-45 min | data-analyzer | Tax optimization |
| Pre-Commit Quality | 3-5 min | code-reviewer | Before commits |
| Full Test Suite | 20-30 min | test-runner | Before releases |
| MCP Troubleshooting | 5-10 min | None | Server issues |
| Multi-Period Analysis | 15-20 min | data-analyzer | Trend analysis |
| Release Preparation | 15-20 min | All | Production releases |
| **GitHub Issue Resolution** (NEW!) | **45-60 min** | **issue-analyzer, test-runner, code-implementer, code-reviewer** | **Complete issue-to-PR workflow** |

---

**Last Updated**: 2025-10-11
**Maintained By**: Development Team
