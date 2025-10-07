#!/usr/bin/env python3
"""
US Treasury STRIP Bond Hold-to-Maturity Analysis
Analyzes holding scenarios for S 0 11/15/40 (US Treasury STRIP)
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

def analyze_strip_bond():
    """
    Analyze US Treasury STRIP (Separate Trading of Registered Interest and Principal of Securities)

    STRIP = Zero-coupon bond created by stripping coupons from Treasury securities
    S 0 11/15/40 = Treasury STRIP maturing November 15, 2040
    """

    print("=" * 80)
    print("US TREASURY STRIP BOND ANALYSIS - S 0 11/15/40")
    print("=" * 80)
    print()

    # Current position details
    face_value = 50000  # Par value at maturity
    quantity = 50000    # Units held
    current_price = 49.30192  # Current market price (% of par)
    purchase_price = 46.914   # Your purchase price (% of par)
    purchase_cost = 23457     # Total cost basis
    current_value = 24650.96  # Current market value
    unrealized_pnl = 1193.96  # Current unrealized P&L

    maturity_date = datetime(2040, 11, 15)
    purchase_date = datetime(2025, 7, 10)
    today = datetime(2025, 10, 5)

    days_held = (today - purchase_date).days
    days_to_maturity = (maturity_date - today).days
    years_to_maturity = days_to_maturity / 365.25

    print("CURRENT POSITION")
    print("-" * 80)
    print(f"Security:                US Treasury STRIP 0% 11/15/2040")
    print(f"CUSIP:                   912834JH2")
    print(f"ISIN:                    US912834JH26")
    print(f"")
    print(f"Face Value at Maturity:  ${face_value:,.2f}")
    print(f"Units Held:              {quantity:,}")
    print(f"")
    print(f"Purchase Date:           {purchase_date.strftime('%Y-%m-%d')}")
    print(f"Purchase Price:          {purchase_price}% of par")
    print(f"Total Cost Basis:        ${purchase_cost:,.2f}")
    print(f"")
    print(f"Current Date:            {today.strftime('%Y-%m-%d')}")
    print(f"Current Price:           {current_price}% of par")
    print(f"Current Value:           ${current_value:,.2f}")
    print(f"Unrealized P&L:          ${unrealized_pnl:,.2f} ({unrealized_pnl/purchase_cost*100:.2f}%)")
    print(f"")
    print(f"Days Held:               {days_held} days")
    print(f"Maturity Date:           {maturity_date.strftime('%Y-%m-%d')}")
    print(f"Days to Maturity:        {days_to_maturity:,} days")
    print(f"Years to Maturity:       {years_to_maturity:.2f} years")
    print()

    # Calculate yield to maturity (YTM)
    # For zero-coupon bonds: YTM = (Face Value / Purchase Price) ^ (1/Years) - 1
    ytm = (pow(face_value / purchase_cost, 1 / years_to_maturity) - 1) * 100

    print("=" * 80)
    print("SCENARIO 1: HOLD TO MATURITY (Nov 15, 2040)")
    print("=" * 80)
    print()

    print("MATURITY PROCEEDS")
    print("-" * 80)
    print(f"Face Value Payment:      ${face_value:,.2f}")
    print(f"Total Cost Basis:        ${purchase_cost:,.2f}")
    print(f"Total Gain at Maturity:  ${face_value - purchase_cost:,.2f}")
    print(f"")
    print(f"Return on Investment:    {(face_value - purchase_cost) / purchase_cost * 100:.2f}%")
    print(f"Annualized Yield (YTM):  {ytm:.3f}%")
    print(f"Holding Period:          {years_to_maturity:.2f} years")
    print()

    print("INTERACTIVE BROKERS FEES & COSTS")
    print("-" * 80)
    print(f"Purchase Commission:     $5.00 (already paid)")
    print(f"Annual Custody Fee:      $0.00 (IB doesn't charge for US Treasuries)")
    print(f"Maturity Processing:     $0.00 (automatic, no fee)")
    print(f"Total Additional Costs:  $0.00")
    print()

    print("NET PROCEEDS AT MATURITY")
    print("-" * 80)
    final_value = face_value
    total_invested = purchase_cost + 5  # Including commission
    net_profit = final_value - total_invested
    net_roi = (net_profit / total_invested) * 100

    print(f"Maturity Value:          ${final_value:,.2f}")
    print(f"Total Investment:        ${total_invested:,.2f} (cost + commission)")
    print(f"Net Profit:              ${net_profit:,.2f}")
    print(f"Net ROI:                 {net_roi:.2f}%")
    print(f"Annualized Return:       {ytm:.3f}%")
    print()

    print("=" * 80)
    print("SCENARIO 2: SELL NOW (Oct 5, 2025)")
    print("=" * 80)
    print()

    print("IMMEDIATE SALE PROCEEDS")
    print("-" * 80)

    # Estimate selling costs (IB bond commission structure)
    # Typically $1-5 per trade for bonds
    estimated_sell_commission = 5.00

    sale_proceeds = current_value - estimated_sell_commission
    net_profit_sell_now = sale_proceeds - purchase_cost - 5  # Including both commissions
    net_roi_sell_now = (net_profit_sell_now / (purchase_cost + 5)) * 100

    # Calculate holding period return
    holding_days = days_held
    annualized_return = (net_roi_sell_now / holding_days * 365.25)

    print(f"Current Market Value:    ${current_value:,.2f}")
    print(f"Est. Selling Commission: ${estimated_sell_commission:,.2f}")
    print(f"Net Sale Proceeds:       ${sale_proceeds:,.2f}")
    print(f"")
    print(f"Total Investment:        ${purchase_cost + 5:,.2f}")
    print(f"Net Profit:              ${net_profit_sell_now:,.2f}")
    print(f"Net ROI:                 {net_roi_sell_now:.2f}%")
    print(f"Holding Period:          {holding_days} days")
    print(f"Annualized Return:       {annualized_return:.2f}%")
    print()

    print("=" * 80)
    print("COMPARISON & RECOMMENDATION")
    print("=" * 80)
    print()

    print(f"{'Metric':<30} {'Sell Now':<20} {'Hold to Maturity':<20}")
    print("-" * 80)
    print(f"{'Total Proceeds':<30} ${sale_proceeds:<19,.2f} ${final_value:<19,.2f}")
    print(f"{'Net Profit':<30} ${net_profit_sell_now:<19,.2f} ${net_profit:<19,.2f}")
    print(f"{'ROI':<30} {net_roi_sell_now:<19.2f}% {net_roi:<19.2f}%")
    print(f"{'Annualized Return':<30} {annualized_return:<19.2f}% {ytm:<19.3f}%")
    print(f"{'Time to Realize':<30} {'Immediate':<20} {f'{years_to_maturity:.1f} years':<20}")
    print(f"{'Additional Costs':<30} ${estimated_sell_commission:<19,.2f} ${0:<19,.2f}")
    print()

    print("KEY CONSIDERATIONS")
    print("-" * 80)
    print("✓ PROS of Holding to Maturity:")
    print("  • Guaranteed return of $50,000 at maturity (US government-backed)")
    print(f"  • Locked-in yield of {ytm:.3f}% annually")
    print("  • No additional transaction costs")
    print("  • No reinvestment risk")
    print("  • Predictable cash flow in 2040")
    print()
    print("✗ CONS of Holding to Maturity:")
    print(f"  • Capital locked up for {years_to_maturity:.1f} years")
    print("  • Interest rate risk (if rates rise, opportunity cost increases)")
    print("  • Inflation risk (purchasing power erosion over 15 years)")
    print("  • Liquidity constraints (cannot access funds without selling)")
    print()
    print("✓ PROS of Selling Now:")
    print("  • Immediate access to capital (~$24,646)")
    print(f"  • Lock in current {net_roi_sell_now:.2f}% gain")
    print("  • Opportunity to reinvest in higher-yielding assets")
    print("  • Reduced duration/interest rate risk")
    print()
    print("✗ CONS of Selling Now:")
    print("  • Additional $5 commission")
    print(f"  • Forfeit remaining ${net_profit - net_profit_sell_now:,.2f} potential gain")
    print("  • Reinvestment risk (may not find better yield)")
    print("  • Market timing risk")
    print()

    print("=" * 80)
    print("INTEREST RATE SENSITIVITY ANALYSIS")
    print("=" * 80)
    print()
    print("If interest rates RISE by 1%:")
    print(f"  → Bond price will FALL approximately ${current_value * 0.15:,.2f} (15% for 15-year duration)")
    print(f"  → Your position would be worth ~${current_value * 0.85:,.2f}")
    print()
    print("If interest rates FALL by 1%:")
    print(f"  → Bond price will RISE approximately ${current_value * 0.15:,.2f}")
    print(f"  → Your position would be worth ~${current_value * 1.15:,.2f}")
    print()

    print("=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print()
    print("Based on the analysis:")
    print()
    print(f"1. Your YTM of {ytm:.3f}% is ABOVE current risk-free rates (~4.5% for 10Y Treasury)")
    print("   → This suggests your bond is providing good value")
    print()
    print("2. With 15 years to maturity, you face significant interest rate risk")
    print("   → If rates rise, you could see substantial mark-to-market losses")
    print()
    print("3. Your current unrealized gain of $1,193.96 represents profit cushion")
    print("   → Consider your risk tolerance and liquidity needs")
    print()
    print("SUGGESTED STRATEGY:")
    print("  • If you don't need the capital: HOLD to maturity for guaranteed return")
    print("  • If you need liquidity: SELL now and lock in gains")
    print("  • If concerned about rising rates: SELL and reinvest in shorter duration")
    print("  • If rates are expected to fall: HOLD or even buy more for capital gains")
    print()
    print("Note: This is educational analysis only, not financial advice.")
    print("Consider consulting with a financial advisor for personalized guidance.")
    print()
    print("=" * 80)

if __name__ == '__main__':
    analyze_strip_bond()
