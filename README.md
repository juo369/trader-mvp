# Trader MVP

Python-Grundgerüst für einen einfachen Trader: Aktien und ETFs, Kursdaten von Yahoo Finance (`yfinance`), ein Backtesting-Modul und lokales Paper-Trading.

**Wichtig:** Dies ist eine reine Simulation. Es gibt keinen Broker-Anschluss, keine API-Keys und keine echten Orders. Das Projekt ist keine Anlageberatung.

## Die App (am einfachsten)

Es gibt eine kleine Web-App mit Oberfläche, ganz ohne Befehle im Kopf. Sie läuft lokal in deinem Browser.

Einmal die neuen Pakete installieren (Streamlit):

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt      # Windows PowerShell
.venv/bin/python -m pip install -r requirements.txt              # Mac/Linux
```

Starten:

```bash
.venv\Scripts\python.exe -m streamlit run app.py                 # Windows PowerShell
.venv/bin/python -m streamlit run app.py                         # Mac/Linux
```

### Windows: Desktop-Verknüpfung (ohne offenes Fenster)

Einmalig im Projektordner ausführen:

```powershell
.venv\Scripts\python.exe -m trader.shortcut
```

Danach liegt auf dem Desktop **„Trader MVP“**. Doppelklick startet die App im Hintergrund und öffnet den Browser; läuft sie schon, öffnet sich nur der Browser. Beenden über den Knopf **„⏻ App beenden“** links in der App.

- Der Browser öffnet sich automatisch unter http://localhost:8501.
- Beenden: Knopf **„⏻ App beenden“** in der App, oder im Terminal-Fenster **Strg+C**.
- Beim ersten Start fragt Streamlit vielleicht nach einer E-Mail-Adresse. Dann einfach **Enter** drücken, du musst nichts eingeben.

## Funktionen

- **Backtest** einer SMA-Crossover-Strategie mit Gebühren, ohne Lookahead (Signal von gestern, Ausführung zum heutigen Schlusskurs), inkl. Buy-&-Hold-Vergleich
- **Paper-Trading** mit einem lokalen, simulierten Konto (Zustand als JSON gespeichert)
- Daten aus Yahoo Finance mit lokalem CSV-Cache

## Windows: ganz einfach per Doppelklick

Voraussetzung: Python von https://www.python.org/downloads/ (beim Installieren **„Add Python to PATH“** anhaken).

Im Ordner `windows/` nacheinander doppelklicken:

1. `1-installieren.bat` – richtet alles ein (nur einmal nötig)
2. `2-backtest.bat` – testet die Strategie mit historischen Daten
3. `3-paper-trading.bat` – ein Handelsschritt mit aktuellen Kursen, zeigt danach das Konto
4. `4-taeglich-automatisch.bat` – optional: führt Schritt 3 jeden Werktag um 22:15 Uhr automatisch aus (Ergebnisse in `paper.log`)

Den Ticker (Standard `SPY`) kannst du oben in den `.bat`-Dateien ändern (Rechtsklick → Bearbeiten).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Nutzung

Alle Befehle werden aus dem Projektverzeichnis gestartet.

### Backtest

```bash
python -m trader backtest --ticker SPY --start 2015-01-01
python -m trader backtest --ticker SPY --start 2015-01-01 --end 2023-12-31 --fast 20 --slow 50 --cash 10000 --fee 0.001
```

Gibt Gesamtrendite, CAGR, maximalen Drawdown, Sharpe-Ratio, Anzahl Trades und die Buy-&-Hold-Rendite aus.

### Paper-Trading

```bash
python -m trader paper --ticker SPY
python -m trader paper --ticker SPY --fast 20 --slow 50 --state paper_state/account.json
```

Lädt rund ein Jahr Kursdaten, berechnet das aktuelle Signal, führt bei Bedarf eine simulierte Order aus und zeigt Aktion, Cash, Positionen und Equity. Das Konto wird in `paper_state/account.json` gespeichert.

### Kontostand

```bash
python -m trader status
python -m trader status --state paper_state/account.json
```

## Tests

```bash
pytest
```

Die Tests laufen ohne Netzwerkzugriff und verwenden synthetische Daten.

## Projektstruktur

```
trader/
  data.py       Kursdaten (yfinance, Cache)
  indicators.py SMA, RSI
  strategy.py   Strategien (Basisklasse, SmaCrossover)
  backtest.py   Backtest-Engine und Kennzahlen
  broker.py     Simuliertes Paper-Konto
  paper.py      Ein Paper-Trading-Schritt
  cli.py        Kommandozeile
tests/          pytest-Tests
```
