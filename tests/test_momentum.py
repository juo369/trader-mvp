import numpy as np
import pandas as pd
import pytest

from trader.momentum import (
    UNIVERSES,
    choose,
    current_ranking,
    equal_weight_buy_and_hold,
    load_universe,
    month_end_dates,
    momentum_scores,
    run_momentum_backtest,
)


def make_closes(columns: dict[str, np.ndarray], start="2020-01-01") -> pd.DataFrame:
    length = len(next(iter(columns.values())))
    index = pd.bdate_range(start, periods=length)
    return pd.DataFrame(columns, index=index)


def three_years_rising_and_falling():
    """Zwei synthetische Reihen über rund 3 Jahre: A steigt stark, B fällt."""
    days = pd.bdate_range("2020-01-01", "2022-12-31")
    t = np.arange(len(days))
    a = 100 * (1.001 ** t)
    b = 100 * (0.9995 ** t)
    return pd.DataFrame({"A": a, "B": b}, index=days)


def test_month_end_dates_picks_last_trading_day_per_month():
    index = pd.DatetimeIndex(
        ["2021-01-04", "2021-01-29", "2021-02-01", "2021-02-26", "2021-03-31"]
    )
    ends = month_end_dates(index)
    assert list(ends) == [
        pd.Timestamp("2021-01-29"),
        pd.Timestamp("2021-02-26"),
        pd.Timestamp("2021-03-31"),
    ]


def test_momentum_scores_use_month_end_prices():
    index = pd.bdate_range("2020-01-01", "2020-12-31")
    # Preis ist je Monat konstant: Monat m (0 = Januar) hat den Wert 100 + m.
    month_offset = index.month - 1
    closes = pd.DataFrame({"X": 100.0 + month_offset.astype(float)}, index=index)

    scores = momentum_scores(closes, lookback_months=2, as_of=pd.Timestamp("2020-06-30"))
    # Juni (Index 5) gegen April (Index 3): 105 / 103 - 1
    assert scores["X"] == pytest.approx(105 / 103 - 1)


def test_momentum_scores_nan_without_enough_history():
    closes = make_closes({"X": np.linspace(100, 110, 60)}, start="2020-01-01")
    scores = momentum_scores(closes, lookback_months=12, as_of=closes.index[-1])
    assert scores.isna().all()


def test_choose_takes_top_n_and_ignores_nan():
    scores = pd.Series({"A": 0.1, "B": np.nan, "C": 0.3, "D": 0.2})
    assert choose(scores, top_n=2, cash_filter=True) == ["C", "D"]
    assert choose(scores, top_n=1, cash_filter=True) == ["C"]


def test_choose_cash_filter_gives_empty_list_when_all_negative():
    scores = pd.Series({"A": -0.1, "B": -0.2})
    assert choose(scores, top_n=1, cash_filter=True) == []
    assert choose(scores, top_n=1, cash_filter=False) == ["A"]


def test_backtest_holds_rising_series_and_makes_money():
    closes = three_years_rising_and_falling()
    result = run_momentum_backtest(closes, lookback_months=6, top_n=1, cash_filter=True)

    assert result.rebalances.iloc[-1]["holdings"] == "A"
    assert result.metrics["total_return"] > 0
    assert result.equity.iloc[-1] > 10_000.0


def test_backtest_stays_in_cash_before_enough_history():
    closes = three_years_rising_and_falling()
    result = run_momentum_backtest(closes, lookback_months=12, top_n=1, cash_filter=True)

    first_execution_day = result.rebalances["date"].iloc[0]
    before = result.equity[result.equity.index < first_execution_day]
    assert (before == 10_000.0).all()
    # Ein 12-Monate-Score braucht Kurse von Januar 2020: die erste Entscheidung ist Ende Januar 2021,
    # ausgeführt wird am 1. Februar 2021.
    assert first_execution_day == pd.Timestamp("2021-02-01")


def test_backtest_executes_on_day_after_month_end():
    closes = three_years_rising_and_falling()
    fee_rate = 0.005
    result = run_momentum_backtest(
        closes, lookback_months=6, top_n=1, cash_filter=True, fee_rate=fee_rate
    )

    first = result.rebalances["date"].iloc[0]
    position = closes.index.get_loc(first)
    month_end = closes.index[position - 1]
    # Der Tag vor der Ausführung ist das Monatsende; am Monatsende selbst wird noch nichts gekauft.
    assert month_end.month != first.month
    assert result.equity.loc[month_end] == 10_000.0
    # Ausgeführt zum Schlusskurs des Ausführungstags: danach bleibt nur das Geld abzüglich Gebühr.
    assert result.equity.loc[first] == pytest.approx(10_000.0 * (1 - fee_rate))


