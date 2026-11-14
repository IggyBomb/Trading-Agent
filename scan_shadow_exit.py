#!/usr/bin/env python3
"""
scan_shadow_exit.py — A/B test of the "give-back" exit rule, run as a shadow.

Nothing here changes the real tracker. For every row of the bubble-watch table
(config.SCAN_TRACKING_TABLE) it keeps a twin row in SHADOW_TABLE with two exits
replayed on the same daily bars:

  A = control   stop / target / expected_close_date   (same rules as scan_daily_update.py)
  B = give-back  same as A, plus: once the best high since entry is >= +ARM_PCT %,
                 sell at the close of any day that closes below
                 entry + KEEP_FRACTION * (best high - entry)

Both arms use one engine, so the comparison is fair. Each run replays the full
path from the bars, so a missed night costs nothing: the next run catches up.

The rule is applied to every pick; `extended` (stock up > EXT_OWN20 % in 20 days,
or its sector ETF beating the S&P by > EXT_SECTOR_RS points) is stored so the
report can split extended vs calm. Rows scanned on/after AB_START_DATE are the
real out-of-sample test; earlier rows are backfill.

Usage:
    python scan_shadow_exit.py            # sync + update (run after the 22:45 tracker)
    python scan_shadow_exit.py --report   # print the A/B comparison only
"""

import argparse
import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from config import SCAN_TRACKING_TABLE
from common_utils import keep_awake

log = logging.getLogger("scan_shadow_exit")

DB_PATH      = "data/scan_tracking.db"
SOURCE_TABLE = SCAN_TRACKING_TABLE          # scan_tracking_bubble_watch
SHADOW_TABLE = "scan_shadow_giveback"

# Rule parameters (from the 2026-11-13 backtest on 154 extended picks)
ARM_PCT       = 3.0    # rule switches on once the best high is this % above entry
KEEP_FRACTION = 0.45   # exit on a close below entry + this share of the best gain (was 0.6 until 2026-11-14)
EXT_OWN20     = 8.0    # extended if the stock is up more than this % in 20 sessions
EXT_SECTOR_RS = 4.0    # ...or its sector ETF beat the S&P by more than this many points
AB_START_DATE = "2026-11-13"   # rows scanned from here on = out-of-sample

SECTOR_ETF = {
    "Technology": "XLK", "Energy": "XLE", "Financial Services": "XLF",
    "Healthcare": "XLV", "Consumer Defensive": "XLP", "Consumer Cyclical": "XLY",
    "Industrials": "XLI", "Utilities": "XLU", "Basic Materials": "XLB",
    "Real Estate": "XLRE", "Communication Services": "XLC",
}

CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {SHADOW_TABLE} (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date           TEXT NOT NULL,
    ticker              TEXT NOT NULL,
    final_verdict       TEXT,
    strategy_type       TEXT,
    selection_group     TEXT,
    sector              TEXT,
    entry               REAL,
    stop                REAL,
    target              REAL,
    expected_close_date TEXT,

    -- extended flag, measured on closes BEFORE the scan date (no look-ahead)
    own_20d_pct         REAL,
    sector_rs20_pts     REAL,
    extended            INTEGER,
    out_of_sample       INTEGER,      -- 1 if scan_date >= AB_START_DATE

    -- path facts (shared by both arms, up to the control exit = end of the trade)
    peak_price          REAL,
    peak_date           TEXT,
    armed_date          TEXT,         -- first day the best high reached +ARM_PCT %
    floor_price         REAL,         -- latest give-back floor
    last_close          REAL,
    last_bar_date       TEXT,

    -- arm A: control
    ctrl_outcome        TEXT,         -- TARGET_HIT / STOP_HIT / CLOSE_DATE_HIT
    ctrl_exit_date      TEXT,
    ctrl_exit_price     REAL,
    ctrl_pct            REAL,
    ctrl_r              REAL,

    -- arm B: give-back rule
    rule_outcome        TEXT,         -- TARGET_HIT / STOP_HIT / GIVEBACK_EXIT / CLOSE_DATE_HIT
    rule_exit_date      TEXT,
    rule_exit_price     REAL,
    rule_pct            REAL,
    rule_r              REAL,

    updated_at          TEXT,
    UNIQUE(scan_date, ticker)
)
"""


# ---------------------------------------------------------------- replay engine
def replay(bars, entry, stop, target, close_date, giveback):
    """Walk daily bars (DataFrame: Open/High/Low/Close, DatetimeIndex, sessions
    AFTER the scan date only) and return the exit, or None if still open.

    Same conventions as scan_daily_update.py: target wins if target and stop are
    both touched on one bar; fills are at the level. The give-back check runs on
    the close, after stop/target. Returns dict(outcome, date, price) or None."""
    peak = entry
    for ix, b in bars.iterrows():
        day = ix.strftime("%Y-%m-%d")
        if b["High"] >= target:
            return {"outcome": "TARGET_HIT", "date": day, "price": float(target)}
        if b["Low"] <= stop:
            return {"outcome": "STOP_HIT", "date": day, "price": float(stop)}
        peak = max(peak, float(b["High"]))
        if giveback and (peak / entry - 1) * 100 >= ARM_PCT:
            floor = entry + KEEP_FRACTION * (peak - entry)
            if b["Close"] < floor:
                return {"outcome": "GIVEBACK_EXIT", "date": day, "price": float(b["Close"])}
        if day >= close_date:
            return {"outcome": "CLOSE_DATE_HIT", "date": day, "price": float(b["Close"])}
    return None


def path_facts(bars, entry, until=None):
    """Peak, armed date and current floor over bars up to `until` (inclusive)."""
    if until:
        bars = bars[bars.index <= pd.Timestamp(until)]
    peak, peak_date, armed = entry, None, None
    for ix, b in bars.iterrows():
        if b["High"] > peak:
            peak, peak_date = float(b["High"]), ix.strftime("%Y-%m-%d")
        if armed is None and (peak / entry - 1) * 100 >= ARM_PCT:
            armed = ix.strftime("%Y-%m-%d")
    floor = entry + KEEP_FRACTION * (peak - entry) if armed else None
    return peak, peak_date, armed, floor


# ---------------------------------------------------------------- data helpers
def download(tickers, start):
    """Daily OHLC per ticker as {ticker: DataFrame}; missing tickers are absent."""
    raw = yf.download(sorted(set(tickers)), start=start, progress=False,
                      auto_adjust=True, group_by="ticker", threads=True)
    out = {}
    for t in set(tickers):
        try:
            df = raw[t].dropna(how="all")
        except KeyError:
            continue
        if not df.empty:
            out[t] = df
    return out


def completed_bars(df):
    """Drop today's bar unless it is late enough that every market has closed."""
    now = datetime.now()
    if now.hour < 22:
        df = df[df.index.normalize() < pd.Timestamp(now.date())]
    return df


def extended_flag(px, ticker, sector, scan_date):
    """(own_20d_pct, sector_rs20_pts, extended) from closes strictly before scan_date."""
    def before(t):
        s = px.get(t)
        if s is None:
            return None
        s = s["Close"].dropna()
        s = s[s.index < pd.Timestamp(scan_date)]
        return s if len(s) >= 21 else None

    own, spx = before(ticker), before("^GSPC")
    etf = SECTOR_ETF.get(sector or "")
    sec = before(etf) if etf else None
    own20 = (own.iloc[-1] / own.iloc[-21] - 1) * 100 if own is not None else None
    rs = None
    if sec is not None and spx is not None:
        rs = ((sec.iloc[-1] / sec.iloc[-21]) - (spx.iloc[-1] / spx.iloc[-21])) * 100
    ext = (own20 is not None and own20 > EXT_OWN20) or (rs is not None and rs > EXT_SECTOR_RS)
    r2 = lambda v: round(float(v), 2) if v is not None else None
    return r2(own20), r2(rs), int(ext)


# ---------------------------------------------------------------- main steps
def sync_new_rows(conn):
    """Copy any source rows not yet in the shadow table. Returns how many."""
    cur = conn.execute(f"""
        INSERT OR IGNORE INTO {SHADOW_TABLE}
            (scan_date, ticker, final_verdict, strategy_type, selection_group, sector,
             entry, stop, target, expected_close_date, out_of_sample)
        SELECT scan_date, ticker, final_verdict, strategy_type, selection_group, sector,
               entry, stop, target, expected_close_date,
               CASE WHEN scan_date >= ? THEN 1 ELSE 0 END
        FROM {SOURCE_TABLE}
        WHERE entry IS NOT NULL AND stop IS NOT NULL AND target IS NOT NULL
          AND entry > stop
    """, (AB_START_DATE,))
    return cur.rowcount


