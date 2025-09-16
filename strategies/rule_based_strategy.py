import pandas as pd
import numpy as np


class MovingAverageCrossover:
    """
    A simple Moving Average Crossover strategy.

    - Generates a BUY signal when the short-term MA crosses above the long-term MA.
    - Generates a SELL signal when the short-term MA crosses below the long-term MA.
    """
    def __init__(self, short_period=9, long_period=21):
        self.short_period = short_period
        self.long_period = long_period
        self.last_signal = None # To prevent repeated signals

    def generate_signal(self, data):
        """
        Generates a trading signal (BUY, SELL, or HOLD) based on MA crossover.

        Args:
            data (pd.DataFrame): A DataFrame containing 'close' prices.

        Returns:
            str: 'BUY', 'SELL', or 'HOLD'.
        """
        # create a copy to avoid the SettingWithCopyWarning
        df = data.copy()

        if len(df) < self.long_period:
            return 'HOLD'
        
        # Calculate Moving Averages
        df['short_ma'] = df['close'].rolling(window=self.short_period).mean()
        df['long_ma'] = df['close'].rolling(window=self.long_period).mean()

        # Check for crossover at the latest point
        # Make sure the last two values are not NaN before comparison
        if not pd.isna(df['short_ma'].iloc[-2]) and not pd.isna(df['long_ma'].iloc[-2]):
            # Check for BUY signal: short MA crosses above long MA
            if df['short_ma'].iloc[-2] < df['long_ma'].iloc[-2] and \
               df['short_ma'].iloc[-1] > df['long_ma'].iloc[-1]:
                if self.last_signal != 'BUY':
                    self.last_signal = 'BUY'
                    return 'BUY'
            # Check for SELL signal: short MA crosses below long MA
            elif df['short_ma'].iloc[-2] > df['long_ma'].iloc[-2] and \
                 df['short_ma'].iloc[-1] < df['long_ma'].iloc[-1]:
                if self.last_signal != 'SELL':
                    self.last_signal = 'SELL'
                    return 'SELL'
            
        return 'HOLD'