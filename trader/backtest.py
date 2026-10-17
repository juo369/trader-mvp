"""Einfacher Backtest: long-only, voll investiert oder Cash, ohne Lookahead."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from trader.broker import affordable_shares

TRADING_DAYS = 252


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: pd.DataFrame
    metrics: dict = field(default_factory=dict)


def run_backtest(
    prices: pd.DataFrame,
    signals: pd.Series,
    initial_cash: float = 10_000.0,
    fee_rate: float = 0.001,
) -> BacktestResult:
    """Simuliert den Handel.

    Das Signal von Tag t-1 bestimmt die Position am Tag t (shift(1)); ausgeführt
    wird zum Schlusskurs von Tag t. Dadurch gibt es keinen Lookahead.
    """
    close = prices["Close"].astype(float)
    target = signals.reindex(close.index).fillna(0).shift(1).fillna(0).astype(int)

    cash = float(initial_cash)
    shares = 0
    equity_values = []
    trade_rows = []

    for date, price in close.items():
        want_long = target.loc[date] == 1

        if want_long and shares == 0:
            shares = affordable_shares(cash, price, fee_rate)
            if shares > 0:
                volume = shares * price
                fee = fee_rate * volume
                cash -= volume + fee
                trade_rows.append(
                    {"date": date, "side": "BUY", "price": price, "shares": shares, "fee": fee}
                )
        elif not want_long and shares > 0:
            volume = shares * price
            fee = fee_rate * volume
            cash += volume - fee
            trade_rows.append(
                {"date": date, "side": "SELL", "price": price, "shares": shares, "fee": fee}
            )
            shares = 0

        equity_values.append(cash + shares * price)

    equity = pd.Series(equity_values, index=close.index, name="equity")
    trades = pd.DataFrame(trade_rows, columns=["date", "side", "price", "shares", "fee"])

    metrics = _compute_metrics(equity, initial_cash, close, len(trades))
    return BacktestResult(equity=equity, trades=trades, metrics=metrics)


def _compute_metrics(
    equity: pd.Series, initial_cash: float, close: pd.Series, num_trades: int
) -> dict:
    final_value = float(equity.iloc[-1])
    total_return = final_value / initial_cash - 1

    days = (equity.index[-1] - equity.index[0]).days
    years = days / 365.25
    cagr = (final_value / initial_cash) ** (1 / years) - 1 if years > 0 else 0.0

    running_max = equity.cummax()
    max_drawdown = float((equity / running_max - 1).min())

    returns = equity.pct_change().dropna()
    std = returns.std()
    if len(returns) < 2 or not np.isfinite(std) or std == 0:
        sharpe = 0.0
    else:
        sharpe = float(returns.mean() / std * np.sqrt(TRADING_DAYS))

    buy_and_hold_return = float(close.iloc[-1] / close.iloc[0] - 1)

    return {
        "total_return": float(total_return),
        "cagr": float(cagr),
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "num_trades": int(num_trades),
        "buy_and_hold_return": buy_and_hold_return,
    }
