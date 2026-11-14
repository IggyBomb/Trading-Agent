#!/usr/bin/env python3
"""
scan_shadow_breakout.py — A/B test of the breakout confirmation rule, run as a shadow.

Nothing here changes the real tracker. Every WAIT row of the bubble-watch table
whose reason carries a price trigger ("close > $X", "close >= 1% above EUR X",
"close above MA200 $X", "close > MA50") becomes one breakout event in
SHADOW_TABLE. The first close above the level within WINDOW_DAYS calendar days
after the scan is the breakout day. Two entries are replayed on the same bars:

  A = old rule   buy at the close of the first close above the level
  B = new rule   ("Breakout confirmation", 2026-11-11 -- shadow only: removed from
                 final-analyst.md on 2026-11-14, so the live agent runs A. The
                 rule text is in reports/breakout_confirmation_rule_2026-11-11.patch)
                 buy that close only if it is >= CLEAR_PCT % above the level on
                 >= VOL_MULT x the 20-session average volume, or if the previous
                 close was already above the level; otherwise buy the NEXT close
                 if it is still above the level, else no trade (failed breakout).
                 Non-TURNAROUND entries below MA200 also need R:R to MA200 >=
                 MA200_RR (reward = MA200 - entry, risk = entry - stop).

Both arms then exit with the same engine as scan_shadow_exit.py (control arm):
the scan's stop and target, plus the strategy time stop counted from the entry
day. Returns are compared with the S&P 500 over the same days.

Prices are NOT dividend-adjusted, so they match the levels the scan wrote.
Rows scanned on/after AB_START_DATE are out-of-sample; earlier rows are backfill.

Usage:
    python scan_shadow_breakout.py            # sync + update (run after the 22:45 tracker)
    python scan_shadow_breakout.py --report   # print the A/B comparison only
    python scan_shadow_breakout.py --show-parsed   # list the parsed trigger levels
"""

import argparse
import logging
import os
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta

import pandas as pd
import yfinance as yf

from config import SCAN_TRACKING_TABLE
from common_utils import keep_awake
from scan_logger import STRATEGY_TIME_STOP, DEFAULT_TIME_STOP, add_trading_days
from scan_shadow_exit import replay, completed_bars

log = logging.getLogger("scan_shadow_breakout")

DB_PATH      = "data/scan_tracking.db"
SOURCE_TABLE = SCAN_TRACKING_TABLE          # scan_tracking_bubble_watch
SHADOW_TABLE = "scan_shadow_breakout"

# Rule parameters ("Breakout confirmation", 2026-11-11; shadow only since 2026-11-14)
CLEAR_PCT     = 1.0    # close must clear the level by this %
VOL_MULT      = 1.5    # ...on this multiple of the 20-session average volume
MA200_RR      = 1.2    # below MA200 (non-TURNAROUND): min R:R measured to MA200
WINDOW_DAYS   = 14     # calendar days after the scan a WAIT trigger stays live (~10 sessions)
FAIL_SESSIONS = 5      # "failed breakout" = a close back below the level within this many sessions
SANITY_PCT    = 20.0   # a parsed level further than this from the scan price is a mis-parse
SAME_LEVEL_PCT = 1.0   # a repeat WAIT within this % of a live event's level is the same event
AB_START_DATE = "2026-11-11"   # rule designed on data to 2026-11-10: out-of-sample from here
STAKE_EUR     = 1000   # per trade, for the EUR totals in the report

CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {SHADOW_TABLE} (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date           TEXT NOT NULL,
    ticker              TEXT NOT NULL,
    strategy_type       TEXT,
    sector              TEXT,
    selection_group     TEXT,
    scan_price          REAL,         -- the row's entry column (price at the scan)
    stop                REAL,
    target              REAL,
    level               REAL,         -- parsed trigger level
    level_kind          TEXT,         -- PRICE / MA20 / MA50 / MA200
    level_source        TEXT,         -- TEXT (number in the reason) or COMPUTED (MA from prices)
    trigger_text        TEXT,
    window_end          TEXT,
    out_of_sample       INTEGER,

    status              TEXT,         -- PENDING / NO_CROSS / CROSSED / NO_DATA
    cross_date          TEXT,
    cross_close         REAL,
    cross_pct_above     REAL,         -- % the breakout close cleared the level
    cross_vol_ratio     REAL,         -- breakout-day volume / prior 20-session average
    prev_close_above    INTEGER,      -- 1 if the close before the breakout day was already above
    failed_5d           INTEGER,      -- 1 if a close fell back below the level within 5 sessions
    ma200_at_b          REAL,

    -- arm A: old rule (first close above)
    a_entry_date        TEXT,
    a_entry             REAL,
    a_outcome           TEXT,         -- TARGET_HIT / STOP_HIT / CLOSE_DATE_HIT / INVALID
    a_exit_date         TEXT,
    a_exit_price        REAL,
    a_pct               REAL,
    a_r                 REAL,
    a_spx_pct           REAL,

    -- arm B: confirmation rule
    b_decision          TEXT,         -- CONFIRMED_DAY1 / PRIOR_CLOSE_ABOVE / CONFIRMED_DAY2 /
                                      -- REJECTED_FAILED / REJECTED_MA200 / AWAITING_DAY2
    b_entry_date        TEXT,
    b_entry             REAL,
    b_outcome           TEXT,
    b_exit_date         TEXT,
    b_exit_price        REAL,
    b_pct               REAL,
    b_r                 REAL,
    b_spx_pct           REAL,

    done                INTEGER DEFAULT 0,   -- 1 = final, not replayed again
    updated_at          TEXT,
    UNIQUE(scan_date, ticker)
)
"""


# ---------------------------------------------------------------- trigger parser
_NUM = r"(?P<num>\d[\d,]*(?:\.\d+)?)"
TRIGGER_RE = re.compile(
    r"(?P<who>\b[A-Z]{2,5}\s+)?"                      # "SMH close ..." = another ticker's trigger
    r"(?P<paren>\(\s*)?"                              # "(close > ...)" = an aside / stale trigger
    r"close\s+(?:back\s+)?"
    r"(?:>=?|above|over)\s*"
    r"(?:\d+(?:\.\d+)?%\s*above\s+)?"                 # "close >= 1% above ..."
    r"(?:the\s+)?"
    r"(?:(?:20d|20-day|52w)\s+high\s+)?"
    r"(?:(?P<ma>MA(?:200|50|20)(?!\d))\s*)?"
    r"(?:resistance\s+)?"
    r"(?P<cparen>\(\s*)?~?\s*"
    r"(?P<cur>\$|EUR\s?|€|�)?\s*"
    + _NUM +
    r"(?P<pence>p)?"
    r"(?!\d|\.\d|\s*[x%])",
    re.I,
)
TRIGGER_MA_ONLY_RE = re.compile(
    r"(?P<who>\b[A-Z]{2,5}\s+)?(?P<paren>\(\s*)?"
    r"close\s+(?:back\s+)?(?:>=?|above|over)\s*(?:the\s+)?(?P<ma>MA(?:200|50|20)(?!\d))\b",
    re.I,
)


def is_us(ticker):
    return "." not in ticker


def _foreign(m, ticker):
    """True if the match is another instrument's trigger (e.g. 'SMH close >= MA20')
    or an aside in brackets."""
    who = (m.group("who") or "").strip()
    if who and who.upper() == who and who != ticker.split(".")[0]:
        return True
    return bool(m.group("paren"))


def parse_trigger(reason, ticker):
    """-> (level or None, kind, source, snippet). kind PRICE/MA20/MA50/MA200;
    source TEXT, or NEEDS_MA when the MA is named without a usable number."""
    if not reason:
        return None, None, None, None
    text = reason
    i = text.lower().find("trigger:")
    if i >= 0:                       # new-format reasons: only read the trigger clause
        text = text[i:]
    for m in TRIGGER_RE.finditer(text):
        if _foreign(m, ticker):
            continue
        cur = (m.group("cur") or "").strip().upper()
        if is_us(ticker) and cur in ("EUR", "€", "�"):
            continue                 # "(EUR 121.8)" is a conversion of a USD level
        level = float(m.group("num").replace(",", ""))
        kind = (m.group("ma") or "PRICE").upper()
        return level, kind, "TEXT", m.group(0).strip()
    for m in TRIGGER_MA_ONLY_RE.finditer(text):
        if _foreign(m, ticker):
            continue
        return None, m.group("ma").upper(), "NEEDS_MA", m.group(0).strip()
    return None, None, None, None


# ---------------------------------------------------------------- breakout logic
def moving_avg(close, pos, n):
    """n-session simple average of closes ending at integer position pos (inclusive)."""
    if pos + 1 < n:
        return None
    return float(close.iloc[pos + 1 - n: pos + 1].mean())


def decide(df, scan_date, level, window_end, strategy, stop):
    """Find the breakout and both entries. df: full daily history (Open/High/Low/
    Close/Volume, DatetimeIndex) of completed bars. Returns a dict of facts."""
    out = {"status": "PENDING"}
    close, vol = df["Close"], df["Volume"]
    after = [i for i, ix in enumerate(df.index) if pd.Timestamp(scan_date) < ix <= pd.Timestamp(window_end)]
    p = next((i for i in after if close.iloc[i] > level), None)
    if p is None:
        if len(df) and df.index[-1] >= pd.Timestamp(window_end):
            out["status"] = "NO_CROSS"
        return out

    day = lambda i: df.index[i].strftime("%Y-%m-%d")
    prev_above = p > 0 and close.iloc[p - 1] > level
    avg_vol = float(vol.iloc[max(0, p - 20): p].mean()) if p > 0 else 0.0
    vol_ratio = float(vol.iloc[p]) / avg_vol if avg_vol > 0 else None
    clear_pct = (float(close.iloc[p]) / level - 1) * 100
    out.update({
        "status": "CROSSED", "cross_date": day(p), "cross_close": round(float(close.iloc[p]), 4),
        "cross_pct_above": round(clear_pct, 2),
        "cross_vol_ratio": round(vol_ratio, 2) if vol_ratio is not None else None,
        "prev_close_above": int(prev_above),
        "a_entry_date": day(p), "a_entry": round(float(close.iloc[p]), 4),
    })
    later = close.iloc[p + 1: p + 1 + FAIL_SESSIONS]
    if (later < level).any():
        out["failed_5d"] = 1
    elif len(later) == FAIL_SESSIONS:
        out["failed_5d"] = 0

    if prev_above:
        q, decision = p, "PRIOR_CLOSE_ABOVE"
    elif clear_pct >= CLEAR_PCT and vol_ratio is not None and vol_ratio >= VOL_MULT:
        q, decision = p, "CONFIRMED_DAY1"
    elif p + 1 < len(df):
        q, decision = (p + 1, "CONFIRMED_DAY2") if close.iloc[p + 1] > level else (None, "REJECTED_FAILED")
    else:
        q, decision = None, "AWAITING_DAY2"

    if q is not None:
        entry = float(close.iloc[q])
        ma200 = moving_avg(close, q, 200)
        out["ma200_at_b"] = round(ma200, 4) if ma200 else None
        if (strategy or "").upper() != "TURNAROUND" and ma200 and entry < ma200 and entry > stop:
            if (ma200 - entry) / (entry - stop) < MA200_RR:
                q, decision = None, "REJECTED_MA200"
    out["b_decision"] = decision
    if q is not None:
        out["b_entry_date"], out["b_entry"] = day(q), round(float(close.iloc[q]), 4)
    return out


def run_trade(df, entry_date, entry, stop, target, strategy):
    """Exit for an entry at entry_date's close -> dict(outcome,date,price) or None (open)."""
    if not (stop < entry < target):
        return {"outcome": "INVALID", "date": None, "price": None}
    n = STRATEGY_TIME_STOP.get((strategy or "").upper(), DEFAULT_TIME_STOP)
    close_date = add_trading_days(date.fromisoformat(entry_date), n).isoformat()
    bars = df[df.index > pd.Timestamp(entry_date)]
    return replay(bars, entry, stop, target, close_date, giveback=False)


