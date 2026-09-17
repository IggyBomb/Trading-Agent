
#!/usr/bin/env python3
"""
alt_data.py — Alternative Data Fetcher
Fetches and scores:
  1. Short interest (% float, days-to-cover, month-over-month change)
  2. Insider transactions (Form 4 via yfinance, open-market only) + Finnhub MSPR sentiment modifier
  3. Analyst recommendation trend (Finnhub — buy/hold/sell shift month over month)
  4. News NLP sentiment (yfinance headlines, Finnhub company-news fallback + VADER)

Congressional trading (Quiver) is fetched and stored for reference but no longer scored —
both Quiver and Finnhub gate congressional data behind paid plans now. Revisit if a free
source (e.g. Financial Modeling Prep) gets wired in.

Reads:  ./data/market_data.json  (High/Medium conviction tickers from fetch_data.py)
Writes: ./data/alt_data.json

Run after fetch_data.py:
  python3 fetch_data.py
  python3 alt_data.py

API keys (both optional — skipped gracefully if missing), set in .env or env vars:
  FINNHUB_API_KEY=...   # free signup at finnhub.io — powers analyst trend + insider MSPR
  QUIVER_API_KEY=...    # free signup at quiverquant.com — congressional data (reference only)
"""

import json, os, sys, time
from pydantic import ValidationError
from schemas import AltDataRecord
import logging
from datetime import datetime, timezone, timedelta

log = logging.getLogger("alt_data")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    os.system(f"{sys.executable} -m pip install python-dotenv --quiet")
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

try:
    import yfinance as yf
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests --quiet")
    import requests

try:
    import pandas as pd
except ImportError:
    os.system(f"{sys.executable} -m pip install pandas --quiet")
    import pandas as pd

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = True
except ImportError:
    os.system(f"{sys.executable} -m pip install vaderSentiment --quiet")
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _VADER = True
    except ImportError:
        _VADER = False


# ── Config ────────────────────────────────────────────────────────────────────

from config import CONVICTION_FILTER, MARKET_DATA_PATH, ALT_DATA_PATH

OUTPUT_PATH       = ALT_DATA_PATH
REQUEST_PAUSE     = 0.5
INSIDER_DAYS      = 60
CONGRESS_DAYS     = 60
NEWS_DAYS         = 5

QUIVER_API_KEY = os.environ.get("QUIVER_API_KEY", "")
QUIVER_BASE    = "https://api.quiverquant.com/beta"

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
FINNHUB_BASE    = "https://finnhub.io/api/v1"
ANALYST_MONTHS  = 2   # compare latest vs prior month of recommendation trend


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(x, default=None):
    try:
        v = float(x)
        return default if v != v else v  # NaN guard
    except (TypeError, ValueError):
        return default

def _days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).date()


# Counts 403s so main() can report the plan wall once instead of ~3x per
# blocked ticker. The free Finnhub plan is US-only, so every non-US symbol
# returns 403 on every endpoint — logging each one would bury the real errors.
_FINNHUB_403 = {"count": 0, "symbols": set(), "paths": set()}


def _finnhub_get(path, params):
    symbol = params.get("symbol", "?")
    params = {**params, "token": FINNHUB_API_KEY}
    try:
        r = requests.get(f"{FINNHUB_BASE}/{path}", params=params, timeout=10)
    except Exception as e:
        # never log the URL — it carries the API key
        log.warning(f"finnhub {path} [{symbol}] request failed: {e}")
        raise
    if r.status_code == 403:
        _FINNHUB_403["count"] += 1
        _FINNHUB_403["symbols"].add(symbol)
        _FINNHUB_403["paths"].add(path)
        log.debug(f"finnhub {path} [{symbol}]: 403 — not available on this plan")
        return None  # endpoint not available on this plan
    if r.status_code == 429:
        log.warning(f"finnhub {path} [{symbol}]: 429 rate limited — consider raising REQUEST_PAUSE")
    r.raise_for_status()
    return r.json()


# ── 1. Short Interest ─────────────────────────────────────────────────────────

def fetch_short_interest(info):
    try:
        pct   = _safe(info.get("shortPercentOfFloat"))
        dtc   = _safe(info.get("shortRatio"))
        cur   = _safe(info.get("sharesShort"), 0)
        prior = _safe(info.get("sharesShortPriorMonth"), 0)

        pct_display = round(pct * 100, 2) if pct is not None else None
        mom = round((cur - prior) / prior * 100, 1) if (prior and prior > 0) else None

        if pct_display is None:
            sig, squeeze = "UNKNOWN", False
        elif pct_display < 5:
            sig, squeeze = "LOW", False
        elif pct_display < 10:
            sig, squeeze = "MODERATE", False
        elif pct_display < 20:
            sig, squeeze = "HIGH", bool(dtc and dtc > 5)
        else:
            sig, squeeze = "EXTREME", True

        return {
            "short_pct_float": pct_display,
            "days_to_cover":   round(dtc, 1) if dtc else None,
            "mom_change_pct":  mom,
            "signal":          sig,
            "squeeze_watch":   squeeze,
            "interpretation":  _interp_short(pct_display, dtc, mom, squeeze),
        }
    except Exception as e:
        log.warning(f"short interest parse failed: {e}", exc_info=True)
        return {"signal": "ERROR", "squeeze_watch": False, "interpretation": str(e)}


