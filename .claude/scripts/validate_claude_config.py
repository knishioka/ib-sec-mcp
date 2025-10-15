#!/usr/bin/env python3
"""
Claude Code Configuration Validator

Validates sub-agents and slash commands for proper structure and configuration.
No external dependencies required - uses only Python standard library.

Usage:
    python validate_claude_config.py                    # Validate all files
    python validate_claude_config.py path/to/file.md    # Validate specific file
    python validate_claude_config.py --changed-only     # Git changed files only
    python validate_claude_config.py --fix             # Auto-fix common issues
"""

import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(Enum):
    """Validation message severity levels"""

    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    SUCCESS = "✅"


@dataclass
class ValidationMessage:
    """A validation finding"""

    severity: Severity
    file_path: Path
    line_number: int | None
    message: str
    suggestion: str | None = None


class FrontmatterParser:
    """Parse YAML frontmatter from Markdown files"""

    @staticmethod
    def extract(content: str) -> tuple[dict | None, int]:
        """Extract frontmatter and return (dict, end_line_number)"""
        lines = content.split("\n")

        if not lines or lines[0].strip() != "---":
            return None, 0

        # Find closing ---
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break

        if end_idx is None:
            return None, 0

        # Parse YAML manually (simple key: value format)
        frontmatter = {}
        for line in lines[1:end_idx]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip()

        return frontmatter, end_idx + 1


class ToolsValidator:
    """Validate tools configuration"""

    # Known valid tools
    VALID_TOOLS = {
        # Core tools
        "Task",
        "Read",
        "Write",
        "Edit",
        "MultiEdit",
        "Glob",
        "Grep",
        "Bash",
        "WebSearch",
        "WebFetch",
        "TodoWrite",
        "SlashCommand",
        # MCP tools pattern: mcp__ib-sec-mcp__*
    }

    # Bash command patterns
    BASH_PATTERN = re.compile(r"Bash\([^)]+\)")

    # MCP tool pattern
    MCP_PATTERN = re.compile(r"mcp__ib-sec-mcp__\w+")

    @classmethod
    def validate(cls, tools_str: str, file_type: str) -> list[ValidationMessage]:
        """Validate tools list"""
        messages = []

        if not tools_str:
            return [
                ValidationMessage(
                    Severity.ERROR,
                    Path(),
                    None,
                    f"Empty tools list - {file_type} must specify allowed tools",
                )
            ]

        # Parse tools (comma separated, handle Bash() patterns specially)
        # Split by comma first to preserve Bash(command:*) patterns
        tools = []
        for part in tools_str.split(","):
            part = part.strip()
            if part:
                tools.append(part)

        for tool in tools:
            # Check if valid tool
            if tool in cls.VALID_TOOLS:
                continue

            # Check Bash pattern
            if cls.BASH_PATTERN.match(tool):
                continue

            # Check MCP pattern
            if cls.MCP_PATTERN.match(tool):
                continue

            # Unknown tool
            messages.append(
                ValidationMessage(
                    Severity.WARNING,
                    Path(),
                    None,
                    f"Unknown tool: {tool}",
                    "Check if this is a valid tool or MCP server name",
                )
            )

        return messages


