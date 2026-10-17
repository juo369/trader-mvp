"""Ein Simulationsschritt des Paper-Tradings. Keine Netzwerkzugriffe, Daten werden übergeben."""

from __future__ import annotations

import math

import pandas as pd

from trader.broker import PaperBroker
from trader.strategy import Strategy


def run_paper_step(
    strategy: Strategy,
    ticker: str,
    broker: PaperBroker,
    prices: pd.DataFrame,
    price: float,
) -> str:
    """Wendet das letzte Signal der Strategie auf das Paper-Konto an."""
    signals = strategy.generate_signals(prices)
    if len(signals) == 0:
        raise ValueError("Keine Signale berechnet: prices ist leer.")
    signal = int(signals.iloc[-1])
    held = broker.positions.get(ticker, 0)

    action = "HOLD"
    if signal == 1 and held == 0:
        shares = math.floor(broker.cash / (price * (1 + broker.fee_rate)))
        # Sicherheitsschleife gegen Rundungsfehler bei der Gebühr.
        while shares > 0 and shares * price * (1 + broker.fee_rate) > broker.cash:
            shares -= 1
        if shares > 0:
            broker.buy(ticker, shares, price)
            action = f"BUY {shares} {ticker} @ {price:.2f}"
    elif signal == 0 and held > 0:
        broker.sell(ticker, held, price)
        action = f"SELL {held} {ticker} @ {price:.2f}"

    broker.save()
    return action
