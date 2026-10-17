import numpy as np
import pandas as pd
import pytest

from trader import data


def _fake_download(close_values):
    index = pd.date_range("2020-01-01", periods=len(close_values), freq="D")
    frame = pd.DataFrame(
        {col: close_values for col in ["Open", "High", "Low", "Close"]} | {"Volume": 1},
        index=index,
    )
    return lambda *args, **kwargs: frame


def test_load_prices_drops_days_without_close(monkeypatch, tmp_path):
    monkeypatch.setattr(data.yf, "download", _fake_download([np.nan, np.nan, 10.0, 11.0]))
    df = data.load_prices("BTC", "2020-01-01", cache_dir=str(tmp_path))
    assert len(df) == 2
    assert df["Close"].notna().all()


def test_load_prices_all_nan_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(data.yf, "download", _fake_download([np.nan, np.nan]))
    with pytest.raises(ValueError):
        data.load_prices("BTC", "2020-01-01", cache_dir=str(tmp_path))
