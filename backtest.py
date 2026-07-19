#!/usr/bin/env python3
"""
backtest.py — Trade validation and setup simulation backtester

Modes:
  validate              — replay every closed trade: was stop hit or target hit first?
  simulate TICKER DATE ENTRY STOP TARGET  — simulate a hypothetical trade from DATE
  summary               — statistical breakdown of validate results

Usage:
  python3 backtest.py validate
  python3 backtest.py simulate RKLB 2026-05-01 100.00 90.00 120.00
  python3 backtest.py summary
"""

import json, os, sys, argparse
from datetime import datetime, date, timedelta
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    os.system(f"{sys.executable} -m pip install yfinance pandas --quiet")
    import yfinance as yf
    import pandas as pd

LOGS_PATH   = "./logs/trades.jsonl"
OUTPUT_PATH = "./data/backtest_results.json"


def load_trades() -> list:
    if not Path(LOGS_PATH).exists():
        return []
    with open(LOGS_PATH) as f:
        return [json.loads(l) for l in f if l.strip()]


def get_history(ticker: str, start: str, end: str) -> pd.DataFrame | None:
    try:
        hist = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.droplevel(1)
        if "High" not in hist.columns or len(hist) < 2:
            return None
        return hist
    except Exception:
        return None


def simulate_trade(ticker: str, entry_date: str, entry: float, stop: float,
                   target: float, direction: str = "LONG", max_days: int = 60) -> dict:
    end_dt  = (datetime.strptime(entry_date, "%Y-%m-%d") + timedelta(days=max_days + 5)).strftime("%Y-%m-%d")
    hist    = get_history(ticker, entry_date, end_dt)

    if hist is None or hist.empty:
        return {"outcome": "NO_DATA", "ticker": ticker, "entry_date": entry_date}

    risk     = abs(entry - stop)
    reward   = abs(target - entry)
    planned_rr = round(reward / risk, 2) if risk else None

    result = {
        "ticker":      ticker,
        "entry_date":  entry_date,
        "entry":       entry,
        "stop":        stop,
        "target":      target,
        "direction":   direction,
        "planned_rr":  planned_rr,
        "outcome":     "OPEN",
        "exit_date":   None,
        "exit_price":  None,
        "days_held":   None,
        "r_achieved":  None,
        "max_favorable_pct": None,
        "max_adverse_pct":   None,
    }

    max_fav = 0.0
    max_adv = 0.0

    for i, (idx, row) in enumerate(hist.iterrows()):
        high  = float(row["High"])
        low   = float(row["Low"])
        close = float(row["Close"])
        day   = idx.strftime("%Y-%m-%d")

        if direction == "LONG":
            fav = (high  - entry) / entry * 100
            adv = (entry - low)   / entry * 100
            stop_hit   = low  <= stop
            target_hit = high >= target
        else:
            fav = (entry - low)  / entry * 100
            adv = (high - entry) / entry * 100
            stop_hit   = high >= stop
            target_hit = low  <= target

        max_fav = max(max_fav, fav)
        max_adv = max(max_adv, adv)

        if target_hit and stop_hit:
            # Both in same candle — use open to guess order
            result.update({"outcome": "TARGET_HIT", "exit_date": day,
                           "exit_price": target, "days_held": i + 1})
            break
        elif target_hit:
            result.update({"outcome": "TARGET_HIT", "exit_date": day,
                           "exit_price": target, "days_held": i + 1})
            break
        elif stop_hit:
            result.update({"outcome": "STOP_HIT", "exit_date": day,
                           "exit_price": stop, "days_held": i + 1})
            break

        if i + 1 >= max_days:
            result.update({"outcome": "TIME_STOP", "exit_date": day,
                           "exit_price": close, "days_held": i + 1})
            break

    if result["outcome"] in ("TARGET_HIT", "STOP_HIT", "TIME_STOP") and risk:
        exit_p  = result["exit_price"]
        move    = (exit_p - entry) if direction == "LONG" else (entry - exit_p)
        result["r_achieved"] = round(move / risk, 2)

    result["max_favorable_pct"] = round(max_fav, 2)
    result["max_adverse_pct"]   = round(max_adv, 2)
    return result


def cmd_validate(args):
    trades  = load_trades()
    closed  = [t for t in trades if t.get("status") == "closed"
               and t.get("stop_price") and t.get("target_price")
               and t.get("entry_date") and t.get("entry_price")]

    if not closed:
        print("\n  No closed trades with full stop/target data to validate.\n")
        return []

    print(f"\n  Validating {len(closed)} closed trades with stop + target logged...")
    results = []

    for t in closed:
        ticker = t["ticker"]
        print(f"  → {ticker:<12}", end="", flush=True)
        r = simulate_trade(
            ticker     = ticker,
            entry_date = t["entry_date"],
            entry      = t["entry_price"],
            stop       = t["stop_price"],
            target     = t["target_price"],
            direction  = t.get("direction", "LONG"),
        )
        r["actual_pnl_eur"]  = t.get("pnl_eur")
        r["actual_outcome"]  = "WIN" if (t.get("pnl_eur") or 0) > 0 else "LOSS"
        r["trade_id"]        = t.get("id")
        results.append(r)
        print(f"  {r['outcome']:<14}  "
              f"R planned {r.get('planned_rr') or '—'}  achieved {r.get('r_achieved') or '—'}")

    Path("./data").mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved → {OUTPUT_PATH}")
    return results


