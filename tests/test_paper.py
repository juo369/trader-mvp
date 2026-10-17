import numpy as np
import pandas as pd
import pytest

from trader.broker import PaperBroker
from trader.paper import run_paper_step
from trader.strategy import Strategy


class DummyStrategy(Strategy):
    """Liefert konstant ein vorgegebenes Signal."""

    def __init__(self, value: int):
        self.value = value

    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        return pd.Series(self.value, index=prices.index)


def make_prices(n: int = 30) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=n, freq="B")
    return pd.DataFrame({"Close": np.full(n, 100.0)}, index=index)


def test_signal_one_buys_with_all_cash(tmp_path):
    broker = PaperBroker(state_file=str(tmp_path / "acc.json"), initial_cash=1_000.0, fee_rate=0.001)
    action = run_paper_step(DummyStrategy(1), "SPY", broker, make_prices(), 100.0)

    # Bruchteile erlaubt: 1000 / (100 * 1.001) = 9.99001 Anteile (auf 6 Stellen abgerundet)
    assert action == "BUY 9.99001 SPY @ 100.00"
    assert broker.positions == {"SPY": pytest.approx(9.99001)}
    assert broker.cash == pytest.approx(0.0, abs=0.01)
    assert (tmp_path / "acc.json").exists()


def test_signal_one_with_position_holds(tmp_path):
    broker = PaperBroker(state_file=str(tmp_path / "acc.json"), initial_cash=1_000.0)
    run_paper_step(DummyStrategy(1), "SPY", broker, make_prices(), 100.0)
    action = run_paper_step(DummyStrategy(1), "SPY", broker, make_prices(), 100.0)
    assert action == "HOLD"


def test_signal_zero_sells_position(tmp_path):
    broker = PaperBroker(state_file=str(tmp_path / "acc.json"), initial_cash=1_000.0)
    run_paper_step(DummyStrategy(1), "SPY", broker, make_prices(), 100.0)

    action = run_paper_step(DummyStrategy(0), "SPY", broker, make_prices(), 110.0)
    assert action == "SELL 9.99001 SPY @ 110.00"
    assert "SPY" not in broker.positions
    assert broker.cash > 1_000.0 - 10.0  # Gewinn abzüglich Gebühr


def test_signal_zero_without_position_holds(tmp_path):
    broker = PaperBroker(state_file=str(tmp_path / "acc.json"))
    assert run_paper_step(DummyStrategy(0), "SPY", broker, make_prices(), 100.0) == "HOLD"
