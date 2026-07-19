#!/usr/bin/env python3
"""
earnings_calendar.py — Pre-scan earnings risk screener
Scans watchlist for tickers reporting earnings in the next LOOKAHEAD_DAYS.
Cross-references with market_data.json to flag HIGH/MEDIUM conviction tickers.

Run as the FIRST step in the pipeline, before fetch_data.py:
  python3 earnings_calendar.py
  python3 earnings_calendar.py --days 14
"""

import json, os, sys, argparse
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import yfinance as yf
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

WATCHLIST_PATH   = "./data/watchlist.txt"
MARKET_DATA_PATH = "./data/market_data.json"
OUTPUT_PATH      = "./data/earnings_calendar.json"
LOOKAHEAD_DAYS   = 7
MAX_WORKERS      = 30


def load_watchlist():
    with open(WATCHLIST_PATH) as f:
        return [t.strip() for t in f if t.strip()]


def load_conviction_map():
    try:
        with open(MARKET_DATA_PATH) as f:
            data = json.load(f)
        signals = data.get("signals", [])
        return {s["ticker"]: s.get("conviction", "") for s in signals if "ticker" in s}
    except Exception:
        return {}


def check_ticker(ticker, cutoff_start, cutoff_end):
    try:
        cal = yf.Ticker(ticker).calendar
        if not cal:
            return None
        dates = cal.get("Earnings Date")
        if not dates:
            return None
        if not isinstance(dates, list):
            dates = [dates]

        for ed in dates:
            if isinstance(ed, datetime):
                ed = ed.date()
            elif hasattr(ed, "date"):
                ed = ed.date()
            elif isinstance(ed, str):
                try:
                    ed = datetime.strptime(ed, "%Y-%m-%d").date()
                except Exception:
                    continue

            if cutoff_start <= ed <= cutoff_end:
                return {
                    "ticker":         ticker,
                    "earnings_date":  ed.isoformat(),
                    "days_away":      (ed - cutoff_start).days,
                    "eps_estimate":   cal.get("Earnings Average"),
                    "eps_high":       cal.get("Earnings High"),
                    "eps_low":        cal.get("Earnings Low"),
                    "rev_estimate":   cal.get("Revenue Average"),
                }
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=LOOKAHEAD_DAYS,
                        help=f"Lookahead window in calendar days (default: {LOOKAHEAD_DAYS})")
    args = parser.parse_args()

    today      = date.today()
    cutoff_end = today + timedelta(days=args.days)

    print(f"\n{'='*60}")
    print(f"  Earnings Calendar — {today.isoformat()}")
    print(f"  Scanning for earnings: {today} → {cutoff_end} ({args.days}d window)")
    print(f"{'='*60}\n")

    tickers    = load_watchlist()
    conviction = load_conviction_map()

    print(f"  Scanning {len(tickers)} tickers ({MAX_WORKERS} threads)...", flush=True)

    upcoming = []
    done     = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_ticker, t, today, cutoff_end): t for t in tickers}
        for future in as_completed(futures):
            done += 1
            if done % 300 == 0:
                print(f"    {done}/{len(tickers)} scanned...", flush=True)
            result = future.result()
            if result:
                result["conviction"] = conviction.get(result["ticker"], "")
                upcoming.append(result)

    # Sort by date then conviction
    conv_order = {"High": 0, "Medium": 1, "Low": 2, "": 3}
    upcoming.sort(key=lambda x: (x["earnings_date"], conv_order.get(x.get("conviction", ""), 3)))

    high_med = [t for t in upcoming if t.get("conviction") in ("High", "Medium")]
    other    = [t for t in upcoming if t.get("conviction") not in ("High", "Medium")]

    print(f"\n  Found {len(upcoming)} tickers reporting in the next {args.days} days.\n")

    # ── HIGH / MEDIUM conviction block ────────────────────────────────────────
    if high_med:
        print(f"  ⚠  HIGH/MEDIUM CONVICTION — REPORTING SOON ({len(high_med)} tickers)")
        print(f"  {'─'*72}")
        print(f"  {'TICKER':<10}  {'DATE':<12}  {'DAYS':>4}  {'CONVICTION':<10}  {'EPS EST':>8}  {'REV EST':>12}")
        print(f"  {'─'*72}")
        for t in high_med:
            eps = f"${t['eps_estimate']:.3f}"  if t.get("eps_estimate") is not None else "N/A"
            rev = f"${t['rev_estimate']/1e6:.0f}M" if t.get("rev_estimate") is not None else "N/A"
            print(f"  {t['ticker']:<10}  {t['earnings_date']:<12}  {t['days_away']:>4}  "
                  f"{t.get('conviction',''):<10}  {eps:>8}  {rev:>12}")
        print()

    # ── Rest of watchlist ─────────────────────────────────────────────────────
    if other:
        display = other[:40]
        print(f"  WATCHLIST TICKERS REPORTING SOON ({len(other)} tickers)")
        print(f"  {'─'*60}")
        for t in display:
            eps = f"${t['eps_estimate']:.3f}"  if t.get("eps_estimate") is not None else "N/A"
            rev = f"${t['rev_estimate']/1e6:.0f}M" if t.get("rev_estimate") is not None else "N/A"
            print(f"  {t['ticker']:<10}  {t['earnings_date']:<12}  +{t['days_away']}d  "
                  f"EPS est: {eps:<8}  Rev: {rev}")
        if len(other) > 40:
            print(f"  ... and {len(other) - 40} more — see earnings_calendar.json")
        print()

    if not upcoming:
        print(f"  ✓ No earnings in the next {args.days} days for any watchlist ticker.\n")

    # ── Risk summary ──────────────────────────────────────────────────────────
    print(f"  RISK SUMMARY")
    print(f"  {'─'*50}")
    if high_med:
        for t in high_med:
            verb = "TODAY" if t["days_away"] == 0 else (
                   "TOMORROW" if t["days_away"] == 1 else f"in {t['days_away']}d ({t['earnings_date']})")
            print(f"  ⚠  {t['ticker']} ({t['conviction']}) reports {verb} — "
                  f"AVOID new entries unless event-driven setup")
    else:
        print(f"  ✓ No HIGH/MEDIUM conviction tickers reporting in the next {args.days} days")

    # ── Save ──────────────────────────────────────────────────────────────────
    output = {
        "generated_at":     datetime.now().isoformat(),
        "scan_date":        today.isoformat(),
        "cutoff_date":      cutoff_end.isoformat(),
        "lookahead_days":   args.days,
        "total_upcoming":   len(upcoming),
        "high_medium_count": len(high_med),
        "tickers":          upcoming,
    }
    os.makedirs("./data", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Output saved to: {OUTPUT_PATH}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
