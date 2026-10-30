#!/usr/bin/env python3
"""
build_score_panel.py — rebuild the pipeline's DETERMINISTIC price-based scores
historically and attach forward outcomes, producing a ticker-date panel for
regression (Stata .dta + CSV).

WHAT IT REPRODUCES (by importing the live functions, so it stays in sync with
whatever fetch_data.py / watchlist_ranker.py / config.py currently say):
  fetch_data.py      : trend, volume ratio, S/R, setup, conviction, ATR, stop,
                       target, rr, target_atr, MA50/MA200, RSI, 52w high,
                       liquidity + ATR% tradability filters
  watchlist_ranker.py: score_technical(), volatility(), composite()

GAP DETECTOR: gap_event / gap_days_ago / gap_up / gap_size_atr columns come
from fetch_data.detect_gap(). Historical earnings dates are not fetched, so all
panel gaps are treated as "unverified" (scored normally), the same as live.

WHAT IT DELIBERATELY LEAVES OUT (cannot be rebuilt point-in-time):
  - fund / alt scores   -> composite_px uses composite()'s neutral 50 for both
  - earnings, short %, regime_penalty (sector rotation / Minsky / bubble watch)
  - live_price() / backfill_daily(): history uses the daily close as "price"
  - every LLM agent step (risk-manager, final-analyst, ...)
So composite_px tests the RANKER'S PRICE LAYER, not the full strategy.

KNOWN BIASES — read before interpreting results:
  - Survivorship: the universe is TODAY's watchlist.txt; names delisted since
    the start date are missing -> forward returns are biased upward.
  - auto_adjust=True prices (same as fetch_data.py) -> splits/dividends
    back-adjusted; fine for returns, but the price filters (MIN_PRICE) use
    adjusted, not as-traded, prices in early years.
  - EU volume from yfinance is unreliable (see BUG2 notes) -> region flag lets
    you split or drop.

Usage (run from the repo root, in your normal venv):
  python3 research/build_score_panel.py                 # download + build
  python3 research/build_score_panel.py --skip-download # rebuild from cache
  python3 research/build_score_panel.py --start 2015-01-01 --step 1

Outputs (data/ is gitignored):
  data/backtest/prices.csv.gz      raw OHLCV cache (long format)
  data/backtest/score_panel.csv    the panel
  data/backtest/score_panel.dta    same, for Stata
"""

import argparse, sys, time, logging
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    MIN_PRICE, MIN_AVG_VOLUME, EU_MIN_AVG_VOLUME, JP_MIN_AVG_VOLUME,
    CA_MIN_AVG_VOLUME, BR_MIN_AVG_VOLUME,
    MIN_ATR_PCT, EU_MIN_ATR_PCT, JP_MIN_ATR_PCT, CA_MIN_ATR_PCT, BR_MIN_ATR_PCT,
    SR_WINDOW, ATR_STOP_MULT, RR_RATIO, BATCH_SIZE, BATCH_PAUSE,
    WATCHLIST_PATH, DATA_DIR,
)
import fetch_data as fd          # noqa: E402  (pure scoring functions)
import watchlist_ranker as wr    # noqa: E402

log = logging.getLogger("score_panel")

OUT_DIR      = DATA_DIR / "backtest"
PRICES_PATH  = OUT_DIR / "prices.csv.gz"
PANEL_CSV    = OUT_DIR / "score_panel.csv"
PANEL_DTA    = OUT_DIR / "score_panel.dta"

WINDOW       = 252          # fetch_data pulls period="1y" -> ~252 bars per scan
HORIZONS     = (5, 20, 60)  # forward-return horizons, trading days
TRADE_MAX    = 60           # max holding period for the stop/target simulation
CONV_NUM     = {"Low": 0, "Medium": 1, "High": 2}


# ── region / thresholds (mirrors process_ticker) ────────────────────────────
def region_of(t):
    if fd.is_japanese(t):  return "JP"
    if fd.is_canadian(t):  return "CA"
    if fd.is_brazilian(t): return "BR"
    if fd.is_european(t):  return "EU"
    return "US"

THRESH = {
    "US": (MIN_AVG_VOLUME,    MIN_ATR_PCT),
    "EU": (EU_MIN_AVG_VOLUME, EU_MIN_ATR_PCT),
    "JP": (JP_MIN_AVG_VOLUME, JP_MIN_ATR_PCT),
    "CA": (CA_MIN_AVG_VOLUME, CA_MIN_ATR_PCT),
    "BR": (BR_MIN_AVG_VOLUME, BR_MIN_ATR_PCT),
}


