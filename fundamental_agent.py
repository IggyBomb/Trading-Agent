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

# ═════════════════════════════════════════════════════════════════════════════
#  SCORING REVIEW — functions tagged "REVIEW(scoring)" define the fundamental
#  score bands, the 33/34/33 composite weights, and the rating thresholds.
#  All hand-picked and sector-blind — they need a second opinion.
#
#  RAW(yfinance) — every ratio below is now calculated by us from raw .info
#  primitives (price, EPS, book value, EBITDA, debt, cash, shares...) instead
#  of trusting Yahoo's own pre-baked trailingPE/priceToBook/etc. The field
#  names used in _raw() match yfinance's typical schema but have NOT been
#  confirmed against a live call in this environment (network blocked here).
#  If a value comes back None where you'd expect a number, check the exact
#  key with:
#    python3 -c "import yfinance as yf; print(yf.Ticker('AAPL').info.get('KEY'))"
#  Exception: revenue/earnings growth still come straight from Yahoo
#  (revenueGrowth/earningsGrowth) — a true YoY calc needs financial-statement
#  history, a separate heavier call, not a field inside .info. Same for PEG's
#  growth input — see compute_ratios() below.
#
#  Search for: REVIEW(scoring), RAW(yfinance)
# ═════════════════════════════════════════════════════════════════════════════

import json
import os
import sys
import time
from datetime import datetime
from schemas import FundamentalRecord
from pydantic import ValidationError
import logging
log = logging.getLogger("fundamental_agent")


try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf


# RAW(yfinance): Yahoo's unofficial `.info` endpoint is known to occasionally
# return a transiently incomplete payload — confirmed live on a real ticker:
# freeCashflow came back non-positive/None on one call and a stable positive
# value on five back-to-back calls right after, with every other field
# identical. That one flaky field flowed straight into fcf_positive and the
# composite score with no way to tell it apart from a real negative FCF.
# This retries the whole .info call once if freeCashflow looks suspicious
# (missing/non-positive) while operatingCashflow — which should move with it
# — is present and positive. Adds at most one extra call, only when triggered.
def _fetch_info(ticker: str) -> dict | None:
    info = yf.Ticker(ticker).info
    if not info or len(info) < 5:
        return info

    fcf_yahoo = _safe(info, "freeCashflow")
    op_cf     = _safe(info, "operatingCashflow")
    suspicious = (fcf_yahoo is None or fcf_yahoo <= 0) and op_cf is not None and op_cf > 0
    if suspicious:
        log.debug(f"{ticker}: freeCashflow looks suspicious ({fcf_yahoo}) vs "
                  f"positive operatingCashflow ({op_cf}) — retrying .info once")
        time.sleep(1.0)
        retry_info = yf.Ticker(ticker).info
        retry_fcf  = _safe(retry_info, "freeCashflow") if retry_info else None
        if retry_info and retry_fcf is not None and retry_fcf > 0:
            info = retry_info

    return info

# ── Config ───────────────────────────────────────────────────────────────────
from config import CONVICTION_FILTER, MARKET_DATA_PATH, FUNDAMENTAL_PATH

REQUEST_PAUSE = 0.3   # seconds between yfinance .info calls

# ── Scoring weights ───────────────────────────────────────────────────────────
# Each dimension scored 0–10, combined into 0–100 total.
# Value 33% | Quality 34% | Growth 33%


# Helper — dict lookup that also treats NaN as a missing value.
def _safe(d, key, default=None):
    v = d.get(key, default)
    if v is None or (isinstance(v, float) and (v != v)):  # NaN check
        return default
    return v