def _interp_short(pct, dtc, mom, squeeze):
    if pct is None:
        return "Short interest data unavailable"
    if pct < 3:
        base = f"Very low short interest ({pct}%) — no bearish headwind"
    elif pct < 5:
        base = f"Low short interest ({pct}%) — benign"
    elif pct < 10:
        base = f"Moderate short interest ({pct}%) — some bearish conviction"
    elif pct < 20:
        base = f"High short interest ({pct}%)" + (f" | DTC {dtc}d — squeeze risk elevated" if squeeze else "")
    else:
        base = f"Extreme short interest ({pct}%) — major bearish bet, squeeze candidate on catalyst"
    if mom is not None:
        if mom > 10:
            base += f" | Short interest +{mom}% MoM — bearish conviction growing"
        elif mom < -10:
            base += f" | Short covering {mom}% MoM — bullish signal"
    return base


# ── 2. Insider Transactions ───────────────────────────────────────────────────

PURCHASE_KW = {"purchase", "buy", "bought", "acquisition"}
SALE_KW     = {"sale", "sell", "sold", "disposition"}
EXCLUDE_KW  = {"automatic", "exercise", "grant", "gift", "transfer", "award", "conversion"}


def _classify_text(text):
    t = text.lower()
    if any(kw in t for kw in EXCLUDE_KW):
        return None
    if any(kw in t for kw in PURCHASE_KW):
        return "BUY"
    if any(kw in t for kw in SALE_KW):
        return "SELL"
    return None


# ── 2a. Insider impact model ──────────────────────────────────────────────────
# Buyer-count alone was misleading the score: 2 insiders buying €10 each
# outranked 1 insider buying €10M (see conversation). This replaces that with
# a relative-impact model — how much of the daily volume/float the buy
# actually moves, filtered by market cap relevance — per the framework:
#   1. Volume:   trade size vs ADV — <5% no market impact, ≥15% can't pass unnoticed
#   2. Float:    low-float (<20M shares) + ≥0.5% of float bought = scarcity shock;
#                high-float (>300M shares) = drop in the ocean regardless of %
#   3. Mkt cap:  <$2B = insider buy is the strongest signal available (info vacuum);
#                >$100B = even a large $ buy is noise against the total cap
#
# RAW(yfinance): averageVolume/floatShares/marketCap all come from the same
# .info dict already fetched once per ticker in main() (line ~669) — no extra
# API calls. shares_col below (insider_transactions "Shares" column) has NOT
# been confirmed live in this environment — verify with:
#   yf.Ticker('AAPL').insider_transactions.columns

ADV_HIGH_PCT        = 0.15     # trade shares / avg daily volume
ADV_MODERATE_PCT    = 0.05

FLOAT_LOW_SHARES    = 20_000_000
FLOAT_MID_SHARES    = 300_000_000
FLOAT_HIGH_PCT      = 0.005    # 0.5% of float bought
FLOAT_MODERATE_PCT  = 0.002   # 0.2% of float bought
FLOAT_LOW_PCT       = 0.001  # 0.1% of float bought

MCAP_MICRO_SMALL    = 100_000_000
MCAP_MEDIUM         = 5_000_000_000
MCAP_LARGE_MEGA     = 150_000_000_000


def _volume_impact(shares_bought, avg_volume):
    """Trade size vs average daily volume. Returns (band, pct-or-None)."""
    if not avg_volume or avg_volume <= 0 or not shares_bought:
        return "UNKNOWN", None
    pct = shares_bought / avg_volume
    if pct >= ADV_HIGH_PCT:
        band = "HIGH"
    elif pct >= ADV_MODERATE_PCT:
        band = "MODERATE"
    else:
        band = "LOW"
    return band, round(pct * 100, 2)


def _float_impact(shares_bought, float_shares):
    """Scarcity shock potential. High-float stocks stay MINIMAL regardless of
    % bought — the buy is a drop in the ocean no matter the dollar size.
    Three floor levels below HIGH: MODERATE (>=0.2%), LOW (>=0.1% — the
    minimum to register any impact at all), MINIMAL (<0.1%, or high-float)."""
    if not float_shares or float_shares <= 0 or not shares_bought:
        return "UNKNOWN", None, "UNKNOWN"

    if float_shares < FLOAT_LOW_SHARES:
        size_tier = "LOW_FLOAT"
    elif float_shares < FLOAT_MID_SHARES:
        size_tier = "MID_FLOAT"
    else:
        size_tier = "HIGH_FLOAT"

    pct = shares_bought / float_shares
    if size_tier == "HIGH_FLOAT":
        band = "MINIMAL"
    elif pct >= FLOAT_HIGH_PCT:
        band = "HIGH"
    elif pct >= FLOAT_MODERATE_PCT:
        band = "MODERATE"
    elif pct >= FLOAT_LOW_PCT:
        band = "LOW"
    else:
        band = "MINIMAL"
    return band, round(pct * 100, 4), size_tier


def _market_cap_tier(market_cap):
    """Four tiers now: MICRO_SMALL (<$100M) gets the strongest relevance
    boost (pure info vacuum), SMALL ($100M-$5B) a smaller boost, MEDIUM
    ($5B-$150B) neutral, LARGE_MEGA (>$150B) dampened — a $ amount that
    moves a micro cap is noise against a $150B+ company."""
    if not market_cap or market_cap <= 0:
        return "UNKNOWN"
    if market_cap < MCAP_MICRO_SMALL:
        return "MICRO_SMALL"
    if market_cap < MCAP_MEDIUM:
        return "SMALL"
    if market_cap < MCAP_LARGE_MEGA:
        return "MEDIUM"
    return "LARGE_MEGA"


