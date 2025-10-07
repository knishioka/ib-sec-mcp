"""MCP Prompts for IB Analytics

Provides reusable prompt templates for common analysis workflows.
"""

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register all IB Analytics prompts with MCP server"""

    @mcp.prompt
    def analyze_portfolio(csv_path: str) -> str:
        """
        Comprehensive portfolio analysis prompt

        Args:
            csv_path: Path to IB Flex Query CSV file

        Returns:
            Prompt message for LLM
        """
        return f"""Please perform a comprehensive analysis of my Interactive Brokers portfolio using the data at: {csv_path}

Run the following analyses and provide insights:

1. **Performance Analysis**: Calculate win rate, profit factor, average win/loss, and overall performance metrics
2. **Cost Analysis**: Break down trading costs by symbol and asset class
3. **Bond Analysis**: For any zero-coupon bonds (STRIPS), calculate YTM, duration, and analyze maturity profile
4. **Tax Analysis**: Calculate phantom income (OID) for bonds and estimate tax liability
5. **Risk Analysis**: Assess concentration risk and perform interest rate scenario analysis

Please present the results in a clear, organized manner with:
- Key findings and summary
- Detailed metrics for each analysis
- Any recommendations or insights based on the data"""

    @mcp.prompt
    def tax_planning(csv_path: str) -> str:
        """
        Tax planning analysis prompt

        Args:
            csv_path: Path to IB Flex Query CSV file

        Returns:
            Prompt message for LLM
        """
        return f"""Please analyze the tax implications of my portfolio at: {csv_path}

Focus on:

1. **Realized Gains/Losses**: Calculate total realized P&L for the period
2. **Phantom Income (OID)**: For zero-coupon bonds, calculate the Original Issue Discount (OID) income that must be reported even though no cash was received
3. **Tax Liability Estimation**: Estimate total tax liability considering:
   - Capital gains tax on realized profits
   - Ordinary income tax on phantom income
   - Your assumed tax bracket

4. **Tax Optimization Recommendations**:
   - Tax loss harvesting opportunities
   - Holding period considerations
   - Strategies to minimize phantom income impact

Please provide clear calculations and actionable recommendations."""

    @mcp.prompt
    def risk_assessment(csv_path: str, scenarios: str = "1% up, 1% down") -> str:
        """
        Portfolio risk assessment prompt

        Args:
            csv_path: Path to IB Flex Query CSV file
            scenarios: Interest rate scenarios to analyze

        Returns:
            Prompt message for LLM
        """
        return f"""Please assess the risk profile of my portfolio at: {csv_path}

Perform the following risk analyses:

1. **Concentration Risk**:
   - Asset class concentration
   - Single security concentration
   - Sector/industry concentration (if applicable)

2. **Interest Rate Risk**:
   - Analyze portfolio sensitivity to interest rate changes
   - Run scenarios: {scenarios}
   - Calculate estimated impact on portfolio value

3. **Liquidity Risk**:
   - Assess position sizes relative to typical trading volumes
   - Identify potentially illiquid positions

4. **Overall Risk Assessment**:
   - Risk/reward profile
   - Maximum drawdown analysis
   - Volatility metrics

Provide specific risk metrics and recommendations for risk mitigation."""

    @mcp.prompt
    def bond_portfolio_analysis(csv_path: str) -> str:
        """
        Specialized bond portfolio analysis prompt

        Args:
            csv_path: Path to IB Flex Query CSV file

        Returns:
            Prompt message for LLM
        """
        return f"""Please analyze my zero-coupon bond (STRIPS) portfolio at: {csv_path}

Provide detailed analysis on:

1. **Current Holdings**:
   - List all STRIPS positions
   - Cost basis vs. current value
   - Unrealized gains/losses

2. **Yield Analysis**:
   - Yield to Maturity (YTM) for each position
   - Weighted average YTM of the portfolio
   - Comparison to current market rates

3. **Maturity Profile**:
   - Maturity ladder visualization
   - Duration analysis
   - Reinvestment considerations

4. **Tax Considerations**:
   - Phantom income (OID) calculations
   - Estimated annual tax impact
   - After-tax yield analysis

5. **Risk Metrics**:
   - Interest rate sensitivity
   - Duration-based risk metrics
   - Concentration by maturity date

Please provide actionable insights for bond portfolio management."""

    @mcp.prompt
    def monthly_performance_review(csv_path: str, month: str) -> str:
        """
        Monthly performance review prompt

        Args:
            csv_path: Path to IB Flex Query CSV file
            month: Month to review (e.g., "2025-01")

        Returns:
            Prompt message for LLM
        """
        return f"""Please review my trading performance for {month} using data at: {csv_path}

Provide a comprehensive monthly review including:

1. **Monthly Summary**:
   - Total realized P&L
   - Number of trades executed
   - Win rate and profit factor
   - Trading costs

2. **Best and Worst Trades**:
   - Top 3 profitable trades
   - Top 3 losing trades
   - Lessons learned

3. **Performance Metrics**:
   - Average win vs. average loss
   - Risk/reward ratio
   - Consistency of returns

4. **Cost Analysis**:
   - Total commissions paid
   - Cost as percentage of volume
   - Cost efficiency by asset class

5. **Action Items**:
   - Areas for improvement
   - Patterns to continue
   - Recommendations for next month

Present the review in a clear, structured format suitable for monthly record-keeping."""
