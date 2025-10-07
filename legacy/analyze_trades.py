#!/usr/bin/env python3
"""
Interactive Brokers Trading Performance Analysis with Trade History
Analyzes 2025 trading data including individual trades
"""

import csv
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

def parse_csv_sections(filepath: str) -> Dict[str, List[Dict[str, str]]]:
    """Parse multi-section CSV file from IB Flex Query"""
    sections = {}
    current_section = None
    headers = []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

        for row in reader:
            if not row or not row[0]:
                continue

            # Detect new section by first column name
            if row[0] == 'ClientAccountID':
                headers = row
                # Identify section type from subsequent columns
                if 'Name' in headers:
                    current_section = 'account_info'
                elif 'StartingCash' in headers and 'LevelOfDetail' in headers:
                    current_section = 'cash_summary'
                elif 'Quantity' in headers and 'MarkPrice' in headers:
                    current_section = 'positions'
                elif 'TradeID' in headers:
                    current_section = 'trades'

                if current_section:
                    sections[current_section] = []
            elif current_section and headers:
                # Parse data row
                row_dict = dict(zip(headers, row))
                sections[current_section].append(row_dict)

    return sections

def analyze_trades(trades: List[Dict]) -> Dict[str, Any]:
    """Analyze individual trades"""
    if not trades:
        return {}

    trade_details = []
    symbols = defaultdict(lambda: {'buys': 0, 'sells': 0, 'qty_bought': 0, 'qty_sold': 0,
                                    'amount_bought': 0, 'amount_sold': 0, 'realized_pnl': 0,
                                    'commissions': 0})

    total_commissions = 0
    total_realized_pnl = 0

    by_date = defaultdict(list)
    by_asset_class = defaultdict(list)

    for trade in trades:
        symbol = trade.get('Symbol', '')
        trade_date = trade.get('TradeDate', '')
        quantity = float(trade.get('Quantity', 0))
        price = float(trade.get('TradePrice', 0))
        trade_money = float(trade.get('TradeMoney', 0))
        commission = float(trade.get('IBCommission', 0))
        realized_pnl = float(trade.get('FifoPnlRealized', 0))
        buy_sell = trade.get('Buy/Sell', '')
        asset_class = trade.get('AssetClass', '')

        # Aggregate by symbol
        if buy_sell == 'BUY':
            symbols[symbol]['buys'] += 1
            symbols[symbol]['qty_bought'] += abs(quantity)
            symbols[symbol]['amount_bought'] += abs(trade_money)
        else:
            symbols[symbol]['sells'] += 1
            symbols[symbol]['qty_sold'] += abs(quantity)
            symbols[symbol]['amount_sold'] += abs(trade_money)

        symbols[symbol]['realized_pnl'] += realized_pnl
        symbols[symbol]['commissions'] += abs(commission)

        total_commissions += abs(commission)
        total_realized_pnl += realized_pnl

        # Track by date and asset class
        by_date[trade_date].append(trade)
        by_asset_class[asset_class].append(trade)

        trade_details.append({
            'date': trade_date,
            'symbol': symbol,
            'asset_class': asset_class,
            'buy_sell': buy_sell,
            'quantity': quantity,
            'price': price,
            'trade_money': trade_money,
            'commission': commission,
            'realized_pnl': realized_pnl,
        })

    return {
        'trade_count': len(trades),
        'trade_details': trade_details,
        'by_symbol': dict(symbols),
        'by_date': dict(by_date),
        'by_asset_class': dict(by_asset_class),
        'total_commissions': total_commissions,
        'total_realized_pnl': total_realized_pnl,
    }

def analyze_cash_flow(cash_summary: List[Dict]) -> Dict[str, float]:
    """Analyze cash flow metrics"""
    if not cash_summary:
        return {}

    data = cash_summary[0]

    return {
        'starting_cash': float(data.get('StartingCash', 0)),
        'ending_cash': float(data.get('EndingCash', 0)),
        'deposits': float(data.get('Deposits', 0)),
        'withdrawals': float(data.get('Withdrawals', 0)),
        'internal_transfers': float(data.get('InternalTransfers', 0)),
        'commissions': float(data.get('Commissions', 0)),
        'dividends': float(data.get('Dividends', 0)),
        'broker_interest': float(data.get('BrokerInterest', 0)),
        'broker_fees': float(data.get('BrokerFees', 0)),
        'net_trades_sales': float(data.get('NetTradesSales', 0)),
        'net_trades_purchases': float(data.get('NetTradesPurchases', 0)),
        'other_fees': float(data.get('OtherFees', 0)),
        'transaction_tax': float(data.get('TransactionTax', 0)),
    }

