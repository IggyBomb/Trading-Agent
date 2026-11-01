#!/usr/bin/env python3
"""
institutional_data.py — Smart Money Score inputs for institutional-flow.md (/scan Step 8).

Until 2026-10-27 no institutional source was wired in, so every scan candidate got
the agent's DATA UNAVAILABLE fallback (score 50 / CAUTIOUS). This script pulls the
free sources that exist and scores them with the agent's own rubric:

  Component        Pts  Source                                          Coverage
  13F consensus     40  yfinance institutional_holders (top-10 13F      US listings
                        filers, pctChange vs prior quarter)
  Dark pool         20  FINRA OTC transparency API, weekly ATS +        US listings
                        non-ATS volume / consolidated volume (yfinance)  (~3 wk lag)
  Options flow      20  yfinance option chains, expiries <= 45 days     optionable US
  ETF sector flow   10  PROXY: sector ETF 1m return vs benchmark from   US + EU
                        data/sector_rotation.json (no free flow data)
  Dry powder        10  data/institutional_market.json, filled by hand  manual
                        (BofA FMS cash %, GS HF net leverage); neutral
                        when missing or older than 45 days

If 13F, dark pool AND options are all unavailable (typical for EU-only names) the
ticker keeps the agent's fallback: score 50, CAUTIOUS, DATA UNAVAILABLE. Nothing
is fabricated — every component carries its source and a status of OK / PROXY /
UNAVAILABLE so the agent can see what the number is made of.

Usage:
    python3 institutional_data.py TRV SAP.DE DHR      # score, print, write data/institutional.json
    python3 institutional_data.py --json TRV          # also print the JSON block per ticker

Run after the close: options volume and the price trend use today's bar.
"""

import argparse
import json
import re
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import requests
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pandas")

OUT_PATH = "./data/institutional.json"
SECTOR_PATH = "./data/sector_rotation.json"
MARKET_PATH = "./data/institutional_market.json"
FINRA_URL = "https://api.finra.org/data/group/otcMarket/name/weeklySummary"

# institutional-flow.md universe, matched against yfinance holder names (lower-case substrings)
TIER1 = [
    "berkshire", "citadel", "bridgewater", "point72", "millennium", "d. e. shaw", "d.e. shaw",
    "renaissance", "two sigma", "appaloosa", "pershing square", "third point", "viking global",
    "coatue", "tiger global", "blackrock", "vanguard", "state street", "fmr", "fidelity",
    "jpmorgan", "goldman sachs", "morgan stanley", "bank of america", "t. rowe", "price (t.rowe)",
    "capital research", "capital world", "capital international", "norges", "amundi", "eurizon",
    "generali", "dws", "ubs", "bnp paribas", "schroder", "man group", "societe generale",
]

US_SECTOR_ETF = {
    "Technology": "XLK", "Financial Services": "XLF", "Healthcare": "XLV", "Energy": "XLE",
    "Industrials": "XLI", "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP",
    "Utilities": "XLU", "Real Estate": "XLRE", "Basic Materials": "XLB",
    "Communication Services": "XLC",
}
EU_SECTOR_ETF = {
    "Technology": "EXV3.DE", "Healthcare": "EXV4.DE", "Energy": "EXH1.DE", "Industrials": "EXH4.DE",
    "Consumer Cyclical": "EXV5.DE", "Consumer Defensive": "EXH3.DE", "Basic Materials": "EXV6.DE",
    "Communication Services": "EXV2.DE", "Financial Services": "EXV1.DE",
}


def is_us(ticker):
    return "." not in ticker


# ── 1. 13F consensus (40) ───────────────────────────────────────────────────

def score_13f(t, price_now):
    if not is_us(t):
        return {"pts": None, "status": "UNAVAILABLE", "signal": "DATA UNAVAILABLE",
                "detail": "non-US listing: 13F covers US filers only (ESMA disclosures not wired)"}
    ih = yf.Ticker(t).institutional_holders
    if ih is None or ih.empty or "pctChange" not in ih.columns:
        return {"pts": None, "status": "UNAVAILABLE", "signal": "DATA UNAVAILABLE", "detail": "no 13F holder table"}
    adds, trims, holders = [], [], []
    for _, r in ih.iterrows():
        name, chg = str(r["Holder"]), float(r["pctChange"] or 0)
        action = "ADD" if chg > 0.02 else "TRIM" if chg < -0.02 else "HOLD"
        tier1 = any(k in name.lower() for k in TIER1)
        holders.append({"holder": name, "pct_held": round(float(r["pctHeld"]) * 100, 2),
                        "change_pct": round(chg * 100, 1), "action": action, "tier1": tier1})
        if tier1 and action == "ADD":
            adds.append(name)
        elif tier1 and action == "TRIM":
            trims.append(name)
    a, tr = len(adds), len(trims)
    # institutional-flow.md rubric: 3+ adds 40 / 1-2 adds 25 / mixed 10 / hold 15 / exits 0.
    # Top-10 tables show trims, not full exits, so trims are scored as mild bearish.
    if a >= 3 and a > tr:
        pts, sig = 40, "ACCUMULATING"
    elif a >= 1 and a > tr:
        pts, sig = 25, "ACCUMULATING"
    elif a == 0 and tr == 0:
        pts, sig = 15, "HOLDING"
    elif tr >= 3 and a == 0:
        pts, sig = 0, "DISTRIBUTING"
    else:
        pts, sig = 10, "MIXED" if a == tr else "MIXED (net trims)"
    quarter = str(ih["Date Reported"].max())[:10]
    lag = {"quarter_end": quarter}
    try:
        h = yf.Ticker(t).history(start=quarter, period=None)["Close"].dropna()
        move = (price_now / float(h.iloc[0]) - 1) * 100
        lag["price_move_since_pct"] = round(move, 1)
        # Lag adjustment: a +/-15% move since quarter-end makes the filing stale; pull halfway to neutral
        if abs(move) >= 15:
            pts = round((pts + 15) / 2)
            lag["note"] = "STALE: price moved >=15% since quarter-end, score pulled toward neutral"
        else:
            lag["note"] = "valid: price within 15% of quarter-end"
    except Exception:
        lag["note"] = "lag check failed"
    return {"pts": pts, "status": "OK", "signal": sig, "tier1_adds": adds, "tier1_trims": trims,
            "lag": lag, "holders": holders}


# ── 2. dark pool (20) ───────────────────────────────────────────────────────

def finra_weekly(t, code, start):
    body = {"limit": 60, "fields": ["weekStartDate", "totalWeeklyShareQuantity"],
            "compareFilters": [{"compareType": "equal", "fieldName": "issueSymbolIdentifier", "fieldValue": t},
                               {"compareType": "equal", "fieldName": "summaryTypeCode", "fieldValue": code}],
            "dateRangeFilters": [{"fieldName": "weekStartDate", "startDate": start,
                                  "endDate": date.today().isoformat()}]}
    r = requests.post(FINRA_URL, json=body, headers={"Accept": "application/json"}, timeout=20)
    r.raise_for_status()
    out = {}
    for row in r.json() if r.text.strip() else []:
        out[row["weekStartDate"]] = out.get(row["weekStartDate"], 0) + float(row["totalWeeklyShareQuantity"])
    return out


def score_darkpool(t):
    if not is_us(t):
        return {"pts": None, "status": "UNAVAILABLE", "signal": "DATA UNAVAILABLE",
                "detail": "FINRA OTC transparency covers US NMS stocks only"}
    start = (date.today() - timedelta(days=56)).isoformat()
    ats, otc = finra_weekly(t, "ATS_W_SMBL", start), finra_weekly(t, "OTC_W_SMBL", start)
    weeks = sorted(set(ats) & set(otc))[-3:]  # last 3 weeks published in both datasets
    if len(weeks) < 2:
        return {"pts": None, "status": "UNAVAILABLE", "signal": "DATA UNAVAILABLE", "detail": "FINRA weeks missing"}
    h = yf.Ticker(t).history(start=weeks[0], end=(date.fromisoformat(weeks[-1]) + timedelta(days=7)).isoformat())
    h.index = h.index.tz_localize(None).normalize()
    rows = []
    for w in weeks:
        ws = date.fromisoformat(w)
        wk = h[(h.index.date >= ws) & (h.index.date < ws + timedelta(days=7))]
        vol = float(wk["Volume"].sum())
        if vol:
            rows.append({"week": w, "off_exchange_pct": round((ats[w] + otc[w]) / vol * 100, 1),
                         "ats_pct": round(ats[w] / vol * 100, 1)})
    if len(rows) < 2:
        return {"pts": None, "status": "UNAVAILABLE", "signal": "DATA UNAVAILABLE", "detail": "no matching volume"}
    trend = (float(h["Close"].iloc[-1]) / float(h["Open"].iloc[0]) - 1) * 100
    elevated = sum(r["off_exchange_pct"] > 45 for r in rows)
    avg = sum(r["off_exchange_pct"] for r in rows) / len(rows)
    # Inviolable rule: no single-week spike — need >=2 elevated weeks before calling direction
    if elevated >= 2 and trend > 2:
        pts, sig = 20, "ACCUMULATION"
    elif elevated >= 2 and trend < -2:
        pts, sig = 0, "DISTRIBUTION"
    elif elevated >= 2:
        pts, sig = 10, "POSITIONING (direction unclear)"
    else:
        pts, sig = 10, "BELOW NORMAL" if avg < 30 else "NORMAL"
    return {"pts": pts, "status": "OK", "signal": sig, "avg_off_exchange_pct": round(avg, 1),
            "price_trend_pct": round(trend, 1), "weeks": rows,
            "detail": f"FINRA ATS+non-ATS, latest published week {rows[-1]['week']}"}


