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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import MINSKY_HY_OAS_TIGHT, MINSKY_REAL_YIELD_JUMP, MINSKY_DEBT_GDP_PCTILE  # noqa: E402
from config import INFLATION_HIGH_CPI_YOY  # noqa: E402
from gold_regime import fetch_fred  # noqa: E402  (public FRED CSV, no key)

# FRED series for minsky_score(): series id -> start date. Debt/GDP needs the
# long history for its percentile; the daily ones only need ~3 months.
MINSKY_FRED_SERIES = {
    "BAMLH0A0HYM2": None,          # ICE BofA US High Yield OAS, %, daily
    "DFII10":       None,          # 10Y TIPS real yield, %, daily
    "BCNSDODNS":    "1980-01-01",  # nonfinancial corporate debt, MILLIONS $, quarterly
    "GDP":          "1980-01-01",  # nominal GDP, BILLIONS $ SAAR, quarterly
}

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


# Longest lookback any metric below needs is ma(200) — 200 TRADING rows, not
# calendar days. Markets trade ~252 days/year, so 200 rows ≈ 290 calendar days;
# 400 yields ~276 rows, a comfortable margin for holidays and thin history.
# Do NOT lower this below ~300: ma200 and ret_6m go silently null (no error, no
# log), which strips the above_ma200 signal out of classify_growth() and the
# ret_6m checks out of minsky_score() — the regime is then called on short
# windows only, and minsky_score floors at 0.
FETCH_DAYS = 400


def fetch_indicator(ticker: str, days: int = FETCH_DAYS) -> dict | None:
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
    # TLT inverse: rising bonds = falling growth expectations. Symmetric since
    # 2026-11-01 -- it used to score +1 for anything <= +5%, i.e. on 78% of
    # days since 2019, a near-constant pro-growth vote. Flat bonds = 0 now.
    if tlt and tlt.get("ret_3m") is not None:
        signals.append(-1 if tlt["ret_3m"] > 5 else (1 if tlt["ret_3m"] < -5 else 0))

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


def fetch_cpi_yoy() -> tuple[float | None, str | None]:
    """Latest published CPI YoY (FRED public CSV, no key) and its month.
    Matched BY DATE, not row position: Oct 2025 was never published (US
    shutdown), so shift(12) would compare against the wrong month.
    (None, None) when unavailable -- the level guard then stays off."""
    start = (datetime.today() - timedelta(days=800)).strftime("%Y-%m-%d")
    cpi = fetch_fred("CPIAUCSL", start)
    if cpi is None or not len(cpi):
        return None, None
    last = cpi.index[-1]
    prev = last - pd.DateOffset(years=1)
    if prev not in cpi.index:
        return None, None
    return round((float(cpi.iloc[-1]) / float(cpi[prev]) - 1) * 100, 1), str(last.date())


# Added 2026-11-01. classify_inflation() reads direction only, so with CPI at
# 8% and easing (Jun/Sep 2022) the matrix said DEFLATION and favoured long
# bonds. Replayed 2020-2026 quarterly: this changes exactly those two quarters.
def apply_inflation_level_guard(regime: str, favored: list, growth: str, inflation: str,
                                cpi_yoy: float | None) -> tuple[str, list, str | None]:
    """Weak growth + easing inflation is not deflation while CPI is high.
    Returns (regime, favored, override_reason or None)."""
    if (cpi_yoy is not None and cpi_yoy >= INFLATION_HIGH_CPI_YOY
            and growth == "CONTRACTING" and inflation in ("FALLING", "STABLE")):
        return ("STAGFLATION", ["Cash", "Short duration", "Defensives"],
                f"CPI {cpi_yoy}% >= {INFLATION_HIGH_CPI_YOY}%: {regime} overridden")
    return regime, favored, None


# REVIEW(scoring): classify_regime() above picks favored_sectors purely from a
# static growth/inflation textbook matrix — it never looks at how those sectors
# are actually trading. That let it flag "Technology" as favored during the
# Aug-2026 AI/chip selloff while XLK sat -4% for the month, below its own 50MA.
# This maps the matrix's loose labels to the real sector_rotation.json ETF
# tickers and flags any favored sector whose live 1M return + 50MA position
# contradicts the theoretical call, so the mismatch is visible instead of
# silently passed through.
SECTOR_ETF_MAP = {
    "Technology":             "XLK",
    "Growth":                 "XLK",
    "Consumer Discret.":      "XLY",
    "Consumer":               "XLY",
    "Financials":             "XLF",
    "Banks":                  "XLF",
    "Energy":                 "XLE",
    "Materials":              "XLB",
    "Healthcare":              "XLV",
    "Industrials":            "XLI",
    "Utilities":              "XLU",
    "Real Estate":            "XLRE",
    "Communication Services": "XLC",
    # Added 2026-11-01: non-SPDR labels, so the check also works outside
    # Goldilocks/Reflation. Lists = basket, decided by majority. SPY/TLT/GLD/
    # PDBC come from this script's own INDICATORS (same ret_1m/above_ma50 fields).
    "Defensives":             ["XLP", "XLU", "XLV"],
    "Defensive tilt":         ["XLP", "XLU", "XLV"],
    "Broad equities":         "SPY",
    "Bonds":                  "TLT",
    "Bonds (TLT)":            "TLT",
    "Gold":                   "GLD",
    "Commodities":            "PDBC",
}

# Labels a "is it trading up?" check can't judge (Cash, shorts, duration), or
# with no ETF in the data (Value) -- reported as NOT_CHECKABLE, so NO_DATA only
# ever means "should exist but is missing".
NOT_CHECKABLE = {"Cash", "Short duration", "Short equities", "Value"}


def load_sector_rotation(path: str = "./data/sector_rotation.json") -> dict:
    try:
        with open(path) as f:
            return json.load(f).get("us_sectors", {})
    except Exception:
        return {}


def _etf_status(row: dict) -> str:
    ret_1m, above_ma50 = row.get("ret_1m"), row.get("above_ma50")
    if ret_1m is not None and above_ma50 is not None and ret_1m < 0 and not above_ma50:
        return "CONTRADICTED"
    elif ret_1m is not None and above_ma50 is not None and ret_1m > 0 and above_ma50:
        return "CONFIRMED"
    return "MIXED"


def cross_check_favored_sectors(favored_sectors: list, us_sectors: dict,
                                indicators: dict | None = None) -> list:
    """Cross-check theoretical favored_sectors against actual performance:
    sector_rotation.json first, then this script's own indicators (SPY, TLT...).
    CONTRADICTED = the matrix calls it favored but the sector is both down over
    1M and below its own 50-day average right now. Baskets (Defensives =
    XLP/XLU/XLV) take the majority status of the members that have data."""
    indicators = indicators or {}
    results = []
    for label in favored_sectors:
        if label in NOT_CHECKABLE:
            results.append({"sector": label, "ticker": None, "status": "NOT_CHECKABLE"})
            continue
        mapped  = SECTOR_ETF_MAP.get(label)
        tickers = mapped if isinstance(mapped, list) else ([mapped] if mapped else [])
        ticker  = "/".join(tickers) or None
        rows = {t: us_sectors.get(t) or indicators.get(t) for t in tickers}
        rows = {t: r for t, r in rows.items() if r}
        if not rows:
            results.append({"sector": label, "ticker": ticker, "status": "NO_DATA"})
            continue

        statuses = [_etf_status(r) for r in rows.values()]
        half = len(statuses) / 2
        if statuses.count("CONFIRMED") > half:
            status = "CONFIRMED"
        elif statuses.count("CONTRADICTED") > half:
            status = "CONTRADICTED"
        else:
            status = "MIXED"

        rets = [r["ret_1m"] for r in rows.values() if r.get("ret_1m") is not None]
        mas  = [r["above_ma50"] for r in rows.values() if r.get("above_ma50") is not None]
        results.append({
            "sector":     label,
            "ticker":     ticker,
            "status":     status,
            # basket: average 1M return, majority above-MA50
            "ret_1m":     round(sum(rets) / len(rets), 2) if rets else None,
            "above_ma50": (sum(mas) > len(mas) / 2) if mas else None,
            "rank":       next(iter(rows.values())).get("rank") if len(rows) == 1 else None,
        })
    return results


def fetch_minsky_fred() -> dict:
    """Fetch the FRED inputs for minsky_score(). Missing series are omitted --
    each check then falls back to its old yfinance proxy."""
    default_start = (datetime.today() - timedelta(days=FETCH_DAYS)).strftime("%Y-%m-%d")
    out = {}
    for sid, start in MINSKY_FRED_SERIES.items():
        ser = fetch_fred(sid, start or default_start)
        if ser is not None:
            out[sid] = ser
    return out


def _debt_gdp(debt, gdp):
    """Corporate debt/GDP aligned on quarter dates (debt in millions, GDP in
    billions). Returns (latest ratio, percentile of latest in its history)."""
    if debt is None or gdp is None:
        return None, None
    df = pd.concat({"debt": debt / 1000.0, "gdp": gdp}, axis=1, join="inner").dropna()
    if len(df) < 20:
        return None, None
    r = df["debt"] / df["gdp"]
    return float(r.iloc[-1]), float((r <= r.iloc[-1]).mean())


# Five checks, one point each, /5 -- the ranker's >= 4 threshold is unchanged.
# Changed 2026-10-31: the score measured market euphoria only (HYG, VIX, SPY
# twice, TLT) and nothing about debt. Now: credit spread (1), volatility (2),
# rally (3), cost of debt service (4), stock of corporate leverage (5).
# "SPY above MA50+MA200" was dropped -- it duplicated check 3, so any bull
# market scored 2/5 for free. Checks 1 and 4 fall back to the old HYG / TLT
# proxies when FRED is unavailable; check 5 has no market proxy and scores 0.
def minsky_score(data: dict, fred: dict | None = None) -> tuple[int, list]:
    fred = fred or {}
    score, checks = 0, []
    hyg, vix, spy, tlt = (data.get(k) for k in ("HYG", "^VIX", "SPY", "TLT"))

    # 1. Credit complacency -- HY spread, fallback HYG 3M return
    oas = fred.get("BAMLH0A0HYM2")
    if oas is not None and len(oas):
        if oas.iloc[-1] < MINSKY_HY_OAS_TIGHT:
            score += 1; checks.append(f"HY spread {oas.iloc[-1]:.2f}% — credit priced for perfection")
    elif hyg and hyg.get("ret_3m") is not None and hyg["ret_3m"] > 3:
        score += 1; checks.append("Credit spreads tight — HYG strong (fallback: FRED spread unavailable)")

    # 2. Euphoria -- VIX
    if vix and vix.get("last") and vix["last"] < 15:
        score += 1; checks.append(f"VIX {vix['last']:.1f} — low volatility (euphoria zone)")

    # 3. Extended rally -- SPY 6M
    if spy and spy.get("ret_6m") and spy["ret_6m"] > 20:
        score += 1; checks.append(f"SPY +{spy['ret_6m']:.0f}% in 6M — extended rally")

    # 4. Debt service cost rising -- 10Y real yield over ~3M, fallback TLT
    ry = fred.get("DFII10")
    if ry is not None and len(ry) > 63:
        d = float(ry.iloc[-1] - ry.iloc[-64])
        if d >= MINSKY_REAL_YIELD_JUMP:
            score += 1; checks.append(f"10Y real yield +{d*100:.0f}bp in 3M — debt service stress")
    elif tlt and tlt.get("ret_3m") and tlt["ret_3m"] < -5:
        score += 1; checks.append("TLT falling — yield pressure (fallback: FRED real yield unavailable)")

    # 5. Stock of leverage -- nonfinancial corporate debt / GDP vs its history
    ratio, pct = _debt_gdp(fred.get("BCNSDODNS"), fred.get("GDP"))
    if pct is not None and pct >= MINSKY_DEBT_GDP_PCTILE:
        score += 1; checks.append(f"Corp debt/GDP {ratio:.0%} — top {1 - pct:.0%} of history since 1980")

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
    # run_pipeline.sh exports PYTHONUTF8=1, but the documented standalone usage
    # (`python macro_regime_classifier.py`) inherits a cp1252 console on Windows
    # and dies on the ✓/✗ glyphs below. Same guard as sentiment_agent.py.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
    cpi_yoy, cpi_month                = fetch_cpi_yoy()
    regime, favored_sectors, regime_override = apply_inflation_level_guard(
        regime, favored_sectors, growth_state, inflation_state, cpi_yoy)
    inflation_level = ("UNKNOWN" if cpi_yoy is None
                       else "HIGH" if cpi_yoy >= INFLATION_HIGH_CPI_YOY else "NORMAL")
    minsky_pts, minsky_checks         = minsky_score(data, fetch_minsky_fred())

    us_sectors   = load_sector_rotation()
    sector_check = cross_check_favored_sectors(favored_sectors, us_sectors, data)
    contradicted = [c for c in sector_check if c["status"] == "CONTRADICTED"]

    tnx_level = (data.get("^TNX") or {}).get("last")
    dalio_pos = dalio_cycle(data, tnx_level)

    confidence = "HIGH" if growth_state not in ("MIXED", "UNKNOWN") and inflation_state not in ("STABLE", "UNKNOWN") else "MEDIUM"

    print(f"  {'='*62}")
    print(f"  MACRO REGIME CLASSIFIER — {datetime.today().strftime('%Y-%m-%d')}")
    print(f"  {'='*62}")
    print(f"\n  Growth:     {growth_state:<14}  {growth_detail}")
    print(f"  Inflation:  {inflation_state:<14}  {inflation_detail}")
    print(f"  Infl. level:{inflation_level:<14}  " +
          (f"CPI {cpi_yoy}% YoY ({cpi_month[:7]})" if cpi_yoy is not None else "CPI unavailable — level guard off"))
    print(f"\n  ──────────────────────────────────────────────────────────")
    print(f"  REGIME:     {regime}  [{confidence} confidence]")
    if regime_override:
        print(f"  ⚠ LEVEL GUARD: {regime_override}")
    print(f"  Favoured:   {', '.join(favored_sectors)}")
    if contradicted:
        print(f"  ⚠ SECTOR CROSS-CHECK: {len(contradicted)} favoured sector(s) contradicted by actual price action")
        for c in contradicted:
            print(f"    └─ {c['sector']} ({c['ticker']}): {c['ret_1m']:+.2f}% 1M, below 50MA — "
                  f"regime theory says favoured, live sector data disagrees")
    for c in sector_check:
        if c["status"] == "CONFIRMED":
            print(f"  ✓ Confirmed: {c['sector']} ({c['ticker']}): {c['ret_1m']:+.2f}% 1M, above 50MA")

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
        "inflation_level": inflation_level,
        "cpi_yoy":         cpi_yoy,
        "cpi_month":       cpi_month,
        "regime_override": regime_override,
        "favored_sectors": favored_sectors,
        "sector_cross_check": sector_check,
        "minsky_score":    minsky_pts,
        "minsky_checks":   minsky_checks,
        "dalio_cycle":     dalio_pos,
        "indicators":      data,
    }
    Path("./data").mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved → {OUTPUT_PATH}\n")


if __name__ == "__main__":
    main()
