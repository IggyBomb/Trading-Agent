# Scan Command

You are a trading setup scanner backed by fundamental analysis. When invoked:

## Step 0 — Exit Analyst (open positions first)

Before scanning for new ideas, run `exit-analyst.md` on all currently open positions.

- Run `python3 trade_logger.py open` and `python3 position_monitor.py` to get the current position list
- Pass each open position to `exit-analyst.md`
- Output the EXIT VERDICT block for each position: HOLD / TRAIL / PARTIAL / EXIT
- Only after this step is complete, proceed to Step 1

Rationale: managing what you already hold takes priority over adding new risk.

If no open positions exist, skip this step and proceed directly to Step 1.

---

## Step 1 — Load data

- Read technical signals from `./data/market_data.json` (pre-fetched by `fetch_data.py`)
- Read fundamental scores from `./data/fundamental_data.json` (pre-fetched by `fundamental_agent.py`)
- If `fundamental_data.json` is missing, print:
  `⚠ [FUNDAMENTAL PILLAR INCOMPLETE — fundamental_data.json missing. Run: python3 fundamental_agent.py. Proceeding on technicals only.]`
  and continue without blocking.
- If `sentiment_data.json` is missing, print:
  `⚠ [SENTIMENT PILLAR INCOMPLETE — sentiment_data.json missing. Run: python3 sentiment_agent.py. Sizing tier unknown.]`
  and continue without blocking.
- If `alt_data.json` is missing, print:
  `⚠ [CATALYST PILLAR INCOMPLETE — alt_data.json missing. Run: python3 alt_data.py. Alt data scores unavailable.]`
  and continue without blocking.

Never stop the scan due to missing data. Flag and proceed — the user makes all final decisions.

## Step 2 — Cross-reference

For each High or Medium conviction technical setup, look up its fundamental score:

- **CONFIRMED** — technical conviction is High or Medium AND f_rating is Undervalued or Fair
- **CAUTION** — technical conviction is High or Medium BUT f_rating is Overvalued (momentum play, elevated risk)
- Drop everything else.

If fundamental data is unavailable for a ticker, include it as-is (no flag).

**f_rating carries forward past this gate — it is not just a pass/fail filter.** CONFIRMED collapses Undervalued and Fair into one bucket, but the 2026-10-08 benchmark report found they are not equal-strength signals: Undervalued names won 70% of the time (+0.40 pts vs the S&P) against 34% for Fair (−1.56 pts) — the single cleanest edge found in the whole report. Tag every CONFIRMED ticker's `f_rating` through Steps 5–11 so `final-analyst.md` (Step 12) can weigh it explicitly instead of it being discarded once CONFIRMED is decided.

## Step 3 — Assess each setup

For each ticker assess:
- Trend direction (up / down / sideways)
- Volume vs average (volume_ratio field)
- Distance from support/resistance
- Setup type (breakout, pullback, reversal)
- ATR% — confirms the stock has enough range for short-term trading
- F-Score and sub-scores (value, quality, growth)

## Step 4 — Rank and output

Sort order:
1. CONFIRMED setups — by f_score descending
2. CAUTION setups — by volume_ratio descending

Output format (one line per ticker):

TICKER | Setup | Entry | Stop | Target | Tech | F-Score | Rating | Flag

- Tech = High / Medium
- F-Score = 0–100 (-- if unavailable)
- Rating = Undervalued / Fair / Overvalued (-- if unavailable)
- Flag = CONFIRMED / CAUTION / (blank if no fundamental data)

## Steps 5–9 scope — CONFIRMED only

Steps 5–9 run only for tickers flagged **CONFIRMED** in Step 4. CAUTION tickers stop
after Step 4 — they appear in the ranked table with their Step 4 line (Setup / Entry /
Stop / Target / Tech / F-Score / Rating / CAUTION) and get no deeper agent treatment by
default.

Rationale: CAUTION already means "technically valid but fundamentally expensive,
elevated risk" — it's the secondary bucket by design. Running the full mandatory
agent stack (market-researcher, alt-data-agent, strategy-analyst, institutional-flow,
risk-manager) against every CAUTION name as well as every CONFIRMED one roughly
doubled the sub-agent volume of a scan on a broad watchlist (74 vs. 41 tickers in a
same-size-universe comparison, 2026-09-02) with no forking, which pushed a full run
over the available token budget before it could finish. Gating to CONFIRMED brings
per-run agent-call volume back in line with historical runs.

