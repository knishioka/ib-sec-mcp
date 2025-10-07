# Installation Guide

## Quick Start

### 1. Install Dependencies

```bash
# Using pip
pip install -e .

# Or using requirements.txt
pip install -r requirements.txt
```

### 2. Configure Environment

Create/update `.env` file with your IB Flex Query credentials:

```env
# Single account
QUERY_ID=your_query_id
TOKEN=your_token_here

# OR Multiple accounts
ACCOUNT_1_QUERY_ID=your_query_id
ACCOUNT_1_TOKEN=your_token_here
ACCOUNT_1_ALIAS=Main Trading

ACCOUNT_2_QUERY_ID=another_query_id
ACCOUNT_2_TOKEN=another_token_here
ACCOUNT_2_ALIAS=Retirement
```

### 3. Test Installation

```bash
# Test CLI commands
ib-sec-fetch --help
ib-sec-analyze --help

# Or run example script
python scripts/example_usage.py
```

## Development Setup

### Install with Development Dependencies

```bash
pip install -e ".[dev]"
```

### Install All Optional Features

```bash
pip install -e ".[dev,visualization,reporting]"
```

## Usage Examples

### Fetch Data

```bash
# Fetch YTD data
ib-sec-fetch

# Fetch specific date range
ib-sec-fetch --start-date 2025-01-01 --end-date 2025-10-05

# Fetch all accounts
ib-sec-fetch --multi-account
```

### Run Analysis

```bash
# Run all analyzers
ib-sec-analyze data/raw/U16231259_2025-01-01_2025-10-05.csv --all

# Run specific analyzer
ib-sec-analyze data/raw/U16231259_2025-01-01_2025-10-05.csv --analyzer performance

# Run multiple analyzers with custom tax rate
ib-sec-analyze data.csv -a performance -a tax --tax-rate 0.25
```

### Programmatic Usage

```python
from datetime import date
from ib_sec_mcp import FlexQueryClient
from ib_sec_mcp.analyzers import PerformanceAnalyzer
from ib_sec_mcp.core.parsers import CSVParser

# Fetch data
client = FlexQueryClient(query_id="123", token="abc")
statement = client.fetch_statement(
    start_date=date(2025, 1, 1),
    end_date=date(2025, 10, 5)
)

# Parse data
account = CSVParser.to_account(
    statement.raw_data,
    from_date=date(2025, 1, 1),
    to_date=date(2025, 10, 5)
)

# Run analysis
analyzer = PerformanceAnalyzer(account=account)
results = analyzer.analyze()

print(results)
```

## Troubleshooting

### Import Errors

If you get import errors, make sure you've installed the package:

```bash
pip install -e .
```

### Missing Dependencies

Install missing dependencies:

```bash
pip install -r requirements.txt
```

### API Connection Issues

- Check your `.env` file has correct credentials
- Verify QUERY_ID and TOKEN are valid
- Check internet connection
- IB API may be temporarily unavailable

## Next Steps

1. Read [README.md](README.md) for detailed documentation
2. Check [scripts/example_usage.py](scripts/example_usage.py) for code examples
3. Review existing analyses in `legacy/` folder
4. Run tests: `pytest` (after implementing tests)

## Migration from Legacy Scripts

Your existing scripts have been moved to `legacy/` folder:

- `analyze_performance.py` → Use `PerformanceAnalyzer`
- `trading_cost_analysis.py` → Use `CostAnalyzer`
- `phantom_income_tax_analysis.py` → Use `TaxAnalyzer`
- `bond_analysis.py` → Use `BondAnalyzer`
- `interest_rate_scenario_analysis.py` → Use `RiskAnalyzer`
- `comprehensive_summary_report.py` → Use multiple analyzers + `ConsoleReport`

The new library provides:
- ✅ Better structure and organization
- ✅ Type safety with Pydantic v2
- ✅ Multi-account support
- ✅ Reusable components
- ✅ CLI tools
- ✅ Async support for performance
