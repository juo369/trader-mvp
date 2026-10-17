@echo off
rem Legt eine Windows-Aufgabe an: Paper-Trading jeden Werktag um 22:15 Uhr.
rem Ergebnisse stehen danach in paper.log im Projektordner.
schtasks /create /tn "Trader-MVP Paper-Trading" /tr "\"%~dp03-paper-trading.bat\" auto" /sc weekly /d MON,TUE,WED,THU,FRI /st 22:15 /f
if errorlevel 1 (
    echo FEHLER beim Anlegen der Aufgabe. Bitte Screenshot an Claude schicken.
) else (
    echo.
    echo Fertig! Laeuft jetzt jeden Werktag um 22:15 Uhr, solange der PC an ist.
    echo Ergebnisse: paper.log im Projektordner.
    echo Wieder entfernen: schtasks /delete /tn "Trader-MVP Paper-Trading" /f
)
pause