class SubAgentValidator:
    """Validate sub-agent configuration files"""

    REQUIRED_FIELDS = ["name", "description", "tools", "model"]
    VALID_MODELS = ["opus", "sonnet", "haiku"]

    @staticmethod
    def validate(file_path: Path) -> list[ValidationMessage]:
        """Validate a sub-agent file"""
        messages = []

        content = file_path.read_text()
        frontmatter, fm_end = FrontmatterParser.extract(content)

        # Check frontmatter exists
        if frontmatter is None:
            messages.append(
                ValidationMessage(
                    Severity.ERROR,
                    file_path,
                    1,
                    "Missing YAML frontmatter",
                    "Add frontmatter block starting with --- on line 1",
                )
            )
            return messages

        # Check required fields
        for field in SubAgentValidator.REQUIRED_FIELDS:
            if field not in frontmatter:
                messages.append(
                    ValidationMessage(
                        Severity.ERROR,
                        file_path,
                        None,
                        f"Missing required field: {field}",
                        f"Add '{field}: value' to frontmatter",
                    )
                )

        # Validate name format (kebab-case)
        if "name" in frontmatter:
            name = frontmatter["name"]
            if not re.match(r"^[a-z]+(-[a-z]+)*$", name):
                messages.append(
                    ValidationMessage(
                        Severity.WARNING,
                        file_path,
                        None,
                        f"Name should be kebab-case: {name}",
                        f"Consider: {name.lower().replace('_', '-')}",
                    )
                )

        # Validate model
        if "model" in frontmatter:
            model = frontmatter["model"]
            if model not in SubAgentValidator.VALID_MODELS:
                messages.append(
                    ValidationMessage(
                        Severity.ERROR,
                        file_path,
                        None,
                        f"Invalid model: {model}",
                        f"Use one of: {', '.join(SubAgentValidator.VALID_MODELS)}",
                    )
                )

        # Validate tools
        if "tools" in frontmatter:
            tool_messages = ToolsValidator.validate(frontmatter["tools"], "Sub-agent")
            for msg in tool_messages:
                msg.file_path = file_path
            messages.extend(tool_messages)

        # Check description quality
        if "description" in frontmatter:
            desc = frontmatter["description"]
            if len(desc) < 20:
                messages.append(
                    ValidationMessage(
                        Severity.WARNING,
                        file_path,
                        None,
                        "Description too short - should be descriptive",
                        "Add clear description of when and how to use this agent",
                    )
                )

            # Recommend PROACTIVELY for auto-activation
            if "proactive" not in desc.lower():
                messages.append(
                    ValidationMessage(
                        Severity.INFO,
                        file_path,
                        None,
                        "Consider adding 'Use PROACTIVELY' for auto-activation",
                        "Add to description if this agent should activate automatically",
                    )
                )

        # Content validation
        lines = content.split("\n")
        has_workflow = any("## Workflow" in line or "## workflow" in line for line in lines)
        has_responsibilities = any(
            "## Responsibilities" in line or "## responsibilities" in line for line in lines
        )

        if not has_workflow:
            messages.append(
                ValidationMessage(
                    Severity.INFO,
                    file_path,
                    None,
                    "Recommended: Add '## Workflow' section",
                    "Document step-by-step process for this agent",
                )
            )

        if not has_responsibilities:
            messages.append(
                ValidationMessage(
                    Severity.INFO,
                    file_path,
                    None,
                    "Recommended: Add '## Responsibilities' section",
                    "Clearly list what this agent is responsible for",
                )
            )

        return messages


