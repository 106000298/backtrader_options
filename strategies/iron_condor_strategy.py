#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Iron Condor Options Strategy for Backtrader

This strategy implements an Iron Condor, which is a neutral options strategy
that profits from low volatility in the underlying asset.
It involves selling an out-of-the-money put and call while buying a further
out-of-the-money put and call for protection.
"""
import backtrader as bt
import math
from datetime import date, datetime, timedelta
from enum import Enum
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.options_pricing import simulate_option_chain, calculate_greeks

# Enum for option position types
class OptionPositionType(Enum):
    NONE = 0
    IRON_CONDOR = 1
    IRON_BUTTERFLY = 2
    CALENDAR_SPREAD = 3

class IronCondorStrategy(bt.Strategy):
    """
    An Iron Condor strategy that profits from a sideways market.

    The strategy:
    1. Sells an OTM put
    2. Buys a further OTM put (for protection)
    3. Sells an OTM call
    4. Buys a further OTM call (for protection)

    It aims to profit from time decay while the underlying price stays between the short strikes.
    """
    
    params = (
        ('put_delta', 0.3),       # Target delta for short put
        ('put_width', 0.1),       # Width between short put and long put (% of underlying price)
        ('call_delta', 0.3),      # Target delta for short call
        ('call_width', 0.1),      # Width between short call and long call (% of underlying price)
        ('days_to_expiry', 30),   # Target days to expiration
        ('risk_percentage', 0.02), # Max loss percentage of portfolio per trade
        ('exit_days_left', 5),    # Exit when this many days are left until expiration
        ('profit_target_pct', 0.5), # Close position at this percentage of max profit
        ('loss_stop_pct', 2.0),   # Close position if loss reaches this multiple of max profit
        ('iv_rank_min', 0.3),     # Minimum IV Rank to place a trade
        ('atr_period', 14),       # ATR period for volatility measurement
    )
    
    def __init__(self):
        """Initialize the strategy"""
        # Store historical prices for volatility calculations
        self.close_hist = []
        
        # ATR for historical volatility measurement
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        
        # Track option positions
        self.active_options = None
        self.option_type = OptionPositionType.NONE
        
        # Track current position details
        self.entry_date = None
        self.expiry_date = None
        self.short_put_strike = 0
        self.long_put_strike = 0
        self.short_call_strike = 0
        self.long_call_strike = 0
        self.max_profit = 0
        self.max_loss = 0
        self.entry_credit = 0
        
        # Risk management variables
        self.hv_20 = 0  # 20-day historical volatility
        self.iv_estimate = 0  # Current implied volatility estimate
        self.iv_rank = 0  # Current IV rank
        
    def next(self):
        """Main strategy implementation that's called for each bar"""
        # Get current date and asset price
        current_date = self.data.datetime.date()
        current_price = self.data[0]
        
        # Update historical price list for volatility calculations
        self.close_hist.append(current_price)
        if len(self.close_hist) > 252:  # Keep 1 year of data
            self.close_hist.pop(0)
        
        # Calculate historical volatility (20-day)
        if len(self.close_hist) >= 20:
            self.calculate_historical_volatility()
        
        # Estimate implied volatility based on ATR and historical volatility
        self.estimate_implied_volatility()
        
        # Log the market conditions
        self.log(f'Price: {current_price:.2f}, HV: {self.hv_20:.2%}, IV: {self.iv_estimate:.2%}, IV Rank: {self.iv_rank:.2%}, ATR: {self.atr[0]:.2f}')
        
        # Check if we have an active iron condor position
        if self.active_options:
            # Manage existing position
            self.manage_iron_condor(current_date, current_price)
        else:
            # Consider new position if conditions are favorable
            self.consider_new_iron_condor(current_date, current_price)
    
    def calculate_historical_volatility(self):
        """Calculate 20-day historical volatility"""
        if len(self.close_hist) < 20:
            return
        
        # Calculate daily returns
        returns = []
        for i in range(1, 20):
            daily_return = math.log(self.close_hist[-i] / self.close_hist[-(i+1)])
            returns.append(daily_return)
        
        # Calculate standard deviation of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        daily_vol = math.sqrt(variance)
        
        # Annualize volatility
        self.hv_20 = daily_vol * math.sqrt(252)
    
    def estimate_implied_volatility(self):
        """Estimate implied volatility based on ATR and historical volatility"""
        if len(self.close_hist) < 20:
            return
        
        # Use ATR as a percentage of price as a volatility proxy
        atr_vol = self.atr[0] / self.data[0]
        
        # Blend ATR-based volatility with historical volatility
        self.iv_estimate = (atr_vol * math.sqrt(252) * 0.5) + (self.hv_20 * 0.5)
        
        # Calculate IV rank based on historical data
        if len(self.close_hist) >= 252:  # Need a full year for IV rank
            hist_vol_min = 0.1  # Assumed minimum for demonstration
            hist_vol_max = 0.5  # Assumed maximum for demonstration
            
            # In a real implementation, these would be calculated from historical data
            # self.iv_rank = (self.iv_estimate - hist_vol_min) / (hist_vol_max - hist_vol_min)
            
            # For demo, set IV rank based on current ATR relative to average
            avg_atr = sum(self.atr.array[-20:]) / 20
            self.iv_rank = min(1.0, max(0.0, self.atr[0] / (2 * avg_atr)))
    
    def manage_iron_condor(self, current_date, current_price):
        """Manage existing iron condor position"""
        # Calculate days left to expiration
        days_left = (self.expiry_date - current_date).days
        
        # Simulate current option prices using Black-Scholes
        # For a real implementation, we'd use actual market data
        days_to_expiry = max(1, days_left)  # Ensure at least 1 day for calculations
        risk_free_rate = 0.02  # 2% annual rate
        
        # Get simulated options chain
        options_chain = simulate_option_chain(
            current_price, 
            days_to_expiry, 
            self.iv_estimate, 
            risk_free_rate
        )
        
        # Find the closest option strikes in the chain
        short_put_option = self.find_closest_option(options_chain['puts'], 'strike', self.short_put_strike)
        long_put_option = self.find_closest_option(options_chain['puts'], 'strike', self.long_put_strike)
        short_call_option = self.find_closest_option(options_chain['calls'], 'strike', self.short_call_strike)
        long_call_option = self.find_closest_option(options_chain['calls'], 'strike', self.long_call_strike)
        
        # Calculate current position value
        current_value = (
            -short_put_option['price']    # Short put (we sold it, so negative)
            +long_put_option['price']     # Long put (we bought it, so positive)
            -short_call_option['price']   # Short call (we sold it, so negative)
            +long_call_option['price']    # Long call (we bought it, so positive)
        )
        
        # Calculate current profit
        # Initial credit minus current value of position
        current_profit = self.entry_credit - current_value
        profit_pct = current_profit / self.max_profit if self.max_profit > 0 else 0
        
        # Log current position status
        self.log(f'Iron Condor - Days Left: {days_left}, Profit: {current_profit:.2f} ({profit_pct:.2%} of max)')
        
        # Determine if we should exit the position
        should_exit = False
        exit_reason = ""
        
        # Exit if approaching expiration
        if days_left <= self.params.exit_days_left:
            should_exit = True
            exit_reason = f"approaching expiration ({days_left} days left)"
        
        # Exit if profit target reached
        elif profit_pct >= self.params.profit_target_pct:
            should_exit = True
            exit_reason = f"profit target reached ({profit_pct:.2%})"
        
        # Exit if loss exceeds stop threshold
        elif current_profit < 0 and abs(current_profit) > (self.max_profit * self.params.loss_stop_pct):
            should_exit = True
            exit_reason = f"stop loss triggered (loss: {current_profit:.2f})"
        
        # Exit the position if any conditions met
        if should_exit:
            self.log(f"Closing Iron Condor - Reason: {exit_reason}")
            self.close_iron_condor()
    
    def close_iron_condor(self):
        """Close the iron condor position"""
        # In a real implementation, we'd place the orders to close the position
        # For this simulation, we just reset the position tracking variables
        self.active_options = None
        self.option_type = OptionPositionType.NONE
        
        self.entry_date = None
        self.expiry_date = None
        self.short_put_strike = 0
        self.long_put_strike = 0
        self.short_call_strike = 0
        self.long_call_strike = 0
        self.max_profit = 0
        self.max_loss = 0
        self.entry_credit = 0
    
    def consider_new_iron_condor(self, current_date, current_price):
        """Consider opening a new iron condor position if conditions are favorable"""
        # Check if IV rank is high enough for iron condor
        if self.iv_rank < self.params.iv_rank_min:
            return
        
        # Calculate days to expiration date (usually 3rd Friday of month)
        expiry_date = self.get_next_monthly_expiration(current_date)
        days_to_expiry = (expiry_date - current_date).days
        
        # If expiry is too close, use the next month
        if days_to_expiry < self.params.days_to_expiry:
            expiry_date = self.get_next_monthly_expiration(
                current_date + timedelta(days=35)  # Look ahead to next month
            )
            days_to_expiry = (expiry_date - current_date).days
        
        # Get simulated options chain using Black-Scholes
        options_chain = simulate_option_chain(
            current_price, 
            days_to_expiry, 
            self.iv_estimate, 
            0.02  # 2% risk-free rate
        )
        
        # Find appropriate put strikes based on delta
        short_put = None
        for put in options_chain['puts']:
            if abs(put['delta']) <= self.params.put_delta:
                short_put = put
                break
        
        if not short_put:
            return  # No suitable short put found
        
        # Calculate long put strike based on width
        long_put_strike = short_put['strike'] * (1 - self.params.put_width)
        long_put = self.find_closest_option(options_chain['puts'], 'strike', long_put_strike)
        
        # Find appropriate call strikes based on delta
        short_call = None
        for call in options_chain['calls']:
            if abs(call['delta']) <= self.params.call_delta:
                short_call = call
                break
        
        if not short_call:
            return  # No suitable short call found
        
        # Calculate long call strike based on width
        long_call_strike = short_call['strike'] * (1 + self.params.call_width)
        long_call = self.find_closest_option(options_chain['calls'], 'strike', long_call_strike)
        
        # Calculate credit received
        credit = (short_put['price'] - long_put['price'] + 
                 short_call['price'] - long_call['price'])
        
        # Calculate max risk (width between strikes minus credit)
        put_spread_width = short_put['strike'] - long_put['strike']
        call_spread_width = long_call['strike'] - short_call['strike']
        max_risk = max(put_spread_width, call_spread_width) - credit
        
        # Calculate max return (credit received)
        max_return = credit
        
        # Calculate required capital (margin requirement)
        margin_requirement = max(put_spread_width, call_spread_width)
        
        # Calculate return on risk
        return_on_risk = max_return / margin_requirement if margin_requirement > 0 else 0
        
        # Check if return on risk is acceptable
        if return_on_risk < 0.15:  # Minimum 15% return on risk
            return
        
        # Calculate position sizing based on risk management
        portfolio_value = self.broker.getvalue()
        max_risk_dollars = portfolio_value * self.params.risk_percentage
        
        # Calculate number of spreads based on risk
        num_spreads = math.floor(max_risk_dollars / (max_risk * 100))  # 100 shares per contract
        num_spreads = max(1, num_spreads)  # At least 1 spread
        
        # Log the position details
        self.log(f"Opening Iron Condor: Short Put @ {short_put['strike']:.2f}, "
                f"Long Put @ {long_put['strike']:.2f}, "
                f"Short Call @ {short_call['strike']:.2f}, "
                f"Long Call @ {long_call['strike']:.2f}")
        self.log(f"Credit: {credit:.2f}, Max Risk: {max_risk:.2f}, "
                f"Return on Risk: {return_on_risk:.2%}, "
                f"Contracts: {num_spreads}")
        
        # Set position tracking variables
        self.active_options = True
        self.option_type = OptionPositionType.IRON_CONDOR
        self.entry_date = current_date
        self.expiry_date = expiry_date
        self.short_put_strike = short_put['strike']
        self.long_put_strike = long_put['strike']
        self.short_call_strike = short_call['strike']
        self.long_call_strike = long_call['strike']
        self.max_profit = credit * num_spreads * 100  # 100 shares per contract
        self.max_loss = max_risk * num_spreads * 100
        self.entry_credit = credit
    
    def get_next_monthly_expiration(self, current_date):
        """
        Calculate the next monthly options expiration date (3rd Friday of month)
        """
        # Start with the first day of next month
        if current_date.month == 12:
            year = current_date.year + 1
            month = 1
        else:
            year = current_date.year
            month = current_date.month + 1
        
        # Get the first day of the month
        first_day = date(year, month, 1)
        
        # Find the first Friday of the month
        days_to_add = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_to_add)
        
        # Get the third Friday (add 14 days to first Friday)
        third_friday = first_friday + timedelta(days=14)
        
        return third_friday
    
    def find_closest_option(self, options_list, key, target_value):
        """Find the option with the closest value for the given key"""
        if not options_list:
            return None
        
        closest_option = options_list[0]
        closest_diff = abs(closest_option[key] - target_value)
        
        for option in options_list:
            diff = abs(option[key] - target_value)
            if diff < closest_diff:
                closest_diff = diff
                closest_option = option
        
        return closest_option
    
    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}') 