---
description: Automate GitHub Issue resolution with TDD, quality checks, and PR creation workflow
allowed-tools: Bash(gh:*), Task, TodoWrite, Bash(git:*), Bash(pytest:*), Bash(black:*), Bash(ruff:*), Bash(mypy:*), Edit, MultiEdit, Write, Read, Grep, Glob
argument-hint: <issue-number> [--skip-checks] [--skip-tests] [--dry-run]
---

Resolve GitHub Issue with automated, high-quality development workflow for IB Analytics project.

## Command Usage

```bash
/resolve-gh-issue <issue-number> [flags]

Flags:
  --skip-checks     Skip quality checks (black, ruff, mypy)
  --skip-tests      Skip test execution (only create tests)
  --dry-run         Show plan without executing
```

## Workflow Overview

```
Issue #123 → Analyze → Plan → Branch → Tests → Implement → Review → PR → Monitor
     ↓           ↓        ↓       ↓       ↓         ↓         ↓      ↓      ↓
  gh issue   Sub-Agent  Todo   git    TDD    Sub-Agent  Quality  gh pr  CI
   view      issue-     Write checkout        code-     checks  create check
            analyzer              implementer  reviewer
```

## IMPORTANT: Progress Tracking

**MANDATORY**: Use `TodoWrite` tool to track all major steps:

```yaml
todos:
  - content: "Analyze issue requirements"
    status: "in_progress"
  - content: "Create feature branch"
    status: "pending"
  - content: "Write tests (TDD)"
    status: "pending"
  - content: "Implement solution"
    status: "pending"
  - content: "Run quality checks"
    status: "pending"
  - content: "Create pull request"
    status: "pending"
  - content: "Monitor CI status"
    status: "pending"
```

Update status as you progress: `pending` → `in_progress` → `completed`

## Step-by-Step Workflow

### Phase 1: Issue Analysis (5 min)

**Delegate to issue-analyzer sub-agent**:

```
Use the issue-analyzer subagent to analyze GitHub Issue #$ARGUMENTS
```

**Expected Output**:
- Structured requirements
- Acceptance criteria
- Affected files list
- Financial code flags (if applicable)
- Implementation checklist

**Validation**:
- ✅ Issue exists and is open
- ✅ Requirements are clear
- ✅ Acceptance criteria extracted
- ✅ Technical scope identified

**If unclear**, ask user for clarification before proceeding.

---

### Phase 2: Planning & Task Breakdown (3 min)

Create comprehensive TodoList from analysis:

```yaml
Example for Issue #42 "Add Sharpe Ratio":
- content: "Create test file: tests/test_analyzers/test_performance_sharpe.py"
  status: "pending"
- content: "Implement calculate_sharpe_ratio() in performance.py"
  status: "pending"
- content: "Add sharpe_ratio to AnalysisResult metrics"
  status: "pending"
- content: "Update ConsoleReport._render_performance()"
  status: "pending"
- content: "Run quality checks (black, ruff, mypy)"
  status: "pending"
- content: "Verify with sample data"
  status: "pending"
```

**Branch Naming**:
- Feature: `feature/issue-<number>-brief-description`
- Bug: `fix/issue-<number>-brief-description`
- Refactor: `refactor/issue-<number>-brief-description`

Example: `feature/issue-42-add-sharpe-ratio`

---

### Phase 3: Branch Creation (1 min)

```bash
# Ensure on main branch
git checkout main
git pull origin main

# Create and checkout feature branch
git checkout -b feature/issue-$ISSUE_NUMBER-<description>

# Verify branch
git branch --show-current
```

**Validation**:
- ✅ On correct feature branch
- ✅ Main branch is up to date
- ✅ No uncommitted changes from main

---

### Phase 4: Test Creation (TDD) (10-15 min)

**Delegate to test-runner sub-agent** for test file creation:

```
Use the test-runner subagent to create test file for <module> based on issue requirements
```

**Test File Structure**:

