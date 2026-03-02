"""
Enhanced Stock Simulator with Realistic Market Dynamics

Features:
- Log-return based price modeling
- Multi-factor model (market + sector + idiosyncratic)
- "Ladder down, stairs up" return distribution
- Markov regime switching (calm/bull/volatile)
- Rare jump events (market-wide and idiosyncratic)
- Momentum/persistence in short-term trends
- Parameterized and reproducible with seeding
"""

import numpy as np
from numpy.random import default_rng
from flask import Flask, render_template, request, jsonify
import math

app = Flask(__name__)


# ============================================================================
# SIMULATOR CONFIGURATION
# ============================================================================

class StockSimulatorConfig:
    """
    Configuration parameters for the stock simulator.
    All parameters are calibrated for realistic daily behavior.
    """
    
    # --- Market Parameters ---
    MARKET_DAILY_DRIFT = 0.0004  # ~10% annualized drift (slight bullish bias)
    MARKET_DAILY_VOL = 0.012     # ~1.2% daily vol, ~19% annualized
    MARKET_JUMP_PROB = 0.005     # 0.5% chance of market jump per day
    MARKET_JUMP_MEAN = -0.02     # Average jump is slightly negative (-2%)
    MARKET_JUMP_VOL = 0.03       # Jump magnitude volatility
    
    # --- Return Distribution Parameters ---
    DOWN_DAY_PROB = 0.60         # 60% of days are down days (ladder down)
    UP_DAY_MEAN = 0.0015         # Average up day: +0.15%
    UP_DAY_VOL = 0.015           # Up day vol: 1.5%
    DOWN_DAY_MEAN = -0.0005      # Average down day: -0.05%
    DOWN_DAY_VOL = 0.008         # Down day vol: 0.8%
    
    # --- Momentum Parameters ---
    MOMENTUM_PERSISTENCE = 0.3   # How much yesterday's return affects today
    MOMENTUM_LAG = 5             # Look-back period for momentum (days)
    
    # --- Regime Switching ---
    REGIME_STATES = ['calm', 'bull', 'volatile']  # Three regimes
    REGIME_TRANSITION_PROB = 0.03  # 3% chance to switch regimes per day
    REGIME_CALM = {'drift': 0.0002, 'vol': 0.008}
    REGIME_BULL = {'drift': 0.0006, 'vol': 0.012}
    REGIME_VOLATILE = {'drift': 0.0001, 'vol': 0.025}
    
    # --- Stock-Specific Parameters ---
    N_STOCKS = 10
    SECTORS = ['tech', 'health', 'energy', 'financial', 'consumer']
    MAX_DAILY_RETURN = 0.15  # Cap daily returns at +/-15%
    
    # --- Jumps per stock ---
    STOCK_JUMP_PROB = 0.002    # 0.2% chance of stock-specific jump per day
    STOCK_JUMP_MEAN = 0.003    # Avg stock jump: +0.3%
    STOCK_JUMP_VOL = 0.02      # Jump volatility
    
    # --- Factor Loadings (betas) ---
    MARKET_BETA_MIN = 0.5
    MARKET_BETA_MAX = 1.5
    SECTOR_BETA_MIN = 0.2
    SECTOR_BETA_MAX = 0.8
    
    # --- History ---
    MAX_HISTORY_LEN = 500


# ============================================================================
# MARKOV REGIME SWITCHING MODEL
# ============================================================================

class RegimeModel:
    """Two-state Markov regime switcher for market conditions."""
    
    def __init__(self, seed=None):
        self.rng = default_rng(seed)
        self.current_regime = 'calm'
        self.regime_history = ['calm']
    
    def transition(self):
        """Transition to a new regime based on probabilities."""
        state_probs = {
            'calm': {'calm': 0.92, 'bull': 0.04, 'volatile': 0.04},
            'bull': {'calm': 0.05, 'bull': 0.85, 'volatile': 0.10},
            'volatile': {'calm': 0.10, 'bull': 0.10, 'volatile': 0.80}
        }
        
        probs = state_probs[self.current_regime]
        next_state = self.rng.choice(
            list(probs.keys()),
            p=list(probs.values())
        )
        self.current_regime = next_state
        self.regime_history.append(next_state)
        if len(self.regime_history) > StockSimulatorConfig.MAX_HISTORY_LEN:
            self.regime_history.pop(0)
    
    def get_parameters(self):
        """Get drift and volatility for current regime."""
        regime_params = {
            'calm': StockSimulatorConfig.REGIME_CALM,
            'bull': StockSimulatorConfig.REGIME_BULL,
            'volatile': StockSimulatorConfig.REGIME_VOLATILE
        }
        return regime_params[self.current_regime]


