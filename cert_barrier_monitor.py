#!/usr/bin/env python3
"""
cert_barrier_monitor.py — daily barrier-distance check for held worst-of
Express/Memory certificates.

Held certificates (worst-of, capital barrier as % of initial fixing):
  DE000VJ6DNB5  ("the gold one")  — Vontobel Multi Memory Express Cert,
      worst-of 2 gold miners, barrier 55% of initial fixing,
      maturity 2027-08-17
  DE000VJ135Q5  ("the Italian one") — Vontobel Multi Cash Collect,
      worst-of 4 Italian blue chips, barrier 60% of initial fixing,
      maturity 2027-12-30

Prints live price vs. barrier and % cushion for each underlying.
Distance formula matches the broker's own convention: (price - barrier) / price * 100
— i.e. how far the price would need to FALL to hit the barrier.

Run standalone: python3 cert_barrier_monitor.py
"""

import yfinance as yf

CERTS = [
    {
        "isin": "DE000VJ6DNB5",
        "label": "Gold cert (AngloGold Ashanti / Kinross)",
        "maturity": "2027-08-17",
        "underlyings": [
            {"name": "AngloGold Ashanti", "ticker": "AU",  "initial": 103.70, "barrier": 57.035, "ccy": "USD"},
            {"name": "Kinross Gold",      "ticker": "KGC", "initial": 32.55,  "barrier": 17.9025, "ccy": "USD"},
        ],
    },
    {
        # Vontobel Financial Products, "Multi Cash Collect con Barriera", capital
        # barrier 60% of initial fixing.
        "isin": "DE000VJ135Q5",
        "label": "Italian blue-chip cert (Campari / DiaSorin / Ferrari / Moncler)",
        "maturity": "2027-12-30",
        "underlyings": [
            {"name": "Campari",   "ticker": "CPR.MI",  "initial": 5.521,  "barrier": 3.313,  "ccy": "EUR"},
            {"name": "DiaSorin",  "ticker": "DIA.MI",  "initial": 68.62,  "barrier": 41.17,  "ccy": "EUR"},
            {"name": "Ferrari",   "ticker": "RACE.MI", "initial": 376.17, "barrier": 225.70, "ccy": "EUR"},
            {"name": "Moncler",   "ticker": "MONC.MI", "initial": 54.98,  "barrier": 32.99,  "ccy": "EUR"},
        ],
    },
]


def fetch_price(ticker):
    h = yf.Ticker(ticker).history(period="5d")
    if h.empty:
        return None
    return float(h["Close"].iloc[-1])


def main():
    print(f"\n{'='*72}")
    print("  CERTIFICATE BARRIER MONITOR")
    print(f"{'='*72}")

    summary = []  # (cert, worst underlying, its live price, its cushion)

    for cert in CERTS:
        print(f"\n  {cert['label']}  [{cert['isin']}]  matures {cert['maturity']}")
        print(f"  {'Name':<22} {'Price':>10} {'Barrier':>10} {'vs Initial':>12} {'Cushion':>10}")
        worst = None  # (underlying, price, cushion)
        for u in cert["underlyings"]:
            price = fetch_price(u["ticker"])
            if price is None:
                print(f"  {u['name']:<22} {'NO DATA':>10}")
                continue
            vs_initial = (price / u["initial"] - 1) * 100
            cushion = (price - u["barrier"]) / price * 100
            if worst is None or cushion < worst[2]:
                worst = (u, price, cushion)
            print(f"  {u['name']:<22} {price:>9.2f}{u['ccy'][0]} {u['barrier']:>9.2f}{u['ccy'][0]} "
                  f"{vs_initial:>+11.2f}% {cushion:>9.2f}%")
        if worst is not None:
            u, price, cushion = worst
            flag = " ⚠ TIGHTENING" if cushion < 20 else ""
            print(f"  → Worst-of cushion (binding leg: {u['name']}): {cushion:.2f}%{flag}")
            summary.append((cert, u, price, cushion))

    # Daily summary: binding leg per cert, its live price vs. barrier, and the
    # % it would need to fall to breach the barrier.
    print(f"\n{'='*72}")
    print("  DAILY SUMMARY — worst-of leg per cert")
    print(f"{'='*72}")
    print(f"  {'Cert':<64} {'Worst-of':<16} {'Price':>10} {'Barrier':>10} {'Distance':>10}")
    for cert, u, price, cushion in summary:
        flag = " ⚠" if cushion < 20 else ""
        print(f"  {cert['label']:<64} {u['name']:<16} {price:>9.2f}{u['ccy'][0]} "
              f"{u['barrier']:>9.2f}{u['ccy'][0]} {cushion:>9.2f}%{flag}")

    print(f"\n{'='*72}\n")


if __name__ == "__main__":
    main()