```python
# tests/test_<module>/test_<feature>.py

import pytest
from decimal import Decimal
from ib_sec_mcp.<module> import <Class>

@pytest.fixture
def sample_data():
    """Create test data based on acceptance criteria"""
    # ... fixture implementation
    return data

class Test<Feature>:
    """Test suite for Issue #<number>: <title>"""

    def test_basic_functionality(self, sample_data):
        """Test core functionality (acceptance criterion 1)"""
        # Arrange
        # Act
        # Assert
        pass

    def test_edge_case_zero(self):
        """Test edge case: zero value"""
        pass

    def test_edge_case_negative(self):
        """Test edge case: negative value"""
        pass

    def test_invalid_input(self):
        """Test error handling: invalid input"""
        with pytest.raises(ValueError):
            # Test exception raising
            pass

    @pytest.mark.parametrize("input,expected", [
        (value1, expected1),
        (value2, expected2),
    ])
    def test_various_scenarios(self, input, expected):
        """Test multiple scenarios from acceptance criteria"""
        pass
```

**Financial Code Tests** (if flagged):
```python
def test_decimal_precision():
    """Ensure Decimal precision maintained"""
    result = calculate_financial_metric(Decimal("100.123456789"))
    assert isinstance(result, Decimal)
    # Verify no float conversion occurred

def test_large_values():
    """Test with realistic large portfolio values"""
    result = calculate_metric(Decimal("10000000.00"))  # $10M
    assert result > Decimal("0")
```

**Run Tests (Should Fail)**:
```bash
pytest tests/test_<module>/test_<feature>.py -v

# Expected: All tests fail (no implementation yet)
# This confirms tests are properly written
```

---

### Phase 5: Implementation (20-40 min)

**Delegate to code-implementer sub-agent**:

```
Use the code-implementer subagent to implement solution for Issue #$ISSUE_NUMBER
following TDD approach with tests already created
```

**Implementation Checklist** (from sub-agent):
- [ ] Follow existing code patterns
- [ ] Use Decimal for all financial calculations
- [ ] Add comprehensive type hints
- [ ] Write Google-style docstrings
- [ ] Handle edge cases explicitly
- [ ] Validate all inputs
- [ ] Use Pydantic v2 for models (if creating new models)

**Incremental Development**:
1. Implement minimum to pass first test
2. Run test: `pytest tests/test_<module>/test_<feature>.py::test_first -v`
3. Implement to pass second test
4. Repeat until all tests pass

**Integration Points**:

If adding to existing file:
```bash
# Read existing file first
cat ib_sec_mcp/<module>/<file>.py

# Use Edit tool for modifications
# (code-implementer handles this)
```

If creating new file:
```bash
# Use Write tool
# Follow existing module structure
```

**Verify Tests Pass**:
```bash
pytest tests/test_<module>/test_<feature>.py -v

# Expected: All tests pass ✓
```

---

### Phase 6: Quality Assurance (5-10 min)

**Run Comprehensive Quality Checks**:

Unless `--skip-checks` flag is used, run:

```bash
/quality-check --fix
```

This executes (via code-reviewer sub-agent):
1. **Black** (formatting): `black ib_sec_mcp tests`
2. **Ruff** (linting): `ruff check --fix ib_sec_mcp tests`
3. **Mypy** (type checking): `mypy ib_sec_mcp`
4. **Pytest** (full suite): `pytest --cov=ib_sec_mcp --cov-report=term -q`

**Quality Gate Requirements**:
- ✅ All files properly formatted
- ✅ No linting errors
- ✅ No type errors
- ✅ All tests pass
- ✅ Coverage ≥80% for new code

**If Quality Check Fails**:
- Fix issues reported
- Re-run quality checks
- Do NOT proceed until all checks pass

---

### Phase 7: Documentation Updates (5 min)

**Update if needed**:

1. **Docstrings** (already done in implementation)

2. **CHANGELOG.md** (for user-facing changes):
```markdown
## [Unreleased]

### Added
- Sharpe ratio calculation in PerformanceAnalyzer (#42)

### Changed
- Enhanced performance metrics display (#42)
```

3. **README.md** (for new features/commands):
Only if public API changed or new CLI command added

4. **MCP Server** (if tools/resources added):
Update `ib_sec_mcp/mcp/` files if relevant

---

