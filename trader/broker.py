"""Lokaler Paper-Broker: simuliert Konto und Orders, kein echter Broker."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


class PaperBroker:
    def __init__(
        self,
        state_file: str = "paper_state/account.json",
        initial_cash: float = 10_000.0,
        fee_rate: float = 0.001,
    ):
        self.state_file = state_file
        self.fee_rate = fee_rate
        self.cash = float(initial_cash)
        self.positions: dict[str, int] = {}
        self.order_log: list[dict] = []

        if os.path.exists(state_file):
            self._load()

    def _load(self) -> None:
        with open(self.state_file, encoding="utf-8") as f:
            data = json.load(f)
        self.cash = float(data["cash"])
        self.positions = {k: int(v) for k, v in data.get("positions", {}).items()}
        self.order_log = list(data.get("order_log", []))

    def save(self) -> None:
        directory = os.path.dirname(self.state_file)
        if directory:
            os.makedirs(directory, exist_ok=True)
        data = {
            "cash": self.cash,
            "positions": self.positions,
            "order_log": self.order_log,
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def buy(self, ticker: str, shares: int, price: float) -> None:
        if shares <= 0:
            raise ValueError(f"Stückzahl muss positiv sein, war {shares}.")
        volume = shares * price
        fee = self.fee_rate * volume
        if volume + fee > self.cash:
            raise ValueError(
                f"Nicht genug Cash für {shares} {ticker} @ {price:.2f} "
                f"(benötigt {volume + fee:.2f}, verfügbar {self.cash:.2f})."
            )
        self.cash -= volume + fee
        self.positions[ticker] = self.positions.get(ticker, 0) + shares
        self._log("BUY", ticker, shares, price, fee)

    def sell(self, ticker: str, shares: int, price: float) -> None:
        if shares <= 0:
            raise ValueError(f"Stückzahl muss positiv sein, war {shares}.")
        held = self.positions.get(ticker, 0)
        if shares > held:
            raise ValueError(f"Zu wenig {ticker} im Bestand ({held} vorhanden, {shares} verlangt).")
        volume = shares * price
        fee = self.fee_rate * volume
        self.cash += volume - fee
        remaining = held - shares
        if remaining == 0:
            del self.positions[ticker]
        else:
            self.positions[ticker] = remaining
        self._log("SELL", ticker, shares, price, fee)

    def equity(self, prices: dict[str, float]) -> float:
        value = self.cash
        for ticker, shares in self.positions.items():
            value += shares * prices[ticker]
        return float(value)

    def _log(self, side: str, ticker: str, shares: int, price: float, fee: float) -> None:
        self.order_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ticker": ticker,
                "side": side,
                "shares": shares,
                "price": price,
                "fee": fee,
            }
        )
