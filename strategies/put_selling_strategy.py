#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Put Selling Strategy for Backtrader

This strategy sells cash-secured puts when the underlying asset
is in an uptrend, defined by the price being above a moving average.
The strategy adjusts the strike price based on market conditions.
"""
import backtrader as bt
import math
from datetime import date, datetime, timedelta
from enum import Enum

# Enum for option position types
class OptionPositionType(Enum):
    NONE = 0
    SHORT_PUT = 1
    LONG_PUT = 2
    SHORT_CALL = 3
    LONG_CALL = 4

class PutSellingStrategy(bt.Strategy):
    """
    A strategy that sells out-of-the-money put options when the market is in an uptrend,
    defined by the price being above a moving average.
    """
    
    params = (
        ('ma_period', 20),  # Moving average period
        ('put_delta', 0.3),  # Target delta for puts we sell
        ('days_to_expiry', 30),  # Target days to expiration
        ('risk_percentage', 0.02),  # Max loss percentage of portfolio per trade
        ('profit_target_pct', 0.50),  # Close position at 50% of max profit
    )
    
    def __init__(self):
        """Initialize the strategy"""
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data, period=self.params.ma_period
        )
        
        # Track our options positions
        self.active_option = None
        self.option_type = OptionPositionType.NONE
        self.entry_price = 0
        self.strike_price = 0
        self.expiry_date = None
        self.entry_date = None
        self.num_contracts = 0
        
        # Performance tracking
        self.trades = []
        self.total_premium = 0
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Track equity and drawdown
        self.equity_curve = []
        self.returns = []
        self.dates = []
        
    def start(self):
        # Initialize performance tracking
        self.equity_curve = [self.broker.getvalue()]
        self.returns = [0.0]  
        self.dates = [self.data.datetime.date(0)]
        
    def next(self):
        """Main strategy implementation that's called for each bar"""
        # Get current date and asset price
        current_date = self.data.datetime.date()
        current_price = self.data[0]
        
        # Track equity and dates for plotting
        self.equity_curve.append(self.broker.getvalue())
        if len(self.equity_curve) > 1:
            daily_return = (self.equity_curve[-1] / self.equity_curve[-2]) - 1
            self.returns.append(daily_return)
        
        self.dates.append(current_date)
        
        # Log values for debugging
        self.log(f'Date: {current_date}, Asset Price: {current_price:.2f}, MA: {self.sma[0]:.2f}')
        
        # Check if we already have an active options position
        if self.active_option is not None:
            # If we have an active position, check if we should close it
            self.manage_active_position(current_date, current_price)
        else:
            # If no active position, check if we should open a new one
            self.consider_new_position(current_price)
    
    def manage_active_position(self, current_date, current_price):
        """Manage existing option position"""
        if self.option_type == OptionPositionType.SHORT_PUT:
            # For short put, estimate current option value
            days_left = (self.expiry_date - current_date).days
            
            if days_left <= 0:
                # Option expired
                if current_price > self.strike_price:
                    # Put expired worthless - max profit
                    self.log(f'Put option expired worthless. Strike: {self.strike_price:.2f}')
                    
                    # Add premium to broker cash (options expired worthless)
                    profit = self.entry_price * self.num_contracts * 100  # 100 multiplier for contract size
                    self.broker.add_cash(profit)
                    self.log(f'Added ${profit:.2f} to cash (premium profit)')
                    
                    # Record trade
                    trade_profit = self.entry_price
                    self.record_trade(current_date, trade_profit, 1.0, days_held=self.params.days_to_expiry)
                else:
                    # Put assigned - we buy stock at strike
                    loss = self.strike_price - current_price
                    self.log(f'Put assigned. Strike: {self.strike_price:.2f}, Loss: {loss:.2f}')
                    
                    # Calculate P&L and add to broker cash
                    net_profit = (self.entry_price - loss) * self.num_contracts * 100
                    self.broker.add_cash(net_profit)
                    self.log(f'Added ${net_profit:.2f} to cash (assignment with loss)')
                    
                    # Record trade
                    trade_profit = self.entry_price - loss
                    profit_pct = trade_profit / self.entry_price
                    self.record_trade(current_date, trade_profit, profit_pct, days_held=self.params.days_to_expiry)
                
                # Reset position tracking
                self.active_option = None
                self.option_type = OptionPositionType.NONE
            else:
                # Option still active, estimate current value
                # This is a simplified model - in real implementation we'd use an
                # options pricing model like Black-Scholes
                
                # Intrinsic value
                intrinsic = max(0, self.strike_price - current_price)
                
                # Time value (simplified)
                time_factor = days_left / self.params.days_to_expiry
                vol_factor = 0.8  # Simplified volatility factor
                time_value = vol_factor * time_factor * (current_price * 0.05)
                
                # Estimated current option value
                current_option_value = intrinsic + time_value
                
                # Calculate profit
                profit = self.entry_price - current_option_value
                profit_pct = profit / self.entry_price
                
                # Check if we've hit profit target
                if profit_pct >= self.params.profit_target_pct:
                    self.log(f'Closing put at profit target: {profit_pct*100:.2f}%')
                    
                    # Add profit to broker cash (closing position early)
                    net_profit = profit * self.num_contracts * 100  # 100 multiplier for contract size
                    self.broker.add_cash(net_profit)
                    self.log(f'Added ${net_profit:.2f} to cash (early close)')
                    
                    # Record the trade
                    days_held = (current_date - self.entry_date).days
                    self.record_trade(current_date, profit, profit_pct, days_held)
                    
                    # In real implementation, we'd buy back the put here
                    self.active_option = None
                    self.option_type = OptionPositionType.NONE
    
    def record_trade(self, exit_date, profit, profit_pct, days_held):
        """Record trade details for performance analysis"""
        trade_info = {
            'entry_date': self.entry_date,
            'exit_date': exit_date,
            'days_held': days_held,
            'strike': self.strike_price,
            'premium': self.entry_price,
            'profit': profit,
            'profit_pct': profit_pct * 100,  # Convert to percentage
            'contracts': self.num_contracts,
            'total_profit': profit * self.num_contracts * 100  # 100 shares per contract
        }
        
        self.trades.append(trade_info)
        self.trade_count += 1
        
        if profit > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
    
    def consider_new_position(self, current_price):
        """Consider opening a new options position"""
        # Only sell puts when price is above moving average (uptrend)
        if current_price > self.sma[0]:
            # Calculate position size based on risk management
            cash = self.broker.getcash()
            portfolio_value = self.broker.getvalue()
            
            # Calculate strike price (simplified)
            # In a real implementation, we'd calculate proper strike price based on
            # option chain data and delta target
            strike_price = current_price * (1 - self.params.put_delta)
            
            # Calculate the premium (simplified)
            # In a real implementation, this would come from option chain data
            implied_vol = 0.2  # Simplified IV assumption
            time_factor = 1.0  # Normalized time to expiry
            option_premium = current_price * implied_vol * time_factor * self.params.put_delta
            
            # Risk per trade
            max_risk = portfolio_value * self.params.risk_percentage
            
            # Position sizing based on max risk
            max_loss_per_contract = (strike_price - option_premium) * 100  # 100 shares per contract
            num_contracts = max(1, math.floor(max_risk / max_loss_per_contract))
            
            # Create expiry date (30 days from now)
            today = self.data.datetime.date()
            expiry_date = today + timedelta(days=self.params.days_to_expiry)
            
            # Log the trade
            self.log(f'SELL {num_contracts} PUT(s) @ {strike_price:.2f}, Premium: {option_premium:.2f}')
            
            # Reserve cash for the potential assignment (margin requirement)
            margin_requirement = strike_price * num_contracts * 100
            if margin_requirement <= cash:
                # Only proceed if we have enough cash for margin requirements
                
                # Update broker cash
                collected_premium = option_premium * num_contracts * 100  # 100 shares per contract
                # We don't add cash here since we'll add it when the position is closed
                
                # Track total premium collected
                self.total_premium += option_premium * num_contracts
                
                # Update position tracking
                self.active_option = True
                self.option_type = OptionPositionType.SHORT_PUT
                self.entry_price = option_premium
                self.strike_price = strike_price
                self.expiry_date = expiry_date
                self.entry_date = today
                self.num_contracts = num_contracts
            else:
                self.log(f'Insufficient cash for margin requirement: ${margin_requirement:.2f}')
    
    def stop(self):
        """Called when the strategy is stopped/completed"""
        # Print performance summary
        self.log('==== Strategy Performance Summary ====')
        self.log(f'Total Trades: {self.trade_count}')
        
        if self.trade_count > 0:
            win_rate = (self.winning_trades / self.trade_count) * 100
            self.log(f'Winning Trades: {self.winning_trades} ({win_rate:.2f}%)')
            self.log(f'Losing Trades: {self.losing_trades}')
            
            # Calculate average metrics
            if self.trades:
                avg_profit = sum(trade['profit'] for trade in self.trades) / len(self.trades)
                avg_profit_pct = sum(trade['profit_pct'] for trade in self.trades) / len(self.trades)
                avg_days_held = sum(trade['days_held'] for trade in self.trades) / len(self.trades)
                total_trade_profit = sum(trade['total_profit'] for trade in self.trades)
                
                self.log(f'Average Profit: ${avg_profit:.2f}')
                self.log(f'Average Profit %: {avg_profit_pct:.2f}%')
                self.log(f'Average Days Held: {avg_days_held:.2f}')
                self.log(f'Total P&L from Trades: ${total_trade_profit:.2f}')
        
        self.log(f'Total Premium Collected: ${self.total_premium * 100:.2f}')
        self.log('======================================')
    
    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}') 