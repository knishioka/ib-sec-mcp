# Troubleshooting Guide

Comprehensive troubleshooting guide for IB Analytics. For a quick overview of common issues, see the [README.md Troubleshooting section](../README.md#troubleshooting). For installation-specific issues, see [INSTALL.md](../INSTALL.md).

---

## Table of Contents

- [Configuration Errors](#1-configuration-errors)
- [Input Validation Errors](#2-input-validation-errors)
- [IB Flex Query API Errors](#3-ib-flex-query-api-errors)
- [Yahoo Finance Errors](#4-yahoo-finance-errors)
- [Timeout Errors](#5-timeout-errors)
- [MCP Connection Errors](#6-mcp-connection-errors)
- [XML Parsing Errors](#7-xml-parsing-errors)
- [Multi-Account Data Issues](#8-multi-account-data-issues)
- [Bond Data Gaps](#9-bond-data-gaps)
- [Decimal and Type Errors](#10-decimal-and-type-errors)
- [Permission and File Errors](#11-permission-and-file-errors)
- [Import Errors](#12-import-errors)
- [Debug Mode](#debug-mode)
- [Getting Help](#getting-help)

---

## 1. Configuration Errors

### Error: "Configuration error: Failed to load credentials"

**Exception**: `ConfigurationError`

**Error Message**:

```
Configuration error: Failed to load credentials
```

or

```
QUERY_ID and TOKEN must be set in environment
```

**Cause**: The `QUERY_ID` and/or `TOKEN` environment variables are not set. These credentials are required to authenticate with the IB Flex Query API. The application looks for them in the following order:

1. Environment variables (`QUERY_ID`, `TOKEN`)
2. `.env` file in the current working directory

**Solution**:

```bash
# Option 1: Create a .env file in the project root
cat > .env << 'EOF'
QUERY_ID=your_query_id
TOKEN=your_token_here
EOF

# Option 2: Set environment variables directly
export QUERY_ID=your_query_id
export TOKEN=your_token

# Option 3: Pass via Docker environment
docker run -e QUERY_ID=your_query_id -e TOKEN=your_token ib-sec-mcp
```

**Prevention Tips**:

- Keep a `.env.example` file with placeholder values for reference
- Never commit `.env` files to version control (already in `.gitignore`)
- Verify credentials are loaded: set `IB_DEBUG=1` and check logs for `"Credentials loaded successfully"`
- For Claude Desktop, set credentials in the MCP server config (`claude_desktop_config.json`)

---

## 2. Input Validation Errors

### Error: "Validation error for 'start_date': Invalid date format"

**Exception**: `ValidationError`

**Error Message**:

```
Validation error for 'start_date': Invalid date format. Expected YYYY-MM-DD
```

**Cause**: The date string does not match the expected `YYYY-MM-DD` format. Common mistakes include using `MM/DD/YYYY`, `DD-MM-YYYY`, or omitting leading zeros.

**Solution**:

```bash
# Correct format: YYYY-MM-DD
ib-sec-fetch --start-date 2025-01-01 --end-date 2025-12-31

# Wrong formats (will fail):
# ib-sec-fetch --start-date 01/01/2025      # US format
# ib-sec-fetch --start-date 1-1-2025        # Missing leading zeros
# ib-sec-fetch --start-date 2025/01/01      # Wrong separator
```

**Prevention Tips**:

- Always use ISO 8601 date format: `YYYY-MM-DD`
- Include leading zeros for single-digit months and days
- Ensure `start_date` is before `end_date`

### Error: "Validation error: Symbol is required"

**Exception**: `ValidationError`

**Error Message**:

```
Validation error: Symbol is required
```

or

```
Validation error for 'symbol': Invalid symbol format
```

**Cause**: An empty or invalid stock symbol was provided. Symbols must be 1-12 uppercase alphanumeric characters (may include dots, hyphens, and equals signs for special symbols).

**Solution**:

```
# Valid symbols
AAPL          # US stocks
BTC-USD       # Cryptocurrencies
USDJPY=X      # Forex pairs
VOO           # ETFs
```

**Prevention Tips**:

- Verify the ticker symbol exists on Yahoo Finance or your exchange
- Use uppercase letters
- For crypto, use the `-USD` suffix (e.g., `BTC-USD`)
- For forex, use the `=X` suffix (e.g., `USDJPY=X`)

---

## 3. IB Flex Query API Errors

### Error: "IB API error: Statement not yet ready"

**Exception**: `FlexQueryAPIError` (from API client) / `APIError` (from MCP layer)

**Error Message**:

```
IB API error: Statement not yet ready
```

or

```
Statement not ready after 3 attempts
```

**Cause**: The IB Flex Query API generates statements asynchronously. When a request is submitted, IB needs time to prepare the data. The API returns "Statement generation in progress" while processing. The client automatically retries up to 3 times with a 5-second delay between attempts (configurable via `api_max_retries` and `api_retry_delay`).

**API Workflow**:

1. **SendRequest** to `https://ndcdyn.interactivebrokers.com/.../SendRequest` -- returns a `ReferenceCode`
2. **GetStatement** to `https://gdcdyn.interactivebrokers.com/.../GetStatement` -- returns XML data or "in progress"
3. If still processing, retry after delay (default: 5 seconds, up to 3 retries)

**Solution**:

```bash
# Wait a few minutes and retry
ib-sec-fetch --start-date 2025-01-01 --end-date 2025-10-05

# Reduce the date range for faster processing
ib-sec-fetch --start-date 2025-09-01 --end-date 2025-10-05

# If persistent, check IB Account Management portal to verify Flex Query status
```

**Prevention Tips**:

- Use smaller date ranges when possible
- Avoid requesting data during IB system maintenance windows (typically weekends)
- Check the IB status page for service outages
- The default retry configuration (3 retries, 5s delay) works well for most cases

### Error: "SendRequest failed: ..."

**Exception**: `FlexQueryAPIError`

**Error Message**:

```
SendRequest failed: <error_code> - <error_message>
```

**Cause**: The initial request to the IB Flex Query API failed. Common reasons include:

- Invalid `QUERY_ID` or `TOKEN`
- Flex Query not configured in IB Account Management
- IB API service outage

**Solution**:

1. Verify your `QUERY_ID` and `TOKEN` are correct
2. Log in to IB Account Management and confirm your Flex Query is configured
3. Check that the Flex Query includes the required sections (Account Information, Cash Report, Open Positions, Trades)

---

## 4. Yahoo Finance Errors

### Error: "Yahoo Finance API error: No data found for SYMBOL"

**Exception**: `YahooFinanceError`

**Error Message**:

```
Yahoo Finance API error: No data found for SYMBOL
```

**Cause**: The Yahoo Finance API (`yfinance` library) could not find data for the specified symbol. This can occur because:

- The ticker symbol is incorrect or misspelled
- The security is not listed on exchanges supported by Yahoo Finance
- The symbol represents a bond or STRIPS (not available on Yahoo Finance)
- The time period requested has no available data
- Yahoo Finance API is temporarily unavailable

**Solution**:

```bash
# Verify the symbol on Yahoo Finance website first
# https://finance.yahoo.com/quote/AAPL

# For bonds and STRIPS, use the IB portfolio analysis tools instead
# (they work with IB data directly, not Yahoo Finance)

# Try a different period if data is unavailable for the requested range
```

**Prevention Tips**:

- Bond-only portfolios will not work with Yahoo Finance tools (`calculate_portfolio_metrics`, `analyze_portfolio_correlation`)
- Use IB portfolio analysis tools (`analyze_performance`, `analyze_bonds`) for bond analysis
- Check symbol validity before running analysis

---

## 5. Timeout Errors

### Error: "Timeout: IB API call timed out after 60 seconds"

**Exception**: `IBTimeoutError`

**Error Message**:

```
Timeout during 'fetch_statement': IB API call timed out after 60 seconds
```

or

```
Timeout: Operation timed out
```

**Cause**: The API request did not complete within the configured timeout period (default: 30 seconds). This can happen due to:

- Slow or unstable internet connection
- IB API server under heavy load
- Very large date ranges generating large statements
- Network firewall or proxy interference

**Solution**:

```bash
# 1. Check your internet connection
ping ndcdyn.interactivebrokers.com

# 2. Reduce the date range
ib-sec-fetch --start-date 2025-09-01 --end-date 2025-10-05

# 3. Try again during off-peak hours (IB API is busiest during US market hours)

# 4. If using programmatic access, increase the timeout
client = FlexQueryClient(
    query_id="...",
    token="...",
    timeout=60,        # Increase from default 30s
    max_retries=5,     # Increase from default 3
    retry_delay=10,    # Increase from default 5s
)
```

**Prevention Tips**:

- Use cached data when possible (reuse previously fetched XML files)
- Fetch data in smaller date ranges and combine results
- Schedule data fetches during off-peak hours
- Monitor network stability

---

## 6. MCP Connection Errors

### Error: Claude Desktop cannot connect to MCP server

**Symptoms**:

- Claude Desktop shows "MCP server not available"
- Tools from `ib-sec-mcp` are not listed in Claude Desktop
- Connection timeout when trying to use IB Analytics tools

**Cause**: The MCP server is not running, misconfigured, or the Python environment does not match. Common issues include:

- Wrong Python path in `claude_desktop_config.json`
- Server not installed (`pip install -e ".[mcp]"` not run)
- Port conflict or permission issue
- Missing environment variables in the MCP config

**Solution**:

1. **Verify the config file** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "ib-sec-mcp": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "ib_sec_mcp.mcp.server"],
      "env": {
        "QUERY_ID": "your_query_id",
        "TOKEN": "your_token"
      }
    }
  }
}
```

2. **Check the Python path**:

```bash
# Find the correct Python path for your virtual environment
which python
# or
/path/to/your/venv/bin/python --version

# Verify the module is importable
/path/to/your/venv/bin/python -c "import ib_sec_mcp.mcp.server; print('OK')"
```

3. **Test the server manually**:

```bash
# Start the server directly to check for errors
IB_DEBUG=1 /path/to/your/venv/bin/python -m ib_sec_mcp.mcp.server
```

4. **Check for missing MCP dependencies**:

```bash
pip install -e ".[mcp]"
# This installs fastmcp and other MCP-related dependencies
```

**Prevention Tips**:

- Always use the full absolute path to the Python binary (not `python3` or a relative path)
- Verify the virtual environment has the `mcp` extras installed
- Test the server manually before configuring Claude Desktop
- Check Claude Desktop logs for detailed error messages

---

## 7. XML Parsing Errors

### Error: Invalid XML from IB API

**Exception**: `FlexQueryAPIError` or `defusedxml.ElementTree.ParseError`

**Error Message**:

```
Failed to parse XML response: <parse error details>
```

or

```
Invalid data format. Only XML format is supported.
```

**Cause**: The data received from the IB API is not valid XML. This can happen when:

- The IB API returns an HTML error page instead of XML data (e.g., 500 Internal Server Error, maintenance page)
- The response was truncated due to network issues
- The file being loaded is corrupted or not an IB Flex Query export
- CSV data was provided instead of XML (CSV support has been removed)

**Important**: The parser uses `defusedxml` for secure XML parsing, which prevents XML entity expansion attacks and other XML-based security vulnerabilities.

**Solution**:

```bash
# 1. Verify the file is valid XML
head -5 data/raw/your_file.xml
# Should start with: <?xml version="1.0"?> or <FlexQueryResponse>

# 2. Re-fetch the data
ib-sec-fetch --start-date 2025-01-01 --end-date 2025-10-05

# 3. If using a saved file, check for corruption
xmllint --noout data/raw/your_file.xml  # requires libxml2

# 4. Check the detect_format() validation
# The parser requires the first line to start with '<'
```

**Prevention Tips**:

- Always use the `ib-sec-fetch` CLI or `fetch_ib_data` MCP tool to fetch data (they handle format validation)
- Do not manually edit XML files
- Check file integrity after downloads
- CSV format is no longer supported; if you have CSV data, re-export from IB as XML via Flex Query

---

## 8. Multi-Account Data Issues

### Error: Account ID is "UNKNOWN" or missing

**Symptoms**:

- Account ID appears as `"UNKNOWN"` in analysis results
- Accounts are skipped during parsing
- `to_accounts()` returns fewer accounts than expected

**Cause**: The FlexStatement XML element does not contain an `accountId` attribute, or the `AccountInformation` section is missing. This happens when:

- The Flex Query is not configured to include the Account Information section
- The API returned partial data due to an error
- The XML structure is malformed

**How Multi-Account Parsing Works**:

```xml
<!-- A single Flex Query can return data for multiple accounts -->
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1234567" ...>
      <AccountInformation accountId="U1234567" acctAlias="Main" />
      <!-- positions, trades, cash for this account -->
    </FlexStatement>
    <FlexStatement accountId="U7654321" ...>
      <AccountInformation accountId="U7654321" acctAlias="IRA" />
      <!-- positions, trades, cash for this account -->
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>
```

- `XMLParser.to_accounts()` parses all `FlexStatement` elements and returns a `dict[str, Account]`
- `XMLParser.to_account()` parses a specific account by `account_id` (or the first account if not specified)
- Accounts with `accountId="UNKNOWN"` are skipped by `to_accounts()`

**Solution**:

1. **Verify your Flex Query configuration in IB Account Management**:
   - Ensure the "Account Information" section is included
   - Ensure all desired accounts are selected in the query

2. **Check the raw XML**:

```bash
# Look for accountId attributes
grep -o 'accountId="[^"]*"' data/raw/your_file.xml
```

3. **Use the CLI with split-accounts flag**:

```bash
ib-sec-fetch --split-accounts --start-date 2025-01-01 --end-date 2025-10-05
```

**Prevention Tips**:

- Always include the "Account Information" section in your Flex Query
- Test your Flex Query in IB Account Management before using it programmatically
- Use `--split-accounts` when fetching multi-account data to save separate files per account

---

## 9. Bond Data Gaps

### Error: Missing bond maturity date or bond-specific fields

**Symptoms**:

- `maturity_date` is `None` for bond positions
- Bond-specific fields (`coupon_rate`, `ytm`, `duration`) are `None`
- Bond analysis produces incomplete results

**Cause**: Bond data from IB Flex Query may have incomplete fields:

- **`maturity_date`**: The `maturity` attribute may be missing from `OpenPosition` elements for certain bond types
- **`coupon_rate`**: The `coupon` attribute may be absent for zero-coupon bonds (STRIPS) or if not included in the Flex Query configuration
- **`ytm` (Yield to Maturity)**: Not provided by IB; calculated by the `BondAnalyzer` when maturity date and price are available
- **`duration`**: Also calculated rather than provided by IB

**Solution**:

```python
# Bond fields are Optional in the Position model
# Always check for None before using them
position = account.positions[0]

if position.maturity_date is not None:
    # Safe to use maturity_date
    years_to_maturity = (position.maturity_date - date.today()).days / 365.25
else:
    # Handle missing maturity date
    print(f"Warning: No maturity date for {position.symbol}")
```

**Prevention Tips**:

- Configure your Flex Query to include bond-specific fields (maturity, coupon)
- Use the `BondAnalyzer` which handles missing data gracefully
- Be aware that Yahoo Finance does not have data for most bonds (especially STRIPS)
- For bond analysis, always use IB portfolio tools rather than Yahoo Finance tools

---

## 10. Decimal and Type Errors

### Error: Decimal InvalidOperation or float precision issues

**Exception**: `decimal.InvalidOperation` or unexpected calculation results

**Error Message**:

```
decimal.InvalidOperation: [<class 'decimal.InvalidOperation'>]
```

or subtle precision errors in financial calculations.

**Cause**: Financial calculations in IB Analytics must use Python's `Decimal` type, never `float`. Common issues include:

- Parsing non-numeric strings (e.g., `""`, `"N/A"`, `"--"`) as `Decimal`
- Using `float` intermediary values that lose precision
- Initializing `Decimal` from `float` instead of `str` (e.g., `Decimal(0.1)` vs `Decimal("0.1")`)

**How the Codebase Handles This**:

The `parse_decimal_safe()` utility function in `ib_sec_mcp/utils/validators.py` safely handles non-numeric values:

```python
from ib_sec_mcp.utils.validators import parse_decimal_safe

# Safe parsing - returns 0.0 for invalid input
value = parse_decimal_safe("not_a_number")  # Returns 0.0
value = parse_decimal_safe("")               # Returns 0.0
value = parse_decimal_safe(None)             # Returns 0.0
value = parse_decimal_safe("1,234.56")       # Returns 1234.56 (commas removed)
```

All parsed values are then wrapped in `Decimal()` for precise financial math:

```python
from decimal import Decimal

# Correct: string literal initialization
price = Decimal("100.50")
quantity = Decimal("10")
total = price * quantity  # Decimal("1005.00") - exact

# Wrong: float initialization (loses precision)
price = Decimal(100.50)  # Decimal('100.5') - may have hidden precision issues
```

**Solution**:

- If you see `InvalidOperation`, check that all input strings are numeric before creating `Decimal` objects
- Use `parse_decimal_safe()` for any values coming from XML attributes
- Always initialize `Decimal` from string literals, not floats

**Prevention Tips**:

- Follow the codebase convention: `Decimal(parse_decimal_safe(value))`
- Never use `float()` for financial calculations
- Run `mypy` to catch type mismatches: `mypy ib_sec_mcp`
- See the [Calculation Error Prevention Strategy](./calculation_error_prevention_strategy.md) for architectural details

---

## 11. Permission and File Errors

### Error: Data directory not writable or .env file not found

**Exception**: `FileOperationError` or `PermissionError`

**Error Message**:

```
FileOperationError: Cannot write to data directory
```

or

```
PermissionError: [Errno 13] Permission denied: 'data/raw/...'
```

**Cause**: The application cannot read from or write to the required directories. The following paths are used (configurable in `.env`):

| Environment Variable | Default Path      | Purpose                      |
| -------------------- | ----------------- | ---------------------------- |
| `DATA_DIR`           | `data/`           | Root data directory          |
| `RAW_DATA_DIR`       | `data/raw/`       | Raw XML files from IB API    |
| `PROCESSED_DATA_DIR` | `data/processed/` | Processed results, SQLite DB |

**Solution**:

```bash
# 1. Create the directories manually
mkdir -p data/raw data/processed

# 2. Fix permissions
chmod 755 data data/raw data/processed

# 3. Or configure custom paths in .env
echo 'DATA_DIR=/path/to/custom/data' >> .env
echo 'RAW_DATA_DIR=/path/to/custom/data/raw' >> .env
echo 'PROCESSED_DATA_DIR=/path/to/custom/data/processed' >> .env
```

**Note**: The `Config` class automatically creates directories on startup via the `create_directories` validator. If directory creation fails, it usually indicates a permission issue with the parent directory.

**File Size Limits**: The MCP server enforces a maximum file size of **10 MB** for uploaded data files. If your XML export exceeds this, try reducing the date range.

**Allowed File Extensions**: Only `.csv` and `.xml` files are accepted by the file validator (though only XML is supported for parsing).

**Prevention Tips**:

- Run the application from the project root directory
- Ensure the user running the application has write permissions to the data directories
- For Docker, mount the data volume with appropriate permissions: `-v $(pwd)/data:/app/data`
- Never store data files in the git repository (they are gitignored)

---

## 12. Import Errors

### Error: Missing optional dependencies

**Exception**: `ImportError` or `ModuleNotFoundError`

**Error Message**:

```
ModuleNotFoundError: No module named 'fastmcp'
```

or

```
ImportError: cannot import name 'yfinance' from ...
```

**Cause**: IB Analytics has optional dependency groups that must be installed separately. The core package installs only essential dependencies.

**Dependency Groups**:

| Install Command                             | What It Includes                                     |
| ------------------------------------------- | ---------------------------------------------------- |
| `pip install -e .`                          | Core: requests, pandas, pydantic, httpx, rich, typer |
| `pip install -e ".[mcp]"`                   | + fastmcp (MCP server)                               |
| `pip install -e ".[dev]"`                   | + pytest, mypy, ruff, pre-commit                     |
| `pip install -e ".[visualization]"`         | + matplotlib, plotly (charts)                        |
| `pip install -e ".[dev,mcp,visualization]"` | All optional dependencies                            |

**Solution**:

```bash
# Install all optional dependencies
pip install -e ".[dev,mcp,visualization]"

# Or install only what you need
pip install -e ".[mcp]"       # For MCP server only
pip install -e ".[dev]"       # For development only
```

**Common Missing Dependencies**:

| Module       | Required For              | Install Group   |
| ------------ | ------------------------- | --------------- |
| `fastmcp`    | MCP server                | `mcp`           |
| `yfinance`   | Yahoo Finance market data | core (included) |
| `defusedxml` | Secure XML parsing        | core (included) |
| `pytest`     | Running tests             | `dev`           |
| `mypy`       | Type checking             | `dev`           |
| `ruff`       | Linting and formatting    | `dev`           |
| `matplotlib` | Charts and visualizations | `visualization` |

**Prevention Tips**:

- Use `pip install -e ".[dev,mcp,visualization]"` for a complete development setup
- Check `pyproject.toml` for the full dependency list
- Create a virtual environment to isolate dependencies: `python -m venv .venv && source .venv/bin/activate`
- Verify installation: `python -c "import ib_sec_mcp; print(ib_sec_mcp.__name__)"`

---

## Debug Mode

For detailed error information during development, enable debug mode:

```bash
# Set environment variable
export IB_DEBUG=1

# Run any command with debug output
ib-sec-fetch --start-date 2025-01-01 --end-date 2025-10-05

# Or for the MCP server
IB_DEBUG=1 ib-sec-mcp
```

Debug mode provides:

- Detailed exception stack traces
- API request/response logging (with credentials masked)
- Parser processing details
- Configuration loading status

**Warning**: Never enable debug mode in production as it may expose internal error details.

---

## Exception Hierarchy Reference

### MCP Layer Exceptions (`ib_sec_mcp/mcp/exceptions.py`)

All MCP exceptions inherit from `ToolError` (via `IBAnalyticsError`) and are visible to MCP clients:

```
IBAnalyticsError (base)
  +-- ValidationError          # Input validation failures
  +-- APIError                 # IB API failures (with optional status_code)
  +-- DataNotFoundError        # Requested data not found
  +-- FileOperationError       # File read/write failures
  +-- ConfigurationError       # Missing or invalid configuration
  +-- IBTimeoutError           # Operation timeouts (with optional operation name)
  +-- YahooFinanceError        # Yahoo Finance API failures
```

### API Client Exceptions (`ib_sec_mcp/api/client.py`)

Used internally by the Flex Query API client:

```
FlexQueryError (base)
  +-- FlexQueryAPIError        # API request/response errors
  +-- FlexQueryValidationError # Data validation errors
```

---

## Getting Help

If you cannot resolve an issue using this guide:

1. **Check the README**: [README.md](../README.md) for setup and usage instructions
2. **Check INSTALL.md**: [INSTALL.md](../INSTALL.md) for installation-specific guidance
3. **Enable debug mode**: Set `IB_DEBUG=1` for detailed error information
4. **Check IB documentation**: [IB Flex Query documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/flex-web-service/)
5. **Review the data format**: [IB Flex Query Data Format](./csv-format.md) for XML structure details
6. **File an issue**: Open a GitHub issue with the error message, debug output, and steps to reproduce
