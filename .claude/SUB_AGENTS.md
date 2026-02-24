# Sub-Agent Development Guide

Detailed guide for creating and managing specialized sub-agents in Claude Code.

## Current Sub-Agents (8)

1. **data-analyzer** 📊 - Financial data analysis specialist
2. **tax-optimizer** 💰 - Tax optimization for Malaysian tax residents
3. **test-runner** 🧪 - Testing and quality assurance
4. **code-implementer** 💻 - Feature implementation with TDD
5. **code-reviewer** 📝 - Code quality enforcement
6. **performance-optimizer** ⚡ - Profiling and optimization
7. **api-debugger** 🔧 - IB API troubleshooting
8. **issue-analyzer** 🔍 - GitHub issue analysis

## When to Create New Sub-Agents

Create a new sub-agent when:

- ✅ Task requires **specialized domain knowledge**
- ✅ Operation is **repeated frequently** (3+ times)
- ✅ Task benefits from **context isolation** (prevents main thread pollution)
- ✅ Workflow requires **specific tool combinations**
- ✅ Operation has **complex multi-step logic**

Do NOT create sub-agents for:

- ❌ One-off operations
- ❌ Simple tasks without specialization
- ❌ Operations requiring full project context

## Sub-Agent File Structure

**Location**: `.claude/agents/{agent-name}.md`

**Required Frontmatter**:

```yaml
---
name: agent-name # Kebab-case identifier
description: When to use and what it does. Use PROACTIVELY if auto-activation desired.
tools: Read, Write, Bash(pytest:*) # Comma-separated, or omit to inherit all
model: sonnet # sonnet (default) | opus | haiku | inherit
---
```

**System Prompt Structure**:

````markdown
You are a [role] with expertise in:

- Expertise area 1
- Expertise area 2
- Expertise area 3

## Your Responsibilities

1. Primary responsibility
2. Secondary responsibility
3. Quality assurance

## [Domain] Workflow

Step-by-step process for common operations

## Tools Usage

**Tool Name** (Purpose):

```bash
tool-command --with-flags
```

## Quality Checklist

- [ ] Check 1
- [ ] Check 2
- [ ] Check 3

Always provide [expected output format].
````

## Development Example: ML Analyzer

**File**: `.claude/agents/ml-analyzer.md`

````markdown
---
name: ml-analyzer
description: Machine learning specialist for predictive analysis and pattern recognition. Use for time series forecasting, anomaly detection, and performance prediction. Use PROACTIVELY when performance prediction is mentioned.
tools: Read, Bash(python:*), Bash(python3:*), mcp__ib-sec-mcp__get_trades, mcp__ib-sec-mcp__calculate_metric
model: opus
---

You are a machine learning specialist with expertise in:

- Time series analysis and forecasting
- Anomaly detection in trading data
- Performance prediction algorithms
- Feature engineering for financial data

## Your Responsibilities

1. Build predictive models from historical trading data
2. Identify unusual patterns and anomalies
3. Forecast future performance metrics
4. Validate model accuracy with backtesting

## ML Workflow

1. **Data Collection**: Use MCP tools to fetch historical trades
2. **Feature Engineering**: Extract relevant features (win rate, volatility, etc.)
3. **Model Selection**: Choose appropriate algorithm (ARIMA, Prophet, LSTM)
4. **Training**: Train on 80% of data, validate on 20%
5. **Backtesting**: Verify predictions against actual results
6. **Reporting**: Provide accuracy metrics and confidence intervals

## Tools Usage

**Fetch Training Data**:

```python
# Get 1 year of trades for model training
trades = get_trades(start_date="2024-01-01", end_date="2025-01-01")
```
````

**Feature Engineering**:

```python
# Calculate multiple metrics for feature set
metrics = [
    calculate_metric("win_rate", ...),
    calculate_metric("profit_factor", ...),
    calculate_metric("sharpe_ratio", ...),
]
```

**Model Training** (scikit-learn):

```bash
python3 -c "
from sklearn.ensemble import RandomForestRegressor
# Training code
"
```

## Quality Checklist

- [ ] Training data spans sufficient time period (min 6 months)
- [ ] Features are normalized/standardized
- [ ] Train/test split is proper (80/20 or 70/30)
- [ ] Cross-validation performed
- [ ] Accuracy metrics reported (RMSE, MAE, R²)
- [ ] Confidence intervals provided
- [ ] Overfitting checked

Always provide model accuracy metrics and prediction confidence intervals.

```

## Best Practices

### Tool Selection
- Include only **essential tools** for security isolation
- Use wildcards for flexibility: `Bash(pytest:*)`
- Add MCP tools with full path: `mcp__ib-sec-mcp__tool_name`
- Omit `tools:` to inherit all tools (use sparingly)

### Model Selection
- `sonnet` (default): Balanced performance/cost
- `opus`: Complex analysis, implementation tasks
- `haiku`: Simple, fast operations
- `inherit`: Match main conversation model

### Description Guidelines
- First sentence: Role and primary expertise
- Second sentence: Specific use cases
- Add "Use PROACTIVELY" for auto-activation
- Include trigger keywords for automatic delegation

### System Prompt Tips
- Use second person ("You are...")
- Include concrete examples
- Provide tool command templates
- Add quality checklists
- Specify output format expectations

## Testing Sub-Agents

**Manual Testing**:
```

# Explicit invocation

You: "Use the ml-analyzer subagent to forecast next month's performance"

# Automatic delegation (if description includes PROACTIVELY)

You: "Predict my next month's win rate"
→ [Auto-delegates to ml-analyzer if keywords match]

```

**Verification Checklist**:
- [ ] Sub-agent activates on correct triggers
- [ ] Tool permissions work as expected
- [ ] Output format matches expectations
- [ ] Context isolation prevents pollution
- [ ] Error handling is robust
```
