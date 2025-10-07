# IB Analytics

Interactive Brokers portfolio analytics library with multi-account support.

## Features

- 📊 **Multi-Account Support**: Analyze multiple IB accounts simultaneously
- 🔄 **Flex Query API Integration**: Automated data fetching via IB Flex Query API v3
- 📈 **Comprehensive Analysis**: Performance, tax, cost, risk, and bond analytics
- 🎯 **Type-Safe**: Built with Pydantic v2 for robust data validation
- ⚡ **Async Support**: Parallel data fetching for multiple accounts
- 📄 **Rich Reports**: Console, HTML, and optional PDF reporting

## Installation

```bash
# Install with pip
pip install -e .

# Install with MCP server support
pip install -e ".[mcp]"

# Install with development dependencies
pip install -e ".[dev]"

# Install with visualization support
pip install -e ".[visualization]"

# Install all optional dependencies
pip install -e ".[dev,mcp,visualization,reporting]"
```

## Quick Start

### 1. Configuration

Create a `.env` file with your IB Flex Query credentials:

```env
# Single account
QUERY_ID=your_query_id
TOKEN=your_token_here

# Multiple accounts (optional)
ACCOUNT_1_QUERY_ID=your_query_id
ACCOUNT_1_TOKEN=your_token_here
ACCOUNT_2_QUERY_ID=another_query_id
ACCOUNT_2_TOKEN=another_token_here
```

### 2. Fetch Data

```bash
# Fetch data for single account
ib-sec-fetch --start-date 2025-01-01 --end-date 2025-10-05

# Fetch data for multiple accounts
ib-sec-fetch --multi-account --start-date 2025-01-01 --end-date 2025-10-05
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
├── scripts/               # CLI scripts
├── tests/                 # Test suite
├── data/                  # Data directory
│   ├── raw/              # Raw CSV/XML data
│   └── processed/        # Processed data
└── legacy/               # Legacy scripts
```

## Available Analyzers

- **PerformanceAnalyzer**: Overall trading performance metrics
- **TaxAnalyzer**: Tax liability calculations (OID, capital gains)
- **CostAnalyzer**: Commission and cost efficiency analysis
- **RiskAnalyzer**: Interest rate and market risk scenarios
- **BondAnalyzer**: Bond-specific analytics (YTM, duration, etc.)

## MCP Server Integration

IB Analytics provides a **Model Context Protocol (MCP)** server for integration with Claude Desktop and other MCP clients.

### Quick Start

```bash
# Install with MCP support
pip install -e ".[mcp]"

# Run MCP server
ib-sec-mcp
```

### Features

- **7 Tools**: Fetch IB data, run performance/cost/bond/tax/risk analysis, get portfolio summary
- **6 Resources**: Access portfolio data, account info, trades, and positions via URI patterns
- **5 Prompts**: Pre-configured analysis templates for common workflows

### Claude Desktop Setup

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

See [.claude/CLAUDE.md](.claude/CLAUDE.md) for detailed MCP documentation.

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=ib_sec_mcp --cov-report=html

# Code formatting
black ib_sec_mcp tests

# Linting
ruff check ib_sec_mcp tests

# Type checking
mypy ib_sec_mcp
```

## Requirements

- Python 3.9+
- Interactive Brokers account with Flex Query access

## Dependencies

- **requests** (2.32.5+): HTTP client for API calls
- **pandas** (2.2.3+): Data analysis and manipulation
- **pydantic** (2.10.0+): Data validation and settings management
- **httpx** (0.27.0+): Async HTTP client for parallel requests
- **rich** (13.7.0+): Beautiful console output
- **typer** (0.12.0+): CLI framework

## License

MIT

## Author

Kenichiro Nishioka

## Support

For issues and questions, please check the [IB Flex Query documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/flex-web-service/).