# RAW(yfinance): primitive fields pulled straight from `.info` — no derived
# ratios here, just the numbers Yahoo reports about the business itself.
# Equity is derived (bookValue × sharesOutstanding) when yfinance doesn't
# expose totalStockholderEquity directly; enterpriseValue is derived the same
# way (marketCap + debt − cash) if missing, so a gap in one field doesn't
# silently drop every ratio built on top of it.
def _raw(info: dict) -> dict:
    price       = _safe(info, "currentPrice") or _safe(info, "regularMarketPrice")
    market_cap  = _safe(info, "marketCap")
    total_debt  = _safe(info, "totalDebt")
    total_cash  = _safe(info, "totalCash")
    book_value  = _safe(info, "bookValue")
    shares      = _safe(info, "sharesOutstanding")

    equity = _safe(info, "totalStockholderEquity")
    if equity is None and book_value is not None and shares is not None:
        equity = book_value * shares

    enterprise_value = _safe(info, "enterpriseValue")
    if enterprise_value is None and market_cap is not None and total_debt is not None and total_cash is not None:
        enterprise_value = market_cap + total_debt - total_cash

    return {
        "price":                price,
        "trailing_eps":         _safe(info, "trailingEps"),
        "forward_eps":          _safe(info, "forwardEps"),
        "book_value":           book_value,
        "shares_outstanding":   shares,
        "market_cap":           market_cap,
        "total_debt":           total_debt,
        "total_cash":           total_cash,
        "ebitda":               _safe(info, "ebitda"),
        "enterprise_value":     enterprise_value,
        "total_revenue":        _safe(info, "totalRevenue"),
        "net_income":           _safe(info, "netIncomeToCommon"),
        "operating_cashflow":   _safe(info, "operatingCashflow"),
        "capital_expenditures": _safe(info, "capitalExpenditures"),
        "equity":               equity,
        # Not rebuildable from a single .info call (see header note) — kept as
        # Yahoo's own pre-computed growth figures for now.
        "revenue_growth_yahoo":  _safe(info, "revenueGrowth"),
        "earnings_growth_yahoo": _safe(info, "earningsGrowth"),
        # FALLBACK — confirmed via live test that yfinance's .info frequently
        # omits capitalExpenditures even when operatingCashflow is present, so
        # operating_cashflow - capex silently goes to None more often than
        # expected. Yahoo's own pre-computed freeCashflow is kept as a backup
        # so the FCF signal isn't lost when capex is missing.
        "free_cashflow_yahoo": _safe(info, "freeCashflow"),
        "sector":   _safe(info, "sector", "Unknown"),
        "industry": _safe(info, "industry", "Unknown"),
    }


# REVIEW(scoring): every ratio here is OUR math on the raw primitives from
# _raw(), not Yahoo's pre-baked number — same formulas as before (PE =
# price/EPS, EV/EBITDA, ROE = net income/equity, etc.), just built ourselves
# so the exact inputs are visible and testable. Missing/zero inputs return
# None rather than guessing. PEG is the one exception that stays partly
# black-box: a "real" PEG needs an analyst growth estimate, not a company
# financial, so it's approximated here from Yahoo's own earnings growth.
def compute_ratios(raw: dict) -> dict:
    price, eps, fwd_eps = raw["price"], raw["trailing_eps"], raw["forward_eps"]

    pe     = round(price / eps, 2)      if price and eps and eps != 0 else None
    fwd_pe = round(price / fwd_eps, 2)  if price and fwd_eps and fwd_eps != 0 else None
    pb     = round(price / raw["book_value"], 2) \
             if price and raw["book_value"] and raw["book_value"] > 0 else None

    ev_ebitda = round(raw["enterprise_value"] / raw["ebitda"], 2) \
                if raw["enterprise_value"] and raw["ebitda"] and raw["ebitda"] > 0 else None

    roe = round(raw["net_income"] / raw["equity"], 4) \
          if raw["net_income"] is not None and raw["equity"] and raw["equity"] > 0 else None

    margin = round(raw["net_income"] / raw["total_revenue"], 4) \
             if raw["net_income"] is not None and raw["total_revenue"] else None

    de = round(raw["total_debt"] / raw["equity"], 4) \
         if raw["total_debt"] is not None and raw["equity"] and raw["equity"] > 0 else None

    # RAW(yfinance): capitalExpenditures is unreliable in .info — confirmed via
    # a live AAPL pull where operating_cashflow was present but capex came back
    # null. Rather than build FCF ourselves and silently lose the signal
    # whenever capex is missing, take Yahoo's own freeCashflow directly.
    # operating_cashflow/capital_expenditures are still kept in _raw()/the
    # output "raw" block for transparency, just not used in this calculation.
    fcf = raw["free_cashflow_yahoo"]

    growth_for_peg = raw["earnings_growth_yahoo"]
    peg = round(pe / (growth_for_peg * 100), 2) \
          if pe and pe > 0 and growth_for_peg and growth_for_peg > 0 else None

    return {
        "pe": pe, "forward_pe": fwd_pe, "pb": pb, "ev_ebitda": ev_ebitda,
        "roe": roe, "profit_margin": margin, "debt_equity": de,
        "fcf": fcf, "peg": peg,
    }


