#!/usr/bin/env python3
"""
watchlist_ranker.py — Daily composite ranking of all processed tickers

Reads market_data.json, fundamental_data.json, alt_data.json, earnings_calendar.json.
Computes a composite score (0–100) and outputs the top-N ranked watchlist.

Usage:
  python3 watchlist_ranker.py              — top 50
  python3 watchlist_ranker.py --top 100    — top 100
  python3 watchlist_ranker.py --eu         — EU tickers only
  python3 watchlist_ranker.py --us         — US tickers only
"""

import json, os, sys, argparse
from datetime import datetime, date
from pathlib import Path

from config import (
    EU_SUFFIXES, MARKET_DATA_PATH, FUNDAMENTAL_PATH,
    ALT_DATA_PATH, EARNINGS_PATH, WATCHLIST_RANKED_PATH,
    MACRO_REGIME_PATH, SECTOR_ROTATION_PATH, BUBBLE_WATCH_PATH,
    SECTOR_RET_1M_THRESHOLD, SECTOR_RET_3M_THRESHOLD, SECTOR_THRESHOLD_TOLERANCE,
    BUBBLE_WATCH_MAX_AGE_HOURS, RESCUE_BW_TOP_CUTOFF,
)

MARKET_PATH   = MARKET_DATA_PATH
FUND_PATH     = FUNDAMENTAL_PATH
ALT_PATH      = ALT_DATA_PATH
EARNINGS_PATH = EARNINGS_PATH
OUTPUT_PATH   = WATCHLIST_RANKED_PATH
MACRO_PATH    = MACRO_REGIME_PATH
SECTOR_PATH   = SECTOR_ROTATION_PATH
BUBBLE_PATH   = BUBBLE_WATCH_PATH


def load_json(path: str) -> dict | list | None:
    if not Path(path).exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def load_bubble_watch(path: str, max_age_hours: float) -> dict:
    """Loads data/bubble_watch.json's `entries` dict, or {} when the file is
    missing, unreadable, or older than max_age_hours. Fail-closed on purpose:
    stale/absent bubble data must mean "gate stays shut", never "fall back to
    the old unconditional penalty" -- see regime_penalty()."""
    raw = load_json(path)
    if not isinstance(raw, dict):
        return {}
    generated_at = raw.get("generated_at")
    if not generated_at:
        return {}
    try:
        ts = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            from datetime import timezone
            ts = ts.replace(tzinfo=timezone.utc)
        from datetime import timezone
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        if age_hours > max_age_hours:
            return {}
    except Exception:
        return {}
    entries = raw.get("entries")
    return entries if isinstance(entries, dict) else {}


def is_eu(ticker: str) -> bool:
    dot = ticker.rfind(".")
    return dot != -1 and ticker[dot:].upper() in EU_SUFFIXES


def earnings_days_out(ticker: str, earnings: list) -> int | None:
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


def score_technical(t: dict) -> float:
    """Momentum + trend score from market_data.json ticker entry. Returns 0–100."""
    score = 50.0  # base

    # Conviction from fetch_data.py filters
    conv = (t.get("conviction") or "").upper()
    if conv == "HIGH":
        score += 20
    elif conv == "MEDIUM":
        score += 5


    # Price vs MAs
    close = t.get("close") or t.get("price") or 0
    ma50  = t.get("ma50")
    ma200 = t.get("ma200")
    if ma50  and close > ma50:  score += 8
    if ma50  and close < ma50:  score -= 8
    if ma200 and close > ma200: score += 7
    if ma200 and close < ma200: score -= 7

    # RSI
    rsi = t.get("rsi")
    if rsi:
        if 50 <= rsi <= 70:    score += 8   # momentum zone
        elif 40 <= rsi < 50:   score += 2   # near neutral
        elif rsi > 80:         score -= 8   # overbought
        elif rsi < 30:         score -= 8   # oversold (can be opportunity, but flag)

    # 52-week high proximity
    high52 = t.get("52w_high") or t.get("week52High")
    if high52 and close and high52 > 0:
        pct_from_high = (close - high52) / high52 * 100
        if pct_from_high >= 0:          score += 10  # AT or near 52w high
        elif pct_from_high >= -5:       score += 7
        elif pct_from_high >= -15:      score += 2
        elif pct_from_high <= -30:      score -= 5


    # Volume (relative to average)
    vol_ratio = t.get("volume_ratio")
    if vol_ratio and vol_ratio >= 2.0:   score += 8
    elif vol_ratio and vol_ratio >= 1.5: score += 4
    return max(0.0, min(100.0, score))


