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

## Step 5 — Market Researcher (mandatory for HIGH conviction)

For every ticker flagged **HIGH conviction** in Step 4, invoke `market-researcher.md` immediately.
Do not skip this step — it is not optional for High conviction names.

Medium conviction tickers: market-researcher is optional. Call it only if a specific catalyst or risk event warrants it.

## Step 6 — Alt Data Agent (mandatory for all tickers)

After market-researcher completes, invoke `alt-data-agent.md` for every ticker in the output.
Reads `./data/alt_data.json` — if missing, flag it and continue with available data.

Outputs: ALT DATA VERDICT block per ticker with insider cluster signal, short interest level, congressional direction, news NLP sentiment, and Alt Data Score (0–100).

## Step 7 — Strategy Analyst

After all agent outputs are assembled (technical, fundamental, sentiment, macro, market-researcher, alt-data), invoke `strategy-analyst.md` for every ticker in the output.

Strategy analyst classifies each ticker: POSITION / SWING / MOMENTUM / TURNAROUND / EVENT.
Outputs full STRATEGY VERDICT block per ticker.

## Step 8 — Institutional Flow (mandatory for all tickers)

After strategy-analyst output is complete, invoke `institutional-flow.md` for every ticker.

This is the final analysis layer before risk. It runs once all other agents have produced their output — never before.
Outputs market-wide Institutional Flow Overview (once per session) + per-ticker Institutional Verdict with Smart Money Score.

Verdict flags (never blocks):
- ALIGNED (≥70): pass to risk-manager, no flag
- CAUTIOUS (40–69): pass to risk-manager with CAUTION flag
- CONTRARIAN WARNING (<40): pass to risk-manager with STAND DOWN flag — note reason clearly

## Step 9 — Risk Manager

Pass every ticker with its full analysis stack (strategy verdict + alt data verdict + institutional verdict) to `risk-manager.md` for final position sizing, stop validation, and APPROVE / CAUTION / REJECT verdict.

Provide the current portfolio snapshot (from RISK.local.md or user-supplied screenshot) so the risk manager can check sector concentration, position count, and drawdown status.

## Step 10 — Short Screener (conditional)

Run `short-screener.md` only if the macro-analyst output from this session shows Directional Bias = **NEUTRAL** or **SHORT BIAS**.

If macro bias is LONG BIAS: skip this step entirely.
If macro bias is NEUTRAL or SHORT BIAS: run short-screener against the same market_data.json and output short candidates with their Short Score alongside the long candidates.

---

## Step 11 — Contrarian Scan (optional companion)

After the full momentum scan output is complete, the user may request the contrarian view by invoking `/contrarian`.

The two views are always output separately and never merged. The momentum scan and contrarian scan answer different questions — do not combine their ranked lists.

If the user explicitly requests both views in the same session (`/scan + /contrarian` or "full scan with contrarian"), run `/contrarian` automatically after Step 10 completes. Otherwise, wait for explicit invocation.

See `.claude/commands/contrarian.md` for the full contrarian workflow.

---

## Rules:
- No commentary. No disclaimers. Trade ideas only.
- Short-term setups: stops are ATR(14)-based, target is 1.5:1 R:R minimum (RISK.md).
- CONFIRMED = technically sound + fundamentally backed. These are the primary setups.
- CAUTION = technically valid but fundamentally expensive. Label clearly.
- Never output Low conviction tickers regardless of fundamental score.
- Never skip Steps 5–8 for High conviction tickers — partial analysis is not a complete scan.
- Missing data = flag only, never block. The user makes all final decisions.
- Momentum and contrarian outputs are always separated — never merge the two lists.
