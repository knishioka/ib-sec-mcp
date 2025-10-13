---
description: Run comprehensive portfolio analysis and optimization recommendations
allowed-tools: Task
argument-hint: [csv-file-path]
---

Perform comprehensive portfolio analysis combining portfolio metrics (from data-analyzer) with market analysis (from market-analyst) to provide optimization recommendations.

## Task

Use **strategy-coordinator** to orchestrate portfolio optimization through data-analyzer and market-analyst collaboration.

### Orchestration Process

```
Use the strategy-coordinator subagent to optimize portfolio:

1. Portfolio Analysis Phase (via data-analyzer):
   - Load latest CSV from $ARGUMENTS or data/raw/
   - Run comprehensive analysis (performance, costs, bonds, tax, risk)
   - Identify current holdings and their metrics
   - Generate portfolio health assessment

2. Market Analysis Phase (via market-analyst):
   - Analyze each current holding:
     - Technical outlook and trends
     - Support/resistance levels
     - Entry/exit timing
     - Options opportunities (covered calls, protective puts)
   - Identify new position candidates

3. Optimization Synthesis:
   - For each holding:
     - Combine portfolio metrics with market analysis
     - Recommend: HOLD/SELL/TRIM/ADD
     - Consider tax implications
     - Suggest options strategies for income/protection
   - Portfolio-level recommendations:
     - Rebalancing needs
     - Tax optimization opportunities
     - Options income strategies
     - Risk management improvements

4. Prioritized Action Plan:
   - Urgent actions (this week)
   - High priority (this month)
   - Medium priority (this quarter)
   - Monitoring points

$ARGUMENTS
```

### Analysis Components

The **strategy-coordinator** will provide integrated insights combining:

### Performance Insights
- Trading efficiency (win rate, profit factor)
- Best/worst performing symbols
- Trade frequency patterns
- Risk-adjusted returns

### Cost Optimization
- Commission efficiency
- High-cost trades to avoid
- Fee structure analysis
- Broker comparison suggestions

### Bond Portfolio Optimization
- Yield ladder opportunities
- Duration management
- Interest rate risk exposure
- Maturity distribution

### Tax Optimization Strategies
- Tax-loss harvesting opportunities
- Wash sale warnings
- Long-term vs. short-term gains ratio
- Phantom income impact (OID)
- Optimal holding periods

### Risk Management
- Concentration risk (top positions)
- Interest rate sensitivity
- Diversification recommendations
- Stress test results (+/- 1% rates)

**4. Actionable Recommendations**

Prioritized list of specific actions:
1. Immediate actions (high impact, low effort)
2. Strategic moves (high impact, high effort)
3. Monitoring points (watch for opportunities)

### Expected Output Format

```
=== Portfolio Optimization Report ===
Data Period: 2025-01-01 to 2025-10-05
Portfolio Value: $XXX,XXX

📊 PERFORMANCE ANALYSIS
Current Performance:
- Total P&L: $X,XXX (X.X%)
- Win Rate: XX%
- Profit Factor: X.XX
- Sharpe Ratio: X.XX (if available)

Key Insights:
- ✅ Strong performance in tech sector (XX% return)
- ⚠️ High volatility in positions XXX, YYY
- 💡 Consider rebalancing overweight positions

💰 COST ANALYSIS
Total Costs: $XXX (X.X% of traded value)
- Commissions: $XXX
- Fees: $XXX
- Cost per Trade: $X.XX

Optimization Opportunities:
- 💡 Consider bulk trades for high-frequency symbols
- 💡 Review pricing tier (potential $XXX annual savings)

🏦 BOND PORTFOLIO
Holdings: X bonds, $XXX,XXX face value
- Avg YTM: X.XX%
- Portfolio Duration: X.X years
- Next Maturity: YYYY-MM-DD

Ladder Strategy:
- 💡 Add YYYY maturity for better spacing
- ⚠️ Concentration in 2030 maturity (XX%)
- 💡 Consider +1% rate impact: -$X,XXX

💵 TAX OPTIMIZATION
Current Tax Situation:
- Short-term Gains: $X,XXX (taxed at XX%)
- Long-term Gains: $X,XXX (taxed at XX%)
- Phantom Income (OID): $XXX
- Estimated Liability: $X,XXX

Optimization Strategies:
1. 🎯 Harvest $X,XXX in losses (Symbol XXX, YYY)
2. 🎯 Hold Symbol ZZZ until [date] for long-term treatment
3. ⚠️ Watch for wash sales on Symbol XXX
4. 💡 Consider municipal bonds for tax-free income

⚠️ RISK ASSESSMENT
Portfolio Concentration:
- Top Position: XX% (Symbol: XXX) - MODERATE RISK
- Top 3 Positions: XX% - [HIGH/MEDIUM/LOW]

Interest Rate Scenarios:
- +1% Rate: -$X,XXX (-X.X%)
- -1% Rate: +$X,XXX (+X.X%)

Diversification Score: X/10
- 💡 Consider adding asset classes: [suggestions]

=== PRIORITIZED RECOMMENDATIONS ===

🎯 IMMEDIATE ACTIONS (This Week)
1. Harvest tax losses: Sell XXX (-$XXX) to offset gains
2. Rebalance: Trim YYY position from XX% to XX%
3. Monitor: Watch for wash sale period ending [date]

📈 STRATEGIC MOVES (This Month)
1. Bond Ladder: Add 2028 maturity ($XX,XXX) for diversification
2. Cost Efficiency: Consolidate trades to reduce fees
3. Risk Reduction: Add bonds/defensive positions (target XX%)

👀 MONITORING POINTS
1. Symbol XXX: Approaching long-term holding period [date]
2. Interest Rates: Fed meeting [date] - prepare for volatility
3. Tax Year End: Review positions by December for tax planning

=== PORTFOLIO HEALTH SCORE ===
Overall: [EXCELLENT|GOOD|FAIR|NEEDS ATTENTION]
- Performance: ★★★★☆
- Cost Efficiency: ★★★☆☆
- Tax Optimization: ★★★★☆
- Risk Management: ★★★☆☆
- Diversification: ★★☆☆☆
```

### Examples

```
/optimize-portfolio
/optimize-portfolio data/raw/U1234567_2025-01-01_2025-10-05.csv
```

The **data-analyzer** subagent will provide comprehensive, actionable insights for portfolio optimization.
