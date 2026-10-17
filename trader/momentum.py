"""Monatliche Momentum-Rotation: die zuletzt stärksten Werte halten, einmal im Monat umschichten.

Reine Logik ohne Streamlit. Netzwerk nur über den übergebenen Loader (Standard: load_prices).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from trader.data import load_prices

UNIVERSES: dict[str, list[str]] = {
    "Weltweite ETFs (Aktien, Anleihen, Gold)": ["SPY", "QQQ", "EFA", "EEM", "TLT", "GLD"],
    "US-Tech-Aktien": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META"],
    "Schweizer Aktien": ["NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "ZURN.SW", "ABBN.SW"],
    "Krypto": ["BTC-USD", "ETH-USD"],
}


@dataclass
class MomentumResult:
    """equity: Tageswerte. rebalances: je Entscheidung eine Zeile, date = Tag der Ausführung.

    'changed' ist True, wenn die Auswahl gegenüber der letzten Entscheidung anders ist.
    Die allererste Entscheidung zählt nicht als Wechsel.
    """

    equity: pd.Series
    rebalances: pd.DataFrame
    metrics: dict = field(default_factory=dict)


def load_universe(
    tickers: list[str],
    start: str,
    loader=load_prices,
) -> tuple[pd.DataFrame, list[str]]:
    """Lädt die Schlusskurse aller Ticker und behält nur Tage, an denen alle einen Kurs haben.

    Gibt (DataFrame mit einer Spalte je Ticker, Liste der übersprungenen Ticker) zurück.
    """
    series: dict[str, pd.Series] = {}
    skipped: list[str] = []
    for ticker in dict.fromkeys(tickers):
        try:
            close = loader(ticker, start)["Close"].astype(float).dropna()
            if close.empty:
                raise ValueError(f"Keine Kurse für {ticker}")
        except Exception:
            skipped.append(ticker)
            continue
        series[ticker] = close

    if len(series) < 2:
        raise ValueError(
            f"Es werden mindestens 2 Werte mit Kursdaten gebraucht, geladen werden konnten "
            f"nur {len(series)}."
        )

    closes = pd.DataFrame(series).sort_index().dropna()
    if closes.empty:
        raise ValueError("Die Werte haben keine gemeinsamen Handelstage im gewählten Zeitraum.")
    closes.index.name = "Date"
    return closes, skipped


def month_end_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Letzter vorhandener Handelstag jedes Monats."""
    idx = pd.DatetimeIndex(index).sort_values()
    if len(idx) == 0:
        return idx
    months = idx.to_period("M")
    is_last = np.append(months[:-1] != months[1:], True)
    return idx[is_last]


def momentum_scores(closes: pd.DataFrame, lookback_months: int, as_of) -> pd.Series:
    """Rendite je Ticker vom letzten Handelstag des Monats `lookback_months` vor as_of bis as_of.

    NaN, wenn für diesen Zeitraum keine Historie vorhanden ist.
    """
    if lookback_months < 1:
        raise ValueError("Der Rückblick muss mindestens 1 Monat sein.")
    as_of = pd.Timestamp(as_of)
    index = closes.index
    target_month = as_of.to_period("M") - lookback_months
    past = index[index.to_period("M") == target_month]
    if len(past) == 0:
        return pd.Series(np.nan, index=closes.columns, dtype=float)
    start = past[-1]
    return closes.loc[as_of] / closes.loc[start] - 1


def choose(scores: pd.Series, top_n: int, cash_filter: bool) -> list[str]:
    """Die top_n besten Werte. Mit cash_filter nur Werte mit Plus. Leer heisst Bargeld."""
    if top_n < 1:
        raise ValueError("top_n muss mindestens 1 sein.")
    valid = scores.dropna()
    if cash_filter:
        valid = valid[valid > 0]
    valid = valid.sort_values(ascending=False, kind="stable")
    return [str(t) for t in valid.index[:top_n]]


