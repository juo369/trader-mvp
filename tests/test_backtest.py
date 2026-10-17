import numpy as np
import pandas as pd

from trader.backtest import run_backtest


def make_prices(close):
    close = np.asarray(close, dtype=float)
    index = pd.date_range("2020-01-01", periods=len(close), freq="B")
    return pd.DataFrame(
        {
            "Open": close,
            "High": close,
            "Low": close,
            "Close": close,
            "Volume": 1_000_000,
        },
        index=index,
    )


def test_constant_prices_flat_signal_keeps_equity():
    prices = make_prices(np.full(50, 100.0))
    signals = pd.Series(0, index=prices.index)
    result = run_backtest(prices, signals, initial_cash=10_000.0)
    assert (result.equity == 10_000.0).all()
    assert result.metrics["num_trades"] == 0


def test_rising_prices_always_long_gives_positive_return():
    prices = make_prices(np.linspace(100.0, 200.0, 100))
    signals = pd.Series(1, index=prices.index)
    result = run_backtest(prices, signals)
    assert result.metrics["total_return"] > 0


def test_no_lookahead_trade_happens_day_after_signal():
    prices = make_prices(np.linspace(100.0, 150.0, 60))
    signals = pd.Series(0, index=prices.index)
    k = 10
    signals.iloc[k] = 1
    signals.iloc[k + 1 :] = 1

    result = run_backtest(prices, signals)

    assert not result.trades.empty
    first = result.trades.iloc[0]
    assert first["side"] == "BUY"
    assert pd.Timestamp(first["date"]) == prices.index[k + 1]


def test_max_drawdown_not_positive():
    rng = np.random.default_rng(2)
    prices = make_prices(100 + np.cumsum(rng.normal(0, 2, 300)))
    signals = pd.Series(1, index=prices.index)
    result = run_backtest(prices, signals)
    assert result.metrics["max_drawdown"] <= 0
