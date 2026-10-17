import numpy as np
import pandas as pd
import pytest

from trader.strategy import PriceAboveSma, SmaCrossover


def make_prices(close):
    index = pd.date_range("2020-01-01", periods=len(close), freq="B")
    return pd.DataFrame({"Close": close}, index=index)


def test_signals_only_zero_or_one():
    rng = np.random.default_rng(1)
    prices = make_prices(100 + np.cumsum(rng.normal(0, 1, 200)))
    signals = SmaCrossover(fast=5, slow=20).generate_signals(prices)
    assert set(signals.unique()) <= {0, 1}
    assert signals.index.equals(prices.index)


def test_warmup_phase_is_flat():
    prices = make_prices(np.arange(1.0, 61.0))
    signals = SmaCrossover(fast=5, slow=20).generate_signals(prices)
    assert (signals.iloc[:19] == 0).all()


def test_fast_not_smaller_than_slow_raises():
    with pytest.raises(ValueError):
        SmaCrossover(fast=50, slow=20)
    with pytest.raises(ValueError):
        SmaCrossover(fast=20, slow=20)


def test_price_above_sma_signals_only_zero_or_one():
    rng = np.random.default_rng(2)
    prices = make_prices(100 + np.cumsum(rng.normal(0, 1, 200)))
    signals = PriceAboveSma(window=20).generate_signals(prices)
    assert set(signals.unique()) <= {0, 1}
    assert signals.index.equals(prices.index)


def test_price_above_sma_is_flat_during_warmup():
    prices = make_prices(np.arange(1.0, 61.0))
    signals = PriceAboveSma(window=20).generate_signals(prices)
    assert (signals.iloc[:19] == 0).all()


def test_price_above_sma_is_long_in_rising_series():
    prices = make_prices(np.arange(1.0, 61.0))
    signals = PriceAboveSma(window=20).generate_signals(prices)
    assert (signals.iloc[19:] == 1).all()


def test_price_above_sma_window_below_two_raises():
    with pytest.raises(ValueError):
        PriceAboveSma(window=1)
    with pytest.raises(ValueError):
        PriceAboveSma(window=0)