def test_unchanged_selection_causes_no_extra_fees():
    closes = three_years_rising_and_falling()
    result = run_momentum_backtest(
        closes, lookback_months=6, top_n=1, cash_filter=True, fee_rate=0.01
    )

    # A bleibt über die ganze Zeit gewählt: nur der erste Kauf (10'000 Volumen) kostet Gebühr.
    assert (result.rebalances["holdings"] == "A").all()
    assert result.metrics["num_rebalances_changed"] == 0
    assert result.metrics["total_fees"] == pytest.approx(0.01 * 10_000)


def test_all_falling_with_cash_filter_keeps_initial_cash():
    days = pd.bdate_range("2020-01-01", "2022-12-31")
    t = np.arange(len(days))
    closes = pd.DataFrame(
        {"A": 100 * (0.999 ** t), "B": 100 * (0.998 ** t)}, index=days
    )
    result = run_momentum_backtest(closes, lookback_months=3, top_n=2, cash_filter=True)

    assert (result.equity == 10_000.0).all()
    assert result.metrics["total_fees"] == 0.0
    assert (result.rebalances["holdings"] == "Bargeld").all()


def test_equal_weight_buy_and_hold_starts_with_initial_cash():
    closes = three_years_rising_and_falling()
    equity = equal_weight_buy_and_hold(closes, initial_cash=10_000.0)

    assert equity.iloc[0] == pytest.approx(10_000.0)
    expected_last = 10_000.0 * np.mean(closes.iloc[-1] / closes.iloc[0])
    assert equity.iloc[-1] == pytest.approx(expected_last)


def test_load_universe_skips_failing_ticker():
    days = pd.bdate_range("2020-01-01", periods=30)

    def fake_loader(ticker, start):
        if ticker == "BROKEN":
            raise RuntimeError("Netz weg")
        return pd.DataFrame({"Close": np.arange(1, 31, dtype=float)}, index=days)

    closes, skipped = load_universe(["AAA", "BROKEN", "BBB"], "2020-01-01", loader=fake_loader)

    assert skipped == ["BROKEN"]
    assert list(closes.columns) == ["AAA", "BBB"]
    assert len(closes) == 30


def test_load_universe_keeps_only_common_days():
    full = pd.bdate_range("2020-01-01", periods=10)
    short = full[:7]

    def fake_loader(ticker, start):
        index = full if ticker == "AAA" else short
        return pd.DataFrame({"Close": np.ones(len(index))}, index=index)

    closes, skipped = load_universe(["AAA", "BBB"], "2020-01-01", loader=fake_loader)
    assert skipped == []
    assert len(closes) == 7


def test_load_universe_raises_when_fewer_than_two_tickers_remain():
    days = pd.bdate_range("2020-01-01", periods=10)

    def fake_loader(ticker, start):
        if ticker != "AAA":
            raise RuntimeError("nicht verfügbar")
        return pd.DataFrame({"Close": np.ones(10)}, index=days)

    with pytest.raises(ValueError, match="mindestens 2"):
        load_universe(["AAA", "BBB"], "2020-01-01", loader=fake_loader)


def test_load_universe_raises_without_common_days():
    first = pd.bdate_range("2020-01-01", periods=5)
    second = pd.bdate_range("2021-01-01", periods=5)

    def fake_loader(ticker, start):
        index = first if ticker == "AAA" else second
        return pd.DataFrame({"Close": np.ones(5)}, index=index)

    with pytest.raises(ValueError, match="gemeinsamen Handelstage"):
        load_universe(["AAA", "BBB"], "2020-01-01", loader=fake_loader)


def test_current_ranking_sorted_descending():
    closes = three_years_rising_and_falling()
    closes["C"] = 100 * (1.0 + 0.0005 * np.arange(len(closes)))
    table, selection = current_ranking(closes, lookback_months=6, top_n=1, cash_filter=True)

    returns = table["Rendite"].tolist()
    assert returns == sorted(returns, reverse=True)
    assert list(table.columns) == ["Ticker", "Rendite"]
    assert selection == [table["Ticker"].iloc[0]]


def test_universes_have_expected_lists():
    assert UNIVERSES["Krypto"] == ["BTC-USD", "ETH-USD"]
    assert "SPY" in UNIVERSES["Weltweite ETFs (Aktien, Anleihen, Gold)"]
