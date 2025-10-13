#!/bin/bash
#
# Claude Code PreToolUse Hook - Quality Gates Enforcement
#
# This hook prevents Claude Code from bypassing quality checks using:
# - git commit --no-verify (bypasses pre-commit hooks)
# - git push --no-verify (bypasses pre-push hooks)
# - Lint skip options like SKIP=... or --skip
#
# Exit codes:
# - 0: Allow the command
# - 2: Block the command (PreToolUse only, message to stderr for Claude)
# - Other non-zero: Non-blocking error shown to user

set -euo pipefail

# Parse the command from CLAUDE_TOOL_INPUT JSON
COMMAND=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.command // empty')

# If no command found, allow (not a Bash tool)
if [ -z "$COMMAND" ]; then
  exit 0
fi

# Check for dangerous git flags
if echo "$COMMAND" | grep -qE 'git (commit|push).*--no-verify'; then
  echo "❌ ERROR: --no-verify flag detected!" >&2
  echo "" >&2
  echo "This bypasses pre-commit hooks and quality checks." >&2
  echo "" >&2
  echo "❌ BLOCKED: Please fix the issues reported by pre-commit hooks instead." >&2
  echo "" >&2
  echo "If you believe this is a false positive:" >&2
  echo "1. Fix the actual issue (e.g., add dummy IDs to gitleaks allowlist)" >&2
  echo "2. Update .gitleaks.toml or other tool configurations" >&2
  echo "3. Never use --no-verify to bypass quality gates" >&2
  echo "" >&2
  echo "💡 TIP: Run 'pre-commit run --all-files' to see all issues" >&2
  exit 2
fi

# Check for pre-commit SKIP environment variable
if echo "$COMMAND" | grep -qE 'SKIP=.*git commit'; then
  echo "❌ ERROR: SKIP environment variable detected in git commit!" >&2
  echo "" >&2
  echo "This bypasses pre-commit hooks selectively." >&2
  echo "" >&2
  echo "❌ BLOCKED: Please fix the issues instead of skipping checks." >&2
  echo "" >&2
  echo "💡 TIP: Fix the specific tool issue rather than skipping it" >&2
  exit 2
fi

# Check for ruff/black/mypy skip flags
if echo "$COMMAND" | grep -qE '(ruff|black|mypy|pylint|flake8).*(--skip|-n|--no-check)'; then
  echo "⚠️  WARNING: Lint skip flag detected: $COMMAND" >&2
  echo "" >&2
  echo "Skipping linters may introduce code quality issues." >&2
  echo "" >&2
  echo "❌ BLOCKED: Please fix the linting issues instead." >&2
  echo "" >&2
  echo "💡 TIP: Run the linter without skip flags to see issues" >&2
  exit 2
fi

# Check for pytest skip flags (allow -k for test selection, block --skip)
if echo "$COMMAND" | grep -qE 'pytest.*--skip'; then
  echo "⚠️  WARNING: Test skip flag detected: $COMMAND" >&2
  echo "" >&2
  echo "Skipping tests may hide failures." >&2
  echo "" >&2
  echo "❌ BLOCKED: Please fix the failing tests instead." >&2
  echo "" >&2
  echo "💡 TIP: Run pytest without --skip to see failures" >&2
  exit 2
fi

# Allow the command
exit 0
