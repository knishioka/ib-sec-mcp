---
description: Comprehensive investment strategy combining portfolio and market analysis with actionable plans
allowed-tools: Task
argument-hint: [--save]
---

Generate comprehensive investment strategy by integrating portfolio analysis with market analysis to create unified, actionable recommendations.

**Performance Optimization**: Uses **batched sub-agent execution** with Top 5 holdings focus, achieving **6-8 minute completion** (2+ minute safety margin).

## Task

Delegate to the **strategy-coordinator** subagent to orchestrate comprehensive investment strategy development.

### Command Usage

```bash
/investment-strategy          # Generate strategy
/investment-strategy --save   # Generate and save to file
```

### What This Command Does

The **strategy-coordinator** subagent will:

**1. Portfolio Analysis** (2 min)
- Load latest portfolio data via MCP
- Analyze CONSOLIDATED metrics across ALL accounts
- Identify top 5 holdings by value
- Assess asset allocation and concentration risks

**2. Market Analysis** (3-5 min)
- Analyze **TOP 5 HOLDINGS ONLY** with comprehensive market analysis
- Launch 5 market-analyst instances in parallel
- Each holding receives:
  * Technical analysis (RSI, MACD, trends, support/resistance)
  * Market sentiment (news headlines, options market indicators)
  * Trading recommendations (BUY/SELL/HOLD with specific prices)
  * Risk assessment and conviction scoring
- Remaining holdings: brief portfolio-based recommendations only

**3. Strategy Synthesis** (2-3 min)
- Integrate portfolio metrics with market analysis
- Generate streamlined report (~4K tokens vs 15K+ old format):
  * Executive summary (key findings only)
  * Top 5 holdings with detailed recommendations
  * Remaining holdings with brief notes
  * Portfolio-level strategy (allocation, tax, risk)
  * Prioritized action plan (urgent, high, medium priority)
  * Expected outcomes

**Total Time**: 6-8 minutes (safe within 10 min limit)

## Data Integrity Protection

**Pre-Execution Validation** (Automatic):
The strategy-coordinator subagent will:
1. Verify MCP server connectivity
2. Confirm `analyze_consolidated_portfolio` tool is available
3. Validate portfolio data has > 0 positions
4. If ANY check fails → Return error, ABORT analysis

**Abort Conditions** (Analysis will not proceed if):
- MCP server unavailable
- No XML files in `data/raw/` AND credentials not configured
- Portfolio analysis returns 0 accounts or 0 positions
- Any MCP tool returns critical error

**Error Response Template**:
```
❌ INVESTMENT STRATEGY ABORTED

Reason: [specific error from MCP or sub-agent]
Tool Failed: [tool name if applicable]
Data Source: [FAILED / UNAVAILABLE]

Recovery Steps:
1. Check MCP server status: /mcp-status
2. Verify credentials: Ensure .env has QUERY_ID and TOKEN
3. Fetch latest data: /fetch-latest
4. Retry: /investment-strategy

⚠️  CRITICAL: Investment recommendations require accurate, real-time data.
Analysis cannot proceed with missing, stale, or synthetic data.

Alternative: Try focused analysis commands
- /optimize-portfolio (portfolio analysis only)
- /analyze-symbol SYMBOL (individual stock analysis)
```

### Delegation Instructions

```
Use the strategy-coordinator subagent to generate investment strategy:

Please orchestrate the following:

1. Portfolio Analysis:
   - Call analyze_consolidated_portfolio MCP tool directly
   - Extract top 5 holdings by value for detailed analysis
   - Note asset allocation and concentration risks

2. Market Analysis (Batched):
   - Launch 5 market-analyst subagents in parallel (single message, multiple Task calls)
   - Analyze TOP 5 HOLDINGS ONLY
   - Request focused analysis (target ~800 tokens each, max 1,200):
     * Technical analysis (RSI, MACD, trends, support/resistance)
     * Market sentiment (news headlines, options market indicators)
     * Trading recommendations (BUY/SELL/HOLD with specific prices)
     * Options strategy (if applicable)
     * Risk assessment and conviction score (1-10)

3. Strategy Synthesis:
   - Generate streamlined report following your defined format
   - Top 5 holdings: detailed recommendations
   - Remaining holdings: 1-line summaries
   - Portfolio-level strategy: allocation, tax, risk management
   - Action plan: prioritized by urgency

4. Expected Output:
   - Executive summary (3-5 bullets for strengths/concerns)
   - Position-by-position recommendations (detailed for top 5)
   - Portfolio-level strategy (allocation, tax optimization, risk management)
   - Prioritized action plan (urgent/high/medium priority)
   - Expected outcomes (quantified improvements)

$ARGUMENTS
```

