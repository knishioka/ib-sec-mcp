---
description: Troubleshoot IB Flex Query API connection and data issues
allowed-tools: Read, Bash(python:*), Bash(curl:*), mcp__ib-sec-mcp__fetch_ib_data
argument-hint: [--verbose|--test-credentials]
---

# Debug API Issues

Troubleshoot IB Flex Query API connection and data fetching issues.

## What This Command Does

Performs systematic debugging of API-related issues:
1. Validates environment configuration
2. Tests API connectivity
3. Checks credentials
4. Inspects API responses
5. Provides actionable diagnostics

## Diagnostic Steps

### 1. Environment Check
- Verify `.env` file exists
- Check QUERY_ID and TOKEN are set
- Validate format (no spaces, correct length)
- Display masked credentials for verification

### 2. Configuration Validation
```python
from ib_sec_mcp.utils.config import Config

try:
    config = Config.load()
    credentials = config.get_credentials()
    print(f"✓ Found {len(credentials)} account(s)")
except Exception as e:
    print(f"✗ Config error: {e}")
```

### 3. API Connectivity Test
```python
from ib_sec_mcp.api.client import FlexQueryClient

client = FlexQueryClient(query_id="...", token="...")

# Test SendRequest endpoint
try:
    # Make a test request with minimal date range
    statement = client.fetch_statement(
        start_date=date.today() - timedelta(days=7),
        end_date=date.today()
    )
    print("✓ API connection successful")
except FlexQueryAPIError as e:
    print(f"✗ API error: {e}")
    # Provide specific guidance based on error
```

### 4. Response Inspection
- Display raw XML from SendRequest
- Show ReferenceCode
- Display first 500 chars of statement data
- Check for error codes in response

### 5. Common Issues & Solutions

**Issue**: "Invalid token"
- **Solution**: Regenerate token in IB Account Management

**Issue**: "Query not found"
- **Solution**: Verify QUERY_ID matches Flex Query configuration

**Issue**: "Statement not ready"
- **Solution**: Increase retry delay (default: 5 seconds)

**Issue**: "Connection timeout"
- **Solution**: Check internet connection, try again later

**Issue**: "Rate limit exceeded"
- **Solution**: Wait 5 minutes before retrying

## Detailed Logging

Enable detailed logging for debugging:
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("ib_sec_mcp")

# Now all API calls will be logged
```

## Network Diagnostics

Test basic connectivity:
```bash
# Test DNS resolution
ping ndcdyn.interactivebrokers.com

# Test HTTPS connection
curl -I https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest
```

## Arguments

$ARGUMENTS can specify:
- `--verbose`: Show detailed debug output
- `--test-credentials`: Test credentials without fetching data

## Example Usage

```
/debug-api
/debug-api --verbose
/debug-api --test-credentials
```

## Output Format

```
=== IB API Diagnostics ===

[1/5] Environment Check
✓ .env file found
✓ QUERY_ID: 1304*** (7 digits)
✓ TOKEN: 186998*** (21 digits)

[2/5] Configuration Validation
✓ Config loaded successfully
✓ 1 account configured

[3/5] API Connectivity Test
→ Sending request to SendRequest endpoint...
✓ Request successful
✓ ReferenceCode received: 123456789

[4/5] Statement Fetch Test
→ Waiting for statement generation...
✓ Statement retrieved (2,456 bytes)

[5/5] Data Validation
✓ CSV format detected
✓ Account ID: U1234567
✓ Date range: 2025-10-01 to 2025-10-06

=== Diagnostics Complete ===
All systems operational
```

Use this command when API calls fail or data fetching issues occur.
