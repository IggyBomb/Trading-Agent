#!/usr/bin/env python3
"""
watchlist_monitor.py — Live price/volume trigger check for near-decision-level tickers.

Companion to price_alert_monitor.py, which watches OPEN positions against stop/target.
This one watches PRE-ENTRY candidates against a key level (support, resistance, MA50,
MA200) plus a volume-confirmation threshold. Backs /scan Step 12.

Volume methodology (read this before changing the threshold logic):
Same-day cumulative volume compared against a full 20-day average is systematically
biased low until late in the session — e.g. 20% into the trading day looks like "0.2x
average volume" even on a completely normal day, because only 20% of the day's volume
has had a chance to print. This script instead projects a full session's volume from
the elapsed fraction of the NYSE session (9:30-16:00 ET) before comparing to the 20-day
average. Do not compare raw same-day volume to a full-day average — it reads "thin" all
day regardless of actual participation. This was found and fixed live in session; the
projection still assumes a flat intraday volume pace, which itself under/overstates
early-session and late-session reality (real intraday volume is U-shaped) — treat the
projected ratio as directional, and weight a late-session check (last 30-60 min) more
heavily than an early one.

Usage:
  Explicit watch (one ticker, one level):
    python3 watchlist_monitor.py TICKER --level 139.31 --direction above \\
        --entry 140.53 --stop 137.055 --target 145.7425 [--vol-threshold 1.5]

  Auto-detect near-trigger candidates from the latest /scan output:
    python3 watchlist_monitor.py --auto [--within-pct 2.0]
    (reads market_data.json signals — flags High/Medium conviction tickers within
     --within-pct of support, resistance, MA50, or MA200)

Requires SSL_CERT_FILE / CURL_CA_BUNDLE set if this machine needs the merged CA bundle
(see .trading_certs/build_bundle.py) — same as every other yfinance-based script here.
"""
import argparse
import json
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from config import MARKET_DATA_PATH

ET = ZoneInfo("America/New_York")


def market_status(now_et=None):
    """Coarse session state — does not account for market holidays, only weekday +
    9:30-16:00 ET regular hours. Good enough to gate the volume projection; not a
    full trading calendar."""
    now_et = now_et or datetime.now(ET)
    open_ = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    close_ = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    if now_et.weekday() >= 5:
        return "WEEKEND"
    if now_et < open_:
        return "PRE_MARKET"
    if now_et >= close_:
        return "AFTER_CLOSE"
    return "OPEN"


def session_elapsed_fraction(now_et=None):
    """Only meaningful when the market is OPEN — caller must check market_status()
    first. Returns None otherwise so a stale/absurd projection can't be computed
    (found live: calling this pre-market divided a full completed day's volume by a
    near-zero elapsed fraction and produced a >10,000x "volume ratio")."""
    now_et = now_et or datetime.now(ET)
    status = market_status(now_et)
    if status == "PRE_MARKET" or status == "WEEKEND":
        return None
    if status == "AFTER_CLOSE":
        return 1.0
    open_ = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    close_ = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    return (now_et - open_).total_seconds() / (close_ - open_).total_seconds()


