#!/usr/bin/env python3
"""
scan_logger.py — reads scan_test_group.json (written by /scan's Test Group
Log step) and loads it into the scan_test_group SQLite table.

============================================================================
SESSION HANDOFF NOTE (2026-09-08) — read this before touching the tracking
system again, especially if picking this up with no prior conversation
context.

>>> NEXT SESSION STARTS HERE: rewrite scan_backtest.py for the new SQLite
>>> schema (data/scan_tracking.db, scan_test_group table). It currently
>>> still targets the discarded logs/scan_candidates.jsonl design and will
>>> not work against this file's output. Full requirements are in
>>> "NOT DONE YET / NEXT STEPS" below — read decision #1-8 above it first,
>>> the rewrite won't make sense without that context (esp. #5 on why it's
>>> one table not two, and #6/#7 on dedup + expected_close_date, since
>>> resolve logic needs to respect both).
============================================================================

THE GOAL (why this exists at all):
Build a system to track /scan's daily picks over time, to find out whether
the selection methodology actually predicts good outcomes — not just "did
the user's real trades work" (trade_logger.py already does that), but "is
CONFIRMED actually better than CAUTION, does conviction level matter, does
the deep research pass actually add value." This is a forward-test /
paper-trading harness for the scan methodology itself.

KEY DESIGN DECISIONS FROM TODAY'S SESSION, IN ORDER:

1. Not every ticker /scan touches gets the same depth of analysis. There's
   a funnel: Step 4 (mechanical CONFIRMED/CAUTION cross-reference, cheap,
   covers everyone) -> an R:R >= 1.5 gate (only some CONFIRMED tickers pass)
   -> Steps 5-9 (real strategy/alt-data/institutional/risk-manager verdicts,
   only for tickers that passed the R:R gate) -> Step 5 specifically (real
   market-researcher web research) only for High conviction (mandatory) +
   top 10 Medium conviction by f_score (also mandatory, drawn from the
   R:R-qualified pool only). Logging everything with no marker for how much
   analysis actually backed it would confound "research helps" with "this
   was already the strongest candidate." See .claude/commands/scan.md's
   "Steps 5-9 scope" sections and Step 5 for the formal rules.

2. /scan ITSELF writes the results (not a script recomputing from
   market_data.json/fundamental_data.json after the fact) — because a
   mechanical recompute cannot see what a real research pass found. Example
   that proved this mattered: TSN on 2026-09-08 mechanically looked like a
   clean TURNAROUND setup (trend down + reversal), but market-researcher
   found an active, worsening guidance-cut cycle (2nd cut in a month) with
   no confirmed reversal signal — real analysis disqualified it; a
   mechanical recompute would have logged it as a good TURNAROUND anyway.
   See scan.md's "Test Group Log" section (added today, right after Step 9)
   for exactly what /scan writes to data/scan_test_group.json and why.

3. The tracked population ("test group") = ALL High conviction CONFIRMED
   tickers + the top 10 Medium conviction CONFIRMED tickers by f_score
   (that top 10 drawn only from Medium CONFIRMED tickers that already
   passed the R:R >= 1.5 gate — a ticker that can't be traded on R:R
   grounds is never worth spending research budget on). This keeps daily
   research volume to a predictable ~15 tickers rather than scaling with
   the full CONFIRMED list — scan.md's own documented history shows a full
   agent stack across 74 tickers with no forking blew the token budget
   before finishing (vs. 41 tickers working fine).

4. An EARLIER, DIFFERENT version of this file existed today: it read
   market_data.json/fundamental_data.json directly and mechanically
   recomputed CONFIRMED/CAUTION + a strategy_type classifier (including a
   POSITION-eligibility proxy: weinstein_stage2_proxy() approximated
   Weinstein Stage 2 from daily MA50/MA200/trend since no weekly OHLCV
   exists in this pipeline, and classify_lynch_category() approximated
   Lynch's Stalwart/FastGrower/Cyclical categories from earnings_growth
   and sector). That version wrote to logs/scan_candidates.jsonl and was
   meant to capture the FULL CONFIRMED+CAUTION list (~107 tickers/day),
   no LLM session required. IT WAS DELIBERATELY DISCARDED (explicit user
   instruction: "just overwrite it") in favor of this narrower,
   research-backed design. If the broader mechanical capture is ever
   wanted again (see "NOT DONE YET" below), that classification logic
   will need to be rebuilt — it is not preserved anywhere in the codebase
   anymore, only in this session's conversation history.

5. Single table, not two (open vs. closed). Considered a two-table split
   (open tickers vs. closed/resolved tickers) but rejected it: a "closed"
   table still needs every field a candidate has (ticker, entry, stop,
   target, strategy_type, etc.) to be meaningful, not just outcome columns
   — so it isn't actually narrower, just a duplicate schema. Resolving a
   row would also require insert-into-closed + delete-from-open as two
   operations that must succeed together, vs. one atomic UPDATE on a
   single table. Went with one table (scan_test_group) with nullable
   outcome columns instead.

6. Dedup behavior: if a ticker is reselected (e.g. BEN CONFIRMED again
   tomorrow) while it ALREADY has an unresolved (outcome IS NULL) row from
   a prior day, compare final_verdict on the ladder BUY > WAIT > PASS >
   None (see VERDICT_RANK / verdict_rank()). Insert a NEW row only if
   today's verdict is a strict step UP from the open row's (e.g. WAIT ->
   BUY, PASS -> WAIT); otherwise SKIP — don't insert, don't update the
   existing one. Same-level or downgraded reappearances are ignored; the
   original row stays the tracked sample. After an upgrade the ticker has
   two open rows (the older non-BUY one is NOT closed) — the resolve step
   must handle both independently. (Originally a pure skip, chosen among
   skip / update-in-place / insert linked-by-streak-id; upgraded to the
   ladder rule on 2026-09-11 so a WAIT that later becomes a BUY is
   captured as its own sample.)

7. expected_close_date: computed at insert time as scan_date + the
   strategy_type's time-stop window in trading days (from
   strategy-analyst.md's own table: MOMENTUM=7, SWING=15, POSITION=30,
   TURNAROUND=45, EVENT=3). Mon-Fri counting only, no market holiday
   calendar — a soft "go check this" target, not a hard cutoff.

8. data/scan_test_group.json is OVERWRITTEN by /scan every run (not a
   dated file per day) — deliberate, to avoid a pile of per-day files
   accumulating over a months-long test. This creates a real risk: if
   /scan runs twice without this script running in between, the first
   day's results are lost with no trace. FIXED (2026-09-08, same session):
   scan.md's "Test Group Log" step now explicitly instructs /scan to run
   `python scan_logger.py` itself, immediately after writing the JSON,
   before moving on to Step 10 — not deferred to the user to remember. The
   loss window only reopens if that instruction is skipped or a session
   ends between the JSON write and the scan_logger.py call.

NOT DONE YET / NEXT STEPS:

- scan_backtest.py (the sibling script) has NOT been updated for this new
  SQLite schema — it still expects the old logs/scan_candidates.jsonl
  format from the discarded mechanical version. It needs a full rewrite:
  read from data/scan_tracking.db's scan_test_group table, resolve rows
  where outcome IS NULL by walking price history forward (reuse
  backtest.py's simulate_trade() the way the old version did), and UPDATE
  the row in place (not insert-elsewhere) with outcome/exit_date/
  exit_price/days_held/r_achieved/max_favorable_pct/max_adverse_pct/
  resolved_at. expected_close_date is a natural "is this overdue" signal
  for that resolve step.
- The broader, mechanical, ALL-CONFIRMED+CAUTION capture (~107 tickers/day,
  no research, no LLM needed) was explicitly deferred, not abandoned —
  "we will add it later" (user's words). If resurrected, it's a different
  table/source, not a replacement for scan_test_group.
- This script has not yet been run end-to-end against a real
  data/scan_test_group.json produced by an actual /scan session under the
  new scan.md rules (only tested conceptually during design). Do that
  before trusting it.
============================================================================
"""

