---
description: Comprehensive investment strategy combining portfolio and market analysis with actionable plans
allowed-tools: Task
argument-hint: [--profile growth|income|preservation|balanced] [--horizon short|medium|long] [--save]
---

Generate comprehensive investment strategy by integrating portfolio analysis with market analysis to create unified, actionable recommendations.

**New Features**:
- **Investment Profiles**: Customize recommendations for growth, income, preservation, or balanced objectives
- **Investment Horizons**: Adjust strategy for short (1-2yr), medium (3-5yr), or long (10+yr) time frames
- **Market Context**: Includes macro sentiment (SPY/QQQ) and sector-level analysis

**Performance Optimization**: Uses **batched sub-agent execution** with Top 5 holdings focus, achieving **8-10 minute completion** (1+ minute safety margin).

## Task

Delegate to the **strategy-coordinator** subagent to orchestrate comprehensive investment strategy development.

### Command Usage

```bash
# Basic (defaults: balanced profile, long horizon)
/investment-strategy

# With investment profile
/investment-strategy --profile growth        # Growth-focused (stocks 70-80%)
/investment-strategy --profile income        # Income-focused (dividends, bonds)
/investment-strategy --profile preservation  # Capital preservation (low risk)
/investment-strategy --profile balanced      # Balanced (default)

# With investment horizon
/investment-strategy --horizon short         # 1-2 years
/investment-strategy --horizon medium        # 3-5 years
/investment-strategy --horizon long          # 10+ years

# Combined options
/investment-strategy --profile growth --horizon long --save
```

### Investment Profiles

| Profile | Stocks | Bonds | Cash | Focus |
|---------|--------|-------|------|-------|
| `growth` | 70-80% | 10-20% | 5-10% | Capital gains, tech, emerging markets |
| `income` | 40-50% | 30-40% | 10-20% | Dividends, yields, stability |
| `preservation` | 20-30% | 40-50% | 20-30% | Principal protection, low volatility |
| `balanced` | 50-60% | 20-30% | 15-25% | Diversification, moderate risk |

### Investment Horizons

| Horizon | Time | Stock Emphasis | Volatility | Preferred Assets |
|---------|------|----------------|------------|------------------|
| `short` | 1-2 yr | Lower | Low | IB01, short bonds, dividends |
| `medium` | 3-5 yr | Moderate | Medium | Index ETFs, balanced |
| `long` (default) | 10+ yr | Higher | High | Growth stocks, STRIPS, EM |

### What This Command Does

The **strategy-coordinator** subagent will:

**1. Portfolio Analysis + Macro Context** (2 min, parallel)
- Load latest portfolio data via MCP
- Analyze CONSOLIDATED metrics across ALL accounts
- Identify top 5 holdings by value
- Assess asset allocation and concentration risks
- **Analyze macro sentiment** (SPY/QQQ news and sentiment)

**2. Sector Sentiment Analysis** (30 sec)
- Analyze sentiment for relevant sectors (Tech, Financials, Healthcare, Bonds)
- Map sector trends to portfolio holdings
- Identify sector-level opportunities and risks

**3. Market Analysis** (3.5 min)
- Analyze **TOP 5 HOLDINGS ONLY** with comprehensive market analysis
- Launch 5 market-analyst instances in parallel
- Each holding receives:
  * Technical analysis (RSI, MACD, trends, support/resistance)
  * **Sentiment score and key news** (new!)
  * Trading recommendations (BUY/SELL/HOLD with specific prices)
  * Risk assessment and conviction scoring
- Remaining holdings: brief portfolio-based recommendations only

**4. Strategy Synthesis** (2 min)
- Integrate portfolio metrics with market analysis
- **Apply profile and horizon preferences** (new!)
- Generate streamlined report (~5K tokens):
  * Executive summary (key findings only)
  * **📰 Market Context** (macro + sector sentiment, new!)
  * Top 5 holdings with detailed recommendations + sentiment
  * Remaining holdings with brief notes
  * Portfolio-level strategy (allocation, tax, risk)
  * Prioritized action plan (urgent, high, medium priority)
  * Expected outcomes

**Total Time**: 8-10 minutes (within 10 min limit)

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

**Parse Arguments**:
- Extract --profile from arguments (default: balanced)
- Extract --horizon from arguments (default: long)
- Extract --save flag if present

1. Portfolio Analysis + Macro Context (parallel):
   - Call analyze_consolidated_portfolio MCP tool directly
   - Call analyze_market_sentiment("SPY", sources="composite") for macro context
   - Call get_stock_news("SPY", limit=5) for market headlines
   - Extract top 5 holdings by value for detailed analysis
   - Note asset allocation and concentration risks

2. Sector Sentiment Analysis:
   - Analyze sentiment for sectors relevant to portfolio holdings
   - Map to: Technology (QQQ), Financials (XLF), Healthcare (XLV), Bonds (TLT)

