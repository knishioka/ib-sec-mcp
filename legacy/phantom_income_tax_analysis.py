#!/usr/bin/env python3
"""
Phantom Income Tax Analysis for Zero-Coupon Bonds
Calculates annual tax liability from imputed interest on Treasury STRIPS
"""

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import math

def calculate_phantom_income():
    """
    Calculate phantom income (imputed interest) for Treasury STRIP

    Phantom Income = The annual taxable interest income on zero-coupon bonds
    even though no cash is received until maturity.

    IRS requires reporting this as ordinary income each year.
    """

    print("=" * 80)
    print("PHANTOM INCOME TAX ANALYSIS")
    print("US Treasury STRIP - Zero Coupon Bond")
    print("=" * 80)
    print()

    # Bond details
    cusip = "912834JH2"
    isin = "US912834JH26"
    security_name = "S 0 11/15/40"

    face_value = 50000
    purchase_price = 23457  # Actual cost basis
    purchase_date = datetime(2025, 7, 10)
    maturity_date = datetime(2040, 11, 15)

    current_date = datetime(2025, 10, 5)

    # Calculate total holding period
    total_days = (maturity_date - purchase_date).days
    total_years = total_days / 365.25

    # Calculate yield to maturity (YTM)
    ytm = math.pow(face_value / purchase_price, 1 / total_years) - 1

    print("BOND INFORMATION")
    print("-" * 80)
    print(f"Security:              {security_name}")
    print(f"CUSIP:                 {cusip}")
    print(f"ISIN:                  {isin}")
    print(f"Type:                  Treasury STRIP (Zero Coupon)")
    print()
    print(f"Face Value:            ${face_value:,.2f}")
    print(f"Purchase Price:        ${purchase_price:,.2f}")
    print(f"Purchase Date:         {purchase_date.strftime('%Y-%m-%d')}")
    print(f"Maturity Date:         {maturity_date.strftime('%Y-%m-%d')}")
    print(f"Holding Period:        {total_years:.2f} years ({total_days} days)")
    print(f"Yield to Maturity:     {ytm * 100:.3f}%")
    print()

    print("=" * 80)
    print("WHAT IS PHANTOM INCOME?")
    print("=" * 80)
    print()
    print("Phantom Income (also called 'Original Issue Discount' or OID):")
    print()
    print("• Zero-coupon bonds don't pay interest until maturity")
    print("• However, the IRS treats the price appreciation as taxable interest")
    print("• You must report this 'phantom' interest as income EACH YEAR")
    print("• Even though you receive NO CASH until maturity in 2040")
    print()
    print("This creates a tax liability WITHOUT corresponding cash flow!")
    print()

    print("=" * 80)
    print("ANNUAL PHANTOM INCOME CALCULATION")
    print("=" * 80)
    print()

    # Calculate year-by-year phantom income
    print("Method: Constant Yield Method (IRS Publication 1212)")
    print()
    print(f"{'Year':<6} {'Start Value':<15} {'Interest Income':<18} {'End Value':<15} "
          f"{'Days Held':<10} {'Tax Owed*':<12}")
    print("-" * 80)

    adjusted_basis = purchase_price
    total_phantom_income = 0
    tax_year_data = []

    current_year = purchase_date.year
    end_year = maturity_date.year

    for year in range(current_year, end_year + 1):
        # Determine the period for this tax year
        if year == current_year:
            year_start = purchase_date
            year_end = datetime(year, 12, 31)
        elif year == end_year:
            year_start = datetime(year, 1, 1)
            year_end = maturity_date
        else:
            year_start = datetime(year, 1, 1)
            year_end = datetime(year, 12, 31)

        # Only calculate if we've reached this year
        if year_end < current_date or year == current_year or year <= current_year:
            days_in_period = (year_end - year_start).days + 1

            # Calculate accrued interest for this period
            # Using constant yield method
            if year == end_year:
                # Final year - interest is remaining to reach face value
                accrued_interest = face_value - adjusted_basis
            else:
                # Calculate based on YTM
                fraction_of_year = days_in_period / 365.25
                accrued_interest = adjusted_basis * (math.pow(1 + ytm, fraction_of_year) - 1)

            ending_basis = adjusted_basis + accrued_interest

            # Estimate tax (assuming 30% marginal rate for illustration)
            # Actual rate depends on individual tax situation
            estimated_tax = accrued_interest * 0.30

            status = "✓ Reported" if year < current_year or (year == current_year and current_date >= datetime(year, 12, 31)) else "→ Future"

            if year <= current_year:
                print(f"{year:<6} ${adjusted_basis:<14,.2f} ${accrued_interest:<17,.2f} "
                      f"${ending_basis:<14,.2f} {days_in_period:<10} ${estimated_tax:<11,.2f}")
            else:
                print(f"{year:<6} ${adjusted_basis:<14,.2f} ${accrued_interest:<17,.2f} "
                      f"${ending_basis:<14,.2f} {days_in_period:<10} ${estimated_tax:<11,.2f} (Future)")

            tax_year_data.append({
                'year': year,
                'start_value': adjusted_basis,
                'interest': accrued_interest,
                'end_value': ending_basis,
                'days': days_in_period,
                'tax': estimated_tax,
                'status': status
            })

            total_phantom_income += accrued_interest
            adjusted_basis = ending_basis

    print("-" * 80)
    print(f"{'TOTAL':<6} ${purchase_price:<14,.2f} ${total_phantom_income:<17,.2f} "
          f"${face_value:<14,.2f} {total_days:<10} ${total_phantom_income * 0.30:<11,.2f}")
    print()
    print("*Estimated tax at 30% marginal rate (for illustration only)")
    print()

    # Calculate tax already owed for 2025
    tax_2025 = [t for t in tax_year_data if t['year'] == 2025]
    if tax_2025:
        interest_2025 = tax_2025[0]['interest']
        tax_owed_2025 = tax_2025[0]['tax']

        print("=" * 80)
        print("2025 TAX YEAR IMPACT")
        print("=" * 80)
        print()
        print(f"Purchase Date:         {purchase_date.strftime('%Y-%m-%d')}")
        print(f"Days Held in 2025:     {tax_2025[0]['days']} days")
        print(f"Phantom Interest:      ${interest_2025:,.2f}")
        print(f"Estimated Tax (30%):   ${tax_owed_2025:,.2f}")
        print()
        print("⚠️  You must report this ${:,.2f} as taxable interest income".format(interest_2025))
        print("    on your 2025 tax return, even though you received NO CASH.")
        print()

    print("=" * 80)
    print("CUMULATIVE TAX BURDEN ANALYSIS")
    print("=" * 80)
    print()

    # Calculate cumulative tax over holding period
    years_held = [2025, 2026, 2027, 2028, 2029, 2030, 2035, 2040]  # Sample years

    print(f"{'Year':<8} {'Cumulative Interest':<22} {'Cumulative Tax (30%)':<22} {'% of Total'}")
    print("-" * 80)

    cumulative_interest = 0
    for year_data in tax_year_data:
        year = year_data['year']
        if year in years_held:
            cumulative_interest += year_data['interest']
            cumulative_tax = cumulative_interest * 0.30
            pct_of_total = cumulative_interest / total_phantom_income * 100
            print(f"{year:<8} ${cumulative_interest:<21,.2f} ${cumulative_tax:<21,.2f} {pct_of_total:>6.1f}%")

    print()

    print("=" * 80)
    print("TAX PLANNING CONSIDERATIONS")
    print("=" * 80)
    print()

    print("1. ANNUAL TAX BURDEN (No Cash Received)")
    print("-" * 80)
    avg_annual_interest = total_phantom_income / len(tax_year_data)
    avg_annual_tax = avg_annual_interest * 0.30
    print(f"   Average Annual Phantom Income:  ${avg_annual_interest:,.2f}")
    print(f"   Average Annual Tax (30%):       ${avg_annual_tax:,.2f}")
    print()
    print("   ⚠️  You need OTHER income sources to pay these taxes")
    print("       because the bond pays NO cash until 2040!")
    print()

    print("2. US TAX TREATMENT (For Non-Residents)")
    print("-" * 80)
    print("   • US Treasury interest is normally EXEMPT from withholding for non-residents")
    print("   • However, phantom income (OID) tax treatment may vary")
    print("   • Consult a US tax advisor specializing in non-resident taxation")
    print()

    print("3. MALAYSIAN TAX TREATMENT")
    print("-" * 80)
    print("   • Malaysia generally does NOT tax foreign-source income")
    print("   • If you are Malaysian tax resident, foreign investment income is typically exempt")
    print("   • However, rules can change - consult a Malaysian tax advisor")
    print()

    print("4. TAX TREATY CONSIDERATIONS")
    print("-" * 80)
    print("   • US-Malaysia Tax Treaty may provide relief from double taxation")
    print("   • Treaty typically allows taxation in residence country only")
    print("   • Form W-8BEN may be required to claim treaty benefits")
    print()

    print("5. REPORTING REQUIREMENTS")
    print("-" * 80)
    print("   • IRS Form 1099-OID will be issued annually by broker")
    print("   • Report on US tax return if filing is required")
    print("   • Keep records of OID accruals for basis adjustment")
    print()

    print("=" * 80)
    print("TAX OPTIMIZATION STRATEGIES")
    print("=" * 80)
    print()

    strategies = [
        {
            'strategy': 'Hold in Tax-Advantaged Account',
            'description': 'IRA, 401(k), or tax-deferred accounts (US residents only)',
            'pros': 'No annual tax on phantom income',
            'cons': 'Not applicable to non-US residents',
            'applicability': 'N/A (You are non-US resident)'
        },
        {
            'strategy': 'Tax-Loss Harvesting',
            'description': 'Sell other investments at a loss to offset phantom income',
            'pros': 'Reduces overall tax burden',
            'cons': 'Requires other investments with losses',
            'applicability': 'Possible if US tax filing required'
        },
        {
            'strategy': 'Sell Before Year-End',
            'description': 'Sell bond to realize loss/gain instead of phantom income',
            'pros': 'Convert phantom income to realized gain/loss',
            'cons': 'Give up future gains, pay commission',
            'applicability': 'Available option'
        },
        {
            'strategy': 'Short-Term STRIPS',
            'description': 'Buy shorter maturity STRIPS (lower phantom income)',
            'pros': 'Less annual tax burden',
            'cons': 'Lower yield, more frequent reinvestment',
            'applicability': 'For future purchases'
        },
        {
            'strategy': 'Accept Tax Burden',
            'description': 'Pay taxes from other income sources',
            'pros': 'Simple, no action needed',
            'cons': 'Annual cash outflow for taxes',
            'applicability': 'Current default strategy'
        },
    ]

    for i, strat in enumerate(strategies, 1):
        print(f"STRATEGY {i}: {strat['strategy']}")
        print("-" * 80)
        print(f"Description:    {strat['description']}")
        print(f"Pros:           {strat['pros']}")
        print(f"Cons:           {strat['cons']}")
        print(f"Applicability:  {strat['applicability']}")
        print()

    print("=" * 80)
    print("15-YEAR TAX CASHFLOW SUMMARY")
    print("=" * 80)
    print()

    total_tax_burden = total_phantom_income * 0.30

    print(f"Total Phantom Income (2025-2040):    ${total_phantom_income:,.2f}")
    print(f"Estimated Total Tax (30%):           ${total_tax_burden:,.2f}")
    print()
    print(f"Investment at Purchase:              ${purchase_price:,.2f}")
    print(f"Estimated Tax Payments:              ${total_tax_burden:,.2f}")
    print(f"Total Cash Outflow:                  ${purchase_price + total_tax_burden:,.2f}")
    print()
    print(f"Cash Received at Maturity:           ${face_value:,.2f}")
    print(f"After-Tax Profit:                    ${face_value - purchase_price - total_tax_burden:,.2f}")
    print(f"After-Tax ROI:                       {(face_value - purchase_price - total_tax_burden) / purchase_price * 100:.2f}%")
    print()

    # Calculate effective yield
    after_tax_gain = face_value - purchase_price - total_tax_burden
    after_tax_ytm = math.pow((purchase_price + after_tax_gain) / purchase_price, 1 / total_years) - 1

    print(f"Pre-Tax Yield (YTM):                 {ytm * 100:.3f}%")
    print(f"After-Tax Yield (estimated):         {after_tax_ytm * 100:.3f}%")
    print(f"Tax Impact on Yield:                 {(ytm - after_tax_ytm) * 100:.3f}%")
    print()

    print("=" * 80)
    print("IMPORTANT DISCLAIMERS")
    print("=" * 80)
    print()
    print("⚠️  TAX SITUATION IS COMPLEX - PROFESSIONAL ADVICE REQUIRED")
    print()
    print("This analysis makes several ASSUMPTIONS:")
    print()
    print("1. 30% marginal tax rate (for illustration only)")
    print("   → Your actual rate may be 0%, 10%, 24%, or other depending on:")
    print("     - Your tax residency status")
    print("     - US filing requirements")
    print("     - Income level and tax brackets")
    print("     - Tax treaty benefits")
    print()
    print("2. US tax obligations for non-residents")
    print("   → May not apply if you don't have US-source income filing requirement")
    print("   → Treasury interest may be exempt under tax treaty")
    print()
    print("3. Malaysian tax treatment")
    print("   → Foreign income typically not taxed, but rules vary")
    print("   → Remittance to Malaysia may trigger tax")
    print()
    print("NEXT STEPS:")
    print()
    print("1. Consult a US tax advisor specializing in non-resident taxation")
    print("2. Consult a Malaysian tax advisor for local tax obligations")
    print("3. Review US-Malaysia Tax Treaty provisions")
    print("4. Determine if Form W-8BEN is needed for treaty benefits")
    print("5. Keep detailed records of all OID accruals")
    print()
    print("=" * 80)
    print()
    print("This analysis is for educational purposes only and does not constitute")
    print("tax advice. Consult qualified tax professionals in both jurisdictions.")
    print()
    print("=" * 80)

def main():
    calculate_phantom_income()

if __name__ == '__main__':
    main()
