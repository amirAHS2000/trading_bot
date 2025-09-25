import pytest
import pandas as pd
from strategies.rule_based_strategy import MovingAverageCrossover


def test_moving_average_crossover():
    data = pd.DataFrame({
        'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    })
    strategy = MovingAverageCrossover(short_period=3, long_period=5)
    signal = strategy.generate_signal(data)
    assert signal in ['BUY', 'SELL', 'HOLD']
