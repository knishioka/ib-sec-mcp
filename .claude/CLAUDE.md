# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**IB Analytics** is a comprehensive portfolio analytics library for Interactive Brokers with multi-account support. The library parses IB Flex Query data (CSV/XML), performs financial analysis, and generates detailed reports on trading performance, costs, taxes, and risk.

**Mission**: Enable systematic analysis of trading performance across multiple IB accounts with type-safe, modular, and extensible architecture.

## Tech Stack

- **Python**: 3.9+ (support 3.9, 3.10, 3.11, 3.12)
- **Core Libraries**:
  - `pydantic` 2.10.0+ (data validation and models)
  - `pandas` 2.2.3+ (data analysis)
  - `requests` 2.32.5+ (HTTP client)
  - `httpx` 0.27.0+ (async HTTP)
  - `rich` 13.7.0+ (console UI)
  - `typer` 0.12.0+ (CLI framework)
- **Package Management**: `pip` with `pyproject.toml` (setuptools backend)
- **Code Quality**: `black`, `ruff`, `mypy` (optional dev dependencies)
- **Testing**: `pytest`, `pytest-asyncio`, `pytest-cov` (optional dev dependencies)

## Project Structure

```
ib-sec/
├── ib_sec_mcp/          # Main library package
│   ├── api/              # IB Flex Query API client
│   │   ├── client.py    # FlexQueryClient with async support
│   │   └── models.py    # API response models (Pydantic)
│   ├── core/            # Core business logic
│   │   ├── parsers.py   # CSV/XML parsers
│   │   ├── calculator.py # Financial calculations
│   │   └── aggregator.py # Multi-account aggregation
│   ├── models/          # Domain models (Pydantic v2)
│   │   ├── trade.py     # Trade records
│   │   ├── position.py  # Position holdings
│   │   ├── account.py   # Account data
│   │   └── portfolio.py # Multi-account portfolio
│   ├── analyzers/       # Analysis modules
│   │   ├── base.py      # BaseAnalyzer abstract class
│   │   ├── performance.py # Trading performance metrics
│   │   ├── cost.py      # Commission and cost analysis
│   │   ├── bond.py      # Bond-specific analytics
│   │   ├── tax.py       # Tax liability calculations
│   │   └── risk.py      # Risk analysis (interest rate, concentration)
│   ├── reports/         # Report generation
│   │   ├── base.py      # BaseReport abstract class
│   │   └── console.py   # Rich console reports
│   ├── utils/           # Utilities
│   │   ├── config.py    # Configuration management
│   │   └── validators.py # Data validators
│   └── cli/             # CLI commands
│       ├── fetch.py     # Data fetching CLI
│       ├── analyze.py   # Analysis CLI
│       └── report.py    # Report generation CLI
├── scripts/             # Example and utility scripts
├── tests/               # Test suite (to be implemented)
├── legacy/              # Original scripts (pre-refactor)
└── data/                # Data storage
    ├── raw/            # Raw CSV/XML from API
    └── processed/      # Analysis results
```

## Key Commands

### Installation & Setup
```bash
# Install package in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Install all optional features
pip install -e ".[dev,visualization,reporting]"
```

### CLI Usage
```bash
# Fetch data from IB API
ib-sec-fetch --start-date 2025-01-01 --end-date 2025-10-05

# Fetch data for all accounts (multi-account mode)
ib-sec-fetch --multi-account

# Run analysis on CSV data
ib-sec-analyze data/raw/U16231259_2025-01-01_2025-10-05.csv --all

# Run specific analyzer
ib-sec-analyze data.csv --analyzer performance

# Run multiple analyzers
ib-sec-analyze data.csv -a performance -a cost -a bond -a tax
```

### Development Commands
```bash
# Code formatting
black ib_sec_mcp tests

# Linting
ruff check ib_sec_mcp tests

# Type checking
mypy ib_sec_mcp

# Run tests (when implemented)
pytest
pytest --cov=ib_sec_mcp --cov-report=html
```

## Code Style & Conventions

### Python Style
- **Line Length**: 100 characters max
- **Formatter**: Black (100 char limit)
- **Linter**: Ruff (E, F, I, N, W, UP, B, A, C4, T20, SIM rules)
- **Type Checking**: mypy in strict mode
- **Import Order**: stdlib → third-party → local (managed by ruff)

