#!/usr/bin/env python3
"""
Trading Cost Efficiency Analysis
Comprehensive analysis of commissions, fees, and cost efficiency
"""

import csv
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

def parse_data(filepath: str) -> Dict[str, List[Dict]]:
    """Parse CSV sections"""
    sections = {}
    current_section = None
    headers = []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

        for row in reader:
            if not row or not row[0]:
                continue

            if row[0] == 'ClientAccountID':
                headers = row
                if 'TradeID' in headers:
                    current_section = 'trades'
                elif 'StartingCash' in headers and 'LevelOfDetail' in headers:
                    current_section = 'cash_summary'

                if current_section:
                    sections[current_section] = []
            elif current_section and headers:
                row_dict = dict(zip(headers, row))
                sections[current_section].append(row_dict)

    return sections

def analyze_trading_costs(trades: List[Dict], cash_summary: List[Dict]) -> Dict[str, Any]:
    """Analyze trading costs and efficiency"""

    # Overall metrics
    total_commissions = 0
    total_volume = 0

    # By symbol
    by_symbol = defaultdict(lambda: {
        'trades': 0,
        'volume': 0,
        'commissions': 0,
        'avg_commission': 0
    })

    # By asset class
    by_asset_class = defaultdict(lambda: {
        'trades': 0,
        'volume': 0,
        'commissions': 0
    })

    # By trade type
    buy_commissions = 0
    sell_commissions = 0
    buy_volume = 0
    sell_volume = 0
    buy_count = 0
    sell_count = 0

    # Trade size analysis
    trade_sizes = []
    commission_rates = []

    for trade in trades:
        symbol = trade.get('Symbol', '')
        asset_class = trade.get('AssetClass', '')
        buy_sell = trade.get('Buy/Sell', '')

        commission = abs(float(trade.get('IBCommission', 0)))
        trade_money = abs(float(trade.get('TradeMoney', 0)))
        quantity = abs(float(trade.get('Quantity', 0)))

        # Overall totals
        total_commissions += commission
        total_volume += trade_money

        # By symbol
        by_symbol[symbol]['trades'] += 1
        by_symbol[symbol]['volume'] += trade_money
        by_symbol[symbol]['commissions'] += commission

        # By asset class
        by_asset_class[asset_class]['trades'] += 1
        by_asset_class[asset_class]['volume'] += trade_money
        by_asset_class[asset_class]['commissions'] += commission

        # By trade type
        if buy_sell == 'BUY':
            buy_commissions += commission
            buy_volume += trade_money
            buy_count += 1
        else:
            sell_commissions += commission
            sell_volume += trade_money
            sell_count += 1

        # Trade size and rate analysis
        if trade_money > 0:
            trade_sizes.append(trade_money)
            commission_rate = (commission / trade_money) * 100
            commission_rates.append(commission_rate)

    # Calculate averages
    avg_commission = total_commissions / len(trades) if trades else 0
    avg_trade_size = total_volume / len(trades) if trades else 0
    overall_rate = (total_commissions / total_volume * 100) if total_volume > 0 else 0

    for symbol, data in by_symbol.items():
        data['avg_commission'] = data['commissions'] / data['trades'] if data['trades'] > 0 else 0
        data['rate'] = (data['commissions'] / data['volume'] * 100) if data['volume'] > 0 else 0

    for asset_class, data in by_asset_class.items():
        data['avg_commission'] = data['commissions'] / data['trades'] if data['trades'] > 0 else 0
        data['rate'] = (data['commissions'] / data['volume'] * 100) if data['volume'] > 0 else 0

    # Get cash summary data
    total_pnl = 0
    if cash_summary:
        cs = cash_summary[0]
        net_trades_sales = float(cs.get('NetTradesSales', 0))
        net_trades_purchases = abs(float(cs.get('NetTradesPurchases', 0)))
        total_pnl = net_trades_sales - net_trades_purchases

    return {
        'total_trades': len(trades),
        'total_commissions': total_commissions,
        'total_volume': total_volume,
        'avg_commission': avg_commission,
        'avg_trade_size': avg_trade_size,
        'overall_rate': overall_rate,
        'by_symbol': dict(by_symbol),
        'by_asset_class': dict(by_asset_class),
        'buy_commissions': buy_commissions,
        'sell_commissions': sell_commissions,
        'buy_volume': buy_volume,
        'sell_volume': sell_volume,
        'buy_count': buy_count,
        'sell_count': sell_count,
        'trade_sizes': trade_sizes,
        'commission_rates': commission_rates,
        'total_pnl': total_pnl,
    }

