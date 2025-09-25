import pandas as pd
import numpy as np


def preprocess_data(df):
    """Cleans and preprocesses data for ML strategies"""
    df = df.copy()
    # Handles missing values
    df = df.fillna(method='ffill').fillna(method='bfill')
    # Normalize features (could be optional)
    for col in ['close', 'open', 'high', 'low']:
        if col in df:
            df[f'{col}_norm'] = (df[col] - df[col].mean()) / df[col].std()
    return df
