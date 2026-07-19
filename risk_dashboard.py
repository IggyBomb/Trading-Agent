#!/usr/bin/env python3
"""
risk_dashboard.py — Live portfolio risk snapshot

Usage:
  python3 risk_dashboard.py              — full dashboard with live prices
  python3 risk_dashboard.py --no-prices  — offline mode (skip price fetch)
"""

import json, sys, os, argparse
from datetime import datetime, date, timedelta
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

from config import ACCOUNT_SIZE, TRADES_PATH, SENTIMENT_PATH, EARNINGS_PATH

LOGS_PATH = TRADES_PATH


def dynamic_max_pct(conviction=None, sd=None):
    if sd is None:
        sd = {}
    fg      = (sd.get("cnn_fear_greed") or {}).get("score")
    comp    = sd.get("composite_score") or 50
    eu_comp = sd.get("eu_composite_score") or 0
    vix     = (sd.get("vix") or {}).get("value")
    vstoxx  = (sd.get("eu_internals") or {}).get("vstoxx")
    conv    = (conviction or "").upper()

    if fg is not None and fg > 75:
        return 1.0, "HALF",   f"F&G {fg:.0f} — extreme greed"
    if vix and vix > 30:
        return 1.0, "HALF",   f"VIX {vix:.1f} — high-vol"
    if vstoxx and vstoxx > 25:
        return 1.0, "HALF",   f"VSTOXX {vstoxx:.1f} — EU high-vol"
    if conv == "HIGH" and fg is not None and fg <= 30 and comp >= 55 and eu_comp >= 58:
        return 5.0, "MAX",    f"F&G {fg:.0f} + comp {comp:.0f} + EU {eu_comp:.0f} + HIGH"
    if conv == "HIGH" and fg is not None and fg <= 45 and comp >= 55:
        return 4.0, "STRONG", f"F&G {fg:.0f} + comp {comp:.0f} + HIGH"
    if fg is not None and fg <= 50 and comp >= 48:
        return 3.0, "GOOD",   f"F&G {fg:.0f} + comp {comp:.0f}"
    return 2.0, "NORMAL", "default"


def load_trades():
    if not Path(LOGS_PATH).exists():
        return []
    with open(LOGS_PATH) as f:
        return [json.loads(l) for l in f if l.strip()]


def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def get_live_price(ticker):
    try:
        info  = yf.Ticker(ticker).info
        price = (info.get("currentPrice") or info.get("regularMarketPrice")
                 or info.get("previousClose"))
        return float(price) if price else None
    except Exception:
        return None


