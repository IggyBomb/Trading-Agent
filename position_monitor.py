#!/usr/bin/env python3
"""
position_monitor.py — Daily open position health monitor

Checks live price vs entry / stop / target for every open trade.
Flags: stop proximity, target proximity, time stop, trail signal, earnings.

Usage: python3 position_monitor.py
"""

import json, os, sys
from datetime import datetime, date
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import yfinance as yf
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

from config import ACCOUNT_SIZE, TRADES_PATH, EARNINGS_PATH

LOGS_PATH = TRADES_PATH

TIME_STOPS = {
    "MOMENTUM":   7,
    "SWING":      15,
    "POSITION":   30,
    "TURNAROUND": 45,
    "EVENT":      3,
}


def load_trades():
    if not Path(LOGS_PATH).exists():
        return []
    with open(LOGS_PATH) as f:
        return [json.loads(l) for l in f if l.strip()]


def load_earnings():
    try:
        with open(EARNINGS_PATH) as f:
            data = json.load(f)
        return data if isinstance(data, list) else data.get("earnings", [])
    except Exception:
        return []


# Trade entries in trades.jsonl are logged in EUR-per-share regardless of the
# ticker's listing currency (see notes on LLOY.L/HON trades: entries are
# manually FX-converted at log time). Live prices from yfinance come back in
# the ticker's native currency instead — GBp (pence) for LSE listings, USD for
# US listings — so get_price() must apply the same conversion here or the
# comparison against entry/stop/target is meaningless (e.g. LLOY.L's 114.8p
# read as EUR114.80 instead of EUR1.148, an 8000%+ phantom gain).
_FX_CACHE: dict[str, float | None] = {}


def _fx_rate(pair: str) -> float | None:
    if pair not in _FX_CACHE:
        try:
            info = yf.Ticker(pair).info
            _FX_CACHE[pair] = info.get("regularMarketPrice") or info.get("previousClose")
        except Exception:
            _FX_CACHE[pair] = None
    return _FX_CACHE[pair]


def get_price(ticker: str) -> float | None:
    try:
        info  = yf.Ticker(ticker).info
        price = (info.get("currentPrice") or info.get("regularMarketPrice")
                 or info.get("previousClose"))
        if not price:
            return None
        price    = float(price)
        currency = info.get("currency") or "EUR"

        if currency in ("GBp", "GBX"):   # pence -> pounds (case matters: GBp != GBP)
            price /= 100.0
            currency = "GBP"
        currency = currency.upper()

        if currency == "GBP":
            fx = _fx_rate("GBPEUR=X")
            if fx:
                price *= fx
        elif currency == "USD":
            fx = _fx_rate("EURUSD=X")
            if fx:
                price /= fx
        # else assume already EUR

        return round(price, 4)
    except Exception:
        return None


def days_held(entry_date_str: str) -> int | None:
    try:
        entry = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
        return (date.today() - entry).days
    except Exception:
        return None


def days_to_earnings(ticker: str, earnings: list) -> int | None:
    today = date.today()
    for e in earnings:
        if e.get("ticker", "").upper() == ticker.upper():
            try:
                ed    = datetime.strptime(e["earnings_date"], "%Y-%m-%d").date()
                delta = (ed - today).days
                if 0 <= delta <= 14:
                    return delta
            except Exception:
                pass
    return None


