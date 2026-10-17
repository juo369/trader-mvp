@echo off
rem Ein Paper-Trading-Schritt mit aktuellen Yahoo-Kursen. Ticker hier anpassen.
rem Mit dem Argument "auto" (fuer die Aufgabenplanung) ohne Pause und mit Logdatei.
set TICKER=SPY
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    echo Bitte zuerst "1-installieren.bat" doppelklicken.
    if /i not "%~1"=="auto" pause
    exit /b 1
)
if /i "%~1"=="auto" (
    echo ===== %date% %time% =====>> paper.log
    ".venv\Scripts\python.exe" -m trader paper --ticker %TICKER% >> paper.log 2>&1
    exit /b
)
".venv\Scripts\python.exe" -m trader paper --ticker %TICKER%
echo.
".venv\Scripts\python.exe" -m trader status
pause
