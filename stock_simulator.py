import random
import time
from datetime import datetime, timedelta

class StockSimulator:
    def __init__(self):
        self.stocks = []
        self.user_portfolio = {}
        self.cash = 10000.0
        self.initialize_stocks()
        
    def initialize_stocks(self):
        """Initialize 10 imaginary stocks with realistic starting prices"""
        stock_names = [
            "TechGlobal Inc.", "MediCare Solutions", "GreenEnergy Corp", 
            "FinGlobal Ltd.", "AutoMotive Plus", "RetailWorld", 
            "CloudSystems", "Biotech Innovations", "FoodFusion", 
            "RealEstate Holdings"
        ]
        
        stock_symbols = [
            "TECH", "MDCS", "GREN", "FINL", "AUTO", 
            "RWLD", "CLOD", "BIOT", "FOOD", "REHL"
        ]
        
        for i in range(10):
            # Start with realistic prices between $10-$100
            start_price = random.uniform(10, 100)
            self.stocks.append({
                'name': stock_names[i],
                'symbol': stock_symbols[i],
                'price': round(start_price, 2),
                'previous_price': round(start_price, 2),
                'volatility': random.uniform(0.01, 0.05),  # 1-5% volatility
                'trend': random.choice([1, -1])  # Trend direction
            })
    
    def update_prices(self):
        """Update all stock prices based on random factors"""
        for stock in self.stocks:
            # Calculate daily change based on trend and random factor
            trend_factor = stock['trend'] * 0.02  # 2% trend influence
            random_factor = random.uniform(-stock['volatility'], stock['volatility'])
            change_factor = trend_factor + random_factor
            
            # Apply change to price
            new_price = stock['price'] * (1 + change_factor)
            
            # Ensure price doesn't go below $0.01
            if new_price < 0.01:
                new_price = 0.01
            
            stock['previous_price'] = stock['price']
            stock['price'] = round(new_price, 2)
    
    def display_stocks(self):
        """Display current stock prices"""
        print("\n" + "="*80)
        print(f"{'STOCK':<15} {'SYMBOL':<10} {'CURRENT PRICE':<15} {'CHANGE':<15}")
        print("="*80)
        
        for stock in self.stocks:
            change = stock['price'] - stock['previous_price']
            change_percent = (change / stock['previous_price']) * 100
            
            change_str = f"${change:+.2f} ({change_percent:+.2f}%)"
            
            print(f"{stock['name']:<15} {stock['symbol']:<10} ${stock['price']:<14.2f} {change_str:<15}")
        
        print("="*80)
        print(f"Your Cash Balance: ${self.cash:.2f}")
        print("="*80)
    
    def display_portfolio(self):
        """Display user's current portfolio"""
        print("\n" + "="*50)
        print("YOUR PORTFOLIO")
        print("="*50)
        print(f"{'STOCK':<15} {'SYMBOL':<10} {'SHARES':<10} {'VALUE':<15}")
        print("-"*50)
        
        total_value = self.cash
        if not self.user_portfolio:
            print("No stocks owned")
        else:
            for symbol, shares in self.user_portfolio.items():
                stock = next((s for s in self.stocks if s['symbol'] == symbol), None)
                if stock:
                    value = shares * stock['price']
                    total_value += value
                    print(f"{stock['name']:<15} {symbol:<10} {shares:<10} ${value:<14.2f}")
        
        print("-"*50)
        print(f"Total Portfolio Value: ${total_value:.2f}")
        print("="*50)
    
    def buy_stock(self, symbol, shares):
        """Buy stocks"""
        stock = next((s for s in self.stocks if s['symbol'] == symbol), None)
        if not stock:
            print("Stock not found!")
            return False
            
        cost = stock['price'] * shares
        if cost > self.cash:
            print(f"Insufficient funds! Need ${cost:.2f}, but you have ${self.cash:.2f}")
            return False
            
        self.cash -= cost
        if symbol in self.user_portfolio:
            self.user_portfolio[symbol] += shares
        else:
            self.user_portfolio[symbol] = shares
            
        print(f"Bought {shares} shares of {stock['name']} at ${stock['price']:.2f} per share")
        return True
    
    def sell_stock(self, symbol, shares):
        """Sell stocks"""
        stock = next((s for s in self.stocks if s['symbol'] == symbol), None)
        if not stock:
            print("Stock not found!")
            return False
            
        if symbol not in self.user_portfolio:
            print("You don't own any shares of this stock!")
            return False
            
        if self.user_portfolio[symbol] < shares:
            print(f"You only own {self.user_portfolio[symbol]} shares of {stock['name']}")
            return False
            
        # Sell the stocks
        self.user_portfolio[symbol] -= shares
        if self.user_portfolio[symbol] == 0:
            del self.user_portfolio[symbol]
            
        revenue = stock['price'] * shares
        self.cash += revenue
        print(f"Sold {shares} shares of {stock['name']} at ${stock['price']:.2f} per share")
        return True
    
    def run(self):
        """Main simulation loop"""
        print("Welcome to the Stock Simulator!")
        print("You start with $10,000 in cash.")
        print("Commands: buy [symbol] [shares], sell [symbol] [shares], portfolio, quit")
        
        try:
            while True:
                # Update prices daily
                self.update_prices()
                self.display_stocks()
                
                # Get user input
                command = input("\nEnter command: ").strip().lower()
                
                if command == "quit":
                    self.display_portfolio()
                    print("Thanks for playing!")
                    break
                elif command == "portfolio":
                    self.display_portfolio()
                    continue
                elif command.startswith("buy"):
                    try:
                        parts = command.split()
                        if len(parts) != 3:
                            print("Usage: buy [symbol] [shares]")
                            continue
                        symbol = parts[1].upper()
                        shares = int(parts[2])
                        if shares <= 0:
                            print("Shares must be positive")
                            continue
                        self.buy_stock(symbol, shares)
                    except ValueError:
                        print("Invalid command format. Usage: buy [symbol] [shares]")
                elif command.startswith("sell"):
                    try:
                        parts = command.split()
                        if len(parts) != 3:
                            print("Usage: sell [symbol] [shares]")
                            continue
                        symbol = parts[1].upper()
                        shares = int(parts[2])
                        if shares <= 0:
                            print("Shares must be positive")
                            continue
                        self.sell_stock(symbol, shares)
                    except ValueError:
                        print("Invalid command format. Usage: sell [symbol] [shares]")
                else:
                    print("Unknown command. Use 'buy', 'sell', 'portfolio', or 'quit'")
        except EOFError:
            print("\nExiting simulator...")

if __name__ == "__main__":
    simulator = StockSimulator()
    simulator.run()