If a specific CAUTION ticker is worth a full look, run its Steps 5–9 manually on
request rather than defaulting to it for the whole bucket.

## Steps 5–12 scope — quality pool, R:R flagged (within CONFIRMED)

Changed 2026-10-07 (user decision): R:R and `target_atr` no longer exclude anything. The
old `target_atr >= 2.4` gate (pegged to RR_RATIO x ATR_STOP_MULT) used to stop a CONFIRMED
ticker after Step 4 when its target was too close; it is now a **flag only**. The goal is a
few quality names to buy, chosen on thesis + fundamentals + news + trend, with R:R shown
next to every one of them rather than used as a filter.

**Quality pool** (the only tickers that go through Steps 5–12 — this is what keeps research
volume bounded now that the R:R gate no longer does):
- every **High conviction** CONFIRMED ticker, plus
- the **top 20 Medium conviction** CONFIRMED tickers by f_score (descending) — all of them
  if fewer than 20.

Every other CONFIRMED ticker stops after Step 4 (ranked table only).

**R:R flag** — carried on every pool ticker through Steps 5–12 and into the final output:
- `⚠ R:R {rr} < 1.2 (RISK.md floor)` when `rr` (at the live 3.2x-ATR stop) is under 1.2
- `⚠ target_atr {x} < 2.4` when the target is under 2.4 ATR away
- Both are information for risk-manager / buy / not-buy / final-analyst to weigh, never a
  reason on their own to drop a ticker. A pipeline target that is just the pre-gap price
  after an event-driven drop (profit warning, M&A, etc.) makes R:R look better than it is —
  say so when it applies.

History: 2026-09-14 the gate moved from `rr >= 1.5` to `target_atr >= 1.5` (stop widened to
2x ATR); 2026-10-06 to `target_atr >= 2.4` (stop 3.2x ATR, RR_RATIO 0.75); 2026-10-07 removed
as a gate entirely, kept as the flag above.

## Step 5 — Market Researcher (mandatory for HIGH conviction CONFIRMED + top 20 Medium conviction CONFIRMED)

For every **CONFIRMED** ticker flagged **HIGH conviction** in Step 4, invoke `market-researcher.md` immediately.
Do not skip this step — it is not optional for High conviction CONFIRMED names.

For **Medium conviction CONFIRMED** tickers: invoke `market-researcher.md` for the **top 20
by f_score** (descending) — mandatory, not optional, for that subset (the quality pool above).
If fewer than 20 Medium CONFIRMED tickers exist that day, research all of them.

Any other Medium conviction CONFIRMED ticker (outside that top 20): market-researcher remains
optional — call it only if a specific catalyst or risk
event (e.g. earnings within the lookahead window) warrants it. A ticker researched under
this optional path is not part of the Test Group Log population (see after Step 9) unless
it also independently qualifies via High conviction or top-10-by-f_score.

Rationale: bounds Step 5's daily research volume to a predictable ~15 tickers (High
conviction is typically small, plus 10 Medium) rather than scaling with the full CONFIRMED
list — see the Steps 5–9 CONFIRMED-only rationale above on why unbounded research already
blew the budget once. This rule also defines the Test Group Log population, below.

## Step 6 — Alt Data Agent (mandatory for all CONFIRMED tickers)

After market-researcher completes, invoke `alt-data-agent.md` for every ticker in the **quality pool**.
Reads `./data/alt_data.json` — if missing, flag it and continue with available data.

Outputs: ALT DATA VERDICT block per ticker with insider cluster signal, short interest level, congressional direction, news NLP sentiment, and Alt Data Score (0–100).

## Step 7 — Strategy Analyst

After all agent outputs are assembled (technical, fundamental, sentiment, macro, market-researcher, alt-data), invoke `strategy-analyst.md` for every ticker in the **quality pool**.

Strategy analyst classifies each ticker: POSITION / SWING / MOMENTUM / TURNAROUND / EVENT.
Outputs full STRATEGY VERDICT block per ticker.

## Step 8 — Institutional Flow (mandatory for all CONFIRMED tickers)

