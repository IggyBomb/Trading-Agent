#!/usr/bin/env python3
"""
Price Alert Monitor — checks open positions against stop/target levels.
Reads stops and targets from trades.jsonl. Fetches live prices via direct HTTP.
Usage: python3 price_alert_monitor.py
"""

import json
import datetime
import time
import os
import requests

TRADES_FILE = "./logs/trades.jsonl"
CACHE_FILE  = "./data/price_cache.json"

PENCE_TICKERS = {".L"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

def is_pence(ticker):
    return any(ticker.endswith(sfx) for sfx in PENCE_TICKERS)

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cache(cache):
    os.makedirs("./data", exist_ok=True)
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass

def fetch_price(ticker, cache):
    """Fetch via direct HTTP to Yahoo Finance quote API. Falls back to cache on failure."""
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice") or meta.get("previousClose")
            if price:
                cache[ticker] = {"price": float(price), "ts": datetime.datetime.now().isoformat()}
                save_cache(cache)
                return float(price), False  # (price, is_cached)
    except Exception:
        pass

    # fallback to cache
    if ticker in cache:
        return cache[ticker]["price"], True
    return None, False

def load_open_trades():
    trades = []
    with open(TRADES_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            t = json.loads(line)
            if t.get("status") == "open" and t.get("stop_price") and t.get("target_price"):
                trades.append(t)
    return trades

def check_alerts(trade, price):
    ticker    = trade["ticker"]
    stop      = float(trade["stop_price"])
    target    = float(trade["target_price"])
    entry     = float(trade["entry_price"])
    direction = trade.get("direction", "LONG").upper()

    alerts = []

    if direction == "LONG":
        pct_to_stop   = (price - stop)   / entry * 100
        pct_to_target = (target - price) / entry * 100

        if price <= stop:
            alerts.append(f"🔴 STOP HIT   [{ticker}] price={price:.2f} ≤ stop={stop:.2f}")
        elif pct_to_stop < 1.0:
            alerts.append(f"⚠️  NEAR STOP  [{ticker}] price={price:.2f} | stop={stop:.2f} | {pct_to_stop:.1f}% away")

        if price >= target:
            alerts.append(f"🟢 TARGET HIT  [{ticker}] price={price:.2f} ≥ target={target:.2f}")
        elif pct_to_target < 2.0:
            alerts.append(f"🔵 NEAR TARGET [{ticker}] price={price:.2f} | target={target:.2f} | {pct_to_target:.1f}% away")

    elif direction == "SHORT":
        if price >= stop:
            alerts.append(f"🔴 STOP HIT   [{ticker}] price={price:.2f} ≥ stop={stop:.2f}")
        if price <= target:
            alerts.append(f"🟢 TARGET HIT [{ticker}] price={price:.2f} ≤ target={target:.2f}")

    return alerts

def run():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*60}")
    print(f"  PRICE ALERT MONITOR — {now}")
    print(f"{'='*60}\n")

    trades = load_open_trades()

    if not trades:
        print("  No open positions with stops/targets defined.")
        return

    cache     = load_cache()
    any_alert = False

    for trade in trades:
        ticker = trade["ticker"]
        if ticker in ("ROCKET SHORT",):
            print(f"  [{ticker}] — skipped (invalid ticker — fix in logs/trades.jsonl)")
            continue

        price, is_cached = fetch_price(ticker, cache)

        if price is None:
            print(f"  [{ticker:12s}] — price unavailable")
            continue

        stop   = float(trade["stop_price"])
        target = float(trade["target_price"])
        entry  = float(trade["entry_price"])

        pct_chg       = (price - entry) / entry * 100
        pct_to_stop   = (price - stop)   / entry * 100
        pct_to_target = (target - price) / entry * 100

        alerts = check_alerts(trade, price)

        cached_tag = " [cached]" if is_cached else ""
        status = "  " if not alerts else "⚡"
        print(f"  {status} {ticker:12s}  now={price:>8.2f}{cached_tag}  entry={entry:>8.2f}  chg={pct_chg:+.1f}%  "
              f"stop={stop:>8.2f} ({pct_to_stop:+.1f}%)  target={target:>8.2f} ({pct_to_target:+.1f}%)")

        for alert in alerts:
            print(f"       {alert}")
            any_alert = True

    print()
    if not any_alert:
        print("  ✓ No alerts — all positions within range.\n")
    else:
        print("  ⚡ ACTION REQUIRED — see alerts above.\n")

if __name__ == "__main__":
    run()