def cmd_simulate(args):
    if len(args.params) < 5:
        print("  Usage: python3 backtest.py simulate TICKER DATE ENTRY STOP TARGET")
        return

    ticker, entry_date, entry, stop, target = (args.params[0].upper(),
        args.params[1], float(args.params[2]), float(args.params[3]), float(args.params[4]))

    direction = args.params[5].upper() if len(args.params) > 5 else "LONG"

    print(f"\n  Simulating {ticker} from {entry_date}  entry {entry}  stop {stop}  target {target}  {direction}")
    r = simulate_trade(ticker, entry_date, entry, stop, target, direction)

    rr = r.get("planned_rr") or "—"
    print(f"\n  Outcome:     {r['outcome']}")
    print(f"  Exit date:   {r.get('exit_date') or '—'}  (day {r.get('days_held') or '—'})")
    print(f"  Exit price:  {r.get('exit_price') or '—'}")
    print(f"  Planned R:R: {rr}   |   Achieved R: {r.get('r_achieved') or '—'}")
    print(f"  Max favorable move: +{r.get('max_favorable_pct', 0):.1f}%")
    print(f"  Max adverse move:   -{r.get('max_adverse_pct',  0):.1f}%")
    if r["outcome"] == "NO_DATA":
        print(f"  ⚠ No price data found for {ticker} from {entry_date}")
    print()


def cmd_summary(args):
    if not Path(OUTPUT_PATH).exists():
        print("\n  No backtest results found. Run: python3 backtest.py validate\n")
        return

    with open(OUTPUT_PATH) as f:
        results = json.load(f)

    valid = [r for r in results if r.get("outcome") != "NO_DATA"]
    if not valid:
        print("\n  No valid backtest results.\n")
        return

    target_hits = [r for r in valid if r["outcome"] == "TARGET_HIT"]
    stop_hits   = [r for r in valid if r["outcome"] == "STOP_HIT"]
    time_stops  = [r for r in valid if r["outcome"] == "TIME_STOP"]

    r_achieved  = [r["r_achieved"] for r in valid if r.get("r_achieved") is not None]

    print(f"\n  {'='*58}")
    print(f"  BACKTEST SUMMARY — {len(valid)} trades validated")
    print(f"  {'='*58}")
    print(f"  Target hit:  {len(target_hits)}/{len(valid)} ({len(target_hits)/len(valid)*100:.0f}%)")
    print(f"  Stop hit:    {len(stop_hits)}/{len(valid)} ({len(stop_hits)/len(valid)*100:.0f}%)")
    print(f"  Time stop:   {len(time_stops)}/{len(valid)} ({len(time_stops)/len(valid)*100:.0f}%)")

    if r_achieved:
        avg_r = sum(r_achieved) / len(r_achieved)
        pos_r = [r for r in r_achieved if r > 0]
        neg_r = [r for r in r_achieved if r < 0]
        print(f"\n  Avg R achieved:  {avg_r:+.2f}")
        if pos_r: print(f"  Avg winner R:    {sum(pos_r)/len(pos_r):+.2f}")
        if neg_r: print(f"  Avg loser R:     {sum(neg_r)/len(neg_r):+.2f}")

    # Divergence: actual outcome vs simulated
    matched   = sum(1 for r in valid if
                    (r.get("actual_outcome") == "WIN"  and r["outcome"] == "TARGET_HIT") or
                    (r.get("actual_outcome") == "LOSS" and r["outcome"] == "STOP_HIT"))
    divergent = [r for r in valid if
                 r.get("actual_outcome") and
                 (r.get("actual_outcome") == "WIN"  and r["outcome"] != "TARGET_HIT") or
                 (r.get("actual_outcome") == "LOSS" and r["outcome"] != "STOP_HIT")]

    if valid:
        print(f"\n  Actual vs Simulated match rate: {matched}/{len([r for r in valid if r.get('actual_outcome')])} trades")
    if divergent:
        print(f"  Divergent trades (execution differs from plan): {len(divergent)}")
        for r in divergent[:5]:
            print(f"    {r['ticker']:<10} actual={r.get('actual_outcome')}  simulated={r['outcome']}")

    print()


def main():
    parser = argparse.ArgumentParser(prog="backtest")
    sub    = parser.add_subparsers(dest="command")

    sub.add_parser("validate", help="Validate all closed trades with stop+target against historical data")
    p_sim = sub.add_parser("simulate", help="Simulate a hypothetical trade")
    p_sim.add_argument("params", nargs="+", help="TICKER DATE ENTRY STOP TARGET [LONG|SHORT]")
    sub.add_parser("summary",  help="Summarize backtest results from last validate run")

    args = parser.parse_args()
    if args.command == "validate":  cmd_validate(args)
    elif args.command == "simulate": cmd_simulate(args)
    elif args.command == "summary":  cmd_summary(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
