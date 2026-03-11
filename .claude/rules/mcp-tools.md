---
paths: ib_sec_mcp/mcp/**/*.py
---

# MCP Tool Development Rules

Quick reference for MCP tool development in IB Analytics.

## Tool Design Decision

| If you need...        | Use...         | Example                          |
| --------------------- | -------------- | -------------------------------- |
| Complete analysis     | Coarse-grained | `analyze_performance`            |
| Composable operations | Fine-grained   | `get_trades`, `calculate_metric` |
| Data filtering        | Fine-grained   | `get_positions(symbol="AAPL")`   |

## Tool Decorator Pattern

```python
@mcp.tool
async def tool_name(
    required_param: str,
    optional_param: str | None = None,
    ctx: Context | None = None,
) -> str:
    """One-line description.

    Args:
        required_param: Description
        optional_param: Description (optional)
        ctx: MCP context for logging
    Returns:
        JSON string with results
    """
```

## Decimal JSON Serialization

```python
result = {
    "price": str(price),  # Convert Decimal to string
    "formatted": f"${price:.2f}",
}
return json.dumps(result, default=str, indent=2)
```

See `financial-code.md` for Decimal rules and `DecimalEncoder` pattern.

## Error Handling

```python
from ib_sec_mcp.mcp.exceptions import ValidationError

# Input validation
if not symbol:
    raise ValidationError("Symbol is required")

# API errors - mask internal details
try:
    data = await fetch_data()
except Exception as e:
    if ctx:
        await ctx.error(f"Internal error: {e}")
    raise ValidationError("Failed to fetch data")
```

## Context Logging

```python
if ctx:
    await ctx.info(f"Processing {symbol}")
    await ctx.debug(f"Found {len(trades)} trades")
    await ctx.warning(f"Missing data for {date}")
```

## Caching

Use `use_cache: bool = True` parameter. Check cache before computation.

## External Dependency Pattern

Extract external API logic to module-level for testability:

```python
# Module-level constants and functions (testable)
MARKET_SUFFIX: dict[str, str] = {"4": ".TO", "8": ".T"}

def resolve_symbol(symbol: str) -> str:
    """Resolve IB symbol to Yahoo Finance symbol."""
    ...
```

**Anti-pattern**: `MARKET_SUFFIX` or symbol resolution inside `register_*_tools` closure (untestable).

## Testing Requirement

New tool module → must create `tests/mcp/test_{module}.py`.
See `.claude/rules/testing.md` for patterns and checklist.

See `/CLAUDE.md` for coarse-grained vs fine-grained design philosophy.
