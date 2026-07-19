#!/usr/bin/env python3
"""
fetch_data.py — Pre-scan market data fetcher
Reads watchlist.txt, pulls 60 days of OHLCV data from Yahoo Finance,
computes key technical metrics, and writes data/market_data.json
for Claude to read before running /scan.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta

# ── Install yfinance if missing ──────────────────────────────────────────────
try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    os.system(f"{sys.executable} -m pip install yfinance --quiet")
    import yfinance as yf

try:
    import numpy as np
except ImportError:
    os.system(f"{sys.executable} -m pip install numpy --quiet")
    import numpy as np

# ── Config ───────────────────────────────────────────────────────────────────
from config import (
    EU_SUFFIXES, JP_SUFFIXES, CA_SUFFIXES, BR_SUFFIXES,
    MIN_PRICE, MIN_AVG_VOLUME, EU_MIN_AVG_VOLUME, JP_MIN_AVG_VOLUME,
    CA_MIN_AVG_VOLUME, BR_MIN_AVG_VOLUME,
    MIN_ATR_PCT, EU_MIN_ATR_PCT, JP_MIN_ATR_PCT, CA_MIN_ATR_PCT, BR_MIN_ATR_PCT,
    SR_WINDOW, RR_RATIO, MAX_TICKERS,
    LOOKBACK_DAYS, BATCH_SIZE, BATCH_PAUSE, EU_BATCH_SIZE, EU_BATCH_PAUSE,
    JP_BATCH_SIZE, JP_BATCH_PAUSE, CA_BATCH_SIZE, CA_BATCH_PAUSE,
    BR_BATCH_SIZE, BR_BATCH_PAUSE,
    WATCHLIST_PATH, MARKET_DATA_PATH,
)

OUTPUT_PATH = MARKET_DATA_PATH

# ── Helpers ──────────────────────────────────────────────────────────────────

def is_european(ticker):
    dot = ticker.rfind(".")
    return dot != -1 and ticker[dot:].upper() in EU_SUFFIXES


def is_japanese(ticker):
    dot = ticker.rfind(".")
    return dot != -1 and ticker[dot:].upper() in JP_SUFFIXES


def is_canadian(ticker):
    dot = ticker.rfind(".")
    return dot != -1 and ticker[dot:].upper() in CA_SUFFIXES


def is_brazilian(ticker):
    dot = ticker.rfind(".")
    return dot != -1 and ticker[dot:].upper() in BR_SUFFIXES


def load_watchlist(path):
    if not os.path.exists(path):
        print(f"ERROR: Watchlist not found at {path}")
        sys.exit(1)
    with open(path) as f:
        tickers = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    print(f"Loaded {len(tickers)} tickers from watchlist")
    return tickers[:MAX_TICKERS]

"""volatility?"""
def atr(highs, lows, closes, period=14):
    """Average True Range over `period` days."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i]  - closes[i - 1]),
        )
        trs.append(tr)
    return float(np.mean(trs[-period:]))


def trend_direction(closes):
    """Returns 'up', 'down', or 'sideways' based on last 20 closes."""
    if len(closes) < 20:
        return "unknown"
    recent = closes[-20:]
    highs = [max(recent[i:i+5]) for i in range(0, 15, 5)]
    lows  = [min(recent[i:i+5]) for i in range(0, 15, 5)]
    higher_highs = highs[-1] > highs[0]
    higher_lows  = lows[-1]  > lows[0]
    lower_highs  = highs[-1] < highs[0]
    lower_lows   = lows[-1]  < lows[0]
    if higher_highs and higher_lows:
        return "up"
    if lower_highs and lower_lows:
        return "down"
    return "sideways"


def avg_volume(volumes):
    """20-day average volume."""
    if len(volumes) < 21:
        return None
    return float(np.mean(volumes[-21:-1]))


def volume_vs_avg(volumes):
    """Returns ratio of last close volume vs 20-day average."""
    avg = avg_volume(volumes)
    if avg is None or avg == 0:
        return None
    return round(float(volumes[-1]) / avg, 2)


def support_resistance(highs, lows, window=SR_WINDOW):
    """Pivot-based S/R using a short-term window."""
    if len(highs) < window:
        return None, None
    recent_highs = highs[-window:]
    recent_lows  = lows[-window:]
    resistance   = round(float(max(recent_highs)), 4)
    support      = round(float(min(recent_lows)), 4)
    return support, resistance


