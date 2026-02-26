# IB Analytics

Interactive Brokers portfolio analytics library with **AI-powered investment analysis** and **development automation**.

## Overview

IB Analytics enables systematic analysis of trading performance across multiple IB accounts with type-safe, modular, and extensible architecture.

**For Investors** (Modes 1 & 2):

- **95% faster investment strategy** generation (6-8 hours → 15-20 minutes)
- **Parallel market analysis** of all holdings simultaneously
- **Consolidated multi-account view** with accurate portfolio metrics
- **Professional options strategies** with specific strikes, Greeks, and Max Pain
- **Tax-optimized execution plans** across multiple accounts
- **Multi-timeframe technical analysis** with entry/exit signals

**For Developers** (Mode 3):

- **90% faster issue resolution** (80 minutes → 8 minutes via `/resolve-gh-issue`)
- **Automated quality gates** (black, ruff, mypy, pytest)
- **Complete TDD workflow** (tests → code → PR automation)
- **11 specialized AI agents** + **20 slash commands**

| Task                | Manual    | Automated | Savings |
| ------------------- | --------- | --------- | ------- |
| Investment Strategy | 6-8 hours | 15-20 min | **95%** |
| Stock Analysis      | 1-2 hours | 2-3 min   | **97%** |
| Options Strategy    | 45-60 min | 3-5 min   | **93%** |
| Portfolio Analysis  | 3-4 hours | 5 min     | **95%** |
| GitHub Issue → PR   | 80 min    | 8 min     | **90%** |

## Installation

```bash
# Install with pip
pip install -e .

# Install with MCP server support
pip install -e ".[mcp]"

# Install with development dependencies
pip install -e ".[dev]"

# Install all optional dependencies
pip install -e ".[dev,mcp,visualization,reporting]"
```

## Quick Start

### 1. Configuration

Create a `.env` file with your IB Flex Query credentials:

```env
QUERY_ID=your_query_id
TOKEN=your_token_here
```

**Note**: To analyze multiple accounts, configure them in your IB Flex Query settings. A single query can return data for multiple accounts.

### 2. Fetch Data

```bash
# Fetch data
ib-sec-fetch --start-date 2025-01-01 --end-date 2025-10-05

# Split by account (if query contains multiple accounts)
ib-sec-fetch --split-accounts --start-date 2025-01-01 --end-date 2025-10-05
```

### 3. Run Analysis

```bash
# Run comprehensive analysis
ib-sec-analyze --account U1234567

# Run specific analyzer
ib-sec-analyze --account U1234567 --analyzer performance

# Analyze all accounts
ib-sec-analyze --all-accounts
```

### 4. Generate Reports

```bash
# Console report
ib-sec-report --account U1234567 --format console

# HTML report with charts
ib-sec-report --account U1234567 --format html --output report.html
```

## Docker Usage

Run IB Analytics in an isolated container with security hardening (non-root user, read-only filesystem, resource limits).

```bash
docker-compose up  # or: docker build -t ib-sec-mcp . && docker run -e QUERY_ID=... -e TOKEN=... ib-sec-mcp
```

See [docs/docker.md](docs/docker.md) for full setup, docker-compose configuration, and troubleshooting.

## Programmatic Usage

```python
from ib_sec_mcp import FlexQueryClient, Portfolio
from ib_sec_mcp.analyzers import PerformanceAnalyzer, TaxAnalyzer
from datetime import date

# Initialize client
client = FlexQueryClient(query_id="your_query_id", token="your_token_here")

# Fetch data
data = client.fetch_statement(
    start_date=date(2025, 1, 1),
    end_date=date(2025, 10, 5)
)

# Create portfolio
portfolio = Portfolio.from_flex_data(data)

# Run analysis
perf_analyzer = PerformanceAnalyzer(portfolio)
results = perf_analyzer.analyze()

# Generate report
from ib_sec_mcp.reports import ConsoleReport
report = ConsoleReport(results)
report.render()
```

## Project Structure

```
ib-sec/
├── ib_sec_mcp/           # Main library
│   ├── api/               # Flex Query API client
│   ├── core/              # Core business logic
│   ├── models/            # Pydantic data models
│   ├── analyzers/         # Analysis modules
│   ├── reports/           # Report generators
│   └── utils/             # Utilities
├── tests/                 # Test suite
└── data/                  # Data directory
    ├── raw/              # Raw CSV/XML data
    └── processed/        # Processed data
```

## Architecture

