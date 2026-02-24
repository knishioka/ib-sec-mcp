# IB Analytics

Interactive Brokers portfolio analytics library with **AI-powered investment analysis** and **development automation**.

## 🎯 What This Does

**For Investors** (Mode 1 & 3):

- ⚡ **95% faster investment strategy** generation (6-8 hours → 15-20 minutes)
- 📊 **Parallel market analysis** of all holdings simultaneously
- 🎯 **Consolidated multi-account view** with accurate portfolio metrics
- 📈 **Professional options strategies** with specific strikes, Greeks, and Max Pain
- 💰 **Tax-optimized execution plans** across multiple accounts
- 📉 **Multi-timeframe technical analysis** with entry/exit signals

**For Developers** (Mode 3):

- 🤖 **90% faster issue resolution** (80 minutes → 8 minutes via `/resolve-gh-issue`)
- ✅ **Automated quality gates** (black, ruff, mypy, pytest)
- 🔄 **Complete TDD workflow** (tests → code → PR automation)
- 📝 **Auto-generated PR descriptions** with comprehensive context

**Time Savings Summary**:
| Task | Manual | Automated | Savings |
|------|--------|-----------|---------|
| Investment Strategy | 6-8 hours | 15-20 min | **95%** |
| Stock Analysis | 1-2 hours | 2-3 min | **97%** |
| Options Strategy | 45-60 min | 3-5 min | **93%** |
| Portfolio Analysis | 3-4 hours | 5 min | **95%** |
| GitHub Issue → PR | 80 min | 8 min | **90%** |

## ✨ Key Features

**Investment Analysis**:

- 📊 **Multi-Account Support**: Consolidated analysis across all IB accounts
- 📈 **Market Analysis**: Multi-timeframe technicals, options Greeks, IV metrics, Max Pain
- 💰 **Tax Optimization**: Cross-account tax harvesting and loss optimization
- 🎯 **Options Strategies**: Professional-grade recommendations with specific strikes
- 📉 **Technical Analysis**: Support/resistance, RSI, MACD, volume analysis

**Portfolio Management**:

- 🔄 **Flex Query API Integration**: Automated data fetching via IB Flex Query API v3
- 📈 **Comprehensive Analysis**: Performance, tax, cost, risk, and bond analytics
- 📊 **Position History**: SQLite time-series tracking for historical analysis
- 🎯 **Type-Safe**: Built with Pydantic v2 for robust data validation
- ⚡ **Async Support**: Parallel data fetching for multiple accounts
- 📄 **Rich Reports**: Console, HTML, and optional PDF reporting

**Development Automation** (Mode 3):

- 🤖 **10 Specialized AI Agents**: strategy-coordinator, market-analyst, data-analyzer, + 7 dev agents
- 📋 **15 Slash Commands**: Automated workflows for analysis and development
- ✅ **Quality Gates**: Automated black, ruff, mypy, pytest enforcement
- 🔄 **GitHub Integration**: Issue → Branch → Tests → Code → PR workflow

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

### Market Sentiment Analysis

#### `analyze_market_sentiment` - Multi-Source Sentiment Analysis

Get comprehensive market sentiment from multiple sources: news articles, options market, and technical indicators.

**Features**:

- **News Sentiment**: Sentiment analysis from recent news articles and headlines
- **Options Market Sentiment**: Derived from Put/Call ratios, IV Rank, and Max Pain
- **Technical Sentiment**: Based on RSI, MACD, trend analysis, and support/resistance
- **Composite Sentiment**: Weighted aggregation of all sources with configurable weights
- **Confidence Scoring**: Each sentiment source provides confidence level
- **Key Themes**: Identified sentiment drivers (e.g., "bullish_momentum", "oversold_rsi")
- **Risk Factors**: Highlighted concerns (e.g., "overbought_rsi", "near_resistance")

**Parameters**:

- `symbol`: Stock ticker symbol (e.g., "AAPL", "SPY", "QQQ")
- `sources`: Comma-separated sentiment sources (default: "composite")
  - `"news"`: News article sentiment only
  - `"options"`: Options market sentiment only
  - `"technical"`: Technical indicator sentiment only
  - `"composite"`: All sources combined (recommended)

**Sentiment Score Range**: -1.0 (very bearish) to +1.0 (very bullish)

**Example Usage**:

```python
# Get composite sentiment from all sources
"Analyze market sentiment for AAPL using all sources"

# Get only technical sentiment
"What's the technical sentiment for SPY?"

# Get options market sentiment
"Analyze options market sentiment for QQQ"

# News sentiment only
"What's the news sentiment around Tesla?"
```

**Composite Sentiment Weights** (default):

- News Sentiment: 40%
- Options Market Sentiment: 30%
- Technical Sentiment: 30%

**Response Includes**:

- **Overall Score**: Composite sentiment score (-1.0 to +1.0)
- **Confidence**: Aggregated confidence level (0.0 to 1.0)
- **Individual Sources**: Breakdown by news, options, technical with individual scores
- **Key Themes**: Positive sentiment drivers identified across sources
- **Risk Factors**: Warning signs and bearish indicators
- **Reasoning**: Detailed explanation of sentiment calculation
- **Recommendation**: Suggested action (bullish/neutral/bearish stance)

**Sentiment Interpretation Guide**:

| Score Range  | Sentiment    | Interpretation                              | Trading Bias           |
| ------------ | ------------ | ------------------------------------------- | ---------------------- |
| 0.5 to 1.0   | Very Bullish | Strong positive signals across sources      | Strong Buy bias        |
| 0.2 to 0.5   | Bullish      | Positive sentiment with good conviction     | Buy bias               |
| -0.2 to 0.2  | Neutral      | Mixed signals, no clear direction           | Hold, wait for clarity |
| -0.5 to -0.2 | Bearish      | Negative sentiment with moderate conviction | Sell bias              |
| -1.0 to -0.5 | Very Bearish | Strong negative signals across sources      | Strong Sell bias       |

**Confidence Interpretation**:

- **High (0.7-1.0)**: Multiple sources agree, strong signal reliability
- **Medium (0.4-0.7)**: Some agreement, moderate signal reliability
- **Low (0.0-0.4)**: Sources disagree, weak signal reliability

**Key Themes Examples**:

- `bullish_momentum`: Strong upward price movement
- `oversold_rsi`: RSI below 30, potential reversal
- `bullish_options_flow`: Low Put/Call ratio, bullish positioning
- `positive_news_sentiment`: Positive news coverage
- `high_iv_environment`: Elevated volatility, favorable for option sellers

**Risk Factors Examples**:

- `overbought_rsi`: RSI above 70, potential pullback
- `near_resistance`: Price approaching resistance level
- `bearish_macd_cross`: MACD bearish crossover
- `high_put_call_ratio`: Bearish options positioning
- `negative_news_sentiment`: Negative news coverage

**Use Cases**:

- **Entry Timing**: Identify optimal entry points with sentiment confirmation
- **Exit Strategy**: Detect sentiment shifts for position management
- **Risk Assessment**: Gauge market mood before major positions
- **Contrarian Signals**: Identify extreme sentiment for reversal trades
- **Confirmation**: Validate technical/fundamental analysis with sentiment
- **Options Strategy**: Choose premium-selling vs premium-buying based on IV environment

**Example Natural Language Queries**:

```
"What's the overall market sentiment for Apple right now?"
"Analyze sentiment for SPY - should I buy or wait?"
"Is sentiment bullish or bearish for QQQ?"
"Give me composite sentiment analysis for NVDA"
"What are the key sentiment themes for Tesla?"
```

**Integration with Symbol Analysis**:

The sentiment analysis is automatically included when using `/analyze-symbol` command:

```bash
/analyze-symbol AAPL
```

This provides:

- Multi-timeframe technical analysis
- Current price and fundamentals
- Options market analysis
- **Comprehensive sentiment analysis** (news + options + technical)
- Trading recommendation with sentiment-based conviction