### Naming Conventions
- **Classes**: PascalCase (e.g., `FlexQueryClient`, `PerformanceAnalyzer`)
- **Functions/Methods**: snake_case (e.g., `fetch_statement`, `calculate_ytm`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `API_VERSION`, `BASE_URL_SEND`)
- **Private**: Prefix with `_` (e.g., `_parse_date`, `_extract_account_id`)
- **Type Aliases**: PascalCase (e.g., `AnalysisResult`)

### Documentation
- **Docstrings**: Required for all public classes, methods, and functions
- **Format**: Google-style docstrings
- **Type Hints**: Required for all function signatures
- **Example**:
  ```python
  def calculate_ytm(
      face_value: Decimal,
      current_price: Decimal,
      years_to_maturity: Decimal,
  ) -> Decimal:
      """
      Calculate Yield to Maturity (YTM) for zero-coupon bonds

      Args:
          face_value: Bond face value
          current_price: Current market price
          years_to_maturity: Years until maturity

      Returns:
          YTM as percentage
      """
  ```

### Pydantic Models
- Use Pydantic v2 syntax (`BaseModel`, `Field`)
- Always provide descriptions in `Field(..., description="...")`
- Use `field_validator` for custom validations
- Configure `Config` class for JSON encoding when needed
- Example:
  ```python
  class Trade(BaseModel):
      symbol: str = Field(..., description="Trading symbol")
      quantity: Decimal = Field(..., description="Trade quantity")

      @field_validator("symbol")
      @classmethod
      def validate_symbol(cls, v: str) -> str:
          return v.upper()
  ```

### Error Handling
- Use custom exception classes (e.g., `FlexQueryError`, `FlexQueryAPIError`)
- Provide detailed error messages with context
- Log errors appropriately (use `rich.console` for CLI)
- Always clean up resources (use context managers when possible)

## Repository Etiquette

### Branch Naming
- Feature: `feature/description` (e.g., `feature/add-sharpe-ratio`)
- Fix: `fix/description` (e.g., `fix/csv-parser-date-handling`)
- Refactor: `refactor/description` (e.g., `refactor/analyzer-base-class`)
- Docs: `docs/description` (e.g., `docs/update-readme`)

### Commit Messages
- Format: `type: short description`
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- Keep first line under 72 characters
- Add detailed description after blank line if needed
- Examples:
  - `feat: add Sharpe ratio calculation to PerformanceCalculator`
  - `fix: handle missing maturity date in bond parser`
  - `refactor: extract common analyzer logic to BaseAnalyzer`

### Pull Requests
- Title: Same format as commit message
- Description: Include motivation, changes, and testing notes
- Reference related issues with `#123`
- Request review from team members
- Ensure all tests pass (when CI is set up)

### Merge Strategy
- **Preference**: Squash and merge for feature branches
- **Direct Commits**: Only to main for urgent hotfixes
- **Rebase**: When updating feature branch with main changes

## Environment Setup

### Required Files
- `.env`: IB Flex Query credentials (never commit!)
  ```env
  QUERY_ID=your_query_id
  TOKEN=your_token_here
  ```

**Note**: A single Flex Query can return data for multiple accounts. Configure multiple accounts in your IB Flex Query settings.

### Directory Structure
- `data/raw/`: Store fetched CSV/XML files (git-ignored)
- `data/processed/`: Store analysis results (git-ignored)
- `.claude/commands/`: Custom slash commands (optional, git-committed)

## Important Behaviors & Warnings

### API Rate Limiting
- IB Flex Query API has rate limits
- Default retry: 3 attempts with 5-second delay
- Adjust `api_max_retries` and `api_retry_delay` in config if needed

### Data Parsing
- CSV format has multiple sections with different headers
- Section detection based on first column (`ClientAccountID`)
- Trade dates in `YYYYMMDD` format
- Bond maturity dates may be missing (handle gracefully)

### Type Safety
- Always use `Decimal` for financial calculations (never `float`)
- Use `date` and `datetime` from standard library
- Pydantic models provide runtime validation
- Type hints are enforced in strict mypy mode

