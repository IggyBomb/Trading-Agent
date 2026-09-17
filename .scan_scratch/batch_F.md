# Scan Batch F — Steps 5-9 — 2026-09-16
Tickers: NVDA, FIS, PBF, BNR.DE, EQT, BZU.MI (all CONFIRMED, Medium conviction, pullback setups)

**Session-wide context applied to every ticker below:**
- Macro regime: STAGFLATION (confirmed today). Directional Bias: SHORT BIAS (Semiconductors/AI infra, Consumer Discretionary, long-duration/rate-sensitive names named as short sectors).
- **CYCLE OVERRIDE = TRIGGERED** (4 of 6 cycle frameworks — Marks, Minsky 6/7, Kindleberger 7/7, Reinhart-Rogoff 5/7 — flag late-cycle/high-risk). Per strategy-analyst.md: CYCLE OVERRIDE → **no new POSITION trades system-wide**. This blocks POSITION classification for all six tickers below regardless of sector, forcing SWING as the ceiling classification even where Weinstein/Elder conditions might otherwise support POSITION.
- Sentiment: F&G 28.5 (Fear), VIX 17.2 (calm/normal, not a Scale-Back trigger), composite 54.5 → sizing tier **GOOD (3%, €2,220 max)**, confirmed live from `data/sentiment_data.json` (matches orchestrator's working assumption).
- Portfolio: 1/5 slots used (DVN, Energy, €947/1.3%). 4 free. Sector cap 2/sector — Energy has 1 slot left session-wide; this batch alone has 2 Energy candidates (PBF, EQT) competing for it.
- Account: ~€74,000 (RISK.local.md). EUR/USD ~1.153 used for conversions per user's standing EUR-display preference.

---

## NVDA — Nvidia

### Step 5 — Market Researcher

**1. News Catalysts**
- Summary: Mixed — bullish company-specific news overshadowed by sector-wide AI-safety selling pressure.
- Nvidia reportedly in talks to invest up to **$10B in Anthropic's IPO** (targeting ~$2.3T valuation, pricing before Nov 2026 midterms) — deepens the Nvidia/Anthropic compute-and-equity circular-financing loop (Nvidia already committed $10B + Anthropic pledged $30B in Azure/Nvidia compute spend, Nov 2025 deal).
- **NVDA stock fell on this news, not up** — Anthropic CEO Dario Amodei publicly warned the AI industry should slow its pace of development; this, combined with OpenAI's IPO delay to 2027 over internal AI-safety concerns, is driving broad chip-sector selling.
- President Trump publicly defended Nvidia against AI-regulation concerns at the All-In Summit (mild political tailwind, [UNCONFIRMED] market impact).
- No earnings report in the near term (next report not surfaced in search — [UNCONFIRMED], treat as CLEAR for now).

**2. Sentiment & Narrative**
- Analyst ratings: Strong Buy consensus intact — 9 Strong Buy / 48 Buy / 2 Hold / 1 Sell (60 analysts, as of ~Sept 8), avg PT $327.65 (~54% above spot) [UNCONFIRMED exact date].
- Short interest: alt-data confirms **1.29% of float — LOW**, no bearish structural pressure.
- Social/narrative: broadly bullish on the sell-side (ratings), but narrative is now genuinely mixed — "circular financing" and "AI bubble" framing is gaining real traction (Kindleberger checklist 7/7 complete per today's macro report).
- Narrative verdict: **mixed-to-cautious** — Street ratings still bullish, but the marginal news flow (Amodei's own slow-down warning, OpenAI retreat) is bearish and sector-specific.

**3. Institutional & Options Activity**
- Institutional ownership trend: [NO DATA] — no live 13F/dark-pool/options feed available this session.
- Alt-data insider signal (see Step 6) shows **$653M net insider selling** — a real, dated signal, cross-referenced below.
- Options flow: [NO DATA] — [UNCONFIRMED], no sweep/skew data accessible.

**4. Sector Rotation Signals**
- XLK (Technology): rank 7 of 11 US sectors, ret_1m **-3.69%**, ret_5d **-2.2%**, below 50MA (QQQ below MA50 per sentiment_data.json). Money is flowing OUT of tech relative to the broad market.
- Semiconductors/AI infra specifically named as CONFIRMED Kindleberger Stage 4 (bear market, -20% from June highs) in today's macro report — NVDA sits at the center of this.
- Peer comparison: [NO DATA] on AMD/SMH relative strength this session — [UNCONFIRMED].

**5. Market Structure Summary**
- Trend: up (daily), price $212.17 vs 50MA $213.02 (essentially at the 50MA) vs 200MA $197.42.
- Support 208.93 / resistance (52w high) 234.50 — 234.4976 target = the 52-week high, i.e. this trade requires a fresh breakout to new highs against a sector in a confirmed bear market.
- Volume ratio 0.67–1.04 (below-to-at average) — no accumulation signature on the pullback.
- RSI 49.55 — neutral, not oversold or overbought.
- Distance from 200SMA: +7.5%; price essentially at 50SMA.

**6. Upcoming Risk Events**
- Earnings date: [UNCONFIRMED] — not in `earnings_calendar.json`, no near-term date surfaced.
- Macro: none scheduled beyond today's already-realized FOMC hike; BOJ decision Sept 18 (2 days out) — a known dual-catalyst (Fed hike → BOJ hike) carry-trade stress risk per macro report.
- Sector-specific: Anthropic IPO timeline (target pricing pre-Nov 2026 midterms) is a live, dated catalyst that could move NVDA on headlines even pre-pricing.

### Step 6 — Alt Data Agent
```
┌─────────────────────────────────────────────────────────────────┐
│  ALT DATA VERDICT — NVDA — 2026-09-16                           │
├─────────────────────────────────────────────────────────────────┤
│  Alt Data Score    : 35                                          │
│  Signal            : BEARISH                                     │
│  Flags             : INSIDER_SELLING | INSIDER_MSPR_BEARISH      │
├─────────────────────────────────────────────────────────────────┤
│  Insider           : SELLING                                     │
│  Net 30d           : -$653,017,053 sold (0 buyers, 2 sellers)    │
│  Notable           : none named in feed                          │
│  Insider MSPR      : BEARISH (-98.6, 3mo avg — extreme)          │
├─────────────────────────────────────────────────────────────────┤
│  Short Interest    : 1.29% of float  DTC: 2.3 days                │
│  Level             : LOW                                          │
│  MoM change        : +1.9% (mild rise, not material)              │
│  Squeeze watch     : NO                                           │
├─────────────────────────────────────────────────────────────────┤
│  Analyst Trend     : STABLE                                       │
│  Bull ratio        : 94.2% buy-rated, Δ+0.1pp vs prior month      │
│  Congressional*    : NO_API_KEY (ref only)                        │
├─────────────────────────────────────────────────────────────────┤
│  News Sentiment    : 0.113 (NEUTRAL)                               │
│  Velocity          : STABLE                                       │
│  Articles scored   : 10 in last 5 days                            │
├─────────────────────────────────────────────────────────────────┤
│  Interpretation    : Street analysts still near-unanimously bullish│
│  (94.2% buy-rated), but insiders sold $653M net with extreme MSPR │
│  (-98.6) — a sharp insider/sell-side divergence. CONFLICT flagged.│
└─────────────────────────────────────────────────────────────────┘
```
Conflict flag: analyst STABLE/bullish vs insider SELLING+MSPR BEARISH — insiders may be pricing sector-specific risk (Kindleberger Stage 4) that sell-side ratings haven't caught up to yet. Treat insider signal as the higher-conviction read per framework rules.

### Step 7 — Strategy Analyst
```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY VERDICT — NVDA — 2026-09-16                            │
├─────────────────────────────────────────────────────────────────┤
│  Direction     : LONG                                             │
│  Strategy      : SWING                                            │
│  Holding Period: 5–15 days                                        │
│  Timeframe     : Daily chart                                      │
├─────────────────────────────────────────────────────────────────┤
│  Entry         : 210.96 — pullback to rising 50MA zone            │
│  Entry Method  : MA bounce / pullback                             │
│  Entry Timing  : 10:00–11:30 window                                │
│  Stop          : 195.4785 — structural (below support 208.93/200MA)│
│  Target        : 234.4976 — 52-week high (resistance)              │
│  R:R           : 1.52                                              │
├─────────────────────────────────────────────────────────────────┤
│  Position Mgmt                                                    │
│  Add at        : No add — CYCLE OVERRIDE active, do not scale up  │
│  Trim at       : +1.5R                                            │
│  Trail from    : +1R → breakeven                                  │
├─────────────────────────────────────────────────────────────────┤
│  Hold while    : Price holds above 200MA and stop not hit          │
│  Exit if       : Daily Impulse turns Red; 10 days no progress;     │
│                  weekly close confirms Stage 4 breakdown in chips  │
│  Max hold      : 10 trading days                                   │
├─────────────────────────────────────────────────────────────────┤
│  Thesis        : Pullback to 50MA in an otherwise intact uptrend,  │
│                  undervalued F-score (70.3)                        │
│  Main Risk     : Confirmed sector bear market (Kindleberger Stage 4)│
│                  + insider selling means this is a countertrend bet│
│                  against both macro and smart-money positioning    │
│  Earnings Risk : CLEAR [UNCONFIRMED — no date found]                │
└─────────────────────────────────────────────────────────────────┘
```
Note: POSITION classification (Weinstein Stage-2-like: price at rising 50MA, fundamentals CONFIRMED, ATR% 3.5%<5%) would otherwise be plausible, but CYCLE OVERRIDE is active system-wide today, which per rule forces this to SWING at best (rule explicitly bars new POSITION entries under CYCLE OVERRIDE).

### Step 8 — Institutional Flow (per-ticker verdict only)
```
┌─────────────────────────────────────────────────────────────────┐
│  INSTITUTIONAL VERDICT — NVDA — 2026-09-16                        │
├─────────────────────────────────────────────────────────────────┤
│  Smart Money Score : 35                                            │
│  Alignment         : ⚠ CONTRARIAN                                  │
├─────────────────────────────────────────────────────────────────┤
│  13F Consensus     : UNKNOWN — DATA UNAVAILABLE (no live feed)     │
│  Quarter           : N/A                                           │
│  Notable holders   : [NO DATA]                                     │
│  Lag note          : N/A                                           │
│  Activist flag     : NONE found                                    │
├─────────────────────────────────────────────────────────────────┤
│  Dark Pool         : DATA UNAVAILABLE — default NORMAL assumed     │
│  Direction signal  : UNCLEAR                                        │
├─────────────────────────────────────────────────────────────────┤
│  Options Flow      : DATA UNAVAILABLE — qualitative lean BEARISH   │
│  Detail            : No live sweep/skew feed; scored down from     │
│                      neutral default given sector-wide defensive   │
│                      positioning context (Amodei slow-down warning)│
├─────────────────────────────────────────────────────────────────┤
│  Sector ETF        : XLK — ret_1m -3.69%, ret_5d -2.2%, <MA50      │
│  ETF Signal        : HEADWIND                                       │
├─────────────────────────────────────────────────────────────────┤
│  Dry Powder        : DATA UNAVAILABLE — default NORMAL             │
│  Fuel for move     : LOW (given documented headwinds)              │
├─────────────────────────────────────────────────────────────────┤
│  STAND DOWN                                                        │
│  Reason            : Score <40 driven by real insider selling      │
│                      ($653M, MSPR -98.6) stacked on a confirmed    │
│                      sector headwind (XLK) — not a data-absence    │
│                      default. No documented exogenous reason       │
│                      (e.g. forced selling) to override.            │
└─────────────────────────────────────────────────────────────────┘
```

### Step 9 — Risk Manager
**VERDICT: REJECT**
- Position Size: OK — at GOOD tier max (€2,220 / ~$182.9 eq., ~12 shares of NVDA at €182.9/sh EUR-equiv), well within cap; dollar risk at full size ≈ €163 (0.22% of account), far under the 2% capital-risk rule.
- Portfolio Exposure: OK — Technology sector, no conflict with DVN (Energy); 4/5 slots free.
- R:R Ratio: OK (MARGINAL) — 1.52:1, barely clears the 1.5:1 minimum.
- Drawdown Status: OK — no drawdown data provided this session.
- Stop-Loss: WARNING — stop distance 7.34% from entry (>5% threshold), wider than typical swing structure; not arbitrary (below 200MA/support) but flag the width.
- Volatility Context: **ELEVATED** — trading directly against a CONFIRMED Kindleberger Stage 4 short-bias sector call, with CYCLE OVERRIDE active, insider selling $653M/MSPR -98.6, and Smart Money Score 35 (CONTRARIAN). Research findings (Amodei slow-down warning, OpenAI IPO delay, chip sector -20% from June highs) reinforce rather than contradict the macro thesis.

REJECT rationale: no single hard RISK.md rule is breached (stop exists, R:R clears 1.5, position sizing is fine), but per alt-data-agent.md ("<40 BEARISH — alt data works against the trade; document reason before proceeding") and institutional-flow.md ("<40 STAND DOWN — do not proceed unless technical+fundamental case is exceptional AND institutional selling is documented as unrelated to the thesis"), neither condition for overriding is met here — the insider selling and sector weakness are directly related to the AI-infrastructure short-bias thesis, not an unrelated technical factor. Risk-manager exercises judgment to REJECT despite a technically-clearing R:R.

---

## FIS — Fidelity National Information Services

### Step 5 — Market Researcher

**1. News Catalysts**
- Summary: Business momentum positive, analyst view lukewarm-to-neutral.
- Piper Sandler initiated coverage **Neutral**, PT $42 (Sept 11, 2026).
- Core banking franchise momentum: signed a new bank client with ~$100B in assets, five new de novo bank charters in H1 2026. Management cites three tailwinds: resurgence in new bank launches, accelerating bank consolidation, legacy core-banking modernization demand.
- Quarterly dividend $0.44/share, payable Sept 25, 2026 (record date Sept 11).
- No FDA/M&A/regulatory items found.

**2. Sentiment & Narrative**
- Analyst PT trend: blended target trimmed slightly to ~$56.55 from ~$58.45 — mild downward revision despite the Neutral initiation.
- Stock down ~44.5% over the trailing year — long-term underperformer despite the recent business-momentum narrative.
- Short interest: [NO DATA] — FIS not present in `alt_data.json`.
- Narrative: mixed — improving operational story (new client wins, dividend intact) vs weak multi-year price trend and only-Neutral fresh coverage.

**3. Institutional & Options Activity**
- [NO DATA] — no live 13F/dark-pool/options feed this session.

**4. Sector Rotation Signals**
- FIS classified fintech/payments; nearest sector proxy XLF (Financials): rank 5 of 11, ret_1m -2.42%, ret_5d -0.79%, below MA50 — mild sector headwind, not severe.
- XLK (if treated as "Technology" per batch header) also weak (rank 7, -3.69% 1m) — either proxy points mildly negative, not a tailwind.

**5. Market Structure Summary**
- **Live discrepancy flag**: today's refreshed `market_data.json` shows FIS at $37.34 (trend "sideways", volume ratio 0.96, setup reclassified **"neutral"**, conviction downgraded to **"Low"**) — this differs from the batch's assigned Medium-conviction "pullback" classification. The stock also spiked to $40.05 on Sept 14 (+5% day) before pulling back to $37.34 today (-2.2%) — real whipsaw in the last 48h.
- Price sits essentially at support (37.29, dist 0.13%) with RSI 34.91 (approaching oversold) — could still be read as a valid pullback-to-support entry, but the scan engine's own live re-run downgraded it. Flag for re-verification before execution.
- 50MA 41.25 / 200MA 47.71 — price well below both, confirming a longer-term downtrend context, not a clean Stage-2 uptrend.

**6. Upcoming Risk Events**
- Earnings date: [UNCONFIRMED] — not in earnings_calendar.json, no near-term date surfaced in search.
- Dividend ex-date already passed (Sept 11) relative to today — no impact on this entry.

### Step 6 — Alt Data Agent
```
┌─────────────────────────────────────────────────────────────────┐
│  ALT DATA VERDICT — FIS — 2026-09-16                             │
├─────────────────────────────────────────────────────────────────┤
│  Alt Data Score    : 50 (DEFAULT — DATA UNAVAILABLE)              │
│  Signal            : NEUTRAL                                       │
│  Flags             : DATA_UNAVAILABLE                              │
├─────────────────────────────────────────────────────────────────┤
│  Insider / Short Interest / Analyst Trend / News Sentiment:        │
│  FIS is not present in data/alt_data.json this run — no insider,  │
│  short-interest, MSPR, analyst-trend, or VADER data available for │
│  this ticker. Per fallback rule: flag DATA UNAVAILABLE, do not    │
│  fabricate signals, score neutral (50) by default.                │
├─────────────────────────────────────────────────────────────────┤
│  Interpretation    : No alt-data coverage this run — decision must │
│  rely on technical/fundamental/research inputs only.               │
└─────────────────────────────────────────────────────────────────┘
```

### Step 7 — Strategy Analyst
```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY VERDICT — FIS — 2026-09-16                              │
├─────────────────────────────────────────────────────────────────┤
│  Direction     : LONG                                             │
│  Strategy      : SWING                                            │
│  Holding Period: 5–15 days                                        │
│  Timeframe     : Daily chart                                      │
├─────────────────────────────────────────────────────────────────┤
│  Entry         : 38.18 — pullback toward support (37.29)          │
│  Entry Method  : Pullback / MA bounce                             │
│  Entry Timing  : 10:00–11:30 window                                │
│  Stop          : 35.6096 — below support                           │
│  Target        : 42.3408                                           │
│  R:R           : 1.62                                              │
├─────────────────────────────────────────────────────────────────┤
│  Position Mgmt                                                    │
│  Add at        : No add (CYCLE OVERRIDE active)                    │
│  Trim at       : +1.5R                                             │
│  Trail from    : +1R → breakeven                                   │
├─────────────────────────────────────────────────────────────────┤
│  Hold while    : Setup structure re-confirms Medium conviction     │
│  Exit if       : Impulse turns Red; 10 days no progress;           │
│                  setup fails to reconfirm pullback structure       │
│  Max hold      : 10 trading days                                   │
├─────────────────────────────────────────────────────────────────┤
│  Thesis        : Pullback to support in a name with improving core-│
│                  banking business momentum (new $100B client, 5    │
│                  de novo charters)                                 │
│  Main Risk     : Live technical setup already downgraded to Low   │
│                  conviction/neutral in today's intraday re-run —   │
│                  the pullback structure may not be re-confirming   │
│  Earnings Risk : CLEAR [UNCONFIRMED — no date found]                │
└─────────────────────────────────────────────────────────────────┘
```

### Step 8 — Institutional Flow (per-ticker verdict only)
```
┌─────────────────────────────────────────────────────────────────┐
│  INSTITUTIONAL VERDICT — FIS — 2026-09-16                         │
├─────────────────────────────────────────────────────────────────┤
│  Smart Money Score : 45                                            │
│  Alignment         : CAUTIOUS                                      │
├─────────────────────────────────────────────────────────────────┤
│  13F Consensus     : UNKNOWN — DATA UNAVAILABLE                    │
│  Notable holders   : [NO DATA]                                     │
│  Activist flag     : NONE found                                    │
├─────────────────────────────────────────────────────────────────┤
│  Dark Pool         : DATA UNAVAILABLE — default NORMAL             │
│  Options Flow      : DATA UNAVAILABLE — default NEUTRAL            │
├─────────────────────────────────────────────────────────────────┤
│  Sector ETF        : XLF proxy — ret_1m -2.42%, <MA50              │
│  ETF Signal        : mild HEADWIND                                  │
├─────────────────────────────────────────────────────────────────┤
│  Dry Powder        : DATA UNAVAILABLE — default NORMAL             │
├─────────────────────────────────────────────────────────────────┤
│  WAIT                                                               │
│  Reason            : No hard institutional data this session; only │
│                      real signal (sector ETF) is a mild headwind.  │
└─────────────────────────────────────────────────────────────────┘
```

### Step 9 — Risk Manager
**VERDICT: CAUTION**
- Position Size: OK — GOOD tier max €2,220 (~$2,560, ~67 shares at $38.18), within cap; dollar risk at full size ≈ €149 (0.20% of account).
- Portfolio Exposure: OK — Technology/fintech sector, no conflict.
- R:R Ratio: OK (MARGINAL) — 1.62:1.
- Drawdown Status: OK — no data.
- Stop-Loss: WARNING — 6.73% stop distance (>5%).
- Volatility Context: OK, macro-agnostic name today — but flag ELEVATED on a different axis: live re-run of the scan already downgraded this setup to Low conviction/neutral, and the stock whipsawed +5%/-2.2% in the last 48h. Not a macro-thesis conflict, but a genuine intraday technical-stability concern.

CAUTION rationale: no hard rule violated (R:R clears, stop defined, sizing fine), but re-verify the pullback structure holds before executing — today's live scan data no longer classifies this as a Medium-conviction pullback. Recommend confirming price action at/near support before filling, or reduce size until reconfirmed.

---

## PBF — PBF Energy

### Step 5 — Market Researcher

**1. News Catalysts**
- Summary: Strong positive fundamental momentum, but price has already run hard — chase risk is the dominant issue today.
- **Morgan Stanley raised PT to $76 from $38** (a doubling of target) — a major bullish analyst revision, though note $76 is still below our stated target of $82.61.
- White House reportedly weighing use of the Defense Production Act to expand US refining capacity — sector-level bullish catalyst for refiners.
- New exchangeable notes issuance + debt redemption announced — balance sheet management.
- Net debt cut >62% in Q2 to ~$855M; operational liquidity >$3.5B; run-rate cost improvements >$230M (2025), targeting >$350M by year-end 2026.
- Zacks 2026 EPS consensus estimate up **43.9% in the past 4 weeks** — major positive earnings-revision momentum.

**2. Sentiment & Narrative**
- Stock up **168% over the past year**, **+19.3% in the past month alone** — already a large, extended move.
- Narrative: strongly bullish (refining margins, DPA tailwind, debt paydown, estimate revisions all pointing the same direction) — but bullish narrative + already-extended price = elevated chase risk, not a fresh entry point.
- Short interest: [NO DATA] — PBF not present in alt_data.json this run.

**3. Institutional & Options Activity**
- [NO DATA] — no live 13F/dark-pool/options feed.

**4. Sector Rotation Signals**
- XLE (Energy): rank 2 of 11 US sectors, ret_1m **+7.98%**, ret_5d +1.79%, above MA50 — genuine, strong sector tailwind (oil elevated post-Saudi disruption per macro report).
- This is one of the two names in the batch that sits on the macro TAILWIND side of today's regime call.

**5. Market Structure Summary**
- **Critical live discrepancy**: assigned entry was $70.4; today's refreshed `market_data.json` shows PBF at **$74.72, up +6.14% intraday**, volume ratio **3.29x** (vs 2.77x assigned) — price has already moved materially away from the stated entry, and the scan's live re-run downgraded conviction to **Low** / setup to **"neutral"** (no longer "pullback" — the pullback has already resolved upward).
- At current live price ($74.72), the effective R:R against the original stop/target ($61.9657 / $82.61) collapses to roughly **0.62:1** (risk $12.75 vs reward $7.89) — materially worse than the stated 1.45:1 at the original $70.4 entry.
- RSI 64.11 (approaching overbought), price at new 52-week high ($82.61 = 52w high = the stated target itself), dist_resist_pct only 10.56% because resistance = the fresh high.

**6. Upcoming Risk Events**
- Earnings date: [UNCONFIRMED] — not in earnings_calendar.json.
- DPA refining-capacity policy decision timeline: [UNCONFIRMED], no specific date.

### Step 6 — Alt Data Agent
```
┌─────────────────────────────────────────────────────────────────┐
│  ALT DATA VERDICT — PBF — 2026-09-16                             │
├─────────────────────────────────────────────────────────────────┤
│  Alt Data Score    : 50 (DEFAULT — DATA UNAVAILABLE)              │
│  Signal            : NEUTRAL                                       │
│  Flags             : DATA_UNAVAILABLE                              │
├─────────────────────────────────────────────────────────────────┤
│  PBF is not present in data/alt_data.json this run — no insider,  │
│  short-interest, MSPR, analyst-trend, or VADER data available.    │
│  Per fallback rule: flag DATA UNAVAILABLE, score neutral (50).    │
├─────────────────────────────────────────────────────────────────┤
│  Interpretation    : No alt-data coverage — rely on research/      │
│  technical inputs; note the strong Zacks estimate-revision signal  │
│  (+43.9% 4wk) found via market-researcher is a de facto positive   │
│  fundamental-momentum proxy even without alt-data coverage.        │
└─────────────────────────────────────────────────────────────────┘
```

### Step 7 — Strategy Analyst
```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY VERDICT — PBF — 2026-09-16                              │
├─────────────────────────────────────────────────────────────────┤
│  Direction     : LONG                                             │
│  Strategy      : SWING                                            │
│  Holding Period: 5–15 days                                        │
│  Timeframe     : Daily chart                                      │
├─────────────────────────────────────────────────────────────────┤
│  Entry         : 70.4 (STALE — live price already $74.72, +6.1%   │
│                  above stated entry; do not chase at market)       │
│  Entry Method  : Pullback (as originally scanned — no longer valid │
│                  at current live price)                            │
│  Entry Timing  : N/A — re-evaluate before any entry                │
│  Stop          : 61.9657 — structural                              │
│  Target        : 82.61 (= 52-week high)                            │
│  R:R           : 1.45 as stated (FAILS 1.5 minimum); ~0.62 at live │
│                  price — degrades further if chased                │
├─────────────────────────────────────────────────────────────────┤
│  Position Mgmt                                                    │
│  Add at        : No add                                            │
│  Trim at       : N/A given R:R fail                                │
│  Trail from    : N/A                                               │
├─────────────────────────────────────────────────────────────────┤
│  Hold while    : N/A                                               │
│  Exit if       : N/A — do not enter at current structure           │
│  Max hold      : N/A                                               │
├─────────────────────────────────────────────────────────────────┤
│  Thesis        : Strong refining-sector tailwind (XLE +7.98% 1m,   │
│                  DPA policy tailwind) and major positive estimate  │
│                  revisions support the business — but entry is     │
│                  structurally too extended today                   │
│  Main Risk     : Chasing an already +19.3%/month, +168%/year move  │
│                  into new highs with a sub-1.5 R:R                 │
│  Earnings Risk : CLEAR [UNCONFIRMED]                                │
└─────────────────────────────────────────────────────────────────┘
```

### Step 8 — Institutional Flow (per-ticker verdict only)
```
┌─────────────────────────────────────────────────────────────────┐
│  INSTITUTIONAL VERDICT — PBF — 2026-09-16                         │
├─────────────────────────────────────────────────────────────────┤
│  Smart Money Score : 50                                            │
│  Alignment         : CAUTIOUS                                      │
├─────────────────────────────────────────────────────────────────┤
│  13F/Dark Pool/Options : DATA UNAVAILABLE — defaults applied       │
├─────────────────────────────────────────────────────────────────┤
│  Sector ETF        : XLE — ret_1m +7.98%, above MA50               │
│  ETF Signal        : TAILWIND                                       │
├─────────────────────────────────────────────────────────────────┤
│  Dry Powder        : DATA UNAVAILABLE — default NORMAL             │
├─────────────────────────────────────────────────────────────────┤
│  WAIT                                                               │
│  Reason            : Real sector tailwind (XLE) is the only hard   │
│                      signal; no hard institutional data available  │
│                      to confirm name-specific accumulation at the  │
│                      current extended price.                       │
└─────────────────────────────────────────────────────────────────┘
```

### Step 9 — Risk Manager
**VERDICT: REJECT**
- Position Size: OK — GOOD tier max €2,220 (~$2,560, ~36 shares at $70.4), within cap.
- Portfolio Exposure: WARNING (context) — Energy sector; DVN already occupies 1 of 2 Energy slots, and EQT (this same batch) also competes for the last one — at most 1 of {PBF, EQT} can be approved session-wide even independent of other issues.
- R:R Ratio: **FAIL** — 1.45:1 as stated, below the 1.5:1 RISK.md minimum; degrades to ~0.62:1 at the live price ($74.72).
- Drawdown Status: OK — no data.
- Stop-Loss: WARNING — 11.98% stop distance from stated entry, the widest in this batch.
- Volatility Context: OK on macro (genuine Energy tailwind per macro report) — but ELEVATED on chase-risk grounds: price already +6.1% intraday beyond the stated entry, live scan re-run downgraded conviction to Low/neutral.

REJECT rationale: RISK.md rule violated — R:R below the 1.5:1 minimum (1.45:1 stated, and materially worse at the current live price). Independent of the macro tailwind and strong fundamentals, this fails the hard R:R gate and the entry is stale/already-run. Re-scan on a pullback to a level that restores R:R ≥1.5 before reconsidering.

---

## BNR.DE — Brenntag SE

### Step 5 — Market Researcher

**1. News Catalysts**
- Summary: Quiet, stable — no major catalysts, positive but low-volume news flow.
- Stock trading in a stable range in mid-September, digesting recently reported earnings; market focus is on profitability/cash flow versus current valuation.
- No M&A, management-change, or regulatory items found.
- No FDA-equivalent or sector-shock catalysts identified.

**2. Sentiment & Narrative**
- Narrative: quietly positive — alt-data shows news sentiment **0.464 (POSITIVE) and RISING** (velocity), the strongest sentiment-momentum signal in this batch, though on thin coverage (5 articles/5d).
- Analyst ratings/PT trend: [NO DATA] — no analyst coverage found in alt_data.json (NO_DATA status).
- Short interest: [NO DATA] — unavailable for this EU ticker (expected per alt-data-agent.md EU-sparse-coverage rule).

**3. Institutional & Options Activity**
- [NO DATA] — no live 13F/ESMA/dark-pool/options feed accessible this session; per institutional-flow.md, ESMA large-shareholder filings are the EU 13F-equivalent but not accessible here — [UNCONFIRMED].

**4. Sector Rotation Signals**
- No direct EU "chemical distribution" ETF; closest proxies are EU Basic Resources (EXV6.DE, rank 11/12, ret_1m +0.39% but ret_5d **-5.26%**) — recent-week weakness despite flat monthly return.
- Sector rotation signal: mixed/weak — not a clean tailwind.

**5. Market Structure Summary**
- Price $61.12, trend up, at 50MA ($60.50)/well above 200MA ($54.60).
- Volume ratio 0.76 (below average) — pullback on light volume, not distribution, but also no strong accumulation signature.
- RSI 48.11 — neutral.
- Support 60.28 / resistance 63.72; dist to resistance only 4.25% — target is a near-term level, not a breakout to new highs.

**6. Upcoming Risk Events**
- Earnings date: [UNCONFIRMED] — not in earnings_calendar.json; last reported results already digested per news.
- No other scheduled catalysts identified.

### Step 6 — Alt Data Agent
```
┌─────────────────────────────────────────────────────────────────┐
│  ALT DATA VERDICT — BNR.DE — 2026-09-16                          │
├─────────────────────────────────────────────────────────────────┤
│  Alt Data Score    : 51                                            │
│  Signal            : NEUTRAL                                       │
│  Flags             : NEWS_ACCELERATING                             │
├─────────────────────────────────────────────────────────────────┤
│  Insider           : NONE — DATA_THIN (EU ticker, insider data     │
│                      via yfinance sparse for EU exchanges)         │
│  Insider MSPR      : UNAVAILABLE                                   │
├─────────────────────────────────────────────────────────────────┤
│  Short Interest    : UNKNOWN — data unavailable                    │
│  Squeeze watch     : NO                                            │
├─────────────────────────────────────────────────────────────────┤
│  Analyst Trend     : NO_DATA — no coverage found                   │
├─────────────────────────────────────────────────────────────────┤
│  News Sentiment    : 0.464 (POSITIVE)                              │
│  Velocity          : RISING                                        │
│  Articles scored   : 5 in last 5 days (thin — DATA_THIN caution)   │
├─────────────────────────────────────────────────────────────────┤
│  Interpretation    : Positive and building news narrative is the   │
│  only real signal; insider/short/analyst data absent is expected  │
│  EU-coverage sparsity, not a bearish signal in itself.             │
└─────────────────────────────────────────────────────────────────┘
```

### Step 7 — Strategy Analyst
```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY VERDICT — BNR.DE — 2026-09-16                           │
├─────────────────────────────────────────────────────────────────┤
│  Direction     : LONG                                             │
│  Strategy      : SWING                                            │
│  Holding Period: 5–15 days                                        │
│  Timeframe     : Daily chart                                      │
├─────────────────────────────────────────────────────────────────┤
│  Entry         : 61.12 — pullback to 50MA (60.50)                 │
│  Entry Method  : MA bounce / pullback                              │
│  Entry Timing  : 10:00–11:30 (EU session)                          │
│  Stop          : 58.4629 — below support (60.28)                   │
│  Target        : 63.72                                             │
│  R:R           : 0.98 — FAILS 1.5:1 minimum                        │
├─────────────────────────────────────────────────────────────────┤
│  Position Mgmt : N/A — setup fails minimum R:R, do not size         │
├─────────────────────────────────────────────────────────────────┤
│  Hold while    : N/A                                               │
│  Exit if       : N/A                                               │
│  Max hold      : N/A                                               │
├─────────────────────────────────────────────────────────────────┤
│  Thesis        : Rising news-sentiment momentum in a name pulling  │
│                  back to its 50MA in an intact uptrend              │
│  Main Risk     : Target (63.72) is too close to entry relative to  │
│                  stop distance — the setup's own R:R math doesn't  │
│                  clear the system's minimum, independent of thesis │
│  Earnings Risk : CLEAR [UNCONFIRMED]                                │
└─────────────────────────────────────────────────────────────────┘
```

### Step 8 — Institutional Flow (per-ticker verdict only)
```
┌─────────────────────────────────────────────────────────────────┐
│  INSTITUTIONAL VERDICT — BNR.DE — 2026-09-16                      │
├─────────────────────────────────────────────────────────────────┤
│  Smart Money Score : 45                                            │
│  Alignment         : CAUTIOUS                                      │
├─────────────────────────────────────────────────────────────────┤
│  13F/ESMA/Dark Pool/Options : DATA UNAVAILABLE — defaults applied  │
├─────────────────────────────────────────────────────────────────┤
│  Sector ETF        : EU Basic Resources proxy — ret_5d -5.26%      │
│  ETF Signal        : mild HEADWIND (recent week), flat month        │
├─────────────────────────────────────────────────────────────────┤
│  Dry Powder        : DATA UNAVAILABLE — default NORMAL             │
├─────────────────────────────────────────────────────────────────┤
│  WAIT                                                               │
│  Reason            : No hard institutional data (typical for EU    │
│                      mid-cap); R:R fail at strategy layer already  │
│                      disqualifies regardless.                      │
└─────────────────────────────────────────────────────────────────┘
```

### Step 9 — Risk Manager
**VERDICT: REJECT**
- Position Size: OK — GOOD tier max €2,220 (~36 shares at €61.12), within cap.
- Portfolio Exposure: OK — Basic Materials, no conflict (DVN is Energy).
- R:R Ratio: **FAIL** — 0.98:1, well below the 1.5:1 RISK.md minimum.
- Drawdown Status: OK — no data.
- Stop-Loss: OK — 4.35% stop distance, within the 5% guide.
- Volatility Context: OK — macro-agnostic name today, no direct short-bias sector flag; mild sector-relative weakness noted (EU Basic Resources -5.26% 5d) but not disqualifying on its own.

REJECT rationale: RISK.md rule violated — R:R (0.98:1) is well under the 1.5:1 minimum. This is the clearest and simplest disqualifier in the batch; nothing else needs to be weighed.

---

## EQT — EQT Corp

### Step 5 — Market Researcher

**1. News Catalysts**
- Summary: Modest positive fundamentals, mixed/slightly negative analyst revisions, direct macro tailwind (oil/gas elevated).
- Analyst activity: mixed — Morgan Stanley cut PT to $67 from $68 (Aug 20), RBC maintained Hold (Aug 21); blended PT trimmed slightly to ~$70.04.
- Most recent quarter: higher production and revenue YoY, supported by production volumes and efficiency gains.
- Quarterly dividend $0.165/share paid Sept 1, 2026 — routine, no surprise.
- Main structural risk flagged by researchers: sensitivity to US natural gas prices, which can compress margins quickly if benchmark contracts move against producers.

**2. Sentiment & Narrative**
- Narrative: neutral-to-mildly-positive — no major bullish or bearish catalyst, "mixed" analyst sentiment as of early September.
- Short interest: alt-data shows **3.73% of float — LOW**, but **+12.2% MoM increase** — bears adding conviction at the margin (mild headwind, tighten stops per alt-data-agent framework).
- Insider MSPR: **BEARISH (-29.6, 3mo avg)** — net insider selling trend over the trailing quarter (1 seller, $9.65M, no buyers in 30d — below the threshold for a "cluster" caution but consistent with the MSPR read).

**3. Institutional & Options Activity**
- [NO DATA] — no live 13F/dark-pool/options feed.

**4. Sector Rotation Signals**
- XLE (Energy): rank 2 of 11, ret_1m **+7.98%**, above MA50 — genuine sector tailwind, oil still elevated post-Saudi-pipeline disruption per macro report. This is the second name in the batch (with PBF) on the macro TAILWIND side.

**5. Market Structure Summary**
- Price $53.12–53.21, trend up, essentially at 50MA (52.81/52.81) — a tight pullback-to-MA setup.
- RSI 42.97 — neutral, no overbought/oversold extreme.
- Support 52.52 / resistance 56.52; dist to resistance 6.4%.
- Note: price is below its 200MA (55.77) despite being above its 50MA — a mixed intermediate-term structure, not a clean Stage-2 uptrend.

**6. Upcoming Risk Events**
- Earnings date: [UNCONFIRMED] — not in earnings_calendar.json.
- Natural gas price volatility is the standing structural risk (no single dated event, ongoing).

### Step 6 — Alt Data Agent
```
┌─────────────────────────────────────────────────────────────────┐
│  ALT DATA VERDICT — EQT — 2026-09-16                             │
├─────────────────────────────────────────────────────────────────┤
│  Alt Data Score    : 43                                            │
│  Signal            : NEUTRAL                                       │
│  Flags             : INSIDER_MSPR_BEARISH                          │
├─────────────────────────────────────────────────────────────────┤
│  Insider           : NONE (no 30d cluster) — but net SELL          │
│  Net 30d           : -$9,648,300 sold (0 buyers, 1 seller)         │
│  Insider MSPR      : BEARISH (-29.6, 3mo avg)                      │
├─────────────────────────────────────────────────────────────────┤
│  Short Interest    : 3.73% of float  DTC: 3.3 days — LOW           │
│  MoM change        : +12.2% rising — bears adding conviction        │
│  Squeeze watch     : NO                                            │
├─────────────────────────────────────────────────────────────────┤
│  Analyst Trend     : STABLE — 80.0% buy-rated, Δ0.0pp               │
├─────────────────────────────────────────────────────────────────┤
│  News Sentiment    : 0.127 (NEUTRAL), velocity RISING               │
│  Articles scored   : 5 in last 5 days                              │
├─────────────────────────────────────────────────────────────────┤
│  Interpretation    : No disqualifying insider cluster, but MSPR    │
│  bearish trend + rising short interest MoM is a real, mild caution │
│  layer on top of an otherwise stable analyst/news picture.         │
└─────────────────────────────────────────────────────────────────┘
```

### Step 7 — Strategy Analyst
```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY VERDICT — EQT — 2026-09-16                              │
├─────────────────────────────────────────────────────────────────┤
│  Direction     : LONG                                             │
│  Strategy      : SWING                                            │
│  Holding Period: 5–15 days                                        │
│  Timeframe     : Daily chart                                      │
├─────────────────────────────────────────────────────────────────┤
│  Entry         : 53.21 — pullback to 50MA                          │
│  Entry Method  : MA bounce / pullback                              │
│  Entry Timing  : 10:00–11:30                                       │
│  Stop          : 50.1571 — below support (52.52)                   │
│  Target        : 56.52                                             │
│  R:R           : 1.08 — FAILS 1.5:1 minimum                        │
├─────────────────────────────────────────────────────────────────┤
│  Position Mgmt : N/A — setup fails minimum R:R, do not size         │
├─────────────────────────────────────────────────────────────────┤
│  Hold while    : N/A                                               │
│  Exit if       : N/A                                               │
│  Max hold      : N/A                                               │
├─────────────────────────────────────────────────────────────────┤
│  Thesis        : Energy-sector tailwind (XLE +7.98% 1m) supports   │
│                  the name, but target is too close to entry given  │
│                  the required stop distance                        │
│  Main Risk     : Natural-gas price sensitivity can compress        │
│                  margins quickly; R:R math itself disqualifies      │
│  Earnings Risk : CLEAR [UNCONFIRMED]                                │
└─────────────────────────────────────────────────────────────────┘
```

### Step 8 — Institutional Flow (per-ticker verdict only)
```
┌─────────────────────────────────────────────────────────────────┐
│  INSTITUTIONAL VERDICT — EQT — 2026-09-16                         │
├─────────────────────────────────────────────────────────────────┤
│  Smart Money Score : 50                                            │
│  Alignment         : CAUTIOUS                                      │
├─────────────────────────────────────────────────────────────────┤
│  13F/Dark Pool/Options : DATA UNAVAILABLE — defaults applied       │
├─────────────────────────────────────────────────────────────────┤
│  Sector ETF        : XLE — ret_1m +7.98%, above MA50               │
│  ETF Signal        : TAILWIND                                       │
├─────────────────────────────────────────────────────────────────┤
│  Dry Powder        : DATA UNAVAILABLE — default NORMAL             │
├─────────────────────────────────────────────────────────────────┤
│  WAIT                                                               │
│  Reason            : Real sector tailwind present, but R:R fail at │
│                      strategy layer already disqualifies the trade │
│                      regardless of institutional read.              │
└─────────────────────────────────────────────────────────────────┘
```

### Step 9 — Risk Manager
**VERDICT: REJECT**
- Position Size: OK — GOOD tier max €2,220 (~41 shares at $53.21), within cap.
- Portfolio Exposure: WARNING (context) — Energy sector; DVN already occupies 1 of 2 Energy slots, competing with PBF (this batch) for the last one — moot given the hard R:R fail below.
- R:R Ratio: **FAIL** — 1.08:1, well below the 1.5:1 RISK.md minimum.
- Drawdown Status: OK — no data.
- Stop-Loss: WARNING — 5.74% stop distance, just above the 5% guide.
- Volatility Context: OK on macro (genuine Energy tailwind) — mild caution from rising short interest MoM (+12.2%) and bearish MSPR (-29.6), not disqualifying on their own.

REJECT rationale: RISK.md rule violated — R:R (1.08:1) is well under the 1.5:1 minimum. Genuine sector tailwind noted for context but does not override the hard R:R gate.

---

## BZU.MI — Buzzi S.p.A.

### Step 5 — Market Researcher

**1. News Catalysts**
- Summary: Stable, positive earnings digestion; no near-term dated catalyst.
- Stock holding steady in September on "solid recent results"; cement-sector demand trends being watched by investors.
- Valuation: P/E ~8.92 (as of ~Sept 7), described in coverage as a potential value play — low P/E, trading near book value.
- Key open question raised by researchers: whether Buzzi can convert its strong balance sheet and US exposure into sustainable earnings growth while protecting margins from energy costs, currency moves, and weaker construction demand.
- Next scheduled trading update: **November 5, 2026** — well outside any near-term hold period.

**2. Sentiment & Narrative**
- News sentiment (alt-data): **0.771 (POSITIVE)**, the most positive score in this batch, though STABLE (not rising) and on thin coverage (4 articles/5d — DATA_THIN).
- Analyst coverage: [NO DATA] — none found in alt_data.json.
- Narrative: quietly constructive value-stock story, tempered by explicit "margin pressure" and "cyclical construction demand" concerns in coverage.

**3. Institutional & Options Activity**
- [NO DATA] — no live 13F/ESMA/dark-pool/options feed this session.

**4. Sector Rotation Signals**
- No direct EU cement ETF; closest proxies: EU Construction (EXV8.DE, rank **12 of 12** — last place, ret_1m **-8.56%**, ret_5d -5.56%, below MA50) and EU Basic Resources (rank 11/12, ret_1m +0.39%). Whichever proxy is used, sector-relative momentum is weak-to-poor — this is a genuine (if not officially macro-flagged) sector headwind found independently in research, distinct from the officially-named short-bias sectors.

**5. Market Structure Summary**
- Price $37.73, change -2.96% today, trend "up" per scan but pulling back sharply intraday.
- Volume ratio 1.38 (above average) on a down day — some distribution character on the pullback, worth noting.
- RSI 41.09 — neutral-to-soft.
- Price below 50MA (41.42) and well below 200MA (45.63) — despite "trend: up" classification, the intermediate/long-term MAs argue this is still a corrective bounce inside a larger downtrend from the 52-week high (53.89).
- Distance to resistance/target (41.85) is 10.92% — a real breakout is required to hit target, not just a minor pullback fill.

**6. Upcoming Risk Events**
- Next trading update: Nov 5, 2026 — CLEAR of any near-term hold period.
- No FDA/M&A/regulatory items identified.

### Step 6 — Alt Data Agent
```
┌─────────────────────────────────────────────────────────────────┐
│  ALT DATA VERDICT — BZU.MI — 2026-09-16                          │
├─────────────────────────────────────────────────────────────────┤
│  Alt Data Score    : 46                                            │
│  Signal            : NEUTRAL                                       │
│  Flags             : none                                          │
├─────────────────────────────────────────────────────────────────┤
│  Insider           : NONE — DATA_THIN (EU ticker)                  │
│  Insider MSPR      : UNAVAILABLE                                   │
├─────────────────────────────────────────────────────────────────┤
│  Short Interest    : UNKNOWN — data unavailable                    │
├─────────────────────────────────────────────────────────────────┤
│  Analyst Trend     : NO_DATA                                       │
├─────────────────────────────────────────────────────────────────┤
│  News Sentiment    : 0.771 (POSITIVE), velocity STABLE             │
│  Articles scored   : 4 in last 5 days — DATA_THIN (low confidence) │
├─────────────────────────────────────────────────────────────────┤
│  Interpretation    : Strongly positive but thin-coverage news is   │
│  the only real signal; absence of insider/short/analyst data is   │
│  expected EU sparsity, not a bearish read.                         │
└─────────────────────────────────────────────────────────────────┘
```

### Step 7 — Strategy Analyst
```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY VERDICT — BZU.MI — 2026-09-16                           │
├─────────────────────────────────────────────────────────────────┤
│  Direction     : LONG                                             │
│  Strategy      : SWING                                            │
│  Holding Period: 5–15 days                                        │
│  Timeframe     : Daily chart                                      │
├─────────────────────────────────────────────────────────────────┤
│  Entry         : 37.73 — pullback near support (37.28)            │
│  Entry Method  : Pullback                                          │
│  Entry Timing  : 10:00–11:30 (EU session)                          │
│  Stop          : 35.3157 — below support                           │
│  Target        : 41.85                                             │
│  R:R           : 1.71                                              │
├─────────────────────────────────────────────────────────────────┤
│  Position Mgmt                                                    │
│  Add at        : No add (CYCLE OVERRIDE active)                    │
│  Trim at       : +1.5R                                             │
│  Trail from    : +1R → breakeven                                   │
├─────────────────────────────────────────────────────────────────┤
│  Hold while    : Price holds above stop; sector proxy doesn't      │
│                  deteriorate further                                │
│  Exit if       : Impulse turns Red; 10 days no progress; breaks    │
│                  below 200MA-area structure                         │
│  Max hold      : 10 trading days                                   │
├─────────────────────────────────────────────────────────────────┤
│  Thesis        : Value-stock pullback to support (low P/E, near    │
│                  book value) with strongly positive news sentiment │
│  Main Risk     : EU Construction/Basic-Resources sector proxies    │
│                  both showing weak relative momentum (-5% to -9%   │
│                  1m); today's -2.96% day came on above-average     │
│                  volume — watch for distribution, not accumulation │
│  Earnings Risk : CLEAR — next update Nov 5, 2026                   │
└─────────────────────────────────────────────────────────────────┘
```

### Step 8 — Institutional Flow (per-ticker verdict only)
```
┌─────────────────────────────────────────────────────────────────┐
│  INSTITUTIONAL VERDICT — BZU.MI — 2026-09-16                      │
├─────────────────────────────────────────────────────────────────┤
│  Smart Money Score : 40                                            │
│  Alignment         : CAUTIOUS (borderline — one point above        │
│                      CONTRARIAN threshold)                          │
├─────────────────────────────────────────────────────────────────┤
│  13F/ESMA/Dark Pool/Options : DATA UNAVAILABLE — defaults applied  │
├─────────────────────────────────────────────────────────────────┤
│  Sector ETF        : EU Construction proxy — ret_1m -8.56%, <MA50  │
│  ETF Signal        : HEADWIND                                       │
├─────────────────────────────────────────────────────────────────┤
│  Dry Powder        : DATA UNAVAILABLE — default NORMAL             │
├─────────────────────────────────────────────────────────────────┤
│  WAIT                                                               │
│  Reason            : No hard institutional data (typical for EU    │
│                      mid-cap); the one real signal available       │
│                      (sector ETF proxy) is a headwind, borderline   │
│                      CONTRARIAN — proceed only with awareness.      │
└─────────────────────────────────────────────────────────────────┘
```

### Step 9 — Risk Manager
**VERDICT: CAUTION**
- Position Size: OK — GOOD tier max €2,220 (~58 shares at €37.73), within cap.
- Portfolio Exposure: OK — Basic Materials, no conflict (DVN is Energy); if BNR.DE were also approved this would be the 2nd Basic Materials name (cap is 2/sector) — BNR.DE is REJECTed above on R:R, so no conflict in practice.
- R:R Ratio: OK (MARGINAL) — 1.71:1.
- Drawdown Status: OK — no data.
- Stop-Loss: WARNING — 6.40% stop distance (>5%).
- Volatility Context: ELEVATED (sector-specific, not macro-thesis) — EU Construction/cement sector-relative momentum is weak (-5% to -9% over 1 month across both plausible proxies) despite the name's own positive news sentiment and up-trend classification; today's decline came on above-average volume.

CAUTION rationale: no hard rule violated (R:R clears, stop defined, sizing fine, macro-agnostic per session brief), but the sector-relative-strength picture found independently in research is weaker than the stock's own price action suggests — recommend standard-or-reduced size and tightening the trail given the sector headwind, rather than a clean APPROVE.

---

## Summary Table

| Ticker | Strategy | Alt Score | Inst Score/Align | Risk Verdict | Key Reason |
|---|---|---|---|---|---|
| NVDA | SWING (CYCLE OVERRIDE blocks POSITION) | 35 BEARISH | 35 ⚠ CONTRARIAN | REJECT | Insider selling $653M + MSPR -98.6 + confirmed sector bear market (Kindleberger Stage 4) stack against an otherwise-clearing setup |
| FIS | SWING | 50 NEUTRAL (no data) | 45 CAUTIOUS | CAUTION | Live scan re-run downgraded setup to Low/neutral intraday; R:R clears but structure needs reconfirmation |
| PBF | SWING | 50 NEUTRAL (no data) | 50 CAUTIOUS | REJECT | R:R fails (1.45<1.5) and price already ran +6.1% past stated entry — chasing risk |
| BNR.DE | SWING | 51 NEUTRAL | 45 CAUTIOUS | REJECT | R:R fails badly (0.98<1.5) |
| EQT | SWING | 43 NEUTRAL | 50 CAUTIOUS | REJECT | R:R fails badly (1.08<1.5); Energy sector slot also contested by PBF |
| BZU.MI | SWING | 46 NEUTRAL | 40 CAUTIOUS (borderline) | CAUTION | R:R clears but EU Construction/cement sector-relative momentum weak (-5% to -9%/1m) |
