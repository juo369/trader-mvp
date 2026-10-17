import socket
from pathlib import Path

from trader import launch, shortcut


def test_is_running_detects_open_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]
        assert launch.is_running(port)
    assert not launch.is_running(port)


def test_server_command_runs_app_headless_on_fixed_port():
    cmd = launch.server_command()
    assert cmd[1:4] == ["-m", "streamlit", "run"]
    assert cmd[4].endswith("app.py")
    assert "--server.headless" in cmd and "true" in cmd
    assert str(launch.PORT) in cmd


def test_main_only_opens_browser_when_already_running(monkeypatch):
    opened, started = [], []
    monkeypatch.setattr(launch, "is_running", lambda port=launch.PORT: True)
    monkeypatch.setattr(launch, "start_server", lambda: started.append(True))
    monkeypatch.setattr(launch.webbrowser, "open", opened.append)
    assert launch.main() == 0
    assert opened == [launch.URL]
    assert started == []


def test_main_starts_server_and_waits(monkeypatch):
    states = iter([False, False, True])
    started, opened = [], []
    monkeypatch.setattr(launch, "is_running", lambda port=launch.PORT: next(states))
    monkeypatch.setattr(launch, "start_server", lambda: started.append(True))
    monkeypatch.setattr(launch.time, "sleep", lambda s: None)
    monkeypatch.setattr(launch.webbrowser, "open", opened.append)
    assert launch.main() == 0
    assert started == [True]
    assert opened == [launch.URL]


def test_shortcut_script_points_to_pythonw_and_launcher():
    script = shortcut.build_script(Path(r"C:\Users\o'neil\trader"), Path(r"C:\x\.venv\Scripts"))
    assert "pythonw.exe" in script
    assert "-m trader.launch" in script
    assert "'C:\\Users\\o''neil\\trader'" in script
    assert "Trader MVP.lnk" in script
