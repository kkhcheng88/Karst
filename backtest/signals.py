"""Signal primitives. Wilder's RSI + SMA. Kept minimal and transparent."""
from __future__ import annotations

import pandas as pd


def rsi(close: pd.Series, period: int = 2) -> pd.Series:
    """Wilder's RSI (used by Connors' RSI-2)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period, min_periods=period).mean()
