---
description: Detailed options strategy analysis with Greeks, IV metrics, and specific strategy recommendations
allowed-tools: Task
argument-hint: symbol
---

Generate detailed options trading strategy for a specific stock based on IV environment, Greeks analysis, and Max Pain calculations.

## Task

Delegate to the **market-analyst** subagent to provide professional options strategy analysis and recommendations.

### Command Usage

```bash
/options-strategy AAPL
/options-strategy SPY
/options-strategy VOO
```

### Analysis Components

The **market-analyst** subagent will analyze:

**1. IV Environment Assessment**
- Current implied volatility
- IV Rank (position in 52-week range)
- IV Percentile (historical comparison)
- Recommendation: Buy vs Sell premium strategies

**2. Options Greeks Analysis**
- Delta (directional exposure)
- Gamma (delta sensitivity)
- Theta (time decay)
- Vega (IV sensitivity)
- Rho (interest rate sensitivity)
- Risk assessment based on Greeks

**3. Max Pain Analysis**
- Max Pain strike price
- Current price vs Max Pain
- Expected price movement by expiration
- Expiration day expectations

**4. Options Chain Review**
- Liquidity analysis (bid/ask spreads)
- Open interest distribution
- Volume patterns
- Strike selection recommendations

**5. Strategy Recommendations**
- 2-3 specific options strategies
- Exact strikes and expirations
- Entry costs and max profit/loss
- Probability of profit
- Risk/reward ratios
- Best strategy selection with rationale

### Delegation Instructions

```
Use the market-analyst subagent to analyze options strategy for $ARGUMENTS:

Please provide comprehensive options strategy analysis including:

1. Market Sentiment:
   - Analyze composite sentiment (news + options + technical)
   - Use `analyze_market_sentiment` with sources="composite"
   - Identify key sentiment themes and risk factors

2. IV Environment:
   - Calculate IV Rank and IV Percentile
   - Determine if we should buy or sell premium
   - Recommend strategy types based on IV

3. Greeks Analysis:
   - Calculate Greeks for ATM options
   - Assess risk from each Greek
   - Time decay and IV sensitivity

3. Max Pain Analysis:
   - Calculate Max Pain strike
   - Interpret price pressure by expiration
   - Factor into strategy selection

4. Options Chain:
   - Review liquidity and spreads
   - Identify optimal strikes
   - Check open interest patterns

5. Strategy Recommendations:
   - Provide 2-3 specific strategies
   - Include exact strikes, expirations, costs
   - Calculate max profit, max loss, breakeven
   - Estimate probability of profit
   - Compare risk/reward for each strategy
   - Recommend best strategy with rationale

6. Execution Plan:
   - Entry timing and orders
   - Position sizing guidelines
   - Exit criteria and management
   - Risk management rules

Format as professional options strategy report with specific actionable recommendations.
```

### Expected Output Format

