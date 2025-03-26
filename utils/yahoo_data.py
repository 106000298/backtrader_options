#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Yahoo Finance data fetching utility
"""
import os
import datetime
import pandas as pd
import yfinance as yf
import backtrader as bt

def fetch_yahoo_data(ticker, fromdate, todate, period=None, interval='1d', cache_dir='data'):
    """
    Fetch Yahoo Finance data using yfinance package
    
    Parameters:
    -----------
    ticker : str
        Ticker symbol to fetch data for
    fromdate : datetime
        Start date for data
    todate : datetime
        End date for data
    period : str, optional
        Period to download (e.g., '1y', '6mo', etc.) - if provided, fromdate and todate are ignored
    interval : str, default '1d'
        Data interval ('1d', '1wk', '1mo', etc.)
    cache_dir : str, default 'data'
        Directory to cache downloaded data
        
    Returns:
    --------
    pandas.DataFrame : DataFrame with Yahoo Finance data
    """
    # Create cache directory if it doesn't exist
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    # Construct cache file path
    cache_file = os.path.join(
        cache_dir, 
        f"{ticker}_{fromdate.strftime('%Y%m%d')}_{todate.strftime('%Y%m%d')}_{interval}.csv"
    )
    
    # Check if cached data exists and is recent (less than 1 day old)
    if os.path.exists(cache_file) and (datetime.datetime.now() - 
                                      datetime.datetime.fromtimestamp(os.path.getmtime(cache_file))).days < 1:
        print(f"Loading cached data for {ticker} from {cache_file}")
        data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
    else:
        # Fetch data using yfinance
        print(f"Downloading {ticker} data from Yahoo Finance...")
        if period:
            data = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
        else:
            data = yf.download(
                ticker, 
                start=fromdate.strftime('%Y-%m-%d'), 
                end=todate.strftime('%Y-%m-%d'), 
                interval=interval,
                auto_adjust=True
            )
        
        # Save to cache
        data.to_csv(cache_file)
    
    # Make sure the index is a datetime
    data.index = pd.to_datetime(data.index)
    
    return data 