After strategy-analyst output is complete, invoke `institutional-flow.md` for every ticker in the **quality pool**.

This is the final analysis layer before risk. It runs once all other agents have produced their output — never before.
Outputs market-wide Institutional Flow Overview (once per session) + per-ticker Institutional Verdict with Smart Money Score.

Verdict flags (never blocks):
- ALIGNED (≥70): pass to risk-manager, no flag
- CAUTIOUS (40–69): pass to risk-manager with CAUTION flag
- CONTRARIAN WARNING (<40): pass to risk-manager with STAND DOWN flag — note reason clearly

## Step 9 — Risk Manager

Pass every ticker in the **quality pool** (with its R:R flag), with its full analysis
stack (strategy verdict + alt data verdict + institutional verdict), to `risk-manager.md` for
a **VERDICT: APPROVE / CAUTION / REJECT** plus the position sizing, exposure/correlation,
R:R, drawdown, stop-loss, and volatility detail behind it. This is a flag only (changed
2026-10-06): a REJECT does NOT exclude the ticker — every CONFIRMED ticker that reaches
this step proceeds to Step 10 regardless of its verdict. Treat REJECT as "mechanically
can't be sized as proposed" information for Steps 10–12 to weigh, not as grounds to drop
the ticker from the list.

Provide the current portfolio snapshot (from RISK.local.md or user-supplied screenshot) so the risk manager can check sector concentration, position count, and drawdown status.

## Step 10 — Buy Analyst

For every ticker that reached Step 9 (the whole quality pool — Step 9's verdict does not
filter this set, including REJECT), invoke `buy-analyst.md`.
It builds the strongest evidence-based case for entering now, using only what Steps 1–9
already produced (no new research), including Step 9's verdict and detail as context.
Outputs one BUY CASE block per ticker.

If the quality pool is empty (no High CONFIRMED and no Medium CONFIRMED tickers), skip
Steps 10–12 entirely — there is nothing to adjudicate.

## Step 11 — Not-Buy Analyst

Runs alongside Step 10 (same ticker set, same inputs), invoking `not-buy-analyst.md`. It
builds the strongest evidence-based case against entering now, and explicitly classifies
that case as either THESIS IS WRONG or TIMING IS WRONG. Step 10 and Step 11 do not see
each other's output — both report independently into Step 12. Outputs one NOT-BUY CASE
block per ticker.

## Step 12 — Final Analyst (the approve mark)

