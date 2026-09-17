# Scan Batch A — Steps 5-9 — 2026-09-16
Tickers: BESI.AS, GOOG, GOOGL, TER, ALAB (all CONFIRMED, semiconductor/AI-infrastructure space)

**BATCH-LEVEL FLAGS (read before per-ticker detail):**
1. **GOOG / GOOGL double-count risk**: same underlying company (Alphabet dual share class). GOOG has the weaker alt-data/institutional read (Alt Score 42, INSIDER_SELLING flag) vs GOOGL (Alt Score 61, INSIDER_MSPR_BULLISH). Per instructions, GOOG is flagged as the weaker leg — the two must not be treated as independent, uncorrelated positions in institutional-flow or risk-manager sizing.
2. **Sector-cap collision inside this batch alone**: BESI.AS, TER, and ALAB are all tagged "Technology" (semiconductor equipment / test equipment / AI interconnect). Portfolio sector cap is 2/sector. Even before the other 5 parallel batches are reconciled, these three alone exceed the cap — at most 2 of {BESI.AS, TER, ALAB} can ultimately be approved together. Flagged provisionally on all three; final call deferred to central cross-batch reconciliation.
3. **Macro overlay applied throughout**: Stagflation CONFIRMED today, Fed hiked 25bp into elevated leverage (Minsky escalated 5/7→6/7), 10Y closed >5% for first time since 2007. Directional Bias = SHORT BIAS, with Semiconductors/AI infrastructure explicitly named (Kindleberger Stage 3/4, semis CONFIRMED Stage 4, chip sector -20%+ bear market, SOXX broke into bear market territory, Ed Yardeni sees another -12% to the 200dma). Per instructions, every long entry in this batch is treated as ELEVATED RISK / trading against the macro grain, and this is weighed explicitly into each risk-manager verdict below rather than applied silently.

---

## BESI.AS — BE Semiconductor Industries (Netherlands)

### Step 5 — Market Researcher

**1. News Catalysts** — Verdict: no near-term catalyst; last quarter (Q2/H1) was a strong beat.
- Earnings: next report Oct 22, 2026 [OUTSIDE 5-day window]. Q2/H1 2026 showed record revenue and order growth (AI, photonics, data-center demand), net income and margins sharply higher y/y. [UNCONFIRMED exact beat/miss magnitude]
- No new contracts/M&A/management-change news found in search window.
- Macro: today's Fed hike + Kindleberger Stage-4 semis call is a direct sector headwind (see Step 9).

**2. Sentiment & Narrative** — Verdict: bullish sell-side, but riding a sector-wide pullback.
- Analyst ratings: consensus "Buy" — 15 buy / 8 hold / 0 sell of 23 analysts. Avg 12-mo target €296.57–303.77 (high €401–421, low €173–175) — implies large upside from current ~€176 level, but much of that gap is because the stock has fallen with the broader chip bear market, not because targets just moved.
- Short interest: [NO DATA — EU ticker, sparse coverage, DATA_THIN per alt-data rule, not a bearish signal].
- Narrative: broadly bullish long-term (AI/photonics demand), but the stock is currently caught in the sector-wide de-rating — narrative is mixed short-term, bullish structurally.

**3. Institutional & Options Activity** — Verdict: no confirmed data.
- Institutional ownership trend: [NO DATA — EU 13F-equivalent (ESMA) not retrieved live].
- Hedge fund positioning: [NO DATA].
- Options flow: [NO DATA — Euronext options flow not covered by standard US-centric sources].
- Dark pool/block trades: [NO DATA].

**4. Sector Rotation Signals** — Verdict: sector in a confirmed bear market, headwind.
- Global semiconductor complex (SOXX) entered bear market territory, -20%+ from June highs; Ed Yardeni flags another possible -12% to the 200dma. Drivers: Samsung/SK Hynix margin-call pressure, Moonshot's Kimi K3 model reviving AI-commoditization fears, TSMC results failing to lift sentiment despite beats.
- BESI's own price action (€196–214 range Sept 7-14 vs entry level 175.95) is consistent with this sector-wide de-rating rather than a name-specific issue.
- Peer read: BESI (die-attach/packaging, AI/photonics exposure) is a direct read-through of the same AI-infrastructure capex debate driving TER and ALAB in this batch.

**5. Market Structure Summary** — Verdict: reversal setup at support inside a broader corrective move.
- Technical setup labeled "reversal" by the scan; entry 175.95 sits well below the Sept 7-14 trading range (€196-214), consistent with the sector-wide 2-week chip sell-off.
- [Full weekly-stage/EMA/SMA distances not independently re-derived here — deferred to technical-analyst.md output already produced upstream.]
- Volume ratio 1.92x — elevated but below the 2.0x MOMENTUM threshold.

**6. Upcoming Risk Events** — Verdict: earnings clear of near-term window; BOJ is the nearest macro risk.
- Earnings: Oct 22, 2026 — CLEAR for a swing/short hold, WATCH for anything held into Oct.
- BOJ policy decision Sept 18, 2026 (2 trading days out) — ~97% priced hike, carry-unwind risk live, relevant to global risk sentiment broadly.
- Implied move: [NO DATA — no options-implied-move data available for this EU listing].

### Step 6 — Alt Data Agent

```
┌─────────────────────────────────────────────────────────────────┐
│  ALT DATA VERDICT — BESI.AS — 2026-09-16                        │
├─────────────────────────────────────────────────────────────────┤
│  Alt Data Score    : 51                                          │
│  Signal            : NEUTRAL                                     │
│  Flags             : NEWS_ACCELERATING                           │
├─────────────────────────────────────────────────────────────────┤
│  Insider           : NONE                                        │
│  Net 30d           : neutral (no buyers/sellers recorded)        │
│  Notable           : none                                        │
│  Insider MSPR      : UNAVAILABLE                                 │
├─────────────────────────────────────────────────────────────────┤
│  Short Interest    : UNKNOWN (EU ticker — DATA_THIN, not bearish)│
│  Level             : UNKNOWN                                     │
│  MoM change        : UNKNOWN                                     │
│  Squeeze watch     : NO                                          │
├─────────────────────────────────────────────────────────────────┤
│  Analyst Trend     : NO_DATA                                     │
│  Bull ratio        : N/A (Finnhub coverage absent for this EU    │
│                       listing — sell-side consensus from market- │
│                       researcher step: 15 buy/8 hold/0 sell)      │
│  Congressional*    : NO_API_KEY (ref only)                       │
├─────────────────────────────────────────────────────────────────┤
│  News Sentiment    : 0.151 (POSITIVE)                            │
│  Velocity          : RISING                                      │
│  Articles scored   : 5 in last 5 days (borderline DATA_THIN,     │
│                       flagged per EU-ticker sparse-coverage rule)│
├─────────────────────────────────────────────────────────────────┤
│  Interpretation    : Thin EU alt-data coverage (insider/short/   │
│                      analyst all absent) — no disqualifying      │
│                      signal, but no confirming signal either.    │
│                      Only real data point (rising positive news  │
│                      sentiment) is directionally mild-bullish.   │
└─────────────────────────────────────────────────────────────────┘
```

### Step 7 — Strategy Analyst

