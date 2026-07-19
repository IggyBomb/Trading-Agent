#!/usr/bin/env python3
"""
trade_logger.py — Trade journal CLI
Logs entries, exits, and generates quick stats. Feeds journal-analyzer.md.

Usage:
  python3 trade_logger.py entry TICKER PRICE --qty N --stop S [--target T] [--conviction H/M/L] [--setup TYPE] [--notes "..."]
  python3 trade_logger.py exit  TICKER PRICE [--notes "..."]
  python3 trade_logger.py show  [--last N] [--ticker TICKER]
  python3 trade_logger.py stats [--month YYYY-MM]
  python3 trade_logger.py open
"""

import json, sys, os, argparse, uuid
from datetime import date, datetime
from pathlib import Path

from config import ACCOUNT_SIZE, TRADES_PATH

LOGS_PATH      = TRADES_PATH
SENTIMENT_PATH = "./data/sentiment_data.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_trades():
    if not Path(LOGS_PATH).exists():
        return []
    with open(LOGS_PATH) as f:
        return [json.loads(l) for l in f if l.strip()]

def save_trade(trade: dict):
    os.makedirs("./logs", exist_ok=True)
    with open(LOGS_PATH, "a") as f:
        f.write(json.dumps(trade, ensure_ascii=False) + "\n")

def trade_id():
    return datetime.now().strftime("%Y%m%d") + "-" + str(uuid.uuid4())[:6].upper()

def r_multiple(entry, stop, exit_price):
    if stop is None or entry == stop:
        return None
    risk = abs(entry - stop)
    move = exit_price - entry
    return round(move / risk, 2)

def position_checks(entry_price, qty, stop_price=None, conviction=None, sd=None):
    flags = []
    pos_value = entry_price * qty
    pos_pct   = pos_value / ACCOUNT_SIZE * 100

    max_pct, tier, reason = dynamic_max_pct(conviction, sd)

    if pos_pct > max_pct:
        flags.append(
            f"OVERSIZE: position {pos_pct:.1f}% of account "
            f"(max {max_pct:.0f}% [{tier}] — {reason})"
        )

    if stop_price is None:
        flags.append("NO_STOP: stop price not set — RISK.md violation")
    elif stop_price:
        risk_per_share = abs(entry_price - stop_price)
        risk_eur       = risk_per_share * qty
        risk_pct       = risk_eur / ACCOUNT_SIZE * 100
        if risk_pct > max_pct:
            flags.append(
                f"RISK_EXCEEDED: risk €{risk_eur:.0f} = {risk_pct:.1f}% of account "
                f"(max {max_pct:.0f}% [{tier}])"
            )

    return flags, max_pct, tier, reason