class CommandValidator:
    """Validate slash command configuration files"""

    REQUIRED_FIELDS = ["description", "allowed-tools"]

    @staticmethod
    def validate(file_path: Path) -> list[ValidationMessage]:
        """Validate a slash command file"""
        messages = []

        content = file_path.read_text()
        frontmatter, fm_end = FrontmatterParser.extract(content)

        # Check frontmatter exists
        if frontmatter is None:
            messages.append(
                ValidationMessage(
                    Severity.ERROR,
                    file_path,
                    1,
                    "Missing YAML frontmatter",
                    "Add frontmatter block starting with --- on line 1",
                )
            )
            return messages

        # Check required fields
        for field in CommandValidator.REQUIRED_FIELDS:
            if field not in frontmatter:
                messages.append(
                    ValidationMessage(
                        Severity.ERROR,
                        file_path,
                        None,
                        f"Missing required field: {field}",
                        f"Add '{field}: value' to frontmatter",
                    )
                )

        # Validate description (should be concise)
        if "description" in frontmatter:
            desc = frontmatter["description"]
            if len(desc) > 100:
                messages.append(
                    ValidationMessage(
                        Severity.WARNING,
                        file_path,
                        None,
                        "Description too long - should be one concise line",
                        "Keep under 100 characters for slash command menu",
                    )
                )

        # Validate allowed-tools
        if "allowed-tools" in frontmatter:
            tools_str = frontmatter["allowed-tools"]

            # Check delegation pattern
            has_task = "Task" in tools_str
            has_mcp = "mcp__ib-sec-mcp__" in tools_str

            if has_task and has_mcp:
                messages.append(
                    ValidationMessage(
                        Severity.INFO,
                        file_path,
                        None,
                        "Hybrid pattern detected: Task + MCP tools",
                        "This is valid but consider if direct MCP calls are needed",
                    )
                )
            elif not has_task and not has_mcp:
                messages.append(
                    ValidationMessage(
                        Severity.INFO,
                        file_path,
                        None,
                        "No Task or MCP tools - direct execution pattern",
                        "Ensure command can complete with available tools",
                    )
                )

            # Validate tools list
            tool_messages = ToolsValidator.validate(tools_str, "Command")
            for msg in tool_messages:
                msg.file_path = file_path
            messages.extend(tool_messages)

        # Content validation
        lines = content.split("\n")[fm_end:]
        content_body = "\n".join(lines)

        # Check for $ARGUMENTS usage
        if "$ARGUMENTS" in content_body or "$1" in content_body:
            if "argument-hint" not in frontmatter:
                messages.append(
                    ValidationMessage(
                        Severity.WARNING,
                        file_path,
                        None,
                        "Uses $ARGUMENTS but no argument-hint in frontmatter",
                        "Add 'argument-hint: [expected-args]' for documentation",
                    )
                )

        # Check Task delegation syntax
        task_pattern = re.compile(r"Task\([a-z-]+\)")
        task_matches = task_pattern.findall(content_body)

        if task_matches:
            if "Task" not in frontmatter.get("allowed-tools", ""):
                messages.append(
                    ValidationMessage(
                        Severity.ERROR,
                        file_path,
                        None,
                        "Uses Task delegation but Task not in allowed-tools",
                        "Add 'Task' to allowed-tools in frontmatter",
                    )
                )

            # Validate sub-agent references
            agents_dir = file_path.parent.parent / "agents"
            for match in task_matches:
                agent_name = match.replace("Task(", "").replace(")", "")
                agent_file = agents_dir / f"{agent_name}.md"

                if not agent_file.exists():
                    messages.append(
                        ValidationMessage(
                            Severity.ERROR,
                            file_path,
                            None,
                            f"References non-existent sub-agent: {agent_name}",
                            f"Create {agent_file} or fix reference",
                        )
                    )

        # Check for examples section
        has_examples = "## Examples" in content_body or "### Examples" in content_body
        if not has_examples:
            messages.append(
                ValidationMessage(
                    Severity.INFO,
                    file_path,
                    None,
                    "Recommended: Add usage examples section",
                    "Show how to use this command with different arguments",
                )
            )

        return messages