After both Step 10 and Step 11 complete for a ticker, invoke `final-analyst.md`. It is the
only agent that reads both the bull and bear case together, plus the full Steps 1–9
context (including Step 9's verdict and detail), and issues the verdict that actually
governs whether the ticker gets traded today: **BUY / BUY — REDUCED / WAIT / PASS**. Since
2026-10-06, Step 9's REJECT no longer excludes a ticker — every CONFIRMED ticker reaches
this step regardless of its Step 9 verdict, so this is the only point in the pipeline that
excludes a ticker from being traded, and it does so on thesis + risk facts together, not on
risk mechanics alone (see `final-analyst.md`'s own rationale, and the 2026-09-09 SYK case —
from before this change — that motivated adding this adjudication layer in the first
place). Outputs one FINAL VERDICT block per ticker, plus a one-line session summary of how
many CONFIRMED tickers became BUY / BUY — REDUCED / WAIT / PASS.

**This is the mark that actually matters** — when presenting results to the user, lead with
Step 12's verdict. Step 9's risk summary is context for that verdict, not a prior decision.

## Step 12b — Bubble Watch Rescue (after Step 12, before the Test Group Log)

Added 2026-10-10. A second, separate candidate group alongside the quality pool: tickers in
the top 100 of `watchlist_ranker.py`'s composite ranking whose sector/industry sits at an
early, not-yet-confirmed bubble-watch stage (Stage 2, 3, or 4 not confirmed) — names that
may keep running *because* they are in a bubble. They get the same full analyst treatment
and the same verdict ladder, and are logged as their own group (`BUBBLE_RESCUED`) so their
performance can be compared against the quality pool.

1. **Preconditions — check, never block:**
   - `data/bubble_watch.json` exists and its `generated_at` is < 36 h old
     (`config.BUBBLE_WATCH_MAX_AGE_HOURS`). This session's macro run is what writes it —
     if it's missing or stale, the macro step didn't persist it.
   - `data/sector_rotation.json` has a `us_industries` block (without it every semi resolves
     to XLK instead of SMH and nothing matches the bubble watch).
   If either fails, print
   `⚠ [BUBBLE RESCUE SKIPPED — <reason>. rescued_candidates = []]`, write an empty
   `rescued_candidates` list in the Test Group Log, and continue.
2. **Re-run the rescue now:** `PYTHONIOENCODING=utf-8 python rescue_bw.py`. Do not reuse the
   16:00 pipeline's `data/rescued_bw.json` — it was built before today's macro wrote today's
   bubble watch. Read the fresh `data/rescued_bw.json` → `Rescued_BW` list (already sorted
   by rescue `score`, descending; each row carries `normal_rank`, `bubble_etf`,
   `bubble_stage`, `bubble_theme`).
3. **Drop overlaps, then cap:** any rescued ticker already in today's quality pool is
   dropped from the rescue list (the pool row wins; list the dropped names). From what
   remains, take the **top 10 by rescue score**. Everything below the top 10 is listed in the
   output (ticker, normal_rank, score) but not analysed or logged.
4. **Levels are mandatory:** take `setup`, `conviction`, `entry`, `stop`, `target`, `rr` from
   `market_data.json` and `f_score` / `rating` from `fundamental_data.json`. `entry`, `stop`
   and `target` must all be non-null — `scan_daily_update.py` cannot track a row without them.
   If any is missing, flag `⚠ [NO LEVELS — not logged]` for that ticker and skip it.
   Low technical conviction and any `rating` (including Overvalued) are allowed for this
   group — state both, they are information, not filters.
5. **Run Steps 5–12 on each of the (up to) 10** — market-researcher, alt-data-agent,
   strategy-analyst, institutional-flow, risk-manager, buy-analyst, not-buy-analyst,
   final-analyst — with this framing passed to every agent:
   - **Thesis:** riding the bubble momentum of `bubble_etf` (`bubble_theme`, stage
     `bubble_stage`), not value. Strategy is usually MOMENTUM.
   - **Hard invalidation:** the bubble watch for `bubble_etf` flips to Stage 4 **confirmed**
     (for SMH: an SMH close below its MA20). Name this level in the strategy verdict and
     as the exit trigger.
   - **Macro is context, not a veto (changed 2026-10-10):** a macro "no adds" line or a
     short-list entry for the sector does not on its own turn a rescued buy into WAIT/PASS.
     These names are in the list *because* their sector is running hot, so judge them on
     the bubble-momentum thesis plus the stock's own bull/bear case. Macro still counts as
     a risk input (risk-manager may flag it, the bear case may cite it), and the bubble's
     own invalidation (Stage 4 confirmed) is still a hard exit. Every rescued ticker is
     analysed and logged.
   - **Sizing and limits:** exactly the same rules as the quality pool (risk-manager tier
     sizing; rescued BUYs share Step 16's 5-BUY limit).
   - `final_verdict` uses the same four notations only (`BUY`, `BUY — REDUCED (X%)`, `WAIT`,
     `PASS`). The rescue label is never written into that field — the group lives in
     `rescued_candidates` / `selection_group`.
6. **Output:** a FINAL VERDICT block per rescued ticker, with
   `— BUBBLE WATCH RESCUED` appended to the displayed verdict line
   (e.g. `Verdict : WAIT — BUBBLE WATCH RESCUED`), plus a separate one-line summary:
   `Bubble rescue: N analysed → BUY x / BUY — REDUCED x / WAIT x / PASS x | dropped as pool
   overlap: …`.

## Test Group Log — write the JSON file

After Step 12 completes for every ticker in the Step 5 research population (all High
conviction CONFIRMED + the top 20 Medium conviction CONFIRMED by f_score) **and Step 12b
completes for the rescued top 10**, write the results to `data/scan_test_group.json`
using the Write tool — quality-pool rows under `candidates`, rescued rows under
`rescued_candidates`, in the same file.

This is a FIXED filename, overwritten every `/scan` run — not dated per day. That's
deliberate (avoids a pile of per-day files accumulating over a months-long test), but it
means the file must be read into SQLite before the next `/scan` run overwrites it, or that
day's results are lost with no trace.

**Immediately after writing the JSON, run `python scan_logger.py`** (same session, same
step) to load it into `data/scan_tracking.db` before moving on to Step 13. Do not treat
this as optional or defer it to "later in the session" — the whole point of running it
now is to close the window where an unread file could get overwritten by a future `/scan`
run. Report `scan_logger.py`'s own output (its per-group table: HIGH / MEDIUM_POOL /
BUBBLE_RESCUED — in JSON / inserted / skipped-open / skipped-duplicate) to the user as
part of this step's output.

Since 2026-10-10 the logger writes table `scan_tracking_bubble_watch`
(`config.SCAN_TRACKING_TABLE`), tagging every row with `selection_group`: `HIGH` /
`MEDIUM_POOL` from `conviction` for `candidates`, `BUBBLE_RESCUED` for
`rescued_candidates`. The old `scan_test_group` table is frozen (old tracking rules) and is
no longer written.

This captures what this specific `/scan` session actually concluded — the real Steps 5–12
verdicts, including any override a researched finding produced (e.g. TSN, 2026-09-08:
mechanically shaped like a TURNAROUND, disqualified by market-researcher's finding of an
active, worsening guidance-cut cycle; or SYK, 2026-09-09: risk-manager APPROVEd it on a
scoring error, caught and overridden to REJECT by the Step 10–12 adjudication layer once
final-analyst weighed the buy/not-buy cases against the CFO's live guidance-risk disclosure
that the original approval had missed). No script recomputing from `market_data.json` /
`fundamental_data.json` after the fact can reproduce this — it only exists if this step
writes it.

Schema — one object per ticker in the test group, every key present (use `null`, never omit
a key):

```json
{
  "scan_date": "2026-09-08",
  "candidates": [
    {
      "ticker": "TSN",
      "conviction": "High",
      "setup": "reversal",
      "entry": 51.42,
      "stop": 50.03,
      "target": 58.60,
      "rr_planned": 5.17,
      "f_score": 49.9,
      "rating": "Fair",
      "sector": "Consumer Defensive",
      "strategy_type": "TURNAROUND",
      "alt_data_score": 48,
      "institutional_score": 50,
      "institutional_alignment": "CAUTIOUS",
      "risk_manager_verdict": "REJECT",
      "risk_manager_reason": "RR: 1.3:1 at the 2x ATR stop, below the 1.5:1 minimum",
      "final_verdict": null,
      "final_verdict_reason": null,
      "research_summary": "2nd FY26 guidance cut in a month (widening beef losses), BofA cut PT, no confirmed reversal signal — disqualified despite mechanical TURNAROUND shape"
    }
  ],
  "rescued_candidates": [
    {
      "ticker": "LRCX",
      "conviction": "Low",
      "setup": "neutral",
      "entry": 321.72,
      "stop": 297.61,
      "target": 352.56,
      "rr_planned": 1.28,
      "f_score": 57.1,
      "rating": "Fair",
      "sector": "Technology",
      "strategy_type": "MOMENTUM",
      "alt_data_score": 52,
      "institutional_score": 50,
      "institutional_alignment": "CAUTIOUS",
      "risk_manager_verdict": "CAUTION",
      "risk_manager_reason": "RR: 1.28:1 MARGINAL; MACRO AI hardware 'no adds' in macro verdict (context, not a veto)",
      "final_verdict": "BUY — REDUCED (50%)",
      "final_verdict_reason": "Bubble momentum intact (SMH > MA20), clean uptrend, R:R 1.28; Fair rating and insider selling keep it at half size",
      "research_summary": "Semi-equipment demand strong on AI capex; price above MA50/MA200",
      "bubble_etf": "SMH",
      "bubble_stage": 4,
      "bubble_theme": "Semis/AI-infra",
      "normal_rank": 31,
      "rescue_score": 65.4
    }
  ]
}
```

(The LRCX row is an illustrative shape, not a real verdict.)

Field notes:
- `conviction` doubles as the selection reason under this rule — "High" means it qualified
  via the mandatory-High path, "Medium" means it qualified via top-20-by-f_score. The only
  other path into this file is Step 12b's `rescued_candidates`: a Medium-conviction ticker
  researched only because of the optional catalyst clause in Step 5 does not go in this log
  unless it also independently made the top 20.
- `rescued_candidates`: Step 12b's analysed top 10 only, with exactly the same keys as
  `candidates` plus the five rescue fields below (every key present, `null` if unknown).
  Write `"rescued_candidates": []` when Step 12b was skipped — never omit the key. A ticker
  never appears in both lists on the same day (overlaps were dropped in Step 12b).
- `bubble_etf` / `bubble_stage` / `bubble_theme` / `normal_rank` / `rescue_score`: copied
  from the ticker's row in `data/rescued_bw.json` (`normal_rank` = its rank in the
  composite ranking; `rescue_score` = that row's `score`). Only on `rescued_candidates`
  rows — do not add them to `candidates` (the logger fills them with NULL there).
- `strategy_type`: the real strategy-analyst.md classification, not a mechanical proxy.
- `institutional_score` / `institutional_alignment`: from Step 8. With no real 13F /
  dark-pool / options-flow source wired into this pipeline, this will typically be
  `50` / `"CAUTIOUS"` (`DATA UNAVAILABLE`) per institutional-flow.md's own fallback rule —
  write that honestly rather than fabricating a more specific score.
- `risk_manager_verdict`: exactly Step 9's conclusion (APPROVE / CAUTION / REJECT),
  including a REJECT driven purely by portfolio exposure (no open slots) — do not filter
  those out of the file just because the setup itself was sound. Kept as-is even when
  `final_verdict` overrides it — this is the raw, mechanical read, preserved for audit.
- `risk_manager_reason`: WHY Step 9 landed on REJECT or CAUTION — mandatory for both,
  never left blank; `null` only for APPROVE. Format: `CATEGORY: one-line detail`, where
  CATEGORY is the check that failed, exactly one of:
  - `EXPOSURE` — no open slot (5 positions) or sector/correlation limit (2 per sector)
  - `RR` — R:R below 1.5:1 at the 2x ATR stop
  - `TARGET_ATR` — Step 4 gate, `target_atr < 1.5`
  - `SIZE` — position over the active sentiment tier maximum
  - `DRAWDOWN` — daily/weekly drawdown limit hit or near
  - `STOP` — stop missing, illogical, or outside 1.5–3x ATR
  - `THESIS` — company-specific: negative catalyst, broken thesis, support lost / setup
    invalidated, or an overextended chase (RSI, euphoric run)
  - `MACRO` — sector on the macro short list / macro headwind, with no company-specific issue
  A marginal R:R (1.5–2.0) counts as `RR` only when it is the stated reason for CAUTION.
  If several checks failed, use the first one in this list as CATEGORY and name the others
  in the detail. Example: `"EXPOSURE: 5/5 positions open; R:R also MARGINAL at 1.7:1"`.
  This is what separates a sound setup rejected only for portfolio room from a setup the
  risk manager actually judged bad — the test group compares the two, so never collapse
  them into a bare REJECT.
- `final_verdict`: Step 12's conclusion (BUY / BUY — REDUCED / WAIT / PASS) for tickers
  that reached Steps 10–12 (i.e. `risk_manager_verdict = APPROVE`); `null` for every ticker
  that never reached adjudication because Step 9 already said CAUTION or REJECT. This is
  the field that actually governs whether the ticker gets traded — see `final-analyst.md`.
- `final_verdict_reason`: Step 12's one-line adjudication (why the verdict landed where it
  did); `null` alongside a `null` `final_verdict`. Never leave this blank when
  `final_verdict` is set — a BUY still gets a one-line "why," not just PASS/WAIT.
