import os
from dotenv import load_dotenv

load_dotenv()

BROKER = {
    'account': os.getenv('MT5_ACCOUNT'),
    'password': os.getenv('MT5_PASSWORD'),
    'server': os.getenv('MT5_SERVER'),
    'terminal_path': 'C:\\Program Files\\MetaTrader 5\\terminal64.exe'
}

TRADING = {
    'symbol': 'EURUSD',
    'lot_size': 0.01,
    'magic_number': 123456,
    'stop_loss_pips': 50,
    'take_profit_pips': 100,
    'timeframe': 'M15'
}

STRATEGIES = {
    'moving_average': {'short_period': 9, 'long_period': 21},
    'ml_strategy': {'short_period': 9, 'long_period': 21, 'rsi_period': 14},
    'ACTIVE_STRATEGY': 'rule_based'
}