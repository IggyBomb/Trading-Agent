#!/usr/bin/env python3
"""
test_ptf.py — "Test_PTF": a cash-accounted paper portfolio that /scan manages
day to day (buy / sell / add / trim), built to answer one question: does the
strategy deliver alpha?

Separate from the older test_portfolio.py ("test"), which only tracks equal-
weight entries with no cash, quantities or exits. Like that one, nothing here
is real capital: never logged in trade_logger.py, never read by disclosures.

Accounting rules:
  - Orders are queued and fill at the NEXT session's open after the order
    date (scans run after the close — filling at that close would be
    look-ahead).
  - Stops are mechanical: if a daily low touches the stop, the position is
    sold at the stop (or at the open, if it gapped through).
  - Alpha is measured against a shadow benchmark: every € that goes into a
    position is mirrored into the benchmark (IWDA.AS, MSCI World in EUR) at
    the same fill date; every sale sells the same fraction of that mirror.
    Alpha = Test_PTF NAV - shadow NAV. Cash sits idle in both, so the
    comparison isn't distorted by how much of the book is invested.

Usage:
    python3 test_ptf.py                      # update (fill orders, check stops, snapshot) + report
    python3 test_ptf.py buy TICKER QTY --stop S --target T --reason "..." [--source "/scan 2026-10-02"]
    python3 test_ptf.py sell TICKER QTY|all --reason "..."
    python3 test_ptf.py set-stop TICKER PRICE [--target T] --reason "..."
    python3 test_ptf.py cancel ORDER_ID
"""

import argparse
import json
import sys
from datetime import date, datetime, timedelta

import yfinance as yf

sys.path.insert(0, ".")
from test_portfolio import ticker_currency  # same suffix -> currency map

DATA_PATH = "./data/test_ptf.json"

_hist_cache = {}
_fx_cache = {}


def load_book():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_book(book):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(book, f, indent=2, ensure_ascii=False)


def history(ticker, start):
    key = (ticker, start)
    if key not in _hist_cache:
        h = yf.Ticker(ticker).history(start=start, auto_adjust=False)
        h.index = h.index.tz_localize(None).normalize()
        _hist_cache[key] = h
    return _hist_cache[key]


def fx_eur_per_unit(currency, on_date=None):
    """EUR value of 1 unit of `currency` (latest, or on/just before on_date)."""
    if currency == "EUR":
        return 1.0
    key = (currency, on_date)
    if key not in _fx_cache:
        h = yf.Ticker(f"EUR{currency}=X").history(period="1mo")
        h.index = h.index.tz_localize(None).normalize()
        if on_date:
            h = h[h.index <= on_date] if (h.index <= on_date).any() else h
        _fx_cache[key] = 1 / float(h["Close"].iloc[-1])
    return _fx_cache[key]


def last_close(ticker):
    h = yf.Ticker(ticker).history(period="5d")
    return float(h["Close"].iloc[-1])


# ── ledger ──────────────────────────────────────────────────────────────────

def positions(book):
    """Open positions from filled orders: qty, avg cost (EUR), bench units."""
    pos = {}
    for o in book["orders"]:
        if o["status"] != "filled":
            continue
        p = pos.setdefault(o["ticker"], {"qty": 0, "cost_eur": 0.0, "bench_units": 0.0,
                                         "stop": None, "target": None, "opened": o["fill_date"]})
        if o["side"] == "BUY":
            p["qty"] += o["qty"]
            p["cost_eur"] += o["value_eur"]
            p["bench_units"] += o["bench_units"]
        else:
            frac = o["qty"] / p["qty"] if p["qty"] else 0
            p["cost_eur"] -= p["cost_eur"] * frac
            p["bench_units"] -= o["bench_units"]
            p["qty"] -= o["qty"]
        if p["qty"] == 0:
            del pos[o["ticker"]]
    for t, p in pos.items():
        p.update(book["levels"].get(t, {}))
    return pos


def cash(book):
    c = book["initial_capital"]
    for o in book["orders"]:
        if o["status"] == "filled":
            c += -o["value_eur"] if o["side"] == "BUY" else o["value_eur"]
    return c


def shadow_cash(book):
    c = book["initial_capital"]
    for o in book["orders"]:
        if o["status"] == "filled":
            c += -o["bench_value_eur"] if o["side"] == "BUY" else o["bench_value_eur"]
    return c