```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY VERDICT — BESI.AS — 2026-09-16                        │
├─────────────────────────────────────────────────────────────────┤
│  Direction     : LONG                                            │
│  Strategy      : TURNAROUND                                      │
│  Holding Period: Weeks to months                                 │
│  Timeframe     : Daily reversal within a sector-wide correction  │
├─────────────────────────────────────────────────────────────────┤
│  Entry         : 175.95 — reversal signal at support after the   │
│                   sector-wide chip sell-off                      │
│  Entry Method  : Reversal candle                                 │
│  Entry Timing  : Next session open following confirmed reversal  │
│  Stop          : 158.5071 — structural (below reversal low) —    │
│                   9.91% from entry                                │
│  Target        : 200.20 — prior resistance zone                  │
│  R:R           : 1.39                                            │
├─────────────────────────────────────────────────────────────────┤
│  Position Mgmt                                                   │
│  Add at        : No add (turnaround — do not average into a      │
│                   sector-wide downtrend)                          │
│  Trim at       : Recovery to 50 SMA (25%), 200 SMA (25%)         │
│  Trail from    : +1R → breakeven                                 │
├─────────────────────────────────────────────────────────────────┤
│  Hold while    : F-score/undervalued thesis intact, no earnings  │
│                   miss, sector bear market shows signs of basing │
│  Exit if       : stop hit / new structural low / earnings miss   │
│                   or guidance cut / recovery not visible after   │
│                   2 earnings cycles                                │
│  Max hold      : Reassess each earnings cycle                    │
├─────────────────────────────────────────────────────────────────┤
│  Thesis        : Quality AI/photonics-exposed semi-equipment name│
│                   caught in a sector-wide de-rating, not a        │
│                   company-specific breakdown; record H1 revenue  │
│                   and F-score 67 support a "worst is priced in"  │
│                   recovery thesis.                                │
│  Main Risk     : The stop (9.91%) is wider than both SWING (5%)  │
│                   and POSITION (8%) caps, and R:R (1.39) is below │
│                   the 1.5 floor — this is a genuine structural    │
│                   pullback inside a CONFIRMED sector bear market, │
│                   not a clean reversal setup.                     │
│  Earnings Risk : CLEAR (Oct 22, 2026 — outside hold window start) │
└─────────────────────────────────────────────────────────────────┘
```
Note: classified TURNAROUND rather than SWING specifically because the 9.91% stop exceeds SWING's 5% max; TURNAROUND's 10% max is the only strategy band the stop fits inside at all, and the recovery narrative (AI/photonics demand, CONFIRMED undervalued fundamentals) supports it. Flagging this classification as a close call for risk-manager.

### Step 8 — Institutional Flow (per-ticker verdict only)

```
┌─────────────────────────────────────────────────────────────────┐
│  INSTITUTIONAL VERDICT — BESI.AS — 2026-09-16                   │
├─────────────────────────────────────────────────────────────────┤
│  Smart Money Score : 50 (default — DATA UNAVAILABLE)             │
│  Alignment         : CAUTIOUS                                    │
├─────────────────────────────────────────────────────────────────┤
│  13F Consensus     : DATA UNAVAILABLE (EU listing; ESMA-equivalent│
│                       large-holder data not retrieved live)       │
│  Quarter           : N/A                                          │
│  Notable holders   : none confirmed                                │
│  Lag note          : N/A                                          │
│  Activist flag     : NONE found                                    │
├─────────────────────────────────────────────────────────────────┤
│  Dark Pool         : DATA UNAVAILABLE                              │
│  Direction signal  : UNCLEAR                                       │
├─────────────────────────────────────────────────────────────────┤
│  Options Flow      : DATA UNAVAILABLE (Euronext options flow not  │
│                       covered by standard US-centric sources)      │
│  Detail            : none                                          │
├─────────────────────────────────────────────────────────────────┤
│  Sector ETF        : SOXX (proxy) — confirmed bear market, -20%+  │
│                       from June highs                              │
│  ETF Signal        : HEADWIND                                      │
├─────────────────────────────────────────────────────────────────┤
│  Dry Powder        : DATA UNAVAILABLE                              │
│  Fuel for move     : LOW (per macro report: Minsky escalated to   │
│                       6/7, HY spreads still complacent/tight)      │
├─────────────────────────────────────────────────────────────────┤
│  WAIT                                                              │
│  Reason            : No confirmed institutional data sources for  │
│                       this EU listing; only quantifiable signal    │
│                       (sector ETF proxy) is a clear headwind.      │
└─────────────────────────────────────────────────────────────────┘
```
Per inviolable rule (no data available for a ticker → flag DATA UNAVAILABLE on all five sources, Score = 50 CAUTIOUS default). Sell-side consensus (Buy, 15/23) noted only as reference color from Step 5 — not part of the formal institutional score.

### Step 9 — Risk Manager

**VERDICT: REJECT**

- Position Size: OK (structurally) — would fit under GOOD tier max (€2,220 / 3%) if traded.
- Portfolio Exposure: WARNING — Technology sector; collides with TER and ALAB in this same batch (3 Technology names vs. 2-per-sector cap) — provisional, final call pending cross-batch reconciliation.
- R:R Ratio: **FAIL — 1.39, below the 1.5 minimum required per RISK.md.** This alone disqualifies the trade regardless of other factors.
- Drawdown Status: OK — no drawdown pressure from the single open DVN position.
- Stop-Loss: WARNING — stop defined and structural (below reversal low), but distance is 9.91%, unusually wide (>5% trigger), wider than both SWING (5%) and POSITION (8%) caps; only barely fits inside TURNAROUND's 10% ceiling.
- Volatility Context: ELEVATED — trade is directly against today's SHORT BIAS macro call. Semiconductors/AI infrastructure is explicitly named as the highest-confidence short sector (Kindleberger Stage 4 CONFIRMED, chip sector in a -20%+ bear market, Minsky fragility escalated to 6/7 today). BESI's own research findings (record H1 revenue, Buy consensus) are positive but generic to the AI-capex bull case broadly — they do not specifically contradict the sector-level bear thesis for this name. Per the macro overlay instruction, this leans the verdict toward REJECT rather than overriding it.

**Reason for REJECT**: Hard R:R floor violation (1.39 < 1.5) is sufficient on its own. Compounded by an unusually wide stop that doesn't cleanly fit any strategy tier, and a long entry into a sector under an explicit SHORT BIAS macro call the same day the regime was confirmed as Stagflation with escalating Minsky fragility.

---

## GOOG — Alphabet Inc. Class C

### Step 5 — Market Researcher

**1. News Catalysts** — Verdict: mixed — AI product momentum and a major antitrust win offset by capex/legal overhangs.
- Earnings: next report Oct 27, 2026, after close [OUTSIDE 5-day window].
- Product: Gemini 3.8 Flash launched — 4th Flash-tier model shipped in <4 months, compressing the pace of capability releases at the affordable end. New cybersecurity-focused model for government/enterprise also launched.
- Partnerships: Morgan State University AI Campus Partnership and a "largest foundational partnership" with Ohio State (Sept 9) — education/AI-adoption plays, minor stock-positive catalysts.
- Legal: a federal judge rejected the DOJ's push to force Google to sell its ad exchange — a genuine antitrust win, described by outside counsel as a "big deal." Separately, FTC investigation into YouTube (consumer-protection/account-suspension practices) is reportedly in its final stages, with a lawsuit reportedly being prepared — an open legal overhang.
- Macro: capex guidance ($175-205B range cited across sources for 2026, more than double last year) continues to weigh on near-term FCF/margin narratives; this ties Alphabet directly into today's AI-capex/circular-financing bubble discussion (see macro report Section 10d — Nvidia's reported ~$10B Anthropic IPO investment).

**2. Sentiment & Narrative** — Verdict: broadly bullish, high consensus buy ratio, but capex/legal overhangs create real tension.
- Analyst ratings: 90% buy-rated (per alt_data.json analyst_trend), STABLE trend (+1.4pp vs prior month) — no fresh upgrade/downgrade cycle detected this month.
- Short interest: days-to-cover 2.6, MoM change -8.6% (mild covering, not a strong signal either way).
- Narrative: bullish on AI product cadence (Gemini) and the antitrust win; bearish/cautionary on capex drag and the pending YouTube/FTC matter. Stock reportedly ended its "longest monthly losing streak in over a decade" in early September before the recent broader market pullback.