- `research_summary`: 1–2 sentences, the key market-researcher finding for that ticker.
- `target`: always write the pipeline's own target. `scan_logger.py` stores it as
  `target_pipeline` and tracks the row against `max(target, entry + 1.2 × (entry − stop))`
  (`TARGET_FLOOR_R`, since 2026-10-10), so near-entry consolidation targets don't close
  the row on day one. `scan_daily_update.py` skips the scan-day bar — tracking starts
  the next session.

Write this file every session Step 9 completes for the test-group population, even if a
ticker repeats from a prior day's file with an unchanged verdict — each day is a separate
data point, not a diff.

## Step 13 — Short Screener (conditional)

Run `short-screener.md` only if the macro-analyst output from this session shows Directional Bias = **NEUTRAL** or **SHORT BIAS**.

If macro bias is LONG BIAS: skip this step entirely.
If macro bias is NEUTRAL or SHORT BIAS: run short-screener against the same market_data.json and output short candidates with their Short Score alongside the long candidates.

---

## Step 14 — Contrarian Scan (optional companion)

After the full momentum scan output is complete, the user may request the contrarian view by invoking `/contrarian`.

The two views are always output separately and never merged. The momentum scan and contrarian scan answer different questions — do not combine their ranked lists.

If the user explicitly requests both views in the same session (`/scan + /contrarian` or "full scan with contrarian"), run `/contrarian` automatically after Step 13 completes. Otherwise, wait for explicit invocation.