def run_momentum_backtest(
    closes: pd.DataFrame,
    lookback_months: int = 12,
    top_n: int = 1,
    cash_filter: bool = True,
    fee_rate: float = 0.005,
    initial_cash: float = 10_000.0,
) -> MomentumResult:
    """Simuliert die Rotation.

    Entscheidung am Monatsende t, Ausführung zum Schlusskurs des nächsten Handelstags.
    Gleichgewichtung, Gebühr auf das gehandelte Volumen, kein Umschichten ohne Änderung.
    """
    closes = closes.astype(float).sort_index().dropna()
    if closes.empty:
        raise ValueError("Keine gemeinsamen Kursdaten für den Test vorhanden.")
    dates = closes.index
    n = len(dates)
    columns = list(closes.columns)
    prices = closes.to_numpy()

    # Entscheidungen: Ausführungsposition -> Auswahl. Ausgeführt wird am nächsten Handelstag.
    plan: dict[int, list[str]] = {}
    for end in month_end_dates(dates):
        pos = dates.get_loc(end)
        if pos + 1 >= n:
            break
        scores = momentum_scores(closes, lookback_months, end)
        if scores.isna().all():
            continue
        plan[pos + 1] = choose(scores, top_n, cash_filter)

    shares = np.zeros(len(columns))
    cash = float(initial_cash)
    holdings: frozenset[str] = frozenset()
    previous: frozenset[str] | None = None
    total_fees = 0.0
    values = np.empty(n)
    rebalance_rows = []

    for k in range(n):
        if k in plan:
            selection = plan[k]
            new = frozenset(selection)
            if new != holdings:
                price = prices[k]
                total = cash + float(shares @ price)
                target_shares = np.zeros(len(columns))
                if new:
                    per_ticker = total / len(new)
                    for ticker in new:
                        idx = columns.index(ticker)
                        target_shares[idx] = per_ticker / price[idx]
                traded_volume = float((np.abs(target_shares - shares) * price).sum())
                fee = fee_rate * traded_volume
                cash = total - float((target_shares * price).sum()) - fee
                shares = target_shares
                total_fees += fee
                holdings = new

            changed = previous is not None and new != previous
            rebalance_rows.append(
                {
                    "date": dates[k],
                    "holdings": " + ".join(selection) if selection else "Bargeld",
                    "changed": changed,
                }
            )
            previous = new

        values[k] = cash + float(shares @ prices[k])

    equity = pd.Series(values, index=dates, name="Momentum")
    rebalances = pd.DataFrame(rebalance_rows, columns=["date", "holdings", "changed"])
    num_changed = int(rebalances["changed"].sum()) if not rebalances.empty else 0

    metrics = {
        "total_return": float(equity.iloc[-1] / initial_cash - 1),
        "cagr": _cagr(equity, initial_cash),
        "max_drawdown": _max_drawdown(equity),
        "num_rebalances_changed": num_changed,
        "total_fees": float(total_fees),
    }
    return MomentumResult(equity=equity, rebalances=rebalances, metrics=metrics)


def equal_weight_buy_and_hold(closes: pd.DataFrame, initial_cash: float) -> pd.Series:
    """Am ersten Tag gleich verteilt kaufen und nie umschichten. Ohne Gebühr."""
    closes = closes.astype(float).sort_index().dropna()
    equity = initial_cash * (closes / closes.iloc[0]).mean(axis=1)
    equity.name = "Kaufen & Halten (alle gleich)"
    return equity


def current_ranking(
    closes: pd.DataFrame,
    lookback_months: int = 12,
    top_n: int = 1,
    cash_filter: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """Rangliste mit dem letzten verfügbaren Tag als Stichtag, plus die aktuelle Auswahl."""
    closes = closes.astype(float).sort_index().dropna()
    as_of = closes.index[-1]
    scores = momentum_scores(closes, lookback_months, as_of)
    table = (
        pd.DataFrame({"Ticker": scores.index, "Rendite": scores.to_numpy()})
        .sort_values("Rendite", ascending=False, na_position="last", kind="stable")
        .reset_index(drop=True)
    )
    return table, choose(scores, top_n, cash_filter)


def _cagr(equity: pd.Series, initial_cash: float) -> float:
    days = (equity.index[-1] - equity.index[0]).days
    years = days / 365.25
    final_value = float(equity.iloc[-1])
    if years <= 0 or final_value <= 0:
        return 0.0
    return float((final_value / initial_cash) ** (1 / years) - 1)


def _max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min())
