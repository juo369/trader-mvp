"""Legt auf dem Windows-Desktop eine Verknüpfung "Trader MVP" an.

Aufruf (einmalig, aus dem Projektordner): .venv\\Scripts\\python.exe -m trader.shortcut
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
SHORTCUT_NAME = "Trader MVP.lnk"


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_script(repo_dir: Path, python_dir: Path) -> str:
    """PowerShell-Skript, das die Verknüpfung über WScript.Shell erstellt."""
    target = python_dir / "pythonw.exe"
    return "; ".join(
        [
            "$desktop = [Environment]::GetFolderPath('Desktop')",
            f"$link = Join-Path $desktop {_ps_quote(SHORTCUT_NAME)}",
            "$shell = New-Object -ComObject WScript.Shell",
            "$s = $shell.CreateShortcut($link)",
            f"$s.TargetPath = {_ps_quote(str(target))}",
            "$s.Arguments = '-m trader.launch'",
            f"$s.WorkingDirectory = {_ps_quote(str(repo_dir))}",
            "$s.Description = 'Trader MVP starten'",
            "$s.Save()",
            "Write-Output $link",
        ]
    )


def main() -> int:
    if sys.platform != "win32":
        print("Die Desktop-Verknüpfung gibt es nur unter Windows.")
        return 1
    script = build_script(REPO_DIR, Path(sys.executable).parent)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Die Verknüpfung konnte nicht erstellt werden:")
        print(result.stderr.strip())
        return 1
    print(f"Fertig! Verknüpfung erstellt: {result.stdout.strip()}")
    print("Ab jetzt einfach auf dem Desktop 'Trader MVP' doppelklicken.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
