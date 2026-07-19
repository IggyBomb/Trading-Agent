#!/usr/bin/env python3
"""
sector_rotation.py — Weekly sector rotation monitor

Tracks 11 US SPDR sectors + EU iShares/Xtrackers equivalents.
Ranks by 5d momentum. Outputs data/sector_rotation.json + formatted report.

Usage: python3 sector_rotation.py
"""

import json, os, sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance pandas --quiet")
    import yfinance as yf
    import pandas as pd

OUTPUT_PATH = "./data/sector_rotation.json"

US_SECTORS = {
    "XLK":  "Technology",
    "XLF":  "Financials",
    "XLE":  "Energy",
    "XLV":  "Healthcare",
    "XLI":  "Industrials",
    "XLY":  "Consumer Discret.",
    "XLP":  "Consumer Staples",
    "XLU":  "Utilities",
    "XLRE": "Real Estate",
    "XLB":  "Materials",
    "XLC":  "Comm. Services",
}

EU_SECTORS = {
    "EXV1.DE": "EU Banks",
    "EXV3.DE": "EU Technology",
    "EXH1.DE": "EU Oil & Gas",
    "EXV4.DE": "EU Healthcare",
    "EXH4.DE": "EU Industrials",
    "EXH5.DE": "EU Insurance",
    "EXV5.DE": "EU Autos",
    "EXV6.DE": "EU Basic Resources",
    "EXV2.DE": "EU Telecom",
    "EXH3.DE": "EU Food & Bev",
    "EXV8.DE": "EU Construction",
    "EXV9.DE": "EU Travel & Leisure",
}

BENCHMARKS = {
    "SPY":     "S&P 500",
    "QQQ":     "Nasdaq 100",
    "IWM":     "Russell 2000",
    "SXXP.DE": "Stoxx 600",
    "IWDA.AS": "MSCI World",
}


def fetch_sector_data(tickers: dict) -> dict:
    end   = datetime.today()
    start = end - timedelta(days=75)
    data  = {}
    for ticker, name in tickers.items():
        try:
            hist = yf.download(ticker,
                               start=start.strftime("%Y-%m-%d"),
                               end=end.strftime("%Y-%m-%d"),
                               progress=False, auto_adjust=True)
            if isinstance(hist.columns, pd.MultiIndex):
                hist.columns = hist.columns.droplevel(1)
            if "Close" not in hist.columns or len(hist) < 5:
                continue
            closes = hist["Close"].dropna()
            n      = len(closes)

            def ret(periods):
                if n > periods:
                    return round(float(closes.iloc[-1] / closes.iloc[-1 - periods] - 1) * 100, 2)
                return None

            data[ticker] = {
                "name":       name,
                "price":      round(float(closes.iloc[-1]), 2),
                "ret_1d":     ret(1),
                "ret_5d":     ret(5),
                "ret_1m":     ret(22),
                "ret_3m":     ret(63),
                "above_ma50":  bool(float(closes.iloc[-1]) > float(closes.rolling(50).mean().iloc[-1])) if n >= 50 else None,
                "above_ma200": bool(float(closes.iloc[-1]) > float(closes.rolling(200).mean().iloc[-1])) if n >= 200 else None,
            }
        except Exception:
            pass
    return data


def rank_by(data: dict, key: str = "ret_5d") -> list:
    ranked = [(t, d) for t, d in data.items() if d.get(key) is not None]
    ranked.sort(key=lambda x: x[1][key], reverse=True)
    for i, (t, d) in enumerate(ranked):
        d["rank"] = i + 1
    return ranked