**3. Institutional & Options Activity** — Verdict: historically strong tier-1 institutional support, but confirmatory data for September specifically is thin.
- Institutional ownership: Berkshire Hathaway reportedly purchased $4.9B in Alphabet stock (disclosed late 2025) — a major tier-1 conviction signal, though the disclosure itself is now stale relative to Sept 2026 and should be lag-adjusted. State Street raised its stake +1.8% in Q2 2026.
- Hedge fund positioning: [no fresh Sept 2026-specific entries/exits confirmed in search].
- Options flow: bullish sweep data found is dated January 2026 (large call buying at the $340 strike) — [STALE, UNCONFIRMED for current period]. No September 2026 options-flow data located.
- Dark pool: [NO DATA].

**4. Sector Rotation Signals** — Verdict: Alphabet sits at the intersection of Communication Services (its GICS sector) and the AI-capex/hyperscaler trade that the macro report treats as part of the broader semis/AI-infrastructure short thesis.
- Communication Services sector ETF flow: [NO DATA retrieved].
- Peer/read-through: Alphabet is one of the hyperscalers whose capex is the demand-side counterpart to the semiconductor supply chain (TER, ALAB, BESI in this same batch) — its capex guidance and the macro report's Anthropic/Nvidia circular-financing flag are directly relevant even though Alphabet itself isn't classified as "Semiconductors."

**5. Market Structure Summary** — Verdict: breakout setup, technically the strongest classification in this batch.
- Setup labeled "breakout" by the scan (vs. reversal for BESI/TER/ALAB) — implies price already clearing a base, distinct risk profile from the semis reversal names.
- Volume ratio 1.47x — moderate, below the 1.5x "ideal" breakout-volume threshold noted in strategy-analyst.md.
- [Full weekly-stage/EMA/SMA detail deferred to technical-analyst.md upstream output.]

**6. Upcoming Risk Events** — Verdict: earnings clear; BOJ event and pending FTC/YouTube matter are the near-term watch items.
- Earnings: Oct 27, 2026 — CLEAR for the planned hold window.
- FTC/YouTube: reportedly in final investigation stages with a lawsuit "being prepared" — no confirmed filing date; [UNCONFIRMED, WATCH].
- BOJ decision Sept 18 (2 trading days) — broad market/carry-unwind risk, not GOOG-specific.
- Implied move: [NO DATA].

### Step 6 — Alt Data Agent

```
┌─────────────────────────────────────────────────────────────────┐
│  ALT DATA VERDICT — GOOG — 2026-09-16                            │
├─────────────────────────────────────────────────────────────────┤
│  Alt Data Score    : 42                                          │
│  Signal            : NEUTRAL (close to the 40 BEARISH threshold) │
│  Flags             : INSIDER_SELLING, NEWS_ACCELERATING          │
├─────────────────────────────────────────────────────────────────┤
│  Insider           : SELLING                                     │
│  Net 30d           : -$204,637 net sold (2 sellers, 0 buyers)    │
│  Notable           : none named individually                     │
│  Insider MSPR      : NO_DATA                                     │
├─────────────────────────────────────────────────────────────────┤
│  Short Interest    : % of float UNKNOWN; DTC: 2.6 days            │
│  Level             : UNKNOWN                                     │
│  MoM change        : -8.6% (mild covering — below the 15%         │
│                       threshold for a strong capitulation signal) │
│  Squeeze watch     : NO                                          │
├─────────────────────────────────────────────────────────────────┤
│  Analyst Trend     : STABLE                                      │
│  Bull ratio        : 90.0% buy-rated, +1.4pp vs prior month      │
│  Congressional*    : NO_API_KEY (ref only)                       │
├─────────────────────────────────────────────────────────────────┤
│  News Sentiment    : 0.183 (POSITIVE)                             │
│  Velocity          : RISING                                       │
│  Articles scored   : 10 in last 5 days                            │
├─────────────────────────────────────────────────────────────────┤
│  Interpretation    : Weakest alt-data read of the batch. Insider  │
│                      selling (2 sellers, no buyers) combined with │
│                      no MSPR confirmation drags the score down to │
│                      42 despite a strong 90% analyst buy ratio and│
│                      rising positive news sentiment. This is the  │
│                      WEAKER of the two GOOG/GOOGL legs — see      │
│                      batch-level correlation flag.                │
└─────────────────────────────────────────────────────────────────┘
```

### Step 7 — Strategy Analyst

```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY VERDICT — GOOG — 2026-09-16                            │
├─────────────────────────────────────────────────────────────────┤
│  Direction     : LONG                                             │
│  Strategy      : POSITION                                         │
│  Holding Period: 4-8 weeks                                        │
│  Timeframe     : Daily breakout, weekly trend assumed confirmed   │
│                   (Weinstein Stage 2 read deferred to upstream    │
│                   technical-analyst output)                        │
├─────────────────────────────────────────────────────────────────┤
│  Entry         : 345.71 — breakout from base                      │
│  Entry Method  : Breakout                                         │
│  Entry Timing  : First hour of trading on breakout day, or next   │
│                   morning on volume-confirmed close above pivot   │
│  Stop          : 331.3671 — structural, 4.15% from entry (fits    │
│                   within POSITION's 8% max comfortably)           │
│  Target        : 367.27 — Bulkowski measure rule / resistance     │
│  R:R           : 1.50 (exactly at the 1.5 floor — no margin)      │
├─────────────────────────────────────────────────────────────────┤
│  Position Mgmt                                                    │
│  Add at        : First throwback to breakout level (up to 50%)    │
│  Trim at       : +2R → 25% off; extended >20% from 50 SMA → 50%  │
│                   off                                              │
│  Trail from    : +1R → breakeven                                  │
├─────────────────────────────────────────────────────────────────┤
│  Hold while    : weekly trend intact, fundamental Flag CONFIRMED  │
│  Exit if       : stop hit / weekly close below rising 30-wk MA /  │
│                   earnings miss + guidance cut / CYCLE OVERRIDE    │
│                   triggers a reduction to half                     │
│  Max hold      : 8 weeks                                          │
├─────────────────────────────────────────────────────────────────┤
│  Thesis        : Mega-cap breakout with CONFIRMED undervalued     │
│                   fundamentals (F-score 67), AI product momentum  │
│                   (Gemini 3.8 Flash cadence) and a real antitrust  │
│                   win (ad-exchange breakup rejected) reducing      │
│                   idiosyncratic legal tail risk.                   │
│  Main Risk     : Same underlying company as GOOGL in this batch — │
│                   double-counting risk if both taken. Capex        │
│                   guidance ($175-205B) ties this name into the     │
│                   macro report's AI-capex bubble/circular-         │
│                   financing concern even though GOOG itself is not │
│                   a semiconductor name. R:R sits exactly at the    │
│                   1.5 floor with zero margin for slippage.         │
│  Earnings Risk : CLEAR (Oct 27, 2026 — outside hold window start) │
└─────────────────────────────────────────────────────────────────┘
```

### Step 8 — Institutional Flow (per-ticker verdict only)