def analyze_positions(positions: List[Dict]) -> Dict[str, Any]:
    """Analyze current positions"""
    if not positions:
        return {}

    total_value = 0
    total_cost = 0
    total_unrealized_pnl = 0
    asset_classes = defaultdict(float)

    position_details = []

    for pos in positions:
        value = float(pos.get('PositionValue', 0))
        cost = float(pos.get('CostBasisMoney', 0))
        unrealized = float(pos.get('FifoPnlUnrealized', 0))
        asset_class = pos.get('AssetClass', 'Unknown')

        total_value += value
        total_cost += cost
        total_unrealized_pnl += unrealized
        asset_classes[asset_class] += value

        position_details.append({
            'symbol': pos.get('Symbol', ''),
            'description': pos.get('Description', ''),
            'asset_class': asset_class,
            'quantity': float(pos.get('Quantity', 0)),
            'mark_price': float(pos.get('MarkPrice', 0)),
            'position_value': value,
            'cost_basis': cost,
            'unrealized_pnl': unrealized,
            'percent_of_nav': float(pos.get('PercentOfNAV', 0)),
        })

    return {
        'total_position_value': total_value,
        'total_cost_basis': total_cost,
        'total_unrealized_pnl': total_unrealized_pnl,
        'asset_allocation': dict(asset_classes),
        'positions': position_details,
    }

def calculate_performance_metrics(cash_flow: Dict, positions: Dict, trades: Dict) -> Dict[str, Any]:
    """Calculate key performance metrics"""

    # Net deposits/withdrawals
    net_deposits = cash_flow.get('deposits', 0) - abs(cash_flow.get('withdrawals', 0))
    net_internal_transfers = cash_flow.get('internal_transfers', 0)

    # Total invested capital
    total_invested = net_deposits + net_internal_transfers

    # Current total value (cash + positions)
    current_cash = cash_flow.get('ending_cash', 0)
    current_positions_value = positions.get('total_position_value', 0)
    total_value = current_cash + current_positions_value

    # Profit/Loss calculations
    unrealized_pnl = positions.get('total_unrealized_pnl', 0)
    realized_pnl = trades.get('total_realized_pnl', 0)

    # Trading activity
    gross_sales = cash_flow.get('net_trades_sales', 0)
    gross_purchases = abs(cash_flow.get('net_trades_purchases', 0))
    trading_volume = gross_sales + gross_purchases

    # Costs
    total_commissions = abs(trades.get('total_commissions', 0))
    total_fees = abs(cash_flow.get('broker_fees', 0)) + abs(cash_flow.get('other_fees', 0))
    total_costs = total_commissions + total_fees

    # Income
    dividends = cash_flow.get('dividends', 0)
    interest = cash_flow.get('broker_interest', 0)
    total_income = dividends + interest

    # Overall P&L
    total_pnl = realized_pnl + unrealized_pnl

    # Return percentage
    roi_pct = (total_pnl / total_invested * 100) if total_invested != 0 else 0

    return {
        'total_invested': total_invested,
        'current_value': total_value,
        'current_cash': current_cash,
        'current_positions_value': current_positions_value,
        'realized_pnl': realized_pnl,
        'unrealized_pnl': unrealized_pnl,
        'total_pnl': total_pnl,
        'roi_percentage': roi_pct,
        'trading_volume': trading_volume,
        'gross_sales': gross_sales,
        'gross_purchases': gross_purchases,
        'total_commissions': total_commissions,
        'total_fees': total_fees,
        'total_costs': total_costs,
        'dividends': dividends,
        'interest': interest,
        'total_income': total_income,
    }