def _impact_signal(volume_band, float_band, mcap_tier, u_buyers):
    """Combines the three dimensions above into one label — this is what
    drives the insider score now, buyer count is a secondary +0/+1/+2 nudge
    rather than the primary axis it used to be. Max points unchanged (10),
    so the MAJOR/SIGNIFICANT/MINOR/NEGLIGIBLE cutoffs below still apply."""
    pts = 0
    pts += {"HIGH": 3, "MODERATE": 1}.get(volume_band, 0)
    pts += {"HIGH": 3, "MODERATE": 2, "LOW": 1}.get(float_band, 0)
    pts += {"MICRO_SMALL": 2, "SMALL": 1, "MEDIUM": 0, "LARGE_MEGA": -2}.get(mcap_tier, 0)
    pts += 2 if u_buyers >= 3 else (1 if u_buyers == 2 else 0)

    if pts >= 7:
        label = "MAJOR_IMPACT"
    elif pts >= 4:
        label = "SIGNIFICANT_IMPACT"
    elif pts >= 1:
        label = "MINOR_IMPACT"
    else:
        label = "NEGLIGIBLE"
    return label, pts


def fetch_insider(ticker, info=None):
    info = info or {}
    try:
        df = yf.Ticker(ticker).insider_transactions
        if df is None or (hasattr(df, "empty") and df.empty):
            return _no_insider()

        df.columns = [str(c).strip() for c in df.columns]

        date_col   = next((c for c in df.columns if any(k in c.lower() for k in ["date", "start"])), None)
        text_col   = next((c for c in df.columns if any(k in c.lower() for k in ["text", "type", "transaction"])), None)
        name_col   = next((c for c in df.columns if any(k in c.lower() for k in ["insider", "name", "person"])), None)
        value_col  = next((c for c in df.columns if "value" in c.lower()), None)
        shares_col = next((c for c in df.columns if "share" in c.lower()), None)

        if date_col is None:
            return _no_insider()

        df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=True)
        df = df.dropna(subset=[date_col])
        cutoff = pd.Timestamp(_days_ago(INSIDER_DAYS), tz="UTC")
        recent = df[df[date_col] >= cutoff]

        if recent.empty:
            return {**_no_insider(), "interpretation": f"No insider transactions in last {INSIDER_DAYS} days"}

        buys, sells = [], []
        for _, row in recent.iterrows():
            text   = str(row[text_col]) if text_col else ""
            name   = str(row[name_col]) if name_col else "Unknown"
            value  = abs(_safe(row[value_col], 0) if value_col else 0)
            shares = abs(_safe(row[shares_col], 0) if shares_col else 0)
            action = _classify_text(text)
            if action == "BUY":
                buys.append({"name": name, "value": value, "shares": shares})
            elif action == "SELL":
                sells.append({"name": name, "value": value, "shares": shares})

        u_buyers      = len({b["name"] for b in buys})
        u_sellers     = len({s["name"] for s in sells})
        bought        = sum(b["value"] for b in buys)
        sold          = sum(s["value"] for s in sells)
        shares_bought = sum(b["shares"] for b in buys)

        # Buyer-count label — kept for context/display, no longer drives the score.
        if u_buyers >= 3:            sig = "STRONG_CLUSTER"
        elif u_buyers == 2:          sig = "CLUSTER"
        elif u_buyers == 1 and bought >= 100_000: sig = "SINGLE_BUY_SIGNIFICANT"
        elif u_buyers >= 1:          sig = "SINGLE_BUY"
        elif u_sellers >= 2:         sig = "SELLING"
        else:                        sig = "NONE"

        # Impact model — see _impact_signal() above. This is the new primary
        # driver of the insider score in score_and_signal().
        volume_band, volume_pct           = _volume_impact(shares_bought, _safe(info.get("averageVolume")))
        float_band, float_pct, float_tier = _float_impact(shares_bought, _safe(info.get("floatShares")))
        mcap_tier                         = _market_cap_tier(_safe(info.get("marketCap")))
        impact_signal, impact_pts         = _impact_signal(volume_band, float_band, mcap_tier, u_buyers)

        if bought > sold * 1.5:      net = "BUY"
        elif sold > bought * 1.5:    net = "SELL"
        elif bought > 0 and sold > 0: net = "MIXED"
        elif bought > 0:             net = "BUY"
        elif sold > 0:               net = "SELL"
        else:                        net = "NONE"

        notable = [f"{b['name']}: +${b['value']:,.0f}"
                   for b in sorted(buys, key=lambda x: x["value"], reverse=True)[:3]
                   if b["value"] > 0]

        return {
            "cluster_signal":     sig,
            "impact_signal":      impact_signal,
            "impact_points":      impact_pts,
            "volume_impact":      volume_band,
            "pct_of_avg_volume":  volume_pct,
            "float_impact":       float_band,
            "pct_of_float":       float_pct,
            "float_tier":         float_tier,
            "market_cap_tier":    mcap_tier,
            "net_activity":       net,
            "buyers_30d":         u_buyers,
            "sellers_30d":        u_sellers,
            "shares_bought_30d":  round(shares_bought),
            "total_value_bought": round(bought),
            "total_value_sold":   round(sold),
            "notable":            notable,
            "interpretation":     _interp_insider(sig, u_buyers, bought, sold, impact_signal),
        }
    except Exception as e:
        log.warning(f"{ticker}: insider fetch failed: {e}", exc_info=True)
        return {**_no_insider(), "cluster_signal": "ERROR", "impact_signal": "ERROR",
                "interpretation": f"Insider error: {e}"}