**Sentiment Components Breakdown**:

1. **News Sentiment** (40% weight):
   - Analyzes recent news articles and headlines
   - Natural language processing for sentiment extraction
   - Publisher credibility weighting
   - Time decay for article recency

2. **Options Market Sentiment** (30% weight):
   - **Put/Call Ratio**: <0.7 bullish, 0.7-1.3 neutral, >1.3 bearish
   - **IV Rank**: Low IV (buy premium), High IV (sell premium)
   - **Max Pain**: Price gravitation toward max pain strike

3. **Technical Sentiment** (30% weight):
   - **RSI**: <30 oversold (bullish), >70 overbought (bearish)
   - **MACD**: Bullish/bearish crossovers and divergences
   - **Trend Analysis**: Short/medium/long term trend alignment
   - **Support/Resistance**: Price proximity to key levels

**Performance Notes**:

- Composite sentiment calculation: ~2-3 seconds
- Individual source queries: ~1-2 seconds each
- Cached results valid for 5 minutes (real-time market data)
- Concurrent analysis supported for multiple symbols

### Usage Examples in Claude Desktop

Once you've set up the MCP server in Claude Desktop, you can use natural language:

```
"Show me detailed information for AAPL including all fundamental metrics"

"Compare my portfolio performance against the S&P 500 over the last year"

"What's the correlation between positions in my portfolio? Are they well diversified?"

"Calculate comprehensive risk-adjusted metrics for my portfolio"

"What do analysts think about TSLA? Show me the consensus and target prices"

"How does VOO compare to SPY over the last 2 years?"

"Analyze market sentiment for NVDA - should I buy now or wait?"

"What's the composite sentiment for SPY across news, options, and technicals?"

"Is the technical sentiment bullish or bearish for QQQ?"
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

## Usage Modes

IB Analytics supports **three distinct usage modes** for different user types and workflows:

### 1. Claude Desktop (Conversational Analysis) 💬

**Target Users**: Investors, portfolio managers, financial analysts

**Use Case**: Natural language portfolio analysis and investment research

**Setup**: Install MCP server in Claude Desktop configuration

**What You Can Do**:

- **Portfolio Analysis**: "What's my portfolio performance this quarter?"
- **Investment Research**: "Should I buy Apple stock right now?"
- **Tax Planning**: "Show me tax-loss harvesting opportunities"
- **Market Analysis**: "Analyze SPY with options strategies"
- **Investment Strategy**: "Create a comprehensive investment plan"

**Key Benefits**:

- ✅ **Zero coding required** - just ask questions in natural language
- ✅ **Automated data fetching** from Interactive Brokers
- ✅ **Complete analysis** from a single question
- ✅ **Real-time market data** integrated with your portfolio

**Example Workflow**:

```
You: "Analyze my portfolio performance and suggest tax optimization strategies"
Claude: [Fetches latest data, runs performance/tax analysis, provides recommendations]

You: "Should I buy more VOO or switch to VWRA?"
Claude: [Compares ETFs, analyzes portfolio fit, provides specific recommendation]
```

**Time Savings**: 2-3 hours of manual analysis → 2 minutes

---

### 2. Claude Code + MCP (Custom Analysis) 🔧

**Target Users**: Data scientists, quantitative analysts, developers

**Use Case**: Flexible data analysis with composable MCP tools

**Setup**: Use Claude Code with MCP server enabled

**What You Can Do**:

- **Custom Metrics**: Calculate any combination of performance metrics
- **Fine-grained Data**: Access trades, positions, account data directly
- **Period Comparisons**: Compare performance across any date ranges
- **Advanced Analysis**: Build custom strategies and backtests

**Key Benefits**:

- ✅ **Composable tools** - mix and match for custom analysis
- ✅ **Fine-grained control** - filter by symbol, asset class, date range
- ✅ **Programmatic access** - integrate into your own workflows
- ✅ **Strategy resources** - tax context, rebalancing guides, risk analysis

**Example Workflow**:

```python
# Get AAPL trades from Q1
trades = get_trades(symbol="AAPL", start_date="2025-01-01", end_date="2025-03-31")

