"""Strategie-Finder: Einstellungen in der Lernzeit suchen, in der Prüfzeit ehrlich testen.

Die Lernzeit sind die ersten Handelstage, die Prüfzeit die letzten. Der Sieger aus der
Lernzeit wird nur einmal an der Prüfzeit getestet, die er beim Suchen nicht kannte.
Reine Logik ohne Streamlit und ohne Netzwerk, damit sie testbar bleibt.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from trader.backtest import BacktestResult, run_backtest
from trader.report import buy_and_hold_equity
from trader.strategy import PriceAboveSma, SmaCrossover, Strategy

FAST_WINDOWS = [5, 10, 20, 30, 50]
SLOW_WINDOWS = [20, 50, 100, 150, 200]
PRICE_WINDOWS = [20, 50, 100, 150, 200]
MIN_ROWS_PER_PERIOD = 30


@dataclass
class Candidate:
    label: str
    strategy: Strategy


def default_candidates() -> list[Candidate]:
    """Alle Einstellungen, die der Finder durchprobiert."""
    candidates = [
        Candidate(f"Durchschnitte {fast}/{slow}", SmaCrossover(fast=fast, slow=slow))
        for fast in FAST_WINDOWS
        for slow in SLOW_WINDOWS
        if fast < slow
    ]
    candidates += [
        Candidate(f"Kurs über {window}-Tage-Schnitt", PriceAboveSma(window=window))
        for window in PRICE_WINDOWS
    ]
    return candidates


def split_index(
    prices: pd.DataFrame, train_fraction: float = 0.7
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    """Teilt die Zeilen in Lernzeit (vorne) und Prüfzeit (hinten)."""
    cut = int(len(prices.index) * train_fraction)
    train_index = prices.index[:cut]
    test_index = prices.index[cut:]
    if len(train_index) < MIN_ROWS_PER_PERIOD or len(test_index) < MIN_ROWS_PER_PERIOD:
        raise ValueError(
            "Der Zeitraum ist zu kurz für Lernzeit und Prüfzeit "
            f"(je mindestens {MIN_ROWS_PER_PERIOD} Handelstage). "
            "Wähle ein früheres Startjahr."
        )
    return train_index, test_index


def evaluate(
    prices: pd.DataFrame,
    candidate: Candidate,
    index: pd.DatetimeIndex,
    fee_rate: float,
    initial_cash: float,
) -> BacktestResult:
    """Testet eine Einstellung auf dem Zeitraum index.

    Die Signale werden auf dem ganzen Verlauf berechnet, damit die Durchschnitte am Anfang
    des Zeitraums schon "warm" sind. Das ist ohne Lookahead, weil ein SMA nur die Vergangenheit nutzt.
    """
    signals = candidate.strategy.generate_signals(prices)
    return run_backtest(
        prices.loc[index],
        signals.loc[index],
        initial_cash=initial_cash,
        fee_rate=fee_rate,
    )


def grid_search(
    prices: pd.DataFrame,
    index: pd.DatetimeIndex,
    candidates: list[Candidate],
    fee_rate: float,
    initial_cash: float,
) -> pd.DataFrame:
    """Testet alle Einstellungen auf index, bestes Ergebnis zuerst."""
    rows = []
    for candidate in candidates:
        result = evaluate(prices, candidate, index, fee_rate, initial_cash)
        rows.append(
            {
                "label": candidate.label,
                "total_return": result.metrics["total_return"],
                "max_drawdown": result.metrics["max_drawdown"],
                "num_trades": result.metrics["num_trades"],
                "buy_and_hold_return": result.metrics["buy_and_hold_return"],
            }
        )
    table = pd.DataFrame(
        rows,
        columns=[
            "label",
            "total_return",
            "max_drawdown",
            "num_trades",
            "buy_and_hold_return",
        ],
    )
    return table.sort_values("total_return", ascending=False).reset_index(drop=True)


def walk_forward(
    prices: pd.DataFrame,
    fee_rate: float = 0.005,
    initial_cash: float = 10_000.0,
    train_fraction: float = 0.7,
    candidates: list[Candidate] | None = None,
) -> dict:
    """Sucht den Sieger in der Lernzeit und testet ihn danach in der Prüfzeit."""
    if candidates is None:
        candidates = default_candidates()

    train_index, test_index = split_index(prices, train_fraction)
    ranking = grid_search(prices, train_index, candidates, fee_rate, initial_cash)
    best_label = str(ranking.iloc[0]["label"])
    best = next(c for c in candidates if c.label == best_label)

    return {
        "train_period": (train_index[0], train_index[-1]),
        "test_period": (test_index[0], test_index[-1]),
        "ranking": ranking,
        "best_label": best_label,
        "train_result": evaluate(prices, best, train_index, fee_rate, initial_cash),
        "test_result": evaluate(prices, best, test_index, fee_rate, initial_cash),
        "test_buy_and_hold_equity": buy_and_hold_equity(
            prices.loc[test_index], initial_cash
        ),
    }
