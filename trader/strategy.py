"""Handelsstrategien. Signale: 1 = long, 0 = flat."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from trader.indicators import sma


class Strategy(ABC):
    @abstractmethod
    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        """Liefert pro Zeile von prices ein Signal (1 = long, 0 = flat)."""


class SmaCrossover(Strategy):
    """Long, solange der schnelle SMA über dem langsamen SMA liegt."""

    def __init__(self, fast: int = 20, slow: int = 50):
        if fast >= slow:
            raise ValueError(f"fast ({fast}) muss kleiner als slow ({slow}) sein.")
        self.fast = fast
        self.slow = slow

    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        close = prices["Close"]
        fast_ma = sma(close, self.fast)
        slow_ma = sma(close, self.slow)
        # NaN-Vergleiche ergeben False, damit ist die Anlaufphase automatisch 0.
        signal = (fast_ma > slow_ma).astype(int)
        return pd.Series(signal.values, index=prices.index, name="signal")


class PriceAboveSma(Strategy):
    """Long, solange der Schlusskurs über dem einfachen Durchschnitt der letzten window Tage liegt."""

    def __init__(self, window: int = 200):
        if window < 2:
            raise ValueError(f"window ({window}) muss mindestens 2 sein.")
        self.window = window

    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        close = prices["Close"]
        ma = sma(close, self.window)
        # NaN-Vergleiche ergeben False, damit ist die Anlaufphase automatisch 0.
        signal = (close > ma).astype(int)
        return pd.Series(signal.values, index=prices.index, name="signal")
