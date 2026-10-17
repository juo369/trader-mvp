"""Startet die App ohne sichtbares Fenster und öffnet den Browser.

Läuft die App schon, wird nur der Browser geöffnet. Gedacht für die Desktop-Verknüpfung
(siehe trader/shortcut.py), funktioniert aber auch direkt: python -m trader.launch
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PORT = 8501
URL = f"http://localhost:{PORT}"
REPO_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = REPO_DIR / "app.log"


def is_running(port: int = PORT) -> bool:
    """True, wenn auf dem Port schon ein Server antwortet."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def console_python() -> str:
    """python.exe statt pythonw.exe: Streamlit braucht eine normale Ausgabe (geht ins Log)."""
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        candidate = exe.with_name("python.exe")
        if candidate.exists():
            return str(candidate)
    return str(exe)


def server_command() -> list[str]:
    return [
        console_python(),
        "-m",
        "streamlit",
        "run",
        str(REPO_DIR / "app.py"),
        "--server.headless",
        "true",
        "--server.port",
        str(PORT),
    ]


def start_server() -> None:
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    log = open(LOG_FILE, "a", encoding="utf-8")
    subprocess.Popen(
        server_command(),
        cwd=REPO_DIR,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
    )


def main(timeout: float = 60.0) -> int:
    if not is_running():
        start_server()
        deadline = time.monotonic() + timeout
        while not is_running():
            if time.monotonic() > deadline:
                return 1
            time.sleep(0.5)
    webbrowser.open(URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
