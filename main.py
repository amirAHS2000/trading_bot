import time
import pandas as pd
import MetaTrader5 as mt5
from config.settings import SYMBOL, LOT_SIZE, MAGIC_NUMBER, STOP_LOSS_PIPS, TAKE_PROFIT_PIPS, STRATEGIES, ACTIVE_STRATEGY
from utils.data_fetcher import initialize_mt5, get_historical_data, open_position, close_position
from utils.performance import calculate_metrics, plot_equity_curve
from strategies.rule_based_strategy import MovingAverageCrossover
from strategies.advanced_strategy import MLStrategy
from utils.logger import setup_logger
from strategies.factor import create_strategy

# Initialize the logger
logger = setup_logger()

# Backtesting parameters
INITIAL_BALANCE = 10000.0
SIMULATED_COMMISSION = 2.0  # Commission per trade

def get_open_position():
    """
    Checks if there is an open position for the specified symbol and magic number.
    Returns the position ticket number if found, otherwise returns None.
    """
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions:
        for position in positions:
            if position.magic == MAGIC_NUMBER:
                return position.ticket
    return None

class SimulatedTradeManager:
    """Manages simulated trades for backtesting."""
    def __init__(self, initial_balance):
        self.balance = initial_balance
        self.position = None
        self.entry_price = 0.0
        self.entry_time = None
        self.sl_price = 0.0
        self.tp_price = 0.0
        self.trades = []

    def open_position(self, signal, price, time, spread=2.0):
        if self.position is None:
            self.position = signal
            point = mt5.symbol_info(SYMBOL).point
            if signal == 'BUY':
                self.entry_price = price + spread * point # pay the ask price
                self.sl_price = self.entry_price - STOP_LOSS_PIPS * point
                self.tp_price = self.entry_price + TAKE_PROFIT_PIPS * point
            elif signal == 'SELL':
                self.entry_price = price # Sell at bid price
                self.sl_price = self.entry_price + STOP_LOSS_PIPS * point
                self.tp_price = self.entry_price - TAKE_PROFIT_PIPS * point
            self.entry_time = time
            logger.info(f'SIMULATED TRADE OPENED - {signal} at {self.entry_price:.5f}')
        
    def close_position(self, price, time):
        if self.position is not None:
            profit_per_lot = 0.0
            if self.position == "BUY":
                profit_per_lot = (price - self.entry_price) / mt5.symbol_info(SYMBOL).point
            elif self.position == "SELL":
                profit_per_lot = (self.entry_price - price) / mt5.symbol_info(SYMBOL).point
            
            trade_profit = profit_per_lot * LOT_SIZE - SIMULATED_COMMISSION
            self.balance += trade_profit

            trade_log = {
                "signal": self.position,
                "entry_time": self.entry_time,
                "entry_price": self.entry_price,
                "exit_time": time,
                "exit_price": price,
                "profit": trade_profit,
                "balance": self.balance
            }
            self.trades.append(trade_log)
            logger.info(f"SIMULATED TRADE CLOSED - Profit: {trade_profit:.2f}, New Balance: {self.balance:.2f}")

            self.position = None