def distance_from_sr(price, support, resistance):
    """How far current price is from support and resistance, in %."""
    if support is None or resistance is None or price is None:
        return None, None
    dist_support    = round((price - support) / support * 100, 2)   if support    > 0 else None
    dist_resistance = round((resistance - price) / price * 100, 2)  if resistance > 0 else None
    return dist_support, dist_resistance


def setup_type(closes, volumes, support, resistance):
    """Classify the current setup based on price action."""
    if len(closes) < SR_WINDOW or support is None:
        return "unknown"
    price     = closes[-1]
    prev      = closes[-2]
    vol_ratio = volume_vs_avg(volumes)

    near_resistance = resistance and (resistance - price) / price < 0.02
    near_support    = support    and (price - support) / price    < 0.02
    strong_volume   = vol_ratio and vol_ratio > 1.3

    if near_resistance and strong_volume and price > prev:
        return "breakout"
    if trend_direction(closes) == "up" and near_support:
        return "pullback"
    if trend_direction(closes) == "down" and near_support and strong_volume:
        return "reversal"
    if near_resistance and not strong_volume:
        return "consolidation"
    return "neutral"


def short_setup_type(closes, volumes, support, resistance):
    """Classify short setup based on price action."""
    if len(closes) < SR_WINDOW or resistance is None:
        return "none"
    price     = closes[-1]
    prev      = closes[-2]
    vol_ratio = volume_vs_avg(volumes)
    trend     = trend_direction(closes)

    near_resistance = resistance and (resistance - price) / price < 0.02
    near_support    = support    and (price - support) / price    < 0.02
    strong_volume   = vol_ratio and vol_ratio > 1.3

    # Breakdown: price breaks below support on volume in a downtrend
    if trend == "down" and near_support and strong_volume and price < prev:
        return "breakdown"
    # Distribution: near resistance, failing to break up, trend already down
    if trend == "down" and near_resistance and not strong_volume:
        return "distribution"
    # Dead cat: short-term bounce in a downtrend (price above recent lows but trend down)
    if trend == "down" and not near_support and not near_resistance:
        if len(closes) >= 5 and price > closes[-5]:
            return "dead_cat"
    return "none"


def short_conviction(short_setup, vol_ratio, dist_resistance, trend):
    """Assign short conviction: High / Medium / Low / None."""
    if short_setup == "none" or trend != "down":
        return "None"

    score = 0
    if short_setup == "breakdown":
        score += 3
    elif short_setup in ("distribution", "dead_cat"):
        score += 2

    if vol_ratio and vol_ratio > 1.5:
        score += 2
    elif vol_ratio and vol_ratio > 1.2:
        score += 1

    # Near resistance is ideal for shorts
    if dist_resistance is not None and dist_resistance < 2:
        score += 2
    elif dist_resistance is not None and dist_resistance < 5:
        score += 1

    if score >= 6:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"


def conviction(setup, vol_ratio, dist_resistance, dist_support, trend):
    """Assign conviction: High / Medium / Low."""
    score = 0
    if setup in ("breakout", "reversal"):
        score += 3
    elif setup == "pullback":
        score += 2
    elif setup == "consolidation":
        score += 1

    if vol_ratio and vol_ratio > 1.5:
        score += 2
    elif vol_ratio and vol_ratio > 1.2:
        score += 1

    if dist_resistance is not None and dist_resistance < 2:
        score += 2
    elif dist_resistance is not None and dist_resistance < 5:
        score += 1

    if trend == "up" and setup in ("breakout", "pullback"):
        score += 1
    if trend == "down" and setup == "reversal":
        score += 1

    if score >= 6:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"

# ═══════════════════════════════════════════════════════════════════════════
#  TREND / MOMENTUM INDICATORS  —  MA50, MA200, 52-WEEK HIGH, RSI   [search: INDICATORS]
#  its score_technical() reads the keys
#  REQUIRES the 1-year fetch window (period="1y") so MA200 / 52w-high have enough bars.
# ═══════════════════════════════════════════════════════════════════════════

def sma(closes, period):
    """Simple moving average of the last `period` closes. None if not enough history."""
    if len(closes) < period:
        return None
    return round(float(np.mean(closes[-period:])), 4)


def rsi(closes, period=14):
    """RSI (0-100) over `period` days. Simple-average variant (SMA of gains/losses) —
    consistent with the SMA-style atr() above, NOT Wilder's smoothing. None if short."""
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0,  deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains[-period:]))
    avg_loss = float(np.mean(losses[-period:]))
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def week52_high(highs):
    """Highest intraday high over the available window (~1 year). None if empty."""
    if len(highs) == 0:
        return None
    return round(float(np.max(highs)), 4)