class ConfigValidator:
    """Main validator orchestrator"""

    def __init__(self, auto_fix: bool = False):
        self.auto_fix = auto_fix
        self.messages: list[ValidationMessage] = []

    def validate_file(self, file_path: Path) -> list[ValidationMessage]:
        """Validate a single file"""
        if not file_path.exists():
            return [
                ValidationMessage(Severity.ERROR, file_path, None, f"File not found: {file_path}")
            ]

        # Determine file type
        if "/agents/" in str(file_path):
            return SubAgentValidator.validate(file_path)
        elif "/commands/" in str(file_path):
            return CommandValidator.validate(file_path)
        else:
            return [
                ValidationMessage(
                    Severity.WARNING,
                    file_path,
                    None,
                    "Unknown file type - expected agents/ or commands/",
                )
            ]

    def validate_all(self, base_path: Path) -> list[ValidationMessage]:
        """Validate all config files"""
        messages = []

        # Find all agent and command files
        agents_dir = base_path / "agents"
        commands_dir = base_path / "commands"

        files_to_check = []

        if agents_dir.exists():
            files_to_check.extend(agents_dir.glob("*.md"))

        if commands_dir.exists():
            files_to_check.extend(commands_dir.glob("*.md"))

        for file_path in sorted(files_to_check):
            file_messages = self.validate_file(file_path)
            messages.extend(file_messages)

        return messages

    @staticmethod
    def print_results(messages: list[ValidationMessage], verbose: bool = False):
        """Print validation results"""
        # Group by severity
        errors = [m for m in messages if m.severity == Severity.ERROR]
        warnings = [m for m in messages if m.severity == Severity.WARNING]
        info = [m for m in messages if m.severity == Severity.INFO]

        # Group by file
        by_file = {}
        for msg in messages:
            if msg.file_path not in by_file:
                by_file[msg.file_path] = []
            by_file[msg.file_path].append(msg)

        # Print results
        print("\n" + "=" * 60)
        print("Claude Code Configuration Validation Results")
        print("=" * 60 + "\n")

        for file_path, file_messages in sorted(by_file.items()):
            file_errors = [m for m in file_messages if m.severity == Severity.ERROR]
            file_warnings = [m for m in file_messages if m.severity == Severity.WARNING]

            # File header
            if file_errors:
                status = Severity.ERROR.value
            elif file_warnings:
                status = Severity.WARNING.value
            else:
                status = Severity.SUCCESS.value

            print(f"{status} {file_path.relative_to(file_path.parent.parent.parent)}")

            # Print messages
            for msg in file_messages:
                if not verbose and msg.severity == Severity.INFO:
                    continue

                indent = "   "
                line_info = f"Line {msg.line_number}: " if msg.line_number else ""
                print(f"{indent}{msg.severity.value} {line_info}{msg.message}")

                if msg.suggestion:
                    print(f"{indent}   💡 {msg.suggestion}")

            print()

        # Summary
        print("=" * 60)
        print("Summary:")
        print(f"  {Severity.ERROR.value} Errors: {len(errors)}")
        print(f"  {Severity.WARNING.value} Warnings: {len(warnings)}")
        print(f"  {Severity.INFO.value} Info: {len(info)}")
        print("=" * 60 + "\n")

        # Return code
        return 1 if errors else 0


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Validate Claude Code configuration files")
    parser.add_argument("files", nargs="*", help="Specific files to validate (default: all)")
    parser.add_argument(
        "--changed-only", action="store_true", help="Only validate git changed files"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix common issues (not yet implemented)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show info-level messages")

    args = parser.parse_args()

    # Determine files to check
    base_path = Path(__file__).parent.parent
    validator = ConfigValidator(auto_fix=args.fix)

    if args.files:
        # Validate specific files
        messages = []
        for file_arg in args.files:
            file_path = Path(file_arg)
            messages.extend(validator.validate_file(file_path))

    elif args.changed_only:
        # Validate git changed files
        import subprocess

        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"], capture_output=True, text=True, check=True
            )
            changed_files = result.stdout.strip().split("\n")

            messages = []
            for file_path_str in changed_files:
                if ".claude/" in file_path_str and file_path_str.endswith(".md"):
                    file_path = Path(file_path_str)
                    if file_path.exists():
                        messages.extend(validator.validate_file(file_path))

        except subprocess.CalledProcessError:
            print("Error: Git not available or not in a git repository")
            return 1

    else:
        # Validate all files
        messages = validator.validate_all(base_path)

    # Print results
    exit_code = validator.print_results(messages, verbose=args.verbose)

    if args.fix:
        print("Note: Auto-fix not yet implemented")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