def score_fundamental(ticker: str, fund_data: dict) -> float:
    if not fund_data:
        return None
    entry = fund_data.get(ticker)
    if not entry:
        return None
    return float(entry.get("f_score") or entry.get("score") or entry.get("fundamental_score") or 50)


def score_alt(ticker: str, alt_data: dict) -> float | None:
    if not alt_data:
        return None
    tickers = alt_data.get("tickers") or alt_data
    entry   = tickers.get(ticker) if isinstance(tickers, dict) else None
    if not entry:
        return None
    return float(entry.get("alt_data_score") or entry.get("score") or 50)


# volatility score bands (from the atr_pct distribution, 2026-07-18):
#   <2 → 35 · 2–3 → 55 · 3–8 → 85 (sweet spot) · 8–10 → 60 · 10–15 → 45 · >15 → 25
#   missing or NaN → 50 (neutral)
# Maps a company's yfinance sector label (as stored by fundamental_agent.py's
# _raw()) to the matching US SPDR sector ETF tracked in sector_rotation.json.
SECTOR_ETF_MAP = {
    "Technology":             "XLK",
    "Financial Services":     "XLF",
    "Financials":             "XLF",
    "Energy":                 "XLE",
    "Healthcare":             "XLV",
    "Industrials":            "XLI",
    "Consumer Cyclical":      "XLY",
    "Consumer Defensive":     "XLP",
    "Utilities":              "XLU",
    "Real Estate":            "XLRE",
    "Basic Materials":        "XLB",
    "Communication Services": "XLC",
}


# Maps a company's yfinance INDUSTRY label (finer than the sector map above --
# e.g. "Semiconductors" is a slice of "Technology", not all of it) to a
# sub-industry ETF, when sector_rotation.py tracks one for it (US_INDUSTRIES).
# Deliberately partial: only the industries that have actually come up in
# macro-analyst.md's bubble watch have an entry. Anything not listed here just
# falls back to the broad SECTOR_ETF_MAP lookup, same as before this existed --
# no ticker loses sector-level coverage for lacking an industry-level one.
# Keep in sync with sector_rotation.py's US_INDUSTRIES.
INDUSTRY_ETF_MAP = {
    "Semiconductors":                      "SMH",
    "Semiconductor Equipment & Materials":  "SMH",
    "Biotechnology":                       "XBI",
    "Software - Infrastructure":           "IGV",
    "Software - Application":              "IGV",
    "Aerospace & Defense":                 "ITA",
    "Banks - Regional":                    "KRE",
}


def resolve_bubble_etf(sector: str | None, industry: str | None,
                        sector_rotation: dict | None) -> tuple[str | None, str, str | None]:
    """Picks the ETF to join bubble_watch.json / sector_rotation.json against
    for a ticker -- the industry-level ETF when INDUSTRY_ETF_MAP has one
    mapped AND sector_rotation.json actually carries data for it, otherwise
    the broad sector ETF. Returns (etf, granularity, label); etf is None when
    neither resolves. Shared by regime_penalty() and the Rescued_BW rank so
    both resolve a ticker's sector/industry identically -- two independently
    hand-rolled copies of this preference order would drift apart silently."""
    us_industries = (sector_rotation or {}).get("us_industries", {})
    if industry:
        industry_etf = INDUSTRY_ETF_MAP.get(industry)
        if industry_etf and us_industries.get(industry_etf):
            return industry_etf, "industry", industry
    return (SECTOR_ETF_MAP.get(sector) if sector else None), "sector", sector


