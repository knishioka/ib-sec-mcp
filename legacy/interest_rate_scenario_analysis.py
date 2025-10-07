#!/usr/bin/env python3
"""
Interest Rate Scenario Analysis for Treasury STRIP
Multiple scenarios for rate changes and their impact on bond value
"""

from datetime import datetime
import math

def calculate_bond_price(face_value, years_to_maturity, yield_rate):
    """Calculate zero-coupon bond price given yield"""
    return face_value / math.pow(1 + yield_rate, years_to_maturity)

def analyze_rate_scenarios():
    """Analyze multiple interest rate scenarios"""

    print("=" * 80)
    print("INTEREST RATE SCENARIO ANALYSIS")
    print("US Treasury STRIP - S 0 11/15/40")
    print("=" * 80)
    print()

    # Bond details
    face_value = 50000
    current_price = 24650.96
    purchase_price = 23457
    purchase_date = datetime(2025, 7, 10)
    maturity_date = datetime(2040, 11, 15)
    current_date = datetime(2025, 10, 5)

    years_to_maturity = (maturity_date - current_date).days / 365.25

    # Calculate current implied yield
    current_yield = math.pow(face_value / current_price, 1 / years_to_maturity) - 1

    print("CURRENT POSITION")
    print("-" * 80)
    print(f"Security:              S 0 11/15/40 (Treasury STRIP)")
    print(f"Face Value:            ${face_value:,.2f}")
    print(f"Current Price:         ${current_price:,.2f}")
    print(f"Purchase Price:        ${purchase_price:,.2f}")
    print(f"Years to Maturity:     {years_to_maturity:.2f} years")
    print(f"Current Yield (YTM):   {current_yield * 100:.3f}%")
    print(f"Unrealized P&L:        ${current_price - purchase_price:,.2f}")
    print()

    print("=" * 80)
    print("UNDERSTANDING INTEREST RATE RISK")
    print("=" * 80)
    print()

    print("Zero-Coupon Bond Mechanics:")
    print("-" * 80)
    print("• Zero-coupon bonds are MOST sensitive to interest rate changes")
    print("• Longer maturity = Higher sensitivity (yours: 15 years)")
    print("• When rates ↑ → Bond prices ↓ (inverse relationship)")
    print("• When rates ↓ → Bond prices ↑")
    print()

    print("Duration Concept:")
    print("-" * 80)
    print(f"• Your bond's duration: ~{years_to_maturity:.1f} years")
    print(f"• Rule of thumb: 1% rate change → ~{years_to_maturity:.1f}% price change")
    print(f"• Example: Rates ↑1% → Price ↓~{years_to_maturity:.1f}% (${current_price * years_to_maturity / 100:,.2f})")
    print()

    print("=" * 80)
    print("SCENARIO ANALYSIS: INTEREST RATE CHANGES")
    print("=" * 80)
    print()

    # Define scenarios
    scenarios = [
        {'name': 'Severe Rate Hike', 'change': 0.03, 'probability': '5%', 'likelihood': 'Low'},
        {'name': 'Significant Rate Hike', 'change': 0.02, 'probability': '15%', 'likelihood': 'Moderate'},
        {'name': 'Moderate Rate Hike', 'change': 0.01, 'probability': '25%', 'likelihood': 'Likely'},
        {'name': 'Minor Rate Hike', 'change': 0.005, 'probability': '20%', 'likelihood': 'Likely'},
        {'name': 'No Change (Base Case)', 'change': 0.00, 'probability': '10%', 'likelihood': 'Possible'},
        {'name': 'Minor Rate Cut', 'change': -0.005, 'probability': '10%', 'likelihood': 'Possible'},
        {'name': 'Moderate Rate Cut', 'change': -0.01, 'probability': '10%', 'likelihood': 'Possible'},
        {'name': 'Significant Rate Cut', 'change': -0.02, 'probability': '4%', 'likelihood': 'Low'},
        {'name': 'Severe Rate Cut', 'change': -0.03, 'probability': '1%', 'likelihood': 'Very Low'},
    ]

    print(f"{'Scenario':<30} {'Rate Change':<15} {'New Yield':<12} {'New Price':<15} "
          f"{'P&L Change':<15} {'Total P&L':<15}")
    print("-" * 80)

    scenario_results = []

    for scenario in scenarios:
        rate_change = scenario['change']
        new_yield = current_yield + rate_change
        new_price = calculate_bond_price(face_value, years_to_maturity, new_yield)
        pnl_change = new_price - current_price
        total_pnl = new_price - purchase_price

        scenario_results.append({
            'name': scenario['name'],
            'rate_change': rate_change,
            'new_yield': new_yield,
            'new_price': new_price,
            'pnl_change': pnl_change,
            'total_pnl': total_pnl,
            'probability': scenario['probability'],
            'likelihood': scenario['likelihood']
        })

        # Format rate change
        rate_str = f"+{rate_change*100:.1f}%" if rate_change > 0 else f"{rate_change*100:.1f}%"

        print(f"{scenario['name']:<30} {rate_str:<15} {new_yield*100:<11.3f}% "
              f"${new_price:<14,.2f} ${pnl_change:<14,.2f} ${total_pnl:<14,.2f}")

    print()

    print("=" * 80)
    print("DETAILED SCENARIO BREAKDOWN")
    print("=" * 80)
    print()

    # Group scenarios by direction
    rate_hikes = [s for s in scenario_results if s['rate_change'] > 0]
    rate_cuts = [s for s in scenario_results if s['rate_change'] < 0]
    base_case = [s for s in scenario_results if s['rate_change'] == 0]

    print("📈 RATE HIKE SCENARIOS (Unfavorable)")
    print("-" * 80)
    for scenario in rate_hikes:
        print()
        print(f"SCENARIO: {scenario['name']}")
        print(f"  Rate Change:        {scenario['rate_change']*100:+.1f}%")
        print(f"  New Yield:          {scenario['new_yield']*100:.3f}%")
        print(f"  New Bond Price:     ${scenario['new_price']:,.2f}")
        print(f"  Price Change:       ${scenario['pnl_change']:,.2f} ({scenario['pnl_change']/current_price*100:.1f}%)")
        print(f"  Total P&L:          ${scenario['total_pnl']:,.2f}")
        print(f"  Probability:        {scenario['probability']}")
        print(f"  Likelihood:         {scenario['likelihood']}")

        # Decision guidance
        if scenario['total_pnl'] < 0:
            print(f"  ⚠️  WARNING: Would result in net loss")
        elif scenario['pnl_change'] < -1000:
            print(f"  ⚠️  CAUTION: Significant unrealized loss")

    print()
    print()

    print("➡️  BASE CASE (Current Rates)")
    print("-" * 80)
    for scenario in base_case:
        print()
        print(f"SCENARIO: {scenario['name']}")
        print(f"  Rate Change:        {scenario['rate_change']*100:+.1f}%")
        print(f"  Current Yield:      {scenario['new_yield']*100:.3f}%")
        print(f"  Current Price:      ${scenario['new_price']:,.2f}")
        print(f"  Total P&L:          ${scenario['total_pnl']:,.2f}")

    print()
    print()

    print("📉 RATE CUT SCENARIOS (Favorable)")
    print("-" * 80)
    for scenario in rate_cuts:
        print()
        print(f"SCENARIO: {scenario['name']}")
        print(f"  Rate Change:        {scenario['rate_change']*100:+.1f}%")
        print(f"  New Yield:          {scenario['new_yield']*100:.3f}%")
        print(f"  New Bond Price:     ${scenario['new_price']:,.2f}")
        print(f"  Price Change:       ${scenario['pnl_change']:,.2f} ({scenario['pnl_change']/current_price*100:+.1f}%)")
        print(f"  Total P&L:          ${scenario['total_pnl']:,.2f}")
        print(f"  Probability:        {scenario['probability']}")
        print(f"  Likelihood:         {scenario['likelihood']}")

        # Upside potential
        if scenario['pnl_change'] > 2000:
            print(f"  ✅ OPPORTUNITY: Significant price appreciation")

    print()

    print("=" * 80)
    print("RISK/REWARD ANALYSIS")
    print("=" * 80)
    print()

    # Calculate weighted average outcome
    total_prob = sum(float(s['probability'].rstrip('%')) for s in scenario_results)

    weighted_price = sum(
        s['new_price'] * float(s['probability'].rstrip('%')) / 100
        for s in scenario_results
    )

    weighted_pnl = weighted_price - purchase_price

    print("EXPECTED VALUE ANALYSIS")
    print("-" * 80)
    print(f"Weighted Average Price:    ${weighted_price:,.2f}")
    print(f"Weighted Average P&L:      ${weighted_pnl:,.2f}")
    print(f"Current P&L:               ${current_price - purchase_price:,.2f}")
    print()

    # Calculate upside/downside
    best_case = max(scenario_results, key=lambda x: x['new_price'])
    worst_case = min(scenario_results, key=lambda x: x['new_price'])

    print("BEST/WORST CASE SCENARIOS")
    print("-" * 80)
    print(f"Best Case ({best_case['name']}):")
    print(f"  Price:    ${best_case['new_price']:,.2f}")
    print(f"  Upside:   ${best_case['new_price'] - current_price:,.2f} ({(best_case['new_price']/current_price - 1)*100:+.1f}%)")
    print()
    print(f"Worst Case ({worst_case['name']}):")
    print(f"  Price:    ${worst_case['new_price']:,.2f}")
    print(f"  Downside: ${worst_case['new_price'] - current_price:,.2f} ({(worst_case['new_price']/current_price - 1)*100:.1f}%)")
    print()

    # Risk/Reward Ratio
    upside_potential = best_case['new_price'] - current_price
    downside_risk = current_price - worst_case['new_price']
    risk_reward_ratio = upside_potential / downside_risk if downside_risk > 0 else 0

    print(f"Risk/Reward Ratio:         {risk_reward_ratio:.2f}:1")
    print()

    print("=" * 80)
    print("PROBABILITY-WEIGHTED OUTCOMES")
    print("=" * 80)
    print()

    # Group by outcome type
    loss_scenarios = [s for s in scenario_results if s['total_pnl'] < 0]
    small_gain_scenarios = [s for s in scenario_results if 0 <= s['total_pnl'] < 2000]
    large_gain_scenarios = [s for s in scenario_results if s['total_pnl'] >= 2000]

    loss_prob = sum(float(s['probability'].rstrip('%')) for s in loss_scenarios)
    small_gain_prob = sum(float(s['probability'].rstrip('%')) for s in small_gain_scenarios)
    large_gain_prob = sum(float(s['probability'].rstrip('%')) for s in large_gain_scenarios)

    print(f"{'Outcome Category':<25} {'Probability':<15} {'Scenarios'}")
    print("-" * 80)
    print(f"{'Net Loss':<25} {loss_prob:<14.0f}% {len(loss_scenarios)} scenarios")
    print(f"{'Small Gain ($0-2K)':<25} {small_gain_prob:<14.0f}% {len(small_gain_scenarios)} scenarios")
    print(f"{'Large Gain (>$2K)':<25} {large_gain_prob:<14.0f}% {len(large_gain_scenarios)} scenarios")
    print()

    print("=" * 80)
    print("DECISION FRAMEWORK")
    print("=" * 80)
    print()

    print("RISK TOLERANCE ASSESSMENT")
    print("-" * 80)
    print()

    # Conservative investor
    print("FOR CONSERVATIVE INVESTORS:")
    print("  Concerned about: Potential loss scenarios ({:.0f}% probability)".format(loss_prob))
    print(f"  Downside risk:   ${downside_risk:,.2f} (worst case)")
    print(f"  Recommendation:  Consider selling if rate hikes expected")
    print()

    # Moderate investor
    print("FOR MODERATE INVESTORS:")
    print("  Focus on:        Balanced risk/reward")
    print(f"  Expected value:  ${weighted_pnl:,.2f}")
    print(f"  Recommendation:  Hold if comfortable with volatility")
    print()

    # Aggressive investor
    print("FOR AGGRESSIVE INVESTORS:")
    print("  Opportunity:     Large gains ({:.0f}% probability)".format(large_gain_prob))
    print(f"  Upside potential: ${upside_potential:,.2f}")
    print(f"  Recommendation:  Hold or buy more if rate cuts expected")
    print()

    print("=" * 80)
    print("HEDGING STRATEGIES")
    print("=" * 80)
    print()

    strategies = [
        {
            'name': 'Do Nothing (Hold)',
            'action': 'Keep current position',
            'pros': 'No transaction costs, full upside potential',
            'cons': 'Full downside exposure',
            'best_for': 'Confident in stable/falling rates',
        },
        {
            'name': 'Sell Entire Position',
            'action': 'Exit now at current price',
            'pros': 'Lock in current gain, eliminate rate risk',
            'cons': 'Forfeit future gains, $5 commission',
            'best_for': 'Expecting significant rate hikes',
        },
        {
            'name': 'Partial Sale (50%)',
            'action': 'Sell half, keep half',
            'pros': 'Reduce risk while maintaining upside',
            'cons': 'Partial commission, half exposure',
            'best_for': 'Uncertain about rate direction',
        },
        {
            'name': 'Stop-Loss Order',
            'action': 'Set automatic sell if price drops X%',
            'pros': 'Limits downside automatically',
            'cons': 'May trigger on temporary volatility',
            'best_for': 'Want protection with minimal effort',
        },
        {
            'name': 'Ladder Strategy',
            'action': 'Sell and buy multiple maturities',
            'pros': 'Diversifies rate risk across time',
            'cons': 'Multiple commissions, complexity',
            'best_for': 'Long-term conservative approach',
        },
    ]

    for i, strategy in enumerate(strategies, 1):
        print(f"STRATEGY {i}: {strategy['name']}")
        print("-" * 80)
        print(f"Action:     {strategy['action']}")
        print(f"Pros:       {strategy['pros']}")
        print(f"Cons:       {strategy['cons']}")
        print(f"Best For:   {strategy['best_for']}")
        print()

    print("=" * 80)
    print("MARKET CONTEXT & OUTLOOK")
    print("=" * 80)
    print()

    print("CURRENT RATE ENVIRONMENT (October 2025)")
    print("-" * 80)
    print("• Fed policy stance: [Consult current market data]")
    print("• Inflation trends: [Check latest CPI data]")
    print("• Economic growth: [Review GDP forecasts]")
    print("• Market expectations: [See Fed funds futures]")
    print()

    print("FACTORS SUPPORTING RATE CUTS:")
    print("  ✓ Economic slowdown")
    print("  ✓ Inflation returning to target")
    print("  ✓ Recession concerns")
    print("  → FAVORABLE for bond prices ↑")
    print()

    print("FACTORS SUPPORTING RATE HIKES:")
    print("  ✗ Persistent inflation")
    print("  ✗ Strong economic growth")
    print("  ✗ Wage growth acceleration")
    print("  → UNFAVORABLE for bond prices ↓")
    print()

    print("=" * 80)
    print("RECOMMENDATIONS BY SCENARIO")
    print("=" * 80)
    print()

    print("IF YOU EXPECT RATES TO RISE:")
    print("-" * 80)
    print("1. Consider selling now to avoid losses")
    print("2. Wait for better entry points (lower prices)")
    print("3. Switch to shorter-duration bonds")
    print("4. Diversify into inflation-protected securities")
    print()

    print("IF YOU EXPECT RATES TO FALL:")
    print("-" * 80)
    print("1. HOLD current position for capital gains")
    print("2. Consider buying more at current levels")
    print("3. Extend duration for greater sensitivity")
    print("4. Ride the price appreciation")
    print()

    print("IF YOU'RE UNCERTAIN:")
    print("-" * 80)
    print("1. Partial sale (50%) to reduce risk")
    print("2. Set stop-loss at -5% or -10%")
    print("3. Build ladder with multiple maturities")
    print("4. Monitor Fed communications closely")
    print()

    print("=" * 80)
    print("SUMMARY & ACTION ITEMS")
    print("=" * 80)
    print()

    print(f"Current Position: ${current_price:,.2f} (${current_price - purchase_price:,.2f} unrealized gain)")
    print(f"Rate Risk:        ~{years_to_maturity:.1f}% price change per 1% rate move")
    print(f"Best Case:        ${best_case['new_price']:,.2f} (+${best_case['new_price'] - current_price:,.2f})")
    print(f"Worst Case:       ${worst_case['new_price']:,.2f} (-${current_price - worst_case['new_price']:,.2f})")
    print(f"Expected Value:   ${weighted_price:,.2f}")
    print()

    print("NEXT STEPS:")
    print("1. ✓ Monitor Federal Reserve policy announcements")
    print("2. ✓ Track 10-year Treasury yields as benchmark")
    print("3. ✓ Review inflation and economic data monthly")
    print("4. ✓ Reassess position after major rate changes")
    print("5. ✓ Consider your personal risk tolerance and time horizon")
    print()

    print("=" * 80)

def main():
    analyze_rate_scenarios()

if __name__ == '__main__':
    main()
