---
description: Run performance benchmarks on critical code paths
allowed-tools: Bash(python -m cProfile:*), Bash(python -m timeit:*), Bash(time:*), Read, Write
argument-hint: [--full|--quick|module-name]
---

Execute performance benchmarks on critical components and generate optimization recommendations.

## Task

Delegate to **performance-optimizer** subagent to profile and benchmark code performance.

### Benchmark Modes

**Quick Benchmark** (default or `--quick`):
- Parse CSV (10K rows)
- Run single analyzer
- API fetch simulation
- Total time: ~30 seconds

**Full Benchmark** (`--full`):
- All parsers (CSV, XML)
- All 5 analyzers
- Multi-account operations
- Decimal performance tests
- Memory profiling
- Total time: ~5 minutes

**Module-Specific** (if $ARGUMENTS contains module name):
- Benchmark only specified module
- E.g., `performance`, `bond`, `parser`

### Benchmark Suite

**1. CSV Parsing Performance**
```bash
python -m timeit -n 100 -r 5 -s "
from ib_sec_mcp.core.parsers import CSVParser
from pathlib import Path

csv_file = Path('data/raw/sample_10k.csv')
parser = CSVParser()
" "parser.to_account(csv_file)"
```

Target: < 500ms for 10K rows

**2. Analyzer Performance**
```bash
python -m cProfile -s cumulative -c "
from ib_sec_mcp.analyzers.performance import PerformanceAnalyzer
# ... setup
analyzer.analyze()
"
```

Target: < 1 second per analyzer

**3. Decimal Operations**
```bash
python -m timeit -s "from decimal import Decimal; a = Decimal('100.50')" "a * 2"
python -m timeit -s "from decimal import Decimal; a = Decimal('100.50')" "a + a"
python -m timeit -s "from decimal import Decimal; a = Decimal('100.50'); b = Decimal('2')" "a / b"
```

**4. API Fetch Performance**
```bash
time python -c "
from ib_sec_mcp.api.client import FlexQueryClient
from datetime import date, timedelta

client = FlexQueryClient(query_id='...', token='...')
stmt = client.fetch_statement(
    date.today() - timedelta(days=30),
    date.today()
)
print(f'Fetched {len(stmt.raw_data)} bytes')
"
```

Target: < 3 seconds

**5. Multi-Account Performance**
```bash
time python -c "
import asyncio
from ib_sec_mcp.api.client import FlexQueryClient

async def fetch_all():
    # Fetch 5 accounts in parallel
    tasks = [...]
    return await asyncio.gather(*tasks)

asyncio.run(fetch_all())
"
```

Target: < 5 seconds for 5 accounts

**6. Memory Profiling**
```python
import tracemalloc

tracemalloc.start()

# Run operations
parser = CSVParser()
account = parser.to_account(large_file)

current, peak = tracemalloc.get_traced_memory()
print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
tracemalloc.stop()
```

Target: < 500MB peak

### Expected Output