### Output Format

See `.claude/agents/strategy-coordinator.md` for complete streamlined output format.

**Key Sections**:
- Executive Summary (~500 tokens)
- Top 5 Holdings - Detailed Recommendations (~1,500 tokens)
- Remaining Holdings - Brief Notes (~500 tokens)
- Portfolio-Level Strategy (~800 tokens)
- Prioritized Action Plan (~400 tokens)
- Expected Outcomes (~300 tokens)

**Total**: ~4,000 tokens (70% reduction from old format)

### Output Saving

If `--save` flag provided, save strategy to:
```
data/processed/investment_strategy_YYYY-MM-DD.txt
```

### Use Cases

**Quarterly Portfolio Review**:
```bash
/investment-strategy
```
Get comprehensive strategy update with top holdings focus.

**After Major Market Move**:
```bash
/investment-strategy
```
Reassess top positions and adjust strategy.

**Tax Planning Season**:
```bash
/investment-strategy --save
```
Generate and save strategy with tax optimization.

**New Capital to Deploy**:
```bash
/investment-strategy
```
Identify best opportunities for allocation.

### Performance Benefits

**Old Design** (Before Optimization):
- Analyzed all 15 holdings in detail
- 15+ minutes runtime → timeout
- 15K+ token output
- ❌ Failed to complete

**New Design** (Optimized):
- Analyzes top 5 holdings in detail
- 6-8 minutes runtime ✓
- ~4K token output
- ✅ Reliable completion

### Integration

This is the **master strategy command** that:
1. Coordinates portfolio and market perspectives
2. Provides actionable, prioritized recommendations
3. Considers performance, taxes, risks, market conditions
4. Completes reliably within timeout constraints

### Feature Scope

**✅ What This Command Analyzes**:
- **Top 5 Holdings**: Full technical + sentiment + news + options analysis
- **Remaining Holdings**: Brief recommendations based on portfolio data
- **Portfolio-Level**: Asset allocation, tax optimization, risk management
- **Action Plan**: Prioritized by urgency (urgent/high/medium)

**❌ What This Command Does NOT Analyze**:
- Holdings outside Top 5 (no detailed technical/sentiment analysis)
- Symbols not in your portfolio (use `/analyze-symbol` instead)
- Comparison of alternative investments (use `/compare-etf` instead)

**📊 Analysis Depth by Position**:
| Position | Technical | Sentiment | News | Options | Recommendation |
|----------|-----------|-----------|------|---------|----------------|
| Top 1-5  | ✅ Full   | ✅ Full   | ✅ Yes | ✅ Yes  | ✅ Detailed    |
| Top 6+   | ❌ None   | ❌ None   | ❌ No  | ❌ No   | ⚠️ Brief only  |

### Important Limitations

**Limit Order Recommendations**:
- This command provides **general direction** (e.g., "consider adding CSPX")
- It does **NOT** provide specific limit prices or order quantities
- For precise entry/exit prices, use `/analyze-symbol SYMBOL` on the specific stock

**Example Workflow**:
```bash
# Step 1: Get overall strategy
/investment-strategy
# Output: "Consider adding S&P 500 exposure (CSPX)"

# Step 2: Get specific entry prices for new investments
/analyze-symbol SPY  # or CSPX
# Output: "Entry: $713-716, Stop: $707, Target: $724-737"
```

**Why This Design**:
- `/investment-strategy` focuses on portfolio-level decisions
- `/analyze-symbol` focuses on precise trade execution
- Combining both gives optimal results

### Related Commands

For focused analysis:
- `/analyze-symbol SYMBOL` - Individual stock deep dive with precise entry/exit prices
- `/options-strategy SYMBOL` - Options-focused analysis
- `/optimize-portfolio` - Portfolio optimization only
- `/tax-report` - Tax-focused analysis only

### Troubleshooting

**If command times out**:
- Try individual commands instead:
  ```bash
  /optimize-portfolio           # Portfolio analysis
  /analyze-symbol 9433.T        # Top holding
  /analyze-symbol INDA          # Second holding
  ```

**If output is too long**:
- strategy-coordinator will automatically prioritize top 3 holdings
- Remaining holdings get 1-line summaries

**If market analysis fails**:
- strategy-coordinator falls back to portfolio data only
- Will note "[Analysis unavailable - using portfolio data]"

The **strategy-coordinator** subagent orchestrates the entire process, ensuring efficient, actionable investment strategy generation.
