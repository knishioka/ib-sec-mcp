# Claude Code Hooks - Quality Gates Enforcement

This directory contains hooks that enforce code quality and prevent bypassing pre-commit checks.

## Purpose

Prevents Claude Code from using dangerous flags that bypass quality checks:

- ❌ `git commit --no-verify` (bypasses pre-commit hooks)
- ❌ `git push --no-verify` (bypasses pre-push hooks)
- ❌ `SKIP=... git commit` (selectively skips pre-commit checks)
- ❌ Lint skip flags like `--skip`, `-n`, `--no-check`
- ❌ Test skip flags like `pytest --skip`

## Setup

### 1. Make the hook script executable

```bash
chmod +x .claude/hooks/pre-tool-use.sh
```

### 2. Verify hook configuration

The hook should already be configured in `.claude/settings.local.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/pre-tool-use.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### 3. Restart Claude Code

After making the script executable, restart Claude Code to ensure the new permissions and hook configuration are loaded.

## How It Works

### PreToolUse Hook

The `pre-tool-use.sh` script runs **before every Bash command** that Claude Code tries to execute. It:

1. Parses the command from `$CLAUDE_TOOL_INPUT` JSON
2. Checks for dangerous patterns using regex
3. Returns exit code:
   - `0`: Allow the command
   - `2`: **Block** the command and show error message to Claude
   - Other non-zero: Non-blocking error shown to user

### Blocked Patterns

```bash
# Git bypass flags
git commit --no-verify
git push --no-verify

# Pre-commit skip
SKIP=gitleaks git commit
SKIP=ruff,black git commit

# Linter skip flags
ruff check --skip
black --no-check
mypy -n

# Test skip flags
pytest --skip
```

### Error Messages

When a blocked command is detected, Claude Code receives a clear error message:

```
❌ ERROR: --no-verify flag detected!

This bypasses pre-commit hooks and quality checks.

❌ BLOCKED: Please fix the issues reported by pre-commit hooks instead.

If you believe this is a false positive:
1. Fix the actual issue (e.g., add dummy IDs to gitleaks allowlist)
2. Update .gitleaks.toml or other tool configurations
3. Never use --no-verify to bypass quality gates

💡 TIP: Run 'pre-commit run --all-files' to see all issues
```

## Testing

### Test the hook manually

```bash
# This should be blocked
export CLAUDE_TOOL_INPUT='{"command":"git commit -m \"test\" --no-verify"}'
./.claude/hooks/pre-tool-use.sh
# Expected: Exit code 2 with error message

# This should be allowed
export CLAUDE_TOOL_INPUT='{"command":"git commit -m \"test\""}'
./.claude/hooks/pre-tool-use.sh
# Expected: Exit code 0 (silent)
```

### Test with Claude Code

Try asking Claude Code to commit with `--no-verify`:

```
User: "Commit this change using --no-verify"
Claude: [Hook blocks the command and explains why]
```

## Customization

### Adding More Patterns

Edit `.claude/hooks/pre-tool-use.sh` and add new checks:

```bash
# Check for custom dangerous pattern
if echo "$COMMAND" | grep -qE 'your-pattern-here'; then
  echo "❌ ERROR: Your custom error message!" >&2
  exit 2
fi
```

### Adjusting Timeout

Edit `.claude/settings.local.json` to change the hook timeout:

```json
{
  "type": "command",
  "command": "./.claude/hooks/pre-tool-use.sh",
  "timeout": 30  // Increase if needed
}
```

## Troubleshooting

### Hook not running

1. Verify script is executable: `ls -la .claude/hooks/pre-tool-use.sh`
2. Check for `x` permission: `-rwxr-xr-x`
3. Restart Claude Code after making changes

### Hook blocking legitimate commands

1. Review the command that was blocked in the error message
2. If it's a false positive, update the regex pattern in `pre-tool-use.sh`
3. Consider using a more specific pattern to avoid false positives

### Debugging hook output

The hook writes to stderr, which Claude Code shows to the user. You can test manually:

```bash
export CLAUDE_TOOL_INPUT='{"command":"your-command-here"}'
./.claude/hooks/pre-tool-use.sh 2>&1
echo "Exit code: $?"
```

## Best Practices

### DO ✅

- Fix the root cause of quality check failures
- Update tool configurations (e.g., `.gitleaks.toml`) for false positives
- Use hooks to enforce team standards consistently

### DON'T ❌

- Bypass hooks by manually running commands outside Claude Code
- Disable the hook without team agreement
- Use `--no-verify` in any circumstance

## References

- [Claude Code Hooks Guide](https://docs.claude.com/en/docs/claude-code/hooks-guide)
- [PreToolUse Hook Documentation](https://docs.claude.com/en/docs/claude-code/hooks-guide#pretooluse)
- [Gitleaks Configuration](./../.gitleaks.toml)
- [Pre-commit Configuration](./../../.pre-commit-config.yaml)

## Maintenance

This hook should be reviewed periodically to ensure it:

1. Catches new bypass patterns as they emerge
2. Doesn't have false positives blocking legitimate commands
3. Provides helpful error messages that guide users to solutions
4. Aligns with team quality standards and workflows

**Last Updated**: 2025-10-14
**Maintainer**: Kenichiro Nishioka
