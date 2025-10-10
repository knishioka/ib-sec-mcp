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

### Quick Start with Docker

```bash
# Build image
docker build -t ib-sec-mcp .

# Run with environment variables
docker run -it --rm \
  -e QUERY_ID=your_query_id \
  -e TOKEN=your_token \
  -v $(pwd)/data:/app/data \
  ib-sec-mcp

# Or use docker-compose
docker-compose up
```

### Docker Compose

Create `.env` file:
```env
QUERY_ID=your_query_id
TOKEN=your_token
IB_DEBUG=0
```

Run:
```bash
# Start server
docker-compose up -d

# View logs
docker-compose logs -f

# Stop server
docker-compose down

# Run tests
docker-compose --profile test run test
```

### Docker Security Features

- **Non-root user**: Runs as `mcpuser` (UID 1000)
- **Read-only filesystem**: Root filesystem is read-only
- **Resource limits**: CPU (2 cores) and memory (2GB) limits
- **No new privileges**: Prevents privilege escalation
- **Data persistence**: Data stored in mounted volume

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

## Investment Analysis Tools (MCP)

IB Analytics provides advanced investment analysis tools through the MCP server. These tools integrate Yahoo Finance data for comprehensive market analysis.

### Stock & Fund Analysis

#### `get_stock_info` - Comprehensive Stock Information
Get detailed information about stocks, ETFs, and funds including fundamental metrics.

**Features**:
- Real-time price data (current, open, high, low, volume)
- Valuation metrics (P/E, P/B, P/S, PEG, EV/EBITDA, EV/Revenue)
- Profitability metrics (profit margin, ROE, ROA, operating margin, EPS)
- Financial health (total cash, debt, debt-to-equity, current/quick ratios, FCF)
- Growth metrics (revenue growth, earnings growth)
- Dividend information (yield, ex-date, payment date)
- Trading information (52-week high/low, market cap, volume)

**Example Usage**:
```python
# In Claude Desktop with MCP
"Show me comprehensive information for AAPL stock"
```

#### `get_current_price` - Quick Price Check
Get current price and key metrics for quick market checks.

**Example Usage**:
```python
"What's the current price of VOO?"
```

#### `get_stock_data` - Historical Price Data with Technical Indicators
Fetch OHLCV data with optional technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands).

**Example Usage**:
```python
"Get 1-year daily price data for SPY with SMA 20, SMA 50, and RSI"
```

### Comparative Analysis

#### `compare_with_benchmark` - Performance vs Benchmark
Compare stock/fund performance against a benchmark (default: SPY).

**Features**:
- Return comparison (total return, annualized return)
- Volatility analysis (standard deviation comparison)
- Risk metrics (beta, alpha, correlation)
- Risk-adjusted returns (Sharpe ratio comparison)
- Interpretation and insights

**Example Usage**:
```python
# Compare VOO against SPY over 1 year
"Compare VOO performance with SPY benchmark"

# Compare with custom benchmark over 2 years
"Compare AAPL with QQQ benchmark over 2y period"
```

#### `get_analyst_consensus` - Analyst Ratings & Target Prices
Get analyst recommendations, target prices, and earnings estimates.

**Features**:
- Rating distribution (strong buy/buy/hold/sell/strong sell)
- Consensus rating derived from distribution
- Target prices (mean, median, high, low)
- Upside potential percentage
- Earnings estimates (date, EPS range, revenue estimates)

**Example Usage**:
```python
"What's the analyst consensus for TSLA?"
```

### Portfolio-Level Analysis

#### `calculate_portfolio_metrics` - Advanced Portfolio Metrics
Calculate comprehensive risk-adjusted performance metrics for your portfolio.

**Features**:
- **Return metrics**: Total return, annualized return, volatility
- **Risk-adjusted ratios**:
  - Sharpe Ratio: Risk-adjusted return (excess return / total risk)
  - Sortino Ratio: Downside risk-adjusted return
  - Calmar Ratio: Return / maximum drawdown
  - Treynor Ratio: Excess return / systematic risk (beta)
  - Information Ratio: Excess return / tracking error
- **Risk metrics**:
  - Maximum drawdown (largest peak-to-trough decline)
  - Downside deviation (volatility of negative returns)
  - Beta (systematic risk vs benchmark)
  - Tracking error (deviation from benchmark)
  - Alpha (excess return vs expected return)

**Parameters**:
- `csv_path`: Path to IB Flex Query CSV file
- `benchmark`: Benchmark symbol (default: "SPY")
- `risk_free_rate`: Annual risk-free rate (default: 0.05 = 5%)
- `period`: Time period for analysis (1mo, 3mo, 6mo, 1y, 2y, 5y)