def main():
    trades   = load_trades()
    open_t   = [t for t in trades if t.get("status") == "open"]
    earnings = load_earnings()
    today    = str(date.today())

    if not open_t:
        print("\n  No open positions.\n")
        return

    print(f"\n  {'='*64}")
    print(f"  POSITION MONITOR — {today}  ({len(open_t)} open)")
    print(f"  {'='*64}")

    action_required = []

    for t in open_t:
        ticker    = t["ticker"]
        entry     = t["entry_price"]
        stop      = t.get("stop_price")
        target    = t.get("target_price")
        qty       = t["qty"]
        conv      = t.get("conviction") or "—"
        direction = t.get("direction", "LONG")
        # "strategy" (POSITION/SWING/MOMENTUM/TURNAROUND/EVENT) drives the time stop and is
        # distinct from "setup_type" (breakout/pullback/reversal/consolidation) — trades logged
        # before --strategy existed, or without it set, fall back to the SWING time stop.
        strategy  = (t.get("strategy") or "").upper()
        if strategy not in TIME_STOPS:
            strategy = "SWING"
        setup_disp = (t.get("setup_type") or "—").upper()
        entry_date = t.get("entry_date", "")

        days       = days_held(entry_date)
        time_limit = TIME_STOPS[strategy]
        current    = get_price(ticker)
        dte        = days_to_earnings(ticker, earnings)

        # P&L
        if current:
            move    = (current - entry) if direction == "LONG" else (entry - current)
            pnl     = move * qty
            pnl_pct = pnl / (entry * qty) * 100
        else:
            pnl = pnl_pct = None

        # Stop distance
        stop_dist = None
        if stop and current:
            stop_dist = ((current - stop) if direction == "LONG" else (stop - current)) / current * 100

        # Target progress
        target_pct = None
        if target and current:
            planned    = abs(target - entry)
            actual     = (current - entry) if direction == "LONG" else (entry - current)
            target_pct = (actual / planned * 100) if planned else None

        # R-multiple
        r_val = None
        if stop and current:
            risk  = abs(entry - stop)
            move  = (current - entry) if direction == "LONG" else (entry - current)
            r_val = round(move / risk, 2) if risk else None

        # ── Flags ─────────────────────────────────────────────────────────
        flags = []

        if not stop:
            flags.append(("⛔", "NO_STOP — set immediately"))
            action_required.append(f"⛔ {ticker}: no stop recorded")
        elif stop_dist is not None:
            if stop_dist < 0:
                flags.append(("⛔", f"STOP HIT (price {current:.2f} past stop {stop:.2f})"))
                action_required.append(f"⛔ {ticker}: STOP HIT — exit required")
            elif stop_dist < 3:
                flags.append(("⛔", f"CRITICAL — {stop_dist:.1f}% from stop"))
                action_required.append(f"⛔ {ticker}: {stop_dist:.1f}% from stop")
            elif stop_dist < 7:
                flags.append(("⚠ ", f"NEAR STOP — {stop_dist:.1f}% away"))
                action_required.append(f"⚠  {ticker}: near stop ({stop_dist:.1f}%)")

        if days is not None and days >= time_limit and (target_pct is None or target_pct < 50):
            prog = f"{target_pct:.0f}% toward target" if target_pct is not None else "no target set"
            flags.append(("⚠ ", f"TIME STOP — day {days}/{time_limit} ({prog})"))
            action_required.append(f"⚠  {ticker}: time stop (day {days}/{time_limit})")

        if dte is not None and dte <= 3:
            flags.append(("⚠ ", f"EARNINGS IN {dte}d — decide: hold or exit"))
            action_required.append(f"⚠  {ticker}: earnings in {dte}d")
        elif dte is not None and dte <= 7:
            flags.append(("ℹ ", f"Earnings in {dte}d — monitor"))

        if r_val is not None and r_val >= 1.0 and (stop_dist or 0) > 10:
            flags.append(("✦ ", f"TRAIL SIGNAL — at +{r_val:.1f}R, move stop to break-even"))
            action_required.append(f"✦  {ticker}: trail stop (+{r_val:.1f}R)")

        if target_pct is not None and target_pct >= 80:
            flags.append(("✦ ", f"NEAR TARGET — {target_pct:.0f}% of the way there"))

        # ── Print ──────────────────────────────────────────────────────────
        now_s    = f"€{current:.2f}" if current else "—"
        pnl_s    = f"€{pnl:+,.0f} ({pnl_pct:+.1f}%)" if pnl is not None else "—"
        stop_s   = f"€{stop:.2f}" if stop else "NONE"
        tgt_s    = f"€{target:.2f}" if target else "—"
        r_s      = (f"+{r_val:.1f}R" if r_val and r_val > 0 else f"{r_val:.1f}R") if r_val else "—"
        days_s   = f"Day {days}/{time_limit}" if days is not None else "—"
        tpct_s   = f"  {target_pct:.0f}% → target" if target_pct is not None else ""

        print(f"\n  ── {ticker:<10} [{strategy}] [{setup_disp}] [{conv}] {direction} ──")
        print(f"     Entry €{entry:.2f} → Now {now_s} | P&L {pnl_s} | R: {r_s}")
        print(f"     Stop {stop_s} | Target {tgt_s}{tpct_s}")
        print(f"     {days_s} | {'Earnings ' + str(dte) + 'd' if dte is not None else 'No earnings near'}")

        for marker, msg in flags:
            print(f"     {marker} {msg}")

    # ── Action summary ─────────────────────────────────────────────────────
    if action_required:
        print(f"\n  {'='*64}")
        print(f"  ACTIONS REQUIRED ({len(action_required)})")
        print(f"  {'─'*64}")
        for a in action_required:
            print(f"  {a}")

    print()


if __name__ == "__main__":
    main()
