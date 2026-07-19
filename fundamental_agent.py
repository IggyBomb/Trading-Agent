#!/usr/bin/env python3
"""
fundamental_agent.py — Fundamental analysis layer
Reads High/Medium conviction tickers from market_data.json,
fetches fundamental data via yfinance, scores each on value/quality/growth,
and writes data/fundamental_data.json.

Run after fetch_data.py:
  python3 fetch_data.py
  python3 fundamental_agent.py
"""

# this is a test
# ═════════════════════════════════════════════════════════════════════════════
#  SCORING REVIEW — functions tagged "REVIEW(scoring)" define the fundamental
#  score bands, the 40/40/20 composite weights, and the rating thresholds.
#  All hand-picked and sector-blind — they need a second opinion.
#  Search for: REVIEW(scoring)
# ═════════════════════════════════════════════════════════════════════════════

import json
import os
import sys
import time
from datetime import datetime
import logging
log = logging.getLogger("fundamental_agent")


try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

# ── Config ───────────────────────────────────────────────────────────────────
from config import CONVICTION_FILTER, MARKET_DATA_PATH, FUNDAMENTAL_PATH

REQUEST_PAUSE = 0.3   # seconds between yfinance .info calls

# ── Scoring weights ───────────────────────────────────────────────────────────
# Each dimension scored 0–10, combined into 0–100 total.
# Value 40% | Quality 40% | Growth 20%

#Review of the weights , better to put then as equal weight since is just a model for now so 0,33 - 0,33 - 0,34 (quality has 0,34)

# Helper — dict lookup that also treats NaN as a missing value.
def _safe(d, key, default=None):
    v = d.get(key, default)
    if v is None or (isinstance(v, float) and (v != v)):  # NaN check
        return default
    return v


# REVIEW(scoring): value/cheapness 0–10. Points: P/E up to +3 (bands 12/20/30,
# negative P/E −1), P/B up to +3 (bands 1/2/3), EV/EBITDA up to +2 (bands 8/15),
# PEG up to +2 (bands 1.0/1.5). Max raw = 10. All band edges are hand-picked and
# applied to every sector alike (a bank and a SaaS company get the same bands).
def score_value(info):
    """Score cheapness: P/E, P/B, EV/EBITDA, PEG. Returns 0-10."""
    score = 0.0

#PE increased parameter due to the tech leading markets, always for a model, these numbers should all change depending on the sector (a good pe for tech is 30 but is high for industrials and so on)

    pe = _safe(info, "trailingPE")
    if pe is not None:
        if pe < 0:
            score -= 1
        elif pe < 18:
            score += 3
        elif pe < 25:
            score += 2
        elif pe < 34:
            score += 1

    pb = _safe(info, "priceToBook")
    if pb is not None and pb > 0:
        if pb < 0.75:
            score += 3
        elif pb < 1.5:
            score += 2
        elif pb < 3.0:
            score += 1

    ev_ebitda = _safe(info, "enterpriseToEbitda")
    if ev_ebitda is not None and ev_ebitda > 0:
        if ev_ebitda < 8:
            score += 2
        elif ev_ebitda < 15:
            score += 1

    peg = _safe(info, "pegRatio")
    if peg is not None and peg > 0:
        if peg < 1.0:
            score += 2
        elif peg < 1.5:
            score += 1

    return round(min(max(score, 0), 10), 2)


