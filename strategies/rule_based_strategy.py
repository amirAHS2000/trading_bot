import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy


class MovingAverageCrossover(BaseStrategy):
    """
    A simple Moving Average Crossover strategy.

    - Generates a BUY signal when the short-term MA crosses above the long-term MA.
    - Generates a SELL signal when the short-term MA crosses below the long-term MA.
    """

    def __init__(self, short_period=9, long_period=21):
        super().__init__()
        self.short_period = short_period
        self.long_period = long_period

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

        # Get the latest values
        latest_short_ma = df['short_ma'].iloc[-1]
        latest_long_ma = df['long_ma'].iloc[-1]
        previous_short_ma = df['short_ma'].iloc[-2]
        previous_long_ma = df['long_ma'].iloc[-2]

        if not pd.isna(previous_short_ma) and not pd.isna(previous_long_ma):
            # Check for BUY signal: short MA crosses above long MA
            if previous_short_ma < previous_long_ma and latest_short_ma > latest_long_ma:
                if self.last_signal != 'BUY':
                    self.last_signal = 'BUY'
                    return 'BUY'
            
            # Check for SELL signal: short MA crosses below long MA
            elif previous_short_ma > previous_long_ma and latest_short_ma < latest_long_ma:
                if self.last_signal != 'SELL':
                    self.last_signal = 'SELL'
                    return 'SELL'
        
        return 'HOLD'