### Layer Structure

```
┌─────────────────────────────────────┐
│      CLI Layer (typer + rich)       │
├─────────────────────────────────────┤
│    Reports Layer (console/html)     │
├─────────────────────────────────────┤
│   Analyzers Layer (5 analyzers)     │
├─────────────────────────────────────┤
│  Core Logic (parser/calc/agg)       │
├─────────────────────────────────────┤
│   Models Layer (Pydantic v2)        │
├─────────────────────────────────────┤
│    API Layer (sync + async)         │
└─────────────────────────────────────┘
```

### Design Patterns

**Template Method** (BaseAnalyzer):

```python
class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self) -> AnalysisResult:
        pass

    def _create_result(self, **kwargs) -> AnalysisResult:
        """Shared result creation with metadata"""
        result = AnalysisResult(self.analyzer_name, **kwargs)
        result["timestamp"] = datetime.now().isoformat()
        return result

class PerformanceAnalyzer(BaseAnalyzer):
    def analyze(self) -> AnalysisResult:
        trades = self.get_trades()
        # ... compute metrics ...
        return self._create_result(win_rate=win_rate, profit_factor=pf)
```

**Strategy** (Reports):

```python
class BaseReport(ABC):
    @abstractmethod
    def render(self) -> str:
        pass
```

**Factory Method** (Parsers, Portfolio):

```python
account = CSVParser.to_account(csv_data, from_date, to_date)
portfolio = Portfolio.from_accounts(accounts, base_currency="USD")
```

See [docs/architecture.md](docs/architecture.md) for data flow diagrams, layer responsibilities, and new feature decision guide.

## Available Analyzers

- **PerformanceAnalyzer**: Overall trading performance metrics
- **TaxAnalyzer**: Tax liability calculations (OID, capital gains)
- **CostAnalyzer**: Commission and cost efficiency analysis
- **RiskAnalyzer**: Interest rate and market risk scenarios
- **BondAnalyzer**: Bond-specific analytics (YTM, duration, etc.)

## Investment Analysis Tools (MCP)

45 MCP tools for stock, options, and portfolio analysis via Yahoo Finance and IB portfolio data.

| Category            | Tools | Representative Tools                                            |
| ------------------- | :---: | --------------------------------------------------------------- |
| Portfolio Analysis  |  15   | `analyze_performance`, `analyze_risk`, `get_portfolio_summary`  |
| Stock & Market Data |  12   | `get_stock_analysis`, `get_current_price`, `get_stock_info`     |
| Options Analysis    |   8   | `get_options_chain`, `calculate_greeks`, `calculate_iv_metrics` |
| Tax & Costs         |   6   | `analyze_tax`, `analyze_costs`, `calculate_tax_loss_harvesting` |
| Position History    |   4   | `get_position_history`, `compare_portfolio_snapshots`           |

Full reference (all arguments, return values, examples): [docs/mcp-tools-reference.md](docs/mcp-tools-reference.md)

## Usage Examples in Claude Desktop

Once you've set up the MCP server in Claude Desktop, you can use natural language:

```
"Show me detailed information for AAPL including all fundamental metrics"

"Compare my portfolio performance against the S&P 500 over the last year"

"What's the correlation between positions in my portfolio? Are they well diversified?"

"Analyze market sentiment for NVDA - should I buy now or wait?"

"What's the composite sentiment for SPY across news, options, and technicals?"

"Create a comprehensive investment plan for my portfolio"
```

## Usage Modes

IB Analytics supports three distinct usage modes optimized for different user types:

| Mode                      | Target              | Characteristics                                                               |
| ------------------------- | ------------------- | ----------------------------------------------------------------------------- |
| **1: Claude Desktop**     | Investors, analysts | Natural language queries, zero coding, complete analysis from single question |
| **2: Claude Code + MCP**  | Data scientists     | Direct tool composition, fine-grained data access, custom analysis workflows  |
| **3: Claude Code + Repo** | Developers          | Sub-agents, slash commands, GitHub integration, TDD workflow automation       |

**Mode 3 example**:

```bash
/resolve-gh-issue 42
# Automated: Issue analysis → Tests → Implementation → Quality checks → PR
# Result: 80 minutes → 8 minutes (90% time savings)
```

Detailed architecture, workflow examples, and implementation guide: [CLAUDE.md](CLAUDE.md)

See [.claude/README.md](.claude/README.md) for all 11 sub-agents and 20 slash commands.

## Feature Comparison

