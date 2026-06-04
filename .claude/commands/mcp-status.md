---
description: Check MCP server health and tool availability
allowed-tools: mcp__ib-sec-mcp__fetch_ib_data, mcp__ib-sec-mcp__analyze_performance, mcp__ib-sec-mcp__analyze_consolidated_portfolio, Read, Bash(python:*)
argument-hint: [--verbose|--test]
---

Check the health and status of IB Analytics MCP server and its tools.

## Task

Verify MCP server connectivity, tool availability, and basic functionality.

### Health Checks

**1. Server Connectivity**

```python
# Check if MCP server is running
try:
    # Attempt simple MCP call
    result = mcp__ib-sec-mcp__analyze_consolidated_portfolio(file_path="test")
    print("✅ MCP server responding")
except Exception as e:
    print(f"❌ MCP server error: {e}")
```

**2. Tool Availability**

Check all 7 MCP tools:

1. `fetch_ib_data` - Data fetching
2. `analyze_performance` - Performance metrics
3. `analyze_costs` - Cost analysis
4. `analyze_bonds` - Bond analytics
5. `analyze_tax` - Tax calculations
6. `analyze_risk` - Risk assessment
7. `analyze_consolidated_portfolio` - Consolidated portfolio overview

**3. Credential Validation**

```bash
# Check .env credentials
if [ -f .env ]; then
    grep -E "^(QUERY_ID|TOKEN)=" .env
    echo "✅ Credentials configured"
else
    echo "❌ No .env file found"
fi
```

**4. Data Availability**

```bash
# Check for CSV files
ls -lh data/raw/*.csv 2>/dev/null | wc -l
```

**5. Resource Access**

Test MCP resources (6 URIs):

- `ib://portfolio/list`
- `ib://portfolio/latest`
- `ib://accounts/{account_id}`
- `ib://trades/recent`
- `ib://positions/current`

### Expected Output