3. Market Analysis (Batched):
   - Launch 5 market-analyst subagents in parallel (single message, multiple Task calls)
   - Analyze TOP 5 HOLDINGS ONLY
   - Request focused analysis (target ~700 tokens each):
     * Technical analysis (RSI, MACD, trends, support/resistance)
     * Sentiment score and key news (CRITICAL: use analyze_market_sentiment)
     * Trading recommendations (BUY/SELL/HOLD with specific prices)
     * Options strategy (if applicable)
     * Risk assessment and conviction score (1-10)

4. Strategy Synthesis:
   - Apply investment profile: [profile from arguments]
   - Apply investment horizon: [horizon from arguments]
   - Generate streamlined report following your defined format
   - Include 📰 MARKET CONTEXT section with macro + sector sentiment
   - Top 5 holdings: detailed recommendations with sentiment
   - Remaining holdings: 1-line summaries
   - Portfolio-level strategy: allocation, tax, risk management (adjusted for profile/horizon)
   - Action plan: prioritized by urgency

5. Expected Output:
   - Executive summary with profile/horizon context
   - 📰 Market Context (macro sentiment + sector breakdown)
   - Position-by-position recommendations (detailed for top 5, with sentiment)
   - Portfolio-level strategy (adjusted for profile and horizon)
   - Prioritized action plan (urgent/high/medium priority)
   - Expected outcomes (quantified improvements)

$ARGUMENTS
```

### Output Format

See `.claude/agents/strategy-coordinator.md` for complete streamlined output format.

**Key Sections**:
- Executive Summary (~500 tokens) - includes profile/horizon context
- **📰 Market Context** (~600 tokens) - macro + sector sentiment (NEW!)
- Top 5 Holdings - Detailed Recommendations (~1,750 tokens) - includes sentiment
- Remaining Holdings - Brief Notes (~500 tokens)
- Portfolio-Level Strategy (~800 tokens) - adjusted for profile/horizon
- Prioritized Action Plan (~400 tokens)
- Expected Outcomes (~300 tokens)

**Total**: ~4,850 tokens (optimized format with market context)

### Output Saving

If `--save` flag provided, save strategy to:
```
data/processed/investment_strategy_YYYY-MM-DD.txt
```

### Use Cases

**Quarterly Portfolio Review** (Balanced):
```bash
/investment-strategy
```
Get comprehensive strategy update with top holdings focus.

**Growth-Focused Long-Term Investor**:
```bash
/investment-strategy --profile growth --horizon long
```
Maximize capital appreciation, accept higher volatility.

**Retirement Income Focus**:
```bash
/investment-strategy --profile income --horizon medium
```
Prioritize dividends and yields, moderate risk.

**Capital Preservation (Near-Term Goals)**:
```bash
/investment-strategy --profile preservation --horizon short
```
Protect principal, minimize volatility.

**After Major Market Move**:
```bash
/investment-strategy
```
Reassess top positions with current market sentiment.

**Tax Planning Season**:
```bash
/investment-strategy --save
```
Generate and save strategy with tax optimization.

**New Capital to Deploy**:
```bash
/investment-strategy --profile growth
```
Identify best growth opportunities for new capital.

### Performance Benefits

**Old Design** (Before Optimization):
- Analyzed all 15 holdings in detail
- 15+ minutes runtime → timeout
- 15K+ token output
- No market context
- ❌ Failed to complete

**Current Design** (Optimized with Market Context):
- Analyzes top 5 holdings in detail
- **Includes macro + sector sentiment** (new!)
- **Profile and horizon customization** (new!)
- 8-10 minutes runtime ✓
- ~5K token output
- ✅ Reliable completion with rich context

### Integration

This is the **master strategy command** that:
1. Coordinates portfolio and market perspectives
2. Provides actionable, prioritized recommendations
3. Considers performance, taxes, risks, market conditions
4. Completes reliably within timeout constraints

### Feature Scope

**✅ What This Command Analyzes**:
- **Macro Environment**: SPY/QQQ sentiment, Fed policy news, market themes
- **Sector Sentiment**: Tech, Financials, Healthcare, Bonds trends
- **Top 5 Holdings**: Full technical + sentiment + news + options analysis
- **Remaining Holdings**: Brief recommendations based on portfolio data
- **Portfolio-Level**: Asset allocation, tax optimization, risk management
- **Action Plan**: Prioritized by urgency (urgent/high/medium)
- **Profile/Horizon**: Customized recommendations based on investor preferences

**❌ What This Command Does NOT Analyze**:
- Holdings outside Top 5 (no detailed technical/sentiment analysis)
- Symbols not in your portfolio (use `/analyze-symbol` instead)
- Comparison of alternative investments (use `/compare-etf` instead)

**📊 Analysis Depth by Position**:
| Position | Technical | Sentiment | News | Options | Recommendation |
|----------|-----------|-----------|------|---------|----------------|
| Macro (SPY) | ❌ | ✅ Full | ✅ Yes | ❌ | ✅ Context |
| Sectors | ❌ | ✅ Brief | ❌ | ❌ | ✅ Impact |
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