# ============================================================================
# STOCK CLASS
# ============================================================================

class Stock:
    """Represents a single stock with its own parameters."""
    
    def __init__(self, name, symbol, sector, market_beta, sector_beta, 
                 idio_vol, start_price, seed=None):
        self.name = name
        self.symbol = symbol
        self.sector = sector
        self.market_beta = market_beta
        self.sector_beta = sector_beta
        self.idio_vol = idio_vol
        self.price = start_price
        self.previous_price = start_price
        self.history = [start_price]
        self.return_history = [0.0]
        self.betas = {'market': market_beta, 'sector': sector_beta}
        self.rng = default_rng(seed)
    
    def update_price(self, market_return, sector_return, regime_drift, regime_vol):
        """
        Update stock price using factor model:
        r_i,t = alpha_i + beta_m,i * M_t + beta_s,i * S_{sector(i),t} + eps_i,t
        
        Plus jump component and momentum.
        """
        # 1. Get regime parameters
        drift = regime_drift * (0.5 + self.betas['market'] * 0.5)
        
        # 2. Generate factor returns with momentum
        # Apply momentum: if last few days were positive, increase up-day probability
        recent_returns = self.return_history[-StockSimulatorConfig.MOMENTUM_LAG:]
        momentum_bias = 0.0
        if len(recent_returns) >= 3:
            recent_up = sum(1 for r in recent_returns if r > 0)
            if recent_up > len(recent_returns) * 0.6:
                momentum_bias = StockSimulatorConfig.MOMENTUM_PERSISTENCE * 0.01
            elif recent_up < len(recent_returns) * 0.4:
                momentum_bias = -StockSimulatorConfig.MOMENTUM_PERSISTENCE * 0.01
        
        # Combined return components
        # Market component
        market_component = self.betas['market'] * market_return
        
        # Sector component
        sector_component = self.betas['sector'] * sector_return
        
        # Idiosyncratic component
        idio_return = self.rng.normal(0, self.idio_vol * regime_vol / StockSimulatorConfig.MARKET_DAILY_VOL)
        
        # Jump component (idiosyncratic)
        jump = 0.0
        if self.rng.random() < StockSimulatorConfig.STOCK_JUMP_PROB:
            jump = self.rng.normal(StockSimulatorConfig.STOCK_JUMP_MEAN, StockSimulatorConfig.STOCK_JUMP_VOL)
        
        # Combine all components
        raw_return = drift + market_component + sector_component + idio_return + jump
        
        # 3. Apply regime-adjusted volatility
        raw_return *= regime_vol / StockSimulatorConfig.MARKET_DAILY_VOL
        
        # 4. Add momentum bias
        raw_return += momentum_bias
        
        # 5. Apply down-up bias (ladder down, stairs up)
        # If return is negative, increase its magnitude slightly
        if raw_return < 0:
            raw_return *= self.rng.uniform(1.0, 1.3)
        
        # 6. Clamp to reasonable bounds
        raw_return = np.clip(raw_return, -StockSimulatorConfig.MAX_DAILY_RETURN, 
                            StockSimulatorConfig.MAX_DAILY_RETURN)
        
        # 7. Calculate new price
        self.previous_price = self.price
        self.price = self.price * math.exp(raw_return)
        
        # 8. Append to history
        self.history.append(self.price)
        self.return_history.append(raw_return)
        
        if len(self.history) > StockSimulatorConfig.MAX_HISTORY_LEN:
            self.history.pop(0)
            self.return_history.pop(0)


# ============================================================================
# MAIN SIMULATOR CLASS
# ============================================================================