def _no_insider():
    return {
        "cluster_signal": "NONE", "impact_signal": "NEGLIGIBLE", "impact_points": 0,
        "volume_impact": "UNKNOWN", "pct_of_avg_volume": None,
        "float_impact": "UNKNOWN", "pct_of_float": None, "float_tier": "UNKNOWN",
        "market_cap_tier": "UNKNOWN",
        "net_activity": "NONE",
        "buyers_30d": 0, "sellers_30d": 0, "shares_bought_30d": 0,
        "total_value_bought": 0, "total_value_sold": 0,
        "notable": [], "interpretation": "No insider data available",
    }


# ── 2b. Insider Sentiment (Finnhub MSPR) ──────────────────────────────────────

def fetch_insider_sentiment(ticker):
    """Finnhub's Monthly Share Purchase Ratio — smoothed institutional-grade insider
    sentiment, distinct from the raw Form 4 cluster detection above."""
    if not FINNHUB_API_KEY:
        return {"status": "NO_API_KEY", "avg_mspr": None, "trend": "UNKNOWN"}
    try:
        data = _finnhub_get("stock/insider-sentiment", {
            "symbol": ticker,
            "from": str(_days_ago(180)),
            "to": str(_days_ago(0)),
        })
        if not data:
            return {"status": "UNAVAILABLE", "avg_mspr": None, "trend": "UNKNOWN"}
        rows = sorted(data.get("data", []), key=lambda r: (r.get("year", 0), r.get("month", 0)))
        if not rows:
            return {"status": "NO_DATA", "avg_mspr": None, "trend": "UNKNOWN"}

        recent = rows[-3:]
        avg = round(sum(r.get("mspr", 0) for r in recent) / len(recent), 1)

        if avg > 15:    trend = "BULLISH"
        elif avg < -15: trend = "BEARISH"
        else:           trend = "NEUTRAL"

        return {"status": "OK", "avg_mspr": avg, "trend": trend,
                "months_used": len(recent)}
    except Exception as e:
        log.warning(f"{ticker}: insider sentiment (MSPR) failed: {e}", exc_info=True)
        return {"status": "ERROR", "avg_mspr": None, "trend": "UNKNOWN", "error": str(e)}


def _interp_insider(sig, buyers, bought, sold, impact=None):
    if sig == "SELLING":
        return f"Insider selling ${sold:,.0f} net — insiders know their own business best"
    if bought <= 0:
        return "No meaningful insider activity in last 30 days"

    buyer_note = f"{buyers} insider{'s' if buyers != 1 else ''} bought ${bought:,.0f} in last 30d"
    if impact == "MAJOR_IMPACT":
        return f"{buyer_note} — major impact (large vs volume/float, and/or small-cap relevance): one of the highest-conviction signals available"
    if impact == "SIGNIFICANT_IMPACT":
        return f"{buyer_note} — significant impact relative to volume/float/market cap"
    if impact == "MINOR_IMPACT":
        return f"{buyer_note} — some impact, but modest relative to volume/float/market cap"
    if impact == "NEGLIGIBLE":
        return f"{buyer_note} — negligible relative to volume/float/market cap (e.g. a small buy on a large, liquid, high-float name)"
    return buyer_note  # impact unknown (missing volume/float/mcap data)


# ── 3. Congressional Trading ──────────────────────────────────────────────────

def fetch_congressional(ticker):
    if not QUIVER_API_KEY:
        return {
            "status": "NO_API_KEY", "net_direction": "UNKNOWN",
            "notable": [], "recent_trades": [],
            "interpretation": "Set QUIVER_API_KEY env var for congressional data (free at quiverquant.com)",
        }
    try:
        r = requests.get(
            f"{QUIVER_BASE}/historical/congresstrading/{ticker}",
            headers={"Accept": "application/json", "Authorization": f"Token {QUIVER_API_KEY}"},
            timeout=10,
        )
        if r.status_code == 404:
            return {"status": "NO_DATA", "net_direction": "NONE", "notable": [], "recent_trades": [],
                    "interpretation": "No congressional trades on record for this ticker"}
        r.raise_for_status()
        trades = r.json() or []

        cutoff = _days_ago(CONGRESS_DAYS)
        recent = []
        for t in trades:
            d_str = t.get("ReportDate") or t.get("Date", "")
            try:
                if datetime.strptime(d_str[:10], "%Y-%m-%d").date() >= cutoff:
                    recent.append({
                        "date":           d_str[:10],
                        "representative": t.get("Representative", "Unknown"),
                        "party":          t.get("Party", ""),
                        "transaction":    t.get("Transaction", ""),
                        "range":          t.get("Range", ""),
                    })
            except Exception:
                continue

        buys  = [x for x in recent if "purchase" in x["transaction"].lower()]
        sells = [x for x in recent if "sale" in x["transaction"].lower()]

        if len(buys) > len(sells):      net = "BUY"
        elif len(sells) > len(buys):    net = "SELL"
        elif recent:                    net = "MIXED"
        else:                           net = "NONE"

        notable = [f"{b['representative']} ({b['party']}): {b['transaction']} {b['range']} on {b['date']}"
                   for b in buys[:3]]

        return {
            "status": "OK", "net_direction": net,
            "buys_count": len(buys), "sells_count": len(sells),
            "recent_trades": recent[:10], "notable": notable,
            "interpretation": _interp_congress(net, buys, sells),
        }
    except Exception as e:
        log.warning(f"{ticker}: congressional fetch failed (reference only, unscored): {e}", exc_info=True)
        return {"status": "ERROR", "net_direction": "UNKNOWN", "notable": [], "recent_trades": [],
                "interpretation": f"Congressional data error: {e}"}


