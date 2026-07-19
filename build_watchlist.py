#!/usr/bin/env python3
"""
build_watchlist.py — Rebuild data/watchlist.txt

Fetches live S&P 500 + Nasdaq 100 from Wikipedia, merges with a
curated mid-cap/growth list, and preserves all EU tickers from the
existing watchlist. JP, CA, BR are dropped.

Run whenever you want to refresh the US index composition (quarterly
rebalances etc.). Safe to re-run — always rewrites from scratch.

Usage: python3 build_watchlist.py
"""

import os
import re
import pandas as pd

WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "data", "watchlist.txt")

EU_SUFFIXES = {
    ".MI", ".AS", ".PA", ".L", ".DE", ".F", ".ST", ".CO",
    ".OL", ".HE", ".BR", ".LS", ".MC", ".VI", ".SW", ".AT",
}

# ── Curated mid-cap / growth names not covered by S&P 500 or Nasdaq 100 ──────
# Add or remove tickers here as your universe evolves.
CURATED = sorted({
    # Fintech & Payments
    "PAYO", "AFRM", "BILL", "UPST", "HOOD", "DAVE", "NU",
    # Cybersecurity (beyond Nasdaq 100 names)
    "S", "TENB", "RPD", "QLYS",
    # AI / Software
    "AI", "SOUN", "BBAI", "PATH", "GTLB", "DOMO",
    # Space & Defense tech
    "RKLB", "ASTS", "LUNR", "KTOS",
    # Healthcare / Biotech growth
    "RXRX", "BEAM", "EDIT", "NTLA", "CRSP", "NTRA", "TMDX", "INVA",
    "HIMS", "ACCD",
    # Consumer growth
    "BROS", "CAVA", "SG", "SHAK",
    # Industrials / Clean energy
    "GTLS", "ESAB", "ATKR", "ITRI", "ARRY", "NOVA", "BLNK", "CHPT",
    # Semiconductors (smaller cap)
    "ONTO", "UCTT", "ACLS", "COHU", "CAMT", "FORM", "POET", "AEHR",
    # Materials
    "MP",
    # Marketplace / Platform
    "LYFT",
    # Energy (smaller cap E&P)
    "VTLE", "CIVI", "SM",
    # Positions / names analyzed in prior sessions
    "SOFI", "NCLH", "ACGL",
})


def fetch_sp500() -> set:
    try:
        df = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            attrs={"id": "constituents"},
        )[0]
        col = "Symbol" if "Symbol" in df.columns else df.columns[0]
        # Wikipedia uses BRK.B; yfinance wants BRK-B
        tickers = {t.replace(".", "-") for t in df[col].dropna().tolist()}
        print(f"  S&P 500   : {len(tickers)} tickers")
        return tickers
    except Exception as e:
        print(f"  WARNING: S&P 500 fetch failed ({e})")
        return set()


def fetch_nasdaq100() -> set:
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        for t in tables:
            lower_cols = [c.lower() for c in t.columns]
            if "ticker" in lower_cols or "symbol" in lower_cols:
                col = t.columns[
                    [c.lower() in ("ticker", "symbol") for c in t.columns].index(True)
                ]
                tickers = set(t[col].dropna().tolist())
                if len(tickers) > 80:
                    print(f"  Nasdaq 100: {len(tickers)} tickers")
                    return tickers
        print("  WARNING: Nasdaq 100 table not found in Wikipedia page")
        return set()
    except Exception as e:
        print(f"  WARNING: Nasdaq 100 fetch failed ({e})")
        return set()


def load_eu_tickers() -> set:
    if not os.path.exists(WATCHLIST_PATH):
        print("  WARNING: no existing watchlist.txt — EU tickers not loaded")
        return set()
    with open(WATCHLIST_PATH) as f:
        lines = [l.strip() for l in f if l.strip()]
    eu = {t for t in lines if any(t.upper().endswith(s.upper()) for s in EU_SUFFIXES)}
    print(f"  EU        : {len(eu)} tickers preserved from existing watchlist")
    return eu


def clean(t: str) -> str:
    return re.sub(r"\s+", "", t).upper()


def main():
    print("\nRebuilding watchlist.txt...")
    print("-" * 40)

    sp500   = {clean(t) for t in fetch_sp500()}
    ndx100  = {clean(t) for t in fetch_nasdaq100()}
    curated = {clean(t) for t in CURATED}
    eu      = load_eu_tickers()

    us_all = sp500 | ndx100 | curated

    # US sorted first, then EU sorted — deduped
    ordered = []
    seen: set = set()
    for t in sorted(us_all) + sorted(eu):
        if t not in seen:
            seen.add(t)
            ordered.append(t)

    os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)
    with open(WATCHLIST_PATH, "w") as f:
        f.write("\n".join(ordered) + "\n")

    us_count = len([t for t in ordered if not any(t.endswith(s) for s in EU_SUFFIXES)])
    eu_count = len(ordered) - us_count

    overlap = sp500 & ndx100
    curated_new = curated - sp500 - ndx100

    print("-" * 40)
    print(f"  Total    : {len(ordered)} tickers")
    print(f"  US       : {us_count}")
    print(f"    S&P 500 only    : {len(sp500 - ndx100)}")
    print(f"    Nasdaq 100 only : {len(ndx100 - sp500)}")
    print(f"    Both indices    : {len(overlap)}")
    print(f"    Curated (extra) : {len(curated_new)}")
    print(f"  EU       : {eu_count}")
    print(f"  JP/CA/BR : dropped")
    print(f"  Saved to : {WATCHLIST_PATH}")
    print("-" * 40)
    print()


if __name__ == "__main__":
    main()
