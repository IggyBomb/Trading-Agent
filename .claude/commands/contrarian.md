# Contrarian Command

Runs the contrarian opportunity scanner as a companion view to the momentum scan. Finds high-quality stocks under temporary pressure — not broken businesses, but good assets being mispriced by fear, narrative, or crowded positioning.

**Key principle:** Contrarian and momentum outputs are always displayed separately and never merged. They answer different questions.

---

## Step 0 — Data Check

Check whether `data/contrarian_data.json` is fresh (< 24 hours old).

- If fresh: proceed to Step 2 using existing data.
- If stale or missing: proceed to Step 1.

Print the data timestamp so the user can see what they're working with:
```
[CONTRARIAN DATA: generated_at timestamp | N candidates scanned]
```

---

## Step 1 — Run the Scanner

```bash
python3 contrarian_scan.py
```

This scans the current `market_data.json` downtrend pool + open positions for tickers that are:
- Down ≥20% from 52-week high
- RSI ≤ 35
- Revenue not collapsing (growth > −20%)

Runtime: approximately 3–5 minutes depending on pool size.

**Optional overrides:**
- `--tickers AMZN MSFT RKLB` — scan a specific list instead of the auto pool
- `--min-conviction HIGH` — show only HIGH conviction results

---

## Step 2 — Load Contrarian Data

Read `data/contrarian_data.json`.

If the file is missing:
```
⚠ [CONTRARIAN DATA MISSING — run: python3 contrarian_scan.py]
```
Proceed with any manually provided tickers, or stop here if none.

---

## Step 3 — Invoke Contrarian Analyst Agent

Pass the full contents of `contrarian_data.json` to `contrarian-analyst.md`.

The contrarian analyst will:
1. Output the **CONTRARIAN OVERVIEW** block (market-wide context)
2. Output one **CONTRARIAN VERDICT** block per candidate — HIGH first, then MEDIUM, then LOW
3. Classify each candidate's narrative type (MACRO_FEAR / SINGLE_EVENT / etc.)
4. Provide a one-line thesis for manual validation

---

## Step 4 — Sentiment Context

Before presenting contrarian results, pull the current F&G reading from `data/sentiment_data.json`:

- **F&G < 25 (Extreme Fear):** This is Dreman's "maximum pessimism" zone. Historically the highest-probability entry window for contrarian setups. Note explicitly: *"F&G at [X] — statistically this is the best time to be a contrarian buyer."*
- **F&G 25–40 (Fear):** Good contrarian environment. Market is pessimistic but not panicking.
- **F&G 40–65 (Neutral to Greed):** Contrarian setups exist but are harder to execute — the market is not at maximum pessimism, so mean reversion takes longer.
- **F&G > 65 (Greed):** Flag that contrarian entries are working against momentum. Higher probability of continued downside before reversal.

---

## Step 5 — Cross-check with Momentum Scan (if /scan was run this session)

If `/scan` was already run in the same session, add a cross-reference note at the top of the contrarian output:

```
──── DUAL-VIEW SESSION ──────────────────────────────────────────
Momentum scan ran this session: [N] setups identified.
Contrarian scan: [N] candidates.
Any ticker appearing in BOTH views is flagged: [DUAL SIGNAL]
─────────────────────────────────────────────────────────────────
```

If the same ticker appears in both: explain why (e.g. "MSFT: momentum scan flagged a reversal setup; contrarian scan flags oversold fundamentals intact — both views converge on a potential turnaround entry").

---

## Step 6 — Risk Gate

After contrarian candidates are presented, flag portfolio-level implications:

- Check position count (RISK.local.md) — if already at 5 positions, note that all contrarian entries are blocked until a slot opens
- Check sector concentration — if entering a contrarian name would create a third position in the same sector, flag it
- Confirm that every contrarian entry still requires: stop loss defined, R:R ≥ 1.5:1, size ≤ active tier maximum

No contrarian thesis overrides RISK.md. A compelling narrative does not justify skipping the stop.

---

## Output structure (always in this order)

```
══════════════════════════════════════════════════════════
  CONTRARIAN SCAN — [DATE]
  ── Separate from momentum scan. Never merged. ──
══════════════════════════════════════════════════════════

[CONTRARIAN OVERVIEW block]

[HIGH CONVICTION VERDICTS]

[MEDIUM CONVICTION VERDICTS]

[LOW CONVICTION VERDICTS — "watch but don't buy yet"]

══════════════════════════════════════════════════════════
```

---

## Rules

- The contrarian scan is a companion view, not a replacement for `/scan`
- Never apply momentum entry rules to contrarian candidates (RSI 50–70 breakout logic does not apply here)
- Never apply contrarian logic to momentum candidates
- All five contrarian signals are described in `contrarian-analyst.md` — apply them fully
- Distribution volume disqualifies any contrarian candidate regardless of RSI or price depth
- Output is for manual decision-making only — no automated order routing
- Missing data = flag and proceed, never block
