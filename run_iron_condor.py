#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Run Iron Condor Options Strategy Backtest
"""
import datetime
import backtrader as bt
import argparse
from strategies.iron_condor_strategy import IronCondorStrategy

def parse_args():
    parser = argparse.ArgumentParser(description='Backtest an Iron Condor options trading strategy')
    
    parser.add_argument('--ticker', '-t',
                        default='SPY',
                        help='Ticker symbol to run the strategy on')
    
    parser.add_argument('--cash', '-c',
                        default=100000.0,
                        type=float,
                        help='Starting cash for the backtest')
    
    parser.add_argument('--commission', '-comm',
                        default=0.0035, # $0.35 per contract is typical for options
                        type=float,
                        help='Commission per contract')
    
    parser.add_argument('--fromdate', '-f',
                        default='2019-01-01',
                        help='Start date in YYYY-MM-DD format')
    
    parser.add_argument('--todate', '-to',
                        default='2021-12-31',
                        help='End date in YYYY-MM-DD format')
    
    parser.add_argument('--put-delta', '-pd',
                        default=0.3,
                        type=float,
                        help='Target delta for short put options (0-1.0)')
    
    parser.add_argument('--call-delta', '-cd',
                        default=0.3,
                        type=float,
                        help='Target delta for short call options (0-1.0)')
    
    parser.add_argument('--put-width', '-pw',
                        default=0.1,
                        type=float,
                        help='Width between short put and long put as % of underlying price')
    
    parser.add_argument('--call-width', '-cw',
                        default=0.1,
                        type=float,
                        help='Width between short call and long call as % of underlying price')
    
    parser.add_argument('--profit-target', '-profit',
                        default=0.5,
                        type=float,
                        help='Profit target as percentage of max profit (e.g., 0.5 for 50%)')
    
    parser.add_argument('--risk-percentage', '-risk',
                        default=0.02,
                        type=float,
                        help='Maximum risk per trade as percentage of portfolio (e.g., 0.02 for 2%)')
    
    parser.add_argument('--iv-rank-min', '-iv',
                        default=0.3,
                        type=float,
                        help='Minimum IV Rank to place a trade (0-1.0)')
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Create a cerebro entity
    cerebro = bt.Cerebro()
    
    # Add strategy with parameters from command line
    cerebro.addstrategy(
        IronCondorStrategy,
        put_delta=args.put_delta,
        call_delta=args.call_delta,
        put_width=args.put_width,
        call_width=args.call_width,
        risk_percentage=args.risk_percentage,
        profit_target_pct=args.profit_target,
        iv_rank_min=args.iv_rank_min
    )
    
    # Parse dates
    fromdate = datetime.datetime.strptime(args.fromdate, '%Y-%m-%d')
    todate = datetime.datetime.strptime(args.todate, '%Y-%m-%d')
    
    # Load data
    data = bt.feeds.YahooFinanceData(
        dataname=args.ticker,
        fromdate=fromdate,
        todate=todate,
        reverse=False)
    
    cerebro.adddata(data)
    
    # Set our desired cash start
    cerebro.broker.setcash(args.cash)
    
    # Set commission - Flat rate per contract
    cerebro.broker.setcommission(commission=args.commission)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.01)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    # Print out the starting conditions
    print('Starting Portfolio Value: ${:.2f}'.format(cerebro.broker.getvalue()))
    print(f'Backtesting Iron Condor strategy on {args.ticker} from {args.fromdate} to {args.todate}')
    print(f'Strategy parameters:')
    print(f'  - Put Delta: {args.put_delta}')
    print(f'  - Call Delta: {args.call_delta}')
    print(f'  - Put Width: {args.put_width:.1%} of underlying price')
    print(f'  - Call Width: {args.call_width:.1%} of underlying price')
    print(f'  - Profit Target: {args.profit_target:.1%} of max profit')
    print(f'  - Risk per Trade: {args.risk_percentage:.1%} of portfolio')
    print(f'  - Minimum IV Rank: {args.iv_rank_min:.1%}')
    
    # Run the strategy
    results = cerebro.run()
    strat = results[0]
    
    # Print out the final result
    print('Final Portfolio Value: ${:.2f}'.format(cerebro.broker.getvalue()))
    
    # Print analyzer results
    print('\nPerformance Metrics:')
    print('Sharpe Ratio: {:.3f}'.format(strat.analyzers.sharpe.get_analysis()['sharperatio']))
    print('Max Drawdown: {:.2%}'.format(strat.analyzers.drawdown.get_analysis()['max']['drawdown'] / 100))
    
    # Trade metrics
    trade_analysis = strat.analyzers.trades.get_analysis()
    
    if trade_analysis:
        total_trades = trade_analysis.total.closed
        winning_trades = trade_analysis.won.total if hasattr(trade_analysis, 'won') else 0
        losing_trades = trade_analysis.lost.total if hasattr(trade_analysis, 'lost') else 0
        
        if total_trades > 0:
            win_rate = winning_trades / total_trades
            print(f'Total Trades: {total_trades}')
            print(f'Win Rate: {win_rate:.2%} ({winning_trades} winning, {losing_trades} losing)')
            
            if hasattr(trade_analysis, 'won') and winning_trades > 0:
                avg_win = trade_analysis.won.pnl.average
                print(f'Average Winning Trade: ${avg_win:.2f}')
                
            if hasattr(trade_analysis, 'lost') and losing_trades > 0:
                avg_loss = trade_analysis.lost.pnl.average
                print(f'Average Losing Trade: ${avg_loss:.2f}')
                
            if hasattr(trade_analysis, 'won') and winning_trades > 0 and hasattr(trade_analysis, 'lost') and losing_trades > 0:
                profit_factor = abs(trade_analysis.won.pnl.total / trade_analysis.lost.pnl.total) if trade_analysis.lost.pnl.total != 0 else float('inf')
                print(f'Profit Factor: {profit_factor:.2f}')
    
    # Plot the result
    cerebro.plot(style='candle', barup='green', bardown='red', plotname=f'Iron Condor on {args.ticker}')

if __name__ == '__main__':
    main() 