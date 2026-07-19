#!/usr/bin/env python3
"""
populate_trades.py — One-time import of historical trades from May/June 2026 screenshot.
Run once: python3 populate_trades.py
"""
import json, os
from datetime import datetime

LOGS_PATH    = "./logs/trades.jsonl"
ACCOUNT_SIZE = 50_000

def make_trade(idx, ticker, direction, entry_total, exit_total, qty,
               pnl_eur, pnl_pct, month, entry_price_per=None, exit_price_per=None,
               stop=None, conviction=None, setup=None, notes="", status="closed"):
    entry_p = entry_price_per if entry_price_per else round(entry_total / qty, 4)
    exit_p  = exit_price_per  if exit_price_per  else (round(exit_total / qty, 4) if exit_total else None)
    pos_pct = round(entry_total / ACCOUNT_SIZE * 100, 2)

    # R-multiple
    r_mult = None
    if stop and exit_p and direction == "LONG":
        risk = abs(entry_p - stop)
        if risk > 0:
            r_mult = round((exit_p - entry_p) / risk, 2)

    # Auto-flag violations
    flags = []
    if pos_pct > 2.0:
        flags.append(f"OVERSIZE: position {pos_pct:.1f}% of account (max 2%)")
    if stop is None and status == "closed":
        flags.append("NO_STOP_RECORDED: stop not logged")
    if stop and exit_p and direction == "LONG" and exit_p < stop and pnl_eur < 0:
        flags.append(f"STOP_VIOLATED: exited €{exit_p:.2f}, stop was €{stop:.2f}")
    if pnl_pct < -10:
        flags.append(f"LARGE_LOSS: {pnl_pct:.1f}% — review stop discipline")

    date_str = f"2026-05-{'15' if month == 'MAY' else '30'}"

    return {
        "id":                    f"HIST-{month[:3]}-{idx:03d}",
        "status":                status,
        "ticker":                ticker,
        "direction":             direction,
        "entry_date":            date_str,
        "entry_price":           entry_p,
        "qty":                   qty,
        "position_value":        round(entry_total, 2),
        "position_pct_account":  pos_pct,
        "stop_price":            stop,
        "target_price":          None,
        "rr_planned":            None,
        "conviction":            conviction,
        "setup_type":            setup,
        "exit_date":             date_str if status == "closed" else None,
        "exit_price":            exit_p,
        "pnl_eur":               pnl_eur  if status == "closed" else None,
        "pnl_pct":               pnl_pct  if status == "closed" else None,
        "r_multiple":            r_mult,
        "notes":                 notes,
        "rule_violations":       flags,
        "source":                "historical_import_screenshot_2026-06-12",
    }

# ── Historical trades (from screenshot, net of all commissions) ───────────────