def update_open_rows(conn):
    rows = conn.execute(f"""
        SELECT * FROM {SHADOW_TABLE}
        WHERE ctrl_outcome IS NULL OR rule_outcome IS NULL OR extended IS NULL
    """).fetchall()
    if not rows:
        print("  Nothing to update")
        return
    start = (pd.Timestamp(min(r["scan_date"] for r in rows)) - timedelta(days=45)).strftime("%Y-%m-%d")
    tickers = {r["ticker"] for r in rows} | {"^GSPC"} | set(SECTOR_ETF.values())
    print(f"  Rows to update: {len(rows)} ({len(tickers)} tickers incl. ETFs) from {start}")
    px = download(tickers, start)

    closed_a = closed_b = 0
    for r in rows:
        df = px.get(r["ticker"])
        if df is None:
            log.debug("%s: no price data, skipped", r["ticker"])
            continue
        vals = {}
        if r["extended"] is None:
            vals["own_20d_pct"], vals["sector_rs20_pts"], vals["extended"] = \
                extended_flag(px, r["ticker"], r["sector"], r["scan_date"])

        bars = completed_bars(df)
        bars = bars[bars.index > pd.Timestamp(r["scan_date"])]   # tracking starts the next session
        if not bars.empty:
            risk = r["entry"] - r["stop"]
            for arm, gb in (("ctrl", False), ("rule", True)):
                if r[f"{arm}_outcome"] is not None:
                    continue
                ex = replay(bars, r["entry"], r["stop"], r["target"], r["expected_close_date"], gb)
                if ex:
                    vals.update({
                        f"{arm}_outcome":    ex["outcome"],
                        f"{arm}_exit_date":  ex["date"],
                        f"{arm}_exit_price": round(ex["price"], 4),
                        f"{arm}_pct":        round((ex["price"] / r["entry"] - 1) * 100, 2),
                        f"{arm}_r":          round((ex["price"] - r["entry"]) / risk, 3),
                    })
                    closed_a += arm == "ctrl"
                    closed_b += arm == "rule"
            # B never exits after A (same stop/target/date + one extra exit), so A's
            # exit date bounds the trade's life; open rows use all bars to date.
            until = vals.get("ctrl_exit_date") or r["ctrl_exit_date"]
            peak, peak_date, armed, floor = path_facts(bars, r["entry"], until)
            life = bars[bars.index <= pd.Timestamp(until)] if until else bars
            vals.update({
                "peak_price": round(peak, 4), "peak_date": peak_date, "armed_date": armed,
                "floor_price": round(floor, 4) if floor else None,
                "last_close": round(float(life["Close"].iloc[-1]), 4),
                "last_bar_date": life.index[-1].strftime("%Y-%m-%d"),
            })
        vals["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sets = ", ".join(f"{k} = :{k}" for k in vals)
        conn.execute(f"UPDATE {SHADOW_TABLE} SET {sets} WHERE id = :id", {**vals, "id": r["id"]})
    conn.commit()
    print(f"  Closed this run: control {closed_a}, give-back {closed_b}")


def report(conn):
    df = pd.read_sql(f"SELECT * FROM {SHADOW_TABLE}", conn)
    done = df[df.ctrl_outcome.notna() & df.rule_outcome.notna()].copy()
    print(f"\n=== A/B report: {len(df)} rows, {len(done)} closed in both arms ===")
    if done.empty:
        return
    done["diff"] = done.rule_r - done.ctrl_r
    groups = [
        ("OUT-OF-SAMPLE extended",       done[(done.out_of_sample == 1) & (done.extended == 1)]),
        ("OUT-OF-SAMPLE calm",           done[(done.out_of_sample == 1) & (done.extended == 0)]),
        ("OUT-OF-SAMPLE BUY",            done[(done.out_of_sample == 1) & done.final_verdict.str.startswith("BUY", na=False)]),
        ("backfill extended (in-sample)", done[(done.out_of_sample == 0) & (done.extended == 1)]),
    ]
    for name, g in groups:
        g = g[g.selection_group != "BUBBLE_RESCUED"]
        print(f"\n-- {name}: n={len(g)} (bubble-rescued excluded)")
        if g.empty:
            continue
        for arm, label in (("ctrl", "A control  "), ("rule", "B give-back")):
            print(f"   {label} avgR {g[f'{arm}_r'].mean():+.3f}  avg% {g[f'{arm}_pct'].mean():+.2f}"
                  f"  win {100 * (g[f'{arm}_pct'] > 0).mean():3.0f}%  totR {g[f'{arm}_r'].sum():+6.1f}")
        print(f"   B vs A: better {(g['diff'] > 0.01).sum()}, worse {(g['diff'] < -0.01).sum()},"
              f" net {g['diff'].sum():+.1f}R")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--report", action="store_true", help="print the A/B comparison only")
    args = ap.parse_args()

    os.makedirs("logs", exist_ok=True)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler("logs/scan_shadow_exit.log", mode="w", encoding="utf-8")],
    )
    print(f"=== scan_shadow_exit === {datetime.now():%Y-%m-%d %H:%M:%S}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(CREATE_SQL)

    if not args.report:
        added = sync_new_rows(conn)
        conn.commit()
        print(f"  New rows copied from {SOURCE_TABLE}: {added}")
        update_open_rows(conn)
    report(conn)
    conn.close()


if __name__ == "__main__":
    keep_awake()
    main()
