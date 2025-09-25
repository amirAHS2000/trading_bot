import pandas as pd
import matplotlib.pyplot as plt


def calculate_metrics(trades, initial_balance):
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        return {'total_return': 0, 'win_rate': 0, 'max_drawdown': 0}
    
    # total return
    final_balance = trades_df['balance'].iloc[-1]
    total_return = (final_balance - initial_balance) / initial_balance * 100

    # win rate
    win_rate = (trades_df['profit'] > 0).mean() * 100

    # maximum drawdown
    balance_series = trades_df['balance']
    rolling_max = balance_series.cummax()
    drawdowns = (rolling_max - balance_series) / rolling_max * 100
    max_drawdown = drawdowns.max()

    return {
        'total_return': total_return,
        'win_rate': win_rate,
        'max_drawdown': max_drawdown
    }

def plot_equity_curve(trades, save_path='logs/equity_curve.png'):
    trades_df = pd.DataFrame(trades)
    plt.figure(figsize=(10, 6))
    plt.plot(trades_df['exit_time'], trades_df['balance'], label='Equity Curve')
    plt.xlabel('Time')
    plt.ylabel('Balance')
    plt.title('Backtest Equity Curve')
    plt.legend()
    plt.savefig(save_path)
    plt.close()
