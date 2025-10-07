# IB Analytics - Project Summary

**Version**: 0.1.0
**Created**: 2025-10-06
**Author**: Kenichiro Nishioka

---

## 📋 Project Overview

**IB Analytics** is a professional-grade portfolio analytics library for Interactive Brokers with comprehensive multi-account support. Built with modern Python best practices, type safety, and extensible architecture.

### Key Features

✅ **Multi-Account Support** - Analyze multiple IB accounts simultaneously
✅ **Type-Safe** - Pydantic v2 models with runtime validation
✅ **Async Support** - Parallel data fetching with httpx
✅ **Modular Design** - Easy to extend with new analyzers
✅ **CLI Tools** - User-friendly command-line interface
✅ **Rich Reports** - Beautiful console output with Rich library
✅ **Latest Dependencies** - Using stable 2024 versions

---

## 🏗️ Architecture

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

### Components

| Component | Files | Purpose |
|-----------|-------|---------|
| **API Client** | 3 | IB Flex Query API integration |
| **Models** | 4 | Type-safe domain models |
| **Core Logic** | 3 | Parsers, calculations, aggregation |
| **Analyzers** | 6 | Performance, cost, bond, tax, risk |
| **Reports** | 2 | Console and base report classes |
| **CLI** | 3 | Fetch, analyze, report commands |
| **Utils** | 2 | Config and validators |

**Total**: 23 Python modules, ~3,500 lines of code

---

## 📦 Dependencies (Latest Stable)

| Library | Version | Purpose |
|---------|---------|---------|
| **requests** | 2.32.5+ | HTTP API client |
| **pandas** | 2.2.3+ | Data analysis |
| **pydantic** | 2.10.0+ | Data validation |
| **httpx** | 0.27.0+ | Async HTTP |
| **rich** | 13.7.0+ | Console UI |
| **typer** | 0.12.0+ | CLI framework |

### Python Support
- ✅ Python 3.9
- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12

---

## 📊 Available Analyzers

### 1. PerformanceAnalyzer
**Metrics**: Win rate, profit factor, ROI, risk/reward ratio
**Use Case**: Overall trading performance evaluation

### 2. CostAnalyzer
**Metrics**: Commission rates, cost efficiency, impact on P&L
**Use Case**: Cost optimization and broker comparison

### 3. BondAnalyzer
**Metrics**: YTM, duration, maturity analysis
**Use Case**: Zero-coupon bond (STRIPS) analytics

### 4. TaxAnalyzer
**Metrics**: Phantom income (OID), capital gains tax
**Use Case**: Tax liability estimation

### 5. RiskAnalyzer
**Metrics**: Interest rate scenarios, concentration risk
**Use Case**: Portfolio risk assessment

---

## 🚀 Quick Start

### Installation

```bash
# Clone or navigate to project
cd ib-sec

# Install dependencies
pip install -e .

# Verify installation
ib-sec-fetch --help
ib-sec-analyze --help
```

### Configuration

Create `.env` file:

```env
QUERY_ID=your_query_id_here
TOKEN=your_token_here
```

### Basic Usage

```bash
# 1. Fetch data
ib-sec-fetch --start-date 2025-01-01 --end-date 2025-10-05

# 2. Run analysis
ib-sec-analyze data/raw/U16231259_2025-01-01_2025-10-05.csv --all

# 3. View results in console
```

### Programmatic Usage

```python
from ib_sec_mcp import FlexQueryClient
from ib_sec_mcp.analyzers import PerformanceAnalyzer
from ib_sec_mcp.core.parsers import CSVParser

# Fetch data
client = FlexQueryClient(query_id="...", token="...")
statement = client.fetch_statement(start_date, end_date)

# Parse
account = CSVParser.to_account(statement.raw_data, start_date, end_date)

# Analyze
analyzer = PerformanceAnalyzer(account=account)
results = analyzer.analyze()

print(results)
```

---

## 📁 Project Structure

```
ib-sec/
├── .claude/                  # Claude Code configuration
│   ├── CLAUDE.md            # Project context (313 lines)
│   ├── README.md            # .claude directory guide
│   └── commands/            # Custom slash commands (5)
│       ├── analyze-all.md
│       ├── fetch-latest.md
│       ├── add-analyzer.md
│       ├── explain-architecture.md
│       └── debug-api.md
├── ib_sec_mcp/            # Main library package
│   ├── api/                 # API client (3 files)
│   ├── core/                # Business logic (3 files)
│   ├── models/              # Data models (4 files)
│   ├── analyzers/           # Analyzers (6 files)
│   ├── reports/             # Report generators (2 files)
│   ├── utils/               # Utilities (2 files)
│   └── cli/                 # CLI tools (3 files)
├── scripts/                 # Example scripts
│   └── example_usage.py
├── tests/                   # Test framework (to be implemented)
├── legacy/                  # Original scripts (10 files)
├── data/                    # Data storage
│   ├── raw/                 # Raw CSV files
│   └── processed/           # Analysis results
├── pyproject.toml           # Project metadata
├── requirements.txt         # Pip dependencies
├── README.md                # User documentation
├── INSTALL.md               # Installation guide
├── CHANGELOG.md             # Version history
└── .env                     # API credentials (not committed)
```

---

## 🎯 Design Patterns Used

### Template Method (BaseAnalyzer)
```python
class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self) -> AnalysisResult:
        pass

class PerformanceAnalyzer(BaseAnalyzer):
    def analyze(self) -> AnalysisResult:
        # Implementation
        return self._create_result(...)
```