def check_ticker(ticker, level, direction, entry, stop, target, vol_threshold=1.5, min_rr=1.5):
    """`holding_level` alone is not sufficient for "wait for a pullback to X" watches:
    it only checks price is on the right side of `level`, which is trivially true for
    a stock that never actually pulled back and is still sitting far above it. Found
    live on 2026-08-24: TGT was watched with level=161 (a named pullback zone) and
    direction=above; price never came down to 161, it stayed at ~170, so "holding
    above 161" was true by default and the tool reported SIGNAL FIRED with R:R=0.26 —
    a terrible entry, not a confirmation. min_rr gates the signal on the trade still
    being worth taking at the CURRENT price, not just on which side of the level it's
    on. Default 1.5 matches RISK.md's minimum R:R requirement — do not lower this to
    make a signal fire; that defeats the purpose of the gate.
    """
    hist = yf.download(ticker, period="30d", interval="1d", progress=False, auto_adjust=True)
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.droplevel(1)
    last = float(hist["Close"].iloc[-1])
    today_vol = float(hist["Volume"].iloc[-1])
    avg20 = float(hist["Volume"].iloc[-21:-1].mean())
    status = market_status()
    frac = session_elapsed_fraction()
    projected_ratio = (today_vol / frac) / avg20 if (avg20 and frac) else None

    holding = (last > level) if direction == "above" else (last < level)
    # No intraday volume exists to confirm anything while the market is closed —
    # never treat a closed-market read as volume confirmation, regardless of price.
    volume_confirmed = status == "OPEN" and projected_ratio is not None and projected_ratio >= vol_threshold

    # Trade structure (long vs short) is NOT the same thing as `direction` (which
    # side of `level` triggers the check) — a long dip-buy watch legitimately uses
    # direction="below" (waiting for price to drop INTO a lower entry zone) while
    # still being a long trade: stop below entry, target above. The old code keyed
    # the risk/reward formula off `direction` alone, so a long pullback watch got
    # the short-side formula (risk = stop-last, reward = last-target) — with a
    # long-style stop/target that always produces a negative risk_now, so rr_now
    # was silently None forever regardless of price. Found live 2026-08-25: a TGT
    # pullback watch sat exactly on its entry zone with 5x volume and still
    # couldn't fire. Infer long/short from target vs entry instead, independent
    # of direction.
    is_long = target >= entry
    if is_long:
        risk_now = last - stop
        reward_now = target - last
    else:
        risk_now = stop - last
        reward_now = last - target
    rr_now = round(reward_now / risk_now, 2) if risk_now and risk_now > 0 else None
    rr_confirmed = rr_now is not None and rr_now >= min_rr

    signal = holding and volume_confirmed and rr_confirmed

    return {
        "ticker": ticker,
        "price": round(last, 2),
        "level": level,
        "direction": direction,
        "holding_level": holding,
        "market_status": status,
        "projected_vol_ratio": round(projected_ratio, 2) if projected_ratio else None,
        "vol_threshold": vol_threshold,
        "volume_confirmed": volume_confirmed,
        "rr_now": rr_now,
        "min_rr": min_rr,
        "rr_confirmed": rr_confirmed,
        "signal": signal,
        "session_elapsed_pct": round(frac * 100, 1) if frac else 0.0,
    }


CONFIRMED_LIST_PATH = "./scan_step1_4_output.json"


def auto_detect(within_atr=0.2, confirmed_path=CONFIRMED_LIST_PATH, conviction_filter=None):
    """Flag CONFIRMED tickers genuinely worth a live watch. Deliberately narrow — two
    mechanical checks only, run across the FULL CONFIRMED list (not just HIGH
    conviction), cross-referenced back into market_data.json for the fields they need:

    1. DUAL_SIGNAL — the ticker has both a long setup AND a live short_setup flag in
       the same market_data.json pull (a genuine same-session disagreement between the
       long screen and the short screen — rare, and worth resolving live rather than
       guessing which side is right).
    2. STRUCTURAL_GATE — price is very close (tight ATR band) to MA50 or MA200
       specifically, NOT support/resistance. The moving averages are an independent
       structural read (Weinstein stage, trend confirmation) that the entry/stop/target
       math doesn't already encode, so proximity there is informative rather than
       tautological.

    A blind "is price within X ATR of its own support/resistance" filter was tried and
    discarded — every scanned entry is close to its own pivot/support/resistance by
    construction (that's how the entry, stop, and target were derived in the first
    place), so a loose version of that check matches nearly the whole scan output and
    tells you nothing.

    IMPORTANT LIMITATION: this only covers the two mechanical checks. A third category
    — a ticker whose STRATEGY VERDICT/RISK MANAGER output explicitly said "don't chase,
    wait for a pullback to X" during the Steps 5-9 deep-dive — cannot be detected here.
    That judgment only exists for tickers that actually went through the full agent
    pipeline (mandatory for HIGH conviction, optional for Medium), so most of the
    CONFIRMED list was never analysed deeply enough to produce it. Cross-check the
    output of this function against any deep-dive verdicts you already have before
    treating the combined list as complete — this was under-applied once already in
    this session (NEM/TGT/EL/MRK/BDX all had explicit "wait for pullback" language that
    got missed because only ALB was manually cross-checked).

    Requires ./scan_step1_4_output.json (the Step 2 CONFIRMED/CAUTION cross-reference
    output) to exist — falls back to scanning market_data.json's own High/Medium
    conviction signals directly (unfiltered by fundamental rating) if it's missing,
    and flags that fallback explicitly rather than silently returning a different set.
    """
    with open(MARKET_DATA_PATH) as f:
        market = {s["ticker"]: s for s in json.load(f).get("signals", [])}

    try:
        with open(confirmed_path) as f:
            confirmed_tickers = {r["ticker"] for r in json.load(f)["confirmed"]}
        used_fallback = False
    except (FileNotFoundError, KeyError):
        confirmed_tickers = {t for t, s in market.items() if s.get("conviction") in ("High", "Medium")}
        used_fallback = True

    candidates = []
    for ticker in confirmed_tickers:
        s = market.get(ticker)
        if not s:
            continue
        if conviction_filter and s.get("conviction") != conviction_filter:
            continue
        price = s.get("price")
        atr = s.get("atr")
        if price is None or not atr:
            continue
        reasons = []

        if s.get("short_setup") and s["short_setup"] not in ("none", "None", None):
            reasons.append(("DUAL_SIGNAL", f"short_setup={s['short_setup']} ({s.get('short_conviction')})"))

        for label, ma in (("ma50", s.get("ma50")), ("ma200", s.get("ma200"))):
            if ma and abs(price - ma) / atr < within_atr:
                direction = "above" if price >= ma else "below"
                reasons.append(("STRUCTURAL_GATE", f"{label} {ma:.2f} ({direction})"))

        if reasons:
            candidates.append({
                "ticker": ticker, "price": price, "conviction": s.get("conviction"),
                "setup": s.get("setup"), "reasons": reasons,
            })
    candidates.sort(key=lambda c: (c["conviction"] != "High", c["ticker"]))
    return candidates, used_fallback


