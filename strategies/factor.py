from .rule_based_strategy import MovingAverageCrossover
from .advanced_strategy import MLStrategy


def create_strategy(strategy_name, **kwargs):
    if strategy_name == 'rule_based':
        return MovingAverageCrossover(**kwargs)
    elif strategy_name == 'ml_strategy':
        return MLStrategy(**kwargs)
    else:
        raise ValueError(f'Unknown strategy: {strategy_name}')
