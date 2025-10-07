# Fetch Latest Data

Fetch the most recent trading data from Interactive Brokers Flex Query API.

## What This Command Does

1. Loads credentials from `.env` file
2. Determines appropriate date range:
   - Start: Beginning of current year OR last data fetch date + 1 day
   - End: Today
3. Fetches data using FlexQueryClient
4. Saves to `data/raw/` with standardized filename

## Steps to Execute

1. Load Config from `.env`
2. Check `data/raw/` for most recent file to determine date range
3. Initialize FlexQueryClient with credentials
4. Call `fetch_statement()` with calculated date range
5. Save raw CSV data to `data/raw/[account_id]_[from]_[to].csv`
6. Display success message with file location

## Multi-Account Support

If $ARGUMENTS contains `--multi-account` or multiple accounts are configured:
- Use `fetch_all_statements_async()` for parallel fetching
- Save separate file for each account

## Arguments

$ARGUMENTS can specify:
- `--multi-account`: Fetch all configured accounts
- `--start-date YYYY-MM-DD`: Override start date
- `--end-date YYYY-MM-DD`: Override end date

## Example Usage

```
/fetch-latest
/fetch-latest --multi-account
/fetch-latest --start-date 2025-01-01
```

## Error Handling

- If credentials missing: Display helpful error about .env setup
- If API fails: Retry with exponential backoff (3 attempts)
- If network error: Suggest checking connection

This command ensures you always have up-to-date data for analysis.
