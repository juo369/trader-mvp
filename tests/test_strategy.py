import numpy as np
import pandas as pd
import pytest

from trader.strategy import SmaCrossover


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