def days_to_earnings(ticker, earnings_list):
    today = date.today()
    for e in earnings_list:
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
    parser = argparse.ArgumentParser(prog="risk_dashboard")
    parser.add_argument("--no-prices", action="store_true", help="Skip live price fetch")
    args = parser.parse_args()

    trades  = load_trades()
    open_t  = [t for t in trades if t.get("status") == "open"]
    closed_t = [t for t in trades if t.get("status") == "closed"]
    sd       = load_json(SENTIMENT_PATH)

    raw_earnings = load_json(EARNINGS_PATH, default=[])
    if isinstance(raw_earnings, dict):
        raw_earnings = raw_earnings.get("earnings", [])
    earnings = raw_earnings if isinstance(raw_earnings, list) else []

    today_str    = str(date.today())
    today_closed = [t for t in closed_t if (t.get("exit_date") or "") == today_str]
    daily_pnl    = sum(t.get("pnl_eur", 0) or 0 for t in today_closed)
    daily_dd_pct = abs(min(daily_pnl, 0)) / ACCOUNT_SIZE * 100

    _, tier, tier_reason = dynamic_max_pct(sd=sd)

    fg_data = sd.get("cnn_fear_greed") or {}
    fg      = fg_data.get("score")
    comp    = sd.get("composite_score")
    eu_comp = sd.get("eu_composite_score")

    print(f"\n  {'='*64}")
    print(f"  RISK DASHBOARD — {today_str}")
    print(f"  {'='*64}")

    # ── Market context ────────────────────────────────────────────────────
    print(f"\n  MARKET CONTEXT")
    if fg is not None:
        print(f"  F&G:        {fg:.1f}  ({fg_data.get('rating', '—')})")
    if comp is not None:
        print(f"  Composite:  {comp:.1f}  ({sd.get('composite_label', '—')})")
    if eu_comp is not None:
        print(f"  EU Comp:    {eu_comp:.1f}  ({sd.get('eu_composite_label', '—')})")
    print(f"  Active tier: [{tier}] — {tier_reason}")

    dd_flag = "  ⛔ NEAR LIMIT" if daily_dd_pct >= 2.5 else ""
    print(f"  Daily P&L:   €{daily_pnl:+,.2f}  ({daily_dd_pct:.2f}% of 3% limit used){dd_flag}")

    if not open_t:
        print(f"\n  No open positions.\n")
        return

    # ── Open positions ────────────────────────────────────────────────────
    print(f"\n  OPEN POSITIONS  ({len(open_t)}/5 max)")
    print(f"  {'─'*64}")

    total_exposure = 0
    sector_counts: dict[str, list] = {}
    all_violations = []

    for t in open_t:
        ticker    = t["ticker"]
        entry     = t["entry_price"]
        qty       = t["qty"]
        stop      = t.get("stop_price")
        target    = t.get("target_price")
        conv      = t.get("conviction") or "—"
        direction = t.get("direction", "LONG")
        pos_val   = t.get("position_value", entry * qty)
        total_exposure += pos_val

        current = get_live_price(ticker) if not args.no_prices else None

        # P&L
        if current:
            live_pnl = ((entry - current) if direction == "SHORT" else (current - entry)) * qty
            live_pct = live_pnl / pos_val * 100
        else:
            live_pnl = live_pct = None

        # Stop proximity
        stop_flag = ""
        stop_dist = None
        if stop and current:
            stop_dist = ((current - stop) if direction == "LONG" else (stop - current)) / current * 100
            if stop_dist < 0:
                stop_flag = " ⛔ STOP HIT"
                all_violations.append(f"{ticker}: STOP HIT — exit required")
            elif stop_dist < 5:
                stop_flag = " ⚠ NEAR STOP"
        elif not stop:
            stop_flag = " ⚠ NO STOP"
            all_violations.append(f"{ticker}: NO_STOP_RECORDED")

        # Target progress
        target_prog = ""
        if target and current and stop:
            planned = abs(target - entry)
            actual  = (current - entry) if direction == "LONG" else (entry - current)
            pct     = actual / planned * 100 if planned else 0
            target_prog = f"  {pct:.0f}% → target"

        # R-multiple (for trail signal)
        r_flag = ""
        if stop and current:
            risk  = abs(entry - stop)
            move  = (current - entry) if direction == "LONG" else (entry - current)
            r_val = move / risk if risk else 0
            if r_val >= 1.0 and (stop_dist or 0) > 10:
                r_flag = f"  ✦ TRAIL STOP (+{r_val:.1f}R)"

        # Sizing check
        max_pct, pos_tier, _ = dynamic_max_pct(conviction=conv if conv != "—" else None, sd=sd)
        pos_pct = pos_val / ACCOUNT_SIZE * 100
        size_flag = "  ⛔ OVERSIZE" if pos_pct > max_pct else ""

        # Earnings
        dte     = days_to_earnings(ticker, earnings)
        dte_s   = f"  ⚠ EARNINGS IN {dte}d" if dte is not None and dte <= 5 else ""

        # Output row
        now_s   = f"€{current:.2f}" if current else "—"
        pnl_s   = f"€{live_pnl:+,.0f} ({live_pct:+.1f}%)" if live_pnl is not None else "—"
        stop_s  = f"€{stop:.2f}" if stop else "NONE"
        tgt_s   = f"€{target:.2f}" if target else "—"
        dist_s  = f"  stop dist {stop_dist:.1f}%" if stop_dist is not None else ""

        print(f"\n  {ticker:<10} {direction:<6} | entry €{entry:.2f} → now {now_s} | P&L {pnl_s}")
        print(f"  {'':10}        | size {pos_pct:.1f}% (max {max_pct:.0f}% [{pos_tier}]){size_flag}")
        print(f"  {'':10}        | stop {stop_s}{stop_flag}{dist_s} | target {tgt_s}{target_prog}")
        if r_flag or dte_s:
            print(f"  {'':10}        |{r_flag}{dte_s}")

        # Track for violation summary
        for v in (t.get("rule_violations") or []):
            all_violations.append(f"{ticker}: {v}")

    # ── Totals ────────────────────────────────────────────────────────────
    exp_pct = total_exposure / ACCOUNT_SIZE * 100
    print(f"\n  {'─'*64}")
    print(f"  Total exposure:  €{total_exposure:,.0f}  ({exp_pct:.1f}% of €{ACCOUNT_SIZE:,})")

    if len(open_t) >= 5:
        print(f"  ⛔ MAX POSITIONS REACHED (5/5) — no new trades until one closes")
    elif len(open_t) == 4:
        print(f"  ⚠  1 slot remaining before max positions")

    # ── Violations ────────────────────────────────────────────────────────
    if all_violations:
        print(f"\n  ACTIVE VIOLATIONS ({len(all_violations)})")
        for v in all_violations:
            print(f"    ⚠  {v}")

    # ── Drawdown ──────────────────────────────────────────────────────────
    remaining = max(0, ACCOUNT_SIZE * 0.03 - abs(min(daily_pnl, 0)))
    print(f"\n  DRAWDOWN STATUS")
    print(f"  Daily P&L:          €{daily_pnl:+,.2f}  ({daily_dd_pct:.2f}% used / 3.00% limit)")
    print(f"  Remaining capacity: €{remaining:,.0f}")

    print()


if __name__ == "__main__":
    main()
