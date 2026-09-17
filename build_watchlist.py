#!/usr/bin/env python3
"""
build_watchlist.py — Rebuild data/watchlist.txt

Fetches live S&P 500 + Nasdaq 100 + FTSE 100 + DAX 40 + CAC 40 +
FTSE MIB + AEX constituents from Wikipedia, merges the US indices with
a curated mid-cap/growth list. JP, CA, BR are dropped. Falls back to
preserving the existing watchlist's EU tickers only if every live EU
index fetch fails.

Run whenever you want to refresh the US index composition (quarterly
rebalances etc.). Safe to re-run — always rewrites from scratch.

Usage: python3 build_watchlist.py
"""

import os
import re
from io import StringIO

import pandas as pd
import requests

WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "data", "watchlist.txt")

EU_SUFFIXES = {
    ".MI", ".AS", ".PA", ".L", ".DE", ".F", ".ST", ".CO",
    ".OL", ".HE", ".BR", ".LS", ".MC", ".VI", ".SW", ".AT",
}

# Wikipedia 403s requests with no User-Agent — every index fetch needs this.
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def _get_html(url: str) -> str:
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text

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
        html = _get_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        df = pd.read_html(StringIO(html), attrs={"id": "constituents"})[0]
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
        # NB: "Nasdaq-100" itself no longer inlines a components table — the
        # constituent wikitable lives on this separate list page.
        html = _get_html("https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies")
        df = pd.read_html(StringIO(html), attrs={"id": "constituents"})[0]
        col = "Ticker" if "Ticker" in df.columns else df.columns[0]
        tickers = {clean(str(t)) for t in df[col].dropna().tolist()}
        print(f"  Nasdaq 100: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        print(f"  WARNING: Nasdaq 100 fetch failed ({e})")
        return set()


# Wikipedia constituent tables for the major EU indices. DAX/CAC/FTSE MIB/AEX
# already publish the Yahoo-style suffixed ticker (e.g. "SAP.DE", "CS.PA");
# FTSE 100 publishes the bare LSE ticker, so it needs ".L" appended.
def _fetch_index_tickers(url: str, label: str, min_rows: int, append_suffix: str = "") -> set:
    try:
        html = _get_html(url)
        tables = pd.read_html(StringIO(html))
        for t in tables:
            cols_lower = [str(c).lower() for c in t.columns]
            if "ticker" in cols_lower and len(t) >= min_rows:
                col = t.columns[cols_lower.index("ticker")]
                raw = t[col].dropna().astype(str).tolist()
                tickers = {clean(x) + append_suffix for x in raw}
                print(f"  {label:10s}: {len(tickers)} tickers")
                return tickers
        print(f"  WARNING: {label} table not found in Wikipedia page")
        return set()
    except Exception as e:
        print(f"  WARNING: {label} fetch failed ({e})")
        return set()


def fetch_ftse100() -> set:
    return _fetch_index_tickers(
        "https://en.wikipedia.org/wiki/FTSE_100_Index", "FTSE 100", min_rows=80, append_suffix=".L"
    )


def fetch_dax40() -> set:
    return _fetch_index_tickers("https://en.wikipedia.org/wiki/DAX", "DAX 40", min_rows=30)


def fetch_cac40() -> set:
    return _fetch_index_tickers("https://en.wikipedia.org/wiki/CAC_40", "CAC 40", min_rows=30)


def fetch_ftsemib() -> set:
    return _fetch_index_tickers("https://en.wikipedia.org/wiki/FTSE_MIB", "FTSE MIB", min_rows=30)


def fetch_aex() -> set:
    return _fetch_index_tickers("https://en.wikipedia.org/wiki/AEX_index", "AEX", min_rows=20)


def load_eu_tickers() -> set:
    """Fallback only — used if all live EU index fetches fail."""
    if not os.path.exists(WATCHLIST_PATH):
        print("  WARNING: no existing watchlist.txt — EU tickers not loaded")
        return set()
    with open(WATCHLIST_PATH) as f:
        lines = [l.strip() for l in f if l.strip()]
    eu = {t for t in lines if any(t.upper().endswith(s.upper()) for s in EU_SUFFIXES)}
    print(f"  EU        : {len(eu)} tickers preserved from existing watchlist (fallback)")
    return eu


def clean(t: str) -> str:
    return re.sub(r"\s+", "", t).upper()


def main():
    print("\nRebuilding watchlist.txt...")
    print("-" * 40)

    sp500   = {clean(t) for t in fetch_sp500()}
    ndx100  = {clean(t) for t in fetch_nasdaq100()}
    curated = {clean(t) for t in CURATED}

    ftse100 = {clean(t) for t in fetch_ftse100()}
    dax40   = {clean(t) for t in fetch_dax40()}
    cac40   = {clean(t) for t in fetch_cac40()}
    ftsemib = {clean(t) for t in fetch_ftsemib()}
    aex     = {clean(t) for t in fetch_aex()}
    eu = ftse100 | dax40 | cac40 | ftsemib | aex

    if not eu:
        print("  WARNING: all live EU index fetches failed — falling back to existing watchlist EU tickers")
        eu = load_eu_tickers()

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
    print(f"    FTSE 100 : {len(ftse100)}")
    print(f"    DAX 40   : {len(dax40)}")
    print(f"    CAC 40   : {len(cac40)}")
    print(f"    FTSE MIB : {len(ftsemib)}")
    print(f"    AEX      : {len(aex)}")
    print(f"  JP/CA/BR : dropped")
    print(f"  Saved to : {WATCHLIST_PATH}")
    print("-" * 40)
    print()


if __name__ == "__main__":
    main()