# REVIEW(scoring): business quality 0–10. Points: ROE up to +3 (bands 25%/15%/5%),
# profit margin up to +2.5 (bands 20%/10%/5%), debt/equity up to +2.5 (bands
# 0.3/0.7/1.5, heavy leverage −1), positive FCF +2 (negative −0.5).
# NOTE: yfinance returns debtToEquity as a percentage — divided by 100 here.
def score_quality(info):
    """Score business quality: ROE, margins, debt, FCF. Returns 0-10."""
    score = 0.0

    roe = _safe(info, "returnOnEquity")
    if roe is not None:
        if roe > 0.25:
            score += 3
        elif roe > 0.15:
            score += 2
        elif roe > 0.05:
            score += 1

    margin = _safe(info, "profitMargins")
    if margin is not None:
        if margin > 0.20:
            score += 2.5
        elif margin > 0.10:
            score += 1.5
        elif margin > 0.05:
            score += 0.5

    de = _safe(info, "debtToEquity")
    if de is not None:
        de_ratio = de / 100.0  # yfinance returns as percentage
        if de_ratio < 0.3:
            score += 2.5
        elif de_ratio < 0.7:
            score += 1.5
        elif de_ratio < 1.5:
            score += 0.5
        else:
            score -= 1

    fcf = _safe(info, "freeCashflow")
    if fcf is not None:
        if fcf > 0:
            score += 2
        else:
            score -= 0.5

    return round(min(max(score, 0), 10), 2)


# REVIEW(scoring): growth 0–10. Points: revenue growth up to +3 (bands 20%/10%/3%),
# earnings growth up to +3 (same bands), forward P/E below trailing +2 (if >10%
# lower) or +1 (any lower) — a proxy for "earnings expected to improve".
def score_growth(info):
    """Score momentum: revenue growth, earnings growth, forward vs trailing PE. Returns 0-10."""
    score = 0.0

    rev_growth = _safe(info, "revenueGrowth")
    if rev_growth is not None:
        if rev_growth > 0.20:
            score += 3
        elif rev_growth > 0.10:
            score += 2
        elif rev_growth > 0.03:
            score += 1

    earn_growth = _safe(info, "earningsGrowth")
    if earn_growth is not None:
        if earn_growth > 0.20:
            score += 3
        elif earn_growth > 0.10:
            score += 2
        elif earn_growth > 0.03:
            score += 1

    # Improving earnings: forward P/E lower than trailing P/E
    fwd_pe = _safe(info, "forwardPE")
    tr_pe  = _safe(info, "trailingPE")
    if fwd_pe and tr_pe and fwd_pe > 0 and tr_pe > 0:
        if fwd_pe < tr_pe * 0.90:
            score += 2
        elif fwd_pe < tr_pe:
            score += 1

    return round(min(max(score, 0), 10), 2)


# REVIEW(scoring): maps the 0–100 composite to a label — ≥62 "Undervalued",
# 40–61 "Fair", <40 "Overvalued". The 62/40 cutoffs are arbitrary; review whether
# they produce a sensible distribution across a real run.
def fundamental_rating(total_score):
    if total_score >= 62:
        return "Undervalued"
    if total_score >= 40:
        return "Fair"
    return "Overvalued"


# REVIEW(scoring): pulls yfinance .info for one ticker and combines the three
# sub-scores into the 0–100 composite HERE: value×4 + quality×4 + growth×2
# (i.e. the 40/40/20 weighting). Also note the blanket `except: return None` —
# it hides whether a failure was a fetch error or a scoring bug (known issue).
def fetch_fundamentals(ticker):
    """Returns a dict of scored fundamental data for one ticker."""
    try:
        info = yf.Ticker(ticker).info
        if not info or len(info) < 5:
            return None

        value = score_value(info)
        quality = score_quality(info)
        growth = score_growth(info)
        log.debug(f"{ticker}: value={value} quality={quality} growth={growth}")

        # Weighted composite: value 40%, quality 40%, growth 20%
        total = round((value * 4.0) + (quality * 4.0) + (growth * 2.0), 1)  # max = 100

        return {
            "ticker":          ticker,
            "f_score":         total,
            "value_score":     value,
            "quality_score":   quality,
            "growth_score":    growth,
            "rating":          fundamental_rating(total),
            # Raw metrics for transparency
            "pe":              _safe(info, "trailingPE"),
            "fwd_pe":          _safe(info, "forwardPE"),
            "pb":              _safe(info, "priceToBook"),
            "ev_ebitda":       _safe(info, "enterpriseToEbitda"),
            "peg":             _safe(info, "pegRatio"),
            "roe":             round(_safe(info, "returnOnEquity", 0) * 100, 1),
            "profit_margin":   round(_safe(info, "profitMargins", 0) * 100, 1),
            "debt_equity":     round((_safe(info, "debtToEquity", 0) or 0) / 100, 2),
            "revenue_growth":  round((_safe(info, "revenueGrowth", 0) or 0) * 100, 1),
            "earnings_growth": round((_safe(info, "earningsGrowth", 0) or 0) * 100, 1),
            "fcf_positive":    (_safe(info, "freeCashflow") or 0) > 0,
            "market_cap":      _safe(info, "marketCap"),
            "sector":          _safe(info, "sector", "Unknown"),
            "industry":        _safe(info, "industry", "Unknown"),
        }
    except Exception:
        return None