# REVIEW(scoring): value/cheapness 0–10. Points: P/E up to +3 (bands 18/25/34,
# negative P/E −1), P/B up to +3 (bands 0.75/1.5/3.0), EV/EBITDA up to +2
# (bands 8/15), PEG up to +2 (bands 1.0/1.5). Max raw = 10. Bands unchanged
# from before — still hand-picked and sector-blind, applied to every sector
# alike (a bank and a SaaS company get the same bands). Only the SOURCE of
# pe/pb/ev_ebitda/peg changed (see compute_ratios), not the thresholds.
def score_value(ratios: dict) -> float:
    """Score cheapness: P/E, P/B, EV/EBITDA, PEG. Returns 0-10."""
    score = 0.0

    pe = ratios["pe"]
    if pe is not None:
        if pe < 0:
            score -= 1
        elif pe < 18:
            score += 3
        elif pe < 25:
            score += 2
        elif pe < 34:
            score += 1

    pb = ratios["pb"]
    if pb is not None and pb > 0:
        if pb < 0.75:
            score += 2.5
        elif pb < 1.5:
            score += 1.5
        elif pb < 3.0:
            score += 0.5

    ev_ebitda = ratios["ev_ebitda"]
    if ev_ebitda is not None and ev_ebitda > 0:
        if ev_ebitda < 8:
            score += 2
        elif ev_ebitda < 15:
            score += 1

    peg = ratios["peg"]
    if peg is not None and peg > 0:
        if peg < 1.0:
            score += 2
        elif peg < 1.5:
            score += 1

    return round(min(max(score, 0), 10), 2)


# NOTE: debt/equity here is a plain ratio (total debt / equity), not a
# percentage — no /100 conversion needed since we compute it ourselves now
# instead of reading yfinance's debtToEquity (which comes back as a percent).
def score_quality(ratios: dict) -> float:
    """Score business quality: ROE, margins, debt, FCF. Returns 0-10."""
    score = 0.0

    roe = ratios["roe"]
    if roe is not None:
        if roe > 0.3:
            score += 3
        elif roe > 0.15:
            score += 2
        elif roe > 0.075:
            score += 1

    margin = ratios["profit_margin"]
    if margin is not None:
        if margin > 0.25:
            score += 3
        elif margin > 0.125:
            score += 2
        elif margin > 0.075:
            score += 1

    de_ratio = ratios["debt_equity"]
    if de_ratio is not None:
        if de_ratio < 0.7:
            score += 2.5
        elif de_ratio < 1:
            score += 1.5
        elif de_ratio < 2:
            score += 0.5
        else:
            score -= 1

    fcf = ratios["fcf"]
    if fcf is not None:
        if fcf > 0:
            score += 2
        else:
            score -= 0.5

    return round(min(max(score, 0), 10), 2)


# REVIEW(scoring): growth 0–10. Points: revenue growth up to +3 (bands
# 40%/20%/15%/5%), earnings growth up to +3 (bands 15%/10%/5%), forward P/E
# below trailing +2 (if >10% lower) or +1 (any lower) — a proxy for "earnings
# expected to improve". revenue_growth/earnings_growth still come straight
# from Yahoo (raw["..._yahoo"]) — see header note on why these two can't be
# rebuilt from a single .info call. forward_pe/pe now use OUR computed values.
def score_growth(raw: dict, ratios: dict) -> float:
    """Score momentum: revenue growth, earnings growth, forward vs trailing PE. Returns 0-10."""
    score = 0.0

    rev_growth = raw["revenue_growth_yahoo"]
    if rev_growth is not None:
        if rev_growth > 0.40:
            score += 3
        elif rev_growth > 0.20:
            score += 2
        elif rev_growth > 0.15:
            score += 1
        elif rev_growth > 0.05:
            score += 0.2

    earn_growth = raw["earnings_growth_yahoo"]
    if earn_growth is not None:
        if earn_growth > 0.15:
            score += 3
        elif earn_growth > 0.1:
            score += 2
        elif earn_growth > 0.05:
            score += 1

    # Improving earnings: forward P/E lower than trailing P/E
    fwd_pe, tr_pe = ratios["forward_pe"], ratios["pe"]
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


