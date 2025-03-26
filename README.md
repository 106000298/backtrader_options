# Backtrader Options Trading Framework

A framework for backtesting options trading strategies using Backtrader.

## Strategies

This framework includes the following options trading strategies:

1. **Put Selling Strategy**: Sells cash-secured puts when the underlying is in an uptrend (price above moving average), collecting premium and managing risk with early closure at a profit target.

2. **Iron Condor Strategy**: Creates a range-bound strategy by selling a put spread and a call spread, profiting from time decay when the underlying stays within a specified range.

3. **Covered Call Strategy**: Holds the underlying stock while selling call options against that position to generate additional income.

## Installation

1. Clone this repository
2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

## Data Sources

The framework uses Yahoo Finance data through the `yfinance` package, offering:
- Real market data for backtesting
- Automatic adjustments for splits and dividends
- Built-in date range filtering

## Usage

### Put Selling Strategy

```bash
python main.py --ticker SPY --fromdate 2022-01-01 --todate 2022-06-01 --ma-period 20 --put-delta 0.3 --days-to-expiry 30 --risk-percentage 0.02 --profit-target 0.5
```

### Iron Condor Strategy

```bash
python iron_condor.py --ticker SPY --fromdate 2022-01-01 --todate 2022-06-01 --call-delta 0.3 --put-delta 0.3 --days-to-expiry 45 --risk-percentage 0.02 --profit-target 0.5
```

### Covered Call Strategy

```bash
python covered_call.py --ticker AAPL --fromdate 2022-01-01 --todate 2022-06-01 --call-delta 0.3 --days-to-expiry 30 --profit-target 0.5
```

## Strategy Parameters

| Parameter | Description |
|-----------|-------------|
| `--ticker` | The ticker symbol to trade (e.g., SPY, AAPL) |
| `--fromdate` | Start date for the backtest (YYYY-MM-DD) |
| `--todate` | End date for the backtest (YYYY-MM-DD) |
| `--ma-period` | Moving average period for trend determination |
| `--put-delta` | Target delta for put options (0-1.0) |
| `--call-delta` | Target delta for call options (0-1.0) |
| `--days-to-expiry` | Target days to expiration for options |
| `--risk-percentage` | Maximum risk per trade as percentage of portfolio |
| `--profit-target` | Profit target as percentage of max profit |

## Visualization

The framework includes a comprehensive visualization system that provides:

1. **Equity Curve**: Plots portfolio value over time with trade markers showing entries and exits, along with underlying price and drawdown chart.

2. **Trade Analysis**: Detailed visuals including:
   - Profit distribution histogram
   - Cumulative P&L chart 
   - Holding period vs. profit scatter plot
   - Win/loss ratio pie chart

3. **Performance Metrics**: Automatically calculates key metrics:
   - Absolute and percentage returns
   - Annualized returns and volatility
   - Sharpe ratio
   - Maximum drawdown
   - Win rate and trade statistics

4. **Output Options**:
   - `--save-plots`: Save plots to files instead of displaying them
   - `--no-plot`: Disable visualization
   - `--output-dir`: Specify directory for saved files

Example:
```bash
python main.py --ticker SPY --fromdate 2022-01-01 --todate 2022-06-01 --save-plots --output-dir my_results
```

## Performance Tracking

The framework keeps detailed logs of all trades, including:
- Entry and exit dates
- Option strike prices and premium
- Profit/loss per trade
- Performance statistics

A comprehensive performance summary is displayed at the end of each backtest, showing:
- Total return (absolute and percentage)
- Trading statistics (win rate, average profit, etc.)
- Annualized metrics (return, volatility, Sharpe ratio)

## Advanced Features

- **Black-Scholes Option Pricing**: Uses mathematical models to estimate option prices
- **Implied Volatility Estimation**: Estimates implied volatility for option pricing
- **Performance Analytics**: Comprehensive performance metrics and visualizations
- **Trade Logging**: Detailed trade history with entries, exits, and P&L

## Limitations

- Option pricing uses theoretical models rather than historical option prices
- No consideration for bid-ask spreads or liquidity constraints
- No modeling of early assignment risk
- Simplified estimation of implied volatility 