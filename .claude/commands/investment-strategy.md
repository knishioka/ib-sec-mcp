---
description: Comprehensive investment strategy combining portfolio analysis and market analysis for actionable recommendations
allowed-tools: Task
argument-hint: [--save]
---

Generate comprehensive investment strategy by integrating portfolio analysis (from data-analyzer) with market analysis (from market-analyst) to create unified, actionable recommendations.

## Task

Delegate to the **strategy-coordinator** subagent to orchestrate comprehensive investment strategy development.

### Command Usage

```bash
/investment-strategy
/investment-strategy --save
```

### Strategy Development Process

The **strategy-coordinator** subagent will:

**1. Orchestrate Portfolio Analysis (via data-analyzer)**
- Load latest portfolio data
- Analyze performance, costs, bonds, taxes, risks
- Identify current holdings and their status
- Assess portfolio strengths and weaknesses

**2. Orchestrate Market Analysis (via market-analyst)**
- Analyze each current holding:
  - Technical outlook
  - Entry/exit signals
  - Options strategies
  - News and catalysts
- Analyze candidate positions:
  - Market opportunities
  - Technical setups
  - Options strategies

**3. Synthesize Unified Strategy**
- Integrate portfolio metrics with market outlook
- Balance risk and return
- Consider tax implications
- Prioritize actions by urgency and impact
- Create executable action plan

### Delegation Instructions

```
Use the strategy-coordinator subagent to generate comprehensive investment strategy:

Please orchestrate the following:

1. Portfolio Analysis Phase:
   - Delegate to data-analyzer subagent
   - Get current holdings with performance metrics
   - Analyze tax situation and risk profile
   - Identify portfolio strengths and concerns

2. Market Analysis Phase:
   - Delegate to market-analyst subagent
   - Analyze each current holding (technical, options)
   - Identify new position candidates
   - Assess market opportunities and risks

3. Strategy Synthesis:
   - For each current holding:
     - Combine portfolio metrics with market outlook
     - Recommend: HOLD/SELL/TRIM/ADD with rationale
     - Consider tax implications
     - Suggest options strategies

   - For new positions:
     - Identify candidates based on portfolio gaps
     - Analyze technical setups and entry points
     - Define position sizing and risk management

   - Portfolio-level recommendations:
     - Rebalancing needs
     - Tax optimization strategies
     - Options for income/protection
     - Risk management adjustments

4. Action Prioritization:
   - Urgent actions (this week)
   - High priority (this month)
   - Medium priority (this quarter)
   - Monitoring points (ongoing)

5. Expected Outcomes:
   - Portfolio improvements
   - Risk/return adjustments
   - Tax savings
   - Performance targets

Generate comprehensive investment strategy report with specific, actionable recommendations.

$ARGUMENTS
```

### Expected Output Format

