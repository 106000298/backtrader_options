#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Simple Options Trading Strategy with Backtrader
"""
import os
import datetime
import backtrader as bt
import argparse
import yfinance as yf
import pandas as pd
from strategies.put_selling_strategy import PutSellingStrategy
from utils.visualization import (
    plot_equity_curve, 
    plot_trade_analysis, 
    save_trade_log, 
    calculate_performance_metrics,
    print_performance_summary
)

class YahooPandasData(bt.feeds.PandasData):
    """
    Customized PandasData feed to work with Yahoo Finance data
    """
    params = (
        ('nocase', True),
        ('datetime', None),  # Use index for date
        ('open', 'Open'),    # Column names for data
        ('high', 'High'),
        ('low', 'Low'),
        ('close', 'Close'),
        ('volume', 'Volume'),
        ('openinterest', None),  # Not present in Yahoo data
    )

    def start(self):
        """Override start method to handle issues with dataname parameter"""
        if isinstance(self.p.dataname, tuple):
            # If dataname is somehow a tuple, convert it to the actual DataFrame
            raise ValueError(f"dataname should be a DataFrame but got: {type(self.p.dataname)}")
        super(YahooPandasData, self).start()

def parse_args():
    parser = argparse.ArgumentParser(description='Backtest an options trading strategy')
    
    parser.add_argument('--ticker', '-t',
                        default='SPY',
                        help='Ticker symbol to run the strategy on')
    
    parser.add_argument('--cash', '-c',
                        default=100000.0,
                        type=float,
                        help='Starting cash for the backtest')
    
    parser.add_argument('--commission', '-comm',
                        default=0.001,
                        type=float,
                        help='Commission rate (e.g., 0.001 for 0.1%)')
    
    parser.add_argument('--fromdate', '-f',
                        default='2020-01-01',
                        help='Start date in YYYY-MM-DD format')
    
    parser.add_argument('--todate', '-to',
                        default='2021-01-01',
                        help='End date in YYYY-MM-DD format')
    
    parser.add_argument('--ma-period', '-ma',
                        default=20,
                        type=int,
                        help='Moving average period for trend determination')
    
    parser.add_argument('--put-delta', '-delta',
                        default=0.3,
                        type=float,
                        help='Target delta for put options (0-1.0)')
    
    parser.add_argument('--days-to-expiry', '-dte',
                        default=30,
                        type=int,
                        help='Target days to expiration for options')
    
    parser.add_argument('--risk-percentage', '-risk',
                        default=0.02,
                        type=float,
                        help='Maximum risk per trade as percentage of portfolio (e.g., 0.02 for 2%)')
    
    parser.add_argument('--profit-target', '-profit',
                        default=0.5,
                        type=float,
                        help='Profit target as percentage of max profit (e.g., 0.5 for 50%)')

    parser.add_argument('--plot', '-p',
                        action='store_true',
                        help='Plot the results')
                        
    parser.add_argument('--no-plot',
                        action='store_true',
                        help='Disable all plotting')
                        
    parser.add_argument('--save-plots',
                        action='store_true',
                        help='Save plots to files instead of displaying them')
                        
    parser.add_argument('--output-dir', '-o',
                        default='results',
                        help='Directory to save results')
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Create a cerebro entity
    cerebro = bt.Cerebro()
    
    # Add strategy with parameters from command line
    cerebro.addstrategy(
        PutSellingStrategy,
        ma_period=args.ma_period,
        put_delta=args.put_delta,
        days_to_expiry=args.days_to_expiry,
        risk_percentage=args.risk_percentage,
        profit_target_pct=args.profit_target
    )
    
    # Parse dates
    fromdate = datetime.datetime.strptime(args.fromdate, '%Y-%m-%d')
    todate = datetime.datetime.strptime(args.todate, '%Y-%m-%d')
    
    # Fetch Yahoo Finance data directly
    print(f"Downloading {args.ticker} data from Yahoo Finance...")
    data_df = yf.download(
        args.ticker, 
        start=fromdate.strftime('%Y-%m-%d'), 
        end=todate.strftime('%Y-%m-%d'),
        auto_adjust=True
    )
    
    # Debug information
    print(f"DataFrame shape: {data_df.shape}")
    print(f"DataFrame columns: {data_df.columns}")
    print(f"DataFrame index: {type(data_df.index)}")
    print(f"First 5 rows:\n{data_df.head()}")
    
    # Reset column names if they are MultiIndex
    if isinstance(data_df.columns, pd.MultiIndex):
        # Create a new dataframe with flattened column names
        new_df = pd.DataFrame()
        new_df['Open'] = data_df['Open']
        new_df['High'] = data_df['High']
        new_df['Low'] = data_df['Low']
        new_df['Close'] = data_df['Close']
        new_df['Volume'] = data_df['Volume']
        data_df = new_df
        
        # Show the modified dataframe
        print("DataFrame after column renaming:")
        print(f"DataFrame columns: {data_df.columns}")
        print(f"First 5 rows:\n{data_df.head()}")
    
    # Use built-in PandasData feed
    data = bt.feeds.PandasData(
        dataname=data_df,
        datetime=None,  # Index is the date column
        open='Open',
        high='High',
        low='Low',
        close='Close',
        volume='Volume',
        openinterest=None,  # No open interest data
        fromdate=fromdate,
        todate=todate
    )
    
    cerebro.adddata(data)
    
    # Set our desired cash start
    cerebro.broker.setcash(args.cash)
    
    # Set commission
    cerebro.broker.setcommission(commission=args.commission)
    
    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    
    # Run over everything
    result = cerebro.run()
    strategy = result[0]  # Get the first strategy instance
    
    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    
    # Create output directory if it doesn't exist
    if args.save_plots:
        os.makedirs(args.output_dir, exist_ok=True)
    
    # Calculate and display performance metrics
    metrics = calculate_performance_metrics(strategy)
    print_performance_summary(metrics, f"{args.ticker} Put Selling Strategy Performance")
    
    # Generate visualizations if not disabled
    if not args.no_plot:
        # Generate the equity curve plot
        if args.save_plots:
            equity_plot_path = os.path.join(args.output_dir, f"{args.ticker}_equity_curve.png")
            plot_equity_curve(strategy, 
                             title=f"{args.ticker} Equity Curve", 
                             save_path=equity_plot_path)
            print(f"Equity curve plot saved to {equity_plot_path}")
        else:
            plot_equity_curve(strategy, title=f"{args.ticker} Equity Curve")
        
        # Generate trade analysis plot if we have trades
        if strategy.trades:
            if args.save_plots:
                trade_plot_path = os.path.join(args.output_dir, f"{args.ticker}_trade_analysis.png")
                plot_trade_analysis(strategy, 
                                   title=f"{args.ticker} Trade Analysis", 
                                   save_path=trade_plot_path)
                print(f"Trade analysis plot saved to {trade_plot_path}")
            else:
                plot_trade_analysis(strategy, title=f"{args.ticker} Trade Analysis")
        
        # Save trade log to CSV
        if strategy.trades:
            trade_log_path = os.path.join(args.output_dir, f"{args.ticker}_trade_log.csv")
            save_trade_log(strategy, trade_log_path)
    
    # Use backtrader's plotting only if explicitly requested
    if args.plot:
        try:
            cerebro.plot(style='candle', barup='green', bardown='red')
        except ImportError as e:
            print(f"Error plotting results with backtrader: {e}")
            print("Using our custom plotting instead.")

if __name__ == '__main__':
    main() 