class StockSimulator:
    """
    Main stock simulator with all features:
    - Multi-factor model
    - Regime switching
    - Momentum
    - Jumps
    """
    
    def __init__(self, seed=None):
        self.rng = default_rng(seed)
        self.user_portfolio = {}
        self.cost_basis = {}
        self.cash = 10000.0
        self.day = 0
        self.active_orders = {}
        self.trade_history = []
        
        # Initialize regime model
        self.regime_model = RegimeModel(seed=seed)
        
        # Initialize stocks
        self.stocks = self._initialize_stocks(seed)
        
        # Track sector returns
        self.sector_returns = {s: 0.0 for s in StockSimulatorConfig.SECTORS}
        
        # Track market return history
        self.market_return_history = []
        
        # Initialize regime history
        self.regime_history = ['calm']
    
    def _initialize_stocks(self, seed):
        """Initialize all stocks with realistic parameters."""
        np.random.seed(seed)
        
        stocks = []
        start_prices = []
        stock_names = [
            "TechGlobal Inc.", "MediCare Solutions", "GreenEnergy Corp", 
            "FinGlobal Ltd.", "AutoMotive Plus", "RetailWorld", 
            "CloudSystems", "Biotech Innovations", "FoodFusion", 
            "RealEstate Holdings", "TotalMarket Fund"
        ]
        
        stock_symbols = ["TECH", "MDCS", "GREN", "FINL", "AUTO", 
                        "RWLD", "CLOD", "BIOT", "FOOD", "REHL", "TMFT"]
        
        stock_sectors = ['tech', 'health', 'energy', 'financial', 'consumer',
                        'tech', 'financial', 'health', 'consumer', 'real_estate', 'all']
        
        for i in range(StockSimulatorConfig.N_STOCKS):
            # Market beta: varies between 0.5 and 1.5
            market_beta = self.rng.uniform(
                StockSimulatorConfig.MARKET_BETA_MIN,
                StockSimulatorConfig.MARKET_BETA_MAX
            )
            
            # Sector beta: varies between 0.2 and 0.8
            sector_beta = self.rng.uniform(
                StockSimulatorConfig.SECTOR_BETA_MIN,
                StockSimulatorConfig.SECTOR_BETA_MAX
            )
            
            # Idiosyncratic volatility: varies between 1% and 3%
            idio_vol = self.rng.uniform(0.01, 0.03)
            
            # Start price: $10 to $100
            start_price = self.rng.uniform(10, 100)
            start_prices.append(start_price)
            
            stock = Stock(
                name=stock_names[i],
                symbol=stock_symbols[i],
                sector=stock_sectors[i],
                market_beta=market_beta,
                sector_beta=sector_beta,
                idio_vol=idio_vol,
                start_price=start_price,
                seed=seed + i + 100
            )
            stocks.append(stock)
        
        # Add mutual fund that tracks all stocks
        avg_start_price = sum(start_prices) / len(start_prices) / 10
        mutual_fund = Stock(
            name="TotalMarket Fund",
            symbol="TMFT",
            sector="all",
            market_beta=1.0,
            sector_beta=1.0,
            idio_vol=0.005,
            start_price=round(avg_start_price, 2),
            seed=seed + 1000
        )
        stocks.append(mutual_fund)
        
        return stocks
    
    def update_market_factor(self):
        """
        Generate market factor return with:
        - Drift (average trend)
        - Volatility (regime-dependent)
        - Jump component
        """
        # Get regime parameters
        regime_params = self.regime_model.get_parameters()
        regime_drift = regime_params['drift']
        regime_vol = regime_params['vol']
        
        # Base market return
        market_return = self.rng.normal(
            regime_drift,
            StockSimulatorConfig.MARKET_DAILY_VOL * regime_vol / StockSimulatorConfig.MARKET_DAILY_VOL
        )
        
        # Add momentum component
        if len(self.market_return_history) >= 2:
            last_return = self.market_return_history[-1]
            momentum = last_return * StockSimulatorConfig.MOMENTUM_PERSISTENCE
            market_return += momentum
        
        # Add jump component
        if self.rng.random() < StockSimulatorConfig.MARKET_JUMP_PROB:
            jump = self.rng.normal(
                StockSimulatorConfig.MARKET_JUMP_MEAN,
                StockSimulatorConfig.MARKET_JUMP_VOL
            )
            market_return += jump
        
        # Clamp returns
        market_return = np.clip(market_return, -0.2, 0.2)
        
        return market_return, regime_drift, regime_vol
    
    def update_sector_returns(self, market_return):
        """Update sector returns based on market factor."""
        for sector in StockSimulatorConfig.SECTORS:
            # Sector follows market with some lag
            noise = self.rng.normal(0, 0.005)
            self.sector_returns[sector] = market_return * 0.7 + noise * 0.3
    
    def update_prices(self):
        """
        Update all stock prices for one day.
        Called automatically every second in the web interface (1/4 day per second).
        """
        self.day += 1
        
        # Update regime
        if self.rng.random() < StockSimulatorConfig.REGIME_TRANSITION_PROB:
            self.regime_model.transition()
        
        # Update market factor
        market_return, regime_drift, regime_vol = self.update_market_factor()
        
        # Initialize market return history tracking
        if not hasattr(self, 'market_return_history'):
            self.market_return_history = []
        self.market_return_history.append(market_return)
        if len(self.market_return_history) > StockSimulatorConfig.MAX_HISTORY_LEN:
            self.market_return_history.pop(0)
        
        # Update sector returns
        self.update_sector_returns(market_return)
        
        # Update each stock (except the mutual fund)
        for stock in self.stocks[:-1]:
            sector_return = self.sector_returns.get(stock.sector, 0.0)
            stock.update_price(market_return, sector_return, regime_drift, regime_vol)
        
        # Update mutual fund to track average of all other stocks
        mutual_fund = self.stocks[-1]
        # Calculate average return of all other stocks
        if len(self.stocks) > 1:
            recent_returns = []
            for s in self.stocks[:-1]:
                if len(s.return_history) > 1:
                    recent_returns.append(s.return_history[-1])
            avg_return = sum(recent_returns) / len(recent_returns) if recent_returns else 0.0
            mutual_fund.previous_price = mutual_fund.price
            mutual_fund.price = mutual_fund.price * math.exp(avg_return)
            mutual_fund.history.append(mutual_fund.price)
            mutual_fund.return_history.append(avg_return)
            if len(mutual_fund.history) > StockSimulatorConfig.MAX_HISTORY_LEN:
                mutual_fund.history.pop(0)
                mutual_fund.return_history.pop(0)
        
        return self.get_stocks_data()
    
    def get_stocks_data(self):
        """Return current stock data in the format expected by the web interface."""
        return {
            'stocks': [{
                'name': s.name,
                'symbol': s.symbol,
                'price': round(s.price, 2),
                'previous_price': round(s.previous_price, 2),
                'volatility': s.idio_vol,
                'history': s.history,
                'sector': s.sector
            } for s in self.stocks],
            'cash': round(self.cash, 2),
            'portfolio': self.user_portfolio.copy(),
            'day': self.day,
            'regime': self.regime_model.current_regime
        }
    
    def get_stock_history(self, symbol):
        """Get history for a specific stock."""
        stock = next((s for s in self.stocks if s.symbol == symbol), None)
        if not stock:
            return None
        
        return {
            'history': stock.history,
            'return_history': stock.return_history,
            'symbol': symbol
        }
    
    def buy_stock(self, symbol, shares):
        """Buy shares of a stock."""
        stock = next((s for s in self.stocks if s.symbol == symbol), None)
        if not stock:
            return False, "Stock not found!"
        
        cost = stock.price * shares
        if cost > self.cash:
            return False, f"Insufficient funds! Need ${cost:.2f}, have ${self.cash:.2f}"
        
        self.cash -= cost
        if symbol in self.user_portfolio:
            self.user_portfolio[symbol] += shares
            self.cost_basis[symbol] = (
                self.cost_basis[symbol] * (self.user_portfolio[symbol] - shares) + 
                cost
            ) / self.user_portfolio[symbol]
        else:
            self.user_portfolio[symbol] = shares
            self.cost_basis[symbol] = stock.price
        
        self.trade_history.append({
            'day': self.day,
            'type': 'buy',
            'symbol': symbol,
            'shares': shares,
            'price_per_share': stock.price,
            'total': cost,
            'profit': None
        })
        
        return True, f"Bought {shares} shares of {stock.name} at ${stock.price:.2f}"
    
    def sell_stock(self, symbol, shares):
        """Sell shares of a stock."""
        stock = next((s for s in self.stocks if s.symbol == symbol), None)
        if not stock:
            return False, "Stock not found!"
        
        if symbol not in self.user_portfolio:
            return False, "You don't own any shares of this stock!"
        
        if self.user_portfolio[symbol] < shares:
            return False, f"You only own {self.user_portfolio[symbol]} shares"
        
        self.user_portfolio[symbol] -= shares
        if self.user_portfolio[symbol] == 0:
            del self.user_portfolio[symbol]
            del self.cost_basis[symbol]
        
        revenue = stock.price * shares
        self.cash += revenue
        
        profit = (stock.price - self.cost_basis.get(symbol, 0)) * shares
        
        self.trade_history.append({
            'day': self.day,
            'type': 'sell',
            'symbol': symbol,
            'shares': shares,
            'price_per_share': stock.price,
            'total': revenue,
            'profit': profit
        })
        
        return True, f"Sold {shares} shares of {stock.name} at ${stock.price:.2f}"
    
    def sell_all(self, symbol):
        """Sell all shares of a stock."""
        if symbol not in self.user_portfolio or self.user_portfolio[symbol] <= 0:
            return False, "You don't own any shares of this stock!"
        
        shares = self.user_portfolio[symbol]
        return self.sell_stock(symbol, shares)
    
    def get_market_factor_history(self, n_days=None):
        """Get historical market factor returns."""
        if not hasattr(self, 'market_return_history'):
            return []
        
        if n_days is None:
            n_days = len(self.market_return_history)
        
        return self.market_return_history[-n_days:]
    
    def get_trade_history(self):
        """Get trade history."""
        history = self.trade_history.copy()
        # Add average cost basis info to each trade
        for trade in history:
            if trade['type'] == 'buy':
                # For buy trades, include the running cost basis after this purchase
                trade['avg_cost_basis'] = self.cost_basis.get(trade['symbol'], 0)
            else:
                # For sell trades, include the cost basis at time of sale
                trade['avg_cost_basis'] = self.cost_basis.get(trade['symbol'], 0)
        return history


