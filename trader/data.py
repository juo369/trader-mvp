"""Kursdaten von Yahoo Finance (yfinance) mit lokalem CSV-Cache."""

from __future__ import annotations

import os

import pandas as pd
import yfinance as yf

PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def _normalize(raw: pd.DataFrame) -> pd.DataFrame:
    """Reduziert das yfinance-Ergebnis (ggf. MultiIndex-Spalten) auf OHLCV."""
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.loc[:, ~df.columns.duplicated()]
    return df[PRICE_COLUMNS]


def load_prices(
    ticker: str,
    start: str,
    end: str | None = None,
    cache_dir: str = "data/cache",
) -> pd.DataFrame:
    """Lädt OHLCV-Daten für ein Ticker-Symbol, bevorzugt aus dem Cache.

    Gecacht wird nur mit festem ``end``; ohne ``end`` wären die Daten sonst für immer veraltet.
    """
    cache_path = os.path.join(cache_dir, f"{ticker}_{start}_{end}.csv") if end else None
    if cache_path and os.path.exists(cache_path):
        return pd.read_csv(cache_path, index_col=0, parse_dates=True)

    raw = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        raise ValueError(
            f"Keine Kursdaten für '{ticker}' im Zeitraum {start} bis {end or 'heute'} gefunden."
        )

    # Tage ohne Schlusskurs (z. B. vor dem ersten Handelstag) würden Kennzahlen zu NaN machen.
    df = _normalize(raw).dropna(subset=["Close"])
    if df.empty:
        raise ValueError(
            f"Keine Kursdaten für '{ticker}' im Zeitraum {start} bis {end or 'heute'} gefunden."
        )
    df.index.name = "Date"
    if cache_path:
        os.makedirs(cache_dir, exist_ok=True)
        df.to_csv(cache_path)
    return df


def latest_price(ticker: str) -> float:
    """Letzter Schlusskurs der letzten 5 Handelstage."""
    raw = yf.download(ticker, period="5d", auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        raise ValueError(f"Keine aktuellen Kursdaten für '{ticker}' gefunden.")

    close = _normalize(raw)["Close"].dropna()
    if close.empty:
        raise ValueError(f"Keine gültigen Schlusskurse für '{ticker}' gefunden.")
    return float(close.iloc[-1])
