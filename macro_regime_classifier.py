#!/usr/bin/env python3
"""
macro_regime_classifier.py — Automated macro regime classification

Classifies the current macro regime using market-based indicators from yfinance.
Outputs: data/macro_regime.json + formatted report.

Regime matrix (Growth × Inflation):
  Goldilocks  — Growth ↑ + Inflation ↓  → long equities, growth/tech favoured
  Reflation   — Growth ↑ + Inflation ↑  → commodities, energy, banks, value
  Stagflation — Growth ↓ + Inflation ↑  → commodities, cash, short equities
  Deflation   — Growth ↓ + Inflation ↓  → long bonds, gold, defensive

Usage: python3 macro_regime_classifier.py
"""

import json, os, sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance pandas numpy --quiet")
    import yfinance as yf
    import pandas as pd
    import numpy as np

OUTPUT_PATH = "./data/macro_regime.json"

INDICATORS = {
    # Yields
    "^TNX":    "US 10Y yield",
    "^FVX":    "US 5Y yield",
    "^IRX":    "US 3M yield",
    # Equities
    "SPY":     "S&P 500",
    "QQQ":     "Nasdaq 100",
    "IWM":     "Russell 2000",
    "XLI":     "Industrials ETF",
    "XLE":     "Energy ETF",
    "XLF":     "Financials ETF",
    "XLU":     "Utilities ETF",
    # Inflation proxies
    "GLD":     "Gold",
    "USO":     "Oil (crude proxy)",
    "PDBC":    "Commodities broad",
    "VTIP":    "TIPS (infl. expectation)",
    # Credit
    "HYG":     "High yield bonds",
    "LQD":     "Investment grade bonds",
    "TLT":     "Long-term treasuries",
    # Risk / volatility
    "^VIX":    "VIX",
    # Dollar
    "DX-Y.NYB": "Dollar Index",
    # EU
    "^V2TX":   "VSTOXX (EU VIX proxy)",
}


def fetch_indicator(ticker: str, days: int = 130) -> dict | None:
    end   = datetime.today()
    start = end - timedelta(days=days)
    try:
        hist = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                           end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.droplevel(1)
        if "Close" not in hist.columns or len(hist) < 5:
            return None
        closes = hist["Close"].dropna()
        n      = len(closes)
        last   = float(closes.iloc[-1])

        def ret(periods):
            return round((last / float(closes.iloc[-1 - periods]) - 1) * 100, 2) if n > periods else None

        def ma(periods):
            return round(float(closes.rolling(periods).mean().iloc[-1]), 4) if n >= periods else None

        return {
            "last":        round(last, 4),
            "ret_1m":      ret(22),
            "ret_3m":      ret(63),
            "ret_6m":      ret(126),
            "above_ma50":  last > (ma(50) or 0) if ma(50) else None,
            "above_ma200": last > (ma(200) or 0) if ma(200) else None,
            "ma50":        ma(50),
            "ma200":       ma(200),
        }
    except Exception:
        return None


def classify_growth(data: dict) -> tuple[str, str]:
    spy    = data.get("SPY")
    iwm    = data.get("IWM")
    xli    = data.get("XLI")
    tlt    = data.get("TLT")

    signals = []
    if spy and spy.get("ret_3m") is not None:
        signals.append(1 if spy["ret_3m"] > 0 else -1)
    if spy and spy.get("above_ma200") is not None:
        signals.append(1 if spy["above_ma200"] else -1)
    if iwm and iwm.get("ret_3m") is not None:
        signals.append(1 if iwm["ret_3m"] > 0 else -1)
    if xli and xli.get("above_ma50") is not None:
        signals.append(1 if xli["above_ma50"] else -1)
    # TLT inverse: rising bonds = falling growth expectations
    if tlt and tlt.get("ret_3m") is not None:
        signals.append(-1 if tlt["ret_3m"] > 5 else 1)

    if not signals:
        return "UNKNOWN", "insufficient data"
    score = sum(signals) / len(signals)
    if score >= 0.4:
        return "EXPANDING", f"score {score:+.2f} (SPY/IWM/XLI positive)"
    elif score <= -0.4:
        return "CONTRACTING", f"score {score:+.2f} (risk-off signals dominant)"
    else:
        return "MIXED", f"score {score:+.2f} (conflicting signals)"


