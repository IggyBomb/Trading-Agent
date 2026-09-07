#!/usr/bin/env python3
"""
paper_portfolio.py — tracks the 4 CONFIRMED /scan picks from 2026-09-07
(REYN, TSN, KLAC, ON) as a paper position, no real capital involved.

Deliberately separate from trade_logger.py / logs/trades.jsonl: this is not
a real position, must never be read by disclosures.py or the publishing
track, and must never influence risk-manager sizing on the real account.

Run standalone: python3 paper_portfolio.py
"""

import json
from datetime import date, datetime

try:
    import yfinance as yf
except ImportError:
    import os, sys
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

DATA_PATH = "./data/paper_portfolio.json"


def fetch_price(ticker):
    h = yf.Ticker(ticker).history(period="5d")
    if h.empty:
        return None
    return float(h["Close"].iloc[-1])


def main():
    book = json.load(open(DATA_PATH))
    positions = book["positions"]

    print(f"\n{'='*88}")
    print(f"  PAPER PORTFOLIO — {book['source']}")
    print(f"  {book['note']}")
    print(f"{'='*88}\n")

    header = f"  {'Ticker':<8}{'Entry':>10}{'Stop':>10}{'Target':>10}{'Price':>10}{'Return':>10}{'vs Stop':>10}{'vs Target':>10}"
    print(header)
    print(f"  {'-'*84}")

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
        print(f"  {t:<8}{entry:>10.2f}{stop:>10.2f}{target:>10.2f}{price:>10.2f}{ret:>+9.2f}%{stop_dist:>+9.2f}%{target_dist:>+9.2f}%{flag}")

    if returns:
        avg = sum(returns) / len(returns)
        days = (date.today() - date.fromisoformat(book["created"])).days
        print(f"\n  Equal-weighted portfolio return since {book['created']} ({days}d): {avg:+.2f}%")

    print(f"\n{'='*88}\n")


if __name__ == "__main__":
    main()
