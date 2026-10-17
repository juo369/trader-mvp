import json

import pytest

from trader.broker import PaperBroker


def test_buy_updates_cash_and_positions_including_fee(tmp_path):
    broker = PaperBroker(state_file=str(tmp_path / "acc.json"), initial_cash=10_000.0, fee_rate=0.001)
    broker.buy("SPY", 10, 100.0)

    assert broker.positions == {"SPY": 10}
    assert broker.cash == pytest.approx(10_000.0 - 1000.0 - 1.0)
    assert broker.order_log[-1]["side"] == "BUY"
    assert broker.order_log[-1]["fee"] == pytest.approx(1.0)


def test_sell_updates_cash_and_positions_including_fee(tmp_path):
    broker = PaperBroker(state_file=str(tmp_path / "acc.json"), initial_cash=10_000.0, fee_rate=0.001)
    broker.buy("SPY", 10, 100.0)
    broker.sell("SPY", 4, 110.0)

    assert broker.positions == {"SPY": 6}
    assert broker.cash == pytest.approx(8999.0 + 440.0 - 0.44)


def test_sell_all_removes_position(tmp_path):
    broker = PaperBroker(state_file=str(tmp_path / "acc.json"))
    broker.buy("SPY", 5, 100.0)
    broker.sell("SPY", 5, 100.0)
    assert "SPY" not in broker.positions


def test_buy_with_insufficient_cash_raises(tmp_path):
    broker = PaperBroker(state_file=str(tmp_path / "acc.json"), initial_cash=1_000.0)
    with pytest.raises(ValueError):
        broker.buy("SPY", 100, 100.0)
    assert broker.cash == pytest.approx(1_000.0)


def test_sell_more_than_held_raises(tmp_path):
    broker = PaperBroker(state_file=str(tmp_path / "acc.json"))
    broker.buy("SPY", 2, 100.0)
    with pytest.raises(ValueError):
        broker.sell("SPY", 3, 100.0)


def test_non_positive_shares_raise(tmp_path):
    broker = PaperBroker(state_file=str(tmp_path / "acc.json"))
    with pytest.raises(ValueError):
        broker.buy("SPY", 0, 100.0)
    with pytest.raises(ValueError):
        broker.sell("SPY", -1, 100.0)


def test_save_and_load_roundtrip(tmp_path):
    state = tmp_path / "sub" / "acc.json"
    broker = PaperBroker(state_file=str(state))
    broker.buy("SPY", 3, 50.0)
    broker.save()

    assert state.exists()
    json.loads(state.read_text(encoding="utf-8"))

    loaded = PaperBroker(state_file=str(state))
    assert loaded.cash == pytest.approx(broker.cash)
    assert loaded.positions == broker.positions
    assert loaded.order_log == broker.order_log


def test_equity_uses_current_prices(tmp_path):
    broker = PaperBroker(state_file=str(tmp_path / "acc.json"), initial_cash=1_000.0, fee_rate=0.0)
    broker.buy("SPY", 5, 100.0)
    assert broker.equity({"SPY": 120.0}) == pytest.approx(500.0 + 600.0)