See `.claude/commands/contrarian.md` for the full contrarian workflow.

---

## Step 15 — Live Watch (optional, offered after the full pipeline)

After Steps 0–13 complete (Step 14 is the separate `/contrarian` companion, not a
prerequisite), identify which output tickers are genuinely worth a live price/volume
watch rather than a static wait-and-recheck-later. Two independent sources feed this:

1. **Mechanical detection** — run `python3 watchlist_monitor.py --auto`. It reads the
   full CONFIRMED list (`scan_step1_4_output.json`, both conviction tiers — add
   `--conviction High` to narrow it) cross-referenced into `market_data.json`, and
   flags tickers on two narrow, non-circular criteria. Note this only covers
   CONFIRMED tickers by default — HIGH-conviction CAUTION names (e.g. an Overvalued
   ticker sitting on a key MA) are invisible to it and need a manual add if wanted:
   - `DUAL_SIGNAL` — the ticker has both a long setup and a live `short_setup` flag in
     the same pull (the long screen and short screen disagree — rare, worth resolving
     live rather than guessing which side is right)
   - `STRUCTURAL_GATE` — price sits within a tight ATR band of MA50 or MA200
     specifically (not support/resistance — those define the entry/stop/target
     themselves, so "close to support" is true of nearly every scanned setup by
     construction and was tried and discarded as a filter; see the docstring in
     `watchlist_monitor.py` for the full reasoning if resurrecting that idea)

