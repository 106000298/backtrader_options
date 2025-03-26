#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Visualization utilities for backtesting results
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

def plot_equity_curve(strategy, title=None, save_path=None):
    """
    Plot equity curve and underlying price
    
    Parameters:
    -----------
    strategy : backtrader.Strategy instance
        The strategy instance containing results
    title : str, optional
        Title for the plot
    save_path : str, optional
        Path to save the figure, if None, it will be displayed
    """
    fig, axes = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]})
    fig.suptitle(title or 'Backtest Results', fontsize=16)
    
    # Convert dates to matplotlib format if they're datetime objects
    dates = [pd.to_datetime(d) if not isinstance(d, datetime) else d for d in strategy.dates]
    
    # Plot equity curve
    axes[0].plot(dates, strategy.equity_curve, 'b-', linewidth=2, label='Portfolio Value')
    
    # Format x-axis
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    axes[0].xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45)
    
    # Plot underlying price
    price_data = strategy.data.close.array
    # We need to adjust the length since strategy.dates might be longer by 1
    price_len = min(len(price_data), len(dates))
    axes[0].plot(dates[:price_len], price_data[:price_len], 'g-', alpha=0.5, label='Asset Price')
    
    # Add trade markers
    for trade in strategy.trades:
        entry_date = pd.to_datetime(trade['entry_date'])
        exit_date = pd.to_datetime(trade['exit_date'])
        
        # Find index of dates closest to trade dates
        # Convert dates to epoch time for comparison
        dates_epoch = np.array([pd.Timestamp(d).timestamp() for d in dates])
        entry_epoch = entry_date.timestamp()
        exit_epoch = exit_date.timestamp()
        
        entry_idx = np.abs(dates_epoch - entry_epoch).argmin()
        exit_idx = np.abs(dates_epoch - exit_epoch).argmin()
        
        # Mark entry and exit points
        if entry_idx < len(strategy.equity_curve):
            axes[0].plot(dates[entry_idx], strategy.equity_curve[entry_idx], 'go', markersize=6)
        
        if exit_idx < len(strategy.equity_curve):
            if trade['profit'] > 0:
                marker_color = 'g^'  # green triangle up for profit
            else:
                marker_color = 'rv'  # red triangle down for loss
            axes[0].plot(dates[exit_idx], strategy.equity_curve[exit_idx], marker_color, markersize=8)
    
    # Add legend and labels
    axes[0].set_ylabel('Portfolio Value ($)')
    axes[0].legend(loc='best')
    axes[0].grid(True)
    
    # Calculate drawdown
    equity_curve = np.array(strategy.equity_curve)
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = 100 * ((running_max - equity_curve) / running_max)
    
    # Plot drawdown
    axes[1].fill_between(dates, 0, drawdown, color='r', alpha=0.3)
    axes[1].set_ylabel('Drawdown (%)')
    axes[1].set_xlabel('Date')
    axes[1].grid(True)
    
    # Add drawdown percentage on right y-axis
    axes[1].set_ylim(0, max(drawdown) * 1.1 if max(drawdown) > 0 else 1)  # Add 10% margin
    
    # Adjust layout and save or display
    plt.tight_layout()
    plt.subplots_adjust(top=0.93)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()
    
def plot_trade_analysis(strategy, title=None, save_path=None):
    """
    Plot trade analysis charts
    
    Parameters:
    -----------
    strategy : backtrader.Strategy instance
        The strategy instance containing trade results
    title : str, optional
        Title for the plot
    save_path : str, optional
        Path to save the figure, if None, it will be displayed
    """
    if not strategy.trades:
        print("No trades to analyze")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(title or 'Trade Analysis', fontsize=16)
    
    # Convert trade data to DataFrame for easier analysis
    trades_df = pd.DataFrame(strategy.trades)
    
    # 1. Plot profit distribution
    axes[0, 0].hist(trades_df['total_profit'], bins=20, alpha=0.7, color='blue')
    axes[0, 0].axvline(0, color='r', linestyle='--')
    axes[0, 0].set_xlabel('Profit/Loss ($)')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Profit Distribution')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. Plot cumulative P&L
    cumulative_pnl = trades_df['total_profit'].cumsum()
    axes[0, 1].plot(cumulative_pnl.index, cumulative_pnl.values, 'b-', linewidth=2)
    axes[0, 1].set_xlabel('Trade Number')
    axes[0, 1].set_ylabel('Cumulative P&L ($)')
    axes[0, 1].set_title('Cumulative Profit/Loss')
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Plot holding period vs profit
    axes[1, 0].scatter(trades_df['days_held'], trades_df['profit_pct'], 
                      alpha=0.7, c=trades_df['profit'] > 0, cmap='RdYlGn')
    axes[1, 0].axhline(0, color='r', linestyle='--')
    axes[1, 0].set_xlabel('Holding Period (days)')
    axes[1, 0].set_ylabel('Profit (%)')
    axes[1, 0].set_title('Holding Period vs. Profit %')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. Plot win/loss pie chart
    win_count = sum(1 for p in trades_df['profit'] if p > 0)
    loss_count = len(trades_df) - win_count
    axes[1, 1].pie([win_count, loss_count], labels=['Wins', 'Losses'], 
                  autopct='%1.1f%%', colors=['green', 'red'], startangle=90)
    axes[1, 1].axis('equal')
    axes[1, 1].set_title('Win/Loss Ratio')
    
    # Add text with summary statistics
    win_rate = win_count / len(trades_df) * 100
    avg_profit = trades_df['profit'].mean()
    avg_profit_pct = trades_df['profit_pct'].mean()
    max_profit = trades_df['profit'].max()
    max_loss = trades_df['profit'].min()
    
    stat_text = (
        f"Win Rate: {win_rate:.1f}%\n"
        f"Avg Profit: ${avg_profit:.2f} ({avg_profit_pct:.1f}%)\n"
        f"Max Profit: ${max_profit:.2f}\n"
        f"Max Loss: ${max_loss:.2f}\n"
        f"Total Trades: {len(trades_df)}"
    )
    
    plt.figtext(0.5, 0.01, stat_text, ha='center', fontsize=12, 
                bbox=dict(facecolor='lightgray', alpha=0.5))
    
    # Adjust layout and save or display
    plt.tight_layout()
    plt.subplots_adjust(top=0.9, bottom=0.1)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()