# ── 3. options flow (20) ────────────────────────────────────────────────────

def score_options(t, price_now):
    tk = yf.Ticker(t)
    exps = [e for e in (tk.options or ()) if date.fromisoformat(e) <= date.today() + timedelta(days=45)][:3]
    if not exps:
        return {"pts": None, "status": "UNAVAILABLE", "signal": "DATA UNAVAILABLE", "detail": "no listed options <=45 DTE"}
    cv = pv = 0.0
    unusual = []
    for e in exps:
        ch = tk.option_chain(e)
        for kind, df in (("CALL", ch.calls), ("PUT", ch.puts)):
            df = df.fillna(0)
            if kind == "CALL":
                cv += df["volume"].sum()
            else:
                pv += df["volume"].sum()
            otm = df[df["strike"] > price_now] if kind == "CALL" else df[df["strike"] < price_now]
            hot = otm[(otm["volume"] >= 500) & (otm["volume"] > otm["openInterest"])]
            for _, r in hot.iterrows():
                unusual.append({"type": kind, "expiry": e, "strike": float(r["strike"]),
                                "volume": int(r["volume"]), "open_interest": int(r["openInterest"])})
    pc = pv / cv if cv else None
    uc = sum(u["type"] == "CALL" for u in unusual)
    up = sum(u["type"] == "PUT" for u in unusual)
    if uc and not up and pc is not None and pc < 0.77:
        pts, sig = 20, "BULLISH (unusual calls)"
    elif up and not uc and pc is not None and pc > 1.3:
        pts, sig = 0, "BEARISH / HEDGE (put build)"
    else:
        pts, sig = 10, "NEUTRAL"
    return {"pts": pts, "status": "OK", "signal": sig, "put_call_volume": round(pc, 2) if pc else None,
            "call_volume": int(cv), "put_volume": int(pv), "unusual": unusual[:8], "expiries": exps}


# ── 4. ETF sector flow proxy (10) ───────────────────────────────────────────

def score_sector(t, sector, rot):
    if rot is None or not sector:
        return {"pts": 5, "status": "UNAVAILABLE", "signal": "NEUTRAL", "detail": "no sector or sector_rotation.json"}
    us = is_us(t)
    etf = (US_SECTOR_ETF if us else EU_SECTOR_ETF).get(sector)
    group = rot.get("us_sectors" if us else "eu_sectors", {})
    bench = rot["benchmarks"].get("SPY" if us else "EXSA.DE", {})
    if not etf or etf not in group or "ret_1m" not in bench:
        return {"pts": 5, "status": "UNAVAILABLE", "signal": "NEUTRAL", "detail": f"no ETF mapped for {sector}"}
    rel = group[etf]["ret_1m"] - bench["ret_1m"]
    pts, sig = (10, "TAILWIND") if rel > 2 else (0, "HEADWIND") if rel < -2 else (5, "NEUTRAL")
    return {"pts": pts, "status": "PROXY", "signal": sig, "etf": etf, "rel_1m_pct": round(rel, 2),
            "detail": f"{etf} 1m return vs {'SPY' if us else 'Stoxx 600'} (relative strength, not flows)"}


# ── 5. dry powder (10) ──────────────────────────────────────────────────────

def score_dry_powder(m):
    if not m or (date.today() - date.fromisoformat(m.get("as_of", "1900-01-01"))).days > 45:
        return {"pts": 5, "status": "UNAVAILABLE", "signal": "NORMAL (assumed)",
                "detail": f"fill {MARKET_PATH}: {{as_of, fms_cash_pct, hf_net_leverage_pct}}"}
    cash, lev = m.get("fms_cash_pct"), m.get("hf_net_leverage_pct")
    if (cash is not None and cash > 5) or (lev is not None and lev < 40):
        pts, sig = 10, "DRY POWDER AVAILABLE"
    elif cash is not None and cash < 4 and lev is not None and lev > 60:
        pts, sig = 0, "CROWDED"
    else:
        pts, sig = 5, "NORMAL"
    return {"pts": pts, "status": "OK", "signal": sig, "detail": f"as of {m['as_of']}: FMS cash {cash}%, HF net lev {lev}%"}


