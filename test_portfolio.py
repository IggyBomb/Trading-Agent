#!/usr/bin/env python3
"""
test_portfolio.py — running paper-tracking portfolio for /scan CONFIRMED
picks ("test" portfolio). Grows over time as new scans add tickers — this
is not a single day's snapshot, it accumulates.

Deliberately separate from trade_logger.py / logs/trades.jsonl: nothing
here is a real position, must never be read by disclosures.py or the
publishing track, and must never influence risk-manager sizing on the real
account.

Usage:
    python3 test_portfolio.py                  # show performance report
    python3 test_portfolio.py add TICKER ENTRY STOP TARGET SETUP F_SCORE RATING
        e.g. python3 test_portfolio.py add NVDA 185.0 177.0 197.0 breakout 62.1 Undervalued
        (uses today's date and tags the source as a manual add unless
        --source is passed)
    python3 test_portfolio.py add TICKER ENTRY STOP TARGET SETUP F_SCORE RATING --source "/scan 2026-09-10 CONFIRMED"
"""

import argparse
import json
from datetime import date

try:
    import yfinance as yf
except ImportError:
    import os, sys
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

DATA_PATH = "./data/test_portfolio.json"


def load_book():
    return json.load(open(DATA_PATH))


def save_book(book):
    with open(DATA_PATH, "w") as f:
        json.dump(book, f, indent=2)
        f.write("\n")


def fetch_price(ticker):
    h = yf.Ticker(ticker).history(period="5d")
    if h.empty:
        return None
    return float(h["Close"].iloc[-1])


def cmd_add(args):
    book = load_book()
    existing = {p["ticker"] for p in book["positions"]}
    if args.ticker.upper() in existing:
        print(f"  {args.ticker.upper()} is already in the test portfolio — not adding a duplicate.")
        print(f"  (edit {DATA_PATH} by hand if you mean to re-enter it.)")
        return 1

    entry = {
        "ticker": args.ticker.upper(),
        "entry_date": date.today().isoformat(),
        "entry_price": args.entry,
        "stop": args.stop,
        "target": args.target,
        "setup": args.setup,
        "f_score": args.f_score,
        "rating": args.rating,
        "source": args.source or f"manual add {date.today().isoformat()}",
    }
    book["positions"].append(entry)
    save_book(book)
    print(f"  Added {entry['ticker']} @ {entry['entry_price']} ({entry['source']})")
    return 0


def cmd_show(args):
    book = load_book()
    positions = book["positions"]

    print(f"\n{'='*96}")
    print(f"  TEST PORTFOLIO — {book.get('description', '')}")
    print(f"  Created {book['created']}, {len(positions)} position(s)")
    print(f"{'='*96}\n")

    header = (f"  {'Ticker':<8}{'Entry date':<12}{'Entry':>10}{'Stop':>10}{'Target':>10}"
              f"{'Price':>10}{'Return':>10}{'vs Stop':>10}{'vs Target':>10}")
    print(header)
    print(f"  {'-'*92}")

    returns = []
    for pos in positions:
        t = pos["ticker"]
        entry = pos["entry_price"]
        stop = pos["stop"]
        target = pos["target"]
        price = fetch_price(t)
        if price is None:
            print(f"  {t:<8}{'NO DATA':>10}")
            continue
        ret = (price / entry - 1) * 100
        returns.append(ret)
        stop_dist = (price - stop) / price * 100
        target_dist = (target - price) / price * 100
        flag = ""
        if price <= stop:
            flag = "  ⚠ STOP HIT"
        elif price >= target:
            flag = "  ✓ TARGET HIT"
        print(f"  {t:<8}{pos['entry_date']:<12}{entry:>10.2f}{stop:>10.2f}{target:>10.2f}"
              f"{price:>10.2f}{ret:>+9.2f}%{stop_dist:>+9.2f}%{target_dist:>+9.2f}%{flag}")

    if returns:
        avg = sum(returns) / len(returns)
        print(f"\n  Equal-weighted return across {len(returns)} position(s): {avg:+.2f}%")

    print(f"\n{'='*96}\n")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("add", help="add a new ticker to the test portfolio")
    p.add_argument("ticker")
    p.add_argument("entry", type=float)
    p.add_argument("stop", type=float)
    p.add_argument("target", type=float)
    p.add_argument("setup")
    p.add_argument("f_score", type=float)
    p.add_argument("rating")
    p.add_argument("--source", default=None, help='e.g. "/scan 2026-09-14 CONFIRMED"')

    args = ap.parse_args()
    if args.cmd == "add":
        return cmd_add(args)
    return cmd_show(args)


if __name__ == "__main__":
    raise SystemExit(main())
