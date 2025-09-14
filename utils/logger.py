import logging
import os


def setup_logger():
    """
    Sets up a logger for the trading bot.
    """
    if not os.path.exists("logs"):
        os.makedirs("logs")

    log_file = os.path.join("logs", "trading.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler() # Also prints to the console
        ]
    )

    return logging.getLogger("trading_bot")