def fill(book, o, day, price):
    bench = book["benchmark"]
    fx = fx_eur_per_unit(ticker_currency(o["ticker"]), day)
    value = o["qty"] * price * fx
    bh = history(bench, o["created"])
    bpx = float(bh.loc[bh.index >= day, "Open"].iloc[0])
    if o["side"] == "BUY":
        units = value / bpx
    else:  # sell the same fraction of this ticker's benchmark mirror
        p = positions(book)[o["ticker"]]
        units = p["bench_units"] * o["qty"] / p["qty"]
    o.update(status="filled", fill_date=day.strftime("%Y-%m-%d"), fill_price=round(price, 4),
             fx=round(fx, 6), value_eur=round(value, 2), bench_price=round(bpx, 4),
             bench_units=units, bench_value_eur=round(units * bpx, 2))


def next_id(book):
    return max([o["id"] for o in book["orders"]], default=0) + 1


# ── update: fill pending orders, enforce stops, snapshot ────────────────────

def check_stop(book, ticker, until=None):
    """Sell the whole position if a daily low touched its stop (on or before `until`)."""
    p = positions(book).get(ticker)
    if not p or not p.get("stop"):
        return None
    stop = p["stop"]
    h = history(ticker, p["opened"])
    bars = h[h.index >= pd_date(p["opened"])]
    if until is not None:
        bars = bars[bars.index <= until]
    hit = bars[bars["Low"] <= stop]
    if hit.empty:
        return None
    day = hit.index[0]
    px = min(float(hit["Open"].iloc[0]), stop)  # gap through the stop fills at the open
    o = {"id": next_id(book), "created": day.strftime("%Y-%m-%d"), "ticker": ticker, "side": "SELL",
         "qty": p["qty"], "reason": f"STOP HIT ({stop})", "source": "auto-stop", "status": "pending"}
    book["orders"].append(o)
    fill(book, o, day, px)
    return f"STOPPED OUT {ticker}: {o['qty']} @ {round(px, 4)} on {o['fill_date']}"


def update(book):
    events = []
    for o in sorted([o for o in book["orders"] if o["status"] == "pending"], key=lambda o: (o["created"], o["id"])):
        h = history(o["ticker"], o["created"])
        after = h[h.index > pd_date(o["created"])]
        if after.empty:
            continue
        day = after.index[0]
        if o["side"] == "SELL":
            # a stop hit before this sell's fill date takes precedence
            e = check_stop(book, o["ticker"], until=day - timedelta(days=1))
            if e:
                events.append(e)
            held = positions(book).get(o["ticker"], {}).get("qty", 0)
            if o["qty"] == "all":
                o["qty"] = held
            o["qty"] = min(o["qty"], held)
            if not o["qty"]:
                o["status"] = "cancelled"
                events.append(f"CANCELLED #{o['id']} SELL {o['ticker']} — nothing left to sell")
                continue
        fill(book, o, day, float(after["Open"].iloc[0]))
        events.append(f"FILLED #{o['id']} {o['side']} {o['qty']} {o['ticker']} @ {o['fill_price']} on {o['fill_date']}")

    for t in list(positions(book)):
        e = check_stop(book, t)
        if e:
            events.append(e)
    return events


def pd_date(s):
    import pandas as pd
    return pd.Timestamp(s)


def snapshot(book):
    pos = positions(book)
    rows, invested, bench_val = [], 0.0, 0.0
    bpx = last_close(book["benchmark"])
    for t, p in pos.items():
        px = last_close(t)
        fx = fx_eur_per_unit(ticker_currency(t))
        val = p["qty"] * px * fx
        invested += val
        bench_val += p["bench_units"] * bpx
        rows.append((t, p, px, val))
    nav = cash(book) + invested
    shadow = shadow_cash(book) + bench_val
    today = date.today().isoformat()
    book["history"] = [h for h in book["history"] if h["date"] != today]
    book["history"].append({"date": today, "nav": round(nav, 2), "shadow_nav": round(shadow, 2),
                            "cash": round(cash(book), 2), "invested": round(invested, 2),
                            "bench_close": round(bpx, 4)})
    return rows, nav, shadow, bpx


