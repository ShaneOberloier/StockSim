# Stock Simulator Web GUI

I've created a web-based stock simulator with a nice GUI interface. The simulator is now ready to use.

## Features

- 10 imaginary stocks with realistic price fluctuations
- Buy and sell stocks through a web interface
- Portfolio tracking
- Real-time price updates
- Responsive web design

## How to Run

1. Open a terminal in the project directory
2. Run the simulator using:
   ```bash
   ./stock_simulator_env/bin/python stock_simulator_web.py
   ```

3. Open your web browser and go to:
   ```
   http://127.0.0.1:5000
   ```

## How to Use

- The simulator starts with $10,000 in cash
- View stock prices in the table at the bottom
- Use the controls at the top to:
  - Buy stocks (enter symbol and shares)
  - Sell stocks (enter symbol and shares)
  - Update prices manually
- Your portfolio is displayed in the portfolio section

## Requirements

- Python 3
- Flask web framework (automatically installed in virtual environment)

## Notes

The web server will be running on port 5000. You can access it from any device on the same network using the IP address shown in the terminal output (e.g., http://192.168.0.213:5000).

To stop the server, press Ctrl+C in the terminal where it's running.