# ── aggregate ───────────────────────────────────────────────────────────────

def safe(fn, *a):
    try:
        return fn(*a)
    except Exception as e:
        return {"pts": None, "status": "UNAVAILABLE", "signal": "DATA UNAVAILABLE", "detail": f"error: {e}"}


def score_ticker(t, rot, market):
    tk = yf.Ticker(t)
    try:
        price = float(tk.history(period="5d")["Close"].dropna().iloc[-1])
    except Exception:
        price = None
    try:
        sector = tk.info.get("sector")
    except Exception:
        sector = None
    c = {
        "13f": safe(score_13f, t, price) if price else {"pts": None, "status": "UNAVAILABLE", "signal": "DATA UNAVAILABLE"},
        "dark_pool": safe(score_darkpool, t),
        "options": safe(score_options, t, price) if price else {"pts": None, "status": "UNAVAILABLE", "signal": "DATA UNAVAILABLE"},
        "etf_sector": score_sector(t, sector, rot),
        "dry_powder": score_dry_powder(market),
    }
    # Options in liquid names are mostly market-making: a directional options read counts
    # only when 13F or dark pool points the same way (institutional-flow.md inviolable rule)
    o = c["options"]
    if o["pts"] in (0, 20):
        bull = o["pts"] == 20
        agrees = (c["13f"].get("signal", "").startswith("ACCUMULATING") or c["dark_pool"].get("signal") == "ACCUMULATION") if bull \
            else (c["13f"].get("signal") in ("DISTRIBUTING", "MIXED (net trims)") or c["dark_pool"].get("signal") == "DISTRIBUTION")
        if not agrees:
            o["raw_signal"], o["pts"], o["signal"] = o["signal"], 10, "NEUTRAL (uncorroborated)"
    core = [c[k] for k in ("13f", "dark_pool", "options")]
    if all(x["pts"] is None for x in core):
        score, note = 50, "DATA UNAVAILABLE on 13F, dark pool and options — agent fallback score"
    else:
        neutral = {"13f": 15, "dark_pool": 10, "options": 10}  # missing core component counts as neutral
        score = sum(c[k]["pts"] if c[k]["pts"] is not None else neutral[k] for k in neutral)
        score += c["etf_sector"]["pts"] + c["dry_powder"]["pts"]
        missing = [k for k in neutral if c[k]["pts"] is None]
        note = f"neutral fill for missing: {', '.join(missing)}" if missing else "all core sources live"
    align = "ALIGNED" if score >= 70 else "CAUTIOUS" if score >= 40 else "CONTRARIAN WARNING"
    return {"ticker": t, "score": score, "alignment": align, "sector": sector, "price": price,
            "note": note, "components": c}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="+")
    ap.add_argument("--json", action="store_true", help="print each ticker's full JSON block")
    a = ap.parse_args()
    try:
        rot = json.load(open(SECTOR_PATH))
    except (OSError, ValueError):
        rot = None
    try:
        market = json.load(open(MARKET_PATH))
    except (OSError, ValueError):
        market = None
    tickers = list(dict.fromkeys(t.upper() for arg in a.tickers for t in re.split(r"[\s,]+", arg) if t))
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(lambda t: score_ticker(t, rot, market), tickers))

    try:
        out = json.load(open(OUT_PATH))
    except (OSError, ValueError):
        out = {"tickers": {}}
    out["generated"] = datetime.now().isoformat(timespec="seconds")
    for r in res:
        r["as_of"] = out["generated"]
        out["tickers"][r["ticker"]] = r
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=1, default=str)
        f.write("\n")

    print(f"\n  {'Ticker':<9}{'Score':>6}  {'Alignment':<19}{'13F':<24}{'Dark pool':<26}{'Options':<26}{'Sector (proxy)':<16}")
    for r in res:
        c = r["components"]
        cell = lambda k: (f"{c[k]['pts']} " if c[k]["pts"] is not None else "– ") + c[k]["signal"][:21]
        print(f"  {r['ticker']:<9}{r['score']:>6}  {r['alignment']:<19}{cell('13f'):<24}{cell('dark_pool'):<26}"
              f"{cell('options'):<26}{cell('etf_sector'):<16}")
        if a.json:
            print(json.dumps(r, indent=1, default=str))
    print(f"\n  Dry powder: {res[0]['components']['dry_powder']['detail'] if res else ''}")
    print(f"  Written to {OUT_PATH}\n")


if __name__ == "__main__":
    sys.exit(main())
