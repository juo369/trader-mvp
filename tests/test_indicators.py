import numpy as np
import pandas as pd

from trader.indicators import rsi, sma


def test_sma_known_values():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = sma(s, 3)
    assert np.isnan(result.iloc[0])
    assert np.isnan(result.iloc[1])
    np.testing.assert_allclose(result.iloc[2:].values, [2.0, 3.0, 4.0])


def test_rsi_within_bounds():
    rng = np.random.default_rng(0)
    s = pd.Series(100 + np.cumsum(rng.normal(0, 1, 300)))
    result = rsi(s, 14).dropna()
    assert len(result) > 0
    assert (result >= 0).all()
    assert (result <= 100).all()


def test_rsi_rising_series_is_high():
    s = pd.Series(np.arange(1.0, 101.0))
    result = rsi(s, 14)
    assert result.iloc[-1] > 90


def test_rsi_flat_series_is_neutral():
    flat = pd.Series([100.0] * 30)
    values = rsi(flat, window=14).dropna()
    assert (values == 50.0).all()
