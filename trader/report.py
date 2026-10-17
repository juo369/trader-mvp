"""Auswertung für die Web-App: Vergleich mit Kaufen & Halten und Texte in einfacher Sprache.

Reine Logik ohne Streamlit und ohne Netzwerk, damit sie testbar bleibt.
"""

from __future__ import annotations

import pandas as pd

PRESETS: dict[str, tuple[int, int]] = {
    "Schnell (10/30)": (10, 30),
    "Standard (20/50)": (20, 50),
    "Langsam – Golden Cross (50/200)": (50, 200),
}

POPULAR_TICKERS: dict[str, str] = {
    "S&P 500 ETF (SPY)": "SPY",
    "Nasdaq 100 ETF (QQQ)": "QQQ",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Nvidia": "NVDA",
    "Nestlé": "NESN.SW",
    "Novartis": "NOVN.SW",
    "UBS": "UBSG.SW",
    "SMI-Index ETF (CSSMI.SW)": "CSSMI.SW",
    "Bitcoin (BTC-USD)": "BTC-USD",
    "Ethereum (ETH-USD)": "ETH-USD",
}


def clean_ticker(text: str) -> str:
    """Ticker vereinheitlichen: Grossbuchstaben, Leerzeichen werden zu Bindestrichen.

    "btc usd" -> "BTC-USD". Ohne das würde Yahoo zwei verschiedene Ticker laden.
    """
    return "-".join(text.upper().split())


def fmt_number(value: float, decimals: int = 0, signed: bool = False) -> str:
    """Zahl im Schweizer Format: 10'000 oder 1'234.50."""
    sign = "+" if signed else ""
    text = f"{value:{sign},.{decimals}f}"
    return text.replace(",", "'")


def fmt_pct(value: float, signed: bool = True) -> str:
    """Anteil als Prozent mit einer Nachkommastelle, z. B. '+162.0 %'."""
    number = round(value * 100, 1) + 0.0  # + 0.0 verhindert '-0.0'
    sign = "+" if signed else ""
    return f"{number:{sign}.1f} %"


def buy_and_hold_equity(prices: pd.DataFrame, initial_cash: float) -> pd.Series:
    """Wert eines Kontos, das am ersten Tag komplett investiert und dann liegen gelassen wird."""
    close = prices["Close"].astype(float)
    equity = initial_cash * close / close.iloc[0]
    equity.name = "Kaufen & Halten"
    return equity


def verdict(metrics: dict) -> tuple[str, str]:
    """Kurzes Urteil: (level, text). level ist 'good', 'neutral' oder 'bad'."""
    total_return = metrics["total_return"]
    buy_and_hold_return = metrics["buy_and_hold_return"]

    if total_return < 0:
        return "bad", "Die Strategie hätte Geld verloren."
    if total_return >= buy_and_hold_return:
        return "good", "Die Strategie war besser als einfach Kaufen & Halten."
    return (
        "neutral",
        "Die Strategie hat Gewinn gemacht, aber einfach Kaufen & Halten wäre besser gewesen.",
    )


def explain_metrics(metrics: dict, initial_cash: float, final_value: float) -> list[str]:
    """Erklärt die Kennzahlen in einfachen Sätzen."""
    total_return = metrics["total_return"]
    cagr = metrics["cagr"]
    max_drawdown = metrics["max_drawdown"]
    num_trades = metrics["num_trades"]
    buy_and_hold_return = metrics["buy_and_hold_return"]

    return [
        f"Aus {fmt_number(initial_cash)} wären {fmt_number(final_value)} geworden "
        f"({fmt_pct(total_return)}).",
        f"Pro Jahr im Schnitt {fmt_pct(cagr)}.",
        f"Im schlimmsten Moment lag das Konto {fmt_pct(abs(max_drawdown), signed=False)} "
        "unter seinem Höchststand.",
        f"Die Strategie hat {num_trades} Mal gekauft oder verkauft.",
        f"Einfach Kaufen & Halten hätte {fmt_pct(buy_and_hold_return, signed=False)} gebracht.",
    ]
