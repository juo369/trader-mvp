@echo off
rem Startet die Lern-App (Streamlit). Der Browser oeffnet sich automatisch unter http://localhost:8501.
rem Zum Beenden: dieses Fenster schliessen oder Strg+C druecken.
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    echo Bitte zuerst "1-installieren.bat" doppelklicken.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run app.py
pause