# Global simulator instance
class GlobalSimulator:
    """Container for global state."""
    reset_seed: int

global_state = GlobalSimulator()
global_state.reset_seed = 42

simulator = StockSimulator(seed=42)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/update_prices', methods=['POST'])
def update_prices():
    simulator.update_prices()
    return jsonify({'status': 'success'})


@app.route('/get_stocks', methods=['GET'])
def get_stocks():
    # Update prices on every request to ensure real-time updates
    simulator.update_prices()
    data = simulator.get_stocks_data()
    return jsonify(data)


@app.route('/get_stock_history/<symbol>', methods=['GET'])
def get_stock_history(symbol):
    range_type = request.args.get('range', 'all')  # all, 1m, 6m, 1y
    
    history = simulator.get_stock_history(symbol)
    if not history:
        return jsonify({'status': 'error', 'message': 'Stock not found'}), 404
    
    full_history = history['history']
    full_return_history = history['return_history']
    
    # Convert to days for range selection
    days_map = {'all': None, '300': 300, '30': 30}
    num_days = days_map.get(range_type, None)
    
    # Get the last num_days of data (or all if None)
    if num_days is None:
        history_slice = full_history
        return_slice = full_return_history
    else:
        start_idx = max(0, len(full_history) - num_days)
        history_slice = full_history[start_idx:]
        return_slice = full_return_history[start_idx:] if start_idx < len(full_return_history) else []
    
    return jsonify({
        'status': 'success',
        'history': history_slice,
        'return_history': return_slice,
        'symbol': symbol,
        'show_all_time': num_days is None
    })