```
=== MCP Server Health Check ===
Date: 2025-10-11 15:00:00

🔧 SERVER STATUS

MCP Server: ib-sec-mcp
Status: ✅ RUNNING
Transport: stdio
Process: Running (PID: 12345)

🛠️ TOOL AVAILABILITY (7 tools)

1. fetch_ib_data
   Status: ✅ Available
   Purpose: Fetch data from IB Flex Query API
   Args: start_date, end_date, account_index, use_cache

2. analyze_performance
   Status: ✅ Available
   Purpose: Trading performance metrics
   Args: start_date, end_date, account_index, use_cache

3. analyze_costs
   Status: ✅ Available
   Purpose: Commission and cost analysis
   Args: start_date, end_date, account_index, use_cache

4. analyze_bonds
   Status: ✅ Available
   Purpose: Zero-coupon bond analytics
   Args: start_date, end_date, account_index, use_cache

5. analyze_tax
   Status: ✅ Available
   Purpose: Tax liability including phantom income
   Args: start_date, end_date, account_index, use_cache

6. analyze_risk
   Status: ✅ Available
   Purpose: Portfolio risk with interest rate scenarios
   Args: start_date, end_date, interest_rate_change, account_index, use_cache

7. analyze_consolidated_portfolio
   Status: ✅ Available
   Purpose: Consolidated portfolio overview (holdings, allocation, concentration risk)
   Args: file_path

🔐 CREDENTIALS CHECK

Environment Variables:
✅ QUERY_ID: 1304*** (7 characters)
✅ TOKEN: 186998*** (21 characters)
✅ .env file: Present

Credential Format:
✅ QUERY_ID is numeric
✅ TOKEN is alphanumeric
✅ No spaces detected

📁 DATA AVAILABILITY

CSV Files in data/raw/:
- Total files: 12
- Latest: U1234567_2025-01-01_2025-10-05.csv (2.4 MB)
- Oldest: U1234567_2024-01-01_2024-12-31.csv (8.1 MB)
- Total size: 45.6 MB

Status: ✅ Data available for analysis

📋 RESOURCE AVAILABILITY (6 resources)

1. ib://portfolio/list
   Status: ✅ Available
   Description: List available CSV files
   Data: 12 files found

2. ib://portfolio/latest
   Status: ✅ Available
   Description: Latest portfolio summary
   Data: U1234567_2025-01-01_2025-10-05.csv

3. ib://accounts/{account_id}
   Status: ✅ Available
   Description: Specific account data
   Example: ib://accounts/U1234567

4. ib://trades/recent
   Status: ✅ Available
   Description: Recent trades (last 10)
   Data: 10 trades from 2025-10-01 to 2025-10-05

5. ib://positions/current
   Status: ✅ Available
   Description: Current positions
   Data: 45 positions

6. ib://prompts
   Status: ✅ Available
   Description: 5 prompt templates available
   Templates: analyze_portfolio, tax_planning, risk_assessment, etc.

🧪 FUNCTIONALITY TEST

Running basic tool test...

Test 1: analyze_consolidated_portfolio
- Input: data/raw/U1234567_2025-01-01_2025-10-05.xml
- Result: ✅ Success
- Response time: 234ms
- Data: Account U1234567, 1,234 trades, 45 positions

Test 2: analyze_performance (cached)
- Input: 2025-01-01 to 2025-10-05
- Result: ✅ Success
- Response time: 89ms (cached)
- Metrics: P&L, win rate, profit factor returned

=== HEALTH CHECK SUMMARY ===

Overall Status: ✅ HEALTHY

Component Status:
✅ MCP Server: Running
✅ Tools: 7/7 available (100%)
✅ Credentials: Valid
✅ Data Files: 12 available
✅ Resources: 6/6 accessible (100%)
✅ Functionality: Tests passed

Performance:
- Tool response: <250ms
- Cached response: <100ms
- Status: ✅ Normal

Recommendations:
✅ System ready for analysis
✅ All components operational
✅ No issues detected

Next Steps:
1. Run /fetch-latest to update data
2. Use /optimize-portfolio for analysis
3. Generate /tax-report for planning
```

### Verbose Mode

If $ARGUMENTS contains `--verbose`:

- Show detailed tool signatures
- Display all resource URIs
- List all prompt templates
- Show environment variables (masked)
- Include debug logs

### Test Mode

If $ARGUMENTS contains `--test`:

- Run actual API test (requires credentials)
- Fetch minimal data (last 7 days)
- Validate response format
- Measure response times
- Test caching functionality

### Troubleshooting Outputs

**If MCP Server Not Running**:

```
❌ MCP SERVER ERROR

Status: NOT RUNNING
Error: Connection refused

Troubleshooting Steps:
1. Check Claude Desktop config:
   ~/Library/Application Support/Claude/claude_desktop_config.json

2. Verify Python path in config:
   "command": "/path/to/venv/bin/python"

3. Restart Claude Desktop

4. Check server logs:
   tail -f ~/Library/Logs/Claude/mcp-ib-sec-mcp.log
```

**If Credentials Missing**:

```
❌ CREDENTIALS ERROR

Status: NOT CONFIGURED
Error: .env file not found

Setup Steps:
1. Create .env file in project root:
   touch .env

2. Add credentials:
   QUERY_ID=your_query_id
   TOKEN=your_token

3. Verify format:
   cat .env

4. Re-run health check
```

**If Tools Not Available**:

```
❌ TOOL AVAILABILITY ERROR

Status: PARTIAL
Available: 0/7 tools

Possible Causes:
1. MCP server not properly installed
   pip install -e ".[mcp]"

2. Server not configured in Claude Desktop

3. Import errors in server code
   python -m ib_sec_mcp.mcp.server

4. Check server logs for errors
```

### Examples

```
/mcp-status
/mcp-status --verbose
/mcp-status --test
```

Use this command to verify MCP setup and troubleshoot any connectivity issues.
