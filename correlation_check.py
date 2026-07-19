#!/usr/bin/env python3
"""
correlation_check.py — Portfolio correlation and sector concentration monitor

Usage:
  python3 correlation_check.py              — check all open positions
  python3 correlation_check.py --add TICKER — include a proposed new ticker
  python3 correlation_check.py --threshold 0.7
"""

import json, sys, os, argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
    import numpy as np
    import pandas as pd
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance numpy pandas --quiet")
    import yfinance as yf
    import numpy as np
    import pandas as pd

from config import ACCOUNT_SIZE, TRADES_PATH

LOGS_PATH = TRADES_PATH
LOOKBACK  = 60  # days of return history

SECTOR_OVERRIDE = {
    "XOM": "Energy",    "OXY": "Energy",    "CVX": "Energy",    "COP": "Energy",
    "EOG": "Energy",    "TRGP": "Energy",   "WMB": "Energy",    "OKLO": "Energy",
    "CSCO": "Technology", "PANW": "Technology", "META": "Technology", "AAPL": "Technology",
    "MSFT": "Technology", "NVDA": "Technology", "AMZN": "Technology", "GOOGL": "Technology",
    "POET": "Technology", "PLAB": "Technology",
    "RF": "Financials",  "ACGL": "Financials", "INVA": "Financials", "AON": "Financials",
    "PGR": "Financials", "AFL": "Financials",  "SOFI": "Financials",
    "ISP.MI": "Financials", "BPE.MI": "Financials", "BMPS.MI": "Financials",
    "UCG.MI": "Financials", "MB.MI": "Financials",  "HSBA.L": "Financials",
    "BARC.L": "Financials", "LLOY.L": "Financials", "DBK.DE": "Financials",
    "GLE.PA": "Financials",
    "INCY": "Healthcare", "CRMD": "Healthcare",
    "NEM": "Materials",
    "EXPD": "Industrials", "LKQ": "Industrials", "LEN": "Industrials",
    "RKLB": "Aerospace",
    "MELI": "Consumer", "DIS": "Consumer",
}


def load_open_positions():
    if not Path(LOGS_PATH).exists():
        return []
    with open(LOGS_PATH) as f:
        trades = [json.loads(l) for l in f if l.strip()]
    return [t for t in trades if t.get("status") == "open"]


def get_sector(ticker):
    if ticker in SECTOR_OVERRIDE:
        return SECTOR_OVERRIDE[ticker]
    try:
        info = yf.Ticker(ticker).info
        return info.get("sector") or info.get("sectorDisp") or "Unknown"
    except Exception:
        return "Unknown"


def download_returns(tickers, days=LOOKBACK):
    end   = datetime.today()
    start = end - timedelta(days=days + 15)
    results = {}
    for ticker in tickers:
        try:
            hist = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                               end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
            if isinstance(hist.columns, pd.MultiIndex):
                hist.columns = hist.columns.droplevel(1)
            if "Close" in hist.columns and len(hist) > 5:
                results[ticker] = hist["Close"].pct_change().dropna()
        except Exception:
            pass
    return results


def build_corr_matrix(returns_dict):
    if len(returns_dict) < 2:
        return pd.DataFrame()
    df = pd.DataFrame(returns_dict).dropna()
    return df.corr()


def main():
    parser = argparse.ArgumentParser(prog="correlation_check")
    parser.add_argument("--add",       "-a", default=None,  help="Proposed new ticker to test")
    parser.add_argument("--threshold", "-t", type=float, default=0.70, help="Correlation warning threshold")
    args = parser.parse_args()

    open_trades = load_open_positions()
    tickers     = list({t["ticker"] for t in open_trades})

    proposed = None
    if args.add:
        proposed = args.add.upper()
        if proposed not in tickers:
            tickers.append(proposed)

    if not tickers:
        print("\n  No open positions to check.\n")
        return

    print(f"\n  Downloading return data ({LOOKBACK}d) for {len(tickers)} tickers...")
    returns = download_returns(tickers)

    # ── Sector concentration ───────────────────────────────────────────────
    sector_groups: dict[str, list] = {}
    for t in tickers:
        sec = get_sector(t)
        sector_groups.setdefault(sec, []).append(t)

    print(f"\n  {'='*58}")
    print(f"  SECTOR CONCENTRATION")
    print(f"  {'='*58}")
    for sec, members in sorted(sector_groups.items(), key=lambda x: -len(x[1])):
        marker = "  ⛔ RISK.md LIMIT (max 2)" if len(members) > 2 else "  ⚠ CONCENTRATED" if len(members) > 1 else ""
        print(f"  {sec:<22}  {len(members)}×  {', '.join(members)}{marker}")

    # ── Correlation matrix ─────────────────────────────────────────────────
    corr = build_corr_matrix(returns)
    if corr.empty:
        print("\n  Not enough data for correlation matrix.\n")
        return

    print(f"\n  {'='*58}")
    print(f"  CORRELATION MATRIX (last {LOOKBACK}d)")
    print(f"  {'='*58}")
    cols = list(corr.columns)
    header = f"  {'':>12}" + "".join(f"  {t[:8]:>8}" for t in cols)
    print(header)
    for row in corr.index:
        vals = ""
        for col in cols:
            v = corr.loc[row, col]
            if row == col:
                vals += f"  {'---':>8}"
            elif abs(v) >= args.threshold:
                vals += f"  {v:>+7.2f}⚠"
            else:
                vals += f"  {v:>+8.2f}"
        print(f"  {row[:12]:>12}{vals}")

    # ── Flagged pairs ──────────────────────────────────────────────────────
    flagged = []
    for i, r in enumerate(corr.index):
        for j, c in enumerate(corr.columns):
            if j <= i:
                continue
            v = corr.loc[r, c]
            if abs(v) >= args.threshold:
                flagged.append((r, c, v))

    print(f"\n  {'='*58}")
    print(f"  CORRELATED PAIRS (≥ {args.threshold:.2f})")
    print(f"  {'='*58}")
    if flagged:
        for r, c, v in sorted(flagged, key=lambda x: -abs(x[2])):
            marker    = "⛔" if abs(v) >= 0.85 else "⚠ "
            direction = "CO-MOVE" if v > 0 else "INVERSE"
            print(f"  {marker}  {r} / {c}:  r = {v:+.2f}  [{direction}]")
            if proposed and (r == proposed or c == proposed):
                other = c if r == proposed else r
                print(f"       → Adding {proposed} creates effective double-exposure to {other}")
    else:
        print(f"  ✓ No pairs above {args.threshold:.2f} — portfolio diversified")

    # ── Effective combined exposure ────────────────────────────────────────
    if open_trades and flagged:
        print(f"\n  EFFECTIVE EXPOSURE (correlated clusters)")
        print(f"  {'─'*58}")
        for r, c, v in flagged:
            if v >= args.threshold:
                val_r = sum(t.get("position_value", 0) for t in open_trades if t["ticker"] == r)
                val_c = sum(t.get("position_value", 0) for t in open_trades if t["ticker"] == c)
                if val_r and val_c:
                    combined = val_r + val_c
                    print(f"  {r} €{val_r:,.0f} + {c} €{val_c:,.0f} = €{combined:,.0f} "
                          f"({combined/ACCOUNT_SIZE*100:.1f}% account)  [r={v:.2f}]")

    print()


if __name__ == "__main__":
    main()