2. **Judgment calls surfaced during Steps 7–9** — any ticker whose STRATEGY VERDICT or
   RISK MANAGER output explicitly said "don't chase," "wait for pullback to X," or
   named a specific level/volume condition to watch for. This is not mechanically
   detectable from `market_data.json` (it depends on the deep-dive reasoning, e.g. an
   R:R or extension judgment) — flag these directly while producing those verdicts,
   the same way this happened organically for TJX and ALB in practice.

Combine both lists, present them to the user, and **ask before starting any monitor** —
this step never auto-starts a watch. If the user wants one:

- Set up a recurring check via the `loop` skill or `CronCreate`, invoking
  `watchlist_monitor.py TICKER --level LEVEL --direction above|below --entry ENTRY
  --stop STOP --target TARGET [--vol-threshold 1.5]` per ticker/level being watched.
- **Default cadence: every 15 minutes**, not every minute. Checking volume more often
  than that mostly re-measures noise rather than new signal — see the volume
  methodology note below. The most decisive single check of the session is the last
  30–60 minutes before close, when the volume projection stops being a projection.
- Report only when a signal actually fires (`"signal": true` in the script's output —
  price holding the level AND projected volume clearing the threshold AND R:R at the
  current price clearing `--min-rr`, see below) or when something materially changes;
  a bare "no signal" repeated every cycle is expected and doesn't need elaboration
  each time.
- Session-bound limitation: `CronCreate`/`loop` jobs die when the session ends (7-day
  hard cap regardless). For a watch that needs to survive session closure, use
  `/schedule` instead.

