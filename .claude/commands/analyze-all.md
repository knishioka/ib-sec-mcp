# Comprehensive Analysis

Run a comprehensive analysis on IB trading data including all available analyzers.

## What This Command Does

1. Loads the most recent CSV data file from `data/raw/`
2. Parses the data using CSVParser
3. Runs all 5 analyzers:
   - Performance (win rate, profit factor, ROI)
   - Cost (commission analysis)
   - Bond (zero-coupon bond analytics)
   - Tax (phantom income and capital gains)
   - Risk (interest rate scenarios)
4. Generates a comprehensive console report
5. Saves results to `data/processed/`

## Steps to Execute

1. Find the most recent CSV file in `data/raw/` directory
2. Load and parse the CSV data
3. Create Account object from parsed data
4. Instantiate all 5 analyzers with the account
5. Run each analyzer and collect results
6. Generate ConsoleReport with all results
7. Display the report to console
8. Save report to `data/processed/analysis_report_[timestamp].txt`

## Arguments

$ARGUMENTS can specify:
- Custom data file path (optional)
- Tax rate (default: 0.30)

## Example Usage

```
/analyze-all
/analyze-all data/raw/U1234567_2025-01-01_2025-10-05.csv
/analyze-all --tax-rate 0.25
```

## Expected Output

A comprehensive report showing:
- Overall performance metrics
- Win/loss breakdown
- Cost efficiency analysis
- Current bond holdings with YTM and duration
- Tax liability estimates
- Interest rate risk scenarios

Use this command when you want a complete view of portfolio performance.
