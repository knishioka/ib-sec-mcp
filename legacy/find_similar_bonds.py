#!/usr/bin/env python3
"""
Similar Bond Investment Opportunities Analyzer
Helps find comparable Treasury STRIPS and zero-coupon bonds
"""

def analyze_similar_bonds():
    """
    Analyze alternative Treasury STRIPS and similar zero-coupon bond options
    """

    print("=" * 80)
    print("SIMILAR BOND INVESTMENT OPPORTUNITIES")
    print("US Treasury STRIPS & Zero-Coupon Bonds")
    print("=" * 80)
    print()

    print("CURRENT HOLDINGS PROFILE")
    print("-" * 80)
    print("Security:         US Treasury STRIP 0% 11/15/2040")
    print("Investment:       $23,457")
    print("Current Value:    $24,650.96")
    print("Maturity:         15.1 years")
    print("YTM:              5.136%")
    print("Duration:         ~15 years (high interest rate sensitivity)")
    print()

    print("=" * 80)
    print("OPTION 1: OTHER US TREASURY STRIPS")
    print("=" * 80)
    print()

    strips_options = [
        {
            'maturity': '2030 (5 years)',
            'estimated_ytm': '4.2-4.5%',
            'price_range': '80-85% of par',
            'investment_for_50k': '$40,000-$42,500',
            'duration': '~5 years',
            'risk': 'Low',
            'liquidity': 'High'
        },
        {
            'maturity': '2035 (10 years)',
            'estimated_ytm': '4.5-4.8%',
            'price_range': '62-67% of par',
            'investment_for_50k': '$31,000-$33,500',
            'duration': '~10 years',
            'risk': 'Medium',
            'liquidity': 'Medium'
        },
        {
            'maturity': '2040 (15 years)',
            'estimated_ytm': '5.0-5.3%',
            'price_range': '46-50% of par',
            'investment_for_50k': '$23,000-$25,000',
            'duration': '~15 years',
            'risk': 'Medium-High',
            'liquidity': 'Medium'
        },
        {
            'maturity': '2045 (20 years)',
            'estimated_ytm': '5.1-5.5%',
            'price_range': '35-39% of par',
            'investment_for_50k': '$17,500-$19,500',
            'duration': '~20 years',
            'risk': 'High',
            'liquidity': 'Lower'
        },
        {
            'maturity': '2050 (25 years)',
            'estimated_ytm': '5.2-5.6%',
            'price_range': '27-31% of par',
            'investment_for_50k': '$13,500-$15,500',
            'duration': '~25 years',
            'risk': 'Very High',
            'liquidity': 'Lower'
        },
    ]

    print(f"{'Maturity':<20} {'Est. YTM':<15} {'Investment':<25} {'Risk':<15} {'Liquidity'}")
    print("-" * 80)
    for option in strips_options:
        print(f"{option['maturity']:<20} {option['estimated_ytm']:<15} "
              f"{option['investment_for_50k']:<25} {option['risk']:<15} {option['liquidity']}")
    print()

    print("HOW TO BUY TREASURY STRIPS ON INTERACTIVE BROKERS:")
    print("-" * 80)
    print("1. Log in to TWS (Trader Workstation) or IBKR Portal")
    print("2. Navigate to: Trade → Bonds → US Treasury")
    print("3. Filter by: Asset Type = STRIPS")
    print("4. Sort by: Maturity Date or Yield to Maturity")
    print("5. Review available STRIPS with different maturities")
    print("6. Place order (minimum $1,000 face value)")
    print()
    print("INTERACTIVE BROKERS COMMISSION:")
    print("  • 0.2 bps (0.002%) on first $1M face value")
    print("  • 0.01 bps on face value above $1M")
    print("  • Typical cost: $5-10 per trade for retail sizes")
    print()

    print("=" * 80)
    print("OPTION 2: TREASURY STRIPS ETF")
    print("=" * 80)
    print()

    print("GOVZ - iShares 25+ Year Treasury STRIPS Bond ETF")
    print("-" * 80)
    print("Ticker:           GOVZ")
    print("Expense Ratio:    0.18% annually")
    print("Holdings:         Diversified long-term Treasury STRIPS")
    print("Avg Maturity:     ~25-30 years")
    print("YTM:              ~5.0-5.5% (varies with market)")
    print("Liquidity:        High (trades like stock)")
    print("Minimum:          1 share (~$40-60)")
    print()
    print("PROS:")
    print("  ✓ Instant diversification across multiple STRIPS")
    print("  ✓ High liquidity (buy/sell anytime)")
    print("  ✓ Low minimum investment")
    print("  ✓ Professional management")
    print()
    print("CONS:")
    print("  ✗ Annual fee of 0.18%")
    print("  ✗ No guaranteed maturity value (mark-to-market)")
    print("  ✗ Slightly lower yield due to fees")
    print()

    print("=" * 80)
    print("OPTION 3: LADDER STRATEGY WITH MULTIPLE STRIPS")
    print("=" * 80)
    print()

    print("BOND LADDER EXAMPLE ($25,000 total investment)")
    print("-" * 80)

    ladder = [
        {'year': 2030, 'amount': '$5,000', 'face': '$6,000', 'ytm': '4.3%'},
        {'year': 2033, 'amount': '$5,000', 'face': '$6,500', 'ytm': '4.6%'},
        {'year': 2036, 'amount': '$5,000', 'face': '$7,500', 'ytm': '4.9%'},
        {'year': 2039, 'amount': '$5,000', 'face': '$9,000', 'ytm': '5.1%'},
        {'year': 2042, 'amount': '$5,000', 'face': '$11,000', 'ytm': '5.3%'},
    ]

    print(f"{'Maturity':<15} {'Investment':<15} {'Face Value':<15} {'Yield'}")
    print("-" * 80)
    for rung in ladder:
        print(f"{rung['year']:<15} {rung['amount']:<15} {rung['face']:<15} {rung['ytm']}")
    print()
    print("Total Investment: $25,000")
    print("Total Face Value: $40,000 (paid over 5 maturities)")
    print("Avg Yield:        ~4.8%")
    print()
    print("BENEFITS OF LADDERING:")
    print("  ✓ Reduces interest rate risk through diversification")
    print("  ✓ Provides regular cash flows as bonds mature")
    print("  ✓ Opportunity to reinvest at different rate environments")
    print("  ✓ Flexibility to adjust strategy over time")
    print()

    print("=" * 80)
    print("OPTION 4: ALTERNATIVE ZERO-COUPON INVESTMENTS")
    print("=" * 80)
    print()

    alternatives = [
        {
            'name': 'I Bonds (Series I Savings Bonds)',
            'yield': '3.0-5.0% (inflation-adjusted)',
            'min': '$25',
            'max': '$10,000/year',
            'risk': 'Lowest (government-backed)',
            'liquidity': 'Low (1-year lock, 5-year penalty)',
            'tax': 'Tax-deferred, tax-free if used for education'
        },
        {
            'name': 'EE Bonds (Series EE Savings Bonds)',
            'yield': '2.7% (or doubles in 20 years)',
            'min': '$25',
            'max': '$10,000/year',
            'risk': 'Lowest (government-backed)',
            'liquidity': 'Low (1-year lock, 5-year penalty)',
            'tax': 'Tax-deferred'
        },
        {
            'name': 'Zero-Coupon Corporate Bonds',
            'yield': '5.5-8.0%',
            'min': '$1,000',
            'max': 'Unlimited',
            'risk': 'Medium-High (credit risk)',
            'liquidity': 'Medium',
            'tax': 'Taxable on phantom income'
        },
        {
            'name': 'Zero-Coupon Municipal Bonds',
            'yield': '3.5-5.5% (tax-free)',
            'min': '$5,000',
            'max': 'Unlimited',
            'risk': 'Low-Medium',
            'liquidity': 'Medium',
            'tax': 'Tax-free federal (possibly state)'
        },
    ]

    for alt in alternatives:
        print(f"{alt['name']}")
        print("-" * 80)
        print(f"  Yield:          {alt['yield']}")
        print(f"  Min Investment: {alt['min']}")
        print(f"  Max Investment: {alt['max']}")
        print(f"  Risk Level:     {alt['risk']}")
        print(f"  Liquidity:      {alt['liquidity']}")
        print(f"  Tax Treatment:  {alt['tax']}")
        print()

    print("=" * 80)
    print("RECOMMENDATION FOR YOUR SITUATION")
    print("=" * 80)
    print()

    print("Based on your current $24,650 position in S 0 11/15/40:")
    print()
    print("CONSERVATIVE APPROACH (Lower Risk):")
    print("  → Sell current STRIP and build a ladder with 5/10/15 year maturities")
    print("  → Reduces duration risk while maintaining Treasury quality")
    print("  → Provides periodic cash flows for reinvestment")
    print()
    print("MAINTAIN CURRENT STRATEGY (Medium Risk):")
    print("  → Keep S 0 11/15/40 and add shorter-term STRIPS (5-10 years)")
    print("  → Diversifies maturity risk")
    print("  → Maintains high YTM on long-term holding")
    print()
    print("AGGRESSIVE APPROACH (Higher Risk, Higher Yield):")
    print("  → Sell and buy longer-term STRIPS (20-25 years)")
    print("  → Potentially higher yield (5.3-5.6%)")
    print("  → Greater interest rate sensitivity and risk")
    print()
    print("PASSIVE/DIVERSIFIED APPROACH (Lowest Effort):")
    print("  → Buy GOVZ ETF for instant STRIPS exposure")
    print("  → High liquidity, professional management")
    print("  → Lower yield due to 0.18% fee")
    print()

    print("=" * 80)
    print("NEXT STEPS TO ACQUIRE SIMILAR BONDS")
    print("=" * 80)
    print()
    print("1. LOG INTO INTERACTIVE BROKERS:")
    print("   • TWS (Trader Workstation) or IBKR Web Portal")
    print()
    print("2. ACCESS BOND SEARCH TOOL:")
    print("   • Navigate: Trade → Fixed Income → Bond Search")
    print("   • Or use Bond Scanner in TWS")
    print()
    print("3. FILTER CRITERIA:")
    print("   • Country: United States")
    print("   • Issuer Type: Government")
    print("   • Bond Type: STRIPS or Zero Coupon")
    print("   • Maturity: Your preferred range (e.g., 2030-2045)")
    print("   • Minimum Rating: AAA (Treasury = AAA)")
    print()
    print("4. SORT AND COMPARE:")
    print("   • Sort by Yield to Maturity (highest to lowest)")
    print("   • Compare different maturities")
    print("   • Check liquidity (bid-ask spread)")
    print()
    print("5. PLACE ORDER:")
    print("   • Specify face value (minimum $1,000, typically $5,000 increments)")
    print("   • Choose order type (Limit recommended)")
    print("   • Review total cost including commission")
    print()
    print("6. ALTERNATIVE - BUY GOVZ ETF:")
    print("   • Search ticker: GOVZ")
    print("   • Buy like any stock")
    print("   • Commission: $0 at IB (for stocks/ETFs)")
    print()

    print("=" * 80)
    print("IMPORTANT NOTES")
    print("=" * 80)
    print()
    print("• Treasury STRIPS availability varies - not all maturities always available")
    print("• Yields change daily with market conditions")
    print("• Consider tax implications (phantom income on zero-coupon bonds)")
    print("• Diversification reduces risk but may lower overall yield")
    print("• Consult with tax advisor regarding tax treatment in your situation")
    print()
    print("This analysis is for educational purposes only, not investment advice.")
    print()
    print("=" * 80)

if __name__ == '__main__':
    analyze_similar_bonds()
