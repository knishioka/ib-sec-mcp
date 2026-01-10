---
paths: .claude/agents/**/*.md, .claude/commands/**/*.md
---

# Claude Extensions Development Rules

Quick reference for sub-agents and slash commands.

## Sub-Agent Frontmatter

```yaml
---
name: kebab-case-name
description: When to use. Add "Use PROACTIVELY" for auto-activation.
tools: Read, Write, Bash(pytest:*)  # Minimal set
model: sonnet  # sonnet | opus | haiku
---
```

## Slash Command Frontmatter

```yaml
---
description: One-line (shown in menu)
allowed-tools: Read, mcp__ib-sec-mcp__*
argument-hint: [symbol] [--flag]
---
```

## Model Selection

| Model | When to Use | Token Cost |
|-------|-------------|------------|
| `haiku` | Simple tasks, fast response | Low |
| `sonnet` | Balanced, default choice | Medium |
| `opus` | Complex analysis, implementation | High |

## Tool Patterns

```yaml
# Wildcard for MCP tools
tools: mcp__ib-sec-mcp__*

# Specific bash commands
tools: Bash(pytest:*), Bash(python:*)

# Read-only for analysis
tools: Read, Grep, Glob

# Full development
tools: Read, Write, Edit, Bash(python:*), Bash(pytest:*)
```

## Common Mistakes

- Missing `model:` field (defaults may not be optimal)
- Over-permissive tools (security risk)
- Missing "Use PROACTIVELY" for auto-activation
- No error handling section in commands
- Overly long descriptions (hard to scan)

## Sub-Agent Testing

- [ ] Explicit invocation works
- [ ] Auto-activation triggers correctly (if PROACTIVELY)
- [ ] Tools are sufficient but minimal
- [ ] Output format matches expectations

## Slash Command Testing

- [ ] Appears in command menu (`/` to see)
- [ ] Arguments parsed correctly (`$1`, `$2`, `$ARGUMENTS`)
- [ ] Default values work
- [ ] Error messages are helpful

See `.claude/SUB_AGENTS.md` and `.claude/SLASH_COMMANDS.md` for detailed guides.
