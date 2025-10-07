#!/usr/bin/env python3
"""
VOO (Vanguard S&P 500 ETF) Trading Analysis
Detailed analysis of all VOO trades in 2025
"""

import csv
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

def parse_trades(filepath: str) -> List[Dict]:
    """Parse trades from CSV file"""
    trades = []
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
            elif current_section == 'trades' and headers:
                row_dict = dict(zip(headers, row))
                trades.append(row_dict)

    return trades

def analyze_voo_trades(trades: List[Dict]) -> Dict[str, Any]:
    """Detailed analysis of VOO trades"""

    # Filter VOO trades only
    voo_trades = [t for t in trades if t.get('Symbol') == 'VOO']

    if not voo_trades:
        return {}

    # Sort by date and time
    voo_trades.sort(key=lambda x: x.get('DateTime', ''))

    # Categorize trades
    buys = [t for t in voo_trades if t.get('Buy/Sell') == 'BUY']
    sells = [t for t in voo_trades if t.get('Buy/Sell') == 'SELL']

    # Calculate metrics
    total_bought_qty = sum(abs(float(t.get('Quantity', 0))) for t in buys)
    total_sold_qty = sum(abs(float(t.get('Quantity', 0))) for t in sells)

    total_bought_value = sum(abs(float(t.get('TradeMoney', 0))) for t in buys)
    total_sold_value = sum(abs(float(t.get('TradeMoney', 0))) for t in sells)

    avg_buy_price = total_bought_value / total_bought_qty if total_bought_qty > 0 else 0
    avg_sell_price = total_sold_value / total_sold_qty if total_sold_qty > 0 else 0

    # Commission analysis
    total_commission = sum(abs(float(t.get('IBCommission', 0))) for t in voo_trades)
    avg_commission_per_trade = total_commission / len(voo_trades) if voo_trades else 0

    # Realized P&L analysis
    total_realized_pnl = sum(float(t.get('FifoPnlRealized', 0)) for t in voo_trades)
    winning_trades = [t for t in sells if float(t.get('FifoPnlRealized', 0)) > 0]
    losing_trades = [t for t in sells if float(t.get('FifoPnlRealized', 0)) < 0]

    win_rate = len(winning_trades) / len(sells) * 100 if sells else 0

    avg_win = sum(float(t.get('FifoPnlRealized', 0)) for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(float(t.get('FifoPnlRealized', 0)) for t in losing_trades) / len(losing_trades) if losing_trades else 0

    largest_win = max((float(t.get('FifoPnlRealized', 0)) for t in winning_trades), default=0)
    largest_loss = min((float(t.get('FifoPnlRealized', 0)) for t in losing_trades), default=0)

    # Profit factor
    total_wins = sum(float(t.get('FifoPnlRealized', 0)) for t in winning_trades)
    total_losses = abs(sum(float(t.get('FifoPnlRealized', 0)) for t in losing_trades))
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

    # Trading frequency
    if voo_trades:
        first_trade_date = datetime.strptime(voo_trades[0].get('TradeDate', '20250101'), '%Y%m%d')
        last_trade_date = datetime.strptime(voo_trades[-1].get('TradeDate', '20250101'), '%Y%m%d')
        trading_period_days = (last_trade_date - first_trade_date).days
        trades_per_day = len(voo_trades) / trading_period_days if trading_period_days > 0 else 0
    else:
        trading_period_days = 0
        trades_per_day = 0

    # Daily trading pattern
    trades_by_date = defaultdict(list)
    for trade in voo_trades:
        date = trade.get('TradeDate', '')
        trades_by_date[date].append(trade)

    # Round trip analysis
    round_trips = []
    buy_queue = []

    for trade in voo_trades:
        qty = float(trade.get('Quantity', 0))
        if qty > 0:  # Buy
            buy_queue.append(trade)
        else:  # Sell
            round_trips.append(trade)

    return {
        'total_trades': len(voo_trades),
        'buy_trades': len(buys),
        'sell_trades': len(sells),
        'total_bought_qty': total_bought_qty,
        'total_sold_qty': total_sold_qty,
        'total_bought_value': total_bought_value,
        'total_sold_value': total_sold_value,
        'avg_buy_price': avg_buy_price,
        'avg_sell_price': avg_sell_price,
        'total_commission': total_commission,
        'avg_commission_per_trade': avg_commission_per_trade,
        'total_realized_pnl': total_realized_pnl,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'profit_factor': profit_factor,
        'trading_period_days': trading_period_days,
        'trades_per_day': trades_per_day,
        'trades_by_date': dict(trades_by_date),
        'all_trades': voo_trades,
        'buy_trades_detail': buys,
        'sell_trades_detail': sells,
        'winning_trades_detail': winning_trades,
        'losing_trades_detail': losing_trades,
    }

def generate_voo_report(analysis: Dict):
    """Generate comprehensive VOO trading report"""

    if not analysis:
        print("No VOO trades found.")
        return

    print("=" * 80)
    print("VOO (VANGUARD S&P 500 ETF) TRADING ANALYSIS")
    print("=" * 80)
    print()

    print("OVERVIEW")
    print("-" * 80)
    print(f"Total Trades:              {analysis['total_trades']}")
    print(f"  Buy Trades:              {analysis['buy_trades']}")
    print(f"  Sell Trades:             {analysis['sell_trades']}")
    print(f"Trading Period:            {analysis['trading_period_days']} days")
    print(f"Trading Frequency:         {analysis['trades_per_day']:.2f} trades/day")
    print()

    print("TRADING VOLUME")
    print("-" * 80)
    print(f"Total Bought:              {analysis['total_bought_qty']:.0f} shares")
    print(f"Total Sold:                {analysis['total_sold_qty']:.0f} shares")
    print(f"Net Position Change:       {analysis['total_bought_qty'] - analysis['total_sold_qty']:.0f} shares")
    print()

    print("PRICE ANALYSIS")
    print("-" * 80)
    print(f"Average Buy Price:         ${analysis['avg_buy_price']:.2f}")
    print(f"Average Sell Price:        ${analysis['avg_sell_price']:.2f}")
    print(f"Price Difference:          ${analysis['avg_sell_price'] - analysis['avg_buy_price']:.2f} "
          f"({(analysis['avg_sell_price'] - analysis['avg_buy_price']) / analysis['avg_buy_price'] * 100:.2f}%)")
    print()

    print("TRANSACTION COSTS")
    print("-" * 80)
    print(f"Total Commissions:         ${analysis['total_commission']:.2f}")
    print(f"Avg Commission/Trade:      ${analysis['avg_commission_per_trade']:.2f}")
    print(f"Commission as % of Volume: {analysis['total_commission'] / (analysis['total_bought_value'] + analysis['total_sold_value']) * 100:.4f}%")
    print()

    print("=" * 80)
    print("PERFORMANCE METRICS")
    print("=" * 80)
    print()

    print("PROFIT & LOSS")
    print("-" * 80)
    print(f"Total Realized P&L:        ${analysis['total_realized_pnl']:.2f}")
    print(f"Net P&L (after commissions): ${analysis['total_realized_pnl'] - analysis['total_commission']:.2f}")
    print(f"Return on Investment:      {analysis['total_realized_pnl'] / analysis['total_bought_value'] * 100:.2f}%")
    print()

    print("WIN/LOSS STATISTICS")
    print("-" * 80)
    print(f"Winning Trades:            {analysis['winning_trades']} ({analysis['win_rate']:.1f}%)")
    print(f"Losing Trades:             {analysis['losing_trades']} ({100 - analysis['win_rate']:.1f}%)")
    print(f"")
    print(f"Average Win:               ${analysis['avg_win']:.2f}")
    print(f"Average Loss:              ${analysis['avg_loss']:.2f}")
    print(f"Win/Loss Ratio:            {abs(analysis['avg_win'] / analysis['avg_loss']):.2f}" if analysis['avg_loss'] != 0 else "N/A")
    print(f"")
    print(f"Largest Win:               ${analysis['largest_win']:.2f}")
    print(f"Largest Loss:              ${analysis['largest_loss']:.2f}")
    print()

    print("RISK METRICS")
    print("-" * 80)
    if analysis['profit_factor'] == float('inf'):
        print(f"Profit Factor:             ∞ (no losing trades)")
    else:
        print(f"Profit Factor:             {analysis['profit_factor']:.2f}")
    print(f"Expected Value/Trade:      ${analysis['total_realized_pnl'] / analysis['sell_trades']:.2f}" if analysis['sell_trades'] > 0 else "N/A")
    print()

    # Risk assessment
    print("RISK ASSESSMENT")
    print("-" * 80)
    if analysis['profit_factor'] > 2.0:
        risk_rating = "EXCELLENT"
        risk_color = "🟢"
    elif analysis['profit_factor'] > 1.5:
        risk_rating = "GOOD"
        risk_color = "🟢"
    elif analysis['profit_factor'] > 1.0:
        risk_rating = "ACCEPTABLE"
        risk_color = "🟡"
    else:
        risk_rating = "POOR"
        risk_color = "🔴"

    print(f"Overall Rating:            {risk_color} {risk_rating}")
    print(f"Profit Factor Rating:      {'Strong' if analysis['profit_factor'] > 1.5 else 'Needs Improvement'}")
    print(f"Win Rate Rating:           {'Strong' if analysis['win_rate'] > 60 else 'Needs Improvement'}")
    print()

    print("=" * 80)
    print("TRADE-BY-TRADE BREAKDOWN")
    print("=" * 80)
    print()

    # Group trades by date
    print("CHRONOLOGICAL TRADE HISTORY")
    print("-" * 80)
    print(f"{'Date':<12} {'Time':<10} {'Type':<6} {'Qty':>8} {'Price':>10} "
          f"{'Value':>12} {'P&L':>12} {'Commission':>10}")
    print("-" * 80)

    for trade in analysis['all_trades']:
        date = trade.get('TradeDate', '')
        time = trade.get('DateTime', '').split(';')[1] if ';' in trade.get('DateTime', '') else ''
        buy_sell = trade.get('Buy/Sell', '')
        qty = float(trade.get('Quantity', 0))
        price = float(trade.get('TradePrice', 0))
        value = float(trade.get('TradeMoney', 0))
        pnl = float(trade.get('FifoPnlRealized', 0))
        commission = float(trade.get('IBCommission', 0))

        # Format date
        if date:
            date_obj = datetime.strptime(date, '%Y%m%d')
            date_str = date_obj.strftime('%Y-%m-%d')
        else:
            date_str = 'N/A'

        print(f"{date_str:<12} {time:<10} {buy_sell:<6} {qty:>8.0f} ${price:>9.2f} "
              f"${value:>11.2f} ${pnl:>11.2f} ${abs(commission):>9.2f}")

    print()

    print("=" * 80)
    print("TRADING PATTERNS & INSIGHTS")
    print("=" * 80)
    print()

    # Daily trading activity
    print("DAILY TRADING ACTIVITY")
    print("-" * 80)
    for date, trades in sorted(analysis['trades_by_date'].items()):
        if date:
            date_obj = datetime.strptime(date, '%Y%m%d')
            date_str = date_obj.strftime('%Y-%m-%d (%a)')
        else:
            date_str = 'Unknown'

        daily_pnl = sum(float(t.get('FifoPnlRealized', 0)) for t in trades)
        daily_commission = sum(abs(float(t.get('IBCommission', 0))) for t in trades)

        print(f"{date_str:<20} {len(trades):>2} trades  "
              f"P&L: ${daily_pnl:>8.2f}  Commission: ${daily_commission:>6.2f}")

    print()

    print("=" * 80)
    print("WINNING TRADES DETAIL")
    print("=" * 80)
    print()

    if analysis['winning_trades_detail']:
        print(f"{'Date':<12} {'Qty':>8} {'Price':>10} {'P&L':>12} {'Return %':>10}")
        print("-" * 80)
        for trade in analysis['winning_trades_detail']:
            date = trade.get('TradeDate', '')
            if date:
                date_obj = datetime.strptime(date, '%Y%m%d')
                date_str = date_obj.strftime('%Y-%m-%d')
            else:
                date_str = 'N/A'

            qty = abs(float(trade.get('Quantity', 0)))
            price = float(trade.get('TradePrice', 0))
            pnl = float(trade.get('FifoPnlRealized', 0))
            cost_basis = abs(float(trade.get('CostBasis', 0)))
            return_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0

            print(f"{date_str:<12} {qty:>8.0f} ${price:>9.2f} ${pnl:>11.2f} {return_pct:>9.2f}%")
    else:
        print("No winning trades.")

    print()

    print("=" * 80)
    print("LOSING TRADES DETAIL")
    print("=" * 80)
    print()

    if analysis['losing_trades_detail']:
        print(f"{'Date':<12} {'Qty':>8} {'Price':>10} {'P&L':>12} {'Return %':>10}")
        print("-" * 80)
        for trade in analysis['losing_trades_detail']:
            date = trade.get('TradeDate', '')
            if date:
                date_obj = datetime.strptime(date, '%Y%m%d')
                date_str = date_obj.strftime('%Y-%m-%d')
            else:
                date_str = 'N/A'

            qty = abs(float(trade.get('Quantity', 0)))
            price = float(trade.get('TradePrice', 0))
            pnl = float(trade.get('FifoPnlRealized', 0))
            cost_basis = abs(float(trade.get('CostBasis', 0)))
            return_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0

            print(f"{date_str:<12} {qty:>8.0f} ${price:>9.2f} ${pnl:>11.2f} {return_pct:>9.2f}%")
    else:
        print("No losing trades.")

    print()

    print("=" * 80)
    print("KEY INSIGHTS & RECOMMENDATIONS")
    print("=" * 80)
    print()

    insights = []

    # Win rate analysis
    if analysis['win_rate'] >= 80:
        insights.append("✓ EXCELLENT win rate (80%+) - Strong trade selection")
    elif analysis['win_rate'] >= 60:
        insights.append("✓ GOOD win rate (60-79%) - Solid performance")
    elif analysis['win_rate'] >= 50:
        insights.append("⚠ AVERAGE win rate (50-59%) - Room for improvement")
    else:
        insights.append("✗ LOW win rate (<50%) - Review entry/exit criteria")

    # Profit factor analysis
    if analysis['profit_factor'] >= 2.0:
        insights.append("✓ EXCELLENT profit factor (2.0+) - Profitable strategy")
    elif analysis['profit_factor'] >= 1.5:
        insights.append("✓ GOOD profit factor (1.5-2.0) - Healthy profits")
    elif analysis['profit_factor'] > 1.0:
        insights.append("⚠ ACCEPTABLE profit factor (1.0-1.5) - Marginally profitable")
    else:
        insights.append("✗ POOR profit factor (<1.0) - Losing strategy")

    # Risk/reward analysis
    if analysis['avg_loss'] != 0:
        rr_ratio = abs(analysis['avg_win'] / analysis['avg_loss'])
        if rr_ratio >= 2.0:
            insights.append("✓ EXCELLENT risk/reward ratio (2:1+) - Good trade management")
        elif rr_ratio >= 1.5:
            insights.append("✓ GOOD risk/reward ratio (1.5:1+) - Acceptable")
        elif rr_ratio >= 1.0:
            insights.append("⚠ AVERAGE risk/reward ratio (1:1+) - Could improve")
        else:
            insights.append("✗ POOR risk/reward ratio (<1:1) - Losses too large")

    # Commission efficiency
    commission_pct = analysis['total_commission'] / (analysis['total_bought_value'] + analysis['total_sold_value']) * 100
    if commission_pct < 0.01:
        insights.append("✓ EXCELLENT commission efficiency (<0.01%) - Very low cost")
    elif commission_pct < 0.05:
        insights.append("✓ GOOD commission efficiency (0.01-0.05%) - Reasonable cost")
    else:
        insights.append("⚠ HIGH commission costs (>0.05%) - Consider reducing frequency")

    # Trading frequency
    if analysis['trades_per_day'] > 2:
        insights.append("⚠ HIGH trading frequency - May be overtrading")
    elif analysis['trades_per_day'] > 1:
        insights.append("⚠ MODERATE trading frequency - Monitor for overtrading")
    else:
        insights.append("✓ CONSERVATIVE trading frequency - Good discipline")

    for insight in insights:
        print(f"  {insight}")

    print()

    print("RECOMMENDATIONS")
    print("-" * 80)

    recommendations = []

    if analysis['win_rate'] < 60:
        recommendations.append("• Improve trade selection: Wait for stronger setups")
        recommendations.append("• Consider tighter entry criteria")

    if analysis['avg_loss'] != 0 and abs(analysis['avg_win'] / analysis['avg_loss']) < 1.5:
        recommendations.append("• Improve risk/reward: Let winners run longer")
        recommendations.append("• Cut losses earlier to reduce average loss size")

    if analysis['losing_trades'] > 0:
        recommendations.append("• Review losing trades for common patterns")
        recommendations.append("• Implement stricter stop-loss discipline")

    if analysis['trades_per_day'] > 1:
        recommendations.append("• Consider reducing trading frequency")
        recommendations.append("• Focus on quality over quantity")

    if analysis['total_realized_pnl'] > 0:
        recommendations.append("• Current strategy is profitable - stay disciplined")
        recommendations.append("• Consider scaling position size gradually")

    recommendations.append("• Track each trade in a journal for continuous improvement")
    recommendations.append("• Set clear profit targets and stop-loss levels before entry")

    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")

    print()
    print("=" * 80)

def main():
    filepath = '/Users/ken/Developer/private/ib-sec/trades_2025_full.csv'

    # Parse all trades
    all_trades = parse_trades(filepath)

    # Analyze VOO trades
    voo_analysis = analyze_voo_trades(all_trades)

    # Generate report
    generate_voo_report(voo_analysis)

if __name__ == '__main__':
    main()