def load_sentiment_snapshot():
    try:
        with open(SENTIMENT_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def dynamic_max_pct(conviction=None, sd=None):
    """
    Return (max_pct, tier, reason) based on live sentiment data.

    Tiers (conditions checked top-down, first match wins):
      HALF   1%  — F&G >75 (extreme greed/euphoria) or VIX/VSTOXX >30
      MAX    5%  — F&G ≤30 AND composite ≥55 AND EU composite ≥58 AND HIGH conviction
      STRONG 4%  — F&G ≤45 AND composite ≥55 AND HIGH conviction
      GOOD   3%  — F&G ≤50 AND composite ≥48
      NORMAL 2%  — default
    """
    if sd is None:
        sd = {}

    fg_data  = sd.get("cnn_fear_greed") or {}
    fg       = fg_data.get("score")
    comp     = sd.get("composite_score") or 50
    eu_comp  = sd.get("eu_composite_score") or 0
    vix      = (sd.get("vix") or {}).get("value")
    vstoxx   = (sd.get("eu_internals") or {}).get("vstoxx")
    conv     = (conviction or "").upper()

    # HALF — euphoria or high-vol stress
    if (fg is not None and fg > 75):
        return 1.0, "HALF", f"F&G {fg:.0f} — extreme greed / euphoria"
    if (vix and vix > 30):
        return 1.0, "HALF", f"VIX {vix:.1f} — high-volatility stress"
    if (vstoxx and vstoxx > 25):
        return 1.0, "HALF", f"VSTOXX {vstoxx:.1f} — EU high-volatility"

    # MAX — all signals aligned + HIGH conviction
    if (conv == "HIGH" and fg is not None and fg <= 30
            and comp >= 55 and eu_comp >= 58):
        return 5.0, "MAX", f"F&G {fg:.0f} fear + composite {comp:.0f} + EU {eu_comp:.0f} + HIGH conviction"

    # STRONG — fear regime + positive composite + HIGH conviction
    if (conv == "HIGH" and fg is not None and fg <= 45 and comp >= 55):
        return 4.0, "STRONG", f"F&G {fg:.0f} fear + composite {comp:.0f} + HIGH conviction"

    # GOOD — fear/neutral regime + composite not bearish
    if (fg is not None and fg <= 50 and comp >= 48):
        return 3.0, "GOOD", f"F&G {fg:.0f} fear/neutral + composite {comp:.0f}"

    return 2.0, "NORMAL", "default (neutral conditions)"

def fmt_pnl(v):
    return f"€{v:+,.2f}" if v else "—"

def fmt_pct(v):
    return f"{v:+.2f}%" if v else "—"

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_entry(args):
    ticker = args.ticker.upper()
    price  = float(args.price)
    qty    = int(args.qty)
    stop   = float(args.stop) if args.stop else None
    target = float(args.target) if args.target else None
    conv      = args.conviction.upper() if args.conviction else None
    setup     = args.setup if args.setup else None
    notes     = args.notes or ""
    direction = (args.direction or "LONG").upper()
    grade     = args.grade.upper() if args.grade else None
    track     = args.track.upper() if args.track else None

    pos_value  = price * qty
    pos_pct    = pos_value / ACCOUNT_SIZE * 100
    sd         = load_sentiment_snapshot()
    flags, max_pct, tier, size_reason = position_checks(price, qty, stop, conv, sd)

    rr_planned = None
    if stop and target:
        risk    = abs(price - stop)
        reward  = abs(target - price)
        rr_planned = round(reward / risk, 2) if risk else None
        if rr_planned and rr_planned < 1.5:
            flags.append(f"LOW_RR: planned R:R {rr_planned:.2f} below RISK.md minimum 1.5")

    trade = {
        "id":           trade_id(),
        "status":       "open",
        "ticker":       ticker,
        "direction":    direction,
        "entry_date":   str(date.today()),
        "entry_price":  price,
        "qty":          qty,
        "position_value":       round(pos_value, 2),
        "position_pct_account": round(pos_pct, 2),
        "stop_price":   stop,
        "target_price": target,
        "rr_planned":   rr_planned,
        "conviction":   conv,
        "setup_type":   setup,
        "setup_grade":  grade,
        "track":        track,
        "sizing_tier":  tier,
        "exit_date":    None,
        "exit_price":   None,
        "pnl_eur":      None,
        "pnl_pct":      None,
        "r_multiple":   None,
        "notes":        notes,
        "rule_violations": flags,
    }
    save_trade(trade)

    print(f"\n  ✓ ENTRY logged — {ticker} {direction}")
    print(f"    Price:    €{price:.2f}  ×  {qty} shares  =  €{pos_value:,.2f}  ({pos_pct:.1f}% of account)")
    print(f"    Sizing:   [{tier}] max {max_pct:.0f}%  (€{ACCOUNT_SIZE * max_pct / 100:,.0f}) — {size_reason}")
    if stop:
        risk_eur = abs(price - stop) * qty
        print(f"    Stop:     €{stop:.2f}  (risk €{risk_eur:,.2f} = {risk_eur/ACCOUNT_SIZE*100:.2f}% of account)")
    if target:
        print(f"    Target:   €{target:.2f}  (R:R {rr_planned:.2f}:1)")
    if conv:
        print(f"    Conviction: {conv}  |  Setup: {setup or '—'}  |  Grade: {grade or '—'}  |  Track: {track or '—'}")
    if flags:
        print(f"\n  ⚠  RISK FLAGS:")
        for f in flags:
            print(f"     • {f}")
    print()


def cmd_exit(args):
    ticker = args.ticker.upper()
    price  = float(args.price)
    notes  = args.notes or ""

    trades = load_trades()
    # Find the most recent open trade for this ticker
    open_trades = [t for t in trades if t["ticker"] == ticker and t["status"] == "open"]
    if not open_trades:
        print(f"  ✗ No open position found for {ticker}")
        return

    target_trade = open_trades[-1]

    entry  = target_trade["entry_price"]
    qty    = target_trade["qty"]
    stop   = target_trade.get("stop_price")
    direction = target_trade.get("direction", "LONG")

    if direction == "SHORT":
        pnl_per_share = entry - price
    else:
        pnl_per_share = price - entry

    pnl_eur = round(pnl_per_share * qty, 2)
    pnl_pct = round(pnl_per_share / entry * 100, 2)
    r_mult  = r_multiple(entry, stop, price)

    # Check for stop violations
    flags = list(target_trade.get("rule_violations", []))
    if stop:
        if direction == "LONG" and price < stop and pnl_eur < 0:
            flags.append(f"STOP_VIOLATED: exited at €{price:.2f}, stop was €{stop:.2f} — loss exceeded plan")
        elif direction == "SHORT" and price > stop and pnl_eur < 0:
            flags.append(f"STOP_VIOLATED: exited at €{price:.2f}, stop was €{stop:.2f} — loss exceeded plan")

    if r_mult and r_mult < -1.1:
        flags.append(f"RUNAWAY_LOSS: R-multiple {r_mult:.2f} — loss exceeded planned 1R")

    combined_notes = target_trade.get("notes", "")
    if notes:
        combined_notes = (combined_notes + " | " + notes).strip(" | ")

    updated = {**target_trade,
        "status":       "closed",
        "exit_date":    str(date.today()),
        "exit_price":   price,
        "pnl_eur":      pnl_eur,
        "pnl_pct":      pnl_pct,
        "r_multiple":   r_mult,
        "notes":        combined_notes,
        "rule_violations": flags,
    }

    # Rewrite log with updated trade
    all_trades = [updated if t["id"] == target_trade["id"] else t for t in trades]
    os.makedirs("./logs", exist_ok=True)
    with open(LOGS_PATH, "w") as f:
        for t in all_trades:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    result = "WIN" if pnl_eur > 0 else "LOSS"
    r_str  = f"  R: {r_mult:+.2f}" if r_mult else ""
    print(f"\n  ✓ EXIT logged — {ticker} [{result}]")
    print(f"    Entry €{entry:.2f} → Exit €{price:.2f}  |  P&L {fmt_pnl(pnl_eur)} ({pnl_pct:+.2f}%){r_str}")
    if flags:
        print(f"\n  ⚠  VIOLATIONS:")
        for f in [x for x in flags if "STOP_VIOLATED" in x or "RUNAWAY" in x]:
            print(f"     • {f}")
    print()


def cmd_show(args):
    trades = load_trades()
    if args.ticker:
        trades = [t for t in trades if t["ticker"] == args.ticker.upper()]
    n = args.last or 15
    trades = trades[-n:]

    print(f"\n  {'ID':<18}  {'TICKER':<8}  {'STATUS':<7}  {'ENTRY':>8}  {'EXIT':>8}  {'P&L':>10}  {'%':>8}  {'R':>6}  CONV")
    print(f"  {'─'*18}  {'─'*8}  {'─'*7}  {'─'*8}  {'─'*8}  {'─'*10}  {'─'*8}  {'─'*6}  {'─'*6}")
    for t in trades:
        ep = f"€{t['exit_price']:.2f}" if t['exit_price'] else "—"
        pnl = fmt_pnl(t['pnl_eur']) if t['pnl_eur'] is not None else "—"
        pct = fmt_pct(t['pnl_pct']) if t['pnl_pct'] is not None else "—"
        r   = f"{t['r_multiple']:+.2f}" if t.get('r_multiple') is not None else "—"
        v   = "⚠" if t.get('rule_violations') else " "
        print(f"  {t['id']:<18}  {t['ticker']:<8}  {t['status']:<7}  €{t['entry_price']:.2f}  {ep:>8}  {pnl:>10}  {pct:>8}  {r:>6}  {t.get('conviction') or '—'} {v}")
    print()


def cmd_open(args):
    trades  = load_trades()
    open_t  = [t for t in trades if t["status"] == "open"]
    if not open_t:
        print("\n  No open positions.\n")
        return
    print(f"\n  OPEN POSITIONS ({len(open_t)})")
    print(f"  {'TICKER':<10}  {'ENTRY':>8}  {'QTY':>6}  {'VALUE':>10}  {'STOP':>8}  {'TARGET':>8}  {'CONV':<8}  FLAGS")
    print(f"  {'─'*10}  {'─'*8}  {'─'*6}  {'─'*10}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*20}")
    total_exposure = 0
    for t in open_t:
        stop_s   = f"€{t['stop_price']:.2f}"  if t.get('stop_price')  else "NONE ⚠"
        tgt_s    = f"€{t['target_price']:.2f}" if t.get('target_price') else "—"
        val      = t.get('position_value', t['entry_price'] * t['qty'])
        total_exposure += val
        flags    = "⚠ " + " | ".join(t['rule_violations'][:1]) if t.get('rule_violations') else "OK"
        print(f"  {t['ticker']:<10}  €{t['entry_price']:.2f}  {t['qty']:>6}  €{val:>9,.0f}  {stop_s:>8}  {tgt_s:>8}  {t.get('conviction') or '—':<8}  {flags}")
    exp_pct = total_exposure / ACCOUNT_SIZE * 100
    print(f"\n  Total exposure: €{total_exposure:,.0f} ({exp_pct:.1f}% of €{ACCOUNT_SIZE:,} account)\n")


def cmd_stats(args):
    trades  = load_trades()
    closed  = [t for t in trades if t["status"] == "closed" and t["pnl_eur"] is not None]
    if not closed:
        print("\n  No closed trades to analyze.\n")
        return

    if args.month:
        closed = [t for t in closed if (t.get("exit_date") or t.get("entry_date") or "").startswith(args.month)]

    winners = [t for t in closed if t["pnl_eur"] > 0]
    losers  = [t for t in closed if t["pnl_eur"] < 0]
    gross_w = sum(t["pnl_eur"] for t in winners)
    gross_l = abs(sum(t["pnl_eur"] for t in losers))
    pf      = gross_w / gross_l if gross_l else float("inf")

    r_trades = [t for t in closed if t.get("r_multiple") is not None]
    avg_r    = sum(t["r_multiple"] for t in r_trades) / len(r_trades) if r_trades else None

    violations = [v for t in closed for v in (t.get("rule_violations") or [])]

    print(f"\n  {'='*55}")
    print(f"  PERFORMANCE STATS — {len(closed)} closed trades")
    print(f"  {'='*55}")
    print(f"  Win rate:       {len(winners)}/{len(closed)} = {len(winners)/len(closed)*100:.0f}%")
    print(f"  Net P&L:        €{sum(t['pnl_eur'] for t in closed):+,.2f}")
    print(f"  Gross wins:     €{gross_w:,.2f}  |  Gross losses: €{gross_l:,.2f}")
    print(f"  Profit factor:  {pf:.2f}x")
    if winners:
        print(f"  Avg winner:     {sum(t['pnl_pct'] for t in winners)/len(winners):+.2f}%")
    if losers:
        print(f"  Avg loser:      {sum(t['pnl_pct'] for t in losers)/len(losers):+.2f}%")
    if avg_r is not None:
        print(f"  Avg R-multiple: {avg_r:+.2f}R")

    # By conviction
    print(f"\n  BY CONVICTION:")
    for conv in ["HIGH", "MEDIUM", "LOW", None]:
        subset = [t for t in closed if (t.get("conviction") or "").upper() == (conv or "").upper() or
                  (conv is None and not t.get("conviction"))]
        if not subset: continue
        w = [t for t in subset if t["pnl_eur"] > 0]
        label = conv or "UNSET"
        pnl   = sum(t["pnl_eur"] for t in subset)
        print(f"    {label:<8}  {len(w)}/{len(subset)} wins  P&L €{pnl:+,.2f}  "
              f"avg {sum(t['pnl_pct'] for t in subset)/len(subset):+.1f}%")

    # Violations
    if violations:
        from collections import Counter
        vc = Counter(v.split(":")[0] for v in violations)
        print(f"\n  RULE VIOLATIONS ({len(violations)} total):")
        for v, n in vc.most_common():
            print(f"    {v:<22} ×{n}")

    # Best and worst
    best  = max(closed, key=lambda t: t["pnl_eur"])
    worst = min(closed, key=lambda t: t["pnl_eur"])
    print(f"\n  Best trade:   {best['ticker']:<10}  {fmt_pnl(best['pnl_eur'])}  ({best['pnl_pct']:+.2f}%)")
    print(f"  Worst trade:  {worst['ticker']:<10}  {fmt_pnl(worst['pnl_eur'])}  ({worst['pnl_pct']:+.2f}%)")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(prog="trade_logger")
    sub    = parser.add_subparsers(dest="command")

    # entry
    p_entry = sub.add_parser("entry", help="Log a new trade entry")
    p_entry.add_argument("ticker")
    p_entry.add_argument("price", type=float)
    p_entry.add_argument("--qty",        "-q",  type=int,   required=True)
    p_entry.add_argument("--stop",       "-s",  type=float, default=None)
    p_entry.add_argument("--target",     "-t",  type=float, default=None)
    p_entry.add_argument("--conviction", "-c",  default=None, help="H/M/L or HIGH/MEDIUM/LOW")
    p_entry.add_argument("--setup",             default=None, help="breakout/pullback/momentum/reversal/event")
    p_entry.add_argument("--direction",         default="LONG", help="LONG or SHORT")
    p_entry.add_argument("--grade",      "-g",  default=None, help="Setup grade: A/B/C (from technical-analyst)")
    p_entry.add_argument("--track",             default=None, help="Fundamental track: A/B/C (from fundamental-analyst)")
    p_entry.add_argument("--notes",      "-n",  default="")

    # exit
    p_exit = sub.add_parser("exit", help="Log a trade exit")
    p_exit.add_argument("ticker")
    p_exit.add_argument("price", type=float)
    p_exit.add_argument("--notes", "-n", default="")

    # show
    p_show = sub.add_parser("show", help="Show recent trades")
    p_show.add_argument("--last",   type=int, default=15)
    p_show.add_argument("--ticker", default=None)

    # open
    sub.add_parser("open", help="Show open positions")

    # stats
    p_stats = sub.add_parser("stats", help="Performance statistics")
    p_stats.add_argument("--month", default=None, help="Filter by month e.g. 2026-05")

    args = parser.parse_args()

    if args.command == "entry":  cmd_entry(args)
    elif args.command == "exit": cmd_exit(args)
    elif args.command == "show": cmd_show(args)
    elif args.command == "open": cmd_open(args)
    elif args.command == "stats":cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