```
┌─────────────────────────────────────────────────────────────────┐
│  INSTITUTIONAL VERDICT — GOOG — 2026-09-16                       │
├─────────────────────────────────────────────────────────────────┤
│  Smart Money Score : 55                                           │
│  Alignment         : CAUTIOUS                                     │
├─────────────────────────────────────────────────────────────────┤
│  13F Consensus     : ACCUMULATING (tier-1) — but STALE            │
│  Quarter           : Berkshire disclosure dated late 2025; State  │
│                       Street +1.8% in Q2 2026                      │
│  Notable holders   : Berkshire Hathaway: NEW/ADD ~$4.9B (STALE —   │
│                       late-2025 disclosure, lag-adjust before      │
│                       treating as current conviction)               │
│                      State Street: ADD, +1.8% Q2 2026                │
│  Lag note          : Berkshire figure is >6 months stale relative  │
│                       to today — treat as directional color, not   │
│                       a live signal; do not assume still buying    │
│  Activist flag     : NONE                                          │
├─────────────────────────────────────────────────────────────────┤
│  Dark Pool         : DATA UNAVAILABLE                              │
│  Direction signal  : UNCLEAR                                       │
├─────────────────────────────────────────────────────────────────┤
│  Options Flow      : DATA UNAVAILABLE for current period (only     │
│                       stale Jan-2026 bullish sweep data found)      │
│  Detail            : $340 strike call sweep, Jan 26 2026 [STALE]   │
├─────────────────────────────────────────────────────────────────┤
│  Sector ETF        : XLC (proxy) — flow DATA UNAVAILABLE; note     │
│                       Alphabet's capex ties it to the AI-capex      │
│                       complex under macro pressure today            │
│  ETF Signal        : NEUTRAL (UNCONFIRMED)                          │
├─────────────────────────────────────────────────────────────────┤
│  Dry Powder        : DATA UNAVAILABLE                               │
│  Fuel for move     : LOW (per macro: Minsky 6/7, HY spreads tight/ │
│                       complacent, CYCLE OVERRIDE triggered)         │
├─────────────────────────────────────────────────────────────────┤
│  WAIT                                                                │
│  Reason            : Genuinely bullish tier-1 institutional history │
│                       (Berkshire, State Street) but the strongest   │
│                       evidence is stale; combined with an insider-  │
│                       selling flag from alt-data and weaker read    │
│                       than GOOGL, this is the weaker of the two     │
│                       correlated legs — flag for risk-manager.      │
└─────────────────────────────────────────────────────────────────┘
```

### Step 9 — Risk Manager

**VERDICT: CAUTION**

