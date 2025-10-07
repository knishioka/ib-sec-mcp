# Add New Analyzer

Create a new analyzer module following the project's architecture and conventions.

## What This Command Does

Creates a complete analyzer implementation including:
1. Analyzer class file in `ib_sec_mcp/analyzers/`
2. Export in `ib_sec_mcp/analyzers/__init__.py`
3. Report rendering logic in `ib_sec_mcp/reports/console.py`
4. CLI integration in `ib_sec_mcp/cli/analyze.py`
5. Unit test skeleton in `tests/test_analyzers/`

## Required Information from $ARGUMENTS

- Analyzer name (e.g., "Sharpe", "Drawdown", "Volatility")
- Brief description of what it analyzes
- Key metrics to calculate

## Steps to Execute

1. **Create Analyzer File**: `ib_sec_mcp/analyzers/[name].py`
   - Import BaseAnalyzer and required dependencies
   - Define analyzer class inheriting from BaseAnalyzer
   - Implement `analyze()` method
   - Add docstrings with Google-style format

2. **Update Exports**: `ib_sec_mcp/analyzers/__init__.py`
   - Add import statement
   - Add to `__all__` list

3. **Add Report Rendering**: `ib_sec_mcp/reports/console.py`
   - Add `_render_[name]()` method
   - Update main `render()` method with new case

4. **Integrate CLI**: `ib_sec_mcp/cli/analyze.py`
   - Add analyzer name to available options
   - Add instantiation logic in main analyze command

5. **Create Test Skeleton**: `tests/test_analyzers/test_[name].py`
   - Import analyzer class
   - Create fixture with sample data
   - Write test cases for key methods

## Template Structure

```python
# ib_sec_mcp/analyzers/{name}.py
\"\"\"[Description] analyzer\"\"\"

from ib_sec_mcp.analyzers.base import AnalysisResult, BaseAnalyzer

class [Name]Analyzer(BaseAnalyzer):
    \"\"\"
    Analyze [description]

    [Detailed description of what this analyzer does]
    \"\"\"

    def analyze(self) -> AnalysisResult:
        \"\"\"
        Run [name] analysis

        Returns:
            AnalysisResult with [name] metrics
        \"\"\"
        # Implementation here

        return self._create_result(
            # metrics here
        )
```

## Example Usage

```
/add-analyzer Sharpe "Calculates Sharpe ratio for risk-adjusted returns"
/add-analyzer Drawdown "Analyzes maximum drawdown and recovery periods"
```

## Validation

After creating the analyzer:
1. Run `black` and `ruff` to ensure code style
2. Run `mypy` to verify type hints
3. Test with sample data
4. Update documentation in README.md

Follow project conventions:
- Use Decimal for calculations
- Provide comprehensive docstrings
- Handle edge cases gracefully
- Return AnalysisResult with all metrics as strings
