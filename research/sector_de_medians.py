#!/usr/bin/env python3
"""Sector median debt/equity from data/fundamental_data.json.

Prints a SECTOR_DE_MEDIAN dict to paste into config.py. Refresh quarterly,
not every run -- the scoring should stay stable between refreshes.
Financial Services is excluded: debt is a bank's raw material, so D/E is
not a fragility measure there (score_quality skips it too).

Usage: python3 research/sector_de_medians.py [path] [--min-n 20]
"""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED = {"Financial Services", "Unknown"}


def sector_medians(fundamentals: dict, min_n: int = 20) -> dict:
    by = defaultdict(list)
    for rec in fundamentals.values():
        de, sector = rec.get("debt_equity"), rec.get("sector") or "Unknown"
        if de is not None and de >= 0 and sector not in EXCLUDED:
            by[sector].append(de)
    return {s: round(statistics.median(v), 2)
            for s, v in sorted(by.items()) if len(v) >= min_n}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    min_n = int(sys.argv[sys.argv.index("--min-n") + 1]) if "--min-n" in sys.argv else 20
    path = Path(args[0]) if args and args[0] != str(min_n) else ROOT / "data" / "fundamental_data.json"
    data = json.loads(path.read_text())
    meds = sector_medians(data.get("fundamentals") or {}, min_n)
    print("SECTOR_DE_MEDIAN = {")
    for s, m in meds.items():
        print(f'    "{s}": {m},')
    print("}")