def _interp_congress(direction, buys, sells):
    if direction == "BUY":
        reps = list({b["representative"] for b in buys})
        return f"Congressional buying: {', '.join(reps[:3])} — statistically significant alpha signal"
    if direction == "SELL":
        reps = list({s["representative"] for s in sells})
        return f"Congressional selling: {', '.join(reps[:3])} — mild caution"
    if direction == "MIXED":
        return "Mixed congressional activity — no directional signal"
    return f"No congressional trades in last {CONGRESS_DAYS} days"


# ── 3b. Analyst Recommendation Trend (Finnhub) ────────────────────────────────

def fetch_analyst_trend(ticker):
    """Month-over-month shift in analyst buy/hold/sell distribution. Free Finnhub
    endpoint — fills the scoring slot vacated by Congressional Trading (now paid
    on both Quiver and Finnhub)."""
    if not FINNHUB_API_KEY:
        return {"status": "NO_API_KEY", "trend": "UNKNOWN",
                "interpretation": "Set FINNHUB_API_KEY env var for analyst trend data"}
    try:
        rows = _finnhub_get("stock/recommendation", {"symbol": ticker})
        if not rows:
            return {"status": "NO_DATA", "trend": "UNKNOWN", "interpretation": "No analyst coverage found"}

        rows = sorted(rows, key=lambda r: r.get("period", ""), reverse=True)[:ANALYST_MONTHS]
        if not rows:
            return {"status": "NO_DATA", "trend": "UNKNOWN", "interpretation": "No analyst coverage found"}

        def bull_ratio(r):
            total = r["strongBuy"] + r["buy"] + r["hold"] + r["sell"] + r["strongSell"]
            return (r["strongBuy"] + r["buy"]) / total if total else None

        latest = rows[0]
        latest_ratio = bull_ratio(latest)
        prior_ratio = bull_ratio(rows[1]) if len(rows) > 1 else None

        if latest_ratio is None:
            return {"status": "NO_DATA", "trend": "UNKNOWN", "interpretation": "No analyst coverage found"}

        delta = round((latest_ratio - prior_ratio) * 100, 1) if prior_ratio is not None else 0.0

        if delta > 5:    trend = "IMPROVING"
        elif delta < -5: trend = "DETERIORATING"
        else:            trend = "STABLE"

        return {
            "status": "OK", "trend": trend,
            "bull_ratio_pct": round(latest_ratio * 100, 1),
            "delta_pct": delta,
            "period": latest.get("period"),
            "strong_buy": latest["strongBuy"], "buy": latest["buy"], "hold": latest["hold"],
            "sell": latest["sell"], "strong_sell": latest["strongSell"],
            "interpretation": _interp_analyst(trend, latest_ratio, delta),
        }
    except Exception as e:
        log.warning(f"{ticker}: analyst trend failed: {e}", exc_info=True)
        return {"status": "ERROR", "trend": "UNKNOWN", "interpretation": f"Analyst trend error: {e}"}


def _interp_analyst(trend, ratio, delta):
    pct = round(ratio * 100, 1)
    if trend == "IMPROVING":
        return f"Analyst sentiment improving: {pct}% buy-rated, +{delta}pp vs prior month — upgrades outpacing downgrades"
    if trend == "DETERIORATING":
        return f"Analyst sentiment deteriorating: {pct}% buy-rated, {delta}pp vs prior month — downgrade pressure"
    return f"Analyst sentiment stable: {pct}% buy-rated, little change vs prior month"


# ── 4. News NLP Sentiment ─────────────────────────────────────────────────────

def fetch_news_sentiment(ticker):
    if not _VADER:
        return {"status": "VADER_UNAVAILABLE", "sentiment_label": "UNKNOWN",
                "interpretation": "VADER not available"}
    try:
        analyzer = SentimentIntensityAnalyzer()
        news = _normalize_yf_news(yf.Ticker(ticker).news or [])

        if not news and FINNHUB_API_KEY:
            news = _fetch_finnhub_news_fallback(ticker)

        cutoff_ts = time.time() - NEWS_DAYS * 86400
        recent = [n for n in news if n.get("providerPublishTime", 0) >= cutoff_ts] or news[:5]

        scores = []
        for article in recent:
            text = f"{article.get('title', '')}. {article.get('summary', '')}".strip(" .")
            if text:
                scores.append(analyzer.polarity_scores(text)["compound"])

        if not scores:
            return {"status": "NO_NEWS", "sentiment_score": None, "sentiment_label": "UNKNOWN",
                    "velocity": "UNKNOWN", "article_count": 0, "interpretation": "No scoreable news"}

        avg = round(sum(scores) / len(scores), 3)

        if len(scores) >= 4:
            mid = len(scores) // 2
            delta = (sum(scores[:mid]) / mid) - (sum(scores[mid:]) / (len(scores) - mid))
            vel = "RISING" if delta > 0.05 else ("FALLING" if delta < -0.05 else "STABLE")
        else:
            vel = "STABLE"

        label = "POSITIVE" if avg >= 0.15 else ("NEGATIVE" if avg <= -0.15 else "NEUTRAL")

        return {
            "status": "OK", "sentiment_score": avg,
            "sentiment_label": label, "velocity": vel,
            "article_count": len(scores),
            "interpretation": _interp_news(avg, label, vel, len(scores)),
        }
    except Exception as e:
        log.warning(f"{ticker}: news sentiment failed: {e}", exc_info=True)
        return {"status": "ERROR", "sentiment_label": "UNKNOWN", "interpretation": str(e)}


def _normalize_yf_news(raw):
    """yfinance nests fields under 'content' with an ISO pubDate string as of mid-2026
    (used to be a flat dict with epoch providerPublishTime). Handle both shapes."""
    out = []
    for n in raw or []:
        c = n.get("content", n)
        pub = c.get("pubDate") or n.get("providerPublishTime") or 0
        if isinstance(pub, str):
            try:
                pub = datetime.fromisoformat(pub.replace("Z", "+00:00")).timestamp()
            except ValueError:
                pub = 0
        out.append({
            "title": c.get("title", ""),
            "summary": c.get("summary") or c.get("description", ""),
            "providerPublishTime": pub,
        })
    return out


def _fetch_finnhub_news_fallback(ticker):
    """Used when yfinance .news returns empty. Normalizes Finnhub's company-news
    shape to the {title, summary, providerPublishTime} fields fetch_news_sentiment expects."""
    try:
        rows = _finnhub_get("company-news", {
            "symbol": ticker, "from": str(_days_ago(NEWS_DAYS)), "to": str(_days_ago(0)),
        }) or []
        return [{
            "title": r.get("headline", ""),
            "summary": r.get("summary", ""),
            "providerPublishTime": r.get("datetime", 0),
        } for r in rows]
    except Exception:
        return []


def _interp_news(score, label, vel, count):
    desc = {
        ("POSITIVE", "RISING"):  f"News sentiment positive and strengthening ({score}) — narrative momentum building",
        ("POSITIVE", "STABLE"):  f"News sentiment positive ({score}) — benign backdrop",
        ("POSITIVE", "FALLING"): f"News sentiment positive but fading ({score}) — watch for shift",
        ("NEUTRAL",  "RISING"):  f"News sentiment improving toward positive ({score})",
        ("NEUTRAL",  "STABLE"):  f"News sentiment neutral ({score})",
        ("NEUTRAL",  "FALLING"): f"News sentiment neutral but drifting negative ({score})",
        ("NEGATIVE", "RISING"):  f"News sentiment negative but recovering ({score})",
        ("NEGATIVE", "STABLE"):  f"News sentiment negative ({score}) — some negative press",
        ("NEGATIVE", "FALLING"): f"News sentiment negative and deteriorating ({score}) — narrative headwind",
    }.get((label, vel), f"News sentiment {label.lower()} ({score})")
    return f"{desc} | {count} articles scored in last {NEWS_DAYS}d"


# ── Alt Data Score ────────────────────────────────────────────────────────────
# Riguarda questa parte, di come vengono calcolati i punteggi e i segnali basati sui dati raccolti. Attualmente una persona che ha comprato 500.000$ vale meno di 2 persone che hanno comprato 5000%.
# Inoltre non viene considerata la posizione di chi compra, cioe' se e' il CFO o una segretaria viene considerato uguale, mentre in realta' il CFO ha piu' informazioni e quindi il suo acquisto vale di piu'.
# questi dati possiamo trovarli in yfinance, quindi possiamo fare un punteggio piu' preciso.

def score_and_signal(insider, short_int, analyst, news, insider_sent):
    s = 0

    # Insider transactions (35 pts) — driven by impact_signal (trade size vs
    # volume/float, filtered by market cap relevance), not raw buyer count.
    # See _impact_signal(): a single large buy on a small, low-float name can
    # now outscore a "cluster" of trivial buys on a mega cap, correctly.
    cluster_sig = (insider or {}).get("cluster_signal", "NONE")
    if cluster_sig == "SELLING":
        s += 0
    elif cluster_sig == "ERROR":
        s += 9
    else:
        impact_sig = (insider or {}).get("impact_signal", "NEGLIGIBLE")
        s += {"MAJOR_IMPACT": 35, "SIGNIFICANT_IMPACT": 26,
              "MINOR_IMPACT": 16, "NEGLIGIBLE": 9}.get(impact_sig, 9)

    # Insider sentiment modifier (±5 pts) — Finnhub MSPR, confirms/conflicts with above
    mspr_trend = (insider_sent or {}).get("trend", "UNKNOWN")
    s += {"BULLISH": 5, "NEUTRAL": 2, "BEARISH": -5}.get(mspr_trend, 2)

    # Short interest (20 pts)
    si  = (short_int or {}).get("signal", "UNKNOWN")
    sq  = (short_int or {}).get("squeeze_watch", False)
    mom = (short_int or {}).get("mom_change_pct") or 0
    base_si = {"LOW": 20, "MODERATE": 12, "HIGH": 8, "EXTREME": 5, "UNKNOWN": 10}.get(si, 10)
    if sq and si in ("HIGH", "EXTREME"):
        base_si += 4  # squeeze potential is bonus upside, not penalty
    # Both gates mirror _interp_short()'s ±10 thresholds, so the written
    # interpretation and the score always agree. Previously the penalty fired
    # at 15 (leaving a warned-but-unpenalised gap) and there was no reward at
    # all for covering, even though the text called it a bullish signal.
    if mom > 10:
        base_si -= 3  # rising short interest is a mild headwind
    elif mom < -10:
        base_si += 3  # short covering — bears capitulating, the mirror case
    s += base_si

    # Analyst recommendation trend (20 pts) — replaces Congressional (now paid everywhere)
    atrend = (analyst or {}).get("trend", "UNKNOWN")
    s += {"IMPROVING": 20, "STABLE": 10, "DETERIORATING": 2, "UNKNOWN": 10}.get(atrend, 10)

    # News NLP (20 pts)
    nl  = (news or {}).get("sentiment_label", "UNKNOWN")
    nv  = (news or {}).get("velocity", "STABLE")
    news_pts = {
        ("POSITIVE", "RISING"): 20, ("POSITIVE", "STABLE"): 15, ("POSITIVE", "FALLING"): 12,
        ("NEUTRAL",  "RISING"): 12, ("NEUTRAL",  "STABLE"): 10, ("NEUTRAL",  "FALLING"): 7,
        ("NEGATIVE", "RISING"): 5,  ("NEGATIVE", "STABLE"): 4,  ("NEGATIVE", "FALLING"): 0,
    }.get((nl, nv), 10)
    s += news_pts

    s = round(min(max(s, 0), 100))
    sig_label = "BULLISH" if s >= 65 else ("NEUTRAL" if s >= 40 else "BEARISH")
    return s, sig_label


