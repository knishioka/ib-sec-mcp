#!/usr/bin/env python3
"""
Monthly Performance Tracking and Analysis
Visualizes 2025 trading performance by month with trends
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

def analyze_monthly_performance(trades: List[Dict], cash_summary: List[Dict]) -> Dict[str, Any]:
    """Analyze performance by month"""

    # Group trades by month
    monthly_data = defaultdict(lambda: {
        'trades': [],
        'buy_count': 0,
        'sell_count': 0,
        'realized_pnl': 0,
        'commissions': 0,
        'volume': 0,
        'symbols': set()
    })

    for trade in trades:
        trade_date = trade.get('TradeDate', '')
        if not trade_date:
            continue

        try:
            date_obj = datetime.strptime(trade_date, '%Y%m%d')
            month_key = date_obj.strftime('%Y-%m')

            qty = float(trade.get('Quantity', 0))
            trade_money = abs(float(trade.get('TradeMoney', 0)))
            pnl = float(trade.get('FifoPnlRealized', 0))
            commission = abs(float(trade.get('IBCommission', 0)))
            symbol = trade.get('Symbol', '')

            monthly_data[month_key]['trades'].append(trade)
            if qty > 0:
                monthly_data[month_key]['buy_count'] += 1
            else:
                monthly_data[month_key]['sell_count'] += 1

            monthly_data[month_key]['realized_pnl'] += pnl
            monthly_data[month_key]['commissions'] += commission
            monthly_data[month_key]['volume'] += trade_money
            monthly_data[month_key]['symbols'].add(symbol)

        except ValueError:
            continue

    # Calculate cumulative metrics
    sorted_months = sorted(monthly_data.keys())
    cumulative_pnl = 0
    cumulative_commissions = 0

    for month in sorted_months:
        cumulative_pnl += monthly_data[month]['realized_pnl']
        cumulative_commissions += monthly_data[month]['commissions']
        monthly_data[month]['cumulative_pnl'] = cumulative_pnl
        monthly_data[month]['cumulative_commissions'] = cumulative_commissions
        monthly_data[month]['net_pnl'] = monthly_data[month]['realized_pnl'] - monthly_data[month]['commissions']

    # Get period info from cash summary
    period_start = None
    period_end = None
    starting_cash = 0
    ending_cash = 0

    if cash_summary:
        cs = cash_summary[0]
        period_start = cs.get('FromDate', '')
        period_end = cs.get('ToDate', '')
        starting_cash = float(cs.get('StartingCash', 0))
        ending_cash = float(cs.get('EndingCash', 0))

    return {
        'monthly_data': dict(monthly_data),
        'sorted_months': sorted_months,
        'period_start': period_start,
        'period_end': period_end,
        'starting_cash': starting_cash,
        'ending_cash': ending_cash,
        'total_months': len(sorted_months)
    }

def generate_monthly_report(analysis: Dict):
    """Generate monthly performance report with visualizations"""

    print("=" * 80)
    print("MONTHLY PERFORMANCE TRACKING - 2025")
    print("=" * 80)
    print()

    period_start = analysis['period_start']
    period_end = analysis['period_end']

    if period_start and period_end:
        start_date = datetime.strptime(period_start, '%Y%m%d')
        end_date = datetime.strptime(period_end, '%Y%m%d')
        print(f"Analysis Period:  {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}")
    print(f"Total Months:     {analysis['total_months']}")
    print()

    monthly_data = analysis['monthly_data']
    sorted_months = analysis['sorted_months']

    # Calculate overall statistics
    total_trades = sum(len(data['trades']) for data in monthly_data.values())
    total_pnl = sum(data['realized_pnl'] for data in monthly_data.values())
    total_commissions = sum(data['commissions'] for data in monthly_data.values())
    total_volume = sum(data['volume'] for data in monthly_data.values())

    print("OVERALL SUMMARY")
    print("-" * 80)
    print(f"Total Trades:          {total_trades}")
    print(f"Total Realized P&L:    ${total_pnl:,.2f}")
    print(f"Total Commissions:     ${total_commissions:,.2f}")
    print(f"Net P&L:               ${total_pnl - total_commissions:,.2f}")
    print(f"Total Trading Volume:  ${total_volume:,.2f}")
    print(f"Average P&L/Month:     ${total_pnl / len(sorted_months):,.2f}")
    print()

    print("=" * 80)
    print("MONTH-BY-MONTH BREAKDOWN")
    print("=" * 80)
    print()

    print(f"{'Month':<12} {'Trades':<8} {'Buy':<6} {'Sell':<6} {'P&L':<12} "
          f"{'Comm.':<10} {'Net P&L':<12} {'Symbols':<15}")
    print("-" * 80)

    for month in sorted_months:
        data = monthly_data[month]
        month_obj = datetime.strptime(month, '%Y-%m')
        month_str = month_obj.strftime('%b %Y')

        trade_count = len(data['trades'])
        buy_count = data['buy_count']
        sell_count = data['sell_count']
        pnl = data['realized_pnl']
        comm = data['commissions']
        net_pnl = data['net_pnl']
        symbols = ', '.join(sorted(data['symbols']))

        print(f"{month_str:<12} {trade_count:<8} {buy_count:<6} {sell_count:<6} "
              f"${pnl:<11,.2f} ${comm:<9,.2f} ${net_pnl:<11,.2f} {symbols:<15}")

    print("-" * 80)
    print(f"{'TOTAL':<12} {total_trades:<8} {'':<6} {'':<6} "
          f"${total_pnl:<11,.2f} ${total_commissions:<9,.2f} ${total_pnl - total_commissions:<11,.2f}")
    print()

    print("=" * 80)
    print("CUMULATIVE PERFORMANCE CHART")
    print("=" * 80)
    print()

    # ASCII chart for cumulative P&L
    print(f"{'Month':<12} {'Cumulative P&L':<20} {'Chart'}")
    print("-" * 80)

    max_pnl = max(data['cumulative_pnl'] for data in monthly_data.values())

    for month in sorted_months:
        data = monthly_data[month]
        month_obj = datetime.strptime(month, '%Y-%m')
        month_str = month_obj.strftime('%b %Y')
        cum_pnl = data['cumulative_pnl']

        # Create bar chart
        bar_length = int((cum_pnl / max_pnl) * 40) if max_pnl > 0 else 0
        bar = '█' * bar_length

        print(f"{month_str:<12} ${cum_pnl:<19,.2f} {bar}")

    print()

    print("=" * 80)
    print("MONTHLY P&L VISUALIZATION")
    print("=" * 80)
    print()

    # ASCII chart for monthly P&L
    print(f"{'Month':<12} {'Monthly P&L':<15} {'Chart'}")
    print("-" * 80)

    max_monthly_pnl = max(abs(data['net_pnl']) for data in monthly_data.values())

    for month in sorted_months:
        data = monthly_data[month]
        month_obj = datetime.strptime(month, '%Y-%m')
        month_str = month_obj.strftime('%b %Y')
        net_pnl = data['net_pnl']

        # Create bar chart (positive/negative)
        if net_pnl >= 0:
            bar_length = int((net_pnl / max_monthly_pnl) * 30) if max_monthly_pnl > 0 else 0
            bar = '█' * bar_length
            chart = f"{'':>30}{bar}"
        else:
            bar_length = int((abs(net_pnl) / max_monthly_pnl) * 30) if max_monthly_pnl > 0 else 0
            bar = '█' * bar_length
            chart = f"{bar[::-1]:>30}"

        print(f"{month_str:<12} ${net_pnl:<14,.2f} {chart}")

    print()

    print("=" * 80)
    print("TRADING ACTIVITY HEATMAP")
    print("=" * 80)
    print()

    print(f"{'Month':<12} {'Activity Level':<20} {'Intensity'}")
    print("-" * 80)

    max_trades = max(len(data['trades']) for data in monthly_data.values())

    for month in sorted_months:
        data = monthly_data[month]
        month_obj = datetime.strptime(month, '%Y-%m')
        month_str = month_obj.strftime('%b %Y')
        trade_count = len(data['trades'])

        # Activity level
        if trade_count >= 10:
            level = "Very High"
            intensity = '🔥' * 5
        elif trade_count >= 7:
            level = "High"
            intensity = '🔥' * 4
        elif trade_count >= 4:
            level = "Moderate"
            intensity = '🔥' * 3
        elif trade_count >= 2:
            level = "Low"
            intensity = '🔥' * 2
        else:
            level = "Minimal"
            intensity = '🔥' * 1

        print(f"{month_str:<12} {level:<20} {intensity}")

    print()

    print("=" * 80)
    print("PERFORMANCE TRENDS & INSIGHTS")
    print("=" * 80)
    print()

    # Identify best and worst months
    best_month = max(sorted_months, key=lambda m: monthly_data[m]['net_pnl'])
    worst_month = min(sorted_months, key=lambda m: monthly_data[m]['net_pnl'])
    most_active_month = max(sorted_months, key=lambda m: len(monthly_data[m]['trades']))

    best_month_obj = datetime.strptime(best_month, '%Y-%m')
    worst_month_obj = datetime.strptime(worst_month, '%Y-%m')
    most_active_obj = datetime.strptime(most_active_month, '%Y-%m')

    print("KEY METRICS")
    print("-" * 80)
    print(f"Best Month:           {best_month_obj.strftime('%B %Y')} (${monthly_data[best_month]['net_pnl']:,.2f})")
    print(f"Worst Month:          {worst_month_obj.strftime('%B %Y')} (${monthly_data[worst_month]['net_pnl']:,.2f})")
    print(f"Most Active Month:    {most_active_obj.strftime('%B %Y')} ({len(monthly_data[most_active_month]['trades'])} trades)")
    print()

    # Calculate consistency
    profitable_months = sum(1 for data in monthly_data.values() if data['net_pnl'] > 0)
    consistency_rate = profitable_months / len(sorted_months) * 100

    print(f"Profitable Months:    {profitable_months}/{len(sorted_months)} ({consistency_rate:.1f}%)")
    print()

    # Calculate growth rate
    if len(sorted_months) >= 2:
        first_month_pnl = monthly_data[sorted_months[0]]['net_pnl']
        last_month_pnl = monthly_data[sorted_months[-1]]['net_pnl']

        print("TREND ANALYSIS")
        print("-" * 80)

        if last_month_pnl > first_month_pnl:
            print("📈 POSITIVE TREND: Performance improving over time")
        elif last_month_pnl < first_month_pnl:
            print("📉 DECLINING TREND: Performance decreasing over time")
        else:
            print("➡️  FLAT TREND: Consistent performance")
        print()

    # Trading frequency analysis
    avg_trades_per_month = total_trades / len(sorted_months)

    print("TRADING FREQUENCY")
    print("-" * 80)
    print(f"Average Trades/Month: {avg_trades_per_month:.1f}")

    if avg_trades_per_month > 10:
        print("Assessment:           High frequency - Active trader")
    elif avg_trades_per_month > 5:
        print("Assessment:           Moderate frequency - Regular trader")
    elif avg_trades_per_month > 2:
        print("Assessment:           Low frequency - Selective trader")
    else:
        print("Assessment:           Minimal frequency - Conservative trader")
    print()

    print("=" * 80)
    print("SEASONALITY ANALYSIS")
    print("=" * 80)
    print()

    # Group by calendar month (across years if applicable)
    calendar_month_data = defaultdict(lambda: {'pnl': 0, 'count': 0, 'trades': 0})

    for month in sorted_months:
        month_obj = datetime.strptime(month, '%Y-%m')
        calendar_month = month_obj.strftime('%B')

        calendar_month_data[calendar_month]['pnl'] += monthly_data[month]['net_pnl']
        calendar_month_data[calendar_month]['count'] += 1
        calendar_month_data[calendar_month]['trades'] += len(monthly_data[month]['trades'])

    print(f"{'Month':<12} {'Avg P&L':<15} {'Total Trades':<15} {'Occurrences'}")
    print("-" * 80)

    month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']

    for month_name in month_order:
        if month_name in calendar_month_data:
            data = calendar_month_data[month_name]
            avg_pnl = data['pnl'] / data['count']
            total_trades = data['trades']
            occurrences = data['count']

            print(f"{month_name:<12} ${avg_pnl:<14,.2f} {total_trades:<15} {occurrences}")

    print()

    print("=" * 80)
    print("INSIGHTS & RECOMMENDATIONS")
    print("=" * 80)
    print()

    insights = []

    # Consistency insight
    if consistency_rate >= 75:
        insights.append("✓ EXCELLENT consistency: 75%+ profitable months")
    elif consistency_rate >= 50:
        insights.append("✓ GOOD consistency: 50-74% profitable months")
    else:
        insights.append("⚠ INCONSISTENT: Less than 50% profitable months")

    # Best month insight
    best_pnl = monthly_data[best_month]['net_pnl']
    if best_pnl > total_pnl * 0.7:
        insights.append(f"⚠ CONCENTRATION: {best_month_obj.strftime('%B')} accounts for {best_pnl/total_pnl*100:.0f}% of total profits")

    # Trading frequency insight
    if avg_trades_per_month < 2:
        insights.append("✓ DISCIPLINED: Low trading frequency suggests selective approach")
    elif avg_trades_per_month > 15:
        insights.append("⚠ HIGH FREQUENCY: Consider if all trades add value")

    # Trend insight
    if len(sorted_months) >= 3:
        recent_months = sorted_months[-3:]
        recent_avg = sum(monthly_data[m]['net_pnl'] for m in recent_months) / len(recent_months)
        overall_avg = total_pnl / len(sorted_months)

        if recent_avg > overall_avg * 1.2:
            insights.append("📈 IMPROVING: Recent performance exceeds overall average")
        elif recent_avg < overall_avg * 0.8:
            insights.append("📉 DECLINING: Recent performance below overall average")

    for insight in insights:
        print(f"  {insight}")

    print()

    print("RECOMMENDATIONS")
    print("-" * 80)

    recommendations = []

    if consistency_rate < 75:
        recommendations.append("• Focus on improving consistency across all months")
        recommendations.append("• Review unsuccessful months for common patterns")

    if best_pnl > total_pnl * 0.5:
        recommendations.append("• Reduce reliance on single exceptional month")
        recommendations.append("• Develop more consistent monthly returns")

    if avg_trades_per_month > 10:
        recommendations.append("• Consider reducing trading frequency")
        recommendations.append("• Focus on higher quality setups")

    recommendations.append("• Continue tracking monthly performance for long-term trends")
    recommendations.append("• Set monthly performance targets and review regularly")

    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")

    print()
    print("=" * 80)

def main():
    filepath = '/Users/ken/Developer/private/ib-sec/trades_2025_full.csv'

    # Parse data
    sections = parse_data(filepath)

    # Analyze monthly performance
    analysis = analyze_monthly_performance(
        sections.get('trades', []),
        sections.get('cash_summary', [])
    )

    # Generate report
    generate_monthly_report(analysis)

if __name__ == '__main__':
    main()
