# Automatic Watcher — Daily Instructions

How to find and live-watch tickers worth watching after a `/scan` run. Backs `/scan`
Step 12 (see `.claude/commands/scan.md`) and `watchlist_monitor.py`. Worked example
below uses the actual output from the 2026-08-24 session.

---

## Why this exists

A `/scan` output is a snapshot — it tells you what looked good at the moment the data
was pulled, not whether it's actually confirmed *right now*. Some tickers in that
output are ambiguous enough (a same-session long/short conflict, price sitting on a
major moving average, or an explicit "don't chase, wait for X" from the deep-dive) that
watching them live — price and volume, checked periodically — is more useful than
reading a static report once and acting on stale numbers.

This is not something that runs on its own. Every step below is manual/on-demand.

---

## Step 1 — Run `/scan` as normal

Steps 0–10 produce the CONFIRMED/CAUTION cross-reference and the full deep-dive
(market-researcher, alt-data, strategy-analyst, institutional-flow, risk-manager) on
every HIGH-conviction ticker. Everything below depends on this output already existing
— specifically `data/market_data.json` and `scan_step1_4_output.json`.

## Step 2 — Run the mechanical detector

```
python3 watchlist_monitor.py --auto
```

Checks every CONFIRMED ticker (both conviction tiers) for two things:

- **DUAL_SIGNAL** — the ticker has both a long setup and a live `short_setup` flag in
  the same pull. A genuine disagreement between the long and short screens.
- **STRUCTURAL_GATE** — price sits within a tight ATR band (default 0.2×) of MA50 or
  MA200 specifically — not support/resistance, which are the entry/stop/target pivot
  itself and therefore close to price *by construction* for nearly every scanned setup
  (a plain "near support/resistance" filter was tried and discarded for exactly this
  reason — it matched almost the whole scan output and told us nothing).

Add `--conviction High` to restrict to HIGH-conviction CONFIRMED names only.

**2026-08-24 result, full CONFIRMED list (147 tickers): 22 candidates** — mix of High
and Medium conviction, mostly DUAL_SIGNAL (a live `short_setup: distribution` sitting
under an otherwise-CONFIRMED long signal).

**Same day, `--conviction High` only: 1 candidate — TJX** (long reversal + short
breakdown at the same price, 140.53).

## Step 3 — Decide whether to include CAUTION-flagged HIGH-conviction names

`--auto` only reads the CONFIRMED list, by design. HIGH-conviction CAUTION names
(Overvalued fundamentals) are invisible to it. On 2026-08-24 this excluded **MOS**,
which would otherwise have shown a STRUCTURAL_GATE hit (sitting right on its 200-day
MA, 24.41 vs 24.28) — worth adding manually if you want CAUTION-tier coverage too.
There's no flag for this yet; it's a manual add.

## Step 4 — Manually cross-check deep-dive verdicts for "wait and see" language

This is the one step that cannot be automated. `--auto` only catches mechanical
signals; it has no way to see what the STRATEGY VERDICT / RISK MANAGER blocks actually
*said* during the Steps 5–9 deep-dive. Skim those verdicts for any explicit
"don't chase" / "wait for pullback to X" call — that judgment only exists for tickers
that went through the full pipeline (mandatory for HIGH conviction, mostly skipped for
Medium).

**2026-08-24 result**, found this way (all HIGH-conviction, all had this language and
were initially missed on the first pass — only re-surfaced after checking systematically):

| Ticker | Quote from the deep-dive |
|---|---|
| NEM | "prefer entry on first pullback to 126-128" |
| TGT | "better entry would be a pullback toward 160-161" |
| EL  | "wait for a pullback/retest of $95-97" |
| MRK | "do not chase more than 5% extended" |
| BDX | "same chase risk as MRK" |
| ALB | "still below its 200-day MA... consider waiting for a throwback" |

## Step 5 — Combine into the day's final watch list

Mechanical hits + judgment calls + any manual CAUTION add. 2026-08-24 total:

**TJX, NEM, TGT, EL, MRK, BDX, ALB, MOS — 8 tickers.**

## Step 6 — Define the trigger for each ticker

Every watch needs a level, a direction, and the original entry/stop/target. For a
DUAL_SIGNAL or STRUCTURAL_GATE hit, the level is the conflict/gate price itself. For a
judgment-call "wait for pullback" ticker, the level is the pullback zone the deep-dive
named — not the original scan entry, since the point is to catch it settling there.

```
python3 watchlist_monitor.py TICKER --level LEVEL --direction above|below \
    --entry ENTRY --stop STOP --target TARGET [--vol-threshold 1.5]
```

