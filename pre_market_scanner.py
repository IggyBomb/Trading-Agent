#!/usr/bin/env python3
"""
pre_market_scanner.py — EU pre-market gap scanner

Run at ~08:30 CET before EU market open.
Scans EU watchlist tickers for overnight gaps vs previous close.
Always checks open positions regardless of threshold.

Usage:
  python3 pre_market_scanner.py              — default 2% gap threshold
  python3 pre_market_scanner.py --min-gap 3  — custom threshold
  python3 pre_market_scanner.py --limit 500  — scan more tickers (slower)
"""

import json, os, sys, argparse
from datetime import datetime, date
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance pandas --quiet")
    import yfinance as yf
    import pandas as pd

from config import (
    EU_SUFFIXES, WATCHLIST_PATH, PREMARKET_GAPS_PATH,
    EARNINGS_PATH, TRADES_PATH,
)

OUTPUT_PATH   = PREMARKET_GAPS_PATH
LOGS_PATH     = TRADES_PATH


def load_watchlist() -> list:
    if not Path(WATCHLIST_PATH).exists():
        return []
    with open(WATCHLIST_PATH) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def load_open_tickers() -> list:
    if not Path(LOGS_PATH).exists():
        return []
    with open(LOGS_PATH) as f:
        trades = [json.loads(l) for l in f if l.strip()]
    return [t["ticker"] for t in trades if t.get("status") == "open"]


def load_earnings() -> list:
    try:
        with open(EARNINGS_PATH) as f:
            data = json.load(f)
        return data if isinstance(data, list) else data.get("earnings", [])
    except Exception:
        return []


def is_eu(ticker: str) -> bool:
    dot = ticker.rfind(".")
    return dot != -1 and ticker[dot:].upper() in EU_SUFFIXES


def gap_for_ticker(ticker: str) -> dict | None:
    try:
        info       = yf.Ticker(ticker).info
        prev_close = (info.get("previousClose") or info.get("regularMarketPreviousClose"))
        current    = (info.get("currentPrice") or info.get("regularMarketPrice")
                      or info.get("preMarketPrice"))
        if not prev_close or not current or prev_close == 0:
            return None
        gap = (float(current) - float(prev_close)) / float(prev_close) * 100
        return {"ticker": ticker, "gap": round(gap, 2),
                "current": round(float(current), 4), "prev": round(float(prev_close), 4)}
    except Exception:
        return None


def days_to_earnings(ticker: str, earnings: list) -> int | None:
    today = date.today()
    for e in earnings:
        if e.get("ticker", "").upper() == ticker.upper():
            try:
                ed    = datetime.strptime(e["earnings_date"], "%Y-%m-%d").date()
                delta = (ed - today).days
                if 0 <= delta <= 7:
                    return delta
            except Exception:
                pass
    return None


def print_section(title: str, items: list, desc: bool = True):
    if not items:
        return
    items = sorted(items, key=lambda x: x["gap"], reverse=desc)
    print(f"  {'─'*58}")
    print(f"  {title}  ({len(items)})")
    print(f"  {'─'*58}")
    print(f"  {'TICKER':<12} {'GAP':>7}  {'PREV':>9}  {'NOW':>9}  NOTES")
    for g in items:
        arrow  = "↑" if g["gap"] > 0 else "↓"
        notes  = ""
        if g.get("dte") is not None:
            notes += f"  ⚠ EARN {g['dte']}d"
        if abs(g["gap"]) >= 5:
            notes += "  ⛔ LARGE"
        print(f"  {g['ticker']:<12} {g['gap']:>+6.1f}%{arrow}  {g['prev']:>9.3f}  {g['current']:>9.3f}{notes}")


def main():
    parser = argparse.ArgumentParser(prog="pre_market_scanner")
    parser.add_argument("--min-gap", type=float, default=2.0)
    parser.add_argument("--limit",   type=int,   default=300)
    args = parser.parse_args()

    all_tickers  = load_watchlist()
    eu_tickers   = [t for t in all_tickers if is_eu(t)][:args.limit]
    open_pos     = load_open_tickers()
    earnings     = load_earnings()
    today        = str(date.today())

    print(f"\n  PRE-MARKET SCANNER — {datetime.now().strftime('%Y-%m-%d %H:%M')} CET")
    print(f"  EU tickers: {len(eu_tickers)}  |  Open positions: {len(open_pos)}")
    print(f"  Gap threshold: ±{args.min_gap:.1f}%\n")

    gaps_up:   list = []
    gaps_down: list = []
    pos_gaps:  list = []

    # ── Always check open positions ───────────────────────────────────────
    if open_pos:
        print(f"  Checking {len(open_pos)} open positions...", end="", flush=True)
        for ticker in open_pos:
            result = gap_for_ticker(ticker)
            if result:
                result["dte"] = days_to_earnings(ticker, earnings)
                pos_gaps.append(result)
        print(f"  done.\n")

    # ── EU watchlist scan ─────────────────────────────────────────────────
    print(f"  Scanning {len(eu_tickers)} EU tickers", end="", flush=True)
    for i, ticker in enumerate(eu_tickers):
        if ticker in open_pos:
            continue
        result = gap_for_ticker(ticker)
        if result and abs(result["gap"]) >= args.min_gap:
            result["dte"] = days_to_earnings(ticker, earnings)
            if result["gap"] > 0:
                gaps_up.append(result)
            else:
                gaps_down.append(result)
        if (i + 1) % 50 == 0:
            print(f".", end="", flush=True)
    print(f"  done.\n")

    # ── Print results ─────────────────────────────────────────────────────
    if pos_gaps:
        print(f"  {'='*58}")
        print(f"  OPEN POSITIONS — OVERNIGHT MOVES")
        print(f"  {'─'*58}")
        print(f"  {'TICKER':<12} {'GAP':>7}  {'PREV':>9}  {'NOW':>9}  NOTES")
        for g in sorted(pos_gaps, key=lambda x: abs(x["gap"]), reverse=True):
            arrow  = "↑" if g["gap"] > 0 else "↓"
            notes  = ""
            if g.get("dte") is not None:
                notes += f"  ⚠ EARN {g['dte']}d"
            if g["gap"] <= -2:
                notes += "  ⛔ CHECK STOP"
            print(f"  {g['ticker']:<12} {g['gap']:>+6.1f}%{arrow}  {g['prev']:>9.3f}  {g['current']:>9.3f}{notes}")

    print()
    print_section(f"GAP UPS  ≥ +{args.min_gap:.1f}%", gaps_up, desc=True)
    print()
    print_section(f"GAP DOWNS ≤ -{args.min_gap:.1f}%", gaps_down, desc=False)

    # ── Save ──────────────────────────────────────────────────────────────
    output = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "date":          today,
        "threshold_pct": args.min_gap,
        "open_positions": sorted(pos_gaps, key=lambda x: abs(x["gap"]), reverse=True),
        "gaps_up":   sorted(gaps_up,   key=lambda x: -x["gap"]),
        "gaps_down": sorted(gaps_down, key=lambda x:  x["gap"]),
    }
    Path("./data").mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved → {OUTPUT_PATH}\n")


if __name__ == "__main__":
    main()
