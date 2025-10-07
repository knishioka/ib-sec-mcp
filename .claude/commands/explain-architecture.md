# Explain Architecture

Provide a comprehensive explanation of the IB Analytics library architecture.

## What This Command Does

Explains the system architecture including:
1. Layer architecture and separation of concerns
2. Data flow from API to reports
3. Design patterns used (Factory, Strategy, Template Method)
4. Multi-account aggregation logic
5. Type safety with Pydantic models
6. Extension points for new features

## Architecture Overview

### Layer 1: API Client (`ib_sec_mcp/api/`)
**Purpose**: Communicate with IB Flex Query API
- `client.py`: FlexQueryClient handles HTTP requests
- `models.py`: Pydantic models for API responses
- **Design**: Supports both sync and async operations
- **Multi-Account**: Parallel fetching using asyncio

### Layer 2: Data Models (`ib_sec_mcp/models/`)
**Purpose**: Type-safe domain models
- `trade.py`: Individual trade records
- `position.py`: Current holdings
- `account.py`: Single account aggregation
- `portfolio.py`: Multi-account aggregation
- **Design**: Pydantic v2 for validation and serialization
- **Benefits**: Runtime validation, IDE autocomplete, type safety

### Layer 3: Core Logic (`ib_sec_mcp/core/`)
**Purpose**: Business logic and calculations
- `parsers.py`: CSV/XML to domain models
- `calculator.py`: Financial calculations (15+ functions)
- `aggregator.py`: Multi-account aggregation
- **Design**: Pure functions, no side effects
- **Benefits**: Testable, reusable, composable

### Layer 4: Analyzers (`ib_sec_mcp/analyzers/`)
**Purpose**: Specialized analysis modules
- `base.py`: BaseAnalyzer abstract class (Template Method pattern)
- `performance.py`, `cost.py`, `bond.py`, `tax.py`, `risk.py`
- **Design**: Each analyzer is independent and focused
- **Benefits**: Easy to add new analyzers, single responsibility

### Layer 5: Reports (`ib_sec_mcp/reports/`)
**Purpose**: Format and present analysis results
- `base.py`: BaseReport abstract class
- `console.py`: Rich console output
- Future: `html.py`, `pdf.py`
- **Design**: Strategy pattern for different output formats

### Layer 6: CLI (`ib_sec_mcp/cli/`)
**Purpose**: Command-line interface
- `fetch.py`, `analyze.py`, `report.py`
- **Design**: Typer framework for user-friendly CLI
- **Benefits**: Type-safe arguments, auto-generated help

### Layer 7: Utilities (`ib_sec_mcp/utils/`)
**Purpose**: Cross-cutting concerns
- `config.py`: Environment-based configuration
- `validators.py`: Data validation functions

## Data Flow

```
1. User → CLI Command (ib-sec-fetch)
2. CLI → FlexQueryClient.fetch_statement()
3. API Client → IB Flex Query API (HTTP)
4. API Response → FlexStatement (Pydantic model)
5. Raw CSV → CSVParser.to_account()
6. Account Model → Analyzer.analyze()
7. AnalysisResult → ConsoleReport.render()
8. Formatted Output → Terminal
```

## Design Patterns

### Template Method (BaseAnalyzer)
- Base class defines analysis workflow
- Subclasses implement specific calculations
- Common operations (result creation) in base class

### Strategy (Reports)
- Different report formats (console, HTML, PDF)
- Same data, different presentation
- Easy to add new formats

### Factory (Parsers)
- CSVParser creates Account objects from CSV
- XMLParser (future) creates from XML
- Abstracts data source complexity

### Builder (Portfolio)
- Portfolio.from_accounts() constructs complex object
- Step-by-step aggregation of account data

## Extension Points

### Adding New Analyzer
1. Inherit from `BaseAnalyzer`
2. Implement `analyze()` method
3. Return `AnalysisResult`
4. No changes to other layers needed

### Adding New Report Format
1. Inherit from `BaseReport`
2. Implement `render()` and `save()`
3. No changes to analyzers needed

### Adding New Data Source
1. Create new parser class
2. Implement `to_account()` method
3. Parsers are interchangeable

## Multi-Account Architecture

```
Portfolio (aggregates all accounts)
├── Account 1
│   ├── Trades
│   ├── Positions
│   └── Cash Balances
├── Account 2
│   ├── Trades
│   ├── Positions
│   └── Cash Balances
└── MultiAccountAggregator
    ├── By Symbol
    ├── By Asset Class
    └── By Account
```

## Type Safety

- **Pydantic Models**: Runtime validation
- **Type Hints**: Static type checking
- **Mypy**: Strict mode enforcement
- **Benefits**: Catch errors before runtime

## Performance Considerations

- **Async API Calls**: Parallel fetching for multiple accounts
- **Lazy Loading**: Parse only when needed
- **Decimal Precision**: Avoid floating-point errors
- **Efficient Aggregation**: Single-pass algorithms

Refer to specific files for implementation details.
