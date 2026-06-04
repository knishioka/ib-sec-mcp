# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Removed

- **MCP tool consolidation** (#121): reduced redundant MCP tools (62 → 59 tools)
  - `get_portfolio_summary` — removed (deprecated); use `analyze_consolidated_portfolio`
  - `get_news_sentiment` — removed; use `analyze_market_sentiment` (default `sources="news"`)
  - `validate_etf_price_mcp` — removed from MCP surface; demoted to the internal
    `ib_sec_mcp.tools.etf_calculator.validate_etf_price` helper
- **Dead code cleanup** (#120):
  - `ib-sec-report` CLI command and its `cli/report.py` stub (was a "not yet implemented" placeholder; use `ib-sec-analyze --output` instead)
  - Unreachable IV Rank and Max Pain branches in `OptionsSentimentAnalyzer` (behavior unchanged; sentiment is derived solely from the Put/Call ratio)
  - `sync_orders_to_ib()` "Phase 2" stub in `storage/order_sync.py` (no callers)

### Changed

- **`FlexQueryClient`** (#120): extracted duplicated SendRequest XML parsing into a shared `_parse_send_request_response()` helper (no behavior change)

### Fixed

- **Position pagination & connection errors** (#105): `CPClient` now paginates the
  positions endpoint (with a `max_pages` safeguard and warning log) and preserves
  underlying connection errors instead of masking them as empty responses

### Added

- **Live-trading tools via Client Portal Gateway** (#99, #142): CP Gateway-backed
  live order/account/position tools (`get_live_orders`, `get_live_account_balance`,
  `get_live_positions`, etc.), gated behind the `IB_ENABLE_LIVE_TRADING` flag
  (default off) so they are not advertised to MCP clients unless explicitly enabled
- **Limit order management** (#80, #100): limit order management table and MCP tools,
  plus DB sync of locally tracked limit orders against live IB orders via the CP API
- **Daily monitor tools** (#81) and **`/daily-check` command** (#82, #83): reliable
  fetch + sync pipeline for scheduled portfolio monitoring with memory-file
  auto-update rules
- **Earnings calendar MCP tool** (#115): upcoming earnings dates for a given symbol
- **Sentiment Analysis Module** (Phase 1-3): Comprehensive market sentiment analysis (#7)
  - **Base Infrastructure**:
    - `SentimentScore` Pydantic model with Decimal precision
    - `BaseSentimentAnalyzer` abstract base class for pluggable analyzers
  - **News Sentiment Analyzer**:
    - Heuristic-based sentiment from news headlines
    - 6-hour TTL caching for 90% API call reduction
    - Yahoo Finance API integration
  - **Options Sentiment Analyzer**:
    - Put/Call ratio interpretation
    - IV Rank/Percentile analysis
    - Max Pain price analysis
  - **Technical Sentiment Analyzer**:
    - RSI overbought/oversold signals
    - MACD trend momentum
    - Support/resistance levels
    - Multi-timeframe trend analysis
  - **Composite Sentiment Analyzer**:
    - Multi-source aggregation with configurable weights
    - Automatic weight normalization
    - Disagreement penalty for confidence
  - **MCP Tools**:
    - `analyze_market_sentiment` - Multi-source sentiment (news-only via default `sources="news"`)
    - Support for news, options, technical, and composite sources
  - **Quality Assurance**:
    - 67 comprehensive test cases (100% pass rate for Phase 1)
    - Type-safe with mypy strict mode
    - Google-style docstrings

## [0.1.0] - 2025-10-06

### Added

#### Core Infrastructure

- **Project Structure**: Professional Python package structure with `pyproject.toml`
- **Dependency Management**: Latest stable versions (requests 2.32.5, pandas 2.2.3, pydantic 2.10.0)
- **Configuration**: Environment-based config with `.env` support
- **Documentation**: Comprehensive README, INSTALL guide, and inline documentation

#### API Client

- **FlexQueryClient**: IB Flex Query API v3 client
- **Multi-Account Support**: Fetch data from multiple accounts
- **Async Support**: Parallel data fetching with `httpx`
- **Error Handling**: Robust retry logic and error recovery
- **Rate Limiting**: Configurable timeout and retry settings

#### Data Models (Pydantic v2)

- **Trade**: Trading activity with buy/sell, P&L, commissions
- **Position**: Current holdings with unrealized P&L
- **Account**: Account-level data aggregation
- **Portfolio**: Multi-account portfolio aggregation
- **Type Safety**: Full validation and type checking

#### Parsers

- **CSVParser**: Parse IB Flex Query CSV format
- **Multi-Section Support**: Account info, cash, positions, trades
- **XMLParser**: Placeholder for future XML support

#### Analyzers

- **PerformanceAnalyzer**: Win rate, profit factor, ROI metrics
- **CostAnalyzer**: Commission analysis and cost efficiency
- **BondAnalyzer**: Zero-coupon bond analytics (YTM, duration)
- **TaxAnalyzer**: Phantom income (OID) and capital gains tax
- **RiskAnalyzer**: Interest rate scenarios and concentration risk

#### Calculation Engine

- **PerformanceCalculator**: 15+ financial calculations
- **Bond Calculations**: YTM, duration, price sensitivity
- **Tax Calculations**: Phantom income using constant yield method
- **Risk Metrics**: Sharpe ratio, max drawdown, etc.

#### Aggregation

- **MultiAccountAggregator**: Cross-account data aggregation
- **Symbol Aggregation**: Aggregate trades/positions by symbol
- **Asset Class Aggregation**: Group by asset class
- **Account Allocation**: Calculate percentage allocations

#### Reporting

- **ConsoleReport**: Rich console output with tables and formatting
- **BaseReport**: Abstract base for future report types
- **HTML/PDF Support**: Planned for future releases

#### CLI Tools

- **ib-sec-fetch**: Fetch data from IB API
- **ib-sec-analyze**: Run analysis on CSV data
- **ib-sec-report**: Generate reports (placeholder)
- **Rich UI**: Beautiful terminal interface

#### Utilities

- **Config**: Settings management with validation
- **Validators**: CUSIP, ISIN, date, symbol validation
- **Type Converters**: Safe decimal parsing

### Migration

- Moved existing scripts to `legacy/` folder
- Preserved all original functionality
- New modular architecture for better maintainability

### Documentation

- README with quick start guide
- INSTALL guide with examples
- API documentation in docstrings
- Example usage script

## [Unreleased]

### Planned Features

- [ ] Unit tests with pytest
- [ ] HTML report generation
- [ ] PDF report generation with charts
- [ ] XML parser implementation
- [ ] Additional analyzers (Sharpe ratio, max drawdown)
- [ ] Portfolio optimization tools
- [ ] Backtesting framework
- [ ] Real-time data streaming
- [ ] Web dashboard (Streamlit/Dash)
- [ ] Docker containerization
- [ ] CI/CD pipeline

### Known Issues

- XML parsing not yet implemented
- PDF report generation requires additional dependencies
- Some edge cases in date parsing may need handling
- Multi-currency FX rate conversion not fully implemented