@app.route('/get_stock_history/<symbol>/<range_type>', methods=['GET'])
def get_stock_history_range(symbol, range_type):
    """Get stock history for a specific time range."""
    history = simulator.get_stock_history(symbol)
    if not history:
        return jsonify({'status': 'error', 'message': 'Stock not found'}), 404
    
    full_history = history['history']
    
    # Convert to days for range selection
    days_map = {'all': None, '300': 300, '30': 30}
    num_days = days_map.get(range_type, None)
    
    # Get the last num_days of data (or all if None)
    if num_days is None:
        history_slice = full_history
    else:
        start_idx = max(0, len(full_history) - num_days)
        history_slice = full_history[start_idx:]
    
    return jsonify({
        'status': 'success',
        'history': history_slice,
        'symbol': symbol,
        'show_all_time': num_days is None
    })


@app.route('/buy_stock', methods=['POST'])
def buy_stock():
    data = request.get_json()
    symbol = data.get('symbol')
    shares = data.get('shares')
    
    if not symbol or not shares:
        return jsonify({'status': 'error', 'message': 'Missing symbol or shares'})
    
    try:
        shares = int(shares)
        if shares <= 0:
            return jsonify({'status': 'error', 'message': 'Shares must be positive'})
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid shares value'})
    
    success, message = simulator.buy_stock(symbol, shares)
    
    return jsonify({
        'status': 'success' if success else 'error',
        'message': message,
        'cash': round(simulator.cash, 2),
        'portfolio': simulator.user_portfolio.copy()
    })


@app.route('/sell_stock', methods=['POST'])
def sell_stock_route():
    data = request.get_json()
    symbol = data.get('symbol')
    shares = data.get('shares')
    
    if not symbol or not shares:
        return jsonify({'status': 'error', 'message': 'Missing symbol or shares'})
    
    try:
        shares = int(shares)
        if shares <= 0:
            return jsonify({'status': 'error', 'message': 'Shares must be positive'})
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid shares value'})
    
    success, message = simulator.sell_stock(symbol, shares)
    
    return jsonify({
        'status': 'success' if success else 'error',
        'message': message,
        'cash': round(simulator.cash, 2),
        'portfolio': simulator.user_portfolio.copy()
    })


