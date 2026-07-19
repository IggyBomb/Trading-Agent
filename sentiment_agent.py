#!/usr/bin/env python3
"""
sentiment_agent.py — Market Sentiment Data Fetcher
Pulls CNN Fear & Greed, VIX metrics, market internals, safe haven demand,
credit market signals, rates, and market leadership ratios.
Writes data/sentiment_data.json.

Run before /scan or standalone:
  python3 sentiment_agent.py
"""

import json, os, sys, time
from datetime import datetime, timezone

try:
    import yfinance as yf
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

try:
    import numpy as np
except ImportError:
    os.system(f"{sys.executable} -m pip install numpy --quiet")
    import numpy as np

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests --quiet")
    import requests

OUTPUT_PATH = "./data/sentiment_data.json"

CNN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":  "application/json, text/plain, */*",
    "Referer": "https://www.cnn.com/",
    "Origin":  "https://www.cnn.com",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def pct_change(a, b):
    if a and b and b != 0:
        return round((a - b) / b * 100, 2)
    return None

def ma(series, n):
    if len(series) < n:
        return None
    return float(np.mean(series[-n:]))

def label_vix(v):
    if v is None:   return "unknown"
    if v < 13:      return "complacency"
    if v < 20:      return "calm"
    if v < 30:      return "elevated"
    if v < 40:      return "fear"
    return "extreme_fear"

def fng_label(score):
    if score is None: return "unknown"
    if score <= 25:   return "Extreme Fear"
    if score <= 45:   return "Fear"
    if score <= 55:   return "Neutral"
    if score <= 75:   return "Greed"
    return "Extreme Greed"

def load_previous():
    try:
        with open(OUTPUT_PATH) as f:
            return json.load(f)
    except Exception:
        return None


# ── 1. CNN Fear & Greed ───────────────────────────────────────────────────────

def fetch_cnn_fng():
    print("  Fetching CNN Fear & Greed...", end=" ", flush=True)
    try:
        r = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers=CNN_HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()["fear_and_greed"]

        score    = round(d["score"], 1)
        rating   = d["rating"]
        prev_1w  = round(d["previous_1_week"], 1)
        prev_1m  = round(d["previous_1_month"], 1)
        prev_1y  = round(d["previous_1_year"], 1)

        weekly_delta  = round(score - prev_1w, 1)
        monthly_delta = round(score - prev_1m, 1)

        print(f"score={score} ({rating})")
        return {
            "score":          score,
            "rating":         fng_label(score),
            "raw_rating":     rating,
            "prev_1_week":    prev_1w,
            "prev_1_month":   prev_1m,
            "prev_1_year":    prev_1y,
            "weekly_delta":   weekly_delta,
            "monthly_delta":  monthly_delta,
            "interpretation": _interpret_fng(score, weekly_delta, monthly_delta),
        }
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def _interpret_fng(score, w_delta, m_delta):
    if score >= 75:
        if w_delta > 5:  return "Extreme greed accelerating — elevated reversal risk"
        if w_delta < -5: return "Extreme greed fading — watch for distribution"
        return "Extreme greed — market complacent, favour tight stops"
    if score >= 55:
        if w_delta > 5:  return "Greed building — momentum intact, stay long"
        if w_delta < -5: return "Greed fading — reduce exposure, tighten stops"
        return "Greed — healthy bull conditions"
    if score >= 45:
        return "Neutral — no clear sentiment edge"
    if score >= 25:
        if w_delta < -5: return "Fear deepening — wait for stabilisation before entry"
        if w_delta > 5:  return "Fear recovering — early contrarian opportunity"
        return "Fear — selective contrarian entry on strong setups"
    if w_delta > 5:      return "Extreme fear recovering — high-conviction contrarian entry"
    return "Extreme fear — highest contrarian opportunity, but catch falling knives carefully"


# ── 2. VIX Metrics ────────────────────────────────────────────────────────────

def fetch_vix():
    print("  Fetching VIX metrics...", end=" ", flush=True)
    try:
        vix   = yf.Ticker("^VIX").history(period="3mo")
        vix9d = yf.Ticker("^VIX9D").history(period="1mo")
        vix3m = yf.Ticker("^VIX3M").history(period="1mo")

        spot = round(float(vix["Close"].iloc[-1]), 2)
        prev = round(float(vix["Close"].iloc[-2]), 2)
        ma20 = round(ma(vix["Close"].values, 20), 2)
        ma50 = round(ma(vix["Close"].values, 50), 2)

        v9d = round(float(vix9d["Close"].iloc[-1]), 2) if not vix9d.empty else None
        v3m = round(float(vix3m["Close"].iloc[-1]), 2) if not vix3m.empty else None

        if v9d and v3m:
            if v9d > spot > v3m:
                term_structure = "backwardation"
            elif v9d < spot < v3m:
                term_structure = "contango"
            else:
                term_structure = "flat"
        else:
            term_structure = "unknown"

        # VIX9D/VIX spread — key new metric
        vix9d_spread = round(v9d - spot, 2) if v9d else None
        vix3m_spread = round(v3m - spot, 2) if v3m else None

        vix_1y = vix["Close"].values[-252:] if len(vix) >= 252 else vix["Close"].values
        percentile = round(float(np.mean(vix_1y <= spot)) * 100, 1)

        print(f"VIX={spot} ({label_vix(spot)}) term={term_structure} VIX9D/VIX={vix9d_spread}")
        return {
            "spot":            spot,
            "prev_close":      prev,
            "change_1d":       pct_change(spot, prev),
            "ma_20":           ma20,
            "ma_50":           ma50,
            "vs_ma20":         round(spot - ma20, 2),
            "vix_9d":          v9d,
            "vix_3m":          v3m,
            "vix9d_spread":    vix9d_spread,
            "vix3m_spread":    vix3m_spread,
            "term_structure":  term_structure,
            "percentile_1y":   percentile,
            "label":           label_vix(spot),
            "interpretation":  _interpret_vix(spot, prev, term_structure, percentile, vix9d_spread),
        }
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def _interpret_vix(spot, prev, term, pct, v9d_spread):
    lines = []
    if spot > 30:
        lines.append("VIX > 30: elevated fear — options expensive, selling premium has edge")
    elif spot < 15:
        lines.append("VIX < 15: complacency — cheap options, consider protective puts")
    else:
        lines.append(f"VIX {spot}: normal range")

    if term == "backwardation":
        lines.append("VIX term structure in backwardation — near-term stress, market hedging for imminent risk")
    elif term == "contango":
        lines.append("VIX term structure in contango — normal, no imminent hedging demand")

    if v9d_spread is not None:
        if v9d_spread > 1:
            lines.append(f"VIX9D/VIX spread +{v9d_spread}: front-end fear elevated — event or gap risk priced in near-term")
        elif v9d_spread < -1:
            lines.append(f"VIX9D/VIX spread {v9d_spread}: near-term calmer than medium-term — no immediate event risk")

    if pct > 80:
        lines.append(f"VIX at {pct}th percentile (1yr) — historically elevated, mean reversion likely")
    elif pct < 20:
        lines.append(f"VIX at {pct}th percentile (1yr) — historically compressed, complacency risk")

    return " | ".join(lines)


# ── 3. Market Internals ───────────────────────────────────────────────────────

def fetch_market_internals():
    print("  Fetching market internals...", end=" ", flush=True)
    try:
        results = {}
        prices = {}
        for sym, label in [("SPY","S&P500"), ("QQQ","Nasdaq100"), ("IWM","Russell2000")]:
            h = yf.Ticker(sym).history(period="1y")
            c = h["Close"].values
            price  = round(float(c[-1]), 2)
            ma50_  = round(ma(c, 50), 2)
            ma200_ = round(ma(c, 200), 2)
            ma125_ = round(ma(c, 125), 2)

            above_125    = price > ma125_ if ma125_ else None
            pct_from_200 = pct_change(price, ma200_)
            prices[sym]  = c  # store full series for ratio calculations

            results[sym] = {
                "price":          price,
                "ma_50":          ma50_,
                "ma_200":         ma200_,
                "ma_125":         ma125_,
                "above_ma50":     price > ma50_,
                "above_ma200":    price > ma200_,
                "above_ma125":    above_125,
                "pct_from_ma200": pct_from_200,
                "label":          label,
            }

        spy_ret = pct_change(results["SPY"]["price"],  results["SPY"]["ma_50"])
        qqq_ret = pct_change(results["QQQ"]["price"],  results["QQQ"]["ma_50"])
        iwm_ret = pct_change(results["IWM"]["price"],  results["IWM"]["ma_50"])
        results["breadth_note"] = _breadth_note(spy_ret, qqq_ret, iwm_ret)

        # ── Market Leadership Ratios ──────────────────────────────────────────
        spy_c = prices["SPY"]
        qqq_c = prices["QQQ"]
        iwm_c = prices["IWM"]
        min_len = min(len(spy_c), len(qqq_c), len(iwm_c))
        spy_c, qqq_c, iwm_c = spy_c[-min_len:], qqq_c[-min_len:], iwm_c[-min_len:]

        def ratio_data(num, den, label):
            r_now  = round(num[-1] / den[-1], 4)  if den[-1] else None
            r_5d   = round(num[-6] / den[-6], 4)  if min_len >= 6  and den[-6] else None
            r_20d  = round(num[-21] / den[-21], 4) if min_len >= 21 and den[-21] else None
            delta_5d  = round((r_now - r_5d)  / r_5d  * 100, 2) if r_now and r_5d  else None
            delta_20d = round((r_now - r_20d) / r_20d * 100, 2) if r_now and r_20d else None
            trend_5d  = "↑" if delta_5d and delta_5d > 0.2 else ("↓" if delta_5d and delta_5d < -0.2 else "→")
            return {
                "label": label, "ratio": r_now,
                "delta_5d": delta_5d, "delta_20d": delta_20d, "trend_5d": trend_5d,
            }

        results["qqq_spy_ratio"] = ratio_data(qqq_c, spy_c, "QQQ/SPY — tech vs market")
        results["iwm_spy_ratio"] = ratio_data(iwm_c, spy_c, "IWM/SPY — small cap vs market")

        print(f"SPY {'▲' if results['SPY']['above_ma200'] else '▼'} MA200  "
              f"QQQ {'▲' if results['QQQ']['above_ma200'] else '▼'} MA200  "
              f"IWM {'▲' if results['IWM']['above_ma200'] else '▼'} MA200  "
              f"QQQ/SPY={results['qqq_spy_ratio']['ratio']} {results['qqq_spy_ratio']['trend_5d']}")
        return results
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def _breadth_note(spy, qqq, iwm):
    if spy is None or qqq is None or iwm is None:
        return "insufficient data"
    if spy > 0 and qqq > 0 and iwm > 0:
        return "Broad participation — all three indices above MA50, healthy rally"
    if spy > 0 and qqq > 0 and iwm < 0:
        return "Narrow leadership — large caps leading, small caps lagging (risk-off undertone)"
    if qqq > spy:
        return "Tech-led rally — Nasdaq outperforming, momentum concentrated in growth"
    if iwm > qqq:
        return "Risk-on rotation — small caps outperforming, broad risk appetite high"
    if spy < 0 and qqq < 0 and iwm < 0:
        return "Broad weakness — all indices below MA50, defensive posture warranted"
    return "Mixed signals — sector rotation in progress"


# ── 4. Safe Haven Demand ──────────────────────────────────────────────────────

def fetch_safe_haven():
    print("  Fetching safe haven demand...", end=" ", flush=True)
    try:
        data = {}
        for sym, label in [("TLT","Bonds_20yr"), ("GLD","Gold"), ("UUP","DollarIndex")]:
            h = yf.Ticker(sym).history(period="1mo")
            if h.empty:
                continue
            c = h["Close"].values
            ret_5d  = pct_change(float(c[-1]), float(c[-6])) if len(c) >= 6 else None
            ret_20d = pct_change(float(c[-1]), float(c[-21])) if len(c) >= 21 else None
            data[sym] = {
                "price":    round(float(c[-1]), 2),
                "ret_5d":   ret_5d,
                "ret_20d":  ret_20d,
                "label":    label,
            }

        interpretation = _interpret_safe_haven(data)
        data["interpretation"] = interpretation
        print(f"TLT {data.get('TLT',{}).get('ret_20d','?')}% 20d  GLD {data.get('GLD',{}).get('ret_20d','?')}% 20d")
        return data
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def _interpret_safe_haven(d):
    tlt = d.get("TLT", {}).get("ret_20d")
    gld = d.get("GLD", {}).get("ret_20d")
    uup = d.get("UUP", {}).get("ret_20d")

    if tlt and gld and tlt > 2 and gld > 2:
        return "Both bonds and gold rising — classic flight to safety, risk-off dominant"
    if gld and gld > 3 and (tlt is None or tlt < 1):
        return "Gold rising without bonds — inflation hedge demand or geopolitical uncertainty"
    if tlt and tlt > 2 and (gld is None or gld < 1):
        return "Bonds rising without gold — deflationary/recession fear, rate cut expectations"
    if tlt and gld and tlt < -1 and gld < -1:
        return "Both bonds and gold falling — risk-on, capital rotating into equities"
    if uup and uup > 2:
        return "Dollar strengthening — global risk-off, dollar as safe haven in demand"
    return "Safe haven demand neutral — no strong flight-to-safety signal"


# ── 5. Credit Market Sentiment ────────────────────────────────────────────────

def fetch_credit():
    print("  Fetching credit market sentiment...", end=" ", flush=True)
    try:
        data = {}
        for sym, label in [("HYG","HighYield"), ("LQD","InvGrade"), ("JNK","Junk")]:
            h = yf.Ticker(sym).history(period="1mo")
            if h.empty:
                continue
            c = h["Close"].values
            data[sym] = {
                "price":    round(float(c[-1]), 2),
                "ret_5d":   pct_change(float(c[-1]), float(c[-6])) if len(c) >= 6 else None,
                "ret_20d":  pct_change(float(c[-1]), float(c[-21])) if len(c) >= 21 else None,
                "label":    label,
            }

        hyg_ret = data.get("HYG", {}).get("ret_20d")
        lqd_ret = data.get("LQD", {}).get("ret_20d")

        if hyg_ret and lqd_ret:
            spread_signal = hyg_ret - lqd_ret
            if spread_signal > 1:
                interp = "High yield outperforming investment grade — credit appetite healthy, risk-on signal"
            elif spread_signal < -1:
                interp = "High yield underperforming investment grade — credit stress, spreads widening, risk-off signal"
            else:
                interp = "High yield / investment grade spread neutral"
        else:
            interp = "Insufficient credit data"

        data["interpretation"] = interp
        print(f"HYG {hyg_ret}% 20d  LQD {lqd_ret}% 20d")
        return data
    except Exception as e:
        print(f"ERROR: {e}")
        return None


# ── 6. Put/Call Ratio ─────────────────────────────────────────────────────────

def fetch_put_call():
    print("  Fetching put/call ratio (SPY options)...", end=" ", flush=True)
    try:
        spy  = yf.Ticker("SPY")
        exps = spy.options
        if not exps:
            print("no options data")
            return None

        chain = spy.option_chain(exps[0])
        calls = chain.calls["openInterest"].sum()
        puts  = chain.puts["openInterest"].sum()

        if calls == 0:
            print("no call OI")
            return None

        ratio = round(puts / calls, 3)
        label = (
            "bearish hedging (> 1.2)" if ratio > 1.2 else
            "elevated puts (0.9-1.2)" if ratio > 0.9 else
            "neutral (0.7-0.9)"        if ratio > 0.7 else
            "bullish (call-heavy)"
        )

        print(f"P/C={ratio} ({label})")
        return {
            "ratio":           ratio,
            "calls_oi":        int(calls),
            "puts_oi":         int(puts),
            "label":           label,
            "expiry_used":     exps[0],
            "interpretation":  _interpret_pc(ratio),
        }
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def _interpret_pc(ratio):
    if ratio > 1.5:
        return "Extreme put buying — market deeply hedged, often contrarian bullish at extremes"
    if ratio > 1.2:
        return "Elevated put/call — bearish hedging dominant, caution warranted"
    if ratio > 0.9:
        return "Slightly elevated puts — mild caution, watch for follow-through"
    if ratio > 0.7:
        return "Neutral put/call — balanced market sentiment"
    return "Call-heavy — bullish speculation dominant, watch for complacency"


# ── 7. EU Market Internals ────────────────────────────────────────────────────

def fetch_eu_internals():
    print("  Fetching EU market internals...", end=" ", flush=True)
    try:
        results = {}

        # EU equity indices
        for sym, label in [
            ("^GDAXI",    "DAX"),
            ("^FTSE",     "FTSE100"),
            ("^FCHI",     "CAC40"),
            ("FTSEMIB.MI","FTSEMIB"),   # ^FTSEMIB not on Yahoo Finance free
        ]:
            try:
                h = yf.Ticker(sym).history(period="1y")
                if h.empty:
                    continue
                c = h["Close"].values
                price        = round(float(c[-1]), 2)
                ma50_        = round(ma(c, 50), 2)
                ma200_       = round(ma(c, 200), 2)
                ret_5d       = pct_change(float(c[-1]), float(c[-6]))  if len(c) >= 6  else None
                ret_1m       = pct_change(float(c[-1]), float(c[-22])) if len(c) >= 22 else None
                pct_from_200 = pct_change(price, ma200_) if ma200_ else None
                results[sym] = {
                    "label":          label,
                    "price":          price,
                    "ma_50":          ma50_,
                    "ma_200":         ma200_,
                    "above_ma50":     bool(price > ma50_)  if ma50_  else None,
                    "above_ma200":    bool(price > ma200_) if ma200_ else None,
                    "pct_from_ma200": pct_from_200,
                    "ret_5d":         ret_5d,
                    "ret_1m":         ret_1m,
                }
            except Exception:
                continue

        # VSTOXX — European volatility index (equivalent of VIX)
        # ^V2TX not always available on Yahoo Finance; try VDAX as fallback
        try:
            vstoxx_sym = "^V2TX"
            h = yf.Ticker(vstoxx_sym).history(period="3mo")
            if h.empty:
                vstoxx_sym = "^VDAX"
                h = yf.Ticker(vstoxx_sym).history(period="3mo")
            if not h.empty:
                vc     = h["Close"].values
                v_spot = round(float(vc[-1]), 2)
                v_prev = round(float(vc[-2]), 2)
                window = vc[-252:] if len(vc) >= 252 else vc
                v_pct  = round(float(np.mean(window <= v_spot)) * 100, 1)
                results["VSTOXX"] = {
                    "spot":       v_spot,
                    "prev":       v_prev,
                    "change_1d":  round(v_spot - v_prev, 2),
                    "percentile": v_pct,
                    "label":      label_vix(v_spot),
                }
        except Exception:
            pass

        # EUR/USD
        try:
            h = yf.Ticker("EURUSD=X").history(period="1mo")
            if not h.empty:
                ec = h["Close"].values
                eu_price = round(float(ec[-1]), 4)
                r5d      = pct_change(float(ec[-1]), float(ec[-6]))  if len(ec) >= 6  else None
                r20d     = pct_change(float(ec[-1]), float(ec[-21])) if len(ec) >= 21 else None
                results["EURUSD"] = {
                    "price":   eu_price,
                    "ret_5d":  r5d,
                    "ret_20d": r20d,
                    "trend":   ("strengthening" if r5d and r5d > 0.3 else
                                "weakening"     if r5d and r5d < -0.3 else "stable"),
                }
        except Exception:
            pass

        # EU breadth
        eu_syms      = ["^GDAXI", "^FTSE", "^FCHI", "^FTSEMIB"]
        tracked      = [s for s in eu_syms if s in results]
        above_200    = [s for s in tracked if results[s].get("above_ma200")]
        bull_regime  = len(above_200) > len(tracked) // 2 if tracked else None

        results["eu_breadth"]     = f"{len(above_200)}/{len(tracked)} EU indices above MA200"
        results["eu_bull_regime"] = bull_regime
        results["interpretation"] = _interpret_eu(results, above_200, tracked)

        # Print summary line
        parts = []
        for sym in ["^GDAXI", "^FTSE"]:
            if sym in results:
                lbl  = results[sym]["label"]
                flag = "▲" if results[sym].get("above_ma200") else "▼"
                parts.append(f"{lbl} {flag} MA200")
        if "VSTOXX" in results:
            parts.append(f"VSTOXX={results['VSTOXX']['spot']}")
        if "EURUSD" in results:
            parts.append(f"EUR/USD={results['EURUSD']['price']}")
        print("  ".join(parts) if parts else "partial data")

        return results
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def _interpret_eu(d, above_200, tracked):
    lines = []

    if tracked:
        n = len(above_200)
        t = len(tracked)
        if n == t:
            lines.append(f"All {t} EU indices above MA200 — EU bull regime intact")
        elif n > t // 2:
            lines.append(f"{n}/{t} EU indices above MA200 — mixed, bullish bias")
        else:
            lines.append(f"Only {n}/{t} EU indices above MA200 — EU caution warranted")

    vstoxx = d.get("VSTOXX", {}).get("spot")
    if vstoxx:
        if vstoxx > 25:
            lines.append(f"VSTOXX {vstoxx} elevated (>{25}) — reduce EU position size")
        elif vstoxx < 15:
            lines.append(f"VSTOXX {vstoxx} compressed — EU complacency risk")
        else:
            lines.append(f"VSTOXX {vstoxx} normal range")

    eurusd = d.get("EURUSD", {})
    trend  = eurusd.get("trend", "stable")
    if trend == "weakening":
        lines.append("EUR/USD weakening — USD-denominated headwind for EU holdings")
    elif trend == "strengthening":
        lines.append("EUR/USD strengthening — tailwind for EU holdings in USD terms")

    return " | ".join(lines) if lines else "EU internals nominal"


def eu_composite_score(eu):
    """Separate 0–100 composite for EU market conditions."""
    if not eu:
        return None, "N/A"

    score = 50

    # VSTOXX (mirrors VIX logic)
    vstoxx = eu.get("VSTOXX", {}).get("spot")
    if vstoxx:
        if vstoxx < 15:   score += 10
        elif vstoxx < 20: score += 5
        elif vstoxx > 30: score -= 10
        elif vstoxx > 25: score -= 5

    # EU indices vs MA200
    for sym in ["^GDAXI", "^FTSE", "^FCHI", "^FTSEMIB"]:
        d = eu.get(sym)
        if d:
            score += 3 if d.get("above_ma200") else -3

    # EUR/USD trend
    eurusd_trend = eu.get("EURUSD", {}).get("trend")
    if eurusd_trend == "weakening":     score -= 3
    elif eurusd_trend == "strengthening": score += 3

    score = round(min(max(score, 0), 100), 1)
    label = (
        "Risk-On"       if score > 65 else
        "Mild Risk-On"  if score > 55 else
        "Neutral"       if score > 45 else
        "Mild Risk-Off" if score > 35 else
        "Risk-Off"
    )
    return score, label


# ── 8. Rates (10Y Treasury) ───────────────────────────────────────────────────

def fetch_rates():
    print("  Fetching rates (10Y Treasury)...", end=" ", flush=True)
    try:
        h10 = yf.Ticker("^TNX").history(period="3mo")
        if h10.empty:
            print("no data")
            return None

        c = h10["Close"].values
        yield_10y  = round(float(c[-1]), 3)
        prev_10y   = round(float(c[-2]), 3)
        change_1d  = round(yield_10y - prev_10y, 3)
        ret_5d     = round(yield_10y - float(c[-6]), 3)  if len(c) >= 6  else None
        ret_20d    = round(yield_10y - float(c[-21]), 3) if len(c) >= 21 else None
        ma20_yield = round(ma(c, 20), 3)

        trend = "rising" if ret_5d and ret_5d > 0.05 else ("falling" if ret_5d and ret_5d < -0.05 else "stable")

        print(f"10Y={yield_10y}% ({trend})")
        return {
            "yield_10y":    yield_10y,
            "prev_close":   prev_10y,
            "change_1d":    change_1d,
            "change_5d":    ret_5d,
            "change_20d":   ret_20d,
            "ma_20":        ma20_yield,
            "trend":        trend,
            "interpretation": _interpret_rates(yield_10y, ret_5d, ret_20d),
        }
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def _interpret_rates(y10, d5, d20):
    lines = []
    if y10 > 5.0:
        lines.append(f"10Y at {y10}% — elevated, significant headwind for growth/high-multiple stocks")
    elif y10 > 4.5:
        lines.append(f"10Y at {y10}% — above neutral, moderate pressure on rate-sensitive names")
    elif y10 < 3.5:
        lines.append(f"10Y at {y10}% — low, tailwind for growth stocks and risk assets")
    else:
        lines.append(f"10Y at {y10}% — neutral range")

    if d5 and d5 > 0.15:
        lines.append("Rising sharply this week — watch growth/fintech/REIT exposure")
    elif d5 and d5 < -0.15:
        lines.append("Falling sharply this week — tailwind for rate-sensitive longs")

    return " | ".join(lines)


# ── Composite Score ───────────────────────────────────────────────────────────

def composite_score(fng, vix, internals, safe_haven, credit, pc, rates, eu=None):
    score = 50

    if fng:
        score += (fng["score"] - 50) * 0.35

    if vix:
        if vix["spot"] < 15:   score += 10
        elif vix["spot"] < 20: score += 5
        elif vix["spot"] > 30: score -= 10
        elif vix["spot"] > 25: score -= 5
        if vix["term_structure"] == "backwardation": score -= 8
        if vix.get("vix9d_spread") and vix["vix9d_spread"] > 1: score -= 3

    if internals:
        for sym in ["SPY", "QQQ", "IWM"]:
            if sym in internals:
                if internals[sym].get("above_ma200"): score += 3
                else: score -= 3
        qqq_spy = internals.get("qqq_spy_ratio", {})
        if qqq_spy.get("delta_5d") and qqq_spy["delta_5d"] > 0.5: score += 2

    if credit:
        hyg = credit.get("HYG", {}).get("ret_20d")
        lqd = credit.get("LQD", {}).get("ret_20d")
        if hyg and lqd:
            if hyg > lqd + 1:  score += 5
            if hyg < lqd - 1:  score -= 5

    if pc:
        if pc["ratio"] > 1.2:  score -= 5
        if pc["ratio"] < 0.7:  score += 5

    if rates:
        y = rates["yield_10y"]
        if y > 5.0:   score -= 5
        elif y > 4.5: score -= 2
        elif y < 3.5: score += 3

    score = round(min(max(score, 0), 100), 1)
    label = (
        "Risk-On"       if score > 65 else
        "Mild Risk-On"  if score > 55 else
        "Neutral"       if score > 45 else
        "Mild Risk-Off" if score > 35 else
        "Risk-Off"
    )
    return score, label


# ── Print Dashboard ───────────────────────────────────────────────────────────

def _fmt(val, suffix="", fallback="—"):
    if val is None: return fallback
    return f"{val}{suffix}"

def _delta_str(curr, prev, suffix="", invert=False):
    if curr is None or prev is None: return "—"
    d = round(curr - prev, 3)
    arrow = "↑" if d > 0 else ("↓" if d < 0 else "→")
    bad = (d > 0) if invert else (d < 0)
    return f"{arrow} {d:+.2f}{suffix}"


def print_dashboard(score, label, score_delta, fng, vix, internals, safe_haven, credit, pc, rates, previous, eu=None, eu_score=None, eu_label=None):
    W = 76
    prev_date = ""
    if previous and previous.get("generated_at"):
        try:
            from datetime import datetime as dt
            prev_date = dt.fromisoformat(previous["generated_at"]).strftime("%Y-%m-%d")
        except Exception:
            prev_date = "prev"

    now_date  = datetime.now().strftime("%Y-%m-%d %H:%M")
    delta_str = f"  Δ {score_delta:+.1f} vs {prev_date}" if score_delta is not None else ""

    print(f"\n{'='*W}")
    print(f"  SENTIMENT DASHBOARD — {now_date}   |   COMPOSITE: {score}/100  {label}{delta_str}")
    print(f"{'='*W}\n")

    # ── Column headers ────────────────────────────────────────────────────────
    prev_col = f"PREV ({prev_date})" if prev_date else "PREVIOUS"
    print(f"  {'INDICATOR':<26}  {'CURRENT':<16}  {prev_col:<16}  {'DELTA':<12}  NOTE")
    print(f"  {'─'*26}  {'─'*16}  {'─'*16}  {'─'*12}  {'─'*28}")

    def row(ind, curr_str, prev_str, delta_s, note=""):
        print(f"  {ind:<26}  {curr_str:<16}  {prev_str:<16}  {delta_s:<12}  {note}")

    def divider(title):
        pad = W - 6 - len(title)
        print(f"\n  ── {title} {'─'*pad}")

    # ── Composite ─────────────────────────────────────────────────────────────
    prev_score = previous.get("composite_score") if previous else None
    prev_label = previous.get("composite_label", "—") if previous else "—"
    d_score    = _delta_str(score, prev_score)
    row("Composite score",
        f"{score} ({label})",
        f"{_fmt(prev_score)} ({prev_label})" if prev_score else "—",
        d_score, "")

    # ── Sentiment & Volatility ────────────────────────────────────────────────
    divider("SENTIMENT & VOLATILITY")

    if fng:
        p_fng   = (previous or {}).get("cnn_fear_greed") or {}
        p_score = p_fng.get("score")
        sizing  = "⚠ HALF SIZE" if fng["score"] > 65 else ("↑ INCREASE" if fng["score"] < 25 else "NORMAL SIZE")
        row("CNN Fear & Greed",
            f"{fng['score']} ({fng['rating']})",
            f"{_fmt(p_score)} ({p_fng.get('rating','—')})" if p_score else "—",
            _delta_str(fng["score"], p_score),
            sizing)

    if vix:
        p_vix  = (previous or {}).get("vix") or {}
        row("VIX",
            f"{vix['spot']} ({vix['label']})",
            _fmt(p_vix.get("spot"), f" ({p_vix.get('label','')})") if p_vix else "—",
            _delta_str(vix["spot"], p_vix.get("spot")),
            f"pct {vix['percentile_1y']}th | {vix['term_structure']}")

        spread = vix.get("vix9d_spread")
        p_spread = p_vix.get("vix9d_spread")
        spread_sig = "front-end risk ⚠" if spread and spread > 1 else ("calm ✓" if spread and spread is not None and spread < -0.5 else "neutral")
        row("VIX9D / VIX spread",
            _fmt(spread, ""),
            _fmt(p_spread) if p_spread is not None else "new",
            _delta_str(spread, p_spread) if p_spread is not None else "—",
            spread_sig)

        row("VIX percentile (1yr)",
            f"{vix['percentile_1y']}th",
            _fmt(p_vix.get("percentile_1y"), "th"),
            _delta_str(vix["percentile_1y"], p_vix.get("percentile_1y")),
            "<20 = complacency | >80 = elevated")

    if pc:
        p_pc = (previous or {}).get("put_call") or {}
        row("Put/Call ratio (SPY)",
            str(pc["ratio"]),
            _fmt(p_pc.get("ratio")) if p_pc else "—",
            _delta_str(pc["ratio"], p_pc.get("ratio")),
            pc["label"])

    # ── Rates ─────────────────────────────────────────────────────────────────
    divider("RATES")

    if rates:
        p_rates = (previous or {}).get("rates") or {}
        p_y = p_rates.get("yield_10y") if p_rates else None
        row("10Y Treasury Yield",
            f"{rates['yield_10y']}%",
            f"{_fmt(p_y)}%" if p_y else "new",
            _delta_str(rates["yield_10y"], p_y, "%") if p_y else "—",
            rates["trend"] + f" | Δ5d {rates.get('change_5d',0):+.3f}%")

    # ── Market Structure ──────────────────────────────────────────────────────
    divider("MARKET STRUCTURE")

    if internals:
        p_int = (previous or {}).get("market_internals") or {}
        for sym in ["SPY", "QQQ", "IWM"]:
            if sym not in internals: continue
            d      = internals[sym]
            p_sym  = p_int.get(sym, {})
            flag   = "▲ BULL" if d["above_ma200"] else "▼ BEAR"
            row(f"{sym} vs MA200",
                f"{d['pct_from_ma200']:+.2f}%",
                f"{_fmt(p_sym.get('pct_from_ma200'), '%'):}" if p_sym else "—",
                _delta_str(d["pct_from_ma200"], p_sym.get("pct_from_ma200"), "%"),
                flag)

        qqq_spy = internals.get("qqq_spy_ratio", {})
        iwm_spy = internals.get("iwm_spy_ratio", {})
        p_qqq   = p_int.get("qqq_spy_ratio", {})
        p_iwm   = p_int.get("iwm_spy_ratio", {})

        if qqq_spy.get("ratio"):
            lead = "tech lead ↑" if (qqq_spy.get("delta_5d") or 0) > 0 else "rotating ↓"
            row("QQQ/SPY ratio",
                f"{qqq_spy['ratio']} {qqq_spy.get('trend_5d','')}",
                _fmt(p_qqq.get("ratio")) if p_qqq.get("ratio") else "new",
                _delta_str(qqq_spy["ratio"], p_qqq.get("ratio")) if p_qqq.get("ratio") else "—",
                lead)

        if iwm_spy.get("ratio"):
            lead = "risk-on ↑" if (iwm_spy.get("delta_5d") or 0) > 0 else "quality ↓"
            row("IWM/SPY ratio",
                f"{iwm_spy['ratio']} {iwm_spy.get('trend_5d','')}",
                _fmt(p_iwm.get("ratio")) if p_iwm.get("ratio") else "new",
                _delta_str(iwm_spy["ratio"], p_iwm.get("ratio")) if p_iwm.get("ratio") else "—",
                lead)

        if "breadth_note" in internals:
            print(f"\n  Breadth: {internals['breadth_note']}")

    # ── Safe Haven & Credit ───────────────────────────────────────────────────
    divider("SAFE HAVEN & CREDIT")

    if safe_haven:
        p_sh = (previous or {}).get("safe_haven") or {}
        for sym, lbl in [("TLT","Bonds 20yr"), ("GLD","Gold"), ("UUP","Dollar")]:
            d   = safe_haven.get(sym, {})
            p_d = p_sh.get(sym, {})
            if not d: continue
            row(f"{sym} ({lbl}) 20d ret",
                f"{_fmt(d.get('ret_20d'), '%')}",
                f"{_fmt(p_d.get('ret_20d'), '%')}" if p_d.get("ret_20d") is not None else "—",
                _delta_str(d.get("ret_20d"), p_d.get("ret_20d"), "%"),
                f"5d: {_fmt(d.get('ret_5d'), '%')}")
        print(f"\n  Safe haven: {safe_haven.get('interpretation','')}")

    if credit:
        p_cr = (previous or {}).get("credit") or {}
        for sym, lbl in [("HYG","High Yield"), ("LQD","Inv Grade")]:
            d   = credit.get(sym, {})
            p_d = p_cr.get(sym, {})
            if not d: continue
            row(f"{sym} ({lbl}) 20d ret",
                f"{_fmt(d.get('ret_20d'), '%')}",
                f"{_fmt(p_d.get('ret_20d'), '%')}" if p_d.get("ret_20d") is not None else "—",
                _delta_str(d.get("ret_20d"), p_d.get("ret_20d"), "%"),
                "")
        print(f"\n  Credit: {credit.get('interpretation','')}")

    # ── EU Market Internals ───────────────────────────────────────────────────
    if eu:
        p_eu = (previous or {}).get("eu_internals") or {}
        divider("EU MARKET INTERNALS")

        if eu_score is not None:
            p_eu_score = p_eu.get("eu_composite_score")
            row("EU Composite",
                f"{eu_score} ({eu_label})",
                f"{_fmt(p_eu_score)}" if p_eu_score else "—",
                _delta_str(eu_score, p_eu_score) if p_eu_score else "—",
                "EU-specific sizing applies for EU tickers")

        for sym, lbl in [("^GDAXI","DAX"), ("^FTSE","FTSE100"), ("^FCHI","CAC40"), ("^FTSEMIB","FTSEMIB")]:
            d   = eu.get(sym, {})
            p_d = p_eu.get(sym, {})
            if not d:
                continue
            flag = "▲ BULL" if d.get("above_ma200") else "▼ BEAR"
            row(f"{lbl} vs MA200",
                f"{_fmt(d.get('pct_from_ma200'), '%'):}",
                f"{_fmt(p_d.get('pct_from_ma200'), '%')}" if p_d.get("pct_from_ma200") is not None else "—",
                _delta_str(d.get("pct_from_ma200"), p_d.get("pct_from_ma200"), "%"),
                flag)

        vstoxx = eu.get("VSTOXX", {})
        p_vs   = p_eu.get("VSTOXX", {})
        if vstoxx.get("spot"):
            sizing_note = ("⚠ REDUCE EU SIZE" if vstoxx["spot"] > 25 else
                           "⚠ EU COMPLACENCY"  if vstoxx["spot"] < 15 else "normal")
            row("VSTOXX",
                f"{vstoxx['spot']} ({vstoxx.get('label','')})",
                _fmt(p_vs.get("spot")) if p_vs.get("spot") else "—",
                _delta_str(vstoxx["spot"], p_vs.get("spot")),
                f"pct {vstoxx.get('percentile','')}th | {sizing_note}")

        eurusd = eu.get("EURUSD", {})
        p_eur  = p_eu.get("EURUSD", {})
        if eurusd.get("price"):
            row("EUR/USD",
                f"{eurusd['price']} ({eurusd.get('trend','')})",
                _fmt(p_eur.get("price")) if p_eur.get("price") else "—",
                _delta_str(eurusd.get("ret_5d"), None) if eurusd.get("ret_5d") else "—",
                f"5d: {_fmt(eurusd.get('ret_5d'), '%')}")

        if eu.get("eu_breadth"):
            print(f"\n  EU Breadth: {eu['eu_breadth']}")
        if eu.get("interpretation"):
            print(f"  EU Read:    {eu['interpretation']}")

        # EU sizing rule
        if vstoxx.get("spot"):
            v = vstoxx["spot"]
            if v > 25:
                print(f"\n  ⚠  EU REDUCE SIZE  — VSTOXX {v} (>{25}) → max 1% on EU tickers")
            elif v < 15:
                print(f"\n  ✓  EU NORMAL SIZE  — VSTOXX {v} (<15, complacency) → standard 2%, tighten stops")
            else:
                print(f"\n  ✓  EU NORMAL SIZE  — VSTOXX {v} normal → standard sizing applies")

    # ── Sizing Rule ───────────────────────────────────────────────────────────
    divider("ACTIVE SIZING RULE")
    if fng:
        if fng["score"] > 65:
            print(f"  ⚠  HALF SIZE   — CNN F&G {fng['score']} (Greed)        → max 1% of capital per trade")
        elif fng["score"] < 25:
            print(f"  ↑  INCREASE    — CNN F&G {fng['score']} (Extreme Fear)  → up to 3% on CONFIRMED setups only")
        else:
            print(f"  ✓  NORMAL SIZE — CNN F&G {fng['score']} (Neutral/Fear)  → max 2% of capital per trade")

    # ── Notes ─────────────────────────────────────────────────────────────────
    divider("INDICATOR NOTES")
    notes = [
        ("CNN Fear & Greed",    ">65 = half size (1%). <25 = increase size (3%, CONFIRMED only)."),
        ("VIX9D/VIX spread",    "Negative = near-term calm. Positive >+1 = front-end event fear priced in."),
        ("VIX percentile",      "<20 = historically compressed (complacency). >80 = elevated (mean revert likely)."),
        ("10Y Yield",           "Rising = headwind for growth/high-multiple stocks. Falling = tailwind."),
        ("QQQ/SPY ratio",       "Rising = tech leading market. Growth stocks favoured. Falling = rotate to value."),
        ("IWM/SPY ratio",       "Rising = small caps leading. Broad risk appetite. Falling = flight to large cap."),
        ("Put/Call > 1.5",      "Extreme hedging — historically contrarian bullish at extremes."),
        ("Composite Δ",         "Direction matters more than absolute level. Rapid drop = de-risking in progress."),
        ("VSTOXX",              ">25 = reduce EU size (1%). <15 = EU complacency, tighten stops."),
        ("EUR/USD trend",       "Weakening EUR = USD headwind for EU holdings. Strengthening = tailwind."),
        ("EU Composite",        "Applies when trading EU-suffix tickers (.L .MI .PA .DE etc)."),
    ]
    print(f"\n  {'INDICATOR':<26}  {'NOTE'}")
    print(f"  {'─'*26}  {'─'*46}")
    for lbl, note in notes:
        print(f"  {lbl:<26}  {note}")

    print(f"\n{'='*W}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"  Sentiment Agent — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    previous   = load_previous()
    prev_score = previous.get("composite_score") if previous else None

    fng        = fetch_cnn_fng()
    vix        = fetch_vix()
    internals  = fetch_market_internals()
    safe_haven = fetch_safe_haven()
    credit     = fetch_credit()
    pc         = fetch_put_call()
    rates      = fetch_rates()
    eu         = fetch_eu_internals()

    score, label       = composite_score(fng, vix, internals, safe_haven, credit, pc, rates, eu)
    score_delta        = round(score - prev_score, 1) if prev_score is not None else None
    eu_score, eu_label = eu_composite_score(eu)

    output = {
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "composite_score":    score,
        "composite_label":    label,
        "composite_delta":    score_delta,
        "cnn_fear_greed":     fng,
        "vix":                vix,
        "market_internals":   internals,
        "safe_haven":         safe_haven,
        "credit":             credit,
        "put_call":           pc,
        "rates":              rates,
        "eu_internals":       eu,
        "eu_composite_score": eu_score,
        "eu_composite_label": eu_label,
    }

    os.makedirs("./data", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    import io, sys
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    print_dashboard(score, label, score_delta, fng, vix, internals, safe_haven, credit, pc, rates, previous,
                    eu=eu, eu_score=eu_score, eu_label=eu_label)
    sys.stdout = old_stdout
    dashboard_text = buf.getvalue()

    report_path = f"./data/sentiment_report_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(report_path, "w") as f:
        f.write(f"# Sentiment Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("```\n")
        f.write(dashboard_text)
        f.write("```\n")

    print(dashboard_text)
    print(f"  Output saved to : {OUTPUT_PATH}")
    print(f"  Report saved to : {report_path}\n")


if __name__ == "__main__":
    main()