| Feature                    | Mode 1: Desktop     | Mode 2: MCP         | Mode 3: Repository                |
| -------------------------- | ------------------- | ------------------- | --------------------------------- |
| **Investment Analysis**    | ✅ Natural language | ✅ Composable tools | ✅ Advanced automation            |
| **Multi-Account Support**  | ✅ Automatic        | ✅ Manual selection | ✅ Consolidated analysis          |
| **Market Analysis**        | ✅ Basic            | ✅ Detailed         | ✅ **Parallel + Advanced**        |
| **Options Strategies**     | ✅ Basic            | ✅ Detailed         | ✅ **Professional-grade**         |
| **Tax Optimization**       | ✅ Recommendations  | ✅ Custom analysis  | ✅ **Multi-account optimization** |
| **Development Tools**      | ❌                  | ❌                  | ✅ 11 AI specialists              |
| **GitHub Integration**     | ❌                  | ❌                  | ✅ Issue → PR automation          |
| **Quality Gates**          | ❌                  | ❌                  | ✅ Automated enforcement          |
| **Time to Analysis**       | 2 minutes           | 15 minutes          | 15-20 minutes (comprehensive)     |
| **Time to Implementation** | N/A                 | N/A                 | 8 minutes (vs 80 manual)          |
| **Learning Curve**         | None                | Low                 | Medium                            |
| **Customization**          | Low                 | High                | Very High                         |

**Recommendation**:

- **Start with Mode 1** if you're an investor looking for quick insights
- **Use Mode 2** if you need custom analysis or programmatic access
- **Adopt Mode 3** if you're developing features or need advanced automation

## Position History & Time-Series Analysis

IB Analytics automatically stores daily position snapshots in SQLite (`data/processed/positions.db`) for historical analysis and time-series tracking.

**Features**: Automatic sync on data fetch, multi-account support, 5 MCP tools for querying history.

| Tool                           | Description                                |
| ------------------------------ | ------------------------------------------ |
| `get_position_history`         | Time series for a symbol over a date range |
| `get_portfolio_snapshot`       | All positions on a specific date           |
| `compare_portfolio_snapshots`  | Portfolio changes between two dates        |
| `get_position_statistics`      | Min/max/average statistics over time       |
| `get_available_snapshot_dates` | List all dates with snapshot data          |

Full schema, indexes, and migration procedures: [docs/database-schema.md](docs/database-schema.md)

---

## MCP Server Integration

IB Analytics provides a **Model Context Protocol (MCP)** server for integration with Claude Desktop and Claude Code.

### Features

- **45 Tools**: Portfolio analysis, market data, risk/tax/cost analytics, rebalancing, dividend/sector/FX analysis
- **9 Resources**: Portfolio data, account info, trades, positions, and strategy context via URI patterns
- **5 Prompts**: Pre-configured analysis templates for common workflows

### Setup Options

#### Option 1: Git リポジトリから直接実行（推奨・クローン不要）

インストール不要。設定ファイルに追記するだけで使用できます。

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "ib-sec-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "ib-sec-mcp[mcp] @ git+https://github.com/knishioka/ib-sec-mcp",
        "ib-sec-mcp"
      ],
      "env": {
        "QUERY_ID": "your_query_id",
        "TOKEN": "your_token"
      }
    }
  }
}
```

**Claude Code** (プロジェクトの `.mcp.json`):

```json
{
  "mcpServers": {
    "ib-sec-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "ib-sec-mcp[mcp] @ git+https://github.com/knishioka/ib-sec-mcp",
        "ib-sec-mcp"
      ],
      "env": {
        "QUERY_ID": "${QUERY_ID}",
        "TOKEN": "${TOKEN}"
      }
    }
  }
}
```

> **Note**: `[mcp]` extra の指定が必須です（`fastmcp`, `scipy`, `pyyaml` が含まれます）。

> **キャッシュ**: 初回のみ依存関係をダウンロード（`~/.cache/uv`）。2回目以降は即座に起動します。最新版を取得したい場合は `uvx --refresh` オプションを使用してください。

#### Option 2: ローカルリポジトリから実行（開発者向け）

リポジトリをクローンして開発する場合：

```bash
git clone https://github.com/knishioka/ib-sec-mcp.git
cd ib-sec-mcp
cp .mcp.json.example .mcp.json  # パスを編集
```

**`.mcp.json`**:

```json
{
  "mcpServers": {
    "ib-sec-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "/path/to/ib-sec-mcp", "run", "ib-sec-mcp"],
      "env": {
        "QUERY_ID": "${QUERY_ID}",
        "TOKEN": "${TOKEN}"
      }
    }
  }
}
```

### Prerequisites

- [uv](https://docs.astral.sh/uv/) インストール済み: `brew install uv` または `curl -LsSf https://astral.sh/uv/install.sh | sh`
- IB Flex Query の `QUERY_ID` と `TOKEN`（IB ポータルで取得）

