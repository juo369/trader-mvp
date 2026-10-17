"""Technische Indikatoren."""

from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    """Einfacher gleitender Durchschnitt; die ersten window-1 Werte sind NaN."""
    return series.rolling(window=window, min_periods=window).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index mit Wilder-Glättung (ewm, alpha=1/window)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()

    rs = avg_gain / avg_loss
    result = 100 - 100 / (1 + rs)
    # Keine Verluste -> 100; weder Gewinne noch Verluste (flache Reihe) -> neutral 50.
    result = result.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    result = result.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
    return result.where(delta.notna())
