from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import trader.data

APP_PATH = Path(__file__).parent.parent / "app.py"


@pytest.fixture
def app_in_tmp_dir(tmp_path, monkeypatch):
    # Das Paper-Konto liegt relativ zum Arbeitsverzeichnis. Im tmp-Ordner bleibt das echte Konto unberührt.
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_app_starts_without_exception(app_in_tmp_dir):
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)

    assert not at.exception
    assert at.title[0].value == "📈 Mein Trading-Spielplatz"
    assert len(at.tabs) == 6


def test_finder_tab_exists_and_app_runs(app_in_tmp_dir):
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)

    assert not at.exception
    assert "🔍 Strategie-Finder" in [tab.label for tab in at.tabs]


def test_momentum_tab_exists_and_app_runs(app_in_tmp_dir):
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)

    assert not at.exception
    assert "🚀 Momentum" in [tab.label for tab in at.tabs]


def fake_load_prices(ticker, start, end=None, cache_dir="data/cache"):
    """Synthetische Kurse statt Yahoo. Jeder Ticker bekommt einen eigenen Trend."""
    days = pd.bdate_range(start, "2026-10-16")
    t = np.arange(len(days))
    drift = {"SPY": 1.0004, "QQQ": 1.0002, "EFA": 0.9999, "EEM": 0.9998, "TLT": 0.9997, "GLD": 1.0001}
    close = 100 * drift.get(ticker, 1.0) ** t
    return pd.DataFrame(
        {"Open": close, "High": close, "Low": close, "Close": close, "Volume": 1.0}, index=days
    )


def test_momentum_tab_runs_with_patched_loader(app_in_tmp_dir, monkeypatch):
    # Kein Netzwerk: load_prices wird im Trader-Paket durch synthetische Daten ersetzt.
    monkeypatch.setattr(trader.data, "load_prices", fake_load_prices)
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=60)

    at.button(key="mom_run").click().run(timeout=60)

    assert not at.exception
    assert len(at.error) == 0
    verdicts = list(at.success) + list(at.info) + list(at.warning)
    assert any("Momentum" in m.value for m in verdicts)
    labels = [m.label for m in at.metric]
    for label in ["Endwert", "Rendite Momentum", "Kaufen & Halten (alle gleich)",
                  "Grösster Einbruch", "Wechsel", "Gebühren gesamt"]:
        assert label in labels


def test_app_does_not_write_files_on_start(app_in_tmp_dir):
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)

    assert not (app_in_tmp_dir / "paper_state").exists()


def test_fee_inputs_default_to_yuh_fee(app_in_tmp_dir):
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)
    assert at.number_input(key="backtest_fee").value == 0.5
    assert at.number_input(key="account_fee").value == 0.5
