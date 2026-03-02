# Stock Simulator - AGENTS.md

This file provides guidelines and instructions for AI agents working on this codebase.

## Project Overview

A stock market simulator with realistic market dynamics including:
- Multi-factor price modeling (market + sector + idiosyncratic)
- Markov regime switching (calm/bull/volatile)
- Momentum/persistence in short-term trends
- Jump events (market-wide and stock-specific)
- Web interface for trading stocks

## Build & Run Commands

```bash
# Activate virtual environment first
source stock_simulator_env/bin/activate

# Run the web server
python stock_simulator_web.py

# Test the API endpoints
curl http://localhost:5000/get_stocks
curl http://localhost:5000/get_stock_history/TECH/1m

# Restart server
pkill -f stock_simulator_web.py && python stock_simulator_web.py &

# Run sanity check (prints statistics)
# Uncomment sanity_check() call at bottom of stock_simulator_web.py
```

## Testing

No formal test suite. Manual testing via:
1. Start server: `python stock_simulator_web.py`
2. Open http://localhost:5000
3. Test each feature (buy, sell, orders, charts)
4. Verify data consistency in portfolio

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve index.html |
| `/get_stocks` | GET | Get all stocks with current prices |
| `/get_stock_history/<symbol>` | GET | Get stock price history |
| `/get_stock_history/<symbol>/<range>` | GET | Get history for range (1m, 6m, 1y) |
| `/buy_stock` | POST | Buy shares `{"symbol": "TECH", "shares": 10}` |
| `/sell_stock` | POST | Sell shares `{"symbol": "TECH", "shares": 10}` |
| `/sell_all` | POST | Sell all shares `{"symbol": "TECH"}` |
| `/reset_simulator` | POST | Reset with new seed |
| `/get_market_factor` | GET | Get market factor and regime |

## Code Style Guidelines

### Python (stock_simulator_web.py)

**Imports:**
- Standard library first: `import`, `from X import Y`
- Third-party: `numpy`, `flask`
- Always use `import numpy as np`
- Use `from numpy.random import default_rng` for RNG
- Group: stdlib → third-party → local (none here)

**Naming Conventions:**
- Classes: `PascalCase` (e.g., `StockSimulator`, `RegimeModel`)
- Functions: `snake_case` (e.g., `update_prices`, `get_stock_history`)
- Variables: `snake_case` (e.g., `market_return`, `user_portfolio`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `MARKET_DAILY_DRIFT`)
- Private methods: prefix with `_` (e.g., `_initialize_stocks`)

**Type Hints:**
- Use type hints for function parameters and return values
- Example: `def update_prices(self) -> dict:`
- Use `List`, `Dict`, `Tuple` from `typing` for complex types
- Example: `def get_stock_history(self, symbol: str) -> Dict[str, List[float]]:`

**Error Handling:**
- Use try/except for file I/O and external API calls
- Return JSON errors with status and message for API endpoints
- Use consistent error response format: `{"status": "error", "message": "..."}`
- Log errors with `print()` for debugging

**Formatting:**
- 4 spaces for indentation
- Max line length: 100 characters
- Docstrings for all public functions and classes (Google style)
- One blank line between functions
- Class docstrings go after class definition line

### JavaScript (templates/index.html)

**Naming Conventions:**
- Variables/functions: `camelCase` (e.g., `updateStocks`, `selectedStockSymbol`)
- CSS classes: `kebab-case` (e.g., `portfolio-item`, `order-container`)
- Constants (if any): `UPPER_SNAKE_CASE`

**Code Organization:**
- Define global state at top: `let stocksData = [];`
- Use `fetch()` for API calls
- Handle errors with `.catch()`
- Update UI immediately on user interaction
- Group related functions together

**Formatting:**
- 2 spaces for indentation in HTML/JS
- Use backticks for template literals
- Minimize DOM manipulation in loops
- Use `const` by default, `let` when reassignment needed

### HTML/CSS

**Structure:**
- Semantic HTML5 elements
- CSS in `<style>` tag in `<head>`
- Use classes for reusable styles
- ID for single elements

**Color Convention:**
- Positive: `#27ae60` (green)
- Negative: `#e74c3c` (red)
- Primary: `#3498db` (blue)
- Warning: `#f39c12` (orange)

## Key Files

- `stock_simulator_web.py` - Backend Flask server (767 lines)
- `templates/index.html` - Frontend HTML/JS/CSS (1109 lines)
- `stock_simulator.py` - CLI version (legacy)
- `AGENTS.md` - This file

## Dependencies

```
Flask==3.1.3
numpy==2.4.2
```

Virtual environment: `stock_simulator_env/`

## Common Patterns

### Adding New API Endpoint
```python
@app.route('/new_endpoint', methods=['POST'])
def new_endpoint():
    data = request.get_json()
    # Validate input
    # Process request
    return jsonify({'status': 'success', 'data': ...})
```

### Adding New Stock Function
```python
def new_stock_method(self, param: str) -> bool:
    """Description of what method does.
    
    Args:
        param: Description of parameter
        
    Returns:
        True if successful, False otherwise
    """
    # Implementation
    return True
```

## Git

- This is not a git repository
- Changes are made directly to files
- Always backup before major changes

## Debugging Tips

- Check browser console (F12) for JavaScript errors
- Use `curl` to test API endpoints directly
- Check server console for Python errors
- Verify data consistency in portfolio after trades

## Agent Behavior Guidelines

- Always present a clear plan/checklist of actions before executing any changes
- Break complex tasks into specific, actionable steps
- Communicate the reasoning behind each decision clearly
- Update the plan as you progress through tasks