# ── Main ─────────────────────────────────────────────────────────────────────

# Orchestration: loads market_data.json, scores every ticker whose conviction is
# in CONVICTION_FILTER (High/Medium), writes data/fundamental_data.json sorted by f_score.
def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s  %(message)s",
        datefmt="%H:%M:%S",)
    log.info("run started")

    if not os.path.exists(MARKET_DATA_PATH):
        log.error(f"{MARKET_DATA_PATH} not found — run fetch_data.py first")
        sys.exit(1)

    with open(MARKET_DATA_PATH) as f:
        market_data = json.load(f)

    # Only process tickers that passed the technical filter
    candidates = [
        s["ticker"] for s in market_data["signals"]
        if s["conviction"] in CONVICTION_FILTER
    ]
    log.info(f"{len(candidates)} High/Medium conviction candidates to score")

    results  = {}
    errors   = []
    total    = len(candidates)

    for i, ticker in enumerate(candidates, 1):
        data = fetch_fundamentals(ticker)
        if data:
            results[ticker] = data
            log.debug(f"[{i}/{total}] {ticker} f_score={data['f_score']} {data['rating']}")
        else:
            errors.append(ticker)
            log.warning(f"[{i}/{total}] {ticker}: no data")
        time.sleep(REQUEST_PAUSE)

    # Sort by f_score descending
    sorted_results = dict(
        sorted(results.items(), key=lambda x: x[1]["f_score"], reverse=True)
    )

    undervalued = [t for t, d in sorted_results.items() if d["rating"] == "Undervalued"]
    fair        = [t for t, d in sorted_results.items() if d["rating"] == "Fair"]
    overvalued  = [t for t, d in sorted_results.items() if d["rating"] == "Overvalued"]

    output = {
        "summary": {
            "generated_at":  datetime.now().isoformat(),
            "total_scored":  len(results),
            "total_errors":  len(errors),
            "undervalued":   len(undervalued),
            "fair":          len(fair),
            "overvalued":    len(overvalued),
            "scoring": {
                "value_weight":   "40%",
                "quality_weight": "40%",
                "growth_weight":  "20%",
                "undervalued_threshold": "≥ 62",
                "fair_threshold":        "40–61",
                "overvalued_threshold":  "< 40",
            },
        },
        "fundamentals": sorted_results,
    }

    os.makedirs("./data", exist_ok=True)
    with open(FUNDAMENTAL_PATH, "w") as f:
        json.dump(output, f, indent=2)

    log.info(f"run finished: scored={len(results)} errors={len(errors)} | "
             f"undervalued={len(undervalued)} fair={len(fair)} overvalued={len(overvalued)} | "
             f"saved to {FUNDAMENTAL_PATH}")

    # ── Report (for the human reader — stays print, not telemetry) ──────────
    print(f"\nTop Undervalued with high f_score:")
    print(f"{'─'*60}")
    for ticker in list(undervalued)[:10]:
        d = sorted_results[ticker]
        print(f"  {ticker:<10} f={d['f_score']:>5.1f}  "
              f"V={d['value_score']} Q={d['quality_score']} G={d['growth_score']}  "
              f"{d['sector']}")
    print(f"\nNow run /scan in Claude Code to see fundamentals alongside technicals.\n")


if __name__ == "__main__":
    main()