@app.route('/sell_all', methods=['POST'])
def sell_all():
    data = request.get_json()
    symbol = data.get('symbol')
    
    if not symbol:
        return jsonify({'status': 'error', 'message': 'Missing symbol'})
    
    success, message = simulator.sell_all(symbol)
    
    return jsonify({
        'status': 'success' if success else 'error',
        'message': message,
        'cash': round(simulator.cash, 2),
        'portfolio': simulator.user_portfolio.copy()
    })


@app.route('/get_market_factor', methods=['GET'])
def get_market_factor():
    """Return current market factor and recent history."""
    market_history = simulator.get_market_factor_history(100)
    
    return jsonify({
        'current_market_return': simulator.market_return_history[-1] if simulator.market_return_history else 0.0,
        'regime': simulator.regime_model.current_regime,
        'market_history': market_history,
        'day': simulator.day
    })


@app.route('/reset_simulator', methods=['POST'])
def reset_simulator():
    """Reset the simulator with a new seed."""
    global_state.reset_seed = global_state.reset_seed + 1
    global simulator
    simulator = StockSimulator(seed=global_state.reset_seed)
    return jsonify({'status': 'success', 'seed': global_state.reset_seed})


@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    """Cancel an active order."""
    data = request.get_json()
    order_id = data.get('order_id')
    
    if order_id is None:
        return jsonify({'status': 'error', 'message': 'Missing order_id'}), 400
    
    global simulator
    if hasattr(simulator, 'active_orders') and order_id in simulator.active_orders:
        del simulator.active_orders[order_id]
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Order not found'}), 404


@app.route('/get_trade_history', methods=['GET'])
def get_trade_history():
    """Return trade history."""
    return jsonify({
        'trade_history': simulator.get_trade_history()
    })


@app.route('/reset_simulator', methods=['POST'])


def sanity_check():
    """Print summary statistics to verify the simulator is working correctly."""
    print("\n" + "="*70)
    print("SANITY CHECK - Stock Simulator Statistics")
    print("="*70)
    
    # Simulate 252 trading days (1 year)
    for _ in range(252):
        simulator.update_prices()
    
    stocks_data = simulator.get_stocks_data()
    
    print(f"\nTotal days simulated: {simulator.day}")
    print(f"Initial cash: $10,000")
    print(f"Final cash: ${simulator.cash:.2f}")
    
    print("\nStock Statistics:")
    print("-" * 70)
    
    for stock in stocks_data['stocks']:
        history = stock['history']
        returns = [history[i]/history[i-1] - 1 for i in range(1, len(history))]
        
        if len(returns) == 0:
            continue
        
        up_days = sum(1 for r in returns if r > 0)
        down_days = len(returns) - up_days
        fraction_up = up_days / len(returns)
        
        mean_return = np.mean(returns)
        vol = np.std(returns) * np.sqrt(252)  # Annualized
        
        # Annualized return
        price_change = history[-1] / history[0] - 1
        annual_return = (1 + price_change) ** (252 / len(returns)) - 1
        
        print(f"{stock['symbol']}:")
        print(f"  Start: ${stock['history'][0]:.2f}, End: ${stock['price']:.2f}")
        print(f"  Total return: {price_change*100:.2f}%")
        print(f"  Up days: {up_days} ({fraction_up*100:.1f}%)")
        print(f"  Mean daily return: {mean_return*100:.3f}%")
        print(f"  Annualized return: {annual_return*100:.2f}%")
        print(f"  Annualized volatility: {vol*100:.2f}%")
        print()
    
    # Check market factor statistics
    market_returns = simulator.get_market_factor_history()
    if market_returns:
        print("Market Factor Statistics:")
        print(f"  Mean daily return: {np.mean(market_returns)*100:.3f}%")
        print(f"  Volatility: {np.std(market_returns)*100*sqrt(252):.2f}%")
        print(f"  Current regime: {simulator.regime_model.current_regime}")
    
    print("="*70)


from math import sqrt


if __name__ == '__main__':
    # Run sanity check (uncomment to test)
    # sanity_check()
    
    # Start web server (disable reloader to avoid issues)
    app.run(debug=False, host='0.0.0.0', port=5000)