```
=== OPTIONS STRATEGY ANALYSIS: [SYMBOL] ===
Generated: [DATE TIME]
Current Stock Price: $XXX.XX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 IV ENVIRONMENT ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current Implied Volatility: XX.XX%

IV Rank: XX.XX
  Position in 52-week range: [HIGH/MEDIUM/LOW]
  52-Week High: XX.XX%
  52-Week Low: XX.XX%
  Current vs Mean: [above/below] by X.X%

IV Percentile: XX.XX
  Percentage of days IV was lower: XX.XX%
  Interpretation: [Description]

Strategy Environment: [PREMIUM SELLING / PREMIUM BUYING]

Recommended Strategy Types:
[HIGH IV Environment]:
  ✅ Covered Calls
  ✅ Cash-Secured Puts
  ✅ Credit Spreads
  ✅ Iron Condors
  ✅ Short Strangles

[LOW IV Environment]:
  ✅ Long Calls/Puts
  ✅ Debit Spreads
  ✅ Calendar Spreads
  ✅ Diagonal Spreads

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ GREEKS ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ATM Strike: $XXX.XX
Expiration: [DATE] (XX DTE - Days To Expiration)

Call Greeks (ATM):
  Delta: +X.XX (XX% probability of expiring ITM)
  Gamma: +X.XXXX (delta change per $1 move)
  Theta: -$X.XX/day ($XX.XX over life of option)
  Vega: +$X.XX per 1% IV change
  Rho: +$X.XX per 1% rate change

Put Greeks (ATM):
  Delta: -X.XX (XX% probability of expiring ITM)
  Gamma: +X.XXXX
  Theta: -$X.XX/day ($XX.XX over life of option)
  Vega: +$X.XX per 1% IV change
  Rho: -$X.XX per 1% rate change

Risk Assessment:
  Time Decay: [HIGH/MODERATE/LOW]
    - Theta burn of $XX.XX total over XX days
    - Accelerates in final 30 days

  IV Risk: [HIGH/MODERATE/LOW]
    - Vega exposure: $X.XX per 1% IV change
    - IV crush risk: [if earnings/event pending]

  Directional Risk: [HIGH/MODERATE/LOW]
    - Delta: XX% of stock move
    - Break-even move: ±$X.XX (±X.X%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 MAX PAIN ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Expiration: [DATE] (XX days away)

Max Pain Strike: $XXX.XX
Current Price: $XXX.XX
Distance: $XX.XX ([above/below] Max Pain)
Percentage: XX.X%

Expected Price Movement:
  Based on ATM Straddle: $XX.XX (±XX.X%)
  Expected Range: $XXX.XX - $XXX.XX

Interpretation:
[BULLISH]: Price below Max Pain suggests upward pressure
[BEARISH]: Price above Max Pain suggests downward pressure
[NEUTRAL]: Price near Max Pain suggests sideways movement

Trading Implications:
- [How Max Pain affects strategy selection]
- [Timing considerations for expiration]
- [Adjustment plans if approaching Max Pain]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 RECOMMENDED STRATEGIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Strategy 1: [STRATEGY NAME]

Setup:
  [Exact option positions with strikes and expirations]
  Example:
  • BUY 1 XXX Call @ $XXX strike, [EXP DATE]
  • SELL 1 XXX Call @ $XXX strike, [EXP DATE]

Cost & Returns:
  Net Debit/Credit: $XXX.XX
  Max Profit: $XXX.XX (XXX% return)
  Max Loss: $XXX.XX
  Breakeven: $XXX.XX

Probability Analysis:
  Prob of Profit: XX%
  Prob of Max Profit: XX%
  Prob of Max Loss: XX%

Risk/Reward: 1:X.X

Greeks (Position):
  Net Delta: ±X.XX
  Net Theta: ±$X.XX/day
  Net Vega: ±$X.XX

When to Use:
  [Market conditions where this strategy excels]

Profit Zones:
  Max Profit: [Price range]
  Profit: [Price range]
  Breakeven: $XXX.XX
  Loss: [Price range]

Management Rules:
  - Take profits if XX% gain reached
  - Roll if underlying moves [direction]
  - Exit if [stop loss condition]
  - Adjustment: [if needed]

### Strategy 2: [STRATEGY NAME]

[Same format as Strategy 1]

### Strategy 3: [STRATEGY NAME]

[Same format as Strategy 1]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 TOP RECOMMENDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Selected Strategy: [STRATEGY NAME]

Confidence Level: [HIGH/MEDIUM/LOW] (X/10)

Why This Strategy:
[Detailed rationale combining IV environment, Greeks, Max Pain, and market outlook]

Specific Action Plan:

1. Entry Execution:
   [Exact orders to place]
   - [Order type, strikes, expiration]
   - [Limit prices or market orders]
   - [Position sizing: $XXX or X contracts]

2. Position Management:
   - Monitor daily: [Key metrics to watch]
   - Adjust if: [Specific conditions]
   - Take profits at: [Price/profit targets]
   - Exit if: [Stop loss conditions]

3. Risk Management:
   - Maximum capital at risk: $XXX (X% of portfolio)
   - Position size: X contracts (or X% of stock position)
   - Stop loss: [Specific price or % loss]
   - Time stop: Exit by [DATE] if no movement

4. Exit Strategy:
   Success Exit:
   - Target 1 (50%): [Condition]
   - Target 2 (50%): [Condition]

   Loss Mitigation:
   - Stop loss trigger: [Condition]
   - Roll strategy: [If applicable]
   - Accept loss and exit: [Max loss threshold]

Expected Outcomes:
  • Best Case: +$XXX (XXX% return) if [condition]
  • Base Case: +$XXX (XX% return) if [condition]
  • Worst Case: -$XXX (XX% loss) if [condition]

Probability-Weighted Return: +$XXX (XX%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 PRE-TRADE CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before Executing:
☐ Confirm current IV environment hasn't changed
☐ Check for upcoming earnings or events
☐ Verify sufficient liquidity (tight bid/ask spreads)
☐ Confirm position sizing within risk limits
☐ Set up alerts for management triggers
☐ Document entry prices and Greeks
☐ Review tax implications if applicable
☐ Confirm account approval for strategy type

During Trade:
☐ Use limit orders (avoid market orders)
☐ Enter one leg at a time if spread
☐ Verify fills before proceeding
☐ Set up closing orders immediately
☐ Document actual entry prices

After Entry:
☐ Set calendar reminders for management
☐ Monitor Greeks daily
☐ Track P&L relative to max profit/loss
☐ Adjust as conditions change
☐ Follow predefined exit plan

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ IMPORTANT DISCLAIMERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Options Trading Risks:
- Options can expire worthless (total loss of premium)
- Time decay (theta) works against long options
- IV crush after earnings can devastate long premium
- Selling options can have unlimited risk (if naked)
- High leverage amplifies both gains and losses
- Complex strategies require active management

Required Knowledge:
- Understand Greeks and how they affect positions
- Know difference between spreads, straddles, strangles
- Be familiar with assignment and exercise risks
- Understand early assignment risk for American options
- Know when to take profits vs. hold to expiration

Risk Management Is Essential:
- Never risk more than you can afford to lose
- Use proper position sizing (typically 1-2% risk per trade)
- Set stop losses and follow them
- Don't trade options in IRA without understanding restrictions
- Consult financial advisor if uncertain

This analysis is for educational purposes only.
Not financial advice. Trade at your own risk.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 ADDITIONAL RESOURCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For deeper symbol analysis:
  /analyze-symbol [SYMBOL]

For portfolio-level strategy:
  /investment-strategy

For tax implications:
  /tax-report

For comprehensive portfolio review:
  /optimize-portfolio
```

### Use Cases

**Before Opening Options Position**:
```bash
/options-strategy AAPL
```
Get complete analysis to select optimal strategy.

**Evaluating Covered Call Opportunities**:
```bash
/options-strategy VOO
```
Analyze if IV environment favors covered calls.

**Finding Cash-Secured Put Strikes**:
```bash
/options-strategy MSFT
```
Identify optimal strike for put selling strategy.

**Options Income Strategy**:
```bash
/options-strategy SPY
```
Analyze weekly options for income generation.

### Error Handling

**If symbol not provided**:
```
Error: Please provide a stock symbol.
Usage: /options-strategy SYMBOL

Examples:
  /options-strategy AAPL
  /options-strategy SPY
```

**If no options available**:
```
Error: No options data available for symbol "$ARGUMENTS".
This stock may not have listed options.
```

### Integration

This command focuses on options strategies. Combine with:
- `/analyze-symbol SYMBOL` - For underlying symbol technical analysis
- `/investment-strategy` - For portfolio-level context
- `/optimize-portfolio` - For income generation opportunities across portfolio

The **market-analyst** subagent will provide professional options strategy analysis using Greeks, IV metrics, and Max Pain calculations.
