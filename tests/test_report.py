import numpy as np
import pandas as pd

from trader.report import (
    PRESETS,
    buy_and_hold_equity,
    explain_metrics,
    fmt_number,
    fmt_pct,
    verdict,
)


def make_prices(closes: list[float]) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=len(closes), freq="B")
    return pd.DataFrame({"Close": np.array(closes, dtype=float)}, index=index)


def make_metrics(**overrides) -> dict:
    metrics = {
        "total_return": 1.62,
        "cagr": 0.085,
        "max_drawdown": -0.278,
        "sharpe": 0.9,
        "num_trades": 53,
        "buy_and_hold_return": 1.9,
    }
    metrics.update(overrides)
    return metrics


def test_buy_and_hold_starts_at_initial_cash():
    equity = buy_and_hold_equity(make_prices([100.0, 110.0, 90.0]), 10_000.0)
    assert equity.iloc[0] == 10_000.0
    assert equity.name == "Kaufen & Halten"


def test_buy_and_hold_matches_price_ratio():
    equity = buy_and_hold_equity(make_prices([50.0, 75.0, 25.0]), 1_000.0)
    assert equity.tolist() == [1_000.0, 1_500.0, 500.0]


def test_verdict_bad_when_money_lost():
    level, text = verdict(make_metrics(total_return=-0.1, buy_and_hold_return=-0.2))
    assert level == "bad"
    assert text == "Die Strategie hätte Geld verloren."


def test_verdict_good_when_better_than_buy_and_hold():
    level, text = verdict(make_metrics(total_return=0.5, buy_and_hold_return=0.3))
    assert level == "good"
    assert text == "Die Strategie war besser als einfach Kaufen & Halten."


def test_verdict_neutral_when_gain_but_worse_than_buy_and_hold():
    level, text = verdict(make_metrics(total_return=0.1, buy_and_hold_return=0.3))
    assert level == "neutral"
    assert text == (
        "Die Strategie hat Gewinn gemacht, aber einfach Kaufen & Halten wäre besser gewesen."
    )


def test_explain_metrics_returns_sentences_with_swiss_thousands():
    sentences = explain_metrics(make_metrics(), 10_000.0, 26_196.3)
    assert 4 <= len(sentences) <= 5
    assert all(isinstance(s, str) for s in sentences)
    assert sentences[0] == "Aus 10'000 wären 26'196 geworden (+162.0 %)."
    assert sentences[1] == "Pro Jahr im Schnitt +8.5 %."
    assert sentences[2] == (
        "Im schlimmsten Moment lag das Konto 27.8 % unter seinem Höchststand."
    )
    assert sentences[3] == "Die Strategie hat 53 Mal gekauft oder verkauft."


def test_fmt_pct_has_no_negative_zero():
    assert fmt_pct(-0.00001, signed=False) == "0.0 %"


def test_fmt_number_uses_apostrophe():
    assert fmt_number(1_234_567.8, decimals=2) == "1'234'567.80"
    assert fmt_number(500.0, signed=True) == "+500"


def test_presets_fast_is_smaller_than_slow():
    for name, (fast, slow) in PRESETS.items():
        assert fast < slow, name