def classify_inflation(data: dict) -> tuple[str, str]:
    gld   = data.get("GLD")
    uso   = data.get("USO")
    pdbc  = data.get("PDBC")
    tnx   = data.get("^TNX")
    vtip  = data.get("VTIP")
    dollar = data.get("DX-Y.NYB")

    signals = []
    if gld and gld.get("ret_3m") is not None:
        signals.append(1 if gld["ret_3m"] > 3 else (-1 if gld["ret_3m"] < -3 else 0))
    if uso and uso.get("ret_3m") is not None:
        signals.append(1 if uso["ret_3m"] > 5 else (-1 if uso["ret_3m"] < -5 else 0))
    if pdbc and pdbc.get("ret_3m") is not None:
        signals.append(1 if pdbc["ret_3m"] > 3 else (-1 if pdbc["ret_3m"] < -3 else 0))
    if tnx and tnx.get("ret_1m") is not None:
        signals.append(1 if tnx["ret_1m"] > 2 else (-1 if tnx["ret_1m"] < -2 else 0))
    if dollar and dollar.get("ret_3m") is not None:
        signals.append(-1 if dollar["ret_3m"] > 3 else (1 if dollar["ret_3m"] < -3 else 0))

    if not signals:
        return "UNKNOWN", "insufficient data"
    score = sum(signals) / len(signals)
    if score >= 0.3:
        return "RISING", f"score {score:+.2f} (commodities/yields elevated)"
    elif score <= -0.3:
        return "FALLING", f"score {score:+.2f} (commodities/yields declining)"
    else:
        return "STABLE", f"score {score:+.2f} (mixed inflation signals)"


def classify_regime(growth: str, inflation: str) -> tuple[str, list]:
    matrix = {
        ("EXPANDING",   "RISING"):  ("REFLATION",   ["Energy", "Financials", "Materials", "Value"]),
        ("EXPANDING",   "FALLING"): ("GOLDILOCKS",  ["Technology", "Growth", "Consumer Discret."]),
        ("EXPANDING",   "STABLE"):  ("GOLDILOCKS",  ["Technology", "Growth", "Broad equities"]),
        ("MIXED",       "RISING"):  ("REFLATION",   ["Energy", "Commodities", "Banks"]),
        ("MIXED",       "FALLING"): ("GOLDILOCKS",  ["Technology", "Healthcare", "Consumer"]),
        ("MIXED",       "STABLE"):  ("MIXED",       ["Broad equities", "Defensive tilt"]),
        ("CONTRACTING", "RISING"):  ("STAGFLATION", ["Cash", "Commodities", "Short equities"]),
        ("CONTRACTING", "FALLING"): ("DEFLATION",   ["Bonds (TLT)", "Gold", "Defensives", "Cash"]),
        ("CONTRACTING", "STABLE"):  ("DEFLATION",   ["Bonds", "Gold", "Defensives"]),
    }
    for (g, i), (regime, favored) in matrix.items():
        if g in growth and i in inflation:
            return regime, favored
    return "UNCLEAR", ["Reduce exposure until clearer signal"]


def minsky_score(data: dict) -> tuple[int, list]:
    score  = 0
    checks = []

    hyg  = data.get("HYG")
    lqd  = data.get("LQD")
    vix  = data.get("^VIX")
    spy  = data.get("SPY")
    tlt  = data.get("TLT")

    if hyg and hyg.get("ret_3m") is not None and hyg["ret_3m"] > 3:
        score += 1; checks.append("Credit spreads tight — HYG strong (complacency signal)")
    if vix and vix.get("last") and vix["last"] < 15:
        score += 1; checks.append(f"VIX {vix['last']:.1f} — low volatility (euphoria zone)")
    if spy and spy.get("ret_6m") and spy["ret_6m"] > 20:
        score += 1; checks.append(f"SPY +{spy['ret_6m']:.0f}% in 6M — extended rally")
    if spy and spy.get("above_ma200") and spy and spy.get("above_ma50"):
        score += 1; checks.append("SPY above MA50 + MA200 — uptrend intact (leverage building)")
    if tlt and tlt.get("ret_3m") and tlt["ret_3m"] < -5:
        score += 1; checks.append("TLT falling — yield curve pressure (debt service stress)")

    return score, checks


def dalio_cycle(data: dict, tnx_level: float | None) -> str:
    vix = (data.get("^VIX") or {}).get("last")
    hyg_ret = (data.get("HYG") or {}).get("ret_3m")
    spy_ret = (data.get("SPY") or {}).get("ret_6m")

    if tnx_level is not None and tnx_level > 5:
        return "Late cycle — high rates constraining credit, watch for credit event"
    elif tnx_level is not None and tnx_level < 3:
        return "Early cycle — loose financial conditions, expansion phase"
    elif vix and vix < 15 and (spy_ret or 0) > 15:
        return "Mid-to-late cycle — low volatility + extended equities, complacency building"
    elif vix and vix > 25:
        return "Potential cycle turn or stress event — monitor credit markets"
    return "Mid cycle — conditions broadly supportive"


