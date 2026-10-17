"""Lern-App für Anfänger: Strategie testen und Spielgeld-Konto. Start mit streamlit run app.py."""

from __future__ import annotations

import os
import threading
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from trader.backtest import run_backtest
from trader.broker import PaperBroker
from trader.data import latest_price, load_prices
from trader.momentum import (
    UNIVERSES,
    current_ranking,
    equal_weight_buy_and_hold,
    load_universe,
    run_momentum_backtest,
)
from trader.optimize import default_candidates, walk_forward
from trader.paper import run_paper_step
from trader.report import (
    clean_ticker,
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
        return clean_ticker(ticker)
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
        "- **🔍 Strategie-Finder:** Er probiert viele Einstellungen aus und prüft den Sieger "
        "an einer Zeit, die er nicht kannte.\n"
        "- **🚀 Momentum:** Du hältst einmal im Monat die Werte, die zuletzt am stärksten "
        "gestiegen sind, und schichtest dafür um.\n"
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


def run_finder(ticker: str, start_year: int, fee_rate: float) -> dict:
    """Lädt Kurse und sucht den Sieger in der Lernzeit. Wirft ValueError oder andere Fehler."""
    prices = load_prices(ticker, f"{start_year}-01-01")
    result = walk_forward(prices, fee_rate=fee_rate, initial_cash=float(START_CASH))
    result["ticker"] = ticker
    result["start_year"] = start_year
    return result


def render_finder() -> None:
    st.header("🔍 Strategie-Finder")
    n_settings = len(default_candidates())
    st.markdown(
        f"Der Finder probiert {n_settings} Einstellungen durch. Er sucht den Sieger nur in den "
        "ersten 70 % der Zeit („Lernzeit“) und prüft ihn dann an den letzten 30 % („Prüfzeit“), "
        "die er nicht kannte. Nur das Ergebnis der Prüfzeit zeigt, ob die Strategie wirklich "
        "etwas taugt – in der Vergangenheit sieht im Nachhinein immer irgendetwas gut aus."
    )

    ticker = choose_ticker("finder_ticker")
    start_year = st.slider(
        "Ab welchem Jahr soll getestet werden?",
        min_value=2000,
        max_value=date.today().year - 1,
        value=2015,
        key="finder_year",
    )
    fee_rate = fee_input("finder_fee")

    if st.button("🔍 Beste Einstellung suchen", type="primary", width="stretch"):
        if not ticker:
            st.warning("Bitte gib zuerst einen Ticker ein.")
        else:
            with st.spinner("Lade Kursdaten von Yahoo Finance und probiere Einstellungen aus…"):
                try:
                    st.session_state["finder"] = run_finder(ticker, start_year, fee_rate)
                except ValueError as err:
                    st.session_state.pop("finder", None)
                    st.error(f"{err} {NETWORK_HINT}")
                except Exception:
                    st.session_state.pop("finder", None)
                    st.error(
                        "Die Kursdaten konnten nicht geladen werden. " + NETWORK_HINT
                    )

    result = st.session_state.get("finder")
    if result:
        show_finder_result(result, n_settings)


def show_finder_result(result: dict, n_settings: int) -> None:
    train_start, train_end = result["train_period"]
    test_start, test_end = result["test_period"]
    train_metrics = result["train_result"].metrics
    test_metrics = result["test_result"].metrics

    st.caption(f"Ergebnis für {result['ticker']} ab {result['start_year']}.")

    st.subheader(
        f"1. Bester Treffer in der Lernzeit ({train_start.year}–{train_end.year})"
    )
    st.markdown(f"**{result['best_label']}**")
    col1, col2 = st.columns(2)
    col1.metric("Rendite Strategie", fmt_pct(train_metrics["total_return"]))
    col2.metric("Kaufen & Halten", fmt_pct(train_metrics["buy_and_hold_return"]))

    st.subheader(f"2. Ehrlicher Test in der Prüfzeit ({test_start.year}–{test_end.year})")
    col1, col2, col3 = st.columns(3)
    col1.metric("Rendite Strategie", fmt_pct(test_metrics["total_return"]))
    col2.metric("Kaufen & Halten", fmt_pct(test_metrics["buy_and_hold_return"]))
    col3.metric("Grösster Einbruch", fmt_pct(test_metrics["max_drawdown"]))

    test_return = test_metrics["total_return"]
    buy_and_hold_return = test_metrics["buy_and_hold_return"]
    if test_return < 0:
        st.warning(
            "Der Sieger hat in der Prüfzeit Geld verloren. Was in der Vergangenheit am besten "
            "war, hat danach nicht mehr funktioniert."
        )
    elif test_return >= buy_and_hold_return:
        st.success(
            "Der Sieger war auch in der Prüfzeit besser als Kaufen & Halten. Das ist ein gutes "
            "Zeichen – aber keine Garantie für die Zukunft."
        )
    else:
        st.info(
            "Der Sieger hat in der Prüfzeit Gewinn gemacht, aber einfach Kaufen & Halten wäre "
            "besser gewesen. Typisch: Der beste Treffer von gestern ist selten der beste von morgen."
        )

    st.subheader("Prüfzeit: Wie hätte sich dein Geld entwickelt?")
    chart = pd.DataFrame(
        {
            "Strategie": result["test_result"].equity,
            "Kaufen & Halten": result["test_buy_and_hold_equity"],
        }
    )
    st.line_chart(chart)

    with st.expander(f"Alle {n_settings} Einstellungen in der Lernzeit"):
        ranking = result["ranking"]
        table = pd.DataFrame(
            {
                "Einstellung": ranking["label"],
                "Rendite": ranking["total_return"].map(fmt_pct),
                "Grösster Einbruch": ranking["max_drawdown"].map(fmt_pct),
                "Trades": ranking["num_trades"],
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


MOMENTUM_LOOKBACK_OPTIONS = [3, 6, 12]
MOMENTUM_STOCK_CAPTION = (
    "Achtung: Die Aktien-Listen enthalten Firmen, die heute bekannt und erfolgreich sind. "
    "Das lässt die Vergangenheit besser aussehen, als sie für einen Anleger damals gewesen wäre."
)


def run_momentum(
    tickers: list[str], start_year: int, lookback: int, top_n: int, cash_filter: bool,
    fee_rate: float, universe_name: str,
) -> dict:
    """Lädt die Kurse und rechnet Momentum, Kaufen & Halten und die aktuelle Rangliste.

    Wirft ValueError oder andere Fehler.
    """
    closes, skipped = load_universe(tickers, f"{start_year}-01-01", loader=load_prices)
    result = run_momentum_backtest(
        closes,
        lookback_months=lookback,
        top_n=top_n,
        cash_filter=cash_filter,
        fee_rate=fee_rate,
        initial_cash=float(START_CASH),
    )
    benchmark = equal_weight_buy_and_hold(closes, float(START_CASH))
    ranking, selection = current_ranking(closes, lookback, top_n, cash_filter)
    return {
        "universe": universe_name,
        "start_year": start_year,
        "lookback": lookback,
        "top_n": top_n,
        "cash_filter": cash_filter,
        "skipped": skipped,
        "equity": result.equity,
        "rebalances": result.rebalances,
        "metrics": result.metrics,
        "benchmark": benchmark,
        "ranking": ranking,
        "selection": selection,
    }


def render_momentum() -> None:
    st.header("🚀 Momentum")
    st.markdown(
        "Einmal im Monat schaust du, welche Werte aus einer Liste in den letzten Monaten am "
        "stärksten gestiegen sind, und hältst die zuletzt stärksten bis zum nächsten Monat. "
        "Das dauert etwa 5 Minuten im Monat. Mit der **Sicherheitsregel** bleibst du in Bargeld, "
        "wenn alle Werte im Minus sind. Das ist eine der bekanntesten Strategien, aber auch sie "
        "schlägt Kaufen & Halten nicht immer."
    )

    universe_name = st.selectbox("Welche Liste soll geprüft werden?", list(UNIVERSES.keys()),
                                 key="mom_universe")
    universe_index = list(UNIVERSES.keys()).index(universe_name)
    members = UNIVERSES[universe_name]
    selected = st.multiselect(
        "Welche Werte sollen dabei sein?",
        members,
        default=members,
        key=f"mom_tickers_{universe_index}",
        help="Abwählen geht jederzeit.",
    )
    extra_text = st.text_input(
        "Weitere Ticker (mit Komma getrennt)",
        key="mom_extra",
        placeholder="z. B. VTI, IWDA.AS",
    )
    extra = [clean_ticker(t) for t in extra_text.split(",") if clean_ticker(t)]
    tickers = list(dict.fromkeys(selected + extra))

    start_year = st.slider(
        "Ab welchem Jahr soll getestet werden?",
        min_value=2000,
        max_value=date.today().year - 1,
        value=2012,
        key="mom_year",
    )
    lookback = st.radio(
        "Rückblick",
        MOMENTUM_LOOKBACK_OPTIONS,
        index=MOMENTUM_LOOKBACK_OPTIONS.index(12),
        format_func=lambda months: f"{months} Monate",
        horizontal=True,
        key="mom_lookback",
    )
    top_n = st.slider(
        "Wie viele Werte gleichzeitig halten?",
        min_value=1,
        max_value=3,
        value=1,
        key="mom_top_n",
    )
    cash_filter = st.checkbox(
        "Sicherheitsregel: Wenn alles fällt, in Bargeld bleiben",
        value=True,
        key="mom_cash_filter",
    )
    fee_rate = fee_input("mom_fee")

    if st.button("🚀 Momentum testen", type="primary", width="stretch", key="mom_run"):
        if len(tickers) < 2:
            st.session_state.pop("momentum", None)
            st.warning("Bitte wähle mindestens zwei Werte aus.")
        else:
            with st.spinner("Lade Kursdaten von Yahoo Finance und rechne die Rotation…"):
                try:
                    st.session_state["momentum"] = run_momentum(
                        tickers, start_year, lookback, top_n, cash_filter, fee_rate,
                        universe_name,
                    )
                except ValueError as err:
                    st.session_state.pop("momentum", None)
                    st.error(f"{err} {NETWORK_HINT}")
                except Exception:
                    st.session_state.pop("momentum", None)
                    st.error(
                        "Die Kursdaten konnten nicht geladen werden. " + NETWORK_HINT
                    )

    result = st.session_state.get("momentum")
    if result:
        show_momentum_result(result)


def show_momentum_result(result: dict) -> None:
    metrics = result["metrics"]
    equity = result["equity"]
    benchmark = result["benchmark"]
    final_value = float(equity.iloc[-1])
    bench_return = float(benchmark.iloc[-1] / float(START_CASH) - 1)
    gain = final_value - START_CASH

    if result["skipped"]:
        st.warning(
            "Diese Werte konnten nicht geladen werden und wurden übersprungen: "
            + ", ".join(result["skipped"])
        )

    cash_text = "mit Sicherheitsregel" if result["cash_filter"] else "ohne Sicherheitsregel"
    st.caption(
        f"Ergebnis für {result['universe']} ab {result['start_year']}, Rückblick "
        f"{result['lookback']} Monate, {result['top_n']} gleichzeitig, {cash_text}."
    )

    if metrics["total_return"] < 0:
        st.warning("Mit Momentum hättest du Geld verloren.")
    elif metrics["total_return"] >= bench_return:
        st.success("Momentum war besser als Kaufen & Halten (alle gleich).")
    else:
        st.info(
            "Momentum hat Gewinn gemacht, aber Kaufen & Halten (alle gleich) wäre besser "
            "gewesen."
        )

    col1, col2, col3 = st.columns(3)
    col1.metric("Endwert", fmt_number(final_value), delta=fmt_number(gain, signed=True))
    col2.metric("Rendite Momentum", fmt_pct(metrics["total_return"]))
    col3.metric("Kaufen & Halten (alle gleich)", fmt_pct(bench_return))
    col4, col5, col6 = st.columns(3)
    col4.metric("Grösster Einbruch", fmt_pct(metrics["max_drawdown"]))
    col5.metric("Wechsel", metrics["num_rebalances_changed"])
    col6.metric("Gebühren gesamt", fmt_number(metrics["total_fees"], decimals=2))

    st.subheader("Momentum im Vergleich")
    st.line_chart(
        pd.DataFrame(
            {"Momentum": equity, "Kaufen & Halten (alle gleich)": benchmark}
        )
    )

    with st.container(border=True):
        st.subheader("📅 Diesen Monat")
        selection = result["selection"]
        if selection:
            st.markdown(f"Stand heute würdest du halten: **{' + '.join(selection)}**")
        elif result["cash_filter"]:
            st.markdown(
                "Stand heute würdest du halten: **Bargeld** (alle Werte sind im Minus)"
            )
        else:
            st.markdown("Stand heute würdest du halten: **Bargeld**")

        ranking = result["ranking"]
        table = pd.DataFrame(
            {
                "Ticker": ranking["Ticker"],
                f"Rendite der letzten {result['lookback']} Monate": [
                    "–" if pd.isna(value) else fmt_pct(value)
                    for value in ranking["Rendite"]
                ],
            }
        )
        st.dataframe(table, hide_index=True)
        st.caption(
            "Prüfe das am ersten Handelstag jedes Monats. Ändert sich die Auswahl, verkaufst du "
            "den alten Wert und kaufst den neuen – sonst musst du nichts tun."
        )

    with st.expander("Was hätte ich wann gehalten?"):
        rebalances = result["rebalances"]
        if rebalances.empty:
            st.write("In diesem Zeitraum gab es noch keine Entscheidung.")
        else:
            table = pd.DataFrame(
                {
                    "Datum": pd.to_datetime(rebalances["date"]).dt.strftime("%d.%m.%Y"),
                    "Gehalten": rebalances["holdings"],
                    "Gewechselt": rebalances["changed"].map({True: "Ja", False: "Nein"}),
                }
            )
            st.dataframe(table, hide_index=True)

    if "Aktien" in result["universe"]:
        st.caption(MOMENTUM_STOCK_CAPTION)


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
        "**Lernzeit / Prüfzeit:** Die Lernzeit sind die ersten 70 % des Zeitraums, in der die "
        "beste Einstellung gesucht wird. Die Prüfzeit sind die letzten 30 %, die der Finder "
        "vorher nicht gesehen hat. Nur dort zeigt sich, ob eine Einstellung auch taugt.\n\n"
        "**Überanpassung (Overfitting):** Eine Strategie passt sich so gut an die alten Kurse an, "
        "dass sie nur dort funktioniert. Bei neuen Kursen klappt sie dann oft nicht mehr.\n\n"
        "**Momentum:** Die Idee, dass Werte, die in den letzten Monaten gestiegen sind, "
        "auch in den nächsten Monaten eher steigen. Man kauft dann die zuletzt stärksten Werte.\n\n"
        "**Umschichten (Rebalancing):** Man verkauft Werte und kauft andere dafür. Das passiert "
        "bei der Momentum-Strategie einmal im Monat, wenn sich die Rangliste geändert hat.\n\n"
        "**Gebühr:** Kosten, die beim Kaufen und Verkaufen anfallen. Hier sind es 0.1 % pro Handel."
    )
    st.subheader("Was tun bei Problemen?")
    st.markdown(
        "1. Prüfe, ob du im Internet bist.\n"
        "2. Prüfe den Ticker auf finance.yahoo.com.\n"
        "3. Mache einen Screenshot von der Fehlermeldung und schicke ihn an Claude."
    )


def render_quit_button() -> None:
    """Beendet den App-Server. Nötig, weil die App über die Verknüpfung ohne Fenster läuft."""
    with st.sidebar:
        st.markdown("### App beenden")
        st.caption("Wenn du fertig bist, hier klicken. Danach kannst du den Browser-Tab schliessen.")
        if st.button("⏻ App beenden", width="stretch"):
            st.success("Die App wird beendet. Du kannst diesen Tab jetzt schliessen.")
            threading.Timer(1.0, lambda: os._exit(0)).start()


def main() -> None:
    st.set_page_config(page_title="Trader MVP", page_icon="📈", layout="wide")
    st.title("📈 Mein Trading-Spielplatz")
    st.info(
        "Alles hier ist nur Simulation mit Spielgeld. Es wird nie echtes Geld bewegt. "
        "Keine Anlageberatung."
    )

    start_tab, backtest_tab, finder_tab, momentum_tab, account_tab, help_tab = st.tabs(
        [
            "🏠 Start",
            "📊 Strategie testen",
            "🔍 Strategie-Finder",
            "🚀 Momentum",
            "💼 Mein Spielgeld-Konto",
            "❓ Hilfe",
        ]
    )
    with start_tab:
        render_start()
    with backtest_tab:
        render_backtest()
    with finder_tab:
        render_finder()
    with momentum_tab:
        render_momentum()
    with account_tab:
        render_account()
    with help_tab:
        render_help()
    render_quit_button()


main()
