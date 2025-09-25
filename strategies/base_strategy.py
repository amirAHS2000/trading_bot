class BaseStrategy:
    def __init__(self):
        self.last_signal = None
    
    def generate_signal(self, data):
        """
        Generate a trading signal based on input data.
        Must be implemented by subclasses.
        """
        raise NotImplementedError('Subclasses must implement generate_signal.')
