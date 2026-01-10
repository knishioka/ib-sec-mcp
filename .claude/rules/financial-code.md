---
paths: ib_sec_mcp/**/*.py
---

# Financial Code Rules

Quick reference for financial code standards in IB Analytics.

## Decimal Checklist

Before committing Python code with financial calculations:

- [ ] All money/price/quantity values use `Decimal`
- [ ] No `float()` calls on financial data
- [ ] String literals for Decimal init: `Decimal("100.50")`
- [ ] Division by zero handled explicitly
- [ ] Negative value validation where appropriate

## Common Pitfalls

```python
# WRONG - float precision issues
rate = 0.05
total = price * 0.95

# CORRECT
rate = Decimal("0.05")
total = price * Decimal("0.95")

# WRONG - loss of precision
value = Decimal(100.50)  # float converted

# CORRECT
value = Decimal("100.50")  # string literal
```

## Validation Pattern

```python
def calculate_metric(value: Decimal, divisor: Decimal) -> Decimal:
    if divisor == Decimal("0"):
        raise ValueError("Division by zero")
    if value < Decimal("0"):
        raise ValueError(f"Value must be non-negative: {value}")
    return value / divisor
```

## Import Order

```python
# Standard library
from decimal import Decimal
from datetime import date

# Third-party
from pydantic import BaseModel, Field

# Local
from ib_sec_mcp.models.trade import Trade
```

## Type Hints

```python
# Explicit Decimal types
def calc_total(price: Decimal, quantity: Decimal) -> Decimal:
    ...

# Pydantic models
class TradeRecord(BaseModel):
    price: Decimal = Field(ge=Decimal("0"))
    quantity: Decimal
```

See `code-implementer` sub-agent for detailed implementation patterns.
