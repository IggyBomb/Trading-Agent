#!/usr/bin/env python3
"""
rescue_bw.py — Rescued_BW: a second, autonomous rank alongside watchlist_ranker.py

Runs after watchlist_ranker.py in the pipeline, as its own separate step with
its own output file (data/rescued_bw.json) -- deliberately not a section glued
onto watchlist_ranker.py's own run or output. It builds the exact same scored
universe (via watchlist_ranker.build_scored_universe(), imported rather than
reimplemented, so both pipelines score identically by construction) and then
asks a different question of it: not "who's in the top N", but "who's outside
the top N on composite score alone, whose sector/industry bubble watch says a
rally may be starting before the score caught up?"

Mirrors watchlist_ranker.regime_penalty()'s bubble-watch gate from the other
side: that function penalizes a sector once Kindleberger Stage 4 is CONFIRMED
(too late, distribution phase). This script rescues the opposite case -- Stage
2 (Boom), Stage 3 (Euphoria), or Stage 4 not yet confirmed -- as names worth a
second look even though their composite score didn't make the main cut.
Confirmed Stage 4 is never rescued here: same signal, already handled as a
penalty elsewhere, not an opportunity.

Usage:
  python3 rescue_bw.py              — full universe
  python3 rescue_bw.py --eu         — EU tickers only
  python3 rescue_bw.py --us         — US tickers only
"""

import json, argparse
from datetime import datetime
from pathlib import Path

from config import RESCUE_BW_TOP_CUTOFF, RESCUED_BW_PATH
from watchlist_ranker import build_scored_universe, resolve_bubble_etf

OUTPUT_PATH = RESCUED_BW_PATH


def main():
    parser = argparse.ArgumentParser(prog="rescue_bw")
    parser.add_argument("--eu", action="store_true", help="EU tickers only")
    parser.add_argument("--us", action="store_true", help="US tickers only")
    args = parser.parse_args()

    result = build_scored_universe(args)
    if result is None:
        print("\n  market_data.json not found — run fetch_data.py first.\n")
        return
    scored, sector_rotation_raw, bubble_watch_raw = result

    # Fixed cutoff (config.py), independent of whatever --top a
    # watchlist_ranker.py run used -- Rescued_BW always means the same thing.
    full_sorted = sorted(scored, key=lambda x: -x["score"])
    rescue_pool = full_sorted[RESCUE_BW_TOP_CUTOFF:]

    rescued = []
    for row in rescue_pool:
        etf, _, _ = resolve_bubble_etf(row.get("sector"), row.get("industry"), sector_rotation_raw)
        if not etf:
            continue
        bubble_entry = (bubble_watch_raw or {}).get(etf)
        if not bubble_entry:
            continue
        stage = bubble_entry.get("stage")
        confirmed = bubble_entry.get("confirmed") is True
        if stage not in (2, 3, 4):
            continue
        if stage == 4 and confirmed:
            continue  # already flagged at risk in watchlist_ranker's regime_penalty() -- never rescued
        rescued.append({
            **row,
            "bubble_stage": stage,
            "bubble_theme": bubble_entry.get("theme"),
            "bubble_etf":   etf,
            "rescue_flag":  "late-stage, not yet confirmed — watch for distribution" if stage == 4 else None,
        })
    rescued.sort(key=lambda x: -x["score"])

    # ── Print ─────────────────────────────────────────────────────────────
    today = datetime.today().strftime("%Y-%m-%d")
    filter_label = " (EU)" if args.eu else " (US)" if args.us else ""
    print(f"\n  {'='*72}")
    print(f"  RESCUED_BW{filter_label} — outside top {RESCUE_BW_TOP_CUTOFF}, early bubble-watch stage — {today}")
    print(f"  {'='*72}")
    if rescued:
        print(f"  {'TICKER':<12} {'SCORE':>6}  {'CONV':<8} {'STAGE':>5}  THEME / FLAG")
        print(f"  {'─'*72}")
        for row in rescued:
            flag  = f" — {row['rescue_flag']}" if row.get("rescue_flag") else ""
            theme = row.get("bubble_theme") or ""
            print(f"  {row['ticker']:<12} {row['score']:>6.1f}  {row['conviction']:<8} "
                  f"{row['bubble_stage']:>5}  {theme}{flag}")
    else:
        print("  (none — data/bubble_watch.json missing/stale, or nothing outside the top "
              f"{RESCUE_BW_TOP_CUTOFF} is at an early bubble-watch stage right now)")

    # ── Save ──────────────────────────────────────────────────────────────
    output = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "top_cutoff":   RESCUE_BW_TOP_CUTOFF,
        "Rescued_BW":   rescued,
    }
    Path(OUTPUT_PATH).parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved → {OUTPUT_PATH}\n")


if __name__ == "__main__":
    main()