# REVIEW(scoring): crowded-sector / regime-fragility penalty - hand-picked
# thresholds, not backtested against history yet. Purpose: a clean technical
# breakout inside a sector that is ALSO the single hottest-ranked one and up
# sharply over the last quarter is the signature of a late-cycle/crowded move
# (e.g. buying an oil name right as energy peaks), not an independent
# idiosyncratic signal. This does not replace score_technical()'s per-ticker
# checks - it adds a sector/macro-breadth check nothing here made before.
# Needs the ticker's sector (only known for tickers that reached
# fundamental_agent.py) - returns (0.0, []) when sector/data is unavailable,
# never blocks scoring.
#
# 2026-10-05: the sector-return part (hot_1m/hot_3m) is now necessary but not
# sufficient. The penalty only actually fires when macro-analyst.md's bubble
# watch has flagged that same sector/industry as Kindleberger Stage 4
# CONFIRMED this session, via data/bubble_watch.json (see load_bubble_watch()).
# Missing/stale/no-entry bubble data = the penalty never fires on this basis,
# even if the return thresholds alone would have triggered it before this
# change -- fail-closed, not a silent revert to the old unconditional rule.
# Industry-level data (INDUSTRY_ETF_MAP + sector_rotation.json's
# "us_industries") is preferred over the broad sector ETF when both the
# ticker's industry and sector_rotation.json have an entry for it, since
# macro-analyst.md's bubble themes ("Semis/AI-infra") are usually narrower
# than a full GICS sector -- falls back to the broad sector otherwise.
# The Minsky fragility penalty below is untouched by this -- it was never
# part of what was asked to be gated.
def regime_penalty(sector: str | None, industry: str | None,
                    sector_rotation: dict | None, macro: dict | None,
                    bubble_watch: dict | None = None) -> tuple[float, list]:
    penalty = 0.0
    notes: list = []

    etf, granularity, label = resolve_bubble_etf(sector, industry, sector_rotation)
    us_industries = (sector_rotation or {}).get("us_industries", {})
    row_source = us_industries if granularity == "industry" else (sector_rotation or {}).get("us_sectors", {})
    sector_row = row_source.get(etf) if etf else None

    if sector_row:
        ret_1m = sector_row.get("ret_1m")
        ret_3m = sector_row.get("ret_3m")
        rank   = sector_row.get("rank")
        # Mechanical OR -- either threshold alone is enough to flag crowding.
        # No rank requirement: a sector can be crowded without being today's
        # single hottest-ranked one.
        # A return within SECTOR_THRESHOLD_TOLERANCE points of the threshold
        # still counts as a hit (e.g. 36% against a 40% 3M threshold triggers,
        # since 40 - 5 = 35 < 36) -- a mechanical rule shouldn't miss a signal
        # by one rounding error's worth of return.
        hot_1m = ret_1m is not None and ret_1m > (SECTOR_RET_1M_THRESHOLD - SECTOR_THRESHOLD_TOLERANCE)
        hot_3m = ret_3m is not None and ret_3m > (SECTOR_RET_3M_THRESHOLD - SECTOR_THRESHOLD_TOLERANCE)
        if hot_1m or hot_3m:
            bubble_entry = (bubble_watch or {}).get(etf) if etf else None
            stage4_confirmed = bool(
                bubble_entry
                and bubble_entry.get("stage") == 4
                and bubble_entry.get("confirmed") is True
            )
            parts = []
            if ret_1m is not None: parts.append(f"{ret_1m:+.0f}% 1M")
            if ret_3m is not None: parts.append(f"{ret_3m:+.0f}% 3M")
            rank_note = f", rank #{rank}" if rank is not None else ""
            both_note = " [both thresholds]" if (hot_1m and hot_3m) else ""
            if stage4_confirmed:
                # Either one alone is enough to flag crowding (-15); both
                # firing together is a stronger signal than either alone (-20).
                sector_pen = -20 if (hot_1m and hot_3m) else -15
                penalty += sector_pen
                notes.append(f"crowded {granularity}: {label} ({' / '.join(parts)}{rank_note}){both_note} "
                             f"[bubble Stage 4 confirmed]")
            else:
                # Hot return, but no confirmed Stage 4 bubble signal -- logged
                # for visibility, no penalty applied.
                notes.append(f"{granularity} return hot but no bubble Stage-4 confirmation: "
                             f"{label} ({' / '.join(parts)}{rank_note}){both_note}")

    minsky = (macro or {}).get("minsky_score")
    if minsky is not None and minsky >= 4:
        penalty -= 10
        notes.append(f"high macro fragility (Minsky {minsky}/5)")

    return penalty, notes