def main():
    print(f"\n  Fetching macro indicators...", flush=True)
    data: dict = {}
    for ticker, name in INDICATORS.items():
        result = fetch_indicator(ticker)
        if result:
            data[ticker] = result
            print(f"  ✓ {ticker:<14} {name:<30} {result['last']:.4f}", flush=True)
        else:
            print(f"  ✗ {ticker:<14} {name:<30} (unavailable)", flush=True)

    print()
    growth_state,    growth_detail    = classify_growth(data)
    inflation_state, inflation_detail = classify_inflation(data)
    regime, favored_sectors           = classify_regime(growth_state, inflation_state)
    minsky_pts, minsky_checks         = minsky_score(data)

    tnx_level = (data.get("^TNX") or {}).get("last")
    dalio_pos = dalio_cycle(data, tnx_level)

    confidence = "HIGH" if growth_state not in ("MIXED", "UNKNOWN") and inflation_state not in ("STABLE", "UNKNOWN") else "MEDIUM"

    print(f"  {'='*62}")
    print(f"  MACRO REGIME CLASSIFIER — {datetime.today().strftime('%Y-%m-%d')}")
    print(f"  {'='*62}")
    print(f"\n  Growth:     {growth_state:<14}  {growth_detail}")
    print(f"  Inflation:  {inflation_state:<14}  {inflation_detail}")
    print(f"\n  ──────────────────────────────────────────────────────────")
    print(f"  REGIME:     {regime}  [{confidence} confidence]")
    print(f"  Favoured:   {', '.join(favored_sectors)}")

    # Key yield data
    if tnx_level:
        fvx = (data.get("^FVX") or {}).get("last")
        irx = (data.get("^IRX") or {}).get("last")
        print(f"\n  YIELD CURVE")
        print(f"  10Y: {tnx_level:.3f}%  |  5Y: {fvx:.3f}%  |  3M: {irx:.3f}%" if fvx and irx else
              f"  10Y: {tnx_level:.3f}%")
        if fvx and irx:
            spread_10_3m = tnx_level - irx
            print(f"  10Y-3M spread: {spread_10_3m:+.2f}%  " +
                  ("(INVERTED — recession risk)" if spread_10_3m < 0 else
                   "(FLAT)" if spread_10_3m < 0.5 else "(NORMAL — steepening)"))

    # VIX
    vix = (data.get("^VIX") or {}).get("last")
    if vix:
        vix_regime = "COMPLACENCY" if vix < 15 else "NORMAL" if vix < 25 else "STRESS" if vix < 35 else "CRISIS"
        print(f"\n  VIX: {vix:.1f}  [{vix_regime}]")

    # Minsky
    print(f"\n  MINSKY FRAGILITY SCORE: {minsky_pts}/5")
    for c in minsky_checks:
        print(f"    + {c}")
    if minsky_pts >= 4:
        print(f"  ⛔ HIGH FRAGILITY — reduce position sizes, tighten stops")
    elif minsky_pts >= 3:
        print(f"  ⚠  ELEVATED FRAGILITY — caution, be selective")

    print(f"\n  DALIO CYCLE: {dalio_pos}")

    # Dollar
    dxy = (data.get("DX-Y.NYB") or {})
    if dxy.get("last"):
        dxy_ret = dxy.get("ret_3m")
        print(f"\n  Dollar Index (DXY): {dxy['last']:.2f}  " +
              (f"3M: {dxy_ret:+.1f}%" if dxy_ret else ""))

    # Commodities
    gld = (data.get("GLD") or {}).get("ret_3m")
    uso = (data.get("USO") or {}).get("ret_3m")
    if gld is not None or uso is not None:
        print(f"\n  COMMODITIES")
        if gld is not None: print(f"  Gold (GLD) 3M:  {gld:+.1f}%")
        if uso is not None: print(f"  Oil  (USO) 3M:  {uso:+.1f}%")

    # Save
    output = {
        "generated_at":    datetime.utcnow().isoformat() + "Z",
        "regime":          regime,
        "confidence":      confidence,
        "growth":          growth_state,
        "inflation":       inflation_state,
        "favored_sectors": favored_sectors,
        "minsky_score":    minsky_pts,
        "dalio_cycle":     dalio_pos,
        "indicators":      data,
    }
    Path("./data").mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved → {OUTPUT_PATH}\n")


if __name__ == "__main__":
    main()
