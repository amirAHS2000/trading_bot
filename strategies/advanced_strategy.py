from .base_strategy import BaseStrategy
from utils.data_preprocessor import preprocess_data


class MLStrategy(BaseStrategy):
    def __init__(self, short_period=9, long_period=21, rsi_period=14, min_train_samples=100):
        super().__init__()
        self.short_period = short_period
        self.long_period = long_period
        self.rsi_period = rsi_period
        self.min_train_samples = min_train_samples
        self.model = None

    def generate_signal(self, data):
        df = preprocess_data(data)
        return