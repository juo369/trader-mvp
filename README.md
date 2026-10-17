# Trader MVP

Python-Grundgerüst für einen einfachen Trader: Aktien und ETFs, Kursdaten von Yahoo Finance (`yfinance`), ein Backtesting-Modul und lokales Paper-Trading.

**Wichtig:** Dies ist eine reine Simulation. Es gibt keinen Broker-Anschluss, keine API-Keys und keine echten Orders. Das Projekt ist keine Anlageberatung.

## Funktionen

- **Backtest** einer SMA-Crossover-Strategie mit Gebühren, ohne Lookahead (Signal von gestern, Ausführung zum heutigen Schlusskurs), inkl. Buy-&-Hold-Vergleich
- **Paper-Trading** mit einem lokalen, simulierten Konto (Zustand als JSON gespeichert)
- Daten aus Yahoo Finance mit lokalem CSV-Cache

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