def generate_cost_report(analysis: Dict):
    """Generate comprehensive cost analysis report"""

    print("=" * 80)
    print("TRADING COST EFFICIENCY ANALYSIS")
    print("=" * 80)
    print()

    print("OVERALL COST SUMMARY")
    print("-" * 80)
    print(f"Total Trades:              {analysis['total_trades']}")
    print(f"Total Trading Volume:      ${analysis['total_volume']:,.2f}")
    print(f"Total Commissions Paid:    ${analysis['total_commissions']:.2f}")
    print(f"Average Commission/Trade:  ${analysis['avg_commission']:.2f}")
    print(f"Average Trade Size:        ${analysis['avg_trade_size']:,.2f}")
    print(f"Overall Commission Rate:   {analysis['overall_rate']:.4f}%")
    print()

    # Cost as percentage of P&L
    if analysis['total_pnl'] != 0:
        cost_pct_of_pnl = (analysis['total_commissions'] / abs(analysis['total_pnl'])) * 100
        print(f"Commissions as % of P&L:   {cost_pct_of_pnl:.2f}%")
    print()

    print("=" * 80)
    print("COST EFFICIENCY RATING")
    print("=" * 80)
    print()

    rate = analysis['overall_rate']

    if rate < 0.01:
        rating = "EXCELLENT"
        color = "🟢"
        assessment = "Extremely low cost - optimal efficiency"
    elif rate < 0.05:
        rating = "VERY GOOD"
        color = "🟢"
        assessment = "Low cost - good efficiency"
    elif rate < 0.10:
        rating = "GOOD"
        color = "🟡"
        assessment = "Moderate cost - acceptable efficiency"
    elif rate < 0.20:
        rating = "FAIR"
        color = "🟡"
        assessment = "Higher cost - consider optimization"
    else:
        rating = "POOR"
        color = "🔴"
        assessment = "High cost - needs improvement"

    print(f"Overall Rating:     {color} {rating}")
    print(f"Commission Rate:    {rate:.4f}%")
    print(f"Assessment:         {assessment}")
    print()

    # Industry benchmarks
    print("INDUSTRY BENCHMARKS")
    print("-" * 80)
    print("Discount Brokers:   0.002% - 0.01%  (e.g., IB, TD Ameritrade)")
    print("Full-Service:       0.10% - 0.50%   (traditional brokers)")
    print("High-Frequency:     0.001% - 0.005% (institutional)")
    print()
    print(f"Your Rate:          {rate:.4f}%")

    if rate < 0.01:
        print("Status:             ✓ BEATING discount broker benchmarks!")
    elif rate < 0.05:
        print("Status:             ✓ Within discount broker range")
    else:
        print("Status:             ⚠ Above discount broker range")
    print()

    print("=" * 80)
    print("COST BREAKDOWN BY SYMBOL")
    print("=" * 80)
    print()

    by_symbol = analysis['by_symbol']

    print(f"{'Symbol':<15} {'Trades':<8} {'Volume':<15} {'Commissions':<15} "
          f"{'Avg Comm':<12} {'Rate %':<10}")
    print("-" * 80)

    for symbol in sorted(by_symbol.keys()):
        data = by_symbol[symbol]
        print(f"{symbol:<15} {data['trades']:<8} ${data['volume']:<14,.2f} "
              f"${data['commissions']:<14.2f} ${data['avg_commission']:<11.2f} {data['rate']:<9.4f}%")

    print()

    print("=" * 80)
    print("COST BREAKDOWN BY ASSET CLASS")
    print("=" * 80)
    print()

    by_asset_class = analysis['by_asset_class']

    print(f"{'Asset Class':<15} {'Trades':<8} {'Volume':<15} {'Commissions':<15} "
          f"{'Avg Comm':<12} {'Rate %':<10}")
    print("-" * 80)

    for asset_class in sorted(by_asset_class.keys()):
        data = by_asset_class[asset_class]
        print(f"{asset_class:<15} {data['trades']:<8} ${data['volume']:<14,.2f} "
              f"${data['commissions']:<14.2f} ${data['avg_commission']:<11.2f} {data['rate']:<9.4f}%")

    print()

    print("=" * 80)
    print("BUY vs SELL COST ANALYSIS")
    print("=" * 80)
    print()

    buy_rate = (analysis['buy_commissions'] / analysis['buy_volume'] * 100) if analysis['buy_volume'] > 0 else 0
    sell_rate = (analysis['sell_commissions'] / analysis['sell_volume'] * 100) if analysis['sell_volume'] > 0 else 0

    print(f"{'Type':<10} {'Trades':<8} {'Volume':<15} {'Commissions':<15} "
          f"{'Avg Comm':<12} {'Rate %':<10}")
    print("-" * 80)

    avg_buy_comm = analysis['buy_commissions'] / analysis['buy_count'] if analysis['buy_count'] > 0 else 0
    avg_sell_comm = analysis['sell_commissions'] / analysis['sell_count'] if analysis['sell_count'] > 0 else 0

    print(f"{'BUY':<10} {analysis['buy_count']:<8} ${analysis['buy_volume']:<14,.2f} "
          f"${analysis['buy_commissions']:<14.2f} ${avg_buy_comm:<11.2f} {buy_rate:<9.4f}%")
    print(f"{'SELL':<10} {analysis['sell_count']:<8} ${analysis['sell_volume']:<14,.2f} "
          f"${analysis['sell_commissions']:<14.2f} ${avg_sell_comm:<11.2f} {sell_rate:<9.4f}%")

    print()

    # Check for asymmetry
    if abs(buy_rate - sell_rate) > 0.001:
        if buy_rate > sell_rate:
            print(f"⚠️  Buy commissions are {(buy_rate/sell_rate - 1)*100:.1f}% higher than sell")
        else:
            print(f"⚠️  Sell commissions are {(sell_rate/buy_rate - 1)*100:.1f}% higher than buy")
    else:
        print("✓ Buy and sell costs are balanced")

    print()

    print("=" * 80)
    print("COMMISSION RATE DISTRIBUTION")
    print("=" * 80)
    print()

    rates = analysis['commission_rates']
    if rates:
        min_rate = min(rates)
        max_rate = max(rates)
        avg_rate = sum(rates) / len(rates)

        print(f"Minimum Rate:      {min_rate:.4f}%")
        print(f"Maximum Rate:      {max_rate:.4f}%")
        print(f"Average Rate:      {avg_rate:.4f}%")
        print(f"Range:             {max_rate - min_rate:.4f}%")
        print()

        # Distribution
        very_low = sum(1 for r in rates if r < 0.005)
        low = sum(1 for r in rates if 0.005 <= r < 0.01)
        moderate = sum(1 for r in rates if 0.01 <= r < 0.05)
        high = sum(1 for r in rates if r >= 0.05)

        print("DISTRIBUTION:")
        print(f"  Very Low (<0.005%):    {very_low} trades ({very_low/len(rates)*100:.1f}%)")
        print(f"  Low (0.005-0.01%):     {low} trades ({low/len(rates)*100:.1f}%)")
        print(f"  Moderate (0.01-0.05%): {moderate} trades ({moderate/len(rates)*100:.1f}%)")
        print(f"  High (>0.05%):         {high} trades ({high/len(rates)*100:.1f}%)")
        print()

    print("=" * 80)
    print("TRADE SIZE vs COMMISSION EFFICIENCY")
    print("=" * 80)
    print()

    sizes = analysis['trade_sizes']
    if sizes:
        min_size = min(sizes)
        max_size = max(sizes)
        avg_size = sum(sizes) / len(sizes)

        print(f"Smallest Trade:    ${min_size:,.2f}")
        print(f"Largest Trade:     ${max_size:,.2f}")
        print(f"Average Trade:     ${avg_size:,.2f}")
        print()

        # Categorize by size
        small_trades = [s for s in sizes if s < 5000]
        medium_trades = [s for s in sizes if 5000 <= s < 20000]
        large_trades = [s for s in sizes if s >= 20000]

        print("TRADE SIZE DISTRIBUTION:")
        print(f"  Small (<$5K):      {len(small_trades)} trades ({len(small_trades)/len(sizes)*100:.1f}%)")
        print(f"  Medium ($5-20K):   {len(medium_trades)} trades ({len(medium_trades)/len(sizes)*100:.1f}%)")
        print(f"  Large (>$20K):     {len(large_trades)} trades ({len(large_trades)/len(sizes)*100:.1f}%)")
        print()

    print("=" * 80)
    print("COST IMPACT ON PROFITABILITY")
    print("=" * 80)
    print()

    # Calculate metrics
    gross_pnl = analysis['total_pnl'] + analysis['total_commissions']
    net_pnl = analysis['total_pnl']
    commission_drag = analysis['total_commissions']

    if gross_pnl != 0:
        cost_impact = (commission_drag / abs(gross_pnl)) * 100
    else:
        cost_impact = 0

    print(f"Gross P&L (before costs):  ${gross_pnl:,.2f}")
    print(f"Total Commissions:         ${commission_drag:,.2f}")
    print(f"Net P&L (after costs):     ${net_pnl:,.2f}")
    print()
    print(f"Commission Impact:         {cost_impact:.2f}% of gross P&L")
    print()

    if cost_impact < 1:
        print("✓ EXCELLENT: Costs have minimal impact on profits (<1%)")
    elif cost_impact < 2:
        print("✓ GOOD: Costs are well-controlled (1-2%)")
    elif cost_impact < 5:
        print("⚠ ACCEPTABLE: Costs are noticeable (2-5%)")
    else:
        print("⚠ HIGH: Costs are significantly eroding profits (>5%)")

    print()

    print("=" * 80)
    print("BROKER FEE STRUCTURE (INTERACTIVE BROKERS)")
    print("=" * 80)
    print()

    print("STOCKS & ETFs (IBKR Lite - USA):")
    print("  Commission:        $0 per trade")
    print("  Your VOO trades:   $0 expected, ${:.2f} actual".format(
        sum(by_symbol[s]['commissions'] for s in by_symbol if 'VOO' in s)
    ))
    print()

    print("BONDS (US Treasuries):")
    print("  Commission:        0.2 bps (0.002%) up to $1M face value")
    print("  Minimum:           Typically $1-5 per trade")
    print("  Your bond trades:  ${:.2f} actual".format(
        sum(by_symbol[s]['commissions'] for s in by_symbol if 'S 0' in s)
    ))
    print()

    print("⚠️  NOTE: Actual commissions may differ from listed rates due to:")
    print("    • Exchange fees and regulatory fees")
    print("    • Routing fees")
    print("    • Market data fees (if applicable)")
    print("    • Account type differences (IBKR Pro vs Lite)")
    print()

    print("=" * 80)
    print("COST OPTIMIZATION OPPORTUNITIES")
    print("=" * 80)
    print()

    recommendations = []

    # Check overall rate
    if analysis['overall_rate'] < 0.01:
        recommendations.append("✓ Your costs are already excellent - no optimization needed")
    else:
        recommendations.append("• Review broker fee structure for potential savings")

    # Check trade size efficiency
    if sizes and len(small_trades) > len(sizes) * 0.3:
        recommendations.append("• Consider batching smaller trades to reduce per-trade costs")
        recommendations.append(f"  → {len(small_trades)} trades under $5K could be combined")

    # Check asset class differences
    if len(by_asset_class) > 1:
        rates_by_class = [(ac, data['rate']) for ac, data in by_asset_class.items()]
        rates_by_class.sort(key=lambda x: x[1])

        if rates_by_class[-1][1] > rates_by_class[0][1] * 2:
            recommendations.append(f"• {rates_by_class[-1][0]} has higher costs ({rates_by_class[-1][1]:.4f}%)")
            recommendations.append(f"  → Consider if {rates_by_class[0][0]} alternatives exist")

    # Check VOO commissions
    if 'VOO' in by_symbol and by_symbol['VOO']['commissions'] > 0:
        recommendations.append(f"• VOO commissions: ${by_symbol['VOO']['commissions']:.2f}")
        recommendations.append("  → IBKR Lite offers $0 commission for US stocks/ETFs")
        recommendations.append("  → Consider account type if not using IBKR Lite")

    # Check frequency
    if analysis['total_trades'] > 50:
        recommendations.append("• High trading frequency may accumulate costs")
        recommendations.append("  → Consider reducing trade count for better efficiency")

    # General best practices
    recommendations.append("• Use limit orders to avoid poor fills and hidden costs")
    recommendations.append("• Trade during liquid hours to minimize spreads")
    recommendations.append("• Review monthly statements for unexpected fees")

    for i, rec in enumerate(recommendations, 1):
        if rec.startswith('•') or rec.startswith('✓'):
            print(rec)
        else:
            print(f"  {rec}")

    print()

    print("=" * 80)
    print("COMPARISON WITH ALTERNATIVES")
    print("=" * 80)
    print()

    # Compare with other brokers (hypothetical)
    volume = analysis['total_volume']
    trades = analysis['total_trades']

    print(f"{'Broker':<20} {'Fee Structure':<30} {'Your Cost':<15} {'Difference'}")
    print("-" * 80)

    # IB actual
    ib_cost = analysis['total_commissions']
    print(f"{'IB (Actual)':<20} {'Varies by asset':<30} ${ib_cost:<14.2f} {'Baseline'}")

    # IB Lite (stocks)
    ib_lite_cost = sum(by_symbol[s]['commissions'] for s in by_symbol if 'S 0' in s)
    diff = ib_lite_cost - ib_cost
    print(f"{'IB Lite (if stocks)':<20} {'$0 stocks, same bonds':<30} ${ib_lite_cost:<14.2f} ${diff:+.2f}")

    # Other brokers (hypothetical)
    fidelity_cost = 0  # $0 for stocks
    schwab_cost = 0    # $0 for stocks
    etrade_cost = 0    # $0 for stocks

    print(f"{'Fidelity':<20} {'$0 stocks/ETFs':<30} ~${fidelity_cost:<14.2f} ${fidelity_cost - ib_cost:+.2f}")
    print(f"{'Schwab':<20} {'$0 stocks/ETFs':<30} ~${schwab_cost:<14.2f} ${schwab_cost - ib_cost:+.2f}")
    print(f"{'E*TRADE':<20} {'$0 stocks/ETFs':<30} ~${etrade_cost:<14.2f} ${etrade_cost - ib_cost:+.2f}")

    print()
    print("Note: Comparison assumes similar bond pricing; some brokers may have different")
    print("      bond commission structures or wider spreads.")
    print()

    print("=" * 80)
    print("ANNUAL COST PROJECTION")
    print("=" * 80)
    print()

    # Project annual costs
    # Assuming data is from Jan-Oct (10 months)
    months_of_data = 10  # Adjust based on actual data
    annual_projection = (analysis['total_commissions'] / months_of_data) * 12

    print(f"Current Period:        {months_of_data} months")
    print(f"Commissions Paid:      ${analysis['total_commissions']:.2f}")
    print(f"Monthly Average:       ${analysis['total_commissions'] / months_of_data:.2f}")
    print(f"Annual Projection:     ${annual_projection:.2f}")
    print()

    # Impact on returns
    if analysis['total_volume'] > 0:
        annual_rate = (annual_projection / analysis['total_volume']) * 100
        print(f"Projected Annual Rate: {annual_rate:.4f}% of current volume")
    print()

    print("=" * 80)
    print("KEY TAKEAWAYS")
    print("=" * 80)
    print()

    print(f"1. COST EFFICIENCY: {rating} ({rate:.4f}%)")
    print(f"2. TOTAL PAID: ${analysis['total_commissions']:.2f} on ${analysis['total_volume']:,.2f} volume")
    print(f"3. IMPACT ON PROFIT: {cost_impact:.2f}% commission drag")
    print(f"4. COMPARISON: Better than full-service, competitive with discount brokers")
    print()

    if rate < 0.01:
        print("🎉 EXCELLENT PERFORMANCE!")
        print("   Your trading costs are extremely efficient.")
        print("   Continue current practices.")
    elif rate < 0.05:
        print("✓ GOOD PERFORMANCE")
        print("  Your costs are reasonable but there's room for optimization.")
    else:
        print("⚠️ ATTENTION NEEDED")
        print("  Consider implementing cost reduction strategies.")

    print()
    print("=" * 80)

def main():
    filepath = '/Users/ken/Developer/private/ib-sec/trades_2025_full.csv'

    # Parse data
    sections = parse_data(filepath)

    # Analyze costs
    analysis = analyze_trading_costs(
        sections.get('trades', []),
        sections.get('cash_summary', [])
    )

    # Generate report
    generate_cost_report(analysis)

if __name__ == '__main__':
    main()