### Multi-Account Support
- Credentials can be single or multiple accounts
- Portfolio aggregates data across accounts
- Each analyzer works with either Account or Portfolio

### Testing
- Tests not yet implemented (TODO)
- When adding tests, use `pytest` with fixtures in `tests/fixtures/`
- Mock API calls using `pytest-asyncio` for async tests

## Claude Code Extensions

### Custom Slash Commands

Slash commands are prompt templates stored in `.claude/commands/` directory for repeated workflows.

#### Creating New Slash Commands

**File Structure**: `.claude/commands/{command-name}.md`

**Frontmatter (Optional)**:
```yaml
---
description: Brief command description
allowed-tools: Optional tool permissions (comma-separated)
argument-hint: [optional argument format]
---
```

**Command Body**: Natural language instructions with argument placeholders

**Argument Placeholders**:
- `$ARGUMENTS` - Captures entire argument string
- `$1`, `$2`, `$3`, etc. - Positional arguments (space-separated)

**Example Command** (`.claude/commands/example.md`):
```markdown
---
description: Run analysis with custom tax rate
allowed-tools: Read, mcp__ib-sec-mcp__analyze_tax
argument-hint: tax-rate
---

Run tax analysis with tax rate: $ARGUMENTS

If no arguments provided, use default rate of 0.30 (30%).

Steps:
1. Load latest CSV from data/raw/
2. Run tax analyzer with specified rate
3. Display results with rich formatting
```

**Usage**: `/example 0.25`

**Best Practices**:
- Use clear, descriptive command names (kebab-case)
- Provide `description` in frontmatter (shows in command menu)
- Use `argument-hint` to guide users on expected arguments
- Delegate complex tasks to sub-agents
- Include error handling instructions
- Document expected output format

**Available Commands**: See `.claude/README.md` for full list (14 commands)

### Specialized Sub-Agents

Sub-agents are AI assistants with dedicated context windows for specific tasks.

#### Creating New Sub-Agents

**File Structure**: `.claude/agents/{agent-name}.md`

**Required Frontmatter**:
```yaml
---
name: agent-name
description: When to use this subagent and what it does
tools: tool1, tool2, tool3  # Comma-separated, or omit to inherit all
model: sonnet  # Optional: sonnet, opus, haiku, or inherit
---
```

**Agent Body**: Specialized system prompt with domain knowledge and workflows

**Example Sub-Agent** (`.claude/agents/example.md`):
```markdown
---
name: security-auditor
description: Security specialist for vulnerability assessment and threat modeling. Use for security reviews, penetration testing, and compliance checks.
tools: Read, Grep, Bash(bandit:*), Bash(safety:*)
model: sonnet
---

You are a security specialist with expertise in:
- Vulnerability assessment
- Threat modeling
- Security best practices
- Compliance (SOC2, GDPR, etc.)

## Your Responsibilities

1. Code Security Review
2. Dependency Vulnerability Scanning
3. Authentication/Authorization Analysis
4. Data Protection Assessment

## Security Checklist

- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF tokens implemented

## Tools Usage

**Bandit** (Python security linter):
```bash
bandit -r ib_sec_mcp/
```

**Safety** (Dependency checker):
```bash
safety check
```

Always provide severity ratings (CRITICAL, HIGH, MEDIUM, LOW) and remediation steps.
```

**Agent Activation**:
- **Automatic**: Based on query patterns matching description
- **Explicit**: "Use the {agent-name} subagent to..."
- **Proactive**: Add "use PROACTIVELY" in description for auto-activation