def print_table(title: str, ranked: list):
    if not ranked:
        return
    n = len(ranked)
    print(f"\n  {title}")
    print(f"  {'─'*67}")
    print(f"  {'':2} {'ETF':<10} {'Name':<24} {'1d':>6} {'5d':>7} {'1M':>7} {'3M':>7}  MA50 MA200")
    print(f"  {'─'*67}")
    for rank, (ticker, d) in enumerate(ranked, 1):
        r1  = f"{d['ret_1d']:+.1f}%" if d.get("ret_1d") is not None else "  —"
        r5  = f"{d['ret_5d']:+.1f}%" if d.get("ret_5d") is not None else "  —"
        r1m = f"{d['ret_1m']:+.1f}%" if d.get("ret_1m") is not None else "  —"
        r3m = f"{d['ret_3m']:+.1f}%" if d.get("ret_3m") is not None else "  —"
        ma50  = "✓" if d.get("above_ma50")  else ("✗" if d.get("above_ma50")  is False else "—")
        ma200 = "✓" if d.get("above_ma200") else ("✗" if d.get("above_ma200") is False else "—")
        arrow = "▲" if rank <= 3 else ("▼" if rank > n - 3 else " ")
        print(f"  {arrow} {ticker:<10} {d['name']:<24} {r1:>6} {r5:>7} {r1m:>7} {r3m:>7}  {ma50:<4} {ma200}")


def rotation_signal(us_ranked: list) -> str:
    if not us_ranked:
        return ""
    top3    = [t for t, _ in us_ranked[:3]]
    bottom3 = [t for t, _ in us_ranked[-3:]]
    tech_r  = next((d["rank"] for t, d in us_ranked if t == "XLK"), None)
    fin_r   = next((d["rank"] for t, d in us_ranked if t == "XLF"), None)
    energy_r= next((d["rank"] for t, d in us_ranked if t == "XLE"), None)

    lines = [
        f"  Leading sectors:  {', '.join(top3)}",
        f"  Lagging sectors:  {', '.join(bottom3)}",
    ]
    if tech_r and fin_r:
        if tech_r < fin_r:
            lines.append(f"  Growth/Tech rotation  (XLK #{tech_r} > XLF #{fin_r})")
        else:
            lines.append(f"  Value/Financial rotation  (XLF #{fin_r} > XLK #{tech_r})")
    if energy_r and energy_r <= 3:
        lines.append(f"  Energy in leadership (XLE #{energy_r}) — Reflation signal")
    return "\n".join(lines)


def main():
    print(f"\n  Fetching sector data...", flush=True)

    bench_data = fetch_sector_data(BENCHMARKS)
    us_data    = fetch_sector_data(US_SECTORS)
    eu_data    = fetch_sector_data(EU_SECTORS)

    us_ranked  = rank_by(us_data)
    eu_ranked  = rank_by(eu_data)

    print(f"\n  {'='*67}")
    print(f"  SECTOR ROTATION — {datetime.today().strftime('%Y-%m-%d')}")
    print(f"  {'='*67}")

    print(f"\n  BENCHMARKS")
    print(f"  {'─'*67}")
    for t, d in bench_data.items():
        r5   = f"{d['ret_5d']:+.1f}%" if d.get("ret_5d") is not None else "—"
        r1m  = f"{d['ret_1m']:+.1f}%" if d.get("ret_1m") is not None else "—"
        ma200 = "✓" if d.get("above_ma200") else ("✗" if d.get("above_ma200") is False else "—")
        print(f"  {t:<12} {d['name']:<24} 5d: {r5:>7}  1M: {r1m:>7}  MA200: {ma200}")

    print_table("US SECTORS — ranked by 5d momentum", us_ranked)
    print_table("EU SECTORS — ranked by 5d momentum", eu_ranked)

    sig = rotation_signal(us_ranked)
    if sig:
        print(f"\n  ROTATION SIGNAL")
        print(f"  {'─'*67}")
        print(sig)

    # ── Save output ───────────────────────────────────────────────────────
    output = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "benchmarks":   bench_data,
        "us_sectors":   dict(us_ranked),
        "eu_sectors":   dict(eu_ranked),
    }
    Path("./data").mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved → {OUTPUT_PATH}\n")


if __name__ == "__main__":
    main()