```
=== COMPREHENSIVE INVESTMENT STRATEGY ===
Generated: [DATE]
Portfolio Value: $XXX,XXX
Analysis Period: [START] to [END]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Portfolio Health: [EXCELLENT|GOOD|FAIR|NEEDS ATTENTION]

Performance Summary:
- YTD Return: +X.X%
- Total P&L: $X,XXX
- Win Rate: XX%
- Sharpe Ratio: X.XX

Key Findings:
✅ Strengths:
   • [Strength 1: e.g., Strong YTD performance +18.5%]
   • [Strength 2: e.g., Well-diversified bond ladder]
   • [Strength 3: e.g., Low cost structure]

⚠️ Concerns:
   • [Concern 1: e.g., Overconcentration in tech sector (45%)]
   • [Concern 2: e.g., Short-term capital gains tax exposure]
   • [Concern 3: e.g., Negative technical signals on key holdings]

💡 Strategic Direction:
[2-3 paragraph summary of recommended strategic direction]

Expected Impact:
- Return Improvement: +X% to +Y%
- Risk Reduction: -X% maximum drawdown
- Tax Savings: $X,XXX
- Income Generation: $XXX/month from options

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 POSITION-BY-POSITION RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Current Holdings

**1. [SYMBOL] - XXX shares @ $XXX.XX**
   Current Price: $XXX.XX | Cost Basis: $XXX.XX
   Position Value: $XX,XXX | P&L: +$X,XXX (+XX.X%)

   📊 Portfolio Analysis (from data-analyzer):
   - Performance: [Win rate, profit factor if traded]
   - Position Size: XX.X% of portfolio
   - Tax Status: [Short-term/Long-term] gain
   - Holding Period: XXX days
   - Risk Contribution: [Concentration, correlation]

   📈 Market Analysis (from market-analyst):
   - Technical Outlook: [BULLISH/NEUTRAL/BEARISH]
   - Daily Trend: [Description]
   - Weekly Trend: [Description]
   - Monthly Trend: [Description]
   - Timeframe Confluence: [HIGH/MEDIUM/LOW]

   - Key Levels:
     Support: $XXX.XX
     Resistance: $XXX.XX
     Stop Loss: $XXX.XX

   - IV Environment: [HIGH/MEDIUM/LOW] (Rank: XX)
   - Options Strategy: [Covered calls / Protective puts / etc.]

   - Recent News: [Summary]
   - Sentiment: [POSITIVE/NEUTRAL/NEGATIVE]

   🎯 INTEGRATED RECOMMENDATION: [HOLD / SELL / TRIM / ADD]
   Conviction: [HIGH/MEDIUM/LOW] (X/10)

   Rationale:
   [Synthesis of portfolio metrics and market outlook]
   - Portfolio perspective: [How it fits current portfolio]
   - Market perspective: [Technical and fundamental outlook]
   - Tax consideration: [Hold for LT / Harvest loss / etc.]

   Action Plan:
   Primary Action:
   - [Specific action: e.g., HOLD with covered call strategy]
   - [Price targets and stop loss]
   - [Position sizing: maintain / reduce to X% / add to X%]

   Options Strategy:
   - [If applicable: Covered call at $XXX strike, earn $XXX premium]
   - [Or: Protective put at $XXX strike for downside protection]

   Tax Strategy:
   - [Hold until [DATE] for long-term treatment, saving $XXX]
   - [Or: Harvest loss to offset gains, saving $XXX]

   Risk Management:
   - Stop Loss: $XXX.XX (XX% below current)
   - Profit Target: $XXX.XX (XX% above current)
   - Review triggers: [Specific conditions to reassess]

   Expected Outcome:
   - Best Case: +$X,XXX if reaches $XXX
   - Base Case: +$XXX with covered calls
   - Worst Case: -$XXX if stop loss hit

**2. [SYMBOL] - [POSITION]**
   [Same detailed format for each holding]

**3. [SYMBOL] - [POSITION]**
   [Continue for all holdings]

### New Position Candidates

**A. [SYMBOL] - Proposed New Position**
   Opportunity: [Why this fills portfolio gap or represents opportunity]

   📈 Market Analysis:
   - Technical Setup: [Description of entry opportunity]
   - Trend: [Daily/Weekly/Monthly alignment]
   - Entry Zone: $XXX.XX - $XXX.XX
   - Stop Loss: $XXX.XX
   - Target 1: $XXX.XX
   - Target 2: $XXX.XX
   - Risk/Reward: 1:X.X

   - IV Environment: [For options strategies]
   - Options Setup: [Initial strategy if applicable]

   📊 Portfolio Fit:
   - Fills Gap: [Diversification need, sector exposure, etc.]
   - Correlation: [With existing holdings]
   - Allocation: X.X% of portfolio
   - Risk Budget: $X,XXX available

   🎯 RECOMMENDATION: INITIATE POSITION
   Conviction: [HIGH/MEDIUM/LOW] (X/10)
   Position Size: $XX,XXX (XXX shares)

   Entry Strategy:
   Phase 1 (50%): Enter at $XXX.XX - $XXX.XX
   Phase 2 (50%): Add on pullback to $XXX.XX or breakout above $XXX.XX

   Or: All at once at current levels if [condition]

   Risk Management:
   - Initial Stop: $XXX.XX (X% risk per share)
   - Position Risk: X.X% of portfolio
   - Trail stop to breakeven after +X%

   Expected Outcome:
   - Target Return: +XX% ($X,XXX)
   - Time Horizon: X-X months
   - Probability: XX%

**B. [SYMBOL] - Proposed New Position**
   [Same format for other candidates]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 PORTFOLIO-LEVEL STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Asset Allocation

Current vs Target:
                Current    Target    Action
Stocks:         XX.X%      XX.X%     [Rebalance +/-X%]
Bonds:          XX.X%      XX.X%     [Rebalance +/-X%]
Cash:           XX.X%      XX.X%     [Adjust]

Rebalancing Trades:
1. [Sell $X,XXX of SYMBOL to reduce to target]
2. [Buy $X,XXX of SYMBOL to increase to target]
3. [Deploy cash into new positions]

Expected Impact:
- Better diversification: Correlation X.XX → X.XX
- Risk reduction: Max drawdown -X%
- Return improvement: Expected +X% annually

### Tax Optimization

Current Tax Position:
- Realized ST Gains: $X,XXX (Tax: $X,XXX at XX%)
- Realized LT Gains: $X,XXX (Tax: $X,XXX at XX%)
- Total Tax Liability: $X,XXX

Available Opportunities:
- Unrealized Losses: $X,XXX (in SYMBOL, SYMBOL)
- Approaching LT: $X,XXX (SYMBOL on [DATE])

Tax Harvesting Strategy:
1. Harvest Loss on SYMBOL: -$X,XXX loss → $XXX tax savings
   - Sell at $XXX.XX
   - Reinvest after 31 days to avoid wash sale
   - Alternative: Buy similar (but not substantially identical) security

2. Hold SYMBOL until [DATE] for LT treatment:
   - Current gain: $X,XXX
   - Tax savings: $XXX (XX% → XX%)

3. Offset with losses before year-end:
   - Current gains: $X,XXX
   - Can offset with: $X,XXX losses
   - Net liability: $X,XXX

Estimated Annual Tax Savings: $X,XXX

### Options Strategies

Income Generation:
1. Covered Calls on SYMBOL:
   - Strike: $XXX (X% OTM)
   - Premium: $XXX per month
   - Annual income: $X,XXX
   - Yield boost: +X.X%

2. Cash-Secured Puts on CANDIDATE:
   - Strike: $XXX (X% below current)
   - Premium: $XXX
   - Effective entry: $XXX (X% discount)
   - Annualized return if assigned: XX%

3. [Additional strategies]

Total Monthly Income Target: $XXX ($X,XXX annually)

Portfolio Protection:
1. Protective Puts on SYMBOL (if concerned):
   - Strike: $XXX
   - Cost: $XXX
   - Protection: Against >X% decline

2. Collar on SYMBOL (reduce cost):
   - Buy $XXX put
   - Sell $XXX call
   - Net cost: $XXX (or credit)

### Risk Management

Current Risk Profile:
- Portfolio Beta: X.XX (vs market)
- Maximum Drawdown: -XX%
- Volatility: XX% annualized
- Sharpe Ratio: X.XX

Risk Concentrations:
- Largest Position: XX% (Target: <XX%)
- Top 3 Positions: XX% (Target: <XX%)
- Sector Concentration:
  - Tech: XX% (vs XX% benchmark)
  - [Other sectors]

Risk Mitigation Plan:
1. Trim SYMBOL from XX% to XX%
   - Reason: [Overconcentration / Technical breakdown]
   - Execute: [Timing and method]

2. Add defensive positions:
   - Bonds: Increase from XX% to XX%
   - Defensive stocks: Add SYMBOL (utilities/consumer staples)

3. Diversification:
   - Add international exposure: SYMBOL
   - Add alternative assets: [If applicable]

Expected Impact:
- Reduce maximum drawdown from -XX% to -XX%
- Lower volatility from XX% to XX%
- Improve Sharpe ratio from X.XX to X.XX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ PRIORITIZED ACTION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚨 URGENT - Execute This Week (Within 7 Days):

1. [Action with specific execution details]
   Symbol: [SYMBOL]
   Action: [Specific trade]
   Why Urgent: [Time-sensitive reason]
   Tax Impact: $XXX savings if executed by [DATE]
   Expected Outcome: [Result]

   Execution Steps:
   - [ ] Step 1
   - [ ] Step 2
   - [ ] Step 3

2. [Next urgent action]
   [Same format]

Total Urgent Actions: X
Time Commitment: X hours
Capital Requirement: $XX,XXX

🎯 HIGH PRIORITY - Execute This Month:

1. [Action]
   [Brief description]
   Impact: [Expected result]

2. [Action]
   [Brief description]
   Impact: [Expected result]

Total High Priority: X
Expected Impact: $X,XXX or +X% return

📈 MEDIUM PRIORITY - Execute This Quarter:

1. [Action]
2. [Action]
3. [Action]

Total Medium Priority: X
Strategic Value: [Long-term benefits]

👀 MONITORING - Watch For Opportunities:

1. [Event/Condition] → [Planned Response]
   - Watch: [Specific trigger]
   - When: [Condition met]
   - Action: [Predetermined response]

2. [Event/Condition] → [Planned Response]

3. Periodic Reviews:
   - Weekly: [Quick checks]
   - Monthly: [Performance review]
   - Quarterly: [Strategic review]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 EXPECTED OUTCOMES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If Strategy Fully Executed:

Portfolio Metrics:
- Current Value: $XXX,XXX
- Expected 12-Month Value: $XXX,XXX (+XX%)
- Expected 12-Month Return: +XX% (vs +XX% market)

Performance Improvements:
- Return Enhancement: +X.X% from options income
- Tax Savings: $X,XXX (reduces after-tax cost)
- Cost Reduction: $XXX from optimization
- Total Benefit: +X.X% net return improvement

Risk Improvements:
- Maximum Drawdown: -XX% → -XX% (improvement of X%)
- Portfolio Volatility: XX% → XX%
- Sharpe Ratio: X.XX → X.XX
- Diversification Score: X/10 → X/10

Tax Efficiency:
- Current Tax Liability: $X,XXX
- Post-Optimization: $X,XXX
- Annual Tax Savings: $X,XXX

Income Generation:
- Current Dividend Income: $XXX/month
- + Options Income: $XXX/month
- Total Cash Flow: $XXX/month ($X,XXX/year)
- Yield on Portfolio: X.X%

Market Scenario Analysis:
Bull Market (+20% SPY):
  - Portfolio Expected: +XX%
  - Outperformance: +X%

Sideways Market (±5% SPY):
  - Portfolio Expected: +X%
  - Options Income: $X,XXX

Bear Market (-20% SPY):
  - Portfolio Expected: -XX%
  - Protection: Better than -XX% (market)
  - Defensive Positioning: Limits downside

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 IMPLEMENTATION SCHEDULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Week 1:
Day 1-2: Execute urgent tax harvesting and stop loss triggers
Day 3-4: Place new position entries (limit orders)
Day 5: Set up options strategies (covered calls, cash-secured puts)

Week 2-4:
- Monitor new positions and adjust stops
- Phase in remaining new positions
- Execute rebalancing trades
- Set up monitoring alerts

Month 2-3:
- Medium priority actions
- Gradual position building
- Options expiration management
- Performance review and adjustments

Quarterly Review:
- Full portfolio assessment
- Strategy effectiveness evaluation
- Adjust based on market conditions
- Tax planning check

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 EXECUTION CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before Trading:
☐ Review full strategy and understand rationale
☐ Confirm available capital and margin requirements
☐ Check for upcoming earnings/events on target stocks
☐ Verify current market conditions align with strategy
☐ Set up tracking spreadsheet or tool

During Execution:
☐ Use limit orders (avoid market orders)
☐ Document actual entry prices and costs
☐ Set up stop losses immediately
☐ Set up profit target alerts
☐ Save trade confirmations

After Execution:
☐ Update portfolio tracking
☐ Set calendar reminders for reviews
☐ Monitor daily for first week
☐ Adjust stops to breakeven when appropriate
☐ Keep trade journal with rationale

Weekly Maintenance:
☐ Check technical levels (support/resistance)
☐ Review stop losses and adjust if needed
☐ Monitor news and catalysts
☐ Manage expiring options
☐ Record observations and learnings

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ IMPORTANT DISCLAIMERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This strategy is based on current market conditions and portfolio analysis as of [DATE].
Markets are dynamic - be prepared to adjust as conditions change.

Risk Warnings:
- Past performance doesn't guarantee future results
- All investments carry risk of loss of principal
- Options trading involves substantial risk
- Leverage amplifies both gains and losses
- Stop losses don't guarantee execution price
- Diversification doesn't guarantee profit or prevent loss

Professional Advice:
- This is analytical guidance, not financial advice
- Consult qualified financial advisor for personalized advice
- Review tax strategies with qualified CPA
- Understand your own risk tolerance and goals
- Only execute what you understand and are comfortable with

Monitoring and Adjustment:
- Markets change - strategy must adapt
- Set up regular review schedule
- Don't be emotionally attached to positions
- Follow predefined stop losses and exit rules
- Document reasons for any deviations from plan

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 RELATED COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Individual Stock Analysis:
  /analyze-stock [SYMBOL] - Technical and fundamental analysis

Options Strategy Analysis:
  /options-strategy [SYMBOL] - Detailed options strategy

Portfolio Optimization:
  /optimize-portfolio - Portfolio-level optimization

Tax Planning:
  /tax-report - Comprehensive tax analysis and strategies

Performance Tracking:
  /compare-periods [dates] - Period comparison analysis
```

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
Get comprehensive strategy update.

**After Major Market Move**:
```bash
/investment-strategy
```
Reassess positions and adjust strategy.

**Tax Planning Season**:
```bash
/investment-strategy --save
```
Generate and save strategy with tax optimization.

**New Capital to Deploy**:
```bash
/investment-strategy
```
Identify best opportunities for new capital.

### Integration

This is the **master strategy command** that:
1. Coordinates **data-analyzer** and **market-analyst** via **strategy-coordinator**
2. Synthesizes both portfolio and market perspectives
3. Provides actionable, prioritized recommendations
4. Considers all factors: performance, taxes, risks, market conditions

For focused analysis, use:
- `/analyze-stock SYMBOL` - Individual stock deep dive
- `/options-strategy SYMBOL` - Options-focused analysis
- `/optimize-portfolio` - Portfolio optimization only
- `/tax-report` - Tax-focused analysis only

The **strategy-coordinator** subagent orchestrates the entire process, ensuring coherent, actionable investment strategy.
