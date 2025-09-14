import MetaTrader5 as mt5
from config.settings import MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER, SYMBOL, TIMEFRAME, SL_PIPS, TP_PIPS
from datetime import datetime


def initialize_mt5():
    """
    Initializes and connects to MetaTrader 5.
    This function should be called only once at the start of the bot.
    """
    if not mt5.initialize(path="C:\\Program Files\\MetaTrader 5\\terminal64.exe"):
        print("initialize() failed, error code =", mt5.last_error())
        return False
    
    print("MetaTrader 5 initialized successfully.")

    # Attempt to login
    if not mt5.login(int(MT5_ACCOUNT), MT5_PASSWORD, MT5_SERVER):
        print("login() failed, error code =", mt5.last_error())
        mt5.shutdown()
        return False
    
    print("Logged in successfully.")
    return True

def get_latest_price(symbol=SYMBOL):
    """Fetches the latest tick data for a given symbol."""
    try:
        # Request tick data
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"Failed to get tick for {symbol}")
            return None
        
        price = tick.bid
        return price
    except Exception as e:
        print(f"An error occurred while fetching price: {e}")
        return None

def get_historical_data(symbol=SYMBOL, timeframe=mt5.TIMEFRAME_M15, num_candles=100):
    """Fetches historical OHLCV data."""
    try:
        # Get historical data
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
        return rates
    except Exception as e:
        print(f"An error occurred while fetching historical data: {e}")
        return None

def calculate_sl_tp_prices(symbol, order_type):
    """
    Calculates the stop loss and take profit prices.
    """
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return None, None
    
    point = symbol_info.point

    # Fetch the latest tick data to get current bid and ask prices
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None, None
    
    if order_type == mt5.ORDER_TYPE_BUY:
        price = tick.ask
        sl_price = price - SL_PIPS * point
        tp_price = price + TP_PIPS * point
    elif order_type == mt5.ORDER_TYPE_SELL:
        price = tick.bid
        sl_price = price + SL_PIPS * point
        tp_price = price - TP_PIPS * point
    else:
        return None, None
    
    return sl_price, tp_price

def open_position(symbol, lot_size, order_type, magic_number):
    """
    Sends a market order to open a new position with SL/TP.
    
    Args:
        symbol (str): The trading symbol (e.g., "EURUSD").
        lot_size (float): The volume of the trade in lots.
        order_type (int): mt5.ORDER_TYPE_BUY or mt5.ORDER_TYPE_SELL.
        magic_number (int): A unique ID for the bot's trades.

    Returns:
        bool: True if the order was sent successfully, False otherwise.
    """
    sl, tp = calculate_sl_tp_prices(symbol, order_type)
    if sl is None or tp is None:
        print("Failed to calculate SL/TP prices.")
        return False
    
    # Create the trade request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": order_type,
        "price": mt5.symbol_info_tick(symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid,
        "sl": sl,
        "tp": tp,
        "deviation": 20, # Slippage in points
        "magic": magic_number,
        "comment": "python script open",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Send the request to the trading terminal
    result = mt5.order_send(request)

    # Check the execution result
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Failed to open position. Error code: {result.retcode}")
        print(f"Request: {request}")
        return False
    else:
        print(f"Successfully sent a {result.type} order for {symbol}.")
        print(f"Position opened with ticket #{result.order} at price {result.price}.")
        print(f"SL: {sl}, TP: {tp}")
        return True

def close_position(position_id):
    """
    Sends a request to close an open position.
    
    Args:
        position_id (int): The ticket number of the position to close.

    Returns:
        bool: True if the order was sent successfully, False otherwise.
    """
    # Get the position details
    position = mt5.positions_get(ticket=position_id)[0]

    # Check the type of the open position to determine the counter-trade
    if position.type == mt5.POSITION_TYPE_BUY:
        close_order_type = mt5.ORDER_TYPE_SELL
        close_price = mt5.symbol_info_tick(position.symbol).bid
    else:
        close_order_type = mt5.ORDER_TYPE_BUY
        close_price = mt5.symbol_info_tick(position.symbol).ask
    
    # Create the trade request to close the position
    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": close_order_type,
        "position": position_id, # THIS IS THE KEY PARAMETER
        "price": close_price,
        "deviation": 20,
        "magic": position.magic,
        "comment": "python script close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    # Send the request
    result = mt5.order_send(close_request)

    # Check the execution result
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Failed to close position {position_id}. Error code: {result.retcode}")
        return False
    else:
        print(f"Successfully closed position {position_id}.")
        return True