**Best Practices**:
- Keep agents focused on single domain
- Provide detailed expertise in system prompt
- Include specific tool commands and workflows
- Use clear section headers (## format)
- Add examples of expected output
- Limit tool access to necessary permissions only

**Tool Permissions**:
- Omit `tools:` to inherit all tools from main agent
- Specify exact tools for security isolation
- Use wildcards: `Bash(pytest:*)` for pattern matching
- Add MCP tools: `mcp__server-name__tool-name`

**Model Selection**:
- `sonnet` - Balanced (default, recommended)
- `opus` - Maximum capability (slower, expensive)
- `haiku` - Fast and efficient (simpler tasks)
- `inherit` - Use same model as main conversation
- Omit to use default model

#### Managing Sub-Agents

**Using `/agents` Command**:
```bash
# Interactive tool permission management
/agents

# Shows all agents and their tool access
# Allows adding/removing tools
```

**Sub-Agent Delegation Patterns**:

```
# Automatic delegation
User: "Run tests with coverage"
Claude: [Detects "test" keyword, delegates to test-runner]

# Explicit delegation
User: "Use the data-analyzer subagent to analyze my bonds"
Claude: [Explicitly delegates to data-analyzer]

# Proactive delegation (in agent description)
description: "...Use this subagent PROACTIVELY after code changes..."
```

**Available Sub-Agents**: See `.claude/README.md` for full list (5 agents)

### Settings Configuration

Project-level settings: `.claude/settings.local.json` (gitignored)

**Structure**:
```json
{
  "permissions": {
    "allow": [
      "Bash(pytest:*)",
      "Read",
      "Write",
      "mcp__ib-sec-mcp__*"
    ],
    "deny": [],
    "ask": []
  },
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["ib-sec-mcp"]
}
```

**Permission Patterns**:
- `Bash(command:*)` - Allow bash command with any arguments
- `Read(/path/**)` - Allow reading files in path recursively
- `mcp__server__tool` - Allow specific MCP tool
- Use wildcards for flexibility

### Quick Reference

**Create Slash Command**:
1. Create `.claude/commands/{name}.md`
2. Add frontmatter with description
3. Write natural language instructions
4. Use `$ARGUMENTS` for parameters
5. Test with `/{name}`

**Create Sub-Agent**:
1. Create `.claude/agents/{name}.md`
2. Add required frontmatter (name, description, tools, model)
3. Write specialized system prompt
4. Add domain expertise and workflows
5. Test by invoking explicitly or waiting for auto-activation

**Manage Permissions**:
1. Use `/permissions` for interactive management
2. Or edit `.claude/settings.local.json` directly
3. Add tools to sub-agent frontmatter for isolation

### Available Commands
See `.claude/README.md` for complete documentation (14 slash commands, 5 sub-agents)

## Special Notes

### Legacy Scripts
- Original scripts preserved in `legacy/` folder
- Do not modify legacy scripts directly
- Reference for behavior comparison only

### Future Enhancements
- XML parser implementation (currently placeholder)
- HTML/PDF report generation (currently console only)
- Additional analyzers (Sharpe ratio, max drawdown, etc.)
- Unit test suite with pytest
- CI/CD pipeline

### Dependencies Version Policy
- Use latest stable versions at time of install
- Pin minimum versions in `pyproject.toml`
- Update dependencies quarterly or for security patches
- Test compatibility before upgrading major versions

## Quick Reference

### Adding New Analyzer
1. Create file in `ib_sec_mcp/analyzers/`
2. Inherit from `BaseAnalyzer`
3. Implement `analyze()` method returning `AnalysisResult`
4. Add to `__init__.py` exports
5. Update `ConsoleReport` with rendering logic
6. Add CLI option in `analyze.py`

### Adding New CLI Command
1. Create file in `ib_sec_mcp/cli/`
2. Use `typer.Typer()` for command group
3. Add to `[project.scripts]` in `pyproject.toml`
4. Document in README.md

### Common Pitfalls
- ❌ Don't use `float` for money (use `Decimal`)
- ❌ Don't commit `.env` file
- ❌ Don't modify legacy scripts
- ❌ Don't forget to update `__init__.py` exports
- ❌ Don't skip type hints
- ✅ Always validate input data
- ✅ Always provide docstrings
- ✅ Always handle errors gracefully
- ✅ Always use context managers for resources

## MCP Server (Model Context Protocol)

IB Analytics provides an MCP server interface for Claude Desktop and other MCP clients.

### MCP Components

**Analysis Tools** (7 tools - coarse-grained, complete analysis):
- `fetch_ib_data` - Fetch data from IB Flex Query API
- `analyze_performance` - Trading performance metrics
- `analyze_costs` - Commission and cost analysis
- `analyze_bonds` - Zero-coupon bond analytics
- `analyze_tax` - Tax liability including phantom income
- `analyze_risk` - Portfolio risk with interest rate scenarios
- `get_portfolio_summary` - Portfolio overview

**Composable Data Tools** (5 tools - fine-grained, sub-agent friendly):
- `get_trades` - Filtered trade data (by symbol, asset class, date range)
- `get_positions` - Current positions with filtering options
- `get_account_summary` - Account overview with P&L breakdown
- `calculate_metric` - Individual metrics (win_rate, profit_factor, etc.)
- `compare_periods` - Period-over-period metric comparison

**Data Resources** (6 URI patterns - raw data access):
- `ib://portfolio/list` - List available CSV files
- `ib://portfolio/latest` - Latest portfolio summary
- `ib://accounts/{account_id}` - Specific account data
- `ib://trades/recent` - Recent trades (last 10)
- `ib://positions/current` - Current positions

**Strategy Resources** (3 URI patterns - strategic context):
- `ib://strategy/tax-context` - Tax planning with loss harvesting opportunities
- `ib://strategy/rebalancing-context` - Portfolio allocation and drift analysis
- `ib://strategy/risk-context` - Risk metrics and scenario analysis

**Prompts** (5 templates):
- `analyze_portfolio` - Comprehensive portfolio analysis
- `tax_planning` - Tax implications and planning
- `risk_assessment` - Portfolio risk assessment
- `bond_portfolio_analysis` - Bond-specific analysis
- `monthly_performance_review` - Monthly performance review

### Running MCP Server

```bash
# Install with MCP support
pip install -e ".[mcp]"

# Run MCP server (stdio transport for Claude Desktop)
ib-sec-mcp

# Or run directly
python -m ib_sec_mcp.mcp.server
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ib-sec-mcp": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "ib_sec_mcp.mcp.server"],
      "env": {
        "QUERY_ID": "your_query_id",
        "TOKEN": "your_token"
      }
    }
  }
}
```

**Important**: Replace `/path/to/venv/bin/python` with your actual Python path.

### MCP Usage Examples

**Traditional Analysis (Coarse-Grained)**:
```
# Fetch latest data
"Please fetch my IB data for the last 30 days"

# Complete analysis
"Analyze my portfolio using the latest data"

# Access resources
"Show me my current positions" → reads ib://positions/current
```

**Sub-Agent Collaboration (Fine-Grained)**:
```
# Get specific data
"Get my AAPL trades from the last quarter"
→ Uses get_trades(symbol="AAPL")

# Calculate specific metrics
"What's my win rate on bond trades?"
→ Uses calculate_metric(metric_name="win_rate", asset_class="BOND")

# Compare periods
"How did my performance in Q1 compare to Q2?"
→ Uses compare_periods(period1_start, period1_end, period2_start, period2_end)

# Strategy context
"What are my tax loss harvesting opportunities?"
→ Reads ib://strategy/tax-context

# Rebalancing guidance
"Does my portfolio need rebalancing?"
→ Reads ib://strategy/rebalancing-context

# Risk assessment
"What's my interest rate risk?"
→ Reads ib://strategy/risk-context
```

### MCP Architecture

```
ib_sec_mcp/mcp/
├── __init__.py      # Module exports
├── server.py        # FastMCP server setup
├── tools.py         # Tool definitions (7 tools)
├── resources.py     # Resource URIs (6 resources)
└── prompts.py       # Prompt templates (5 prompts)
```

**Key Points**:
- Server uses **stdio transport** for Claude Desktop
- **Logging**: All logs go to stderr (stdout reserved for JSON-RPC)
- **Authentication**: Reads QUERY_ID/TOKEN from environment
- **Data Access**: Tools access `data/raw/` CSV files
- **Read-Only**: All operations are read-only (no data modification)

### MCP Framework Notes

Based on **FastMCP 2.0+** (Model Context Protocol Python SDK):
- Tools are Python functions with type hints and docstrings
- Resources use URI patterns (e.g., `ib://resource/{param}`)
- Prompts return message lists for LLM workflows
- Context object available for logging and LLM sampling
- Async/await support for all operations

---

**Last Updated**: 2025-10-11
**Maintained By**: Kenichiro Nishioka
**Project Version**: 0.1.0

**Claude Code Setup**: 5 sub-agents, 14 slash commands
See `.claude/README.md` and `.claude/WORKFLOWS.md` for complete documentation