# ── download ────────────────────────────────────────────────────────────────
def download(tickers, start):
    import yfinance as yf
    frames, failed = [], []
    batches = [tickers[i:i + BATCH_SIZE] for i in range(0, len(tickers), BATCH_SIZE)]
    for n, batch in enumerate(batches, 1):
        log.info(f"batch {n}/{len(batches)} ({len(batch)} tickers)")
        try:
            raw = yf.download(batch, start=start, interval="1d", group_by="ticker",
                              auto_adjust=True, progress=False, threads=True)
        except Exception as e:
            log.error(f"batch {n} failed: {e}")
            failed += batch
            continue
        for t in batch:
            try:
                h = raw if len(batch) == 1 else raw[t]
            except KeyError:
                failed.append(t); continue
            h = h.dropna(subset=["Close"])
            if h.empty:
                failed.append(t); continue
            h = h[["Open", "High", "Low", "Close", "Volume"]].copy()
            h["ticker"] = t
            frames.append(h.reset_index().rename(columns={"Date": "date", "index": "date"}))
        if n < len(batches):
            time.sleep(BATCH_PAUSE)
    if failed:
        log.warning(f"{len(failed)} tickers returned no data: {failed[:20]}{' ...' if len(failed) > 20 else ''}")
    df = pd.concat(frames, ignore_index=True)
    df.columns = [c.lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    return df


# ── per-ticker scoring at one point in time (mirrors process_ticker) ────────
def score_at(ticker, region, o, h, l, c, v):
    """Arrays are the 1y window ENDING at the scan date (inclusive)."""
    if len(c) < SR_WINDOW + 5:
        return None
    price = round(float(c[-1]), 4)
    min_vol, min_atr = THRESH[region]
    avg_vol = fd.avg_volume(v)
    atr14   = fd.atr(h, l, c, period=14)
    if avg_vol is None or atr14 is None or not np.isfinite(price) or price <= 0:
        return None
    atr_pct = round(atr14 / price * 100, 3)

    prev_close = round(float(c[-2]), 4)
    trend      = fd.trend_direction(c)
    vol_ratio  = fd.volume_vs_avg(v)
    support, resistance = fd.support_resistance(h, l)
    dist_sup, dist_res  = fd.distance_from_sr(price, support, resistance)
    setup      = fd.setup_type(c, v, support, resistance)
    bounce     = dist_sup is not None and 0 <= dist_sup < 2 and price > prev_close
    # Gap detector (2026-10-30): price-only here. Live, only gaps confirmed as
    # EARNINGS change scoring; historical earnings dates aren't fetched, so every
    # gap in the panel is "unverified" -> scored normally, exactly as live does
    # for unverified gaps. The columns let the regression compare gap vs no-gap.
    gap        = fd.detect_gap(o, h, l, c, v)
    conv       = fd.conviction(setup, vol_ratio, dist_res, dist_sup, trend, bounce)

    stop   = price - ATR_STOP_MULT * atr14
    base_h = resistance - support
    target = (resistance + base_h) if setup == "breakout" else resistance
    rr     = (target - price) / (price - stop) if price > stop else None
    target_atr = (target - price) / atr14

    t = {
        "price": price, "conviction": conv, "ma50": fd.sma(c, 50),
        "ma200": fd.sma(c, 200), "rsi": fd.rsi(c, 14),
        "52w_high": fd.week52_high(h), "volume_ratio": vol_ratio,
        "atr_pct": atr_pct,
    }
    tech  = wr.score_technical(t)
    volsc = wr.volatility(ticker, t)
    comp  = wr.composite(tech, None, None, None, None, volsc, 0.0)

    pass_liq   = avg_vol >= min_vol
    pass_atr   = atr_pct >= min_atr
    pass_price = price >= MIN_PRICE
    return {
        "price": price, "avg_volume": avg_vol, "atr": atr14, "atr_pct": atr_pct,
        "trend": trend, "volume_ratio": vol_ratio, "support": support,
        "resistance": resistance, "dist_support_pct": dist_sup,
        "dist_resist_pct": dist_res, "setup": setup, "support_bounce": int(bounce),
        "conviction": conv, "conv_num": CONV_NUM[conv],
        "ma50": t["ma50"], "ma200": t["ma200"], "rsi": t["rsi"],
        "high52w": t["52w_high"], "stop": stop, "target": target,
        "rr": rr, "target_atr": target_atr,
        "pass_rr": int(target_atr >= RR_RATIO * ATR_STOP_MULT),
        "tech_score": tech, "vol_score": volsc, "composite_px": comp,
        "pass_liquidity": int(pass_liq), "pass_atr": int(pass_atr),
        "tradable": int(pass_liq and pass_atr and pass_price),
        "gap_event": int(gap is not None),
        "gap_days_ago": gap["days_ago"] if gap else np.nan,
        "gap_up": (1 if gap["direction"] == "up" else 0) if gap else np.nan,
        "gap_size_atr": gap["size_atr"] if gap else np.nan,
    }


def trade_outcome(i, price, stop, target, h, l, c):
    """Walk forward from bar i+1. Stop checked before target on the same bar
    (conservative). Returns (outcome, bars, r_multiple)."""
    risk = price - stop
    end = min(i + TRADE_MAX, len(c) - 1)
    if end <= i or risk <= 0:
        return (np.nan, np.nan, np.nan)
    for j in range(i + 1, end + 1):
        if l[j] <= stop:
            return (-1, j - i, -1.0)
        if h[j] >= target:
            return (1, j - i, (target - price) / risk)
    if end - i < TRADE_MAX:          # ran out of data before the time stop
        return (np.nan, np.nan, np.nan)
    return (0, TRADE_MAX, (c[end] - price) / risk)


def build_ticker(ticker, g, step, first_date):
    g = g.sort_values("date")
    dates = g["date"].values
    o, h, l, c, v = (g[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close", "volume"))
    region = region_of(ticker)
    rows = []
    # first scan once a full 1y window exists; sample every `step` bars
    for i in range(WINDOW - 1, len(c), step):
        if dates[i] < first_date:
            continue
        s = slice(i - WINDOW + 1, i + 1)
        r = score_at(ticker, region, o[s], h[s], l[s], c[s], v[s])
        if r is None:
            continue
        r["ticker"], r["region"], r["date"] = ticker, region, dates[i]
        for H in HORIZONS:
            r[f"fwd_ret_{H}"] = c[i + H] / c[i] - 1 if i + H < len(c) else np.nan
        out, bars, rmult = trade_outcome(i, r["price"], r["stop"], r["target"], h, l, c)
        r["trade_outcome"], r["trade_bars"], r["trade_r"] = out, bars, rmult
        rows.append(r)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="2016-01-01", help="download start (first scores ~1y later)")
    ap.add_argument("--step", type=int, default=5, help="score every N trading days (5 = weekly)")
    ap.add_argument("--skip-download", action="store_true", help="reuse data/backtest/prices.csv.gz")
    ap.add_argument("--prices", default=str(PRICES_PATH), help="price cache path")
    ap.add_argument("--insample-end", default="2022-12-31", help="last date flagged insample=1")
    ap.add_argument("--tickers", nargs="*", help="override watchlist (testing)")
    ap.add_argument("--out-dir", default=str(OUT_DIR), help="where the panel files go")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    panel_csv, panel_dta = out / PANEL_CSV.name, out / PANEL_DTA.name

    if args.skip_download:
        prices = pd.read_csv(args.prices, parse_dates=["date"])
        log.info(f"loaded cache: {prices['ticker'].nunique()} tickers, {len(prices):,} rows")
    else:
        tickers = args.tickers or fd.load_watchlist(WATCHLIST_PATH)
        log.info(f"downloading {len(tickers)} tickers from {args.start} ...")
        prices = download(tickers, args.start)
        prices.to_csv(args.prices, index=False, compression="gzip")
        log.info(f"cached {prices['ticker'].nunique()} tickers -> {args.prices}")

    first_date = np.datetime64(pd.Timestamp(args.start) + pd.Timedelta(days=1))
    rows, groups = [], prices.groupby("ticker", sort=True)
    t0 = time.time()
    for n, (tk, g) in enumerate(groups, 1):
        rows += build_ticker(tk, g, args.step, first_date)
        if n % 50 == 0:
            log.info(f"scored {n}/{groups.ngroups} tickers ({time.time() - t0:.0f}s, {len(rows):,} rows)")

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])

    # cross-sectional excess returns: minus the region-date mean of TRADABLE names
    for H in HORIZONS:
        col = f"fwd_ret_{H}"
        mean = df[df["tradable"] == 1].groupby(["region", "date"])[col].mean().rename("_m")
        df = df.join(mean, on=["region", "date"])
        df[f"xret_{H}"] = df[col] - df["_m"]
        df = df.drop(columns="_m")
    # winsorised copies (1/99 pct by date) — stops a handful of 10-baggers driving OLS
    for H in HORIZONS:
        col = f"xret_{H}"
        q = df.groupby("date")[col].transform
        df[f"{col}_w"] = df[col].clip(q(lambda s: s.quantile(.01)), q(lambda s: s.quantile(.99)))

    df["target_hit"] = np.where(df["trade_outcome"].isna(), np.nan, (df["trade_outcome"] == 1).astype(float))
    df["insample"]   = (df["date"] <= pd.Timestamp(args.insample_end)).astype(int)
    df["year"]       = df["date"].dt.year

    lead = ["ticker", "region", "date", "year", "insample", "tradable"]
    df = df[lead + [c for c in df.columns if c not in lead]].sort_values(["ticker", "date"])

    df.to_csv(panel_csv, index=False)
    stata = df.copy()
    for col in stata.select_dtypes("bool").columns:
        stata[col] = stata[col].astype(int)
    stata.to_stata(panel_dta, write_index=False, convert_dates={"date": "td"}, version=118,
                   data_label="Trading-Agent price-layer score panel")
    log.info(f"panel: {len(df):,} rows, {df['ticker'].nunique()} tickers, "
             f"{df['date'].min().date()} -> {df['date'].max().date()}")
    log.info(f"wrote {panel_csv} and {panel_dta}")

    # quick sanity print: does conviction line up with anything?
    t = df[df["tradable"] == 1]
    print("\nTradable rows by conviction (means):")
    print(t.groupby("conviction")[["xret_20", "xret_60", "target_hit", "trade_r"]]
            .agg(["mean", "count"]).round(4).to_string())


if __name__ == "__main__":
    main()
