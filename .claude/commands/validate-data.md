---
description: Validate CSV data integrity and format compliance
allowed-tools: Read, Bash(python:*), Grep, Glob
argument-hint: [csv-file-path|--latest]
---

Perform comprehensive data validation on IB Flex Query CSV files to ensure data integrity and format compliance.

## Task

Validate CSV data structure, content integrity, and business logic constraints.

### Validation Scope

**File Selection**:
- If $ARGUMENTS provides path: Validate specified CSV
- If $ARGUMENTS contains `--latest`: Validate most recent file in `data/raw/`
- Otherwise: Validate all CSVs in `data/raw/`

### Validation Checks

**1. File Structure Validation**
```python
# Check file exists and readable
assert csv_file.exists()
assert csv_file.stat().st_size > 0

# Check CSV format
with open(csv_file) as f:
    first_line = f.readline()
    assert first_line.strip()  # Not empty
```

**2. Section Detection**
```python
# Verify expected sections present
expected_sections = [
    "Trades",
    "Open Positions",
    "Cash Report"
]

for section in expected_sections:
    assert section in sections_found
```

**3. Date Format Validation**
```python
# Trade dates in YYYYMMDD format
for trade_date in trade_dates:
    assert len(trade_date) == 8
    assert trade_date.isdigit()

    # Valid date range
    year = int(trade_date[:4])
    month = int(trade_date[4:6])
    day = int(trade_date[6:8])

    assert 2000 <= year <= 2030
    assert 1 <= month <= 12
    assert 1 <= day <= 31
```

**4. Numeric Field Validation**
```python
# Prices, quantities must be numeric
for field in numeric_fields:
    value = Decimal(field)
    assert value is not None

    # Financial values shouldn't be extremely large/small
    assert abs(value) < Decimal("1000000000")  # $1B limit
```

**5. Account ID Consistency**
```python
# Account ID format (e.g., U16231259)
assert account_id.startswith("U")
assert account_id[1:].isdigit()
assert len(account_id) >= 8

# Consistent across all sections
for section in sections:
    assert section.account_id == account_id
```

**6. Business Logic Validation**
```python
# P&L calculations
for trade in trades:
    calculated_pnl = (trade.sell_price - trade.buy_price) * trade.quantity
    assert abs(calculated_pnl - trade.pnl) < Decimal("0.01")  # Allow rounding

# Position consistency
total_positions = sum(p.quantity for p in positions)
assert total_positions > 0 or len(positions) == 0

# Cash balances
total_cash = sum(cb.amount for cb in cash_balances)
# Cash can be negative (margin account)
```

**7. Data Completeness**
```python
# Required fields present
required_fields = ["Symbol", "Quantity", "TradePrice", "TradeDate"]
for field in required_fields:
    assert field in headers

# No missing critical data
for trade in trades:
    assert trade.symbol is not None
    assert trade.quantity != 0
    assert trade.price > 0
```

**8. Bond-Specific Validation**
```python
# Bond symbols format (CUSIP)
for position in bond_positions:
    assert len(position.symbol) == 9  # CUSIP length
    assert position.symbol[:6].isdigit()

    # Maturity date validation
    if position.maturity_date:
        assert position.maturity_date > date.today()
```

### Expected Output

