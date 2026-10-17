@echo off
rem Testet die Strategie mit historischen Daten. Ticker und Startdatum hier anpassen.
set TICKER=SPY
set START=2015-01-01
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    echo Bitte zuerst "1-installieren.bat" doppelklicken.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m trader backtest --ticker %TICKER% --start %START%
pause
