---
description: Run pytest test suite with coverage reporting
allowed-tools: Bash(pytest:*), Bash(python -m pytest:*), Read, Glob
argument-hint: [--coverage|--verbose|--failed|pattern]
---

Run the project test suite using pytest with comprehensive coverage reporting.

## Task

Delegate to the **test-runner** subagent to execute tests with the following options:

### Test Modes

**Full Test Suite** (default):
```bash
pytest --cov=ib_sec_mcp --cov-report=term-missing --cov-report=html
```

**With Verbose Output** (if $ARGUMENTS contains `--verbose` or `-v`):
```bash
pytest -v --cov=ib_sec_mcp --cov-report=term-missing
```

**Quick Coverage Check** (if $ARGUMENTS contains `--coverage`):
```bash
pytest --cov=ib_sec_mcp --cov-report=term
```

**Failed Tests Only** (if $ARGUMENTS contains `--failed` or `--lf`):
```bash
pytest --lf -v
```

**Specific Pattern** (if $ARGUMENTS contains test pattern):
```bash
pytest -k "$ARGUMENTS" -v
```

### What the Subagent Should Report

1. **Test Summary**: Pass/fail counts, duration
2. **Coverage Report**: Overall percentage and per-file breakdown
3. **Failed Tests**: Detailed error messages and stack traces
4. **Coverage Gaps**: Files below 80% target
5. **Suggestions**: Missing tests or improvements

### Output Location

- **HTML Report**: `htmlcov/index.html`
- **Terminal**: Color-coded summary with missing lines

### Examples

```
/test
/test --verbose
/test --coverage
/test --failed
/test test_bond
/test performance
```

Use the **test-runner** subagent to handle all test execution and reporting.
