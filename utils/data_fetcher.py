import MetaTrader5 as mt5
import pandas as pd
import os
import time
from datetime import datetime
from config.settings import MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER, SYMBOL, TIMEFRAME, STOP_LOSS_PIPS, TAKE_PROFIT_PIPS, LOT
from utils.logger import setup_logger
from config import settings

logger = setup_logger()

def initialize_mt5(max_retries=3, retry_delay=10):
    for attempt in range(max_retries):
        if mt5.initialize(path=settings.BROKER['terminal_path']):
            if mt5.login(int(settings.BROKER['account']), settings.BROKER['password'], settings.BROKER['server']):
                logger.info('MT5 initialized and logged in.')
                return True
            mt5.shutdown()
        logger.warning(f'MT5 initialization failed, attempt {attempt + 1}/{max_retries}')
        time.sleep(retry_delay)
    logger.error('Failed to initialize MT5 after retries.')
    return False

def get_latest_price(symbol=SYMBOL):
    """Fetches the latest tick data for a given symbol."""
    try:
        # Request tick data
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"Failed to get tick for {symbol}")
            return None
        
        price = tick.bid
        return price
    except Exception as e:
        logger.error(f"An error occurred while fetching price: {e}")
        return None

def get_historical_data(symbol=SYMBOL, timeframe=mt5.TIMEFRAME_M15, num_candles=100):
    """Fetches historical OHLCV data."""
    try:
        # Get historical data
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
        return rates
    except Exception as e:
        logger.error(f"An error occurred while fetching historical data: {e}")
        return None
    
def save_historical_data(symbol, timeframe, num_candles, save_dir='data/raw_data'):
    rates = get_historical_data(symbol, timeframe, num_candles)
    if rates is None:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], units='s')
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{save_dir}/{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    logger.info(f'Saved historical data to {filename}')
    return rates

def calculate_lot_size(symbol, account_equity, risk_percent=1.0, stop_loss_pips=STOP_LOSS_PIPS):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return settings.TRADING['lot_size'] # fallback
    point = symbol_info.point
    pip_value = symbol_info.trade_tick_value
    risk_amount = account_equity * (risk_percent / 100)
    lot_size = risk_amount / (stop_loss_pips * pip_value)
    return round(lot_size, 2)

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
        sl_price = price - STOP_LOSS_PIPS * point
        tp_price = price + TAKE_PROFIT_PIPS * point
    elif order_type == mt5.ORDER_TYPE_SELL:
        price = tick.bid
        sl_price = price + STOP_LOSS_PIPS * point
        tp_price = price - TAKE_PROFIT_PIPS * point
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
    account_info = mt5.account_info()

    if account_info:
        lot_size = calculate_lot_size(symbol, account_info.equity)

    if account_info.margin_free < lot_size * mt5.symbol_info(symbol).margin_initial:
        logger.error('Insufficient margin to open position')
        return False
    
    sl, tp = calculate_sl_tp_prices(symbol, order_type)
    if sl is None or tp is None:
        logger.error("Failed to calculate SL/TP prices.")
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
        logger.error(f"Failed to open position. Error code: {result.retcode}")
        logger.error(f"Request: {request}")
        return False
    else:
        logger.info(f"Successfully sent a {result.type} order for {symbol}.")
        logger.info(f"Position opened with ticket #{result.order} at price {result.price}.")
        logger.info(f"SL: {sl}, TP: {tp}")
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
        logger.error(f"Failed to close position {position_id}. Error code: {result.retcode}")
        return False
    else:
        logger.info(f"Successfully closed position {position_id}.")
        return True