### Phase 8: Commit & Push (3 min)

**Commit Message Format**:
```
<type>: <short description> (#<issue>)

<detailed explanation if needed>

Resolves #<issue>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `docs`: Documentation only
- `test`: Test addition/modification
- `perf`: Performance improvement

**Example**:
```bash
git add .

git commit -m "feat: add Sharpe ratio calculation to PerformanceAnalyzer (#42)

Implements risk-adjusted return calculation using Sharpe ratio formula.
Includes comprehensive tests and proper Decimal precision handling.

Resolves #42"

git push origin feature/issue-42-add-sharpe-ratio
```

---

### Phase 9: Pull Request Creation (5 min)

**Create PR with gh CLI**:

```bash
gh pr create \
  --title "feat: Add Sharpe ratio calculation (#42)" \
  --body "$(cat <<'EOF'
## Summary

Implements Sharpe ratio calculation for risk-adjusted portfolio returns.

## Changes

- Added `calculate_sharpe_ratio()` method to PerformanceAnalyzer
- Comprehensive test suite with edge cases
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
```

**PR Template Content**:
- Summary of changes
- List of modified files
- Test coverage details
- Quality check results
- Issue reference (Resolves #X)
- Checklist confirmation

---

### Phase 10: CI Monitoring (2-5 min)

**Check CI Status**:

```bash
# View PR checks
gh pr checks

# Watch for completion
gh pr checks --watch
```

**Expected Checks**:
- Formatting (black)
- Linting (ruff)
- Type checking (mypy)
- Tests (pytest)
- Coverage report

**If CI Fails**:
1. Review failure logs: `gh pr checks`
2. Fix issues locally
3. Commit fix: `git commit -am "fix: resolve CI failure"`
4. Push: `git push`
5. Re-check: `gh pr checks --watch`

**If All Pass**:
```
✓ All CI checks passing
→ Ready for review
```

---

## Special Considerations for IB Analytics

### Financial Code Issues

If issue involves financial calculations:

**Mandatory Validations**:
- [ ] All calculations use `Decimal` (no float)
- [ ] Input validation (None, zero, negative checks)
- [ ] Output sanity checks (reasonable bounds)
- [ ] Precision maintained throughout calculation chain
- [ ] Edge cases handled (division by zero, etc.)

**Test Requirements**:
- [ ] Test with realistic financial values
- [ ] Test precision preservation
- [ ] Test edge cases (zero, negative, large numbers)
- [ ] Parametrized tests with various scenarios

### Tax Calculation Issues

Special attention:
- [ ] Short-term vs long-term capital gains logic
- [ ] Phantom income (OID) calculations
- [ ] Wash sale rule compliance
- [ ] Tax rate accuracy

### Bond Analytics Issues

Verify:
- [ ] YTM calculation correctness
- [ ] Duration calculation
- [ ] Maturity date handling (can be missing)
- [ ] Face value vs current price logic

### API Integration Issues

Check:
- [ ] FlexQueryClient usage patterns
- [ ] Async/await correctness
- [ ] Error handling (rate limits, timeouts)
- [ ] Response parsing

### MCP Server Issues

If modifying MCP components:
- [ ] Tool signature correctness
- [ ] Resource URI format
- [ ] Prompt template validity
- [ ] Logging to stderr (not stdout)

---

## Flags and Options

### `--skip-checks`

Skip quality checks (use sparingly):
```bash
/resolve-gh-issue 42 --skip-checks

# Skips: black, ruff, mypy, pytest
# Use when: Quick prototype or WIP
# Warning: PR may fail CI checks
```

### `--skip-tests`

Create test file but don't run:
```bash
/resolve-gh-issue 42 --skip-tests

# Creates test file but doesn't execute
# Use when: Want to review tests before running
```

### `--dry-run`

Show execution plan without making changes:
```bash
/resolve-gh-issue 42 --dry-run

# Output: Detailed plan of what would be executed
# Use when: Want to preview workflow
```

---

## Error Handling

### Issue Not Found
```
Error: Issue #123 not found

