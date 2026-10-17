import numpy as np
import pandas as pd
import pytest

from trader.optimize import (
    Candidate,
    default_candidates,
    grid_search,
    split_index,
    walk_forward,
)
from trader.strategy import SmaCrossover

INITIAL_CASH = 10_000.0
EXPECTED_SMA_COMBOS = 21  # fast in [5, 10, 20, 30, 50], slow in [20, 50, 100, 150, 200], fast < slow
EXPECTED_PRICE_WINDOWS = 5  # window in [20, 50, 100, 150, 200]


def make_prices(days=600, seed=3):
    """Synthetische Kurse: Aufwärtstrend mit Sinus-Welle und etwas Rauschen."""
    rng = np.random.default_rng(seed)
    t = np.arange(days)
    close = 100 + 0.05 * t + 8 * np.sin(t / 15) + rng.normal(0, 0.5, days)
    index = pd.date_range("2018-01-01", periods=days, freq="B")
    return pd.DataFrame({"Close": close}, index=index)


def test_default_candidates_count_and_labels():
    candidates = default_candidates()
    assert len(candidates) == EXPECTED_SMA_COMBOS + EXPECTED_PRICE_WINDOWS
    labels = [c.label for c in candidates]
    assert len(set(labels)) == len(labels)


def test_split_index_is_70_30_without_overlap():
    prices = make_prices(600)
    train, test = split_index(prices)
    assert len(train) == 420
    assert len(test) == 180
    assert len(set(train) & set(test)) == 0
    assert test[0] > train[-1]
    assert train[0] == prices.index[0]
    assert test[-1] == prices.index[-1]


def test_split_index_too_short_raises():
    prices = make_prices(50)
    with pytest.raises(ValueError, match="zu kurz"):
        split_index(prices)


def test_grid_search_is_sorted_descending():
    prices = make_prices(600)
    train, _ = split_index(prices)
    ranking = grid_search(prices, train, default_candidates(), 0.005, INITIAL_CASH)
    assert list(ranking.columns) == [
        "label",
        "total_return",
        "max_drawdown",
        "num_trades",
        "buy_and_hold_return",
    ]
    assert len(ranking) == EXPECTED_SMA_COMBOS + EXPECTED_PRICE_WINDOWS
    assert ranking.index.tolist() == list(range(len(ranking)))
    assert ranking["total_return"].is_monotonic_decreasing


def test_walk_forward_returns_all_keys():
    result = walk_forward(make_prices(600), fee_rate=0.005, initial_cash=INITIAL_CASH)
    assert set(result) == {
        "train_period",
        "test_period",
        "ranking",
        "best_label",
        "train_result",
        "test_result",
        "test_buy_and_hold_equity",
    }


def test_walk_forward_test_equity_starts_with_initial_cash():
    prices = make_prices(600)
    result = walk_forward(prices, fee_rate=0.005, initial_cash=INITIAL_CASH)
    _, test_index = split_index(prices)

    equity = result["test_result"].equity
    assert equity.index[0] == test_index[0]
    # Am ersten Prüftag wird nichts gekauft (Signal kommt erst am Folgetag), daher ist der Startwert exakt.
    assert equity.iloc[0] == pytest.approx(INITIAL_CASH, rel=0.005)

    bh = result["test_buy_and_hold_equity"]
    assert bh.index.equals(test_index)
    assert bh.iloc[0] == pytest.approx(INITIAL_CASH)


def test_walk_forward_periods_and_best_label():
    prices = make_prices(600)
    result = walk_forward(prices, fee_rate=0.005, initial_cash=INITIAL_CASH)
    train, test = split_index(prices)

    assert result["train_period"] == (train[0], train[-1])
    assert result["test_period"] == (test[0], test[-1])
    assert result["test_period"][0] > result["train_period"][1]
    assert result["best_label"] == result["ranking"].iloc[0]["label"]


def test_walk_forward_accepts_custom_candidates():
    candidates = [Candidate("Nur ein Test", SmaCrossover(fast=5, slow=20))]
    result = walk_forward(make_prices(600), candidates=candidates)
    assert result["best_label"] == "Nur ein Test"
    assert len(result["ranking"]) == 1