def spx_change(spx, d0, d1):
    """% change of the S&P close from d0 to d1 (as-of, so EU holidays still line up)."""
    if spx is None or d0 is None or d1 is None:
        return None
    s = spx["Close"].dropna()
    a, b = s.asof(pd.Timestamp(d0)), s.asof(pd.Timestamp(d1))
    if pd.isna(a) or pd.isna(b):
        return None
    return round((b / a - 1) * 100, 2)


# ---------------------------------------------------------------- data helpers
def download(tickers, start):
    """Unadjusted daily OHLCV per ticker as {ticker: DataFrame}."""
    raw = yf.download(sorted(set(tickers)), start=start, progress=False,
                      auto_adjust=False, group_by="ticker", threads=True)
    out = {}
    for t in set(tickers):
        try:
            df = raw[t][["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
        except KeyError:
            continue
        if not df.empty:
            out[t] = df
    return out


# ---------------------------------------------------------------- main steps
def sync_new_rows(conn):
    """Turn new WAIT rows with a parsable trigger into events. Returns how many."""
    have = {(r[0], r[1]) for r in conn.execute(f"SELECT scan_date, ticker FROM {SHADOW_TABLE}")}
    events = {}
    for r in conn.execute(f"SELECT ticker, level, window_end FROM {SHADOW_TABLE} WHERE level IS NOT NULL"):
        events.setdefault(r[0], []).append((r[1], r[2]))
    src = conn.execute(f"""
        SELECT scan_date, ticker, strategy_type, sector, selection_group, entry, stop, target,
               final_verdict_reason
        FROM {SOURCE_TABLE}
        WHERE final_verdict = 'WAIT' AND entry IS NOT NULL AND stop IS NOT NULL
          AND target IS NOT NULL AND entry > stop
        ORDER BY scan_date, ticker
    """).fetchall()
    added = 0
    for s in src:
        if (s["scan_date"], s["ticker"]) in have:
            continue
        level, kind, source, snippet = parse_trigger(s["final_verdict_reason"], s["ticker"])
        if kind is None:
            continue
        if level is not None and abs(level / s["entry"] - 1) * 100 > SANITY_PCT:
            log.info("  %s %s: level %.2f too far from %.2f, skipped (%s)",
                     s["scan_date"], s["ticker"], level, s["entry"], snippet)
            continue
        if level is not None and any(abs(level / lv - 1) * 100 <= SAME_LEVEL_PCT and s["scan_date"] <= we
                                     for lv, we in events.get(s["ticker"], [])):
            continue                 # same trigger re-issued while the first one is still live
        window_end = (date.fromisoformat(s["scan_date"]) + timedelta(days=WINDOW_DAYS)).isoformat()
        conn.execute(f"""
            INSERT OR IGNORE INTO {SHADOW_TABLE}
                (scan_date, ticker, strategy_type, sector, selection_group, scan_price, stop, target,
                 level, level_kind, level_source, trigger_text, window_end, out_of_sample, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'PENDING')
        """, (s["scan_date"], s["ticker"], s["strategy_type"], s["sector"], s["selection_group"],
              s["entry"], s["stop"], s["target"], level, kind,
              source, snippet, window_end, int(s["scan_date"] >= AB_START_DATE)))
        if level is not None:
            events.setdefault(s["ticker"], []).append((level, window_end))
        added += 1
    return added


def update_open_rows(conn):
    rows = conn.execute(f"SELECT * FROM {SHADOW_TABLE} WHERE done = 0").fetchall()
    if not rows:
        print("  Nothing to update")
        return
    start = (pd.Timestamp(min(r["scan_date"] for r in rows)) - timedelta(days=320)).strftime("%Y-%m-%d")
    tickers = {r["ticker"] for r in rows} | {"^GSPC"}
    print(f"  Rows to update: {len(rows)} ({len(tickers)} tickers) from {start}")
    px = {t: completed_bars(df) for t, df in download(tickers, start).items()}
    spx = px.get("^GSPC")

    for r in rows:
        df = px.get(r["ticker"])
        vals = {}
        if df is None or df.empty:
            vals["status"] = "NO_DATA"
        else:
            level = r["level"]
            if level is None:        # "close > MA50" with no number: the MA as of the scan close
                hist = df[df.index <= pd.Timestamp(r["scan_date"])]
                n = int(r["level_kind"][2:])
                level = moving_avg(hist["Close"], len(hist) - 1, n) if len(hist) else None
                if level is None:
                    vals["status"] = "NO_DATA"
                else:
                    vals["level"], vals["level_source"] = round(level, 4), "COMPUTED"
            if level is not None:
                f = decide(df, r["scan_date"], level, r["window_end"], r["strategy_type"], r["stop"])
                vals.update(f)
                for arm in ("a", "b"):
                    d0, px0 = f.get(f"{arm}_entry_date"), f.get(f"{arm}_entry")
                    if d0 is None:
                        continue
                    ex = run_trade(df, d0, px0, r["stop"], r["target"], r["strategy_type"])
                    if ex is None:   # still open: mark to the last close, outcome stays NULL
                        last = df.index[-1].strftime("%Y-%m-%d")
                        vals[f"{arm}_pct"] = round((float(df["Close"].iloc[-1]) / px0 - 1) * 100, 2)
                        vals[f"{arm}_spx_pct"] = spx_change(spx, d0, last)
                        continue
                    vals[f"{arm}_outcome"] = ex["outcome"]
                    if ex["outcome"] == "INVALID":
                        continue
                    vals.update({
                        f"{arm}_exit_date": ex["date"], f"{arm}_exit_price": round(ex["price"], 4),
                        f"{arm}_pct": round((ex["price"] / px0 - 1) * 100, 2),
                        f"{arm}_r": round((ex["price"] - px0) / (px0 - r["stop"]), 3),
                        f"{arm}_spx_pct": spx_change(spx, d0, ex["date"]),
                    })
        st, dec = vals.get("status"), vals.get("b_decision")
        a_final = vals.get("a_outcome") is not None
        b_final = dec in ("REJECTED_FAILED", "REJECTED_MA200") or vals.get("b_outcome") is not None
        vals["done"] = int(st == "NO_CROSS" or (st == "CROSSED" and a_final and b_final
                                                  and vals.get("failed_5d") is not None))
        vals["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sets = ", ".join(f"{k} = :{k}" for k in vals)
        conn.execute(f"UPDATE {SHADOW_TABLE} SET {sets} WHERE id = :id", {**vals, "id": r["id"]})
    conn.commit()
    s = conn.execute(f"SELECT status, COUNT(*) FROM {SHADOW_TABLE} GROUP BY 1").fetchall()
    print("  Status: " + ", ".join(f"{a} {b}" for a, b in s))


def _arm_line(label, g, arm):
    g = g[g[f"{arm}_pct"].notna()]
    if g.empty:
        return f"   {label}: no trades"
    xs = g[f"{arm}_pct"] - g[f"{arm}_spx_pct"].fillna(0)
    return (f"   {label}: n={len(g):3d}  avg {g[f'{arm}_pct'].mean():+5.2f}%  vs S&P {xs.mean():+5.2f} pts"
            f"  win {100 * (g[f'{arm}_pct'] > 0).mean():3.0f}%  total EUR {g[f'{arm}_pct'].sum() * STAKE_EUR / 100:+7.0f}"
            f"  (S&P EUR {g[f'{arm}_spx_pct'].fillna(0).sum() * STAKE_EUR / 100:+5.0f})")


def report(conn):
    df = pd.read_sql(f"SELECT * FROM {SHADOW_TABLE}", conn)
    print(f"\n=== Breakout A/B: {len(df)} trigger events ===")
    if df.empty:
        return
    print("  " + ", ".join(f"{k} {v}" for k, v in df.status.value_counts().items()))
    x = df[(df.status == "CROSSED") & (df.selection_group != "BUBBLE_RESCUED")]
    if x.empty:
        return
    print("  B decisions: " + ", ".join(f"{k} {v}" for k, v in x.b_decision.value_counts().items()))
    print("  (open trades are marked to the last close; INVALID = fill outside stop/target)")
    for name, g in (("ALL (backfill + out-of-sample)", x),
                    ("OUT-OF-SAMPLE (scan >= %s)" % AB_START_DATE, x[x.out_of_sample == 1])):
        print(f"\n-- {name}: {len(g)} breakouts")
        if g.empty:
            continue
        print(_arm_line("A old rule ", g, "a"))
        print(_arm_line("B new rule ", g, "b"))
        rej = g[g.b_decision.isin(["REJECTED_FAILED", "REJECTED_MA200"])]
        print(_arm_line("A on trades B rejected", rej, "a"))
        d2 = g[g.b_decision == "CONFIRMED_DAY2"]
        if len(d2):
            print(_arm_line("A on day-2 entries   ", d2, "a"))
            print(_arm_line("B on day-2 entries   ", d2, "b"))
        f = g[g.failed_5d.notna()]
        if len(f):
            for dec, h in f.groupby("b_decision"):
                print(f"   failed within 5 sessions | {dec:18s} {100 * h.failed_5d.mean():3.0f}%  (n={len(h)})")


def show_parsed(conn):
    for r in conn.execute(f"""SELECT scan_date, ticker, scan_price, level, level_kind, level_source,
                                     trigger_text FROM {SHADOW_TABLE} ORDER BY scan_date, ticker"""):
        lv = f"{r[3]:.2f}" if r[3] is not None else "?"
        print(f"{r[0]} {r[1]:9s} px {r[2]:9.2f}  level {lv:>9s} {r[4]:5s} {r[5] or '':8s} | {r[6]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--report", action="store_true", help="print the A/B comparison only")
    ap.add_argument("--show-parsed", action="store_true", help="list parsed trigger levels")
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
                  logging.FileHandler("logs/scan_shadow_breakout.log", mode="w", encoding="utf-8")],
    )
    print(f"=== scan_shadow_breakout === {datetime.now():%Y-%m-%d %H:%M:%S}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(CREATE_SQL)

    if args.show_parsed:
        show_parsed(conn)
    elif not args.report:
        added = sync_new_rows(conn)
        conn.commit()
        print(f"  New trigger events from {SOURCE_TABLE}: {added}")
        update_open_rows(conn)
    report(conn)
    conn.close()


if __name__ == "__main__":
    keep_awake()
    main()