def build_flags(insider, short_int, analyst, news, insider_sent):
    flags = []
    ins    = (insider or {}).get("cluster_signal", "")
    impact = (insider or {}).get("impact_signal", "")
    if impact in ("MAJOR_IMPACT", "SIGNIFICANT_IMPACT"):
        flags.append("INSIDER_CLUSTER")
    if ins == "SELLING":
        flags.append("INSIDER_SELLING")
    if (short_int or {}).get("squeeze_watch"):
        flags.append("SQUEEZE_WATCH")
    if ((short_int or {}).get("mom_change_pct") or 0) > 15:
        flags.append("SHORT_RISING")
    if (insider_sent or {}).get("trend") == "BULLISH":
        flags.append("INSIDER_MSPR_BULLISH")
    if (insider_sent or {}).get("trend") == "BEARISH":
        flags.append("INSIDER_MSPR_BEARISH")
    if (analyst or {}).get("trend") == "IMPROVING":
        flags.append("ANALYST_UPGRADING")
    if (analyst or {}).get("trend") == "DETERIORATING":
        flags.append("ANALYST_DOWNGRADING")
    nl = (news or {}).get("sentiment_label")
    nv = (news or {}).get("velocity")
    if nl == "NEGATIVE" and nv == "FALLING":
        flags.append("NEWS_DETERIORATING")
    if nl == "POSITIVE" and nv == "RISING":
        flags.append("NEWS_ACCELERATING")
    return flags


# ── Print Summary ─────────────────────────────────────────────────────────────

