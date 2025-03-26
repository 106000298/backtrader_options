#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Options pricing utilities for backtrader options strategies
"""
import math
import numpy as np
from scipy.stats import norm

def black_scholes(S, K, T, r, sigma, option_type='call'):
    """
    Calculate option price using Black-Scholes formula
    
    Parameters:
    -----------
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration in years
    r : float
        Risk-free interest rate (annual)
    sigma : float
        Volatility of the underlying stock (annual)
    option_type : str
        'call' or 'put'
        
    Returns:
    --------
    float : Option price
    """
    # Validate inputs
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return 0.0
    
    d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    if option_type.lower() == 'call':
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:  # Put option
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return price

def calculate_greeks(S, K, T, r, sigma, option_type='call'):
    """
    Calculate option Greeks
    
    Parameters:
    -----------
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration in years
    r : float
        Risk-free interest rate (annual)
    sigma : float
        Volatility of the underlying stock (annual)
    option_type : str
        'call' or 'put'
        
    Returns:
    --------
    dict : Dictionary containing the Greeks (delta, gamma, theta, vega, rho)
    """
    # Validate inputs
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'rho': 0}
    
    sqrt_t = math.sqrt(T)
    d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    
    # Calculate common terms
    n_d1 = norm.pdf(d1)
    n_d2 = norm.pdf(d2)
    
    # Calculate delta
    if option_type.lower() == 'call':
        delta = norm.cdf(d1)
    else:  # Put option
        delta = -norm.cdf(-d1)
    
    # Calculate gamma (same for calls and puts)
    gamma = n_d1 / (S * sigma * sqrt_t)
    
    # Calculate theta
    term1 = -(S * sigma * n_d1) / (2 * sqrt_t)
    
    if option_type.lower() == 'call':
        term2 = r * K * math.exp(-r * T) * norm.cdf(d2)
        theta = term1 - term2
    else:  # Put option
        term2 = r * K * math.exp(-r * T) * norm.cdf(-d2)
        theta = term1 + term2
    
    # Adjust theta to daily from annual
    theta = theta / 365
    
    # Calculate vega (same for calls and puts)
    vega = S * sqrt_t * n_d1 / 100  # Divide by 100 to get impact of 1% change in vol
    
    # Calculate rho
    if option_type.lower() == 'call':
        rho = K * T * math.exp(-r * T) * norm.cdf(d2) / 100
    else:  # Put option
        rho = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100
    
    return {
        'delta': delta,
        'gamma': gamma,
        'theta': theta,
        'vega': vega,
        'rho': rho
    }

def calculate_iv(market_price, S, K, T, r, option_type='call', precision=0.00001, max_iterations=100):
    """
    Calculate implied volatility using the bisection method
    
    Parameters:
    -----------
    market_price : float
        Market price of the option
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration in years
    r : float
        Risk-free interest rate (annual)
    option_type : str
        'call' or 'put'
    precision : float
        Desired precision for the result
    max_iterations : int
        Maximum number of iterations
        
    Returns:
    --------
    float : Implied volatility
    """
    # Set bounds for bisection
    vol_low = 0.001
    vol_high = 5.0  # 500% volatility as upper bound
    
    # Check if the market price is between intrinsic and theoretical max
    if option_type.lower() == 'call':
        intrinsic = max(0, S - K)
        if market_price < intrinsic:
            return 0.0  # Price below intrinsic value, no valid IV
        if market_price > S:
            return vol_high  # Price above underlying, extremely high IV
    else:  # Put option
        intrinsic = max(0, K - S)
        if market_price < intrinsic:
            return 0.0  # Price below intrinsic value, no valid IV
        if market_price > K:
            return vol_high  # Price above strike, extremely high IV
    
    # Bisection method
    for i in range(max_iterations):
        vol_mid = (vol_low + vol_high) / 2
        price = black_scholes(S, K, T, r, vol_mid, option_type)
        
        if abs(price - market_price) < precision:
            return vol_mid
        
        if price < market_price:
            vol_low = vol_mid
        else:
            vol_high = vol_mid
    
    # Return the midpoint after max iterations
    return (vol_low + vol_high) / 2

def simulate_option_chain(underlying_price, days_to_expiry, volatility=0.20, risk_free_rate=0.02):
    """
    Simulate an options chain for a given underlying price
    
    Parameters:
    -----------
    underlying_price : float
        Price of the underlying asset
    days_to_expiry : int
        Days to expiration
    volatility : float
        Implied volatility (annual)
    risk_free_rate : float
        Risk-free interest rate (annual)
        
    Returns:
    --------
    dict : Dictionary containing simulated calls and puts at various strikes
    """
    # Convert days to years
    T = days_to_expiry / 365.0
    
    # Generate strike prices (approximately +/- 20% from current price)
    strike_range = np.linspace(underlying_price * 0.8, underlying_price * 1.2, 9)
    strikes = [round(strike, 2) for strike in strike_range]
    
    # Calculate option prices and greeks for each strike
    options_chain = {
        'calls': [],
        'puts': []
    }
    
    for strike in strikes:
        # Calculate call option
        call_price = black_scholes(underlying_price, strike, T, risk_free_rate, volatility, 'call')
        call_greeks = calculate_greeks(underlying_price, strike, T, risk_free_rate, volatility, 'call')
        
        # Calculate put option
        put_price = black_scholes(underlying_price, strike, T, risk_free_rate, volatility, 'put')
        put_greeks = calculate_greeks(underlying_price, strike, T, risk_free_rate, volatility, 'put')
        
        # Add to options chain
        options_chain['calls'].append({
            'strike': strike,
            'price': round(call_price, 2),
            'delta': round(call_greeks['delta'], 4),
            'gamma': round(call_greeks['gamma'], 4),
            'theta': round(call_greeks['theta'], 4),
            'vega': round(call_greeks['vega'], 2),
            'intrinsic': round(max(0, underlying_price - strike), 2)
        })
        
        options_chain['puts'].append({
            'strike': strike,
            'price': round(put_price, 2),
            'delta': round(put_greeks['delta'], 4),
            'gamma': round(put_greeks['gamma'], 4),
            'theta': round(put_greeks['theta'], 4),
            'vega': round(put_greeks['vega'], 2),
            'intrinsic': round(max(0, strike - underlying_price), 2)
        })
    
    return options_chain 