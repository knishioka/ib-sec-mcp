# Error Handling Template for Slash Commands and Sub-Agents

This template provides standardized error handling patterns for consistent error reporting across all IB Analytics commands and agents.

## Standard Error Format

All errors should follow this structured format for consistent handling by Claude Code:

```yaml
error_response:
  category: CLIENT_ERROR | SERVER_ERROR | EXTERNAL_ERROR
  code: 400 | 500 | 502
  message: "Clear, actionable message for the user"
  details:
    field: "specific field that failed"
    expected: "what was expected"
    actual: "what was received"
  recovery_strategy:
    - "Step 1 to recover"
    - "Step 2 to recover"
  retry_after: 60  # seconds, if applicable
```

## Error Categories

### CLIENT_ERROR (400-499)
User input issues that can be fixed by the user:
- Invalid arguments
- Missing required parameters
- Malformed data format
- Symbol not found
- Date out of range

### SERVER_ERROR (500-599)
Internal processing issues:
- Timeout exceeded
- Memory/resource limits
- Calculation failures
- Unexpected internal state

### EXTERNAL_ERROR (502-504)
External service issues:
- MCP server unavailable
- IB Flex Query API down
- Network connectivity issues
- Rate limit exceeded

## Common Error Patterns

### 1. MCP Tool Failure

```markdown
**Error Handling**:
- If `analyze_consolidated_portfolio` fails:
  - **Category**: EXTERNAL_ERROR (MCP server issue)
  - **Code**: 502
  - **Message**: "Portfolio analysis failed - MCP server unavailable"
  - **Details**:
    - error: "[specific error from MCP]"
    - attempted_tool: "analyze_consolidated_portfolio"
  - **Recovery Strategy**:
    1. Check MCP server status: `/mcp-status`
    2. Verify credentials in `.env` file
    3. Retry operation in 60 seconds
    4. Fallback: Use cached data if available
  - **Retry After**: 60
```

### 2. Timeout Handling

```markdown
**Timeout Handling**:
- If operation exceeds 8 minutes:
  - **Category**: SERVER_ERROR (performance issue)
  - **Code**: 504
  - **Message**: "Operation approaching timeout limit (8/10 minutes)"
  - **Details**:
    - elapsed_time: "8 minutes"
    - incomplete_tasks: ["market analysis for AAPL", "synthesis"]
    - completed_tasks: ["portfolio analysis", "3/5 market analyses"]
  - **Recovery Strategy**:
    1. Abort non-critical sub-agents immediately
    2. Generate partial report with available data
    3. Mark incomplete sections clearly: "[INCOMPLETE: Timeout]"
    4. Provide continuation command: `/analyze-stock AAPL`
  - **Retry After**: null  # Don't auto-retry timeouts
```

### 3. Invalid Arguments

```markdown
**Argument Validation**:
- If symbol not found in portfolio:
  - **Category**: CLIENT_ERROR (invalid input)
  - **Code**: 400
  - **Message**: "Symbol 'XYZ' not found in portfolio"
  - **Details**:
    - requested_symbol: "XYZ"
    - available_symbols: ["AAPL", "GOOGL", "MSFT", "TSLA"]
    - similar_matches: ["XYL", "XYF"]  # fuzzy matching
  - **Recovery Strategy**:
    1. Review available symbols listed above
    2. Check for typos in symbol
    3. Try similar symbols: XYL, XYF
    4. Use `/optimize-portfolio` for full portfolio view
  - **Retry After**: null
```

### 4. API Rate Limit

```markdown
**Rate Limit Handling**:
- If IB Flex Query API rate limit exceeded:
  - **Category**: EXTERNAL_ERROR (rate limit)
  - **Code**: 429
  - **Message**: "IB Flex Query API rate limit exceeded"
  - **Details**:
    - requests_made: 5
    - limit: 3
    - reset_time: "2025-11-09T15:30:00Z"
  - **Recovery Strategy**:
    1. Wait 5 seconds before retry (built-in delay)
    2. Maximum 3 automatic retries
    3. Use cached data if available
    4. Schedule for later execution
  - **Retry After**: 5
```