See [MCP Tools Reference](docs/mcp-tools-reference.md) for complete documentation of all 45 tools, 9 resources, and 5 prompts.

See [.claude/CLAUDE.md](.claude/CLAUDE.md) for development guide and usage patterns.

## Documentation

| Document                                                                      | Description                                                                |
| ----------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| [Architecture](docs/architecture.md)                                          | Data flow diagrams, layer responsibilities, and new feature decision guide |
| [Financial Calculators](docs/calculators.md)                                  | Calculation formulas (YTM, duration, Sharpe, Sortino, phantom income)      |
| [Database Schema](docs/database-schema.md)                                    | SQLite position history schema, indexes, and migration procedures          |
| [MCP Tools Reference](docs/mcp-tools-reference.md)                            | Complete reference for all 45 tools, 9 resources, and 5 prompts            |
| [Docker Usage](docs/docker.md)                                                | Docker and docker-compose setup                                            |
| [Troubleshooting](docs/troubleshooting.md)                                    | Common errors and solutions                                                |
| [Calculation Error Prevention](docs/calculation_error_prevention_strategy.md) | ETF calculation accuracy strategy                                          |

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=ib_sec_mcp --cov-report=html

# Code formatting with Ruff
ruff format ib_sec_mcp tests

# Linting with Ruff
ruff check --fix ib_sec_mcp tests

# Type checking with mypy
mypy ib_sec_mcp

# Run all pre-commit hooks manually
pre-commit run --all-files
```

## Requirements

- Python 3.12+
- Interactive Brokers account with Flex Query access

## Dependencies

- **requests** (2.32.5+): HTTP client for API calls
- **pandas** (2.2.3+): Data analysis and manipulation
- **pydantic** (2.10.0+): Data validation and settings management
- **httpx** (0.27.0+): Async HTTP client for parallel requests
- **rich** (13.7.0+): Beautiful console output
- **typer** (0.12.0+): CLI framework
- **yfinance** (0.2.40+): Yahoo Finance data integration
- **fastmcp** (2.0.0+): Model Context Protocol server framework

## Security

### MCP Server Security

- **Error Masking**: Internal error details are masked from clients (configurable with `IB_DEBUG=1`)
- **Input Validation**: All inputs are validated before processing
- **File Path Protection**: Path traversal attacks are prevented
- **File Size Limits**: Maximum file size: 10MB
- **Timeout Protection**: All operations have timeout limits
- **Retry Logic**: Automatic retry for transient errors (max 3 attempts)

### Debug Mode

```bash
export IB_DEBUG=1
ib-sec-mcp
```

**Warning**: Never enable debug mode in production as it exposes internal error details.

### Credentials Security

- **Never commit** `.env` files to version control
- Store credentials in environment variables or secure secret management systems
- Regularly rotate API tokens

## Command Selection Guide

For an interactive decision flowchart and full command reference table, see [.claude/README.md](.claude/README.md).

**Quick reference**:

- **Investors**: `/investment-strategy` → `/analyze-symbol SYMBOL` → `/options-strategy SYMBOL`
- **Developers**: `/resolve-gh-issue N` → `/quality-check` → `/test`

## Troubleshooting

> For a comprehensive troubleshooting guide with detailed error cases, prevention tips, and the full exception hierarchy, see **[docs/troubleshooting.md](docs/troubleshooting.md)**.

### Testing

```bash
pip install -e ".[dev]"
pytest
pytest --cov=ib_sec_mcp --cov-report=html
```

### MCP Server Testing

```bash
# Start server in debug mode
IB_DEBUG=1 ib-sec-mcp
```

### Performance Optimization

If experiencing slow performance:

1. **Reduce date ranges**: Fetch smaller time periods
2. **Use file caching**: Reuse previously fetched data
3. **Limit technical indicators**: Only request needed indicators

## License

MIT

## Author

Kenichiro Nishioka

## Support

For issues and questions, please check the [IB Flex Query documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/flex-web-service/).