def print_summary(results):
    W = 80
    print(f"\n{'='*W}")
    print(f"  ALT DATA SUMMARY — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*W}")
    hdr = f"  {'TICKER':<10} {'SCORE':>5}  {'SIGNAL':<9}  {'INSIDER IMPACT':<20}  {'SI%':>5}  {'FLAGS'}"
    print(hdr)
    print(f"  {'─'*10} {'─'*5}  {'─'*9}  {'─'*20}  {'─'*5}  {'─'*20}")

    for ticker, d in sorted(results.items(), key=lambda x: x[1]["alt_data_score"], reverse=True):
        ins = d.get("insider", {}).get("impact_signal", "—")
        si  = d.get("short_interest", {}).get("short_pct_float")
        si_s = f"{si}%" if si is not None else "—"
        flags = " | ".join(d.get("flags", [])) or "—"
        print(f"  {ticker:<10} {d['alt_data_score']:>5}  {d['alt_data_signal']:<9}  {ins:<20}  {si_s:>5}  {flags}")

    # Highlights
    clusters  = [t for t, d in results.items() if d.get("insider", {}).get("impact_signal") in ("MAJOR_IMPACT", "SIGNIFICANT_IMPACT")]
    squeezes  = [t for t, d in results.items() if d.get("short_interest", {}).get("squeeze_watch")]
    upgrades  = [t for t, d in results.items() if d.get("analyst_trend", {}).get("trend") == "IMPROVING"]
    downgrades = [t for t, d in results.items() if d.get("analyst_trend", {}).get("trend") == "DETERIORATING"]

    print(f"\n  Insider clusters  : {', '.join(clusters) or 'none'}")
    print(f"  Squeeze watches   : {', '.join(squeezes) or 'none'}")
    print(f"  Analyst upgrading : {', '.join(upgrades) or 'none (or FINNHUB_API_KEY not set)'}")
    print(f"  Analyst dngrading : {', '.join(downgrades) or 'none'}")
    print(f"{'='*W}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    
    os.makedirs("logs", exist_ok=True)
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # em-dashes on any Windows console
    except Exception:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/alt_data.log", mode="w", encoding="utf-8"),
        ],
    )
    log.info("=" * 60)
    log.info(f"Alt Data Agent — {datetime.now():%Y-%m-%d %H:%M}")
    log.info("=" * 60)
    log.info(f"Finnhub  : {'enabled (analyst trend + insider MSPR + news fallback)' if FINNHUB_API_KEY else 'DISABLED — set FINNHUB_API_KEY'}")
    log.info(f"Quiver   : {'enabled (reference only, not scored)' if QUIVER_API_KEY else 'DISABLED — set QUIVER_API_KEY'}")
    log.info(f"VADER NLP: {'enabled' if _VADER else 'DISABLED — news sentiment will be skipped'}")

    if not os.path.exists(MARKET_DATA_PATH):
        log.error(f"{MARKET_DATA_PATH} not found — run fetch_data.py first; aborting")
        sys.exit(1)

    with open(MARKET_DATA_PATH, encoding="utf-8") as f:
        market_data = json.load(f)

    candidates = [s["ticker"] for s in market_data["signals"] if s["conviction"] in CONVICTION_FILTER]
    log.info(f"{len(candidates)} High/Medium conviction tickers to process "
             f"(of {len(market_data['signals'])} signals)")

    results = {}
    total   = len(candidates)

    for i, ticker in enumerate(candidates, 1):
        # Single .info call reused for short interest
        info = {}
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception as e:
            log.warning(f"{ticker}: .info fetch failed — short interest will be UNKNOWN: {e}")
        if not info:
            log.debug(f"{ticker}: .info returned empty")
        time.sleep(REQUEST_PAUSE)

        short_int = fetch_short_interest(info)
        si_str    = f"{short_int.get('short_pct_float')}%" if short_int.get("short_pct_float") is not None else "?"

        insider = fetch_insider(ticker, info)
        print(f"ins={insider.get('impact_signal','?')[:16]:<18}", end=" ", flush=True)
        time.sleep(REQUEST_PAUSE)

        insider_sent = fetch_insider_sentiment(ticker)
        time.sleep(0.3)

        analyst = fetch_analyst_trend(ticker)
        time.sleep(0.3)

        congress = fetch_congressional(ticker)  # reference only, not scored
        time.sleep(0.3)

        news = fetch_news_sentiment(ticker)
        time.sleep(REQUEST_PAUSE)

        score, signal = score_and_signal(insider, short_int, analyst, news, insider_sent)
        flags = build_flags(insider, short_int, analyst, news, insider_sent)

        # One line per ticker: every signal's verdict plus the resulting score.
        # (Built as a single record rather than incremental prints so it lands
        # in the logfile as one parseable entry.)
        log.info(
            f"[{i:>4}/{total}] {ticker:<12} "
            f"SI={si_str:<7} "
            f"ins={insider.get('cluster_signal','?'):<22} "
            f"mspr={insider_sent.get('trend','?'):<8} "
            f"an={analyst.get('trend','?'):<14} "
            f"news={news.get('sentiment_label','?'):<8} "
            f"-> {score:>3} {signal}"
            + (f"  flags={','.join(flags)}" if flags else "")
        )

        results[ticker] = {
            "ticker":           ticker,
            "alt_data_score":   score,
            "alt_data_signal":  signal,
            "flags":            flags,
            "insider":          insider,
            "insider_sentiment": insider_sent,
            "short_interest":   short_int,
            "analyst_trend":    analyst,
            "congressional":    congress,
            "news_sentiment":   news,
        }
        
    # ── Schema validation — every record must match schemas.AltDataRecord ────
    # Valid records continue down the pipeline; invalid ones are quarantined
    # with the ticker name and which field(s) failed, and never reach the JSON.
    validated = {}
    rejected  = {}   # ticker -> "section.field: reason; ..."

    for ticker, record in results.items():
        try:
            AltDataRecord.model_validate(record)
            validated[ticker] = record
        except ValidationError as e:
            msg = "; ".join(f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors())
            rejected[ticker] = msg
            log.warning(f"{ticker}: schema rejected — {msg}")

    # Everything below reads `results`, so we overwrite it with the validated subset.
    results = validated
    log.info(f"schema validation — {len(validated)} passed, {len(rejected)} rejected")

    # ── Run summary — how much of each signal actually got data ─────────────
    def _missing(pred):
        return sum(1 for r in results.values() if pred(r))

    n = len(results) or 1
    coverage = {
        "insider":  _missing(lambda r: r["insider"]["cluster_signal"] in ("NONE", "ERROR")),
        "mspr":     _missing(lambda r: r["insider_sentiment"]["trend"] == "UNKNOWN"),
        "short":    _missing(lambda r: r["short_interest"]["signal"] == "UNKNOWN"),
        "analyst":  _missing(lambda r: r["analyst_trend"]["trend"] == "UNKNOWN"),
        "news":     _missing(lambda r: r["news_sentiment"].get("status") != "OK"),
    }
    signals = {}
    for r in results.values():
        signals[r["alt_data_signal"]] = signals.get(r["alt_data_signal"], 0) + 1

    log.info("=" * 60)
    log.info(f"scored {len(results)} tickers — "
             + " ".join(f"{k}:{v}" for k, v in sorted(signals.items())))
    log.info("signal coverage (missing / total):")
    for name, miss in coverage.items():
        log.info(f"  {name:<9} {miss:>4}/{len(results)}  ({miss*100//n}% missing)")

    if _FINNHUB_403["count"]:
        log.warning(
            f"Finnhub returned 403 on {_FINNHUB_403['count']} calls covering "
            f"{len(_FINNHUB_403['symbols'])} symbols and endpoints "
            f"{sorted(_FINNHUB_403['paths'])} — the free plan is US-only, so "
            f"non-US tickers score without MSPR and analyst trend"
        )
    log.info("=" * 60)

    # Human-facing table — stays print, same convention as the other agents
    print_summary(results)

    output = {
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "total_tickers":   len(results),
        "finnhub_enabled": bool(FINNHUB_API_KEY),
        "quiver_enabled":  bool(QUIVER_API_KEY),
        "vader_enabled":   _VADER,
        "schema_rejected": len(rejected),
        "schema_rejected_details": rejected,
        "tickers":         results,
    }
    
   
    
    
    
    # Save JSON output
    os.makedirs("./data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    log.info(f"output saved to {OUTPUT_PATH}")
    log.info("run finished")


if __name__ == "__main__":
    main()