**Example Usage**:
```python
# Analyze portfolio with default settings (SPY benchmark, 5% risk-free rate, 1 year)
"Calculate portfolio metrics for my latest data file"

# Analyze with custom benchmark and 2-year period
"Calculate portfolio metrics using QQQ as benchmark over 2 years"
```

**Limitations**:
- ⚠️ Requires Yahoo Finance data for portfolio positions
- ⚠️ Will not work for bond-only portfolios (STRIPS bonds have no Yahoo Finance data)
- ✅ Works well for stock and ETF portfolios

#### `analyze_portfolio_correlation` - Diversification Analysis
Analyze correlation between portfolio positions to assess diversification.

**Features**:
- Correlation matrix between all positions
- High correlation pairs identification (|r| > 0.7)
- Portfolio beta vs benchmark (default: SPY)
- Diversification score (0-100)
- Position weights in portfolio
- Interpretation and recommendations

**Parameters**:
- `csv_path`: Path to IB Flex Query CSV file
- `period`: Time period for correlation analysis (1mo, 3mo, 6mo, 1y, 2y, 5y)

**Example Usage**:
```python
# Analyze correlation over 1 year (default)
"Analyze the correlation between my portfolio positions"

# Analyze over 6 months
"Analyze portfolio correlation over the last 6 months"
```

**Limitations**:
- ⚠️ Requires Yahoo Finance data for portfolio positions
- ⚠️ Will not work for bond-only portfolios
- ✅ Best for analyzing stock/ETF portfolio diversification

### Options Analysis

#### `get_options_chain` - Options Data
Get calls and puts data for a stock including strike prices, volume, open interest, and implied volatility.

#### `calculate_put_call_ratio` - Market Sentiment
Calculate put/call ratio based on open interest or volume to gauge market sentiment.

**Example Usage**:
```python
# Calculate P/C ratio based on open interest
"What's the put/call ratio for SPY?"

# Calculate based on volume
"Calculate put/call ratio for QQQ based on volume"
```

### News & Market Intelligence

#### `get_stock_news` - Latest News Articles
Get the latest news articles for any stock symbol from Yahoo Finance.

**Features**:
- Latest news articles (up to 50)
- Article metadata (title, publisher, publish time, summary)
- Direct links to full articles
- Thumbnail images for visual context
- Related ticker symbols
- Multiple content types (stories, videos, press releases)

**Parameters**:
- `symbol`: Stock ticker symbol (e.g., "AAPL", "TSLA", "QQQ")
- `limit`: Number of articles to return (default: 10, max: 50)

**Example Usage**:
```python
# Get latest 5 news articles for Apple
"Show me the latest news for AAPL"

# Get 10 news articles for Tesla
"What's the latest news about TSLA stock?"

# Get news for an ETF
"Get recent news articles for QQQ"
```

**Response Includes**:
- **Title**: Article headline
- **Publisher**: News source (e.g., Yahoo Finance, Bloomberg, Reuters)
- **Link**: Direct URL to full article
- **Publish Time**: When the article was published (ISO 8601 format)
- **Summary**: Brief article summary or description
- **Type**: Content type (STORY, VIDEO, etc.)
- **Thumbnail**: Image URL for articles with visuals
- **Related Tickers**: Other stocks mentioned in the article

**Use Cases**:
- **Investment Research**: Stay updated on company news and developments
- **Market Sentiment**: Gauge market sentiment from news coverage
- **Due Diligence**: Research companies before making investment decisions
- **Portfolio Monitoring**: Track news for holdings in your portfolio
- **Event-Driven Trading**: Identify market-moving events quickly

**Example Natural Language Queries**:
```
"What's the latest news about Apple?"
"Show me recent news articles for my Tesla position"
"Get the latest 3 news stories for SPY"
"What are people saying about NVIDIA in the news?"
"Show me news for all my tech holdings: AAPL, MSFT, GOOGL"
```

### Usage Examples in Claude Desktop

Once you've set up the MCP server in Claude Desktop, you can use natural language:

```
"Show me detailed information for AAPL including all fundamental metrics"

"Compare my portfolio performance against the S&P 500 over the last year"

"What's the correlation between positions in my portfolio? Are they well diversified?"

"Calculate comprehensive risk-adjusted metrics for my portfolio"

"What do analysts think about TSLA? Show me the consensus and target prices"

"How does VOO compare to SPY over the last 2 years?"
```

### Technical Notes

**Data Sources**:
- Portfolio data: Interactive Brokers Flex Query (CSV/XML)
- Market data: Yahoo Finance via yfinance library
- Real-time quotes: Yahoo Finance delayed quotes (15-20 minutes)

