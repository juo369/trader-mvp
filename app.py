"""Lern-App für Anfänger: Strategie testen und Spielgeld-Konto. Start mit streamlit run app.py."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from trader.backtest import run_backtest
from trader.broker import PaperBroker
from trader.data import latest_price, load_prices
from trader.paper import run_paper_step
from trader.report import (
    POPULAR_TICKERS,
    PRESETS,
    buy_and_hold_equity,
    explain_metrics,
    fmt_number,
    fmt_pct,
    verdict,
)
from trader.strategy import SmaCrossover

ACCOUNT_FILE = "paper_state/account.json"
DEFAULT_FEE_PERCENT = 0.5  # typische Gebühr bei Yuh
START_CASH = 10_000
ANOTHER_TICKER = "Anderer Ticker…"
PRESET_NAMES = list(PRESETS.keys())
STANDARD_PRESET_INDEX = PRESET_NAMES.index("Standard (20/50)")
NETWORK_HINT = (
    "Prüfe deine Internetverbindung und ob der Ticker stimmt. "
    "Den richtigen Ticker findest du auf finance.yahoo.com."
)


def choose_ticker(key: str) -> str:
    """Auswahl eines Tickers: Liste oder eigene Eingabe."""
    options = list(POPULAR_TICKERS.keys()) + [ANOTHER_TICKER]
    choice = st.selectbox("Welche Aktie oder welcher ETF?", options, key=key)
    if choice == ANOTHER_TICKER:
        ticker = st.text_input(
            "Ticker eingeben (nur Grossbuchstaben)",
            key=f"{key}_custom",
            placeholder="z. B. AAPL",
        )
        st.caption(
            "Den Ticker findest du auf finance.yahoo.com: Suche nach dem Namen, "
            "das Kürzel steht dort oben bei „Symbol“."
        )
        return ticker.strip().upper()
    return POPULAR_TICKERS[choice]


def fee_input(key: str) -> float:
    """Gebühr pro Kauf/Verkauf in Prozent abfragen; gibt den Anteil zurück (0.5 % -> 0.005)."""
    percent = st.number_input(
        "Gebühr pro Kauf oder Verkauf (in %)",
        min_value=0.0,
        max_value=5.0,
        value=DEFAULT_FEE_PERCENT,
        step=0.1,
        format="%.2f",
        key=key,
        help="So viel verlangt deine Bank pro Order. Bei Yuh sind es etwa 0.5 %, "
        "bei US-Aktien kommt noch der Währungswechsel dazu.",
    )
    return percent / 100


def run_test(
    ticker: str, start_year: int, preset: str, cash: float, fee_rate: float
) -> dict:
    """Lädt Kurse und rechnet den Backtest. Wirft ValueError oder andere Fehler."""
    fast, slow = PRESETS[preset]
    prices = load_prices(ticker, f"{start_year}-01-01")
    signals = SmaCrossover(fast=fast, slow=slow).generate_signals(prices)
    result = run_backtest(prices, signals, initial_cash=cash, fee_rate=fee_rate)
    return {
        "ticker": ticker,
        "start_year": start_year,
        "preset": preset,
        "cash": cash,
        "equity": result.equity,
        "buy_and_hold": buy_and_hold_equity(prices, cash),
        "trades": result.trades,
        "metrics": result.metrics,
    }


def render_start() -> None:
    st.markdown(
        "Hier kannst du ausprobieren, wie eine einfache Kauf-Strategie an der Börse "
        "gelaufen wäre. Du arbeitest nur mit Spielgeld."
    )
    st.markdown(
        "Die App lädt echte historische Kurse von Yahoo Finance und rechnet damit. "
        "Dafür brauchst du eine Internetverbindung. Nur wenn du auf einen Knopf drückst, "
        "wird etwas aus dem Internet geladen."
    )
    st.markdown(
        "**Die Strategie:** Kaufen, wenn der kurze Durchschnittskurs über den langen steigt – "
        "verkaufen, wenn er darunter fällt."
    )
    st.markdown(
        "- **📊 Strategie testen:** Du siehst, was diese Strategie in der Vergangenheit "
        "gebracht hätte.\n"
        "- **💼 Mein Spielgeld-Konto:** Du lässt die Strategie mit einem Konto aus Spielgeld "
        "handeln, Schritt für Schritt mit aktuellen Kursen."
    )
    st.subheader("So fängst du an")
    st.markdown(
        "1. Öffne den Tab **📊 Strategie testen**, wähle eine Aktie oder einen ETF und "
        "drücke **▶️ Test starten**.\n"
        "2. Lies das Ergebnis: War die Strategie besser als einfach Kaufen & Halten?\n"
        "3. Probiere danach den Tab **💼 Mein Spielgeld-Konto** aus und drücke dort einmal "
        "am Tag auf **🤖 Heute handeln lassen**."
    )


def render_backtest() -> None:
    st.header("📊 Strategie testen")

    ticker = choose_ticker("backtest_ticker")
    start_year = st.slider(
        "Ab welchem Jahr soll getestet werden?",
        min_value=2000,
        max_value=date.today().year - 1,
        value=2015,
        key="backtest_year",
    )
    preset = st.radio(
        "Tempo der Strategie",
        PRESET_NAMES,
        index=STANDARD_PRESET_INDEX,
        horizontal=True,
        key="backtest_preset",
    )
    with st.expander("Was bedeutet das?"):
        st.markdown(
            "Die Strategie rechnet zwei Durchschnittskurse aus: einen **kurzen** "
            "(z. B. der Durchschnitt der letzten 20 Handelstage) und einen **langen** "
            "(z. B. der Durchschnitt der letzten 50 Handelstage).\n\n"
            "Ist der kurze Durchschnitt höher als der lange, steigt der Kurs gerade. "
            "Dann kauft die Strategie. Fällt der kurze Durchschnitt darunter, verkauft sie.\n\n"
            "Ein **kurzes** Tempo reagiert schnell und kauft und verkauft oft. "
            "Ein **langes** Tempo ist ruhiger und handelt seltener."
        )
    cash = st.number_input(
        "Startkapital (Spielgeld)",
        min_value=1000,
        value=START_CASH,
        step=1000,
        key="backtest_cash",
    )
    fee_rate = fee_input("backtest_fee")

    if st.button("▶️ Test starten", type="primary", width="stretch"):
        if not ticker:
            st.warning("Bitte gib zuerst einen Ticker ein.")
        else:
            with st.spinner("Lade Kursdaten von Yahoo Finance…"):
                try:
                    st.session_state["backtest"] = run_test(
                        ticker, start_year, preset, float(cash), fee_rate
                    )
                except ValueError as err:
                    st.session_state.pop("backtest", None)
                    st.error(f"{err} {NETWORK_HINT}")
                except Exception:
                    st.session_state.pop("backtest", None)
                    st.error(
                        "Die Kursdaten konnten nicht geladen werden. " + NETWORK_HINT
                    )

    result = st.session_state.get("backtest")
    if result:
        show_backtest_result(result)


def show_backtest_result(result: dict) -> None:
    metrics = result["metrics"]
    equity = result["equity"]
    final_value = float(equity.iloc[-1])
    gain = final_value - result["cash"]

    st.caption(
        f"Ergebnis für {result['ticker']} ab {result['start_year']}, "
        f"Tempo {result['preset']}."
    )

    level, text = verdict(metrics)
    if level == "good":
        st.success(text)
    elif level == "neutral":
        st.info(text)
    else:
        st.warning(text)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Endwert", fmt_number(final_value), delta=fmt_number(gain, signed=True))
    col2.metric("Rendite gesamt", fmt_pct(metrics["total_return"]))
    col3.metric("Kaufen & Halten", fmt_pct(metrics["buy_and_hold_return"]))
    col4.metric("Grösster Einbruch", fmt_pct(metrics["max_drawdown"]))

    for sentence in explain_metrics(metrics, result["cash"], final_value):
        st.markdown(f"- {sentence}")

    st.subheader("Wie hätte sich dein Geld entwickelt?")
    chart = pd.DataFrame(
        {"Strategie": equity, "Kaufen & Halten": result["buy_and_hold"]}
    )
    st.line_chart(chart)

    with st.expander("Alle Käufe und Verkäufe"):
        trades = result["trades"]
        if trades.empty:
            st.write("Die Strategie hat in diesem Zeitraum nichts gekauft.")
        else:
            table = pd.DataFrame(
                {
                    "Datum": pd.to_datetime(trades["date"]).dt.strftime("%d.%m.%Y"),
                    "Aktion": trades["side"].map({"BUY": "Kauf", "SELL": "Verkauf"}),
                    "Kurs": trades["price"].round(2),
                    "Stück": trades["shares"],
                    "Gebühr": trades["fee"].round(2),
                }
            )
            st.dataframe(table, hide_index=True)


def render_account() -> None:
    st.header("💼 Mein Spielgeld-Konto")

    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)

    try:
        broker = PaperBroker(state_file=ACCOUNT_FILE)
    except Exception:
        st.error(
            "Dein Konto konnte nicht gelesen werden. "
            f"Lösche die Datei {ACCOUNT_FILE} oder setze das Konto unten zurück."
        )
        broker = None

    if broker is not None:
        held_text = (
            " + ".join(f"{shares} × {ticker}" for ticker, shares in broker.positions.items())
            or "keine"
        )
        col1, col2, col3 = st.columns(3)
        col1.metric("Bargeld", fmt_number(broker.cash, decimals=2))
        col2.metric("Aktien im Depot", held_text)
        col3.metric("Anzahl Orders", len(broker.order_log))

    ticker = choose_ticker("account_ticker")
    preset = st.radio(
        "Tempo der Strategie",
        PRESET_NAMES,
        index=STANDARD_PRESET_INDEX,
        horizontal=True,
        key="account_preset",
    )
    fee_rate = fee_input("account_fee")
    if broker is not None:
        broker.fee_rate = fee_rate

    if broker is not None and st.button(
        "🤖 Heute handeln lassen", type="primary", width="stretch"
    ):
        if not ticker:
            st.warning("Bitte gib zuerst einen Ticker ein.")
        else:
            trade_with_account(broker, ticker, preset)

    st.caption(
        "Am besten einmal pro Werktag nach Börsenschluss (ab ca. 22:15 Uhr) drücken."
    )

    if broker is not None:
        show_orders(broker)

    with st.expander("⚠️ Konto zurücksetzen"):
        confirm = st.checkbox("Ja, ich will wirklich neu mit 10'000 starten", key="reset_confirm")
        if st.button("Zurücksetzen", disabled=not confirm):
            if os.path.exists(ACCOUNT_FILE):
                os.remove(ACCOUNT_FILE)
            st.session_state["flash"] = "Konto wurde zurückgesetzt. Du startest neu mit 10'000."
            st.rerun()


def trade_with_account(broker: PaperBroker, ticker: str, preset: str) -> None:
    fast, slow = PRESETS[preset]
    start = (date.today() - timedelta(days=400)).isoformat()
    orders_before = len(broker.order_log)

    with st.spinner("Lade aktuelle Kursdaten von Yahoo Finance…"):
        try:
            prices = load_prices(ticker, start)
            price = latest_price(ticker)
            run_paper_step(SmaCrossover(fast=fast, slow=slow), ticker, broker, prices, price)
        except ValueError as err:
            st.error(f"{err} {NETWORK_HINT}")
            return
        except Exception:
            st.error("Die Kursdaten konnten nicht geladen werden. " + NETWORK_HINT)
            return

    if len(broker.order_log) > orders_before:
        order = broker.order_log[-1]
        if order["side"] == "BUY":
            st.success(
                f"Gekauft: {order['shares']} Stück {order['ticker']} zu {order['price']:.2f}"
            )
        else:
            st.success(
                f"Verkauft: {order['shares']} Stück {order['ticker']} zu {order['price']:.2f}"
            )
    else:
        st.info("Heute nichts zu tun – die Strategie wartet ab.")

    value = broker.cash
    for held_ticker, shares in broker.positions.items():
        held_price = price if held_ticker == ticker else last_order_price(broker, held_ticker)
        value += shares * held_price
    st.metric("Gesamtwert deines Kontos", fmt_number(value, decimals=2))


def last_order_price(broker: PaperBroker, ticker: str) -> float:
    """Letzter Orderkurs eines Papiers, falls sein aktueller Kurs gerade nicht geladen ist."""
    for order in reversed(broker.order_log):
        if order["ticker"] == ticker:
            return float(order["price"])
    return 0.0


def show_orders(broker: PaperBroker) -> None:
    st.subheader("Deine letzten Orders")
    if not broker.order_log:
        st.info("Noch keine Orders.")
        return

    rows = [
        {
            "Zeitpunkt": datetime.fromisoformat(order["timestamp"])
            .astimezone()
            .strftime("%d.%m.%Y %H:%M"),
            "Aktion": "Kauf" if order["side"] == "BUY" else "Verkauf",
            "Ticker": order["ticker"],
            "Stück": order["shares"],
            "Kurs": round(order["price"], 2),
            "Gebühr": round(order["fee"], 2),
        }
        for order in reversed(broker.order_log)
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True)


def render_help() -> None:
    st.header("❓ Hilfe")
    st.subheader("Wichtige Begriffe")
    st.markdown(
        "**Ticker:** Das Kürzel einer Aktie an der Börse, z. B. `AAPL` für Apple. "
        "Den Ticker findest du auf finance.yahoo.com.\n\n"
        "**ETF:** Ein Fonds, der viele Aktien auf einmal enthält. Ein ETF wie SPY bildet "
        "zum Beispiel die 500 grössten US-Firmen ab.\n\n"
        "**Backtest:** Ein Test mit alten Kursen. Man prüft, was eine Strategie in der "
        "Vergangenheit gebracht hätte.\n\n"
        "**Paper-Trading:** Handeln mit Spielgeld. Es wird nichts wirklich gekauft, das "
        "Konto wird nur auf deinem Computer gespeichert.\n\n"
        "**Gleitender Durchschnitt:** Der Durchschnitt der Kurse der letzten Tage. "
        "Er zeigt die Richtung, in die der Kurs gerade geht.\n\n"
        "**Rendite:** Wie viel Prozent dein Geld gewachsen (oder gesunken) ist.\n\n"
        "**Grösster Einbruch (Drawdown):** Der grösste Rückgang vom höchsten Stand bis zum "
        "tiefsten Punkt danach. Je kleiner, desto ruhiger war die Fahrt.\n\n"
        "**Kaufen & Halten:** Man kauft am Anfang und verkauft nie. Das ist der einfachste "
        "Vergleich für jede Strategie.\n\n"
        "**Gebühr:** Kosten, die beim Kaufen und Verkaufen anfallen. Hier sind es 0.1 % pro Handel."
    )
    st.subheader("Was tun bei Problemen?")
    st.markdown(
        "1. Prüfe, ob du im Internet bist.\n"
        "2. Prüfe den Ticker auf finance.yahoo.com.\n"
        "3. Mache einen Screenshot von der Fehlermeldung und schicke ihn an Claude."
    )


def main() -> None:
    st.set_page_config(page_title="Trader MVP", page_icon="📈", layout="wide")
    st.title("📈 Mein Trading-Spielplatz")
    st.info(
        "Alles hier ist nur Simulation mit Spielgeld. Es wird nie echtes Geld bewegt. "
        "Keine Anlageberatung."
    )

    start_tab, backtest_tab, account_tab, help_tab = st.tabs(
        ["🏠 Start", "📊 Strategie testen", "💼 Mein Spielgeld-Konto", "❓ Hilfe"]
    )
    with start_tab:
        render_start()
    with backtest_tab:
        render_backtest()
    with account_tab:
        render_account()
    with help_tab:
        render_help()


main()
