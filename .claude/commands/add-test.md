---
description: Create test file for analyzer, parser, or other module
allowed-tools: Read, Write, Glob, Grep
argument-hint: module-name [--analyzer|--parser|--model]
---

Generate comprehensive test file following project conventions and best practices.

## Task

Create a complete test file with fixtures, test cases, and proper structure. Delegate to **test-runner** subagent.

### Module Type Detection

From $ARGUMENTS:
- If contains `--analyzer` or module in `analyzers/`: Create analyzer test
- If contains `--parser` or module in `core/parsers`: Create parser test
- If contains `--model` or module in `models/`: Create model test
- Otherwise: Generic module test

### Test File Location

Based on module type:
- Analyzer: `tests/test_analyzers/test_{name}.py`
- Parser: `tests/test_parsers/test_{name}.py`
- Model: `tests/test_models/test_{name}.py`
- Other: `tests/test_{name}.py`

### Test Structure

**1. Imports**
```python
import pytest
from decimal import Decimal
from datetime import date, datetime
from ib_sec_mcp.{module_path} import {ClassName}
```

**2. Fixtures**
```python
@pytest.fixture
def sample_{type}():
    """Create sample {type} for testing"""
    # Based on module type
    return {ClassName}(...)
```

**3. Test Cases**

**For Analyzers**:
```python
def test_{analyzer}_basic(sample_account):
    """Test basic {analyzer} functionality"""
    analyzer = {Name}Analyzer(sample_account)
    result = analyzer.analyze()

    assert result.analyzer_name == "{name}"
    assert "total_pnl" in result.metrics
    assert result.data is not None

def test_{analyzer}_empty_account():
    """Test with empty account"""
    empty_account = Account(account_id="TEST", trades=[], positions=[])
    analyzer = {Name}Analyzer(empty_account)
    result = analyzer.analyze()

    # Should handle gracefully
    assert result.analyzer_name == "{name}"

def test_{analyzer}_edge_cases(sample_account):
    """Test edge cases"""
    # Test with None values, missing data, etc.
    pass
```

**For Parsers**:
```python
def test_parse_valid_csv(tmp_path):
    """Test parsing valid CSV file"""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(sample_csv_data)

    parser = CSVParser()
    account = parser.to_account(csv_file)

    assert account.account_id == "TEST123"
    assert len(account.trades) > 0

def test_parse_invalid_format():
    """Test with invalid CSV format"""
    with pytest.raises(ValueError):
        parser.parse_invalid_data()
```

**For Models**:
```python
def test_model_validation():
    """Test Pydantic validation"""
    # Valid data
    obj = {ModelName}(field1="value", field2=Decimal("100"))
    assert obj.field1 == "VALUE"  # If validator uppercases

def test_model_invalid_data():
    """Test validation errors"""
    with pytest.raises(ValidationError):
        {ModelName}(field1="invalid")
```

**4. Common Test Patterns**

```python
# Decimal precision
def test_decimal_precision():
    result = calculate_something(Decimal("100.50"))
    assert result == Decimal("105.525")
    assert isinstance(result, Decimal)

# Date parsing
def test_date_parsing():
    result = parse_date("20251011")
    assert result == date(2025, 10, 11)

# Error handling
def test_error_handling():
    with pytest.raises(CustomError) as exc_info:
        function_that_raises()
    assert "expected message" in str(exc_info.value)
```

### Sample Test File

```python
\"\"\"Tests for {module_name}\"\"\"

import pytest
from decimal import Decimal
from datetime import date
from ib_sec_mcp.{module_path} import {ClassName}

@pytest.fixture
def sample_data():
    \"\"\"Create sample test data\"\"\"
    # ... sample data creation
    return data

class Test{ClassName}:
    \"\"\"Test suite for {ClassName}\"\"\"

    def test_basic_functionality(self, sample_data):
        \"\"\"Test basic operation\"\"\"
        obj = {ClassName}(sample_data)
        result = obj.main_method()

        assert result is not None
        # Additional assertions

    def test_edge_cases(self):
        \"\"\"Test edge cases and boundary conditions\"\"\"
        # Test with empty/None/invalid data
        pass

    def test_error_handling(self):
        \"\"\"Test error handling\"\"\"
        with pytest.raises(ValueError):
            {ClassName}(invalid_data)

    @pytest.mark.parametrize("input,expected", [
        (value1, expected1),
        (value2, expected2),
        (value3, expected3),
    ])
    def test_parametrized(self, input, expected):
        \"\"\"Test with multiple inputs\"\"\"
        result = function(input)
        assert result == expected
```

### Validation Checklist

After creating test file:
```bash
# 1. Check syntax
python -m py_compile tests/test_{name}.py

# 2. Run new tests
pytest tests/test_{name}.py -v

# 3. Check coverage
pytest tests/test_{name}.py --cov=ib_sec_mcp.{module} --cov-report=term

# 4. Lint
ruff check tests/test_{name}.py

# 5. Type check
mypy tests/test_{name}.py
```

### Examples

```
/add-test performance --analyzer
/add-test csv_parser --parser
/add-test Trade --model
/add-test calculator
```

The **test-runner** subagent will create comprehensive test file with:
- ✅ Proper fixtures
- ✅ Edge case coverage
- ✅ Error handling tests
- ✅ Parametrized tests where appropriate
- ✅ Docstrings and comments
- ✅ Following project conventions
