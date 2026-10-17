from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

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
    assert len(at.tabs) == 4


def test_app_does_not_write_files_on_start(app_in_tmp_dir):
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)

    assert not (app_in_tmp_dir / "paper_state").exists()


def test_fee_inputs_default_to_yuh_fee(app_in_tmp_dir):
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=30)
    assert at.number_input(key="backtest_fee").value == 0.5
    assert at.number_input(key="account_fee").value == 0.5
