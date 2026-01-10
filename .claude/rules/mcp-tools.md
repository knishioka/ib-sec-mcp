---
paths: ib_sec_mcp/mcp/**/*.py
---

# MCP Tool Development Rules

Quick reference for MCP tool development in IB Analytics.

## Tool Design Decision

| If you need... | Use... | Example |
|----------------|--------|---------|
| Complete analysis | Coarse-grained | `analyze_performance` |
| Composable operations | Fine-grained | `get_trades`, `calculate_metric` |
| Data filtering | Fine-grained | `get_positions(symbol="AAPL")` |

## Tool Decorator Pattern

```python
@mcp.tool
async def tool_name(
    required_param: str,
    optional_param: str | None = None,
    ctx: Context | None = None,
) -> str:
    """
    One-line description.

    Args:
        required_param: Description
        optional_param: Description (optional)
        ctx: MCP context for logging

    Returns:
        JSON string with results

    Raises:
        ValidationError: If validation fails

    Example:
        >>> result = await tool_name("value")
    """
```

## Decimal JSON Serialization

```python
# Decimal must be converted for JSON
result = {
    "price": str(price),  # Convert to string
    "formatted": f"${price:.2f}",  # Or format
}
return json.dumps(result)

# For complex objects, use custom encoder
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)
```

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

## Caching Pattern

```python
@mcp.tool
async def analyze_data(
    start_date: str,
    use_cache: bool = True,
    ctx: Context | None = None,
) -> str:
    # Check cache first
    if use_cache:
        cached = await get_cached_data(start_date)
        if cached:
            return cached
    ...
```

See `/CLAUDE.md` for coarse-grained vs fine-grained design philosophy.