### 5. Data Validation Error

```markdown
**Data Validation**:
- If CSV data format invalid:
  - **Category**: CLIENT_ERROR (data format)
  - **Code**: 422
  - **Message**: "Invalid CSV data format in IB Flex Query response"
  - **Details**:
    - section: "Trades"
    - row: 145
    - error: "Missing required field: 'Symbol'"
    - file: "data/raw/U1234567_20251109.csv"
  - **Recovery Strategy**:
    1. Re-fetch data using `/fetch-latest`
    2. Verify Flex Query configuration in IB
    3. Check for partial data availability
    4. Contact IB support if persistent
  - **Retry After**: 300  # 5 minutes
```

## Implementation Examples

### For Slash Commands

Add to each command file (e.g., `/investment-strategy.md`):

```markdown
## Error Handling

**Timeout Protection**:
- Target: 6-8 minutes (2+ min safety margin)
- If >6 min: Streamline remaining analysis
- If >8 min: Generate partial report with [INCOMPLETE] markers

**MCP Failures**:
- If portfolio analysis fails: Exit with clear error
- If market analysis fails: Continue with portfolio data only
- Always provide recovery command

**See**: `.claude/templates/error-handling.md` for standard format
```

### For Sub-Agents

Add to each agent file (e.g., `strategy-coordinator.md`):

```markdown
## Error Handling

Follow standard error format from `.claude/templates/error-handling.md`:

1. **Categorize** error (CLIENT/SERVER/EXTERNAL)
2. **Structure** response with all required fields
3. **Provide** clear recovery steps
4. **Include** retry timing when applicable
5. **Log** for debugging

Example:
```json
{
  "category": "EXTERNAL_ERROR",
  "code": 502,
  "message": "Unable to fetch portfolio data",
  "recovery_strategy": ["Check MCP server", "Verify credentials"]
}
```
```

### For MCP Tools

Implement in Python (`ib_sec_mcp/mcp/tools.py`):

```python
from typing import Literal
from pydantic import BaseModel

class MCPError(BaseModel):
    category: Literal["CLIENT_ERROR", "SERVER_ERROR", "EXTERNAL_ERROR"]
    code: int
    message: str
    details: dict = {}
    recovery_strategy: list[str] = []
    retry_after: int | None = None

# In tool implementation:
@mcp.tool()
def analyze_portfolio(...) -> str:
    try:
        # ... tool logic ...
    except ValidationError as e:
        error = MCPError(
            category="CLIENT_ERROR",
            code=400,
            message=f"Invalid date format: {e}",
            details={"expected": "YYYY-MM-DD", "actual": str(e)},
            recovery_strategy=["Use format: YYYY-MM-DD", "Example: 2025-11-09"],
            retry_after=None
        )
        return json.dumps(error.model_dump(), indent=2)
```

## Best Practices

1. **Be Specific**: Include actual values, not just "error occurred"
2. **Be Actionable**: Every error needs clear recovery steps
3. **Be Consistent**: Use the same format across all errors
4. **Be User-Friendly**: Write messages for investors, not developers
5. **Be Complete**: Include all context needed for debugging

## Testing Error Handling

Test each error scenario:

```bash
# Test timeout
/investment-strategy  # Let it run >8 minutes

# Test invalid symbol
/analyze-stock INVALID_SYMBOL

# Test MCP failure
# (Stop MCP server first)
/optimize-portfolio

# Test rate limit
# (Make rapid repeated calls)
/fetch-latest && /fetch-latest && /fetch-latest
```

## Migration Checklist

When updating existing commands/agents:

- [ ] Identify all error points
- [ ] Categorize each error type
- [ ] Structure error responses
- [ ] Add recovery strategies
- [ ] Include retry timing
- [ ] Test error paths
- [ ] Update documentation

---

**Last Updated**: 2025-11-09
**Template Version**: 1.0.0
**Priority**: Implement for all Priority 1 commands first