2026-08-24 examples:
```
python3 watchlist_monitor.py TJX --level 139.31 --direction above --entry 140.53 --stop 137.055  --target 145.7425
python3 watchlist_monitor.py NEM --level 128.00 --direction above --entry 131.58 --stop 126.5379 --target 139.1432
python3 watchlist_monitor.py TGT --level 161.00 --direction above --entry 165.44 --stop 160.5968 --target 172.7048
python3 watchlist_monitor.py EL  --level 97.00  --direction above --entry 101.94 --stop 98.2464  --target 107.4804
python3 watchlist_monitor.py MRK --level 148.05 --direction above --entry 152.55 --stop 148.0529 --target 159.2957
python3 watchlist_monitor.py BDX --level 187.38 --direction above --entry 192.00 --stop 187.3786 --target 198.9321
python3 watchlist_monitor.py ALB --level 154.48 --direction above --entry 143.25 --stop 137.6443 --target 151.6586
python3 watchlist_monitor.py MOS --level 24.28  --direction above --entry 24.41  --stop 23.3121  --target 26.0568
```

## Step 7 — Schedule the recurring checks

Set up a cron/loop job per ticker (or one job cycling all of them) via the `loop`
skill or `CronCreate`. **Default cadence: every 15 minutes**, not every minute —
checking volume more often than that mostly re-measures noise (see methodology note
below). Report only when a signal actually fires; a repeated "no signal" doesn't need
elaboration each cycle. The most decisive single check of the day is the last 30–60
minutes before close.

Session-bound: these jobs die when the session ends (7-day hard cap regardless). Use
`/schedule` instead if a watch needs to survive closing the session.

## Step 8 — Clean up

Once a signal fires (`"signal": true` — price holding the level **and** projected
volume clearing the threshold **and** R:R at the current price clearing the minimum,
see below) or the ticker is abandoned, cancel its job (`CronDelete <job-id>`). Nothing
should keep running past the point it's useful.

---

## Volume methodology — read before changing thresholds

Same-day cumulative volume compared against a full 20-day average is systematically
biased low until late in the session — e.g. 20% into the trading day reads as "~0.2x
average volume" even on a completely average day, because only 20% of the day's volume
has had a chance to print. `watchlist_monitor.py` projects a full session's volume from
the elapsed fraction of the NYSE session (9:30–16:00 ET) before comparing to the
20-day average. **Never compare raw same-day volume to a full-day average** — it reads
"thin" all day regardless of real participation. (Found and fixed live in the
2026-08-24 session, after a 1-minute cron loop reported false "thin volume" for ~15
consecutive checks before this fix.) The projection still assumes a flat intraday
pace and so under/overstates true early/late-session reality (real volume is
U-shaped — heavier at the open and close) — treat it as directional, and weight an
end-of-session check most heavily.

## R:R gate — read before changing thresholds

`holding_level` alone is not sufficient for a "wait for a pullback to X" watch: it
only checks that price is on the right side of `level`, which is trivially true for a
stock that never actually pulled back and is still sitting far above it.

**Found live on 2026-08-24**: TGT was watched with `level=161` (the pullback zone
named in its deep-dive verdict) and `direction=above`. Price never came down to 161 —
it stayed around $170 the whole session — so "holding above 161" was true by default
and the tool reported `SIGNAL FIRED`, with R:R at the actual $170 price sitting at
**0.25** (risking 4x what you could gain). Not a real confirmation, just an artifact
of the level check being satisfied by a stock that never pulled back at all. EL had
the identical latent issue (R:R 0.89 at its current price) and would have produced the
same false positive the next time its volume happened to cross the threshold.

**The fix**: every signal now requires all three conditions together —
`holding_level` **and** `volume_confirmed` **and** `rr_confirmed` (R:R at the *current*
price, not the original scan price, at or above `--min-rr`, default 1.5 to match
RISK.md's own minimum). Do not lower `--min-rr` to make a signal fire — that defeats
the entire purpose of the gate. If a "wait for pullback" ticker never actually pulls
back, the correct outcome is "no signal," not a forced trigger.

## What this deliberately does not do

- Does not auto-start any monitoring — every watch is opted into explicitly.
- Does not cover CAUTION-flagged tickers by default (Step 3 is a manual override).
- Does not detect judgment-call "wait for pullback" tickers automatically (Step 4 is
  manual, by necessity — that judgment lives in prose, not structured data).
- Does not persist past session end without `/schedule`.

## Reference

- Script: `watchlist_monitor.py` (repo root)
- Pipeline step: `.claude/commands/scan.md`, Step 12
- Architecture: `ARCHITECTURE.md` — script table + "known gaps" section
