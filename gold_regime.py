#!/usr/bin/env python3
"""
gold_regime.py — macro regime for precious-metal miners (added 2026-10-30).

Gold pays no cash flow, so its opportunity cost is the REAL yield, and it is
priced in dollars. This script turns those two channels into one regime flag
that watchlist_ranker.regime_penalty() applies to tickers whose yfinance
industry is in config.GOLD_INDUSTRIES (gold / silver / other precious metals).

  HEADWIND (GOLD_HEADWIND_PEN, default -10)
      (10Y real yield up >= GOLD_REAL_YIELD_UP_BP over ~3 months
       OR dollar index up >= GOLD_DOLLAR_UP_PCT over ~3 months and above its MA50)
      AND gold (GLD) below its 200-day average.
      The GLD condition is deliberate: in 2022-25 real yields hit 15-year highs
      and gold still doubled (central-bank buying). Price must confirm macro.

  TAILWIND (GOLD_TAILWIND_BONUS, default +5)
      2Y Treasury yield >= GOLD_2Y_OFF_PEAK_BP below its 6-month high (market
      pricing the end of the hiking cycle -- leads the actual policy peak)
      AND miners outperforming gold (GDX/GLD ratio above its 50-day average).
      Never on the same day as a headwind.

  NEUTRAL otherwise, and whenever data is missing (fail-closed: missing data
  never produces a penalty or a bonus).

Data (no API key needed):
  FRED public CSV  : DFII10 (10Y TIPS real yield), DGS2 (2Y nominal)
  Yahoo (yfinance) : GLD, GDX, DX-Y.NYB (dollar index; falls back to UUP)

Usage: python3 gold_regime.py          -> data/gold_regime.json
"""
import io, json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from config import (  # noqa: E402
    GOLD_REGIME_PATH, GOLD_REAL_YIELD_UP_BP, GOLD_DOLLAR_UP_PCT,
    GOLD_2Y_OFF_PEAK_BP, GOLD_HEADWIND_PEN, GOLD_TAILWIND_BONUS,
)

FETCH_DAYS = 420          # enough for a 200-day MA plus a 3-month lookback
LB_3M      = 63           # trading days ~ 3 months
LB_6M      = 126          # trading days ~ 6 months
FRED_CSV   = "https://fred.stlouisfed.org/graph/fredgraph.csv"


# ── fetch ───────────────────────────────────────────────────────────────────
def fetch_fred(series_id: str, start: str) -> pd.Series | None:
    """Public CSV endpoint -- works without FRED_API_KEY."""
    try:
        import requests
        r = requests.get(FRED_CSV, params={"id": series_id, "cosd": start}, timeout=20,
                         verify=os.environ.get("SSL_CERT_FILE") or True)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        s = pd.Series(pd.to_numeric(df.iloc[:, 1], errors="coerce").values,
                      index=pd.to_datetime(df.iloc[:, 0])).dropna()
        return s if len(s) else None
    except Exception as e:
        print(f"  ! FRED {series_id} unavailable: {e}")
        return None


def fetch_close(ticker: str, start: str) -> pd.Series | None:
    try:
        import yfinance as yf
        h = yf.download(ticker, start=start, progress=False, auto_adjust=True)
        if isinstance(h.columns, pd.MultiIndex):
            h.columns = h.columns.droplevel(1)
        s = h["Close"].dropna()
        return s if len(s) else None
    except Exception as e:
        print(f"  ! {ticker} unavailable: {e}")
        return None


# ── pure calculations (unit-tested) ─────────────────────────────────────────
def change_over(s, n):
    if s is None or len(s) <= n:
        return None
    return float(s.iloc[-1] - s.iloc[-1 - n])


def pct_change_over(s, n):
    if s is None or len(s) <= n or s.iloc[-1 - n] == 0:
        return None
    return float(s.iloc[-1] / s.iloc[-1 - n] - 1) * 100


def above_ma(s, n):
    if s is None or len(s) < n:
        return None
    return bool(s.iloc[-1] > s.iloc[-n:].mean())


