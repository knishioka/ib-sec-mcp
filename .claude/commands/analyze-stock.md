---
description: Comprehensive stock analysis with technical, fundamental, and options market analysis
allowed-tools: Task
argument-hint: symbol
---

Perform comprehensive analysis of a stock including technical analysis, fundamental data, options market analysis, and trading recommendations.

## Task

Delegate to the **market-analyst** subagent to provide deep stock analysis and actionable trading recommendations.

### Command Usage

```bash
/analyze-stock AAPL
/analyze-stock VOO
/analyze-stock SPY
```

### Analysis Components

The **market-analyst** subagent will provide:

**1. Multi-Timeframe Technical Analysis**
- Daily timeframe (short-term trading)
- Weekly timeframe (medium-term trend)
- Monthly timeframe (long-term context)
- Timeframe confluence analysis
- Support/resistance levels
- Entry/exit signals with specific prices

**2. Current Market Data**
- Real-time price and volume
- 52-week high/low
- Market cap and key metrics
- Intraday trading range

**3. Fundamental Overview**
- Company/fund information
- Business description
- Sector and industry
- Key financial metrics (P/E, dividend yield, etc.)

**4. Options Market Analysis (if applicable)**
- IV environment (IV Rank, IV Percentile)
- Options Greeks analysis
- Max Pain calculation
- Put/Call ratio
- Options strategy recommendations

**5. News and Catalysts**
- Recent news headlines
- Sentiment analysis
- Upcoming events (earnings, dividends)

**6. Trading Recommendation**
- Buy/Sell/Hold rating
- Conviction level (1-10)
- Specific entry prices
- Stop loss levels
- Price targets
- Risk/reward ratio

### Delegation Instructions

```
Use the market-analyst subagent to analyze $ARGUMENTS:

Please provide comprehensive stock analysis including:

1. Multi-timeframe technical analysis (daily, weekly, monthly)
2. Current price and fundamental overview
3. Options market analysis with IV metrics and Greeks
4. Recent news and market sentiment
5. Specific trading recommendation with:
   - Buy/Sell/Hold rating
   - Entry price zone
   - Stop loss level
   - Price targets
   - Risk/reward analysis
   - Conviction level (1-10)

Format the output as a comprehensive stock analysis report.
```

### Expected Output Format