# Calculate win rate for bond trades
bond_performance = calculate_metric(metric_name="win_rate", asset_class="BOND")

# Compare Q1 vs Q2 performance
comparison = compare_periods(
    period1_start="2025-01-01", period1_end="2025-03-31",
    period2_start="2025-04-01", period2_end="2025-06-30"
)
```

**Time Savings**: 4-5 hours of data extraction and analysis → 15 minutes

---

### 3. Claude Code + Repository (Development Automation) 🚀

**Target Users**: Developers, power users, automation engineers

**Use Case**: Complete development workflow automation with specialized AI agents

**Setup**: Clone repository and use Claude Code in project directory

**What You Can Do**:

#### 📊 Portfolio & Investment Analysis (Slash Commands)

- `/investment-strategy` - **Master command**: Complete investment strategy with portfolio + market analysis
  - **Parallel market analysis**: Analyzes all holdings simultaneously (80-90% time reduction)
  - **Consolidated multi-account view**: True portfolio-level analysis across ALL accounts
  - **2-year chart context** for every position with entry/exit scenarios
  - **Options strategies** with specific strikes and premiums
  - **Tax-optimized execution** plans per account
  - **Actionable priorities**: Urgent (this week) → High (this month) → Medium (this quarter)

- `/analyze-symbol SYMBOL` - Comprehensive symbol analysis (stocks, ETFs, crypto, forex) with multi-timeframe technicals
  - Daily/weekly/monthly trend analysis with confluence scoring
  - Support/resistance levels with entry/exit signals
  - Options market analysis (IV Rank, Greeks, Max Pain) when applicable
  - News sentiment and catalysts
  - **Buy/Sell/Hold rating** with conviction level (1-10)

- `/options-strategy SYMBOL` - Detailed options analysis
  - IV environment assessment (buy vs sell premium)
  - Greeks analysis with risk assessment
  - 2-3 specific strategy recommendations with exact strikes
  - Max profit/loss, breakeven, probability of profit
  - Risk/reward comparison with best strategy selection

- `/optimize-portfolio` - Deep portfolio analysis and recommendations
- `/tax-report --save` - Tax planning with optimization strategies
- `/compare-periods START END START END` - Period-over-period performance comparison

**Time Savings**:

- Investment strategy: 6-8 hours manual research → **15-20 minutes** (95% time reduction)
- Stock analysis: 1-2 hours research → **2-3 minutes** (97% time reduction)
- Options strategy: 45-60 minutes → **3-5 minutes** (93% time reduction)

#### 🤖 AI-Powered Development (7 Specialized Sub-Agents)

**Investment Analysis Agents**:

- **data-analyzer** 📊: Portfolio analysis specialist
  - Consolidated multi-account analysis
  - Performance, tax, cost, risk, bond analytics
  - Time-series position tracking

- **market-analyst** 📈: Stock and options market specialist (NEW!)
  - Multi-timeframe technical analysis
  - Options Greeks, IV metrics, Max Pain calculations
  - Entry/exit timing with scenarios
  - **Parallel execution**: Analyzes 5-10 stocks simultaneously

- **strategy-coordinator** 🎯: Investment strategy orchestrator (NEW!)
  - Integrates portfolio + market analysis
  - Coordinates data-analyzer + market-analyst subagents
  - **Parallel market analysis**: 80-90% time reduction
  - Generates actionable, prioritized recommendations

**Development Agents**:

- **test-runner** 🧪: Testing and quality assurance
- **code-implementer** 💻: Feature implementation with TDD
- **code-reviewer** 📝: Code quality enforcement
- **performance-optimizer** ⚡: Profiling and optimization
- **api-debugger** 🔧: IB API troubleshooting
- **issue-analyzer** 🔍: GitHub issue analysis

**Time Savings**:

- Portfolio analysis: 3-4 hours → **5 minutes** (95% reduction)
- GitHub issue resolution: 80 minutes → **8 minutes** (90% reduction)
- Quality checks: 15 minutes → **2 minutes** (87% reduction)

#### 🔄 Complete Development Workflow Automation

**GitHub Integration**:

```bash
# Resolve GitHub issue with complete automation
/resolve-gh-issue 42