trades = [
    # (idx, ticker, dir, entry_total, exit_total, qty, pnl, pnl_pct, month, entry_pp, exit_pp, stop, conviction, setup, notes, status)
    make_trade(1,  "VIX",          "LONG",  735.20,  743.80,  400,    8.60,   1.17, "MAY", notes="VIX momentum"),
    make_trade(2,  "ROCKET LAB",   "LONG",  665.44,  705.00,   10,   39.56,   5.94, "MAY", setup="momentum"),
    make_trade(3,  "SEA1 OFF",     "LONG", 1210.02, 1183.00,  450,  -27.02,  -2.23, "MAY", notes="loss — stopped out"),
    make_trade(4,  "VIX",          "LONG",  712.28,  718.72,  400,    6.44,   0.90, "MAY"),
    make_trade(5,  "OKLO",         "LONG",  445.23,  494.69,    8,   49.46,  11.11, "MAY", setup="momentum"),
    make_trade(6,  "ROCKET LAB",   "LONG",  660.00,  668.00,   10,    8.00,   1.21, "MAY", setup="momentum"),
    make_trade(7,  "BPM",          "LONG", 2461.00, 2565.00,  100,  104.00,   4.23, "MAY", setup="momentum", notes="Banco BPM"),
    make_trade(8,  "CHINA INDEX",  "LONG", 2460.00, 2526.00,  550,   66.00,   2.68, "MAY"),
    make_trade(9,  "FREEPORT",     "LONG", 1033.00, 1094.00,   20,   61.00,   5.91, "MAY", setup="breakout"),
    make_trade(10, "POET",         "LONG",  516.00,  589.50,   20,   73.50,  14.24, "MAY", setup="momentum", conviction="MEDIUM",
               notes="Track B semis photonics"),
    make_trade(11, "ROCKET SHORT", "SHORT",3345.00, 3377.00,  900,    0.00,   0.00, "MAY",
               status="open", notes="short RKLB — position still open"),
    make_trade(12, "SOFI",         "LONG", 1316.80, 1365.75,  100,   48.95,   3.72, "MAY", setup="reversal",
               notes="triple-tested support bounce"),
    make_trade(13, "ZEST",         "LONG", 1000.00,  950.00,  100,  -50.00,  -5.00, "MAY", notes="stopped out"),
    make_trade(14, "MELI",         "LONG", 2576.85, 2720.90,    2,  144.05,   5.59, "MAY", setup="reversal",
               notes="post-earnings dislocation entry"),
    make_trade(15, "ROCKET LAB",   "LONG", 4000.00,14696.00,    2,10696.00, 267.40, "MAY", setup="momentum",
               notes="RKLB moonshot — space proxy run into SPCX IPO"),
    make_trade(16, "LU-VE",        "LONG", 2606.00, 2673.80,   35,   67.80,   2.60, "MAY", notes="Borsa Italiana"),
    make_trade(17, "NEBIUS",       "LONG",  328.50,  345.00,    2,   16.50,   5.02, "MAY"),
    make_trade(18, "OKLO",         "LONG",  270.00,  310.00,    6,   40.00,  14.81, "MAY", setup="momentum"),
    make_trade(19, "ROCKET SHORT", "SHORT",  988.00, 1002.00,    2,    0.00,   0.00, "MAY",
               status="open", notes="short RKLB — still open"),
    make_trade(20, "MPS",          "LONG", 3398.40, 3450.60,  400,   52.20,   1.54, "MAY",
               notes="Monte dei Paschi — post ex-div"),
    make_trade(21, "OHB",          "LONG", 3592.90, 3559.10,    6,  -33.80,  -0.94, "MAY",
               notes="OHB SE German space — small loss"),
    make_trade(22, "ROCKET SHORT", "SHORT",  861.50,  883.30,  300,    0.00,   0.00, "MAY",
               status="open", notes="short RKLB — still open"),
    make_trade(23, "MODERNA",      "LONG", 1236.50, 1033.00,   25, -203.50, -16.46, "MAY",
               entry_price_per=48.26,
               notes="AVERAGED DOWN — added 35 more at 47.32. No stop honored. See trade 27.",
               stop=None),
    make_trade(24, "FREEPORT",     "LONG", 1023.00, 1115.80,   20,   92.80,   9.07, "MAY", setup="breakout"),
    make_trade(25, "ROCKET SHORT", "SHORT",1614.00, 1403.00,  600,  -33.00,  -2.04, "MAY",
               notes="short RKLB — closed loss"),
    make_trade(26, "INCYTE",       "LONG", 2053.00, 2103.50,   25,   50.50,   2.46, "MAY", setup="consolidation",
               conviction="MEDIUM", notes="INCY oncology"),
    make_trade(27, "MODERNA",      "LONG", 1694.00, 1418.00,   35, -276.00, -16.29, "MAY",
               entry_price_per=47.32,
               notes="SECOND MODERNA — averaged down on trade 23. Combined exposure €2,930 = 5.86% of account. No stop honored.",
               stop=None),
    make_trade(28, "INCYTE",       "LONG",  553.00,  620.00,   10,   67.00,  12.12, "MAY", setup="pullback",
               conviction="MEDIUM"),
    # JUNE
    make_trade(29, "FREEPORT",     "LONG", 1000.00, 1890.00,   20,  890.00,  89.00, "JUN", setup="breakout",
               notes="FCX major breakout — outlier win"),
    make_trade(30, "CRH",          "LONG", 1723.00, 1868.00,   20,  145.00,   8.42, "JUN", setup="breakout"),
    make_trade(31, "POET",         "LONG", 1000.00, 1140.00,   50,  140.00,  14.00, "JUN", setup="momentum",
               conviction="MEDIUM", notes="Track B semis — consistent edge"),
    make_trade(32, "MELI",         "LONG", 1402.50, 1426.70,    1,   24.20,   1.73, "JUN", setup="momentum"),
    make_trade(33, "IAG.L",        "LONG", 1264.00, 1318.00,  250,   54.00,   4.27, "JUN", setup="event",
               notes="IAG.L peace deal catalyst — entered at 408p"),
]

os.makedirs("./logs", exist_ok=True)

# Only write if log doesn't exist or is empty
from pathlib import Path
if Path(LOGS_PATH).exists() and Path(LOGS_PATH).stat().st_size > 0:
    print(f"  ⚠  {LOGS_PATH} already has data. Aborting to prevent duplicates.")
    print(f"     Delete the file and re-run to reimport.")
else:
    with open(LOGS_PATH, "w") as f:
        for t in trades:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"  ✓ Imported {len(trades)} trades → {LOGS_PATH}")
    closed = [t for t in trades if t["status"] == "closed"]
    wins   = [t for t in closed if t["pnl_eur"] and t["pnl_eur"] > 0]
    print(f"    Closed: {len(closed)}  |  Winners: {len(wins)}  |  Open: {len([t for t in trades if t['status']=='open'])}")
    print(f"    Net P&L (closed): €{sum(t['pnl_eur'] for t in closed if t['pnl_eur']):+,.2f}")

if __name__ == "__main__":
    pass