# REVIEW(scoring): pulls yfinance .info for one ticker, extracts raw
# primitives (_raw), calculates every ratio ourselves (compute_ratios), then
# combines the three sub-scores into the 0–100 composite: value×3.3 +
# quality×3.4 + growth×3.3 (33/34/33 weighting). Also note the blanket
# `except: return None` — it hides whether a failure was a fetch error or a
# scoring bug (known issue, unchanged).
def fetch_fundamentals(ticker):
    """Returns a dict of scored fundamental data for one ticker."""
    try:
        info = _fetch_info(ticker)
        if not info or len(info) < 5:
            return None

        raw    = _raw(info)
        ratios = compute_ratios(raw)

        value   = score_value(ratios)
        quality = score_quality(ratios)
        growth  = score_growth(raw, ratios)
        log.debug(f"{ticker}: value={value} quality={quality} growth={growth}")

        # Weighted composite: value 33%, quality 34%, growth 33%
        total = round((value * 3.3) + (quality * 3.4) + (growth * 3.3), 1)  # max = 100

        return {
            "ticker":          ticker,
            "f_score":         total,
            "value_score":     value,
            "quality_score":   quality,
            "growth_score":    growth,
            "rating":          fundamental_rating(total),
            # Ratios — now calculated by us from raw primitives, not read pre-made
            "pe":              ratios["pe"],
            "fwd_pe":          ratios["forward_pe"],
            "pb":              ratios["pb"],
            "ev_ebitda":       ratios["ev_ebitda"],
            "peg":             ratios["peg"],
            "roe":             round(ratios["roe"] * 100, 1) if ratios["roe"] is not None else None,
            "profit_margin":   round(ratios["profit_margin"] * 100, 1) if ratios["profit_margin"] is not None else None,
            "debt_equity":     ratios["debt_equity"],
            # Still Yahoo's own pre-computed growth figures — see header note
            "revenue_growth":  round((raw["revenue_growth_yahoo"] or 0) * 100, 1),
            "earnings_growth": round((raw["earnings_growth_yahoo"] or 0) * 100, 1),
            # None means "unknown", not "negative" — don't collapse a missing
            # FCF into a misleading False (this is what caused fcf_positive to
            # read false on a live AAPL pull where the underlying fcf was None).
            "fcf_positive":    (ratios["fcf"] > 0) if ratios["fcf"] is not None else None,
            "market_cap":      raw["market_cap"],
            "sector":          raw["sector"],
            "industry":        raw["industry"],
            # Raw primitives kept for transparency/debugging — lets you check
            # exactly which input produced a given ratio without re-fetching.
            "raw": {
                "price": raw["price"], "trailing_eps": raw["trailing_eps"],
                "forward_eps": raw["forward_eps"], "book_value": raw["book_value"],
                "shares_outstanding": raw["shares_outstanding"],
                "total_debt": raw["total_debt"], "total_cash": raw["total_cash"],
                "ebitda": raw["ebitda"], "enterprise_value": raw["enterprise_value"],
                "total_revenue": raw["total_revenue"], "net_income": raw["net_income"],
                "operating_cashflow": raw["operating_cashflow"],
                "capital_expenditures": raw["capital_expenditures"],
                "equity": raw["equity"],
                # Was missing before — this is the field that actually drives
                # fcf/fcf_positive. Kept here so a run-to-run score jump is
                # visible without patching in debug code.
                "free_cashflow_yahoo": raw["free_cashflow_yahoo"],
            },
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
    
    # validation of the schema of the fundamental ticker data
    validated_tickers = dict()
    erroneous_tickers = dict()
    for ticker, data in sorted_results.items():
        try:
            FundamentalRecord.model_validate(data)   # checkpoint: raises if data is bad
            validated_tickers[ticker] = data          # passed → keep the JSON-ready dict
        except ValidationError as e:
            erroneous_tickers[ticker] = str(e)
            log.error(f"Validation error for {ticker}: {e}")

    undervalued = [t for t, d in validated_tickers.items() if d["rating"] == "Undervalued"]
    fair        = [t for t, d in validated_tickers.items() if d["rating"] == "Fair"]
    overvalued  = [t for t, d in validated_tickers.items() if d["rating"] == "Overvalued"]
    
 


    
    

    output = {
        "summary": {
            "generated_at":  datetime.now().isoformat(),
            "total_scored":  len(results),
            "total_errors":  len(errors),
            "schema_rejected": len(erroneous_tickers),
            "undervalued":   len(undervalued),
            "fair":          len(fair),
            "overvalued":    len(overvalued),
            "scoring": {
                "value_weight":   "33%",
                "quality_weight": "34%",
                "growth_weight":  "33%",
                "undervalued_threshold": "≥ 62",
                "fair_threshold":        "40–61",
                "overvalued_threshold":  "< 40",
            },
        },
        "fundamentals": validated_tickers,
        "validation_errors": erroneous_tickers,
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
        d = validated_tickers[ticker]
        print(f"  {ticker:<10} f={d['f_score']:>5.1f}  "
              f"V={d['value_score']} Q={d['quality_score']} G={d['growth_score']}  "
              f"{d['sector']}")
    print(f"\nNow run /scan in Claude Code to see fundamentals alongside technicals.\n")


if __name__ == "__main__":
    main()