**Volume methodology (critical, found and fixed live in an earlier session — do not
regress this):** same-day cumulative volume compared against a full 20-day average is
systematically biased low until late in the session — e.g. 20% into the trading day
reads as "~0.2x average volume" even on a completely average day, because only 20% of
the day's volume has had a chance to print. `watchlist_monitor.py` instead projects a
full session's volume from the elapsed fraction of the NYSE session (9:30–16:00 ET)
before comparing to the 20-day average. Never compare raw same-day volume to a full-day
average directly — it reads "thin" all day regardless of real participation. The
projection still assumes a flat intraday pace and so under/overstates true early/late
session reality (real volume is U-shaped, heavier at the open and close) — treat it as
directional, and weight an end-of-session check most heavily.

**R:R gate (also critical, also found and fixed live — do not regress this):**
`holding_level` alone is not sufficient for a "wait for pullback to X" watch — it only
checks price is on the right side of `level`, which is trivially true for a stock that
never actually pulled back and is just still sitting far above it. TGT was watched
with `level=161` (a named pullback zone); price never came down to 161, stayed near
$170 the whole session, so "holding above 161" was true by default and produced a false
`SIGNAL FIRED` at an actual R:R of 0.25. EL had the same latent issue. Every signal now
also requires `rr_confirmed` — R:R computed at the *current* live price (not the
original scan price) at or above `--min-rr` (default 0.75 = config.RR_RATIO, RISK.md's
1.2:1 effective minimum at ATR_STOP_MULT=3.2x). Never lower `--min-rr` just to make a signal fire — if a pullback ticker
never pulls back, "no signal" is the correct outcome.

---

## Step 16 — Test_PTF management (every run, after Step 12)

`Test_PTF` (`data/test_ptf.json`, managed with `test_ptf.py`) is the paper portfolio that
measures whether this pipeline produces alpha. Started 2026-10-02 with €100,000 notional,
benchmark IWDA.AS (MSCI World, EUR). Every `/scan` run manages it:

1. Run `python3 test_ptf.py` first — fills orders queued last session at today's open,
   enforces stops mechanically, snapshots NAV vs the shadow benchmark. Report the output.
2. Review each open position against today's full stack (macro verdict, fundamentals,
   alt data, technicals, news, earnings dates) using the SWING / strategy-analyst exit
   rules: target hit → trim 50–100%; +1R → move stop to breakeven (`set-stop`); 10 trading
   days without progress → exit; earnings inside the hold → exit or halve; thesis broken
   → exit. Act with `sell TICKER QTY|all`, `buy` (adds), or `set-stop`, always with
   `--reason`.
3. Enter today's Step 12 verdicts: `BUY` at the risk-manager size (tier % of €100,000),
   `BUY — REDUCED (X%)` at that fraction. WAIT/PASS are not entered; a WAIT whose trigger
   fires on a later run may be entered then. **Few, quality names:**  — if more than 5 BUY verdicts, take the strongest by final-analyst
   conviction (thesis, fundamentals, news, trend), not by R:R. Every order's `--reason`
   states its R:R and flags it if below the 1.2 floor; a below-floor R:R never blocks an
   entry on its own. Step 12b's rescued BUYs are entered under the same rules and count
   toward the same 5-BUY limit; their `--reason` starts with `BUBBLE WATCH RESCUED` and
   names the invalidation (bubble watch for `bubble_etf` flipping to Stage 4 confirmed).

Orders always fill at the next session's open (no same-close fills — the scan runs
after the close). Never edit `data/test_ptf.json` by hand to change history — the alpha
figure is only meaningful if every decision is recorded as it was made.

---

## Rules:
- No commentary. No disclaimers. Trade ideas only.
- Short-term setups: stops are ATR(14)-based. R:R is always shown against RISK.md's 1.2:1
  floor and flagged when below it — a flag, not a disqualifier (since 2026-10-07).
- CONFIRMED = technically sound + fundamentally backed. These are the primary setups.
- CAUTION = technically valid but fundamentally expensive. Label clearly. Stops at Step 4 by default — no Steps 5–9 unless specifically requested for that ticker.
- Never output Low conviction tickers regardless of fundamental score — except Step 12b's
  bubble-watch rescued names, which are selected by bubble stage + composite rank, not by
  technical conviction (show their conviction, don't filter on it).
- Never skip Steps 5–8 for High conviction CONFIRMED tickers — partial analysis is not a complete scan.
- Missing data = flag only, never block. The user makes all final decisions.
- Momentum and contrarian outputs are always separated — never merge the two lists.