def volatility(ticker: str, t: dict) -> float | None:
    score = 50                      # neutral default — covers missing AND NaN
    atr_pct = t.get("atr_pct")
    if atr_pct:
        if   atr_pct < 2:    score = 35   # too calm — barely passed the guard
        elif atr_pct < 3:    score = 55   # tradeable but modest
        elif atr_pct <= 8:   score = 85   # the sweet spot — reward
        elif atr_pct <= 10:  score = 60   # energetic, getting risky
        elif atr_pct <= 15:  score = 45   # risk outweighs opportunity
        elif atr_pct > 15:   score = 25   # chaos / gap-risk territory
    return max(0, min(100, score))
    
# this function calculates the final score for the ticker
def composite(tech: float, fund: float | None, alt: float | None,
              dte: int | None, short_pct: float | None, volatility: float,
              regime_pen: float = 0.0) -> float:
    """Weighted composite score with penalties."""
    weights = {"tech": 0.45, "fund": 0.25, "alt": 0.20, "volatility": 0.10}

    fund_val = fund if fund is not None else 50.0
    alt_val  = alt  if alt  is not None else 50.0
    volatility_val  = volatility if volatility is not None else 50.0  # neutral if no data

    score = (tech     * weights["tech"] +
             fund_val * weights["fund"] +
             alt_val  * weights["alt"]  +
             volatility_val  * weights["volatility"])

    # Penalties
    if dte is not None and dte <= 3:    score -= 20  # earnings in 2-3 days
    elif dte is not None and dte <= 7:  score -= 10
    if short_pct and short_pct > 30:    score -= 10
    if short_pct and short_pct > 50:    score -= 10
    score += regime_pen   # crowded-sector / macro-fragility penalty, see regime_penalty()

    return round(max(0.0, min(100.0, score)), 1)


def build_scored_universe(args) -> tuple[list, dict | None, dict | None] | None:
    """Loads every input file and scores the full universe exactly once --
    shared by watchlist_ranker.py's main() ranking and rescue_bw.py's
    Rescued_BW pass, so both run on identical composite scores and
    sector/industry data by construction, not two hand-written copies that
    could drift apart. Returns (scored, sector_rotation_raw, bubble_watch_raw),
    or None when market_data.json is missing -- the caller decides how to
    report that, this function doesn't print on their behalf.
    `args` only needs `.eu` and `.us` (both argparse flags, default False)."""
    market_raw  = load_json(MARKET_PATH)
    fund_raw    = load_json(FUND_PATH)
    alt_raw     = load_json(ALT_PATH)
    earnings_raw = load_json(EARNINGS_PATH)
    sector_rotation_raw = load_json(SECTOR_PATH)
    macro_raw            = load_json(MACRO_PATH)
    bubble_watch_raw     = load_bubble_watch(BUBBLE_PATH, BUBBLE_WATCH_MAX_AGE_HOURS)

    if market_raw is None:
        return None

    # Normalise market_data structure
    if isinstance(market_raw, dict) and "tickers" in market_raw:
        tickers_data = market_raw["tickers"]
    elif isinstance(market_raw, dict) and "signals" in market_raw:
        tickers_data = {t["ticker"]: t for t in market_raw["signals"] if "ticker" in t}
    elif isinstance(market_raw, list):
        tickers_data = {t["ticker"]: t for t in market_raw if "ticker" in t}
    elif isinstance(market_raw, dict):
        tickers_data = market_raw
    else:
        print("  Unrecognised market_data.json format.\n")
        return

    # Normalise fundamental
    fund_data: dict = {}
    if isinstance(fund_raw, dict):
        fund_data = fund_raw.get("fundamentals") or fund_raw.get("tickers") or fund_raw

    # Normalise alt
    alt_data: dict = {}
    if isinstance(alt_raw, dict):
        alt_data = alt_raw.get("tickers") or alt_raw

    # Normalise earnings
    earnings: list = []
    if isinstance(earnings_raw, list):
        earnings = earnings_raw
    elif isinstance(earnings_raw, dict):
        earnings = earnings_raw.get("tickers") or earnings_raw.get("earnings", [])

    scored = []
    for ticker, t_data in tickers_data.items():
        if not isinstance(t_data, dict):
            continue
        if args.eu and not is_eu(ticker):
            continue
        if args.us and is_eu(ticker):
            continue

        tech_score = score_technical(t_data)
        fund_score = score_fundamental(ticker, fund_data)
        alt_score  = score_alt(ticker, alt_data)
        vol_score  = volatility(ticker, t_data)
        dte        = earnings_days_out(ticker, earnings)

        short_pct: float | None = None
        if alt_raw and isinstance(alt_raw, dict):
            ae = (alt_raw.get("tickers") or alt_raw).get(ticker) or {}
            si = ae.get("short_interest") or {}
            short_pct = si.get("short_pct_float")

        # Sector/industry are only known for tickers that reached
        # fundamental_agent.py - unknown sector just skips the crowded-sector
        # check for this ticker, never a crash. fundamental_agent.py scores
        # the full universe now (not just High/Medium), so this already
        # covers every conviction level, not only High/Medium.
        fund_entry = fund_data.get(ticker) if isinstance(fund_data, dict) else None
        sector     = fund_entry.get("sector")   if fund_entry else None
        industry   = fund_entry.get("industry") if fund_entry else None
        regime_pen, regime_notes = regime_penalty(sector, industry, sector_rotation_raw,
                                                    macro_raw, bubble_watch_raw)

        comp = composite(tech_score, fund_score, alt_score, dte=dte, short_pct=short_pct,
                          volatility=vol_score, regime_pen=regime_pen)

        conv = (t_data.get("conviction") or "").upper()
        scored.append({
            "ticker":         ticker,
            "score":          comp,
            "tech_score":     round(tech_score, 1),
            "fund_score":     round(fund_score, 1) if fund_score else None,
            "alt_score":      round(alt_score, 1)  if alt_score  else None,
            "conviction":     conv or "—",
            "rsi":            t_data.get("rsi"),
            "atr_pct":        t_data.get("atr_pct"),
            "dte":            dte,
            "is_eu":          is_eu(ticker),
            "regime_flags":   regime_notes,
            "sector":         sector,
            "industry":       industry,
        })

    return scored, sector_rotation_raw, bubble_watch_raw