Action:
1. Verify issue number: gh issue list
2. Check repository: gh repo view
3. Confirm permissions: gh auth status
```

### Quality Checks Fail
```
Error: Quality checks failed (ruff: 3 errors)

Action:
1. Review errors: ruff check ib_sec_mcp
2. Auto-fix: ruff check --fix ib_sec_mcp
3. Manual fix remaining errors
4. Re-run: /quality-check
```

### Tests Fail
```
Error: 2 tests failing

Action:
1. Review failures: pytest -v
2. Debug specific test: pytest tests/path/to/test.py::test_name -v
3. Fix implementation or test
4. Re-run: pytest
```

### Merge Conflicts
```
Error: Merge conflict with main

Action:
1. Pull latest main: git checkout main && git pull
2. Rebase feature branch: git checkout feature-branch && git rebase main
3. Resolve conflicts in editor
4. Continue: git rebase --continue
5. Force push: git push --force-with-lease
```

### CI Failure
```
Error: CI check failed (mypy)

Action:
1. View logs: gh pr checks
2. Fix locally: mypy ib_sec_mcp
3. Commit fix: git commit -am "fix: resolve type errors"
4. Push: git push
5. Verify: gh pr checks --watch
```

---

## Success Criteria

Issue is considered **resolved** when:

- ✅ All acceptance criteria met
- ✅ Tests created and passing
- ✅ Quality checks passing (black, ruff, mypy)
- ✅ Test coverage ≥80% for new code
- ✅ Documentation updated (if needed)
- ✅ PR created with clear description
- ✅ CI checks passing
- ✅ Code reviewed and approved (if required)
- ✅ Issue automatically closed when PR merges

---

## Example Execution

```bash
$ /resolve-gh-issue 42

[1/10] Analyzing Issue #42...
→ Delegating to issue-analyzer subagent
✓ Requirements extracted
✓ Acceptance criteria: 4 items
✓ Affected files: 2 files
✓ Financial code: YES (Decimal precision required)

[2/10] Creating task breakdown...
✓ 6 tasks created in TodoList

[3/10] Creating feature branch...
→ feature/issue-42-add-sharpe-ratio
✓ Branch created and checked out

[4/10] Creating tests (TDD)...
→ Delegating to test-runner subagent
✓ Test file created: tests/test_analyzers/test_performance_sharpe.py
✓ 8 tests created (all failing as expected)

[5/10] Implementing solution...
→ Delegating to code-implementer subagent
✓ Method implemented: calculate_sharpe_ratio()
✓ Integration complete: AnalysisResult updated
✓ All tests passing: 8/8 ✓

[6/10] Running quality checks...
→ black: ✓ All files formatted
→ ruff: ✓ No issues found
→ mypy: ✓ No type errors
→ pytest: ✓ 75/75 tests passing (coverage: 84%)

[7/10] Updating documentation...
✓ Docstrings complete
✓ CHANGELOG.md updated

[8/10] Committing and pushing...
✓ Commit created with message
✓ Pushed to origin/feature/issue-42-add-sharpe-ratio

[9/10] Creating pull request...
✓ PR #123 created
✓ URL: https://github.com/user/repo/pull/123

[10/10] Monitoring CI...
→ Formatting: ✓
→ Linting: ✓
→ Type checking: ✓
→ Tests: ✓
→ Coverage: ✓

🎉 Issue #42 resolved successfully!
✓ PR #123 ready for review
✓ All CI checks passing

Next steps:
1. Review PR: gh pr view 123
2. Request reviews: gh pr review 123 --request @reviewer
3. Merge when approved: gh pr merge 123 --squash
```

---

## Best Practices

1. **Always start with issue analysis** - Don't skip to implementation
2. **Write tests first (TDD)** - Clarifies requirements and prevents bugs
3. **Commit frequently** - Small, logical commits are easier to review
4. **Use descriptive messages** - Future you will thank present you
5. **Keep PRs focused** - One issue = one PR (don't mix multiple issues)
6. **Run quality checks** - Don't rely solely on CI
7. **Update TodoList** - Track progress for transparency
8. **Ask for clarification** - Better than implementing wrong thing

---

**Remember**: Quality > Speed. Take time to implement correctly the first time.
