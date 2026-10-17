"""Kommandozeile: backtest, paper, status."""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta

from trader.backtest import run_backtest
from trader.broker import PaperBroker
from trader.data import latest_price, load_prices
from trader.paper import run_paper_step
from trader.strategy import SmaCrossover

DEFAULT_STATE = "paper_state/account.json"


def _pct(value: float) -> str:
    return f"{value * 100:.2f} %"


def cmd_backtest(args: argparse.Namespace) -> int:
    prices = load_prices(args.ticker, args.start, args.end)
    strategy = SmaCrossover(fast=args.fast, slow=args.slow)
    signals = strategy.generate_signals(prices)
    result = run_backtest(prices, signals, initial_cash=args.cash, fee_rate=args.fee)
    m = result.metrics

    print(f"Backtest {args.ticker} | SMA {args.fast}/{args.slow} | {args.start} bis {args.end or 'heute'}")
    print(f"  Startkapital:        {args.cash:,.2f}")
    print(f"  Endwert:             {result.equity.iloc[-1]:,.2f}")
    print(f"  Gesamtrendite:       {_pct(m['total_return'])}")
    print(f"  CAGR:                {_pct(m['cagr'])}")
    print(f"  Max. Drawdown:       {_pct(m['max_drawdown'])}")
    print(f"  Sharpe (rf=0):       {m['sharpe']:.2f}")
    print(f"  Anzahl Trades:       {m['num_trades']}")
    print(f"  Buy & Hold Rendite:  {_pct(m['buy_and_hold_return'])}")
    return 0


def cmd_paper(args: argparse.Namespace) -> int:
    start = (date.today() - timedelta(days=400)).isoformat()
    prices = load_prices(args.ticker, start)
    price = latest_price(args.ticker)

    broker = PaperBroker(state_file=args.state)
    strategy = SmaCrossover(fast=args.fast, slow=args.slow)
    action = run_paper_step(strategy, args.ticker, broker, prices, price)

    print(f"Aktion:    {action}")
    print(f"Kurs:      {args.ticker} {price:.2f}")
    print(f"Cash:      {broker.cash:,.2f}")
    _print_positions(broker)
    print(f"Equity:    {broker.equity({args.ticker: price}):,.2f}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if not os.path.exists(args.state):
        print(f"Kein Konto unter {args.state} gefunden, es wird das Standardkonto angezeigt.")
    broker = PaperBroker(state_file=args.state)
    print(f"Cash:      {broker.cash:,.2f}")
    _print_positions(broker)
    print(f"Orders:    {len(broker.order_log)}")
    for order in broker.order_log[-5:]:
        print(
            f"  {order['timestamp']}  {order['side']:4} {order['shares']} {order['ticker']} "
            f"@ {order['price']:.2f} (Gebühr {order['fee']:.2f})"
        )
    return 0


def _print_positions(broker: PaperBroker) -> None:
    if not broker.positions:
        print("Positionen: keine")
        return
    print("Positionen:")
    for ticker, shares in broker.positions.items():
        print(f"  {ticker}: {shares} Stück")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trader", description="Trader MVP (Simulation, keine Anlageberatung)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_bt = sub.add_parser("backtest", help="Backtest einer SMA-Crossover-Strategie")
    p_bt.add_argument("--ticker", required=True)
    p_bt.add_argument("--start", required=True, help="Startdatum, YYYY-MM-DD")
    p_bt.add_argument("--end", default=None, help="Enddatum, YYYY-MM-DD (optional)")
    p_bt.add_argument("--fast", type=int, default=20)
    p_bt.add_argument("--slow", type=int, default=50)
    p_bt.add_argument("--cash", type=float, default=10_000.0)
    p_bt.add_argument("--fee", type=float, default=0.001)
    p_bt.set_defaults(func=cmd_backtest)

    p_paper = sub.add_parser("paper", help="Paper-Trading-Schritt ausführen")
    p_paper.add_argument("--ticker", required=True)
    p_paper.add_argument("--fast", type=int, default=20)
    p_paper.add_argument("--slow", type=int, default=50)
    p_paper.add_argument("--state", default=DEFAULT_STATE)
    p_paper.set_defaults(func=cmd_paper)

    p_status = sub.add_parser("status", help="Paper-Konto anzeigen")
    p_status.add_argument("--state", default=DEFAULT_STATE)
    p_status.set_defaults(func=cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