def process_ticker(ticker, hist):
    """Extract all metrics for one ticker."""
    if hist is None or hist.empty or len(hist) < SR_WINDOW + 5:
        return None

    closes  = hist["Close"].values
    highs   = hist["High"].values
    lows    = hist["Low"].values
    volumes = hist["Volume"].values

    price = round(float(closes[-1]), 4)
    if price < MIN_PRICE:
        return None

    if is_japanese(ticker):
        min_vol = JP_MIN_AVG_VOLUME
        min_atr = JP_MIN_ATR_PCT
    elif is_canadian(ticker):
        min_vol = CA_MIN_AVG_VOLUME
        min_atr = CA_MIN_ATR_PCT
    elif is_brazilian(ticker):
        min_vol = BR_MIN_AVG_VOLUME
        min_atr = BR_MIN_ATR_PCT
    elif is_european(ticker):
        min_vol = EU_MIN_AVG_VOLUME
        min_atr = EU_MIN_ATR_PCT
    else:
        min_vol = MIN_AVG_VOLUME
        min_atr = MIN_ATR_PCT

    # Liquidity filter
    avg_vol = avg_volume(volumes)
    if avg_vol is None or avg_vol < min_vol:
        return None

    # ATR filter — skip names without enough daily range
    atr14 = atr(highs, lows, closes, period=14)
    if atr14 is None:
        return None
    atr_pct = round(atr14 / price * 100, 2)
    if atr_pct < min_atr:
        return None

    prev_close  = round(float(closes[-2]), 4) if len(closes) > 1 else price
    change_pct  = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0

    trend        = trend_direction(closes)
    vol_ratio    = volume_vs_avg(volumes)
    support, resistance = support_resistance(highs, lows)
    dist_sup, dist_res  = distance_from_sr(price, support, resistance)
    setup        = setup_type(closes, volumes, support, resistance)
    conv         = conviction(setup, vol_ratio, dist_res, dist_sup, trend)

    # Long: ATR-based stop below entry, RR_RATIO target above
    stop   = round(price - atr14, 4)
    risk   = price - stop
    target = round(price + risk * RR_RATIO, 4)

    # Short: ATR-based stop above entry, RR_RATIO target below
    s_setup = short_setup_type(closes, volumes, support, resistance)
    s_conv  = short_conviction(s_setup, vol_ratio, dist_res, trend)
    short_stop   = round(price + atr14, 4)
    short_risk   = short_stop - price
    short_target = round(price - short_risk * RR_RATIO, 4)
    
    
    result = {
        "ticker":           ticker,
        "price":            price,
        "change_pct":       change_pct,
        "trend":            trend,
        "volume_ratio":     vol_ratio,
        "avg_volume":       round(avg_vol),
        "atr":              round(atr14, 4),
        "atr_pct":          atr_pct,
        "support":          support,
        "resistance":       resistance,
        "dist_support_pct": dist_sup,
        "dist_resist_pct":  dist_res,
        "setup":            setup,
        "conviction":       conv,
        "entry":            price,
        "stop":             stop,
        "target":           target,
        "ma50":             sma(closes, 50),
        "ma200":            sma(closes, 200),
        "52w_high":         week52_high(highs),
        "rsi":              rsi(closes, 14),
        "rr":               round((target - price) / (price - stop), 2) if price > stop else None,
        # Short-side fields
        "short_setup":      s_setup,
        "short_conviction": s_conv,
    }

    if s_conv in ("High", "Medium"):
        result["short_entry"]  = price
        result["short_stop"]   = short_stop
        result["short_target"] = short_target
        result["short_rr"]     = round((price - short_target) / short_risk, 2) if short_risk > 0 else None

    return result


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"  Market Data Fetcher — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    all_tickers = load_watchlist(WATCHLIST_PATH)
    results = []
    errors  = []

    standard_tickers = [t for t in all_tickers if not is_european(t) and not is_japanese(t) and not is_canadian(t) and not is_brazilian(t)]
    eu_tickers       = [t for t in all_tickers if is_european(t)]
    jp_tickers       = [t for t in all_tickers if is_japanese(t)]
    ca_tickers       = [t for t in all_tickers if is_canadian(t)]
    br_tickers       = [t for t in all_tickers if is_brazilian(t)]

    # ── Standard tickers — batch download ────────────────────────────────────
    batches = [standard_tickers[i:i+BATCH_SIZE] for i in range(0, len(standard_tickers), BATCH_SIZE)]
    total   = len(batches)

    for idx, batch in enumerate(batches, 1):
        print(f"Fetching batch {idx}/{total} ({len(batch)} tickers)...", end=" ", flush=True)

        try:
            raw = yf.download(
                batch,
                period="1y",
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
        except Exception as e:
            print(f"ERROR: {e}")
            errors.extend(batch)
            continue

        for ticker in batch:
            try:
                if len(batch) == 1:
                    hist = raw
                else:
                    hist = raw[ticker] if ticker in raw.columns.get_level_values(0) else None

                result = process_ticker(ticker, hist)
                if result:
                    results.append(result)
            except Exception:
                errors.append(ticker)

        print(f"done. ({len(results)} processed so far)")

        if idx < total:
            time.sleep(BATCH_PAUSE)

    # ── European tickers — batched download ─────────────────────────────────────
    if eu_tickers:
        eu_batches = [eu_tickers[i:i+EU_BATCH_SIZE] for i in range(0, len(eu_tickers), EU_BATCH_SIZE)]
        eu_total   = len(eu_batches)
        print(f"\nFetching {len(eu_tickers)} EU tickers in {eu_total} batches of {EU_BATCH_SIZE}...")

        for idx, batch in enumerate(eu_batches, 1):
            print(f"  EU batch {idx}/{eu_total} ({len(batch)} tickers)...", end=" ", flush=True)
            try:
                raw = yf.download(
                    batch,
                    period="1y",
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=True,
                    progress=False,
                    threads=True,
                )
            except Exception as e:
                print(f"ERROR: {e}")
                errors.extend(batch)
                continue

            for ticker in batch:
                try:
                    if len(batch) == 1:
                        hist = raw
                    else:
                        hist = raw[ticker] if ticker in raw.columns.get_level_values(0) else None
                    result = process_ticker(ticker, hist)
                    if result:
                        results.append(result)
                except Exception:
                    errors.append(ticker)

            print(f"done. ({len(results)} processed so far)")
            if idx < eu_total:
                time.sleep(EU_BATCH_PAUSE)

    # ── Japanese tickers — batched download ──────────────────────────────────
    if jp_tickers:
        jp_batches = [jp_tickers[i:i+JP_BATCH_SIZE] for i in range(0, len(jp_tickers), JP_BATCH_SIZE)]
        jp_total   = len(jp_batches)
        print(f"\nFetching {len(jp_tickers)} JP tickers in {jp_total} batches of {JP_BATCH_SIZE}...")

        for idx, batch in enumerate(jp_batches, 1):
            print(f"  JP batch {idx}/{jp_total} ({len(batch)} tickers)...", end=" ", flush=True)
            try:
                raw = yf.download(
                    batch,
                    period="1y",
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=True,
                    progress=False,
                    threads=True,
                )
            except Exception as e:
                print(f"ERROR: {e}")
                errors.extend(batch)
                continue

            for ticker in batch:
                try:
                    if len(batch) == 1:
                        hist = raw
                    else:
                        hist = raw[ticker] if ticker in raw.columns.get_level_values(0) else None
                    result = process_ticker(ticker, hist)
                    if result:
                        results.append(result)
                except Exception:
                    errors.append(ticker)

            print(f"done. ({len(results)} processed so far)")
            if idx < jp_total:
                time.sleep(JP_BATCH_PAUSE)

    # ── Canadian tickers — batched download ──────────────────────────────────
    if ca_tickers:
        ca_batches = [ca_tickers[i:i+CA_BATCH_SIZE] for i in range(0, len(ca_tickers), CA_BATCH_SIZE)]
        ca_total   = len(ca_batches)
        print(f"\nFetching {len(ca_tickers)} CA tickers in {ca_total} batches of {CA_BATCH_SIZE}...")

        for idx, batch in enumerate(ca_batches, 1):
            print(f"  CA batch {idx}/{ca_total} ({len(batch)} tickers)...", end=" ", flush=True)
            try:
                raw = yf.download(
                    batch,
                    period="1y",
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=True,
                    progress=False,
                    threads=True,
                )
            except Exception as e:
                print(f"ERROR: {e}")
                errors.extend(batch)
                continue

            for ticker in batch:
                try:
                    if len(batch) == 1:
                        hist = raw
                    else:
                        hist = raw[ticker] if ticker in raw.columns.get_level_values(0) else None
                    result = process_ticker(ticker, hist)
                    if result:
                        results.append(result)
                except Exception:
                    errors.append(ticker)

            print(f"done. ({len(results)} processed so far)")
            if idx < ca_total:
                time.sleep(CA_BATCH_PAUSE)

    # ── Brazilian tickers — batched download ─────────────────────────────────
    if br_tickers:
        br_batches = [br_tickers[i:i+BR_BATCH_SIZE] for i in range(0, len(br_tickers), BR_BATCH_SIZE)]
        br_total   = len(br_batches)
        print(f"\nFetching {len(br_tickers)} BR tickers in {br_total} batches of {BR_BATCH_SIZE}...")

        for idx, batch in enumerate(br_batches, 1):
            print(f"  BR batch {idx}/{br_total} ({len(batch)} tickers)...", end=" ", flush=True)
            try:
                raw = yf.download(
                    batch,
                    period="1y",
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=True,
                    progress=False,
                    threads=True,
                )
            except Exception as e:
                print(f"ERROR: {e}")
                errors.extend(batch)
                continue

            for ticker in batch:
                try:
                    if len(batch) == 1:
                        hist = raw
                    else:
                        hist = raw[ticker] if ticker in raw.columns.get_level_values(0) else None
                    result = process_ticker(ticker, hist)
                    if result:
                        results.append(result)
                except Exception:
                    errors.append(ticker)

            print(f"done. ({len(results)} processed so far)")
            if idx < br_total:
                time.sleep(BR_BATCH_PAUSE)

    conviction_order = {"High": 0, "Medium": 1, "Low": 2}
    results.sort(key=lambda x: (conviction_order.get(x["conviction"], 3), x["ticker"]))

    high_conv        = [r for r in results if r["conviction"] == "High"]
    medium_conv      = [r for r in results if r["conviction"] == "Medium"]
    short_high_conv  = [r for r in results if r.get("short_conviction") == "High"]
    short_medium_conv= [r for r in results if r.get("short_conviction") == "Medium"]

    summary = {
        "generated_at":             datetime.now().isoformat(),
        "total_processed":          len(results),
        "total_errors":             len(errors),
        "high_conviction":          len(high_conv),
        "medium_conviction":        len(medium_conv),
        "short_high_conviction":    len(short_high_conv),
        "short_medium_conviction":  len(short_medium_conv),
        "filters": {
            "us_min_avg_volume":  MIN_AVG_VOLUME,
            "us_min_atr_pct":     MIN_ATR_PCT,
            "eu_min_avg_volume":  EU_MIN_AVG_VOLUME,
            "eu_min_atr_pct":     EU_MIN_ATR_PCT,
            "sr_window_days":     SR_WINDOW,
            "rr_ratio":           RR_RATIO,
        },
        "tickers_with_errors": errors[:50],
    }

    output = {"summary": summary, "signals": results}

    os.makedirs("./data", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  DONE")
    print(f"  Standard : {len(standard_tickers)}  |  EU : {len(eu_tickers)}  |  JP : {len(jp_tickers)}  |  CA : {len(ca_tickers)}  |  BR : {len(br_tickers)}")
    print(f"  Processed : {len(results)} tickers  (filtered by vol + ATR)")
    print(f"  LONG  — High: {len(high_conv)}  Medium: {len(medium_conv)}")
    print(f"  SHORT — High: {len(short_high_conv)}  Medium: {len(short_medium_conv)}")
    print(f"  Errors : {len(errors)}")
    print(f"  Output saved to : {OUTPUT_PATH}")
    print(f"{'='*60}")
    print(f"\nTop LONG high-conviction setups:")
    print(f"{'─'*60}")
    for r in high_conv[:10]:
        print(f"  {r['ticker']:<12} {r['setup']:<14} {r['trend']:<10} "
              f"ATR%: {r['atr_pct']}  vol_ratio: {r['volume_ratio']}")

    print(f"\nTop SHORT high-conviction candidates:")
    print(f"{'─'*60}")
    for r in short_high_conv[:10]:
        print(f"  {r['ticker']:<12} {r['short_setup']:<14} {r['trend']:<10} "
              f"ATR%: {r['atr_pct']}  short_stop: {r.get('short_stop','n/a')}  "
              f"short_target: {r.get('short_target','n/a')}")

    print(f"\nNote: short candidates require squeeze pre-check before entry (see RISK.md).")
    print(f"Now run /scan in Claude Code to get full signals.\n")


if __name__ == "__main__":
    main()