```
=== Stock Analysis: [SYMBOL] ===
Generated: [DATE TIME]
Current Price: $XXX.XX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 MARKET DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current Price: $XXX.XX
Day Range: $XXX.XX - $XXX.XX
52-Week Range: $XXX.XX - $XXX.XX
Volume: X.XXM (Avg: X.XXM)
Market Cap: $XXXB

Company: [Company Name]
Sector: [Sector]
Industry: [Industry]
Dividend Yield: X.XX%
P/E Ratio: XX.XX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 MULTI-TIMEFRAME TECHNICAL ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Daily (Short-Term): [BULLISH/NEUTRAL/BEARISH]
  Signal: [BUY/HOLD/SELL]
  Trend: [Description]
  RSI: XX.XX ([Oversold/Neutral/Overbought])
  MACD: [Bullish/Bearish] [crossover/divergence]
  Support: $XXX.XX
  Resistance: $XXX.XX

  Key Levels:
  - Strong Support: $XXX.XX
  - Support: $XXX.XX
  - Current: $XXX.XX
  - Resistance: $XXX.XX
  - Strong Resistance: $XXX.XX

Weekly (Medium-Term): [BULLISH/NEUTRAL/BEARISH]
  Signal: [BUY/HOLD/SELL]
  Trend: [Description]
  Above SMA50: [Yes/No]
  Trend Strength: [Strong/Moderate/Weak]

Monthly (Long-Term): [BULLISH/NEUTRAL/BEARISH]
  Signal: [BUY/HOLD/SELL]
  Trend: [Description]
  Long-term Context: [Description]

Timeframe Confluence: [HIGH/MEDIUM/LOW] (X/3)
  [Interpretation of timeframe alignment]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ OPTIONS MARKET ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IV Environment:
  Current IV: XX.XX%
  IV Rank: XX.XX ([High/Medium/Low])
  IV Percentile: XX.XX

  Strategy Recommendation:
  [Sell premium / Buy premium] strategies preferred

Greeks (ATM, XX DTE):
  Delta: X.XX
  Gamma: X.XXXX
  Theta: -$X.XX/day
  Vega: $X.XX

Max Pain Analysis:
  Max Pain Strike: $XXX.XX
  Current vs Max Pain: $XX.XX ([above/below])
  Interpretation: [Bullish/Bearish/Neutral] pressure

Put/Call Ratio: X.XX ([Bullish/Neutral/Bearish])

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 NEWS & CATALYSTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Recent Headlines:
  • [Headline 1] - [Sentiment]
  • [Headline 2] - [Sentiment]
  • [Headline 3] - [Sentiment]

Overall Sentiment: [POSITIVE/NEUTRAL/NEGATIVE]

Upcoming Events:
  • [Event]: [Date]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 TRADING RECOMMENDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rating: [BUY / SELL / HOLD]
Conviction: [HIGH/MEDIUM/LOW] (X/10)
Time Horizon: [Short-term / Medium-term / Long-term]

Entry Strategy:
  Entry Zone: $XXX.XX - $XXX.XX
  Preferred Entry: $XXX.XX

Risk Management:
  Stop Loss: $XXX.XX
  Risk per Share: $X.XX

Profit Targets:
  Target 1 (50%): $XXX.XX (+X.X%)
  Target 2 (50%): $XXX.XX (+XX.X%)

Risk/Reward: 1:X.X

Position Sizing:
  Suggested: X% of portfolio
  Risk: X% of portfolio value

Rationale:
[Detailed explanation combining technical, fundamental, and market factors]

Key Factors:
  ✅ [Positive factor 1]
  ✅ [Positive factor 2]
  ⚠️ [Risk factor 1]
  ⚠️ [Risk factor 2]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 EXECUTION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For BUY Recommendation:
1. Set limit order at $XXX.XX (preferred entry)
2. Set stop loss at $XXX.XX upon fill
3. Take 50% profit at $XXX.XX
4. Trail stop for remaining 50% to $XXX.XX

For SELL Recommendation:
1. Sell at market or limit $XXX.XX
2. [Consider options hedge if needed]
3. [Tax implications if applicable]

Alternative Strategy:
[Options strategy if applicable - e.g., covered calls, cash-secured puts]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ RISK WARNINGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- This is not financial advice - do your own research
- Markets are volatile - prices can move against you
- Options trading involves substantial risk
- Always use stop losses and position sizing
- Review your risk tolerance before executing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Use Cases

**Before Buying a Stock**:
```bash
/analyze-stock AAPL
```
Get complete analysis to determine if this is a good entry point.

**Evaluating Current Holdings**:
```bash
/analyze-stock VOO
```
Check if you should hold, add to, or trim your position.

**Finding Entry Points**:
```bash
/analyze-stock MSFT
```
Identify support levels and optimal entry zones.

**Options Trading Setup**:
```bash
/analyze-stock SPY
```
Analyze IV environment and options strategies.

### Error Handling

**If symbol not provided**:
```
Error: Please provide a stock symbol.
Usage: /analyze-stock SYMBOL

Examples:
  /analyze-stock AAPL
  /analyze-stock VOO
```

**If invalid symbol**:
```
Error: Symbol "$ARGUMENTS" not found or has no data available.
Please check the symbol and try again.
```

### Integration with Other Commands

This command provides market analysis. Combine with:
- `/optimize-portfolio` - For portfolio-level decisions
- `/investment-strategy` - For comprehensive strategy including portfolio context
- `/options-strategy SYMBOL` - For detailed options strategy analysis

The **market-analyst** subagent will provide professional-grade analysis using all available technical analysis and options market tools.