import json, sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH   = "data/scan_tracking.db"
JSON_PATH = "data/scan_test_group.json"

# strategy-analyst.md's own time-stop table (trading days)
STRATEGY_TIME_STOP = {
    "MOMENTUM":   7,
    "SWING":      15,
    "POSITION":   30,
    "TURNAROUND": 45,
    "EVENT":      3,
}
DEFAULT_TIME_STOP = 15  # SWING fallback if strategy_type is missing/unrecognized

# Verdict ladder for the reselection rule: a ticker that already has an open
# row is only re-inserted when today's verdict is a step UP from that row.
# None (never reached Step 12) ranks below PASS.
VERDICT_RANK = {"BUY": 3, "WAIT": 2, "PASS": 1}


def verdict_rank(verdict):
    """Map a final_verdict string to its rung on VERDICT_RANK; 0 for None or
    anything unrecognized. Uses substring match so 'BUY — REDUCED (50%)'
    counts as BUY regardless of dash style or sizing suffix."""
    for name, rank in VERDICT_RANK.items():
        if name in (verdict or ""):
            return rank
    return 0

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS scan_test_group (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,

    scan_date                TEXT NOT NULL,
    ticker                   TEXT NOT NULL,
    conviction                TEXT,
    setup                     TEXT,
    entry                     REAL,
    stop                      REAL,
    target                    REAL,
    rr_planned                 REAL,
    f_score                    REAL,
    rating                     TEXT,
    sector                     TEXT,
    strategy_type               TEXT,
    alt_data_score               REAL,
    institutional_score          REAL,
    institutional_alignment       TEXT,
    risk_manager_verdict          TEXT,
    final_verdict                 TEXT,
    final_verdict_reason          TEXT,
    research_summary              TEXT,
    expected_close_date           TEXT,

    outcome                       TEXT,
    exit_date                     TEXT,
    exit_price                    REAL,
    days_held                     INTEGER,
    r_achieved                    REAL,
    max_favorable_pct             REAL,
    max_adverse_pct               REAL,
    resolved_at                   TEXT,

    UNIQUE(scan_date, ticker)
);
"""

INSERT_SQL = """
INSERT OR IGNORE INTO scan_test_group (
    scan_date, ticker, conviction, setup, entry, stop, target, rr_planned,
    f_score, rating, sector, strategy_type, alt_data_score,
    institutional_score, institutional_alignment, risk_manager_verdict,
    final_verdict, final_verdict_reason,
    research_summary, expected_close_date
) VALUES (
    :scan_date, :ticker, :conviction, :setup, :entry, :stop, :target, :rr_planned,
    :f_score, :rating, :sector, :strategy_type, :alt_data_score,
    :institutional_score, :institutional_alignment, :risk_manager_verdict,
    :final_verdict, :final_verdict_reason,
    :research_summary, :expected_close_date
);
"""

# The single source of truth for column order (everything in CREATE_TABLE_SQL
# except the `id` primary key, in the order it should physically appear).
# CREATE TABLE IF NOT EXISTS only applies to a brand-new DB file — a DB that
# already exists (e.g. data/scan_tracking.db from before 2026-09-09's
# buy/not-buy/final-analyst layer was added) keeps its old column set and
# order forever unless something explicitly fixes it. `ALTER TABLE ADD
# COLUMN` alone isn't enough for that: SQLite always appends a new column at
# the end, so a column added after the fact (final_verdict/final_verdict_reason)
# would sit after `resolved_at` instead of next to `risk_manager_verdict`
# where CREATE_TABLE_SQL actually declares it — correct set, wrong order.
DESIRED_COLUMNS = [
    ("scan_date",                "TEXT"),
    ("ticker",                   "TEXT"),
    ("conviction",                "TEXT"),
    ("setup",                     "TEXT"),
    ("entry",                     "REAL"),
    ("stop",                      "REAL"),
    ("target",                    "REAL"),
    ("rr_planned",                "REAL"),
    ("f_score",                   "REAL"),
    ("rating",                    "TEXT"),
    ("sector",                    "TEXT"),
    ("strategy_type",             "TEXT"),
    ("alt_data_score",            "REAL"),
    ("institutional_score",       "REAL"),
    ("institutional_alignment",   "TEXT"),
    ("risk_manager_verdict",      "TEXT"),
    ("final_verdict",             "TEXT"),
    ("final_verdict_reason",      "TEXT"),
    ("research_summary",          "TEXT"),
    ("expected_close_date",       "TEXT"),
    ("outcome",                   "TEXT"),
    ("exit_date",                 "TEXT"),
    ("exit_price",                "REAL"),
    ("days_held",                 "INTEGER"),
    ("r_achieved",                "REAL"),
    ("max_favorable_pct",         "REAL"),
    ("max_adverse_pct",           "REAL"),
    ("resolved_at",               "TEXT"),
]


def migrate_schema(conn):
    """Idempotent: brings an existing scan_test_group table's column SET and
    ORDER in line with DESIRED_COLUMNS / CREATE_TABLE_SQL. No-ops if a fresh
    CREATE_TABLE_SQL already produced the right shape (the common case)."""
    existing = [row[1] for row in conn.execute("PRAGMA table_info(scan_test_group)")]
    desired_names = [c for c, _ in DESIRED_COLUMNS]
    if [c for c in existing if c != "id"] == desired_names:
        return  # already correct set and order — nothing to do

    # Phase 1: add any genuinely missing columns (cheap, safe, preserves data)
    # so phase 2's rebuild can select every desired column without erroring.
    for col, coltype in DESIRED_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE scan_test_group ADD COLUMN {col} {coltype}")

    # Phase 2: rebuild with the correct column order. SQLite has no
    # "ALTER TABLE ... reorder column" — the standard, safe pattern is
    # rename-old -> create-new-with-right-shape -> copy -> drop-old.
    conn.execute("ALTER TABLE scan_test_group RENAME TO scan_test_group_reorder_old")
    conn.execute(CREATE_TABLE_SQL)
    cols_csv = ", ".join(desired_names)
    conn.execute(
        f"INSERT INTO scan_test_group (id, {cols_csv}) "
        f"SELECT id, {cols_csv} FROM scan_test_group_reorder_old"
    )
    conn.execute("DROP TABLE scan_test_group_reorder_old")


def add_trading_days(start, n):
    """Mon-Fri count only — does not account for market holidays.
    expected_close_date is a soft target for 'go check this,' not a hard
    cutoff, so this approximation is treated as good enough for now."""
    d = start
    added = 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d


def main():
    if not Path(JSON_PATH).exists():
        print(f"  No {JSON_PATH} found — nothing to import.")
        return

    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    scan_date     = data["scan_date"]
    scan_date_obj = datetime.strptime(scan_date, "%Y-%m-%d").date()
    candidates    = data["candidates"]

    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_TABLE_SQL)
    migrate_schema(conn)

    # Open (unresolved) rows from prior days, keyed by ticker, with the
    # final_verdict they were logged with. ORDER BY id so that if a ticker
    # has more than one open row (after an upgrade insert), the newest
    # verdict is the one kept in the dict.
    open_tickers = {row[0]: row[1] for row in conn.execute(
        "SELECT ticker, final_verdict FROM scan_test_group "
        "WHERE outcome IS NULL ORDER BY id"
    )}

    inserted, skipped_open, skipped_duplicate = 0, 0, 0
    for c in candidates:
        # Defensive default for JSON written before the buy/not-buy/final-analyst
        # layer existed, or for a candidate that never reached Step 12 (Step 9
        # said CAUTION/REJECT, so there's nothing for final-analyst to adjudicate).
        c.setdefault("final_verdict", None)
        c.setdefault("final_verdict_reason", None)

        # Reselection rule: skip unless today's verdict outranks the open row's.
        if c["ticker"] in open_tickers:
            if verdict_rank(c["final_verdict"]) <= verdict_rank(open_tickers[c["ticker"]]):
                skipped_open += 1
                continue

        c["scan_date"] = scan_date
        time_stop = STRATEGY_TIME_STOP.get(c.get("strategy_type"), DEFAULT_TIME_STOP)
        c["expected_close_date"] = add_trading_days(scan_date_obj, time_stop).isoformat()

        cur = conn.execute(INSERT_SQL, c)
        if cur.rowcount:
            inserted += 1
        else:
            skipped_duplicate += 1

    conn.commit()
    conn.close()

    print(f"  Scan date: {scan_date}")
    print(f"  Candidates in JSON: {len(candidates)}")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped (open from a prior day, verdict not upgraded): {skipped_open}")
    print(f"  Skipped (duplicate same-day row, rare): {skipped_duplicate}")


if __name__ == "__main__":
    main()