# Automated workflow:
# 1. Analyze issue requirements (issue-analyzer)
# 2. Create failing tests (test-runner, TDD)
# 3. Implement feature (code-implementer)
# 4. Quality checks (code-reviewer: black, ruff, mypy)
# 5. Generate PR with comprehensive description
# 6. Monitor CI checks
# Result: 80 minutes → 8 minutes (90% time savings)
```

**Quality Automation**:

```bash
/quality-check --fix             # Auto-fix format, lint, type, test issues
/test --coverage                 # Run pytest with coverage report
/benchmark --full                # Performance profiling
/add-test performance --analyzer # Generate comprehensive test file
```

**Expected Impact**:

- **Time Savings**: 90% reduction in routine tasks
- **Quality Improvement**: Automated enforcement of best practices
- **Consistency**: Standardized workflows across team
- **Documentation**: Auto-generated PR descriptions and test reports

See [.claude/README.md](.claude/README.md) for complete documentation.

---

## Feature Comparison

| Feature                    | Mode 1: Desktop     | Mode 2: MCP         | Mode 3: Repository                |
| -------------------------- | ------------------- | ------------------- | --------------------------------- |
| **Investment Analysis**    | ✅ Natural language | ✅ Composable tools | ✅ Advanced automation            |
| **Multi-Account Support**  | ✅ Automatic        | ✅ Manual selection | ✅ Consolidated analysis          |
| **Market Analysis**        | ✅ Basic            | ✅ Detailed         | ✅ **Parallel + Advanced**        |
| **Options Strategies**     | ✅ Basic            | ✅ Detailed         | ✅ **Professional-grade**         |
| **Tax Optimization**       | ✅ Recommendations  | ✅ Custom analysis  | ✅ **Multi-account optimization** |
| **Development Tools**      | ❌                  | ❌                  | ✅ 7 AI specialists               |
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

---

## Position History & Time-Series Analysis

IB Analytics automatically stores daily position snapshots in SQLite for historical analysis and time-series tracking.

### Features

- **Automatic Sync**: Positions are automatically saved to SQLite when fetching data via `fetch_ib_data`
- **Historical Tracking**: Query position history over any date range
- **Portfolio Evolution**: Compare portfolio snapshots between two dates
- **Statistical Analysis**: Calculate min/max/average metrics for positions over time
- **Multi-Account Support**: Store and query positions from multiple IB accounts

### Storage Location

Position data is stored in `data/processed/positions.db` (SQLite database).

### Usage

#### Automatic Sync (Recommended)

Position snapshots are automatically saved when fetching data:

```python
# Via MCP tool
await fetch_ib_data(start_date="2025-01-01", end_date="2025-10-15")
# → Automatically syncs positions to SQLite
```

#### Manual Sync

Sync existing XML files to SQLite:

```bash
# Sync single file
python -m ib_sec_mcp.cli.sync_positions --xml-file data/raw/U1234567_2025-01-01_2025-10-15.xml

# Sync all files in directory
python -m ib_sec_mcp.cli.sync_positions --directory data/raw/

# Custom database path
python -m ib_sec_mcp.cli.sync_positions --xml-file data/raw/latest.xml --db-path data/custom.db
```

### Historical Queries (MCP Tools)

#### `get_position_history` - Time Series for a Symbol

Get position history for a specific symbol over a date range:

```python
# In Claude Desktop or Claude Code
"Show me the position history for PG from January to October 2025"