def main():
    parser = argparse.ArgumentParser(prog="watchlist_ranker")
    parser.add_argument("--top",  type=int, default=50)
    parser.add_argument("--eu",   action="store_true", help="EU tickers only")
    parser.add_argument("--us",   action="store_true", help="US tickers only")
    args = parser.parse_args()

    result = build_scored_universe(args)
    if result is None:
        print(f"\n  market_data.json not found — run fetch_data.py first.\n")
        return
    scored, sector_rotation_raw, bubble_watch_raw = result

    ranked = sorted(scored, key=lambda x: -x["score"])[:args.top]

    # ── Print ─────────────────────────────────────────────────────────────
    today = datetime.today().strftime("%Y-%m-%d")
    filter_label = " (EU)" if args.eu else " (US)" if args.us else ""
    print(f"\n  {'='*72}")
    print(f"  WATCHLIST RANKED — Top {args.top}{filter_label} — {today}")
    print(f"  {'='*72}")
    print(f"  {'#':>3}  {'TICKER':<12} {'SCORE':>6}  {'TECH':>5}  {'FUND':>5}  {'ALT':>5}  "
          f"{'CONV':<8} {'RSI':>5}  {'ATR%':>5}  NOTES")
    print(f"  {'─'*72}")

    for rank, s in enumerate(ranked, 1):
        fund_s  = f"{s['fund_score']:.0f}" if s["fund_score"] else "—"
        alt_s   = f"{s['alt_score']:.0f}"  if s["alt_score"]  else "—"
        rsi_s   = f"{s['rsi']:.0f}"        if s["rsi"]        else "—"
        atr_s   = f"{s['atr_pct']:.1f}"    if s["atr_pct"]    else "—"
        notes   = f"⚠ EARN {s['dte']}d" if s["dte"] is not None and s["dte"] <= 7 else ""
        if s.get("regime_flags"):
            notes = (notes + "  " if notes else "") + "⚠ " + "; ".join(s["regime_flags"])
        eu_flag = " [EU]" if s["is_eu"] else ""
        print(f"  {rank:>3}  {s['ticker']:<12} {s['score']:>6.1f}  {s['tech_score']:>5.0f}  "
              f"{fund_s:>5}  {alt_s:>5}  {s['conviction']:<8} {rsi_s:>5}  {atr_s:>5}  {notes}{eu_flag}")

    # ── Save ──────────────────────────────────────────────────────────────
    output = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "top_n":        args.top,
        "ranked":       ranked,
    }
    Path("./data").mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved → {OUTPUT_PATH}\n")


if __name__ == "__main__":
    main()