- Position Size: OK — would fit within GOOD tier max (€2,220 / 3%) if traded alone.
- Portfolio Exposure: WARNING — correlation flag: GOOG and GOOGL are the same underlying company (Alphabet). Per strategy-analyst's universal rule, if both are opened they must be treated as ONE position for sizing purposes, not two independent 3% allocations (effectively 6% combined exposure to one company). GOOG is the weaker of the two legs (lower alt-data score 42 vs 61, INSIDER_SELLING flag, more stale institutional evidence) — if only one Alphabet leg is taken, prefer GOOGL over GOOG.
- R:R Ratio: MARGINAL — exactly 1.50, at the bare regulatory floor with zero cushion.
- Drawdown Status: OK.
- Stop-Loss: OK — 4.15%, well within POSITION's 8% cap, structurally placed.
- Volatility Context: ELEVATED — Alphabet's $175-205B capex guidance directly implicates it in the macro report's AI-capex/circular-financing bubble concern (Nvidia's reported ~$10B Anthropic IPO stake cited as the sharpest evidence yet), even though GOOG itself is Communication Services, not Semiconductors. Genuinely strong offsetting facts exist (antitrust win, Gemini cadence, historical Berkshire conviction) but they are shared with GOOGL, which has the cleaner alt-data/institutional read — so GOOG specifically does not clear the bar for an outright APPROVE.

**What needs to change before approval**: resolve the GOOG/GOOGL correlation (pick one leg, or size both as a single combined position); confirm current-period options/dark-pool flow rather than relying on stale Jan-2026 data; get R:R comfortably above the 1.5 floor before entry (tighter fill or wider target).

---

## GOOGL — Alphabet Inc. Class A

### Step 5 — Market Researcher

Same underlying company/news set as GOOG (see full detail above) — summarized here with GOOGL-specific data points only.

**1. News Catalysts**: Identical to GOOG — Gemini 3.8 Flash launch, Ohio State/Morgan State partnerships, ad-exchange antitrust win (DOJ breakup bid rejected), FTC/YouTube investigation in final stages [UNCONFIRMED lawsuit timing]. Earnings Oct 27, 2026 [OUTSIDE 5-day window].

**2. Sentiment & Narrative**: Same 90% buy-rated, STABLE trend (+1.4pp) per alt-data. Same "ended longest losing streak in a decade" narrative. GOOGL is the more commonly-quoted/liquid class in most sell-side coverage.

**3. Institutional & Options Activity**: Same Berkshire $4.9B stake (STALE, late-2025 disclosure) and State Street +1.8% Q2 2026 add — these 13F-style disclosures are generally attributed to the vote-bearing Class A (GOOGL) shares in most trackers, which slightly favors treating GOOGL as the primary institutional-conviction vehicle of the two.

**4. Sector Rotation Signals**: Same as GOOG — Communication Services / AI-capex-adjacent, no direct sector ETF flow data retrieved.

**5. Market Structure Summary**: Setup labeled "breakout," volume ratio 1.57x (slightly stronger than GOOG's 1.47x).

**6. Upcoming Risk Events**: Same as GOOG — earnings CLEAR (Oct 27), BOJ Sept 18 broad-market risk, FTC/YouTube WATCH.

### Step 6 — Alt Data Agent

```
┌─────────────────────────────────────────────────────────────────┐
│  ALT DATA VERDICT — GOOGL — 2026-09-16                           │
├─────────────────────────────────────────────────────────────────┤
│  Alt Data Score    : 61                                          │
│  Signal            : NEUTRAL (upper end, close to 65 BULLISH)    │
│  Flags             : INSIDER_MSPR_BULLISH, NEWS_ACCELERATING     │
├─────────────────────────────────────────────────────────────────┤
│  Insider           : NONE (no 30d cluster activity)               │
│  Net 30d           : neutral                                      │
│  Notable           : none                                         │
│  Insider MSPR      : BULLISH (+30.8, 3mo avg) — net insider buying│
│                       over the trailing quarter despite no recent  │
│                       30-day cluster                                │
├─────────────────────────────────────────────────────────────────┤
│  Short Interest    : 1.32% of float — LOW; DTC: 3.0 days           │
│  Level             : LOW                                           │
│  MoM change        : +10.2% (rising, but below the 15% "bears      │
│                       adding conviction" threshold — mild only)    │
│  Squeeze watch     : NO                                            │
├─────────────────────────────────────────────────────────────────┤
│  Analyst Trend     : STABLE                                        │
│  Bull ratio        : 90.0% buy-rated, +1.4pp vs prior month        │
│  Congressional*    : NO_API_KEY (ref only)                          │
├─────────────────────────────────────────────────────────────────┤
│  News Sentiment    : 0.183 (POSITIVE)                               │
│  Velocity          : RISING                                         │
│  Articles scored   : 10 in last 5 days                              │
├─────────────────────────────────────────────────────────────────┤
│  Interpretation    : Cleanest alt-data read of the batch — MSPR    │
│                      BULLISH (3mo insider accumulation trend),      │
│                      very low short interest, stable high analyst  │
│                      buy ratio, rising positive news. This is the  │
│                      STRONGER of the two GOOG/GOOGL legs — see     │
│                      batch-level correlation flag.                  │
└─────────────────────────────────────────────────────────────────┘
```

### Step 7 — Strategy Analyst

```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY VERDICT — GOOGL — 2026-09-16                            │
├─────────────────────────────────────────────────────────────────┤
│  Direction     : LONG                                              │
│  Strategy      : POSITION                                          │
│  Holding Period: 4-8 weeks                                         │
│  Timeframe     : Daily breakout, weekly trend assumed confirmed    │
│                   (deferred to upstream technical-analyst output)   │
├─────────────────────────────────────────────────────────────────┤
│  Entry         : 349.39 — breakout from base                       │
│  Entry Method  : Breakout                                          │
│  Entry Timing  : First hour on breakout day, or next morning on    │
│                   volume-confirmed close above pivot                 │
│  Stop          : 334.4235 — structural, 4.28% from entry (well     │
│                   within POSITION's 8% max)                          │
│  Target        : 372.08 — Bulkowski measure rule / resistance      │
│  R:R           : 1.52 (marginal — modest cushion over the 1.5 floor)│
├─────────────────────────────────────────────────────────────────┤
│  Position Mgmt                                                     │
│  Add at        : First throwback to breakout level (up to 50%)     │
│  Trim at       : +2R → 25% off; extended >20% from 50 SMA → 50%   │
│                   off                                                │
│  Trail from    : +1R → breakeven                                   │
├─────────────────────────────────────────────────────────────────┤
│  Hold while    : weekly trend intact, fundamental Flag CONFIRMED   │
│  Exit if       : stop hit / weekly close below rising 30-wk MA /   │
│                   earnings miss + guidance cut / CYCLE OVERRIDE     │
│                   triggers a reduction to half                       │
│  Max hold      : 8 weeks                                            │
├─────────────────────────────────────────────────────────────────┤
│  Thesis        : Best-supported setup in the batch — CONFIRMED     │
│                   undervalued fundamentals (F-score 67), cleanest   │
│                   alt-data read (MSPR bullish, low short interest), │
│                   genuine antitrust de-risking event (ad-exchange   │
│                   breakup bid rejected), and historical tier-1      │
│                   institutional conviction (Berkshire, State Street)│
│  Main Risk     : Same underlying company as GOOG — double-counting │
│                   risk if both are opened. AI-capex guidance        │
│                   ($175-205B) still ties this name to the macro     │
│                   report's bubble/circular-financing concern.       │
│  Earnings Risk : CLEAR (Oct 27, 2026 — outside hold window start)  │
└─────────────────────────────────────────────────────────────────┘
```

### Step 8 — Institutional Flow (per-ticker verdict only)

```
┌─────────────────────────────────────────────────────────────────┐
│  INSTITUTIONAL VERDICT — GOOGL — 2026-09-16                       │
├─────────────────────────────────────────────────────────────────┤
│  Smart Money Score : 58                                            │
│  Alignment         : CAUTIOUS                                       │
├─────────────────────────────────────────────────────────────────┤
│  13F Consensus     : ACCUMULATING (tier-1) — but STALE              │
│  Quarter           : Berkshire disclosure dated late 2025 (most     │
│                       commonly attributed to Class A/GOOGL); State  │
│                       Street +1.8% Q2 2026                            │
│  Notable holders   : Berkshire Hathaway: NEW/ADD ~$4.9B [STALE —    │
│                       lag-adjust]; State Street: ADD +1.8%           │
│  Lag note          : Berkshire figure >6 months stale — treat as    │
│                       directional color, not a live signal           │
│  Activist flag     : NONE                                            │
├─────────────────────────────────────────────────────────────────┤
│  Dark Pool         : DATA UNAVAILABLE                                │
│  Direction signal  : UNCLEAR                                          │
├─────────────────────────────────────────────────────────────────┤
│  Options Flow      : DATA UNAVAILABLE for current period (same      │
│                       stale Jan-2026 caveat as GOOG)                  │
│  Detail            : $340 strike call sweep, Jan 26 2026 [STALE]     │
├─────────────────────────────────────────────────────────────────┤
│  Sector ETF        : XLC (proxy) — flow DATA UNAVAILABLE              │
│  ETF Signal        : NEUTRAL (UNCONFIRMED)                            │
├─────────────────────────────────────────────────────────────────┤
│  Dry Powder        : DATA UNAVAILABLE                                  │
│  Fuel for move     : LOW (per macro: Minsky 6/7, CYCLE OVERRIDE       │
│                       triggered)                                       │
├─────────────────────────────────────────────────────────────────┤
│  WAIT                                                                    │
│  Reason            : Best institutional read of the batch (MSPR       │
│                       bullish, low short interest, historical tier-1  │
│                       conviction) but still capped at CAUTIOUS because│
│                       dark pool/options/ETF flow are all unconfirmed  │
│                       for the current period, and this is the         │
│                       stronger of two correlated Alphabet legs.        │
└─────────────────────────────────────────────────────────────────┘
```

### Step 9 — Risk Manager

**VERDICT: CAUTION**

- Position Size: OK — fits within GOOD tier max (€2,220 / 3%) if traded alone.
- Portfolio Exposure: WARNING — same correlation flag as GOOG: same underlying company. If both GOOG and GOOGL are opened, treat as ONE position for sizing (not 6% combined). GOOGL is the stronger leg and is preferred if only one is taken.
- R:R Ratio: MARGINAL — 1.52, modest cushion above the 1.5 floor but not "high quality" (would need ≥2.5 for that classification).
- Drawdown Status: OK.
- Stop-Loss: OK — 4.28%, well within POSITION's 8% cap.
- Volatility Context: ELEVATED — same AI-capex/rate-sensitive-mega-cap tension as GOOG (10Y closed above 5% for the first time since 2007 today, a direct headwind to long-duration growth multiples; Alphabet's own $175-205B capex guidance implicates it in the macro report's circular-financing bubble concern). This is the strongest individual case in the batch to potentially override the macro SHORT BIAS lean — genuine antitrust de-risking event (ad-exchange breakup bid rejected), CONFIRMED undervalued fundamentals, cleanest alt-data/institutional read of any ticker here — but it does not fully escape the macro headwind (still AI-capex-adjacent, still a long-duration multiple facing a >5% 10Y), so it stops short of a clean APPROVE.

**What needs to change before approval**: resolve the GOOG/GOOGL correlation (this is the preferred leg if only one is taken); confirm current-period institutional/options flow rather than relying on stale Jan-2026/late-2025 data before sizing to the full GOOD tier max.

---

## TER — Teradyne (semiconductor test equipment)

### Step 5 — Market Researcher

**1. News Catalysts** — Verdict: sharp single-day drop on profit-taking, not a fundamental break.
- Earnings: Oct 27, 2026, after close [OUTSIDE 5-day window] — this is Q3 2026.
- Product: launched "Advanced UltraFLEXplus Instruments" on Sept 1, 2026 — three new instruments (UltraPin5000-EM, UltraPort-PCIe6, UltraVS64-HP) targeting AI and data-center test complexity — incremental positive, not a major catalyst.
- Dividend: quarterly $0.13/share declared, payable Sept 25, 2026 — routine.
- Price action: stock dropped -13.3% to $329.20 on Sept 14, 2026 — this closing print is essentially identical to the scan's entry level (329.2), meaning the "reversal" setup here is entering right at the bottom of a single-day flash decline, not a multi-week base. The article attributes the drop to profit-taking after a strong prior run-up, coinciding with (not caused by) the opening of a new Bengaluru semiconductor support office on Sept 15.

**2. Sentiment & Narrative** — Verdict: bullish sell-side into the drop, AI-test-equipment growth story intact.
- Analyst ratings: consensus "Moderate Buy," average target $396.80 (as of Sept 10, before the -13.3% drop) — implies meaningful upside from the post-drop $329 level, but the target predates the decline and has not been re-confirmed since.
- Short interest: [NO DATA in alt_data.json — ticker not covered].
- Narrative: bullish long-term (AI-driven test complexity, HBM/optical test qualification, AI-related revenue >60% of total), but the -13.3% single-session move is a genuine, fresh negative data point that a pure "profit-taking" explanation doesn't fully resolve without more confirmation.

**3. Institutional & Options Activity** — Verdict: no confirmed data found.
- Institutional ownership trend: [NO DATA].
- Hedge fund positioning: [NO DATA].
- Options flow: [NO DATA — no unusual options activity located for TER specifically in the search window].
- Dark pool/block trades: [NO DATA].

**4. Sector Rotation Signals** — Verdict: same sector headwind as BESI/ALAB.
- SOXX (semiconductor ETF) in confirmed bear market, -20%+ from June highs, further downside flagged by Ed Yardeni (-12% to 200dma). TER's own -13.3% single-day drop on Sept 14 is directly consistent with this broader sector de-rating rather than an idiosyncratic issue.
- Peer read: TER (test equipment) sits alongside ALAB (interconnect) and BESI (packaging/die-attach) as direct AI-infrastructure supply-chain plays — all three are exposed to the same Kindleberger Stage-4 sector call.

**5. Market Structure Summary** — Verdict: reversal at the low of a sharp single-day flash decline.
- Entry (329.2) = the exact Sept 14 closing print after the -13.3% drop — this is a reversal-at-the-crash-low setup, structurally higher-risk than a reversal at a multi-week base.
- Volume ratio 2.06x — clears the 2.0x institutional-participation threshold, consistent with a high-volume capitulation/profit-taking session.
- [Full weekly-stage detail deferred to upstream technical-analyst output.]

**6. Upcoming Risk Events** — Verdict: earnings clear; BOJ is the nearest event risk.
- Earnings: Oct 27, 2026 — CLEAR for the planned hold window.
- BOJ decision Sept 18 (2 trading days) — broad market risk.
- Implied move: [NO DATA].

### Step 6 — Alt Data Agent

```
┌─────────────────────────────────────────────────────────────────┐
│  ALT DATA VERDICT — TER — 2026-09-16                             │
├─────────────────────────────────────────────────────────────────┤
│  Alt Data Score    : 50 (default — DATA UNAVAILABLE, ticker not  │
│                       present in alt_data.json's 212-ticker set)  │
│  Signal            : NEUTRAL                                     │
│  Flags             : none (DATA UNAVAILABLE — do not fabricate)  │
├─────────────────────────────────────────────────────────────────┤
│  Insider           : DATA UNAVAILABLE                            │
│  Net 30d           : DATA UNAVAILABLE                            │
│  Notable           : DATA UNAVAILABLE                            │
│  Insider MSPR      : DATA UNAVAILABLE                            │
├─────────────────────────────────────────────────────────────────┤
│  Short Interest    : DATA UNAVAILABLE                            │
│  Level             : DATA UNAVAILABLE                            │
│  MoM change        : DATA UNAVAILABLE                            │
│  Squeeze watch     : NO (cannot confirm)                          │
├─────────────────────────────────────────────────────────────────┤
│  Analyst Trend     : DATA UNAVAILABLE in alt_data.json (reference │
│                       only from Step 5: Moderate Buy, avg PT      │
│                       $396.80 as of Sept 10, pre-drop)            │
│  Congressional*    : NO_API_KEY (ref only)                        │
├─────────────────────────────────────────────────────────────────┤
│  News Sentiment    : DATA UNAVAILABLE                             │
│  Velocity          : DATA UNAVAILABLE                             │
│  Articles scored   : DATA UNAVAILABLE                             │
├─────────────────────────────────────────────────────────────────┤
│  Interpretation    : Ticker not covered by alt_data.py's current  │
│                      212-ticker universe — no insider, short-     │
│                      interest, MSPR, or VADER data available.     │
│                      Defaulting to Score=50/CAUTIOUS per the      │
│                      pipeline's standard "no data" convention     │
│                      rather than fabricating a signal.            │
└─────────────────────────────────────────────────────────────────┘
```

### Step 7 — Strategy Analyst

```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY VERDICT — TER — 2026-09-16                             │
├─────────────────────────────────────────────────────────────────┤
│  Direction     : LONG                                             │
│  Strategy      : TURNAROUND                                       │
│  Holding Period: Weeks to months                                  │
│  Timeframe     : Daily reversal at the low of a single-day flash  │
│                   decline within a sector-wide correction          │
├─────────────────────────────────────────────────────────────────┤
│  Entry         : 329.2 — reversal at the exact Sept 14 post-drop  │
│                   closing level                                     │
│  Entry Method  : Reversal candle                                   │
│  Entry Timing  : Next session following confirmed reversal          │
│  Stop          : 290.8327 — structural (below the flash-decline    │
│                   low) — 11.66% from entry                          │
│  Target        : 385.68 — prior resistance / near sell-side avg PT │
│  R:R           : 1.47 (below the 1.5 floor)                        │
├─────────────────────────────────────────────────────────────────┤
│  Position Mgmt                                                     │
│  Add at        : No add (turnaround into an active sector          │
│                   correction)                                       │
│  Trim at       : Recovery to 50 SMA (25%), 200 SMA (25%)          │
│  Trail from    : +1R → breakeven                                   │
├─────────────────────────────────────────────────────────────────┤
│  Hold while    : No earnings miss, AI-test-equipment demand thesis │
│                   intact, sector shows signs of basing              │
│  Exit if       : stop hit / new structural low / earnings miss or  │
│                   guidance cut / recovery not visible after 2       │
│                   earnings cycles                                    │
│  Max hold      : Reassess each earnings cycle                       │
├─────────────────────────────────────────────────────────────────┤
│  Thesis        : AI-driven test-complexity demand (AI revenue >60% │
│                   of total) and CONFIRMED undervalued fundamentals │
│                   (F-score 67) support a "sector-wide pullback, not │
│                   company-specific" recovery read of the -13.3%     │
│                   single-day drop.                                  │
│  Main Risk     : The stop (11.66%) exceeds even TURNAROUND's 10%   │
│                   max — this stop does not fit within ANY strategy  │
│                   tier's risk band as computed. R:R (1.47) also     │
│                   fails the 1.5 floor. The -13.3% single-day drop   │
│                   itself is a fresh, unresolved negative data point.│
│  Earnings Risk : CLEAR (Oct 27, 2026 — outside hold window start)  │
└─────────────────────────────────────────────────────────────────┘
```

### Step 8 — Institutional Flow (per-ticker verdict only)

```
┌─────────────────────────────────────────────────────────────────┐
│  INSTITUTIONAL VERDICT — TER — 2026-09-16                        │
├─────────────────────────────────────────────────────────────────┤
│  Smart Money Score : 50 (default — DATA UNAVAILABLE)             │
│  Alignment         : CAUTIOUS                                     │
├─────────────────────────────────────────────────────────────────┤
│  13F Consensus     : DATA UNAVAILABLE — no fresh 13F/hedge-fund   │
│                       entries or exits located for TER specifically│
│  Quarter           : N/A                                           │
│  Notable holders   : none confirmed                                 │
│  Lag note          : N/A                                            │
│  Activist flag     : NONE found                                     │
├─────────────────────────────────────────────────────────────────┤
│  Dark Pool         : DATA UNAVAILABLE                               │
│  Direction signal  : UNCLEAR                                        │
├─────────────────────────────────────────────────────────────────┤
│  Options Flow      : DATA UNAVAILABLE                               │
│  Detail            : none                                            │
├─────────────────────────────────────────────────────────────────┤
│  Sector ETF        : SOXX (proxy) — confirmed bear market, -20%+   │
│  ETF Signal        : HEADWIND                                        │
├─────────────────────────────────────────────────────────────────┤
│  Dry Powder        : DATA UNAVAILABLE                                │
│  Fuel for move     : LOW (per macro: Minsky 6/7, CYCLE OVERRIDE)     │
├─────────────────────────────────────────────────────────────────┤
│  WAIT                                                                  │
│  Reason            : No confirmed institutional flow data; the only   │
│                       quantifiable signal (sector ETF proxy, and the  │
│                       -13.3% single-day drop itself) is a headwind.   │
└─────────────────────────────────────────────────────────────────┘
```

### Step 9 — Risk Manager

**VERDICT: REJECT**

- Position Size: OK (structurally) — would fit under GOOD tier max if traded.
- Portfolio Exposure: WARNING — Technology sector; collides with BESI.AS and ALAB in this batch (3 Technology names vs. 2-per-sector cap) — provisional, final call pending cross-batch reconciliation.
- R:R Ratio: **FAIL — 1.47, below the 1.5 minimum required per RISK.md.**
- Drawdown Status: OK.
- Stop-Loss: **FAIL — 11.66% from entry, exceeding even TURNAROUND's 10% maximum stop distance.** This does not fit within any defined strategy risk band; the stop is placed below a single-day flash-decline low, which is structurally defensible but produces an outsized risk distance.
- Volatility Context: ELEVATED — same SHORT BIAS sector call as BESI.AS applies (semiconductors/AI infrastructure explicitly named, Kindleberger Stage 4 CONFIRMED). The -13.3% single-day drop that sets up this "reversal" is itself only one session old and unconfirmed as a genuine capitulation low rather than the start of further sector-wide deterioration — the AI-test-equipment growth story (positive) does not specifically contradict the macro sector-bear thesis.

**Reason for REJECT**: R:R fails the hard floor (1.47 < 1.5); stop distance (11.66%) exceeds every defined strategy risk band in strategy-analyst.md, indicating the setup does not structurally fit any approved trade type at this entry/stop combination; long entry into an explicitly SHORT-BIAS-flagged sector the same day the regime was confirmed as Stagflation.

---

## ALAB — Astera Labs (semiconductor/AI interconnect)

### Step 5 — Market Researcher

**1. News Catalysts** — Verdict: no confirmed new catalyst; conference appearance only.
- Earnings: next report ~Nov 10, 2026 (one source; historical-pattern estimate ~Nov 2-5) [OUTSIDE 5-day window either way].
- Sept 1, 2026: announced participation in the Citi 2026 Global TMT Conference (Sept 9) — investor-relations event, not a fundamental catalyst itself, but likely tied to the Sept 4 rally (see below).
- Fundamental: Q2 revenue grew +104% y/y, driven by AI fabric/signal-conditioning demand; Scorpio X-Series entered volume production and is expected to become the largest product line in Q3 [most recent confirmed fundamental datapoint, pre-dates this month].

**2. Sentiment & Narrative** — Verdict: bullish sell-side, high-beta stock, currently well off its recent highs.
- Analyst ratings: 19 buy / 0 sell — unanimous Buy consensus, average 12-mo target $389.95 (high $500, low $190) — wide dispersion reflecting the stock's extreme volatility (52-week range $97.89–$499.48).
- Short interest: [NO DATA in alt_data.json — ticker not covered].
- Price action: traded at $312.63 on Sept 4 (+10.5% that session, on the conference/AI-growth-story revisit), then fell to $252.54 by Sept 15 (prior close $257.04, matching the scan's entry level) — a roughly -19% pullback from the Sept 4 high in under two weeks, consistent with the broader chip-sector de-rating.
- Narrative: bullish on the AI-interconnect growth story specifically; the stock's extreme volatility and recent sharp reversal from the Sept 4 spike reflect the sector-wide risk-off tone more than a name-specific deterioration.

**3. Institutional & Options Activity** — Verdict: genuinely strong institutional/options backdrop, the best-documented of the three "reversal" names in this batch.
- Institutional ownership: 79.3% of shares held institutionally (latest read), down -0.9pp QoQ — high concentration, mild trim.
- Hedge fund positioning: Whale Rock Capital Management added 1,567,882 shares in Q2 2026; D.E. Shaw and Atreides Management reported as maintaining large positions. [Whale Rock is not a Tier-1 name in institutional-flow.md's institution universe table — treat as MEDIUM/unlisted-tier signal weight, not HIGH.]
- Options flow (Sept 4, 2026): calls represented 61.7% of total options volume (38.3% puts) on the +10.5% rally day; total volume 39,673 contracts; the $315 strike traded at >2x open interest — a genuine unusual-call-volume signal, though dated to the Sept 4 spike rather than the current Sept 15-16 pullback.
- Dark pool: [NO DATA].

**4. Sector Rotation Signals** — Verdict: same sector headwind as BESI/TER.
- SOXX confirmed bear market, -20%+ from June highs. ALAB (AI interconnect, Scorpio X-Series ramp) is a direct AI-infrastructure supply-chain read-through, squarely inside the Kindleberger Stage-4-flagged group.

**5. Market Structure Summary** — Verdict: reversal after a sharp two-week pullback from a recent spike high.
- Entry 257.04 sits ~18-19% below the Sept 4 intraday/closing levels (~$312) — a sizable, fast pullback consistent with sector-wide chip-stock weakness rather than an isolated breakdown.
- Volume ratio 1.89x — elevated, just under the 2.0x MOMENTUM threshold.
- [Full weekly-stage detail deferred to upstream technical-analyst output.]

**6. Upcoming Risk Events** — Verdict: earnings clear; BOJ is the nearest event risk.
- Earnings: ~Nov 10, 2026 (or ~Nov 2-5 per pattern-based estimate) — CLEAR for the planned hold window either way.
- BOJ decision Sept 18 (2 trading days) — broad market risk.
- Implied move: [NO DATA].

### Step 6 — Alt Data Agent

```
┌─────────────────────────────────────────────────────────────────┐
│  ALT DATA VERDICT — ALAB — 2026-09-16                            │
├─────────────────────────────────────────────────────────────────┤
│  Alt Data Score    : 50 (default — DATA UNAVAILABLE, ticker not  │
│                       present in alt_data.json's 212-ticker set)  │
│  Signal            : NEUTRAL                                      │
│  Flags             : none (DATA UNAVAILABLE — do not fabricate)   │
├─────────────────────────────────────────────────────────────────┤
│  Insider           : DATA UNAVAILABLE                              │
│  Net 30d           : DATA UNAVAILABLE                              │
│  Notable           : DATA UNAVAILABLE                              │
│  Insider MSPR      : DATA UNAVAILABLE                              │
├─────────────────────────────────────────────────────────────────┤
│  Short Interest    : DATA UNAVAILABLE                              │
│  Level             : DATA UNAVAILABLE                              │
│  MoM change        : DATA UNAVAILABLE                              │
│  Squeeze watch     : NO (cannot confirm)                            │
├─────────────────────────────────────────────────────────────────┤
│  Analyst Trend     : DATA UNAVAILABLE in alt_data.json (reference  │
│                       only from Step 5: unanimous Buy, 19/19, avg  │
│                       PT $389.95)                                    │
│  Congressional*    : NO_API_KEY (ref only)                          │
├─────────────────────────────────────────────────────────────────┤
│  News Sentiment    : DATA UNAVAILABLE                                │
│  Velocity          : DATA UNAVAILABLE                                │
│  Articles scored   : DATA UNAVAILABLE                                │
├─────────────────────────────────────────────────────────────────┤
│  Interpretation    : Ticker not covered by alt_data.py's current    │
│                      212-ticker universe. Defaulting to Score=50/   │
│                      CAUTIOUS per pipeline convention. Note: Step 5 │
│                      market-research found genuinely strong          │
│                      qualitative institutional/options signals       │
│                      (79.3% institutional ownership, bullish Sept 4  │
│                      options flow, Whale Rock add) — these are NOT   │
│                      part of the formal alt_data.json score and are │
│                      cross-referenced into Step 8 instead.           │
└─────────────────────────────────────────────────────────────────┘
```

### Step 7 — Strategy Analyst

```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGY VERDICT — ALAB — 2026-09-16                             │
├─────────────────────────────────────────────────────────────────┤
│  Direction     : LONG                                              │
│  Strategy      : TURNAROUND                                        │
│  Holding Period: Weeks to months                                   │
│  Timeframe     : Daily reversal after a sharp ~19% two-week pullback│
│                   from the Sept 4 spike high, within a sector-wide  │
│                   correction                                        │
├─────────────────────────────────────────────────────────────────┤
│  Entry         : 257.04 — reversal at support                       │
│  Entry Method  : Reversal candle                                    │
│  Entry Timing  : Next session following confirmed reversal           │
│  Stop          : 217.4007 — structural (below reversal low) —       │
│                   15.42% from entry                                  │
│  Target        : 321.65 — prior resistance zone                     │
│  R:R           : 1.63 (acceptable, marginal-to-decent)               │
├─────────────────────────────────────────────────────────────────┤
│  Position Mgmt                                                       │
│  Add at        : No add (turnaround — extremely high-beta name,      │
│                   52-wk range $97.89-$499.48)                         │
│  Trim at       : Recovery to 50 SMA (25%), 200 SMA (25%)             │
│  Trail from    : +1R → breakeven                                     │
├─────────────────────────────────────────────────────────────────┤
│  Hold while    : AI-interconnect demand thesis intact (Scorpio       │
│                   X-Series ramp), no earnings miss                    │
│  Exit if       : stop hit / new structural low / earnings miss or    │
│                   guidance cut / recovery not visible after 2         │
│                   earnings cycles                                      │
│  Max hold      : Reassess each earnings cycle                         │
├─────────────────────────────────────────────────────────────────┤
│  Thesis        : Best-documented institutional/options backdrop of   │
│                   the three "reversal" names (79.3% institutional    │
│                   ownership, bullish Sept 4 options flow, Whale Rock  │
│                   add, +104% y/y Q2 revenue growth); pullback reads   │
│                   as sector-wide, not company-specific.                │
│  Main Risk     : Stop distance (15.42%) is the widest in the entire   │
│                   batch — well beyond even TURNAROUND's 10% nominal   │
│                   cap, reflecting the stock's extreme volatility      │
│                   (52-wk range spans a ~5x band). Requires materially │
│                   reduced position size to keep dollar risk in line.  │
│  Earnings Risk : CLEAR (~Nov 10, 2026 — outside hold window start)    │
└─────────────────────────────────────────────────────────────────┘
```

### Step 8 — Institutional Flow (per-ticker verdict only)

```
┌─────────────────────────────────────────────────────────────────┐
│  INSTITUTIONAL VERDICT — ALAB — 2026-09-16                        │
├─────────────────────────────────────────────────────────────────┤
│  Smart Money Score : 60                                            │
│  Alignment         : CAUTIOUS                                       │
├─────────────────────────────────────────────────────────────────┤
│  13F Consensus     : ACCUMULATING (partial) — 79.3% institutional   │
│                       ownership (-0.9pp QoQ, mild trim); Whale Rock  │
│                       (unlisted-tier fund) added 1.57M shares Q2;    │
│                       D.E. Shaw, Atreides Management holding large   │
│                       positions [not confirmed as NEW/ADD this qtr]  │
│  Quarter           : Q2 2026 (most recent confirmed)                 │
│  Notable holders   : Whale Rock Capital: ADD, +1,567,882 sh (Q2)     │
│                      D.E. Shaw / Atreides: HOLD (large, unconfirmed  │
│                       direction this quarter)                         │
│  Lag note          : Q2 2026 13F data — moderately stale relative to │
│                       today; price has moved significantly since      │
│                       (Sept 4 spike to $312 then pullback to $257)    │
│  Activist flag     : NONE                                             │
├─────────────────────────────────────────────────────────────────┤
│  Dark Pool         : DATA UNAVAILABLE                                  │
│  Direction signal  : UNCLEAR                                           │
├─────────────────────────────────────────────────────────────────┤
│  Options Flow      : BULLISH SWEEP-LIKE (Sept 4 session)                │
│  Detail            : Calls 61.7% of volume (39,673 contracts total);   │
│                       $315 strike traded >2x open interest — but      │
│                       dated to the Sept 4 rally, not the current       │
│                       post-pullback period; no fresher confirmation    │
├─────────────────────────────────────────────────────────────────┤
│  Sector ETF        : SOXX (proxy) — confirmed bear market, -20%+       │
│  ETF Signal        : HEADWIND                                           │
├─────────────────────────────────────────────────────────────────┤
│  Dry Powder        : DATA UNAVAILABLE                                    │
│  Fuel for move     : LOW (per macro: Minsky 6/7, CYCLE OVERRIDE)         │
├─────────────────────────────────────────────────────────────────┤
│  WAIT                                                                      │
│  Reason            : Best individual institutional/options evidence of   │
│                       the batch's three reversal names, but it is dated   │
│                       (Q2 13F, Sept 4 options flow) relative to the       │
│                       current pullback, and sits against a firm sector   │
│                       ETF headwind — genuinely mixed, not a clean         │
│                       PROCEED.                                             │
└─────────────────────────────────────────────────────────────────┘
```

### Step 9 — Risk Manager

**VERDICT: CAUTION**

- Position Size: OK if reduced — GOOD tier max is €2,220 (3%), but given the 15.42% stop distance, sizing to the full tier cap would create outsized dollar risk relative to every other position in the portfolio; recommend sizing down materially (e.g., to keep $ risk comparable to a ~5% stop position) rather than using the full €2,220 notional.
- Portfolio Exposure: WARNING — Technology sector; collides with BESI.AS and TER in this batch (3 Technology names vs. 2-per-sector cap) — provisional, final call pending cross-batch reconciliation.
- R:R Ratio: OK/MARGINAL — 1.63, clears the 1.5 floor with some cushion, the best R:R of the three "reversal" names in this batch.
- Drawdown Status: OK.
- Stop-Loss: WARNING — stop is structural (below the reversal low) but 15.42% from entry is the widest in the entire batch, well beyond even TURNAROUND's 10% nominal ceiling — reflects the stock's extreme volatility (52-wk range ~5x band) more than a normal risk-managed stop.
- Volatility Context: ELEVATED — same SHORT BIAS sector call applies (Kindleberger Stage 4 CONFIRMED for semiconductors/AI infrastructure). ALAB has the strongest individual counter-evidence in the batch (79.3% institutional ownership, genuine bullish options flow on the Sept 4 session, +104% y/y revenue growth, unanimous 19/19 analyst Buy), but that evidence predates the current pullback and does not specifically contradict the macro sector-bear thesis — ALAB is itself a pure-play AI-interconnect semiconductor name, squarely inside the flagged short sector.

**What needs to change before approval**: reduce position size well below the GOOD tier max to compensate for the 15.42% stop (dollar risk must be normalized, not the full 3% notional at this stop width); would benefit from confirmation that the Sept 4 options-flow bullishness persists into the current pullback before treating institutional backdrop as a green light.
