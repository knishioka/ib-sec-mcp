---
paths: tests/**/*.py, ib_sec_mcp/**/*.py
---

# Testing Rules

Standards for testing MCP tools and analyzers in IB Analytics.

## File Naming

| Source                             | Test                             |
| ---------------------------------- | -------------------------------- |
| `ib_sec_mcp/mcp/tools/{module}.py` | `tests/mcp/test_{module}.py`     |
| `ib_sec_mcp/analyzers/{name}.py`   | `tests/analyzers/test_{name}.py` |

**Rule**: New tool module → must create corresponding test file.

## MCP Tool Test Pattern

```python
@pytest.fixture()
def test_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_foo_tools(mcp)
    return mcp

async def test_tool_happy_path(test_mcp):
    tool = await test_mcp.get_tool("tool_name")
    result = await tool.fn(param="value", ctx=None)
    data = json.loads(result)
    assert "expected_key" in data
```

## External API Mock Patterns

```python
# yfinance: patch("yfinance.Ticker"), set mock.info = {...}
# IB API: patch("...._get_or_fetch_data", new_callable=AsyncMock)
# Storage: use real class — LimitOrderStore(tmp_path / "test.db")
# API failure: type(mock).info = property(lambda self: raise RuntimeError(...))
```

## Required Test Checklist

New MCP tool must have:

- [ ] Tool name added to `tests/mcp/test_server.py` `EXPECTED_TOOLS`
- [ ] Happy path with mocked external APIs
- [ ] Input validation error cases
- [ ] External API failure → graceful degradation
- [ ] Response is valid JSON with expected keys
- [ ] Decimal precision (no float contamination in financial values)

## What NOT to Test

- Error message exact wording
- Internal implementation details
- Third-party library behavior
- Log output formatting

## Extractability Rule

**Anti-pattern**: Logic buried inside `register_*_tools` closure

```python
# BAD - untestable
def register_foo_tools(mcp):
    SUFFIX_MAP = {"4": ".TO"}  # trapped in closure
    @mcp.tool
    async def get_foo(symbol: str) -> str:
        resolved = symbol + SUFFIX_MAP.get(...)  # can't unit test
```

```python
# GOOD - testable
SUFFIX_MAP = {"4": ".TO"}  # module-level constant

def resolve_symbol(symbol: str) -> str:  # module-level function
    return symbol + SUFFIX_MAP.get(...)

def register_foo_tools(mcp):
    @mcp.tool
    async def get_foo(symbol: str) -> str:
        resolved = resolve_symbol(symbol)  # delegates to testable fn
```

Extract to module-level: symbol resolution, data transformation, validation logic.

## Commands

```bash
uv run pytest tests/mcp/test_{module}.py -v      # Single module
uv run pytest tests/mcp/ -v                       # All MCP tests
uv run pytest --cov=ib_sec_mcp -v                 # With coverage
```
