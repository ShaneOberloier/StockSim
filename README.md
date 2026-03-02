# Stock Simulator

A basic stock trading simulator that generates 10 imaginary stocks with realistic price fluctuations.

## Features

- 10 imaginary stocks with realistic price movements
- Buy and sell stocks
- Portfolio tracking
- Cash balance management
- Daily price updates

## How to Run

1. Save the code to a file named `stock_simulator.py`
2. Run with Python 3:
   ```
   python3 stock_simulator.py
   ```

## How to Use

- **buy [symbol] [shares]** - Buy specified shares of a stock
- **sell [symbol] [shares]** - Sell specified shares of a stock
- **portfolio** - View your current holdings and cash balance
- **quit** - Exit the simulator

## Example Commands

```
buy TECH 10
sell MDCS 5
portfolio
```

## Simulation Details

- Each stock starts with a realistic price between $10-$100
- Prices fluctuate daily with volatility factors (1-5%)
- Stocks may trend upward or downward over time
- You start with $10,000 in cash