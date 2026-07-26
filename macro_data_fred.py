#!/usr/bin/env python3
"""
macro_data_fred.py — Official macro data (FRED) cross-check

Runs alongside macro_regime_classifier.py, same pipeline stage: standalone
context agent, not read by watchlist_ranker.py. Where macro_regime_classifier.py
infers Growth/Inflation from daily market price proxies (SPY, GLD, yields...),
this script pulls the raw official series from FRED (Federal Reserve Economic
Data) and computes the same Growth/Inflation states mechanically from them —
then flags whether the market-implied regime and the official-data regime
agree or diverge.

Frequency note: most FRED series are monthly/quarterly (CPI, PIL, payrolls),
so this will change far less often day to day than the market-based
classifier. That's expected — it's the slow, "ground truth" confirmation
layer, not a replacement for the daily tactical signal.

Reads:  ./data/macro_regime.json  (market-based regime, if already generated)
Writes: ./data/macro_fred.json

Run alongside macro_regime_classifier.py:
  python3 macro_regime_classifier.py
  python3 macro_data_fred.py

API key (required, free), set in .env or env var:
  FRED_API_KEY=...   # free signup at https://fred.stlouisfed.org/docs/api/api_key.html
"""

import json, os, sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests --quiet")
    import requests

# ── Config ────────────────────────────────────────────────────────────────────

from config import MACRO_REGIME_PATH, MACRO_FRED_PATH

OUTPUT_PATH  = MACRO_FRED_PATH
MARKET_PATH  = MACRO_REGIME_PATH

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_BASE    = "https://api.stlouisfed.org/fred/series/observations"

HISTORY_DAYS = 500   # enough history for a 12-month YoY calc plus some margin

# Daily series — same cadence as the market-based classifier, can be compared 1:1
DAILY_SERIES = {
    "DGS10":  "US 10Y Treasury yield",
    "DGS2":   "US 2Y Treasury yield",
    "DGS3MO": "US 3M Treasury yield",
    "T10Y2Y": "10Y-2Y Treasury spread",
    "T5YIE":  "5Y breakeven inflation",
    "T10YIE": "10Y breakeven inflation",
}

# Monthly / quarterly official series — slow confirmation layer
SLOW_SERIES = {
    "CPIAUCSL": "CPI, headline (all items)",
    "CPILFESL": "CPI, core (ex food & energy)",
    "PCEPI":    "PCE price index (Fed's preferred gauge)",
    "PAYEMS":   "Nonfarm payrolls",
    "UNRATE":   "Unemployment rate",
    "INDPRO":   "Industrial production index",
    "CFNAI":    "Chicago Fed National Activity Index",
}

# Weekly series — the only genuinely high-frequency real-activity data on FRED
WEEKLY_SERIES = {
    "ICSA": "Initial jobless claims",
}

ALL_SERIES = {**DAILY_SERIES, **SLOW_SERIES, **WEEKLY_SERIES}


# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_fred_series(series_id: str, start_date: str) -> list[tuple[str, float]] | None:
    """Raw observations for one FRED series, oldest→newest. None if unavailable."""
    if not FRED_API_KEY:
        return None
    params = {
        "series_id":          series_id,
        "api_key":            FRED_API_KEY,
        "file_type":          "json",
        "observation_start":  start_date,
        "sort_order":         "asc",
    }
    try:
        r = requests.get(FRED_BASE, params=params, timeout=15)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        out = [(o["date"], float(o["value"])) for o in obs
               if o.get("value") not in (".", None, "")]
        return out or None
    except Exception:
        return None


# ── Mechanical calculations (raw series in, ratio/trend out) ─────────────────

def level_diff(series, back):
    """Absolute change vs `back` observations ago (percentage points for rates,
    raw units for indexes/levels). Not a % return — these are rates, not prices."""
    if not series or len(series) <= back:
        return None
    return round(series[-1][1] - series[-1 - back][1], 3)


def yoy_change(series, tolerance_days=45):
    """% change vs the observation closest to 12 months before the latest one."""
    if not series or len(series) < 2:
        return None
    latest_date_str, latest_val = series[-1]
    latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
    target = latest_date - timedelta(days=365)
    best_date, best_val = min(
        series, key=lambda p: abs((datetime.strptime(p[0], "%Y-%m-%d") - target).days)
    )
    if abs((datetime.strptime(best_date, "%Y-%m-%d") - target).days) > tolerance_days:
        return None
    if best_val == 0:
        return None
    return round((latest_val / best_val - 1) * 100, 2)


def moving_avg(series, n):
    if not series or len(series) < n:
        return None
    vals = [v for _, v in series[-n:]]
    return round(sum(vals) / n, 3)


def claims_trend(series):
    """4-week average of jobless claims + % change vs the prior 4-week average."""
    if not series or len(series) < 8:
        return None, None
    recent4 = moving_avg(series, 4)
    prior_vals = [v for _, v in series[-8:-4]]
    prior4 = sum(prior_vals) / 4 if prior_vals else None
    pct = round((recent4 / prior4 - 1) * 100, 2) if prior4 else None
    return recent4, pct


# ── Classification (same vocabulary as macro_regime_classifier.py, for 1:1 comparison) ──

def classify_growth_fred(data: dict) -> tuple[str, str]:
    signals, notes = [], []

    payems = data.get("PAYEMS")
    if payems:
        chg = level_diff(payems, 3)  # net jobs added/lost, last 3 months, thousands
        if chg is not None:
            signals.append(1 if chg > 300 else (-1 if chg < 0 else 0))
            notes.append(f"payrolls 3m: {chg:+.0f}k")

    indpro = data.get("INDPRO")
    if indpro:
        yoy = yoy_change(indpro)
        if yoy is not None:
            signals.append(1 if yoy > 1 else (-1 if yoy < -1 else 0))
            notes.append(f"indprod YoY: {yoy:+.1f}%")

    unrate = data.get("UNRATE")
    if unrate:
        chg = level_diff(unrate, 3)  # percentage points, last 3 months
        if chg is not None:
            signals.append(-1 if chg > 0.3 else (1 if chg < -0.1 else 0))
            notes.append(f"unrate 3m: {chg:+.1f}pp")

    cfnai = data.get("CFNAI")
    if cfnai:
        ma3 = moving_avg(cfnai, 3)
        if ma3 is not None:
            # -0.7 on the 3-month average is the Fed's own published recession-risk threshold
            signals.append(1 if ma3 > 0.2 else (-1 if ma3 < -0.7 else 0))
            notes.append(f"CFNAI-MA3: {ma3:+.2f}")

    icsa = data.get("ICSA")
    if icsa:
        _, trend_pct = claims_trend(icsa)
        if trend_pct is not None:
            signals.append(-1 if trend_pct > 10 else (1 if trend_pct < -10 else 0))
            notes.append(f"claims 4w trend: {trend_pct:+.1f}%")

    if not signals:
        return "UNKNOWN", "dati FRED insufficienti (controlla FRED_API_KEY)"

    score = sum(signals) / len(signals)
    detail = f"score {score:+.2f} (" + ", ".join(notes) + ")"
    if score >= 0.4:
        return "EXPANDING", detail
    elif score <= -0.4:
        return "CONTRACTING", detail
    else:
        return "MIXED", detail


def classify_inflation_fred(data: dict) -> tuple[str, str]:
    signals, notes = [], []

    cpi = data.get("CPIAUCSL")
    if cpi:
        yoy = yoy_change(cpi)
        if yoy is not None:
            signals.append(1 if yoy > 3.0 else (-1 if yoy < 2.0 else 0))
            notes.append(f"CPI YoY: {yoy:+.1f}%")

    core = data.get("CPILFESL")
    if core:
        yoy = yoy_change(core)
        if yoy is not None:
            signals.append(1 if yoy > 3.0 else (-1 if yoy < 2.0 else 0))
            notes.append(f"core CPI YoY: {yoy:+.1f}%")

    pce = data.get("PCEPI")
    if pce:
        yoy = yoy_change(pce)
        if yoy is not None:
            # Fed's own 2% target on PCE — tighter band than headline/core CPI above
            signals.append(1 if yoy > 2.5 else (-1 if yoy < 1.5 else 0))
            notes.append(f"PCE YoY: {yoy:+.1f}%")

    t5yie = data.get("T5YIE")
    if t5yie:
        chg = level_diff(t5yie, 21)  # ~1 trading month, percentage points
        if chg is not None:
            signals.append(1 if chg > 0.10 else (-1 if chg < -0.10 else 0))
            notes.append(f"5Y breakeven 1m: {chg:+.2f}pp")

    if not signals:
        return "UNKNOWN", "dati FRED insufficienti (controlla FRED_API_KEY)"

    score = sum(signals) / len(signals)
    detail = f"score {score:+.2f} (" + ", ".join(notes) + ")"
    if score >= 0.3:
        return "RISING", detail
    elif score <= -0.3:
        return "FALLING", detail
    else:
        return "STABLE", detail


# ── Cross-check vs the market-implied regime ─────────────────────────────────

def compare_with_market_regime(fred_growth: str, fred_inflation: str) -> dict:
    if not Path(MARKET_PATH).exists():
        return {
            "status": "NO_MARKET_REGIME_FILE",
            "note": "esegui prima macro_regime_classifier.py per poter confrontare",
        }
    try:
        with open(MARKET_PATH) as f:
            market = json.load(f)
    except Exception:
        return {"status": "ERROR_READING_MARKET_REGIME", "note": "macro_regime.json illeggibile"}

    m_growth    = market.get("growth", "UNKNOWN")
    m_inflation = market.get("inflation", "UNKNOWN")
    growth_match    = (fred_growth == m_growth)
    inflation_match = (fred_inflation == m_inflation)

    if growth_match and inflation_match:
        status, note = "CONFIRMED", "I dati ufficiali FRED confermano il regime implicito dal mercato."
    elif not growth_match and not inflation_match:
        status = "FULL_DIVERGENCE"
        note = (f"Disaccordo totale: mercato dice growth={m_growth}/inflation={m_inflation}, "
                f"FRED dice growth={fred_growth}/inflation={fred_inflation}.")
    else:
        mismatch = "growth" if not growth_match else "inflation"
        status = "PARTIAL_DIVERGENCE"
        note = (f"Disaccordo solo su {mismatch}: mercato={m_growth if mismatch == 'growth' else m_inflation}, "
                f"FRED={fred_growth if mismatch == 'growth' else fred_inflation}.")

    return {
        "status":          status,
        "market_growth":   m_growth,
        "market_inflation": m_inflation,
        "fred_growth":     fred_growth,
        "fred_inflation":  fred_inflation,
        "note":            note,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not FRED_API_KEY:
        print("\n  FRED_API_KEY non impostata — registrazione gratuita su")
        print("  https://fred.stlouisfed.org/docs/api/api_key.html, poi aggiungila a .env\n")
        Path("./data").mkdir(exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            json.dump({"generated_at": datetime.utcnow().isoformat() + "Z",
                       "status": "NO_API_KEY"}, f, indent=2)
        return

    print(f"\n  Fetching FRED series...", flush=True)
    start_date = (datetime.today() - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")

    data: dict = {}
    for series_id, name in ALL_SERIES.items():
        series = fetch_fred_series(series_id, start_date)
        if series:
            data[series_id] = series
            print(f"  ✓ {series_id:<10} {name:<32} {series[-1][1]}", flush=True)
        else:
            print(f"  ✗ {series_id:<10} {name:<32} (unavailable)", flush=True)

    growth_state,    growth_detail    = classify_growth_fred(data)
    inflation_state, inflation_detail = classify_inflation_fred(data)
    comparison = compare_with_market_regime(growth_state, inflation_state)

    print(f"\n  {'='*66}")
    print(f"  FRED MACRO CROSS-CHECK — {datetime.today().strftime('%Y-%m-%d')}")
    print(f"  {'='*66}")
    print(f"\n  Growth (FRED):     {growth_state:<12}  {growth_detail}")
    print(f"  Inflation (FRED):  {inflation_state:<12}  {inflation_detail}")
    print(f"\n  ──────────────────────────────────────────────────────────────")
    print(f"  vs regime di mercato: {comparison['status']}")
    print(f"  {comparison['note']}")

    # Key daily levels for context
    dgs10 = data.get("DGS10")
    if dgs10:
        print(f"\n  10Y Treasury (ufficiale): {dgs10[-1][1]:.2f}%")
    t10y2y = data.get("T10Y2Y")
    if t10y2y:
        spread = t10y2y[-1][1]
        print(f"  10Y-2Y spread: {spread:+.2f}  " +
              ("(INVERTITO — rischio recessione)" if spread < 0 else "(normale)"))
    t5yie = data.get("T5YIE")
    if t5yie:
        print(f"  Inflazione attesa 5Y (breakeven): {t5yie[-1][1]:.2f}%")

    output = {
        "generated_at":    datetime.utcnow().isoformat() + "Z",
        "status":          "OK",
        "growth":          growth_state,
        "growth_detail":   growth_detail,
        "inflation":       inflation_state,
        "inflation_detail": inflation_detail,
        "vs_market_regime": comparison,
        "indicators": {
            sid: {"name": ALL_SERIES[sid], "latest_date": s[-1][0], "latest_value": s[-1][1]}
            for sid, s in data.items()
        },
    }
    Path("./data").mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved → {OUTPUT_PATH}\n")


if __name__ == "__main__":
    main()