def main():
    p = argparse.ArgumentParser()
    p.add_argument("ticker", nargs="?")
    p.add_argument("--level", type=float)
    p.add_argument("--direction", choices=["above", "below"], default="above")
    p.add_argument("--entry", type=float)
    p.add_argument("--stop", type=float)
    p.add_argument("--target", type=float)
    p.add_argument("--vol-threshold", type=float, default=1.5)
    p.add_argument("--min-rr", type=float, default=1.5,
                    help="Minimum R:R at the CURRENT price required for a signal to fire (default 1.5, matches RISK.md)")
    p.add_argument("--auto", action="store_true")
    p.add_argument("--within-atr", type=float, default=0.2)
    p.add_argument("--conviction", choices=["High", "Medium"], default=None,
                    help="Restrict --auto to one conviction tier (default: both)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.auto:
        candidates, used_fallback = auto_detect(args.within_atr, conviction_filter=args.conviction)
        if args.json:
            print(json.dumps({"used_fallback": used_fallback, "candidates": candidates}, indent=2))
        else:
            if used_fallback:
                print(f"⚠ {CONFIRMED_LIST_PATH} not found — scanning ALL High/Medium conviction "
                      f"tickers directly from market_data.json (unfiltered by fundamental rating).\n")
            if not candidates:
                print("No CONFIRMED tickers show a dual-signal conflict or tight MA proximity right now.")
            for c in candidates:
                reason_str = "; ".join(f"{tag}: {detail}" for tag, detail in c["reasons"])
                print(f"{c['ticker']:<8} conv={c['conviction']:<7} setup={c['setup']:<13} price={c['price']:<10} {reason_str}")
            print(f"\n{len(candidates)} candidate(s) via DUAL_SIGNAL/STRUCTURAL_GATE. This does NOT include "
                  f"judgment-call watches from Steps 7-9 deep-dive verdicts (e.g. explicit \"don't chase, "
                  f"wait for pullback to X\") — cross-check those separately for any tickers that went "
                  f"through the full pipeline.")
        return

    if not args.ticker or args.level is None or args.entry is None or args.stop is None or args.target is None:
        p.error("explicit mode requires: ticker --level LEVEL --entry ENTRY --stop STOP --target TARGET")

    result = check_ticker(args.ticker, args.level, args.direction, args.entry, args.stop, args.target,
                           args.vol_threshold, args.min_rr)
    if args.json:
        print(json.dumps(result, indent=2))
    elif result["market_status"] != "OPEN":
        print(
            f"{result['ticker']}: MARKET {result['market_status']} — no volume confirmation possible. "
            f"Last price={result['price']} vs level={result['level']} ({result['direction']}) | holding={result['holding_level']} "
            f"| R:R at last price={result['rr_now']}"
        )
    else:
        status_str = "SIGNAL FIRED" if result["signal"] else "no signal"
        rr_flag = "OK" if result["rr_confirmed"] else "BELOW MIN"
        print(
            f"{result['ticker']}: {status_str} | price={result['price']} vs level={result['level']} ({result['direction']}) "
            f"| holding={result['holding_level']} | proj_vol={result['projected_vol_ratio']}x "
            f"(threshold {result['vol_threshold']}x) | R:R now={result['rr_now']} ({rr_flag}, min {result['min_rr']}) "
            f"| session {result['session_elapsed_pct']}% elapsed"
        )


if __name__ == "__main__":
    main()