def run_backtest():
    """Runs a backtest on historical data."""
    logger.info("Starting backtest...")

    # Fetch a large amount of historical data
    # MT5 connection must be initialized before calling get_historical_data
    rates = get_historical_data(symbol=SYMBOL, num_candles=5000)
    if rates is None:
        logger.error("Failed to fetch historical data for backtesting.")
        return
    
    rates_df = pd.DataFrame(rates)
    rates_df['time'] = pd.to_datetime(rates_df['time'], unit='s')

    strategy = MovingAverageCrossover()
    trade_manager = SimulatedTradeManager(INITIAL_BALANCE)

    # Loop through the historical data simulating a live feed
    for i in range(strategy.long_period, len(rates_df)):
        current_data = rates_df.iloc[:i]

        signal = strategy.generate_signal(current_data)
        current_price = rates_df.iloc[i]['close']
        current_time = rates_df.iloc[i]['time']

        # --- New Backtest Close Logic ---
        # 1. Check for SL/TP hit
        if trade_manager.position is not None:
            if (trade_manager.position == "BUY" and current_price <= trade_manager.sl_price) or \
               (trade_manager.position == "SELL" and current_price >= trade_manager.sl_price):
                trade_manager.close_position(trade_manager.sl_price, current_time)
                continue  # Skip to next candle to avoid multiple closures
            
            if (trade_manager.position == "BUY" and current_price >= trade_manager.tp_price) or \
               (trade_manager.position == "SELL" and current_price <= trade_manager.tp_price):
                trade_manager.close_position(trade_manager.tp_price, current_time)
                continue

        # 2. Check for counter-signal
        if trade_manager.position == "BUY" and signal == "SELL":
            trade_manager.close_position(current_price, current_time)
        elif trade_manager.position == "SELL" and signal == "BUY":
            trade_manager.close_position(current_price, current_time)

        # Check for open conditions
        if trade_manager.position is None:
            if signal == "BUY":
                trade_manager.open_position("BUY", current_price, current_time)
            elif signal == "SELL":
                trade_manager.open_position("SELL", current_price, current_time)

    logger.info(f"Backtest finished. Final Balance: {trade_manager.balance:.2f}")
    metrics = calculate_metrics(trade_manager.trades, INITIAL_BALANCE)
    logger.info(f"Performance Metrics: Total Return: {metrics['total_return']:.2f}%, "
                f"Win Rate: {metrics['win_rate']:.2f}%, Max Drawdown: {metrics['max_drawdown']:.2f}%")
    plot_equity_curve(trade_manager.trades)    

def run_live_bot():
    """Main function to run the trading bot in live mode."""

    # Initialize strategy
    strategy = MovingAverageCrossover()

    logger.info("Starting trading bot in live mode...")

    try:
        while True:
            # Step 1: Fetch historical data
            rates = get_historical_data(symbol=SYMBOL, num_candles=strategy.long_period + 5)

            if rates is not None:
                # Convert data to a pandas DataFrame for easier manipulation
                rates_df = pd.DataFrame(rates)
                rates_df['time'] = pd.to_datetime(rates_df['time'], unit='s')

                # Step 2: Generate signal
                signal = strategy.generate_signal(rates_df)

                # Step 3: Manage trades based on the signal
                current_position = get_open_position()

                # Close logic: Check if a counter-signal is received
                if current_position is not None:
                    # Get position details to check its type (BUY or SELL)
                    position_details = mt5.positions_get(ticket=current_position)[0]

                    if position_details.type == mt5.POSITION_TYPE_BUY and signal == 'SELL':
                        logger.info("SELL signal received. Closing existing BUY position.")
                        close_position(current_position)
                    elif position_details.type == mt5.POSITION_TYPE_SELL and signal == 'BUY':
                        logger.info("BUY signal received. Closing existing SELL position.")
                        close_position(current_position)

                # Open logic: Check for signals to open a new position
                if current_position is None:
                    if signal == 'BUY':
                        logger.info("BUY signal received. Opening a new long position.")
                        open_position(SYMBOL, LOT_SIZE, mt5.ORDER_TYPE_BUY, MAGIC_NUMBER, STOP_LOSS_PIPS, TAKE_PROFIT_PIPS)
                    elif signal == 'SELL':
                        logger.info("SELL signal received. Opening a new short position.")
                        open_position(SYMBOL, LOT_SIZE, mt5.ORDER_TYPE_SELL, MAGIC_NUMBER, STOP_LOSS_PIPS, TAKE_PROFIT_PIPS)
            
            # Pause for a specified interval before the next iteration
            time.sleep(60) # Pause for 60 seconds (adjust as needed)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")

def main():
    """Main function to run the trading bot."""
    if not initialize_mt5():
        logger.error("Failed to initialize and connect to MetaTrader 5.")
        return
    
    strategy_config = STRATEGIES.get(ACTIVE_STRATEGY, {})
    strategy = create_strategy(ACTIVE_STRATEGY, **strategy_config)

    # # Dynamically select strategy
    # if ACTIVE_STRATEGY == 'rule_based':
    #     strategy = MovingAverageCrossover()
    # elif ACTIVE_STRATEGY == 'ml_strategy':
    #     strategy = MLStrategy()
    # else:
    #     logger.error('Invalid strategy selected.')
    #     return
    
    # run_live_bot() # For live, continuous trading
    run_backtest() # For backtesting

    mt5.shutdown()
    logger.info("MetaTrader 5 connection shut down.")

if __name__ == '__main__':
    main()
