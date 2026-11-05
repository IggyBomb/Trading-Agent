#!/usr/bin/env python3
"""
fetch_growth_estimates.py: one-off, standalone fetch of analyst EPS growth estimates
for the sector-comparison workbook (PEG FWD column).

Reads the ticker universe from data/fundamental_data.json (read-only) and writes ONE
file: sector_comparison/growth_estimates.csv. Imports nothing from the rest of the
repo and changes nothing in it.

Per ticker (yfinance):
  ltg_5y          analysts' long-term EPS growth: '+5y' / 'LTG' row of growth_estimates
                  (same parsing as long_term_analysis/pre_screen.py::_growth_estimate_5y)
  eps_cur_fy      consensus EPS, current fiscal year  (earnings_estimate '0y', avg)
  eps_next_fy     consensus EPS, next fiscal year     (earnings_estimate '+1y', avg)
  growth_next_fy  eps_next_fy / eps_cur_fy - 1, only if eps_cur_fy > 0 (fallback for ltg_5y)
  analysts_*      number of analysts behind each EPS estimate
  status          ltg | next_fy_only | none | error: ...

Usage (from the repo root):
  python sector_comparison/fetch_growth_estimates.py --tickers AMZN,ISP.MI,SAP.DE   # smoke test
  python sector_comparison/fetch_growth_estimates.py                                # full universe
  python sector_comparison/fetch_growth_estimates.py --resume                       # continue / retry errors
"""
import argparse, csv, json, math, random, sys, time
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

HERE = Path(__file__).resolve().parent
DEFAULT_SRC = HERE.parent / "data" / "fundamental_data.json"
DEFAULT_OUT = HERE / "growth_estimates.csv"
PAUSE = 0.4      # seconds between tickers (jittered), to stay under Yahoo's rate limit
RETRIES = 1
FIELDS = ["ticker", "ltg_5y", "eps_cur_fy", "eps_next_fy", "growth_next_fy",
          "analysts_cur_fy", "analysts_next_fy", "status", "fetched_at"]


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def num(x):
    try:
        v = float(x)
        return None if math.isnan(v) or math.isinf(v) else v
    except (TypeError, ValueError):
        return None


def ltg_from(ge):
    """Copy of pre_screen.py::_growth_estimate_5y. Returns a fraction (0.23 = 23%) or None."""
    if ge is None or getattr(ge, "empty", True):
        return None
    col = "stock" if "stock" in ge.columns else ge.columns[0]
    for label in ge.index:
        if str(label).strip().lower() in ("ltg", "+5y", "5y", "next 5 years (per annum)"):
            v = num(ge.loc[label, col])
            if v is not None and abs(v) > 5:          # came as percent, not fraction
                v /= 100.0
            return v
    return None


def cell(df, row, col):
    if df is None or getattr(df, "empty", True) or row not in df.index or col not in df.columns:
        return None
    return num(df.loc[row, col])


def safe(fn):
    try:
        return fn()
    except Exception:
        return None


def fetch_one(ticker):
    t = yf.Ticker(ticker)
    ge = safe(lambda: t.growth_estimates)
    ee = safe(lambda: t.earnings_estimate)
    if ge is None and ee is None:
        raise RuntimeError("no analysis data returned")   # triggers the retry
    ltg = ltg_from(ge)
    e0, e1 = cell(ee, "0y", "avg"), cell(ee, "+1y", "avg")
    g1 = (e1 / e0 - 1) if (e0 is not None and e1 is not None and e0 > 0) else None
    return {
        "ticker": ticker, "ltg_5y": ltg, "eps_cur_fy": e0, "eps_next_fy": e1,
        "growth_next_fy": g1,
        "analysts_cur_fy": cell(ee, "0y", "numberOfAnalysts"),
        "analysts_next_fy": cell(ee, "+1y", "numberOfAnalysts"),
        "status": "ltg" if ltg is not None else ("next_fy_only" if g1 is not None else "none"),
        "fetched_at": now(),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tickers", help="comma-separated list instead of the full universe")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--resume", action="store_true",
                    help="skip tickers already fetched OK; retry the ones that errored")
    a = ap.parse_args(argv)

    tickers = (a.tickers.split(",") if a.tickers
               else sorted(json.load(open(a.src))["fundamentals"]))
    if a.limit:
        tickers = tickers[: a.limit]

    resuming = a.resume and a.out.exists()
    done = set()
    if resuming:
        done = {r["ticker"] for r in csv.DictReader(open(a.out))
                if not r["status"].startswith("error")}
    todo = [t for t in tickers if t not in done]
    print(f"{len(tickers)} tickers | {len(done)} already OK in {a.out.name} | fetching {len(todo)}")

    counts = {"ltg": 0, "next_fy_only": 0, "none": 0, "error": 0}
    with open(a.out, "a" if resuming else "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if not resuming:
            w.writeheader()
        for i, tk in enumerate(todo, 1):
            for attempt in range(RETRIES + 1):
                try:
                    rec = fetch_one(tk)
                    break
                except Exception as e:
                    rec = {"ticker": tk, "status": f"error: {type(e).__name__}", "fetched_at": now()}
                    if attempt < RETRIES:
                        time.sleep(2)
            w.writerow(rec)
            fh.flush()                                   # written as it goes: a crash loses nothing
            counts[rec["status"] if rec["status"] in counts else "error"] += 1
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}  {counts}")
            time.sleep(PAUSE * random.uniform(0.7, 1.3))
    print(f"done -> {a.out}")


if __name__ == "__main__":
    sys.exit(main())