**Performance Metrics Definitions**:
- **Sharpe Ratio**: (Return - Risk-free rate) / Volatility. Higher is better. >1 is good, >2 is excellent.
- **Sortino Ratio**: Like Sharpe but only penalizes downside volatility. Better for asymmetric returns.
- **Calmar Ratio**: Annualized return / Maximum drawdown. Measures return per unit of downside risk.
- **Treynor Ratio**: (Return - Risk-free rate) / Beta. Measures return per unit of systematic risk.
- **Information Ratio**: (Portfolio return - Benchmark return) / Tracking error. Measures active management skill.
- **Beta**: Systematic risk relative to benchmark. 1.0 = same risk as benchmark, >1.0 = more volatile.
- **Alpha**: Excess return vs expected return (CAPM). Positive alpha = outperformance after risk adjustment.
- **Maximum Drawdown**: Largest peak-to-trough decline. Key risk metric for understanding worst-case scenarios.

**Correlation Interpretation**:
- |r| > 0.7: High correlation (limited diversification benefit)
- 0.3 < |r| < 0.7: Moderate correlation (some diversification)
- |r| < 0.3: Low correlation (good diversification)
- Negative correlation: Positions move in opposite directions (excellent diversification)

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

- **16 Tools**:
  - IB Portfolio: Fetch data, performance/cost/bond/tax/risk analysis, portfolio summary
  - Stock Analysis: Stock info, current price, historical data, options chain, put/call ratio, news
  - Investment Analysis: Benchmark comparison, portfolio metrics, correlation analysis, analyst consensus
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

# Code formatting with Ruff
ruff format ib_sec_mcp tests

# Linting with Ruff
ruff check --fix ib_sec_mcp tests

# Type checking with mypy
mypy ib_sec_mcp
# Note: Type checking is configured to check core modules only
# MCP server code is excluded due to external dependencies

# Run all pre-commit hooks manually
pre-commit run --all-files

# Run mypy type checking manually (warning mode only)
pre-commit run mypy --hook-stage manual --all-files
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
- **yfinance** (0.2.40+): Yahoo Finance data integration
- **fastmcp** (2.0.0+): Model Context Protocol server framework

## Security

### MCP Server Security

The IB Analytics MCP server implements security best practices:

- **Error Masking**: Internal error details are masked from clients (configurable with `IB_DEBUG=1`)
- **Input Validation**: All inputs are validated before processing
- **File Path Protection**: Path traversal attacks are prevented
- **File Size Limits**: Maximum file size: 10MB
- **Timeout Protection**: All operations have timeout limits
- **Retry Logic**: Automatic retry for transient errors (max 3 attempts)

### Debug Mode

Enable debug mode for detailed error information (development only):

```bash
# Set environment variable
export IB_DEBUG=1

# Run MCP server
ib-sec-mcp
```

**Warning**: Never enable debug mode in production as it exposes internal error details.

### Credentials Security

- **Never commit** `.env` files to version control
- Store credentials in environment variables or secure secret management systems
- Use separate credentials for development and production
- Regularly rotate API tokens

## Troubleshooting

### Common Issues

#### 1. "Configuration error: Failed to load credentials"

**Problem**: QUERY_ID or TOKEN not found in environment

**Solution**:
```bash
# Create .env file
echo "QUERY_ID=your_query_id" > .env
echo "TOKEN=your_token" >> .env

# Or set environment variables
export QUERY_ID=your_query_id
export TOKEN=your_token
```

#### 2. "Validation error for 'start_date': Invalid date format"

**Problem**: Date format is incorrect

**Solution**: Use YYYY-MM-DD format
```bash
ib-sec-fetch --start-date 2025-01-01 --end-date 2025-12-31
```

#### 3. "IB API error: Statement not yet ready"

**Problem**: IB Flex Query is still processing

**Solution**: The server automatically retries (up to 3 times). If it still fails, wait a few minutes and try again.

#### 4. "Yahoo Finance API error: No data found for SYMBOL"

**Problem**: Invalid stock symbol or no data available

**Solution**:
- Verify the ticker symbol is correct
- Check if the symbol is traded on supported exchanges
- Try a different period or interval

#### 5. "Timeout: IB API call timed out after 60 seconds"

**Problem**: API call took too long

**Solution**:
- Check your internet connection
- Reduce the date range
- Try again during off-peak hours

### Testing

Run tests to verify your installation:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=ib_sec_mcp --cov-report=html
```

### MCP Server Testing

Test the MCP server connection:

```bash
# Start server in debug mode
IB_DEBUG=1 ib-sec-mcp

# Check logs in stderr for connection issues
```

### Performance Optimization

If experiencing slow performance:

1. **Reduce date ranges**: Fetch smaller time periods
2. **Use file caching**: Reuse previously fetched data
3. **Limit technical indicators**: Only request needed indicators
4. **Parallel processing**: Use async operations where possible

## License

MIT

## Author

Kenichiro Nishioka

## Support

For issues and questions, please check the [IB Flex Query documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/flex-web-service/).
