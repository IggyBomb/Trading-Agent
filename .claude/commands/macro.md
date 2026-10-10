# Macro Command

Runs the macro-analyst agent on demand and produces the full Macro Research Report
(regime, rates, cross-asset, cycle frameworks, bubble watch, directional bias).

This is the only place `macro-analyst.md` gets invoked today — there was no dedicated
command for it before, so whether the bubble watch verdict was ever persisted to
`data/bubble_watch.json` depended on whether someone happened to ask for a macro
report in the right words. `watchlist_ranker.py`'s crowded-sector penalty (see
`regime_penalty()`) is gated on that file being fresh, so running `/macro` is now a
prerequisite for that gate ever firing, not optional background colour.

---

## Step 0 — Data check

Check the timestamps on the local feeds the report is built from:

- `data/macro_regime.json`
- `data/sentiment_data.json`
- `data/sector_rotation.json`
- `data/macro_fred.json` (often `NO_API_KEY` — that's expected, not an error)

Print each file's `generated_at` (or `NO_API_KEY` / `MISSING`) before proceeding:
```
[MACRO INPUTS: macro_regime <ts> | sentiment <ts> | sector_rotation <ts> | fred <ts/NO_API_KEY/MISSING>]
```

Missing or stale inputs never block the report — flag them and proceed, same as
every other agent in this pipeline. A macro read built on stale sector data is still
more useful than no read; `macro-analyst.md` already marks anything carried forward
with `[EST]` or `[carried fwd]`.

If `data/sector_rotation.json` is more than ~24h old, note it explicitly — it's the
one feed that directly affects whether the bubble-watch entries this run produces
will actually line up with `watchlist_ranker.py`'s own crowded-sector check (same
file, same staleness window that matters there).

## Step 1 — Load inputs

Read the four files above in full, plus a same-session intraday pull for the
tickers/indices macro-analyst.md references (yfinance), exactly as described in
`macro-analyst.md`'s own "When called, you will receive" section.

## Step 2 — Invoke macro-analyst.md

Pass the loaded data to `macro-analyst.md` and produce its full output structure,
sections 1 through 11, in order. Do not skip sections for brevity — this report is
read in full, not scanned.

**Optional scope argument:**
- `/macro TICKER` or `/macro SECTOR` — after the standard 11 sections, add the
  final **"Macro Read for [TICKER/SECTOR]"** section macro-analyst.md's format
  rules already describe (tailwind/neutral/headwind + 3 bullet reasons).
- `/macro` with no argument — standard report only, no final section.

## Step 3 — Persist bubble_watch.json

This is the step that didn't reliably happen before this command existed.
`macro-analyst.md`'s own instructions (see its "Bubble watch persistence"
subsection under section 11) already specify the exact format — follow them as
written: write (or overwrite) `data/bubble_watch.json` via the Write tool, keyed by
ETF ticker, with `stage` / `confirmed` / `checklist_score` / `theme` / `note` per
entry, carrying forward unrevisited sectors from the previous file rather than
dropping them.

After writing it, read it back and print a one-line confirmation:
```
[BUBBLE WATCH SAVED → data/bubble_watch.json | N entries | Stage 4 confirmed: <list of ETF tickers, or "none">]
```

If the Write tool call fails for any reason, say so explicitly — do not let the
report complete silently without this file, since `watchlist_ranker.py`'s gate is
fail-closed and a missing file means "no penalty ever fires," indistinguishable
from "nothing is in a bubble" unless this confirmation line is there to tell them
apart.

## Step 4 — Suggest the follow-up

End with:
```
Run `python3 watchlist_ranker.py` to see today's bubble watch reflected in the
crowded-sector penalty (data/bubble_watch.json is now <N minutes> old).
```

---

## Rules

- `/macro` only ever produces the report and `bubble_watch.json` — it never screens
  or ranks tickers itself (that's `/scan` and `watchlist_ranker.py`).
- If `/macro` is run earlier in the same session, `/scan`'s Step 13 (short-screener,
  conditional on Directional Bias) and Step 11's Kindleberger-driven SHORT BIAS
  override should use that run's verdict rather than asking the question again.
- Every cycle-framework score (Marks, Minsky, Reinhart-Rogoff) must be reported as
  X/7 per macro-analyst.md's own format rules — never omit, never approximate.
- `bubble_watch.json`'s `confirmed: true` is reserved for language matching
  "Stage 4 CONFIRMED" in the prose verdict — never write it for "tell weakening",
  "approaching Stage 4", or a Stage 3 Euphoria read, even if Stage 4 is the working
  call for where things are headed. Getting this wrong either fires a penalty on a
  hunch or silently suppresses one that should apply.