# Programmatic usage
history = await get_position_history(
    account_id="U1234567",
    symbol="PG",
    start_date="2025-01-01",
    end_date="2025-10-15"
)
```

**Returns**: Daily snapshots including quantity, price, value, and P&L for each date.

#### `get_portfolio_snapshot` - Single-Day Portfolio

Get all positions for an account on a specific date:

```python
"What did my portfolio look like on September 1st, 2025?"

# Programmatic usage
snapshot = await get_portfolio_snapshot(
    account_id="U1234567",
    snapshot_date="2025-09-01"
)
```

**Returns**: All positions on that date with values, quantities, and P&L.

#### `compare_portfolio_snapshots` - Portfolio Changes

Compare portfolio composition between two dates:

```python
"Compare my portfolio between September 1st and October 15th, 2025"

# Programmatic usage
comparison = await compare_portfolio_snapshots(
    account_id="U1234567",
    date1="2025-09-01",
    date2="2025-10-15"
)
```

**Returns**:

- Positions added/removed
- Value changes for continuing positions
- Total portfolio value change
- Percentage changes

#### `get_position_statistics` - Statistical Summary

Get min/max/average statistics for a position over time:

```python
"What are the statistics for my PG position over the last 6 months?"

# Programmatic usage
stats = await get_position_statistics(
    account_id="U1234567",
    symbol="PG",
    start_date="2025-04-01",
    end_date="2025-10-15"
)
```

**Returns**: Min/max/average for price, value, and unrealized P&L.

#### `get_available_snapshot_dates` - Available Dates

List all dates with position snapshots for an account:

```python
"What dates do I have position data for?"

# Programmatic usage
dates = await get_available_snapshot_dates(account_id="U1234567")
```

### Use Cases

1. **Performance Tracking**: Monitor how positions perform over time
2. **Rebalancing Analysis**: Identify portfolio drift from target allocations
3. **Tax Planning**: Analyze holding periods and gain/loss trends
4. **Portfolio Evolution**: Visualize how your portfolio composition changes
5. **Risk Management**: Track concentration risk and diversification over time
6. **Historical Analysis**: Backtest strategies against actual position history

### Database Schema

**position_snapshots**: Daily position data per account

- Composite key: (account_id, snapshot_date, symbol)
- Fields: quantity, price, value, cost basis, P&L, bond-specific fields
- Indexes: account+date, symbol+date, date, asset_class

**snapshot_metadata**: Snapshot-level statistics

- Tracks total positions, portfolio value, cash balance per snapshot
- Links to source XML files for audit trail

### Data Integrity

- **Deduplication**: Automatic deduplication via UNIQUE constraints
- **Decimal Precision**: TEXT storage preserves financial calculation precision
- **Transaction Safety**: ACID compliance for data consistency
- **Indexed Queries**: Fast queries via strategic indexes
- **Audit Trail**: Source XML file tracking for each snapshot

---

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

- **22 Tools**:
  - IB Portfolio: Fetch data, performance/cost/bond/tax/risk analysis, portfolio summary
  - Position History: Position history, portfolio snapshots, snapshot comparison, statistics, available dates
  - Stock Analysis: Stock info, current price, historical data, options chain, put/call ratio, news, **market sentiment**
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

See [MCP Tools Reference](docs/mcp-tools-reference.md) for complete documentation of all 38 tools, 9 resources, and 5 prompts.

See [.claude/CLAUDE.md](.claude/CLAUDE.md) for development guide and usage patterns.

## Documentation

| Document                                                                      | Description                                                                                          |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [Architecture](docs/architecture.md)                                          | Data flow diagrams, layer responsibilities, and new feature decision guide                           |
| [Financial Calculators](docs/calculators.md)                                  | Calculation formulas (YTM, duration, Sharpe, Sortino, phantom income) with implementation references |
| [Database Schema](docs/database-schema.md)                                    | SQLite position history schema, indexes, and migration procedures                                    |
| [Calculation Error Prevention](docs/calculation_error_prevention_strategy.md) | ETF calculation accuracy strategy                                                                    |
| [ETF Calculator Usage](docs/etf_calculator_usage_guide.md)                    | ETF calculator usage guide                                                                           |

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