def generate_report(sections: Dict, metrics: Dict, cash_flow: Dict, positions: Dict, trades: Dict):
    """Generate comprehensive performance report"""

    print("=" * 80)
    print("INTERACTIVE BROKERS - 2025 TRADING PERFORMANCE ANALYSIS")
    print("=" * 80)
    print()

    # Account Info
    if 'account_info' in sections and sections['account_info']:
        acc = sections['account_info'][0]
        print(f"Account ID: {acc.get('ClientAccountID', 'N/A')}")
        print(f"Account Holder: {acc.get('Name', 'N/A')}")
        print(f"Account Type: {acc.get('AccountType', 'N/A')}")
        print(f"Base Currency: {acc.get('CurrencyPrimary', 'N/A')}")

        if 'cash_summary' in sections and sections['cash_summary']:
            cs = sections['cash_summary'][0]
            print(f"Period: {cs.get('FromDate', 'N/A')} to {cs.get('ToDate', 'N/A')}")
        print()

    print("-" * 80)
    print("PORTFOLIO SUMMARY")
    print("-" * 80)
    print(f"Total Invested Capital:      ${metrics['total_invested']:,.2f}")
    print(f"Current Cash:                ${metrics['current_cash']:,.2f}")
    print(f"Current Positions Value:     ${metrics['current_positions_value']:,.2f}")
    print(f"Total Portfolio Value:       ${metrics['current_value']:,.2f}")
    print()

    print("-" * 80)
    print("PROFIT & LOSS")
    print("-" * 80)
    print(f"Realized P&L:                ${metrics['realized_pnl']:,.2f}")
    print(f"Unrealized P&L:              ${metrics['unrealized_pnl']:,.2f}")
    print(f"Total P&L:                   ${metrics['total_pnl']:,.2f}")
    print(f"Return on Investment:        {metrics['roi_percentage']:.2f}%")
    print()

    print("-" * 80)
    print("TRADING ACTIVITY")
    print("-" * 80)
    print(f"Number of Trades:            {trades.get('trade_count', 0)}")
    print(f"Gross Sales:                 ${metrics['gross_sales']:,.2f}")
    print(f"Gross Purchases:             ${metrics['gross_purchases']:,.2f}")
    print(f"Total Trading Volume:        ${metrics['trading_volume']:,.2f}")
    print()

    print("-" * 80)
    print("COSTS & INCOME")
    print("-" * 80)
    print(f"Commissions:                 -${abs(metrics['total_commissions']):,.2f}")
    print(f"Fees:                        -${abs(metrics['total_fees']):,.2f}")
    print(f"Total Costs:                 -${abs(metrics['total_costs']):,.2f}")
    print(f"Dividends:                   ${metrics['dividends']:,.2f}")
    print(f"Interest:                    ${metrics['interest']:,.2f}")
    print(f"Total Income:                ${metrics['total_income']:,.2f}")
    print()

    # Trading by Symbol
    if trades.get('by_symbol'):
        print("-" * 80)
        print("TRADING SUMMARY BY SYMBOL")
        print("-" * 80)
        print(f"{'Symbol':<10} {'Buys':>6} {'Sells':>6} {'Qty Bought':>12} {'Qty Sold':>12} "
              f"{'Realized P&L':>15} {'Commissions':>12}")
        print("-" * 80)

        for symbol, data in sorted(trades['by_symbol'].items()):
            print(f"{symbol:<10} {data['buys']:>6} {data['sells']:>6} "
                  f"{data['qty_bought']:>12,.0f} {data['qty_sold']:>12,.0f} "
                  f"${data['realized_pnl']:>14,.2f} ${data['commissions']:>11,.2f}")
        print()

    # Trade History
    if trades.get('trade_details'):
        print("-" * 80)
        print("TRADE HISTORY (Chronological)")
        print("-" * 80)
        print(f"{'Date':<10} {'Symbol':<10} {'Type':<6} {'Asset':<6} {'Qty':>10} "
              f"{'Price':>10} {'Value':>12} {'P&L':>12}")
        print("-" * 80)

        for trade in sorted(trades['trade_details'], key=lambda x: x['date']):
            print(f"{trade['date']:<10} {trade['symbol']:<10} {trade['buy_sell']:<6} "
                  f"{trade['asset_class']:<6} {trade['quantity']:>10,.0f} "
                  f"${trade['price']:>9,.2f} ${trade['trade_money']:>11,.2f} "
                  f"${trade['realized_pnl']:>11,.2f}")
        print()

    # Asset Allocation
    if positions.get('asset_allocation'):
        print("-" * 80)
        print("ASSET ALLOCATION")
        print("-" * 80)
        total_pos_value = positions['total_position_value']
        for asset_class, value in positions['asset_allocation'].items():
            pct = (value / total_pos_value * 100) if total_pos_value > 0 else 0
            print(f"{asset_class:20s} ${value:>12,.2f}  ({pct:>5.2f}%)")
        print()

    # Current Positions
    if positions.get('positions'):
        print("-" * 80)
        print("CURRENT POSITIONS")
        print("-" * 80)
        print(f"{'Symbol':<15} {'Asset':<8} {'Quantity':>12} {'Price':>10} "
              f"{'Value':>15} {'Unrealized P&L':>15}")
        print("-" * 80)
        for pos in positions['positions']:
            print(f"{pos['symbol']:<15} {pos['asset_class']:<8} {pos['quantity']:>12,.0f} "
                  f"${pos['mark_price']:>9,.2f} ${pos['position_value']:>13,.2f} "
                  f"${pos['unrealized_pnl']:>13,.2f}")
        print()

    print("=" * 80)

def main():
    filepath = '/Users/ken/Developer/private/ib-sec/trades_2025_full.csv'

    # Parse CSV
    sections = parse_csv_sections(filepath)

    # Analyze data
    cash_flow = analyze_cash_flow(sections.get('cash_summary', []))
    positions = analyze_positions(sections.get('positions', []))
    trades = analyze_trades(sections.get('trades', []))
    metrics = calculate_performance_metrics(cash_flow, positions, trades)

    # Generate report
    generate_report(sections, metrics, cash_flow, positions, trades)

if __name__ == '__main__':
    main()
