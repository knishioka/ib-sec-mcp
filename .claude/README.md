# .claude/ Directory

This directory contains Claude Code configuration and custom commands for the IB Analytics project.

## Files Overview

### CLAUDE.md
**Main project context file** that Claude Code automatically reads when working in this repository.

Contains:
- Project overview and mission
- Tech stack and dependencies
- Project structure explanation
- Key commands and workflows
- Code style and conventions
- Repository etiquette
- Common pitfalls and best practices

**When to update**:
- New features or major changes
- Updated dependencies
- New coding conventions
- Common issues discovered
- New team members joining

**How to update**:
- Edit manually, or
- Use `#` key in Claude Code to add instructions interactively
- Commit changes to git for team sharing

### commands/ Directory
Custom slash commands for repeated workflows.

**Available Commands**:
- `/analyze-all`: Run comprehensive analysis on latest data
- `/fetch-latest`: Fetch most recent data from IB API
- `/add-analyzer`: Scaffold a new analyzer module
- `/explain-architecture`: Get detailed architecture explanation
- `/debug-api`: Troubleshoot API connectivity issues

**How to use**:
1. Type `/` in Claude Code
2. Select command from menu
3. Add arguments if needed (e.g., `/analyze-all --tax-rate 0.25`)

**How to add new command**:
1. Create `[command-name].md` in this directory
2. Write natural language instructions
3. Use `$ARGUMENTS` placeholder for parameters
4. Commit to git for team sharing

## Usage Examples

### Interactive Context Building
While coding, press `#` to give Claude an instruction:

```
# Always use Decimal for financial calculations, never float
# Run black and ruff before committing
# New analyzers must inherit from BaseAnalyzer
```

Claude will automatically add these to CLAUDE.md.

### Using Custom Commands

```bash
# Run comprehensive analysis
/analyze-all

# Fetch latest data for all accounts
/fetch-latest --multi-account

# Add new analyzer
/add-analyzer Sharpe "Calculate Sharpe ratio"

# Debug API issues
/debug-api --verbose
```

### Architecture Queries

```
/explain-architecture
```

Get detailed explanation of:
- Layer architecture
- Data flow
- Design patterns used
- Extension points

## Best Practices

### Keep CLAUDE.md Focused
- ✅ Include project-specific information
- ✅ Document common commands
- ✅ List important conventions
- ❌ Don't duplicate README.md
- ❌ Don't include implementation details
- ❌ Don't add personal preferences (use ~/.claude/CLAUDE.md)

### Custom Commands
- ✅ Create commands for repeated workflows
- ✅ Use clear, descriptive names
- ✅ Document expected arguments
- ✅ Provide usage examples
- ❌ Don't create one-off commands
- ❌ Don't duplicate built-in functionality

### Version Control
- ✅ Commit CLAUDE.md to git
- ✅ Commit custom commands to git
- ✅ Review changes in PRs
- ❌ Don't include personal settings
- ❌ Don't commit sensitive information

## File Structure

```
.claude/
├── CLAUDE.md              # Main project context
├── README.md             # This file
├── settings.local.json   # Local settings (not committed)
└── commands/             # Custom slash commands
    ├── analyze-all.md
    ├── fetch-latest.md
    ├── add-analyzer.md
    ├── explain-architecture.md
    └── debug-api.md
```

## Tips & Tricks

### Quick Context Updates
Use `#` during development to organically build context:
- Document unexpected behaviors
- Record useful commands
- Note important decisions
- Capture team conventions

### Command Arguments
Use `$ARGUMENTS` in commands for flexibility:

```markdown
# my-command.md
Run analysis with tax rate: $ARGUMENTS

Default tax rate: 0.30
```

Usage: `/my-command 0.25`

### Hierarchical Context
You can create nested CLAUDE.md files:
- Project root: General context
- Subdirectories: Specific context
- Claude prioritizes most specific file

Example:
```
ib-sec/CLAUDE.md              # General project context
ib-sec/ib_sec_mcp/CLAUDE.md  # Library-specific context
```

### Memory Scoping
- **Project Memory**: `.claude/CLAUDE.md` (shared with team)
- **User Memory**: `~/.claude/CLAUDE.md` (personal preferences)
- **Session Memory**: Current chat context

Claude combines all three, with most specific taking precedence.

## Maintenance

### Regular Updates
- Review CLAUDE.md monthly
- Update after major refactors
- Add new commands as patterns emerge
- Remove outdated information

### Quality Checks
- Run through prompt improver occasionally
- Add emphasis for critical instructions ("IMPORTANT", "NEVER", "ALWAYS")
- Keep language concise and actionable
- Use bullet points over paragraphs

### Team Collaboration
- Review CLAUDE.md changes in PRs
- Discuss new commands in team meetings
- Share useful patterns discovered
- Document team decisions

## Resources

- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Claude Code Documentation](https://docs.claude.com/claude-code)
- [Prompt Engineering Guide](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering)

---

**Last Updated**: 2025-10-06
**Maintained By**: Development Team