```
=== Data Validation Report ===
File: data/raw/U16231259_2025-01-01_2025-10-05.csv
Size: 2.4 MB
Validated: 2025-10-11 14:45:00

✅ FILE STRUCTURE
- File exists and readable
- Non-empty content (2,456,789 bytes)
- Valid CSV format
- UTF-8 encoding

✅ SECTION DETECTION
Found all expected sections:
- ✅ Trades (1,234 rows)
- ✅ Open Positions (45 rows)
- ✅ Cash Report (3 rows)
- ✅ Account Information (1 row)

✅ DATE FORMAT VALIDATION
- Trade dates: 1,234 validated
- Format: YYYYMMDD (all valid)
- Date range: 2025-01-01 to 2025-10-05
- ✅ No invalid dates
- ✅ No future dates

✅ NUMERIC FIELD VALIDATION
- Price fields: 1,234 validated (all Decimal)
- Quantity fields: 1,234 validated
- P&L fields: 1,234 validated
- ✅ No invalid numeric values
- ✅ No extreme outliers

✅ ACCOUNT ID CONSISTENCY
- Account ID: U16231259
- Format: Valid (U + 8 digits)
- ✅ Consistent across all sections

✅ BUSINESS LOGIC VALIDATION
P&L Calculations:
- Validated: 1,234 trades
- Matches: 1,232 (99.8%)
- Discrepancies: 2 (within rounding tolerance <$0.01)

Position Consistency:
- Total positions: 45
- Total quantity: 12,345 shares
- ✅ All positions have valid quantities

Cash Balances:
- USD: $234,567.89
- Total: $234,567.89
- ✅ Cash balance is reasonable

✅ DATA COMPLETENESS
Required Fields:
- Symbol: 100% present
- Quantity: 100% present
- TradePrice: 100% present
- TradeDate: 100% present
- ✅ No missing critical data

Optional Fields:
- Commission: 98% present (28 missing, acceptable)
- IBOrderID: 100% present

✅ BOND-SPECIFIC VALIDATION
Bond Positions: 12 found
- CUSIP format: ✅ All valid (9 characters)
- Maturity dates: 10 present, 2 missing (acceptable)
- ✅ Future maturity dates (2028-2030)

⚠️ WARNINGS (Non-Critical)

1. Commission Missing (28 trades)
   - Trades: #145, #267, #389, ... (25 more)
   - Impact: Cost analysis may be incomplete
   - Severity: LOW
   - Action: Review with broker if needed

2. Bond Maturity Missing (2 positions)
   - Symbols: 912810XX, 912810YY
   - Impact: YTM calculation not possible
   - Severity: MEDIUM
   - Action: Manually add maturity dates

=== VALIDATION SUMMARY ===

Status: ✅ PASSED WITH WARNINGS

Critical Checks: 8/8 passed (100%)
- File Structure: ✅
- Section Detection: ✅
- Date Format: ✅
- Numeric Fields: ✅
- Account ID: ✅
- Business Logic: ✅
- Data Completeness: ✅
- Bond Validation: ✅

Warnings: 2 non-critical issues
- Missing commission data (28 trades, 2%)
- Missing maturity dates (2 bonds, 17%)

Data Quality Score: 96/100

Recommended Actions:
1. ✅ Safe to use for analysis
2. 💡 Review missing commission data if cost analysis needed
3. 💡 Add maturity dates for complete bond analysis

=== DETAILED ERROR LOG ===

(No critical errors found)

=== DATA STATISTICS ===

Trades:
- Total: 1,234
- Date range: 186 days
- Avg per day: 6.6 trades
- Symbols: 67 unique

Positions:
- Total: 45
- Asset types: Stocks (33), Bonds (12)
- Total value: $1,234,567 (estimated)

Cash:
- USD: $234,567.89
- Other currencies: None

Date Coverage:
- Start: 2025-01-01
- End: 2025-10-05
- Days: 186
- Trading days: 124 (estimated)

=== VALIDATION COMPLETE ===
File ready for analysis ✅
```

### Validation Levels

**Quick Validation** (default):
- File structure
- Section detection
- Date formats
- Account ID consistency

**Full Validation** (if $ARGUMENTS contains `--full`):
- All quick checks
- Business logic validation
- P&L calculations
- Statistical analysis
- Outlier detection

**Strict Validation** (if $ARGUMENTS contains `--strict`):
- Zero tolerance for warnings
- All fields must be present
- Perfect P&L matching required

### Error Reporting

**Critical Errors** (block analysis):
- File not found
- Corrupted CSV structure
- Invalid account ID
- Missing required sections
- Invalid date formats

**Warnings** (allow analysis with caution):
- Missing optional fields
- Minor P&L discrepancies (< $0.01)
- Missing maturity dates for some bonds

### Examples

```
/validate-data
/validate-data --latest
/validate-data data/raw/U16231259_2025-01-01_2025-10-05.csv
/validate-data --full
/validate-data --strict
```

Run this command before analysis to ensure data quality and identify potential issues early.
