---
description: Run comprehensive code quality checks (format, lint, type, test)
allowed-tools: Bash(black:*), Bash(ruff:*), Bash(mypy:*), Bash(pytest:*), Read
argument-hint: [--fix|--strict]
---

Execute a full quality gate check including formatting, linting, type checking, and tests.

## Task

Run all quality checks in sequence. Delegate to **code-reviewer** subagent for code quality analysis.

### Quality Gate Steps

**1. Code Formatting (Black)**
```bash
black --check ib_sec_mcp tests
```
- If $ARGUMENTS contains `--fix`: Run `black ib_sec_mcp tests` to auto-format

**2. Linting (Ruff)**
```bash
ruff check ib_sec_mcp tests
```
- If $ARGUMENTS contains `--fix`: Run `ruff check --fix ib_sec_mcp tests`

**3. Type Checking (Mypy)**
```bash
mypy ib_sec_mcp
```
- If $ARGUMENTS contains `--strict`: Ensure strict mode is enabled

**4. Tests (Pytest)**
```bash
pytest --cov=ib_sec_mcp --cov-report=term -q
```

### Expected Output

```
=== Quality Gate Results ===

✅ Formatting (Black)
  All files properly formatted

✅ Linting (Ruff)
  No issues found

✅ Type Checking (Mypy)
  No type errors

✅ Tests (Pytest)
  45 passed in 3.2s
  Coverage: 82%

=== Quality Gate: PASSED ===
```

### On Failure

If any check fails:
1. Report which step failed
2. Show detailed error messages
3. Suggest fixes (use --fix flag)
4. Block commit until resolved

### Examples

```
/quality-check
/quality-check --fix
/quality-check --strict
```

**Important**: This command should be run before every commit to ensure code quality.