def classify(real_yield, y2, dxy, gld, gdx) -> dict:
    """All inputs are daily pd.Series, oldest -> newest (or None). Yields in %."""
    ry_chg = change_over(real_yield, LB_3M)
    ry_chg_bp = round(ry_chg * 100, 1) if ry_chg is not None else None
    dxy_3m = pct_change_over(dxy, LB_3M)
    dxy_up_ma50 = above_ma(dxy, 50)
    gld_up_ma200 = above_ma(gld, 200)

    y2_off_high_bp = None
    if y2 is not None and len(y2) >= LB_6M:
        y2_off_high_bp = round(float(y2.iloc[-LB_6M:].max() - y2.iloc[-1]) * 100, 1)

    ratio_up_ma50 = None
    if gld is not None and gdx is not None:
        ratio_up_ma50 = above_ma((gdx / gld).dropna(), 50)

    rates_up  = ry_chg_bp is not None and ry_chg_bp >= GOLD_REAL_YIELD_UP_BP
    dollar_up = dxy_3m is not None and dxy_3m >= GOLD_DOLLAR_UP_PCT and dxy_up_ma50 is True
    gold_weak = gld_up_ma200 is False            # None (no data) never counts as weak

    headwind = (rates_up or dollar_up) and gold_weak
    tailwind = (not headwind
                and y2_off_high_bp is not None and y2_off_high_bp >= GOLD_2Y_OFF_PEAK_BP
                and ratio_up_ma50 is True)

    notes = []
    if rates_up:
        notes.append(f"10Y real yield +{ry_chg_bp:.0f}bp over 3M")
    if dollar_up:
        notes.append(f"dollar +{dxy_3m:.1f}% over 3M, above MA50")
    if (rates_up or dollar_up) and not gold_weak:
        notes.append("macro headwind NOT confirmed: gold still above its 200d MA"
                     if gld_up_ma200 else "macro headwind but GLD trend unknown -> neutral")
    if y2_off_high_bp is not None and y2_off_high_bp >= GOLD_2Y_OFF_PEAK_BP:
        notes.append(f"2Y yield {y2_off_high_bp:.0f}bp below 6M high (peak being priced)"
                     + ("" if ratio_up_ma50 else " but miners not yet leading gold"))

    regime = "HEADWIND" if headwind else ("TAILWIND" if tailwind else "NEUTRAL")
    adj = GOLD_HEADWIND_PEN if headwind else (GOLD_TAILWIND_BONUS if tailwind else 0)
    return {
        "regime": regime,
        "adjustment": adj,
        "notes": notes,
        "inputs": {
            "real_yield_10y": round(float(real_yield.iloc[-1]), 3) if real_yield is not None else None,
            "real_yield_chg_3m_bp": ry_chg_bp,
            "y2_off_6m_high_bp": y2_off_high_bp,
            "dxy_ret_3m_pct": round(dxy_3m, 2) if dxy_3m is not None else None,
            "dxy_above_ma50": dxy_up_ma50,
            "gld_above_ma200": gld_up_ma200,
            "gdx_gld_ratio_above_ma50": ratio_up_ma50,
        },
    }


def main():
    start = (datetime.today() - timedelta(days=FETCH_DAYS)).strftime("%Y-%m-%d")
    print("\n  Fetching gold-regime inputs...")
    real_yield = fetch_fred("DFII10", start)
    y2  = fetch_fred("DGS2", start)
    dxy = fetch_close("DX-Y.NYB", start)
    if dxy is None:
        dxy = fetch_close("UUP", start)
    gld = fetch_close("GLD", start)
    gdx = fetch_close("GDX", start)

    out = classify(real_yield, y2, dxy, gld, gdx)
    out["generated_at"] = datetime.now(timezone.utc).isoformat()
    out["missing"] = [n for n, s in [("DFII10", real_yield), ("DGS2", y2), ("DXY", dxy),
                                      ("GLD", gld), ("GDX", gdx)] if s is None]

    Path(GOLD_REGIME_PATH).parent.mkdir(exist_ok=True)
    with open(GOLD_REGIME_PATH, "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n  GOLD REGIME: {out['regime']}  (adjustment {out['adjustment']:+d} for precious-metal miners)")
    for k, v in out["inputs"].items():
        print(f"    {k:<26} {v}")
    for n in out["notes"]:
        print(f"    - {n}")
    if out["missing"]:
        print(f"    ! missing inputs: {', '.join(out['missing'])}")
    print(f"\n  Saved -> {GOLD_REGIME_PATH}\n")


if __name__ == "__main__":
    main()