### Strategy (Reports)
```python
class BaseReport(ABC):
    @abstractmethod
    def render(self) -> str:
        pass

class ConsoleReport(BaseReport):
    def render(self) -> str:
        # Console-specific rendering
```

### Factory (Parsers)
```python
account = CSVParser.to_account(csv_data, from_date, to_date)
```

### Builder (Portfolio)
```python
portfolio = Portfolio.from_accounts(accounts, base_currency="USD")
```

---

## 🔧 Development Workflow

### Adding New Features

1. **New Analyzer**
   ```bash
   # Use custom command
   /add-analyzer Sharpe "Calculate Sharpe ratio"
   ```

2. **Update Context**
   ```bash
   # Press # in Claude Code
   # "New analyzers must calculate annualized metrics"
   ```

3. **Format & Lint**
   ```bash
   black ib_sec_mcp tests
   ruff check ib_sec_mcp tests
   mypy ib_sec_mcp
   ```

### Testing (Future)

```bash
# Run tests
pytest

# With coverage
pytest --cov=ib_sec_mcp --cov-report=html

# Specific test
pytest tests/test_analyzers/test_performance.py
```

---

## 📚 Documentation

### User Documentation
- **README.md**: Quick start and usage guide
- **INSTALL.md**: Detailed installation instructions
- **CHANGELOG.md**: Version history and changes

### Developer Documentation
- **.claude/CLAUDE.md**: Project context for Claude Code
- **.claude/README.md**: Claude Code configuration guide
- **Inline Docstrings**: Google-style in all modules

### API Documentation (Future)
- Sphinx auto-generated docs
- GitHub Pages deployment
- Interactive examples

---

## 🎨 Code Quality Standards

### Style
- **Formatter**: Black (100 char line length)
- **Linter**: Ruff (E, F, I, N, W, UP, B, A, C4, T20, SIM)
- **Type Checker**: mypy (strict mode)

### Conventions
- **Classes**: PascalCase
- **Functions**: snake_case
- **Constants**: UPPER_SNAKE_CASE
- **Private**: _leading_underscore

### Documentation
- **Docstrings**: Required for all public APIs
- **Type Hints**: Required for all functions
- **Comments**: Explain why, not what

---

## 🔮 Future Roadmap

### Phase 1 (Current) ✅
- [x] Core library structure
- [x] Multi-account support
- [x] 5 core analyzers
- [x] CLI tools
- [x] Console reports

### Phase 2 (Next)
- [ ] Unit tests with pytest
- [ ] HTML reports with charts
- [ ] XML parser implementation
- [ ] Additional analyzers (Sharpe, Drawdown)
- [ ] Documentation site

### Phase 3 (Future)
- [ ] PDF report generation
- [ ] Web dashboard (Streamlit)
- [ ] Real-time data streaming
- [ ] Backtesting framework
- [ ] Portfolio optimization

### Phase 4 (Advanced)
- [ ] Machine learning predictions
- [ ] Automated trading signals
- [ ] Risk management alerts
- [ ] Mobile app integration

---

## 📊 Migration from Legacy Scripts

### Before (Legacy Scripts)

```
ib-sec/
├── analyze_performance.py      # Standalone script
├── trading_cost_analysis.py    # Standalone script
├── phantom_income_tax_analysis.py
├── bond_analysis.py
├── interest_rate_scenario_analysis.py
└── comprehensive_summary_report.py
```

**Issues**:
- ❌ Code duplication
- ❌ No type safety
- ❌ Hard to test
- ❌ No multi-account support
- ❌ Monolithic structure

### After (New Library)

```
ib_sec_mcp/
├── analyzers/
│   ├── performance.py   # Modular
│   ├── cost.py         # Reusable
│   ├── bond.py         # Type-safe
│   ├── tax.py          # Testable
│   └── risk.py         # Extensible
```

**Benefits**:
- ✅ Modular architecture
- ✅ Type safety (Pydantic)
- ✅ Easy to test
- ✅ Multi-account support
- ✅ CLI + programmatic API

---

## 🤝 Contributing

### Adding New Analyzer

1. Create `ib_sec_mcp/analyzers/your_analyzer.py`
2. Inherit from `BaseAnalyzer`
3. Implement `analyze()` method
4. Add to `__init__.py` exports
5. Update `ConsoleReport` rendering
6. Add CLI integration
7. Write tests
8. Update documentation

### Custom Slash Commands

1. Create `.claude/commands/your-command.md`
2. Write natural language instructions
3. Use `$ARGUMENTS` for parameters
4. Test with `/your-command`
5. Commit to git

---

## 📞 Support

### Issues
- Check existing issues in git
- Include error messages and logs
- Provide minimal reproduction steps

### Questions
- Review `.claude/CLAUDE.md`
- Check README and INSTALL guides
- Use `/explain-architecture` command

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **Interactive Brokers**: Flex Query API
- **Pydantic**: Type-safe data models
- **Rich**: Beautiful console output
- **Typer**: User-friendly CLI
- **Anthropic**: Claude Code integration

---

**Last Updated**: 2025-10-06
**Status**: Production Ready (v0.1.0)
**Maintainer**: Kenichiro Nishioka

For detailed information, see:
- [README.md](README.md) - User guide
- [INSTALL.md](INSTALL.md) - Installation
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [.claude/CLAUDE.md](.claude/CLAUDE.md) - Developer context