def report(book, events):
    rows, nav, shadow, bpx = snapshot(book)
    cap = book["initial_capital"]
    print(f"\n{'=' * 78}\n  {book['name']} — {date.today().isoformat()}   (benchmark {book['benchmark']})\n{'=' * 78}")
    for e in events:
        print(f"  » {e}")
    pend = [o for o in book["orders"] if o["status"] == "pending"]
    for o in pend:
        print(f"  … pending #{o['id']} {o['side']} {o['qty']} {o['ticker']} (fills at next open after {o['created']})")
    if rows:
        print(f"\n  {'Ticker':<9}{'Qty':>6}{'Avg €':>10}{'Last':>10}{'Value €':>11}{'P&L €':>10}{'P&L %':>8}{'Stop':>9}{'Target':>9}")
        for t, p, px, val in rows:
            pnl = val - p["cost_eur"]
            print(f"  {t:<9}{p['qty']:>6}{p['cost_eur'] / p['qty']:>10.2f}{px:>10.2f}{val:>11.2f}"
                  f"{pnl:>10.2f}{pnl / p['cost_eur'] * 100:>7.2f}%"
                  f"{p['stop'] if p.get('stop') else '-':>9}{p['target'] if p.get('target') else '-':>9}")
    closed = [o for o in book["orders"] if o["status"] == "filled" and o["side"] == "SELL"]
    print(f"\n  Cash €{cash(book):,.2f}   Invested €{nav - cash(book):,.2f}   NAV €{nav:,.2f}")
    print(f"  Test_PTF return : {(nav / cap - 1) * 100:+.3f}%   (€{nav - cap:+,.2f})")
    print(f"  Shadow benchmark: {(shadow / cap - 1) * 100:+.3f}%   (€{shadow - cap:+,.2f})")
    print(f"  ALPHA           : €{nav - shadow:+,.2f}  ({(nav - shadow) / cap * 100:+.3f}% of capital)")
    deployed = sum(o["value_eur"] for o in book["orders"] if o["status"] == "filled" and o["side"] == "BUY")
    if deployed:
        print(f"  Alpha on capital deployed (€{deployed:,.0f}): {(nav - shadow) / deployed * 100:+.2f}%")
    print(f"  Closed trades: {len(closed)}   History points: {len(book['history'])}\n")


# ── commands ────────────────────────────────────────────────────────────────

def cmd_buy(a, book):
    oid = next_id(book)
    book["orders"].append({"id": oid, "created": date.today().isoformat(), "ticker": a.ticker, "side": "BUY",
                           "qty": int(a.qty), "reason": a.reason, "source": a.source, "status": "pending"})
    lv = book["levels"].setdefault(a.ticker, {})
    if a.stop is not None:
        lv["stop"] = a.stop
    if a.target is not None:
        lv["target"] = a.target
    print(f"Queued #{oid}: BUY {a.qty} {a.ticker} — fills at next open")


def cmd_sell(a, book):
    oid = next_id(book)
    qty = a.qty if a.qty == "all" else int(a.qty)
    book["orders"].append({"id": oid, "created": date.today().isoformat(), "ticker": a.ticker, "side": "SELL",
                           "qty": qty, "reason": a.reason, "source": a.source, "status": "pending"})
    print(f"Queued #{oid}: SELL {qty} {a.ticker} — fills at next open")


def cmd_set_stop(a, book):
    lv = book["levels"].setdefault(a.ticker, {})
    lv["stop"] = a.price
    if a.target is not None:
        lv["target"] = a.target
    book.setdefault("level_changes", []).append({"date": date.today().isoformat(), "ticker": a.ticker,
                                                 "stop": a.price, "target": a.target, "reason": a.reason})
    print(f"{a.ticker}: stop {a.price}" + (f", target {a.target}" if a.target else ""))


def cmd_cancel(a, book):
    for o in book["orders"]:
        if o["id"] == a.order_id and o["status"] == "pending":
            o["status"] = "cancelled"
            print(f"Cancelled #{a.order_id}")
            return
    print(f"No pending order #{a.order_id}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("buy"); p.add_argument("ticker"); p.add_argument("qty")
    p.add_argument("--stop", type=float); p.add_argument("--target", type=float)
    p.add_argument("--reason", required=True); p.add_argument("--source")
    p = sub.add_parser("sell"); p.add_argument("ticker"); p.add_argument("qty")
    p.add_argument("--reason", required=True); p.add_argument("--source")
    p = sub.add_parser("set-stop"); p.add_argument("ticker"); p.add_argument("price", type=float)
    p.add_argument("--target", type=float); p.add_argument("--reason", required=True)
    p = sub.add_parser("cancel"); p.add_argument("order_id", type=int)
    a = ap.parse_args()

    book = load_book()
    if a.cmd:
        {"buy": cmd_buy, "sell": cmd_sell, "set-stop": cmd_set_stop, "cancel": cmd_cancel}[a.cmd](a, book)
    else:
        events = update(book)
        report(book, events)
    save_book(book)


if __name__ == "__main__":
    main()