def save_trade_log(strategy, filepath):
    """
    Save trade log to CSV file
    
    Parameters:
    -----------
    strategy : backtrader.Strategy instance
        The strategy instance containing trade results
    filepath : str
        Path to save the CSV file
    """
    if not strategy.trades:
        print("No trades to save")
        return
    
    # Convert trade data to DataFrame
    trades_df = pd.DataFrame(strategy.trades)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Save to CSV
    trades_df.to_csv(filepath, index=False)
    print(f"Trade log saved to {filepath}")
    
def calculate_performance_metrics(strategy):
    """
    Calculate performance metrics from backtest results
    
    Parameters:
    -----------
    strategy : backtrader.Strategy instance
        The strategy instance containing results
        
    Returns:
    --------
    dict : Dictionary containing performance metrics
    """
    if not strategy.equity_curve or len(strategy.equity_curve) < 2:
        return {"error": "Insufficient data to calculate metrics"}
    
    # Convert to numpy arrays for calculations
    equity = np.array(strategy.equity_curve)
    returns = np.array(strategy.returns)
    
    # Calculate metrics
    initial_capital = equity[0]
    final_capital = equity[-1]
    
    # Return metrics
    total_return = (final_capital / initial_capital - 1) * 100
    
    # Annualized return (assuming 252 trading days per year)
    trading_days = len(equity) - 1
    if trading_days > 0:
        ann_return = ((final_capital / initial_capital) ** (252 / trading_days) - 1) * 100
    else:
        ann_return = 0
    
    # Volatility and Sharpe ratio
    daily_std = np.std(returns[1:]) * 100  # Skip first return which is 0
    annual_std = daily_std * np.sqrt(252)
    
    # Sharpe ratio (assuming risk-free rate of 0%)
    if annual_std > 0:
        sharpe_ratio = ann_return / annual_std
    else:
        sharpe_ratio = 0
    
    # Drawdowns
    running_max = np.maximum.accumulate(equity)
    drawdowns = (running_max - equity) / running_max * 100
    max_drawdown = np.max(drawdowns)
    
    # Return dictionary of metrics
    return {
        "initial_capital": initial_capital,
        "final_capital": final_capital,
        "total_return_pct": total_return,
        "annualized_return_pct": ann_return,
        "annualized_volatility_pct": annual_std,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown_pct": max_drawdown,
        "trading_days": trading_days,
        "win_rate": strategy.winning_trades / max(1, strategy.trade_count) * 100,
        "total_trades": strategy.trade_count,
        "winning_trades": strategy.winning_trades,
        "losing_trades": strategy.losing_trades,
    }

def print_performance_summary(metrics, title=None):
    """
    Print a formatted performance summary
    
    Parameters:
    -----------
    metrics : dict
        Dictionary containing performance metrics
    title : str, optional
        Title for the summary
    """
    print("\n" + "="*50)
    print(title or "PERFORMANCE SUMMARY")
    print("="*50)
    
    print(f"Initial Capital: ${metrics['initial_capital']:.2f}")
    print(f"Final Capital: ${metrics['final_capital']:.2f}")
    print(f"Absolute Return: ${metrics['final_capital'] - metrics['initial_capital']:.2f} ({metrics['total_return_pct']:.2f}%)")
    print(f"Annualized Return: {metrics['annualized_return_pct']:.2f}%")
    print(f"Annualized Volatility: {metrics['annualized_volatility_pct']:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Maximum Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"Trading Days: {metrics['trading_days']}")
    print(f"Total Trades: {metrics['total_trades']}")
    
    if metrics['total_trades'] > 0:
        print(f"Win Rate: {metrics['win_rate']:.2f}%")
        print(f"Win/Loss: {metrics['winning_trades']}/{metrics['losing_trades']}")
    
    print("="*50) 