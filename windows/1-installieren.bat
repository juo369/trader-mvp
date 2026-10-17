@echo off
rem Richtet den Trader-MVP einmalig ein (Python-Umgebung + Pakete).
cd /d "%~dp0.."
echo === Trader-MVP wird eingerichtet ===
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo FEHLER: Python wurde nicht gefunden.
    echo Bitte Python von https://www.python.org/downloads/ installieren
    echo und beim Installieren "Add Python to PATH" anhaken.
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" python -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo FEHLER beim Installieren der Pakete. Bitte Screenshot an Claude schicken.
    pause
    exit /b 1
)
echo.
echo === Fertig! Jetzt "2-backtest.bat" oder "3-paper-trading.bat" doppelklicken. ===
pause