```
=== Performance Benchmark Results ===
Date: 2025-10-11 14:30:00
Mode: FULL BENCHMARK

📊 CSV PARSING PERFORMANCE

Test: Parse 10K rows CSV
- Runs: 100
- Best: 423ms
- Average: 445ms
- Worst: 489ms
- Target: <500ms
- Status: ✅ PASS (11% under target)

Memory Usage:
- Peak: 87 MB
- Average: 78 MB
- Target: <100MB
- Status: ✅ PASS

⚡ ANALYZER PERFORMANCE

1. PerformanceAnalyzer
   - Time: 0.67s
   - Target: <1s
   - Status: ✅ PASS
   - Bottleneck: Decimal multiplication (342ms)

2. CostAnalyzer
   - Time: 0.45s
   - Target: <1s
   - Status: ✅ PASS

3. BondAnalyzer
   - Time: 1.23s
   - Target: <1s
   - Status: ⚠️ SLOW (23% over target)
   - Bottleneck: YTM calculation (890ms)

4. TaxAnalyzer
   - Time: 0.78s
   - Target: <1s
   - Status: ✅ PASS

5. RiskAnalyzer
   - Time: 0.91s
   - Target: <1s
   - Status: ✅ PASS

💰 DECIMAL OPERATIONS

Operation benchmarks (1M iterations):
- Multiplication: 0.123s (8.1M ops/sec)
- Addition: 0.089s (11.2M ops/sec)
- Division: 0.234s (4.3M ops/sec)

Status: ✅ Acceptable performance

🌐 API PERFORMANCE

Single Account Fetch:
- Total Time: 2.34s
- Network: 1.89s (81%)
- Processing: 0.45s (19%)
- Target: <3s
- Status: ✅ PASS

Multi-Account Fetch (5 accounts):
- Total Time: 3.12s
- Parallelization: 60% efficiency
- Target: <5s
- Status: ✅ PASS

🧠 MEMORY PROFILING

Component Memory Usage:
- CSV Parser: 87 MB
- Account Object: 45 MB
- All Analyzers: 156 MB
- Peak Total: 288 MB

Target: <500 MB
Status: ✅ PASS (42% under target)

🎯 PERFORMANCE SUMMARY

Overall Status: ⚠️ NEEDS OPTIMIZATION

Passing: 8/9 tests (89%)
Failing: 1/9 tests (11%)

Critical Issues:
1. ⚠️ BondAnalyzer YTM calculation slow (1.23s vs 1.0s target)

=== OPTIMIZATION RECOMMENDATIONS ===

🚨 HIGH PRIORITY (Critical Path)

1. Cache YTM Calculations (BondAnalyzer)
   - Current: 890ms for 1,234 calls
   - Issue: Recalculating same values repeatedly
   - Solution: Use @lru_cache(maxsize=256)
   - Expected Improvement: 70% reduction → 267ms
   - Impact: BondAnalyzer under 1s target

   Implementation:
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=256)
   def calculate_ytm(face_value: Decimal, price: Decimal, years: Decimal) -> Decimal:
       # existing logic
       pass
   ```

💡 MEDIUM PRIORITY (Nice to Have)

2. Optimize Decimal Constants
   - Current: Creating Decimal("1") repeatedly
   - Solution: Reuse constants (ZERO, ONE, HUNDRED)
   - Expected Improvement: 5-10% faster Decimal ops
   - Impact: Minor speedup across all analyzers

3. Stream CSV Processing
   - Current: Reading entire file into memory
   - Solution: Line-by-line generator
   - Expected Improvement: 30% less memory
   - Impact: Better for very large files (>100K rows)

🔍 LOW PRIORITY (Future Optimization)

4. Vectorize with NumPy
   - Consider NumPy for bulk calculations
   - Trade-off: Less precision than Decimal
   - Only for non-financial aggregations

5. Async API Improvements
   - Current parallelization: 60%
   - Add connection pooling
   - Expected: 80% parallelization

=== IMPLEMENTATION PLAN ===

Phase 1 (This Week):
1. ✅ Implement YTM caching → Test → Measure
   - Expected: BondAnalyzer <1s
   - Risk: Low (just caching)

Phase 2 (Next Week):
2. ✅ Optimize Decimal constants → Test → Measure
   - Expected: 5-10% overall improvement
   - Risk: Low (straightforward refactor)

Phase 3 (Future):
3. 🔄 Evaluate streaming CSV parser
   - Prototype and benchmark
   - Only if needed for large files

=== REGRESSION TRACKING ===

Baseline (2025-10-11):
- CSV Parse (10K): 445ms
- BondAnalyzer: 1.23s ⚠️
- Memory Peak: 288 MB
- API Fetch: 2.34s

Target After Phase 1:
- CSV Parse (10K): 445ms (no change)
- BondAnalyzer: <1.0s (18% improvement)
- Memory Peak: 288 MB (no change)
- API Fetch: 2.34s (no change)

Run this benchmark weekly to track performance trends.
```

### Benchmark Data Preparation

Before running benchmarks, ensure:

1. **Sample Data Available**:
   ```bash
   # Create 10K row sample if not exists
   head -n 10000 data/raw/large_file.csv > data/raw/sample_10k.csv
   ```

2. **Credentials Set**:
   ```bash
   # For API benchmarks
   test -f .env && echo "✓ Credentials ready"
   ```

3. **Clean State**:
   ```bash
   # Clear any caches
   rm -rf __pycache__
   rm -rf .pytest_cache
   ```

### Examples

```
/benchmark
/benchmark --quick
/benchmark --full
/benchmark performance
/benchmark bond
/benchmark parser
```

The **performance-optimizer** subagent will execute benchmarks, identify bottlenecks, and provide detailed optimization recommendations.
