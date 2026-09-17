# Step 13 — Short Screener (short-screener.md)

Run condition: macro Directional Bias = **SHORT BIAS** (confirmed, 2026-09-16 macro report). Screener authorised to run.

EUR/USD used for conversions: ~1.153 (per standing preference; USD figures / 1.153 = EUR).

---

## Market-Wide Short Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  SHORT SCREENER — 2026-09-16                                    │
├─────────────────────────────────────────────────────────────────┤
│  Macro Bias     : SHORT BIAS                                    │
│  Authorised     : Semiconductors / AI infrastructure (Stage 4   │
│  Sectors          CONFIRMED bubble, highest-confidence thesis); │
│                   Consumer Discretionary (real-income squeeze); │
│                   Long-duration / rate-sensitive (Utilities ex- │
│                   AI-power-demand, REITs, Homebuilders)         │
│  Tailwind       : Energy (XLE +44.9% YTD) — DISQUALIFIED from   │
│  (do not short)   this screen per Inviolable Rules              │
│  Candidates     : 0 High + 41 Medium + 74 Low conviction        │
│                   (115 total pass Stage 1 + squeeze pre-filter, │
│                   out of 129 Stage-1 technical passes; 4 Energy │
│                   names removed as tailwind-sector shorts)      │
├─────────────────────────────────────────────────────────────────┤
│  Market Context : Fed hiked to 3.75-4.00% today with a hawkish  │
│                   dot plot; 10Y closed >5% for the first time   │
│                   since 2007 — confirms the rate-sensitive short│
│                   leg. Anthropic CEO's 9/14 call to slow AI     │
│                   model development triggered an immediate chip-│
│                   equipment selloff (AMAT/LRCX/ASML) — confirms │
│                   the semi/AI-infra short leg live and ongoing. │
└─────────────────────────────────────────────────────────────────┘
```

**Data-quality caveat (applies to every candidate below):** the mandatory Stage 2 squeeze check "price up >20% in the last 10 trading days" has no data source in this pipeline (`price_cache.json` stores only a single latest price/timestamp per ticker, no history). Per short-screener.md's own rule ("If data is unavailable for any of these: flag as SQUEEZE DATA MISSING and proceed with caution — do not assign High conviction"), **every candidate in this run is capped at MEDIUM conviction**, even where the raw technical/fundamental/macro score totals ≥8/12. Three names (AXON, CAVA, SHAK) scored 8-9/12 pre-cap and are flagged `CAPPED FROM HIGH` below. Short interest % float and days-to-cover were available from `alt_data.json` for most US names (used to disqualify/confirm) but are `null` for most European listings (CNA.L, STMMI.MI, STMPA.PA, LAND.L, DTE.DE, CPG.L) — treated as squeeze-data-missing there too.

Stage 3 fundamental-deterioration used available proxies (`fundamental_data.json` lacks the exact fields short-screener.md names — no earnings-revision series, no explicit guidance-cut flag, no Penman accrual flag, and its "F-Score" field is actually a 0–100 value/quality/growth composite, not the Piotroski 0–9 scale). Proxy score (max 5, ≥3 = confirmed): negative revenue growth, negative earnings growth, "Overvalued" composite rating, profit margin <8%, debt/equity >1.5.

Stage 4 institutional distribution: no fresh `institutional-flow.md` Smart Money Score output exists for today's session — that component scored 0 for all candidates (insider-cluster-selling and short-interest MoM change were checked from `alt_data.json` where present, neither triggered for any top candidate).

---

## Top Candidates (ranked by Short Score)

| Rank | Ticker | Setup | Score | Conviction | Sector / Macro tie-in | Entry | Stop | Target | R:R |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **AXON** | breakdown | 9/12 → **MEDIUM** (capped from HIGH) | Industrials/Aerospace & Defense — no named macro tie | $442.08 (€383.42) | $495.32 (€429.60) | $309.62 (€268.53) | 2.49 |
| 2 | **CAVA** | breakdown | 8/12 → **MEDIUM** (capped from HIGH) | **Consumer Discretionary — named short sector** | $49.99 (€43.36) | $55.22 (€47.89) | $34.19 (€29.65) | 3.02 |
| 3 | **SHAK** | breakdown | 8/12 → **MEDIUM** (capped from HIGH) | **Consumer Discretionary — named short sector** | $58.27 (€50.54) | $64.40 (€55.85) | $43.68 (€37.88) | 2.38 |
| 4 | **CARR** | breakdown | 7/12 | MEDIUM | Industrials (Carrier Global, HVAC) | $55.54 (€48.17) | $58.81 (€51.01) | $49.20 (€42.67) | 1.94 |
| 5 | **GE** | breakdown | 7/12 | MEDIUM | Industrials (Aerospace & Defense) | $307.05 (€266.31) | $324.00 (€281.00) | $270.87 (€234.93) | 2.13 |
| 6 | **SYY** | breakdown | 7/12 | MEDIUM | Consumer Defensive (Sysco, food distribution) | $79.60 (€69.04) | $83.15 (€72.12) | $73.60 (€63.83) | 1.69 |
| 7 | **ONTO** | breakdown | 6/12 | MEDIUM | **Semiconductor Equipment — named short sector (AI-infra capex)** | $244.16 (€211.76) | $274.13 (€237.75) | $191.40 (€166.00) | 1.76 |
| 8 | **STMMI.MI** | breakdown | 6/12 | MEDIUM | **Semiconductors — named short sector**; short-interest data unavailable (Milan listing) | €41.77 | €45.01 | €36.33 | 1.68 |
| 9 | **CNA.L** | breakdown | 6/12 | MEDIUM | **Utilities — named rate-sensitive short sector** (Centrica; no AI-power-demand offset identified) | £147.20 | £155.02 | £131.58 | 2.00 |
| 10 | **ROL** | breakdown | 6/12 | MEDIUM | **Consumer Discretionary — named short sector** (Rollins) | $33.77 (€29.29) | $35.45 (€30.75) | $31.03 (€26.91) | 1.63 |
| 11 | **ON** | dead_cat | 5/12 | MEDIUM | **Semiconductors — named short sector** (onsemi) | $73.20 (€63.49) | $78.98 (€68.50) | $68.79 (€59.66) | 0.76 |
| 12 | **MAR** | distribution | 5/12 | MEDIUM | **Consumer Discretionary — named short sector** (Marriott, hotels) | $337.24 (€292.49) | $352.01 (€305.30) | $320.91 (€278.33) | 1.11 |

Instrument recommendation for all above given squeeze-data-missing flag: **put options** (next monthly expiry, 1-2 strikes OTM) rather than a naked/direct short, per short-screener.md default ("squeeze risk elevated but thesis sound → defined risk, no squeeze exposure"). CFD short acceptable for STMMI.MI/CNA.L if margin/financing terms are favorable; watch overnight financing cost.

### Lower-ranked macro-aligned names (LOW conviction, monitor only, do not act yet)
- **BKNG** 4/12 LOW — Consumer Discretionary (Booking Holdings, travel)
- **LAND.L** 4/12 LOW — Real Estate/REIT (Land Securities) — rate-sensitive thesis, but distance-to-resistance and volume components didn't confirm
- **STMPA.PA** 4/12 LOW — Semiconductors (STMicroelectronics, Paris line — same underlying company as STMMI.MI Milan line, ranked #8 above; do not double-count exposure across both listings)
- **PDD, CASY, DECK, CPG.L** — Consumer Discretionary headwind confirmed but score 4/12 (weak volume/resistance confirmation)

---

## Per-Ticker Short Verdict — Top 3

```
┌─────────────────────────────────────────────────────────────────┐
│  SHORT CANDIDATE — AXON — 2026-09-16                             │
├─────────────────────────────────────────────────────────────────┤
│  Conviction     : MEDIUM (capped from HIGH — squeeze data gap)   │
│  Score          : 9/12                                           │
│  Setup          : breakdown                                      │
│  Instrument     : Put options (next monthly, 1-2 strikes OTM)    │
├─────────────────────────────────────────────────────────────────┤
│  Squeeze Risk   : CAUTION — 10d price-move data unavailable      │
│  Short Int %    : 5.28% of float                                 │
│  Days to Cover  : 4.0 days                                       │
├─────────────────────────────────────────────────────────────────┤
│  Technical      : Confirmed downtrend, breakdown setup, 26.5%    │
│                   below resistance already (extended down move), │
│                   volume 3.74x average on the break               │
│  Fundamental    : Earnings growth negative, overvalued composite │
│                   rating, thin margin — 3/5 proxy deterioration  │
│                   flags (confirmed)                               │
│  Institutional  : No fresh Smart Money Score this session; no    │
│                   insider cluster selling flagged                │
│  Macro sector   : Neutral — Industrials/Aerospace & Defense not  │
│                   a named short or tailwind sector this session  │
├─────────────────────────────────────────────────────────────────┤
│  Thesis         : Confirmed downtrend breaking down further on   │
│                   3.7x volume with negative earnings growth and  │
│                   a still-rich valuation — technical and         │
│                   fundamental deterioration both present, no     │
│                   macro tailwind to fight                        │
│  Invalidation   : Reclaim of $495.32 (€429.60) stop level        │
│  Earnings Risk  : CLEAR — no print inside the 5-trading-day       │
│                   window per earnings_calendar.json               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  SHORT CANDIDATE — CAVA — 2026-09-16                              │
├─────────────────────────────────────────────────────────────────┤
│  Conviction     : MEDIUM (capped from HIGH — squeeze data gap)   │
│  Score          : 8/12                                           │
│  Setup          : breakdown                                      │
│  Instrument     : Put options (defined risk — SI 11.9% of float, │
│                   elevated for a squeeze if wrong)                │
├─────────────────────────────────────────────────────────────────┤
│  Squeeze Risk   : CAUTION — SI 11.9% under the 20% disqualify     │
│                   line but non-trivial; 10d move data missing     │
│  Short Int %    : 11.93% of float                                │
│  Days to Cover  : 4.0 days                                       │
├─────────────────────────────────────────────────────────────────┤
│  Technical      : Breakdown setup, 30.5% below resistance         │
│                   (extended), volume 2.91x average                │
│  Fundamental    : Overvalued composite rating + thin margin —     │
│                   2/5 proxy flags (below the 3-flag confirm line) │
│  Institutional  : No fresh Smart Money Score; no insider cluster  │
│  Macro sector   : HEADWIND — Consumer Discretionary named short   │
│                   sector (real-income squeeze from oil per macro) │
├─────────────────────────────────────────────────────────────────┤
│  Thesis         : Restaurant discretionary spend into a real-     │
│                   income squeeze, breaking down on rising volume, │
│                   trading at a rich multiple for a decelerating   │
│                   growth story                                    │
│  Invalidation   : Reclaim of $55.22 (€47.89) stop level           │
│  Earnings Risk  : CLEAR — no print inside 5-trading-day window    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  SHORT CANDIDATE — SHAK — 2026-09-16                              │
├─────────────────────────────────────────────────────────────────┤
│  Conviction     : MEDIUM (capped from HIGH — squeeze data gap)   │
│  Score          : 8/12                                           │
│  Setup          : breakdown                                      │
│  Instrument     : Put options (defined risk)                     │
├─────────────────────────────────────────────────────────────────┤
│  Squeeze Risk   : LOW-CAUTION — SI 10.9%, DTC 2.2d (comfortable), │
│                   10d move data still missing                     │
│  Short Int %    : 10.93% of float                                 │
│  Days to Cover  : 2.2 days                                        │
├─────────────────────────────────────────────────────────────────┤
│  Technical      : Breakdown setup, 23.2% below resistance,        │
│                   volume 1.56x average (weakest of the top 3)     │
│  Fundamental    : Negative earnings growth, overvalued rating,    │
│                   thin margin, high leverage — 4/5 proxy flags    │
│                   (strongest fundamental deterioration in batch)  │
│  Institutional  : No fresh Smart Money Score; no insider cluster  │
│  Macro sector   : HEADWIND — Consumer Discretionary named short   │
│                   sector                                          │
├─────────────────────────────────────────────────────────────────┤
│  Thesis         : Same-store-sales-sensitive restaurant chain     │
│                   with genuine balance-sheet deterioration        │
│                   (leverage + margin) breaking down into a        │
│                   confirmed discretionary-spending headwind        │
│  Invalidation   : Reclaim of $64.40 (€55.85) stop level           │
│  Earnings Risk  : CLEAR — no print inside 5-trading-day window    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Semiconductor / AI-Infrastructure Thesis — Cross-Reference

Four names in this screen tie directly to the session's highest-confidence macro short thesis (Kindleberger Stage 4 CONFIRMED bubble, chip sector down ~20% from June highs, Anthropic-CEO-triggered equipment selloff 9/14):

| Ticker | Score | Conviction | Note |
|---|---|---|---|
| ONTO | 6/12 | MEDIUM | Semicap equipment (Onto Innovation) — directly in the equipment-selloff blast radius (AMAT/LRCX/ASML-adjacent) |
| STMMI.MI | 6/12 | MEDIUM | STMicroelectronics, Milan line |
| ON | 5/12 | MEDIUM | onsemi |
| STMPA.PA | 4/12 | LOW | STMicroelectronics, Paris line — same issuer as STMMI.MI, do not size both |

This is the mirror image of this session's long-side scan, where ASML, ASML.AS, BESI.AS, TER, LRCX, MPWR and NVDA were REJECTED/CAUTIONed as longs specifically because they fight this same sector call. None of the four semi shorts above reached HIGH conviction — mainly because none showed the Stage-2 volume/resistance/fundamental combination needed to clear 8+, and all are capped by the system-wide squeeze-data gap — but sector alignment (+1) is confirmed for all four, and ONTO is the strongest single expression of the thesis in the current signal set.

---

## Full Stage-1-qualifying list (top 45 by score, before Stage-2 disqualification for reference)

See `data/market_data.json` filtered set — 129 tickers pass the mandatory technical filter (`trend=down`, `short_setup` in breakdown/distribution/dead_cat, `atr_pct>=2.0`, `avg_volume>=500k`). 4 Energy names (EOG, FANG, ENI.MI, XOM) were removed as tailwind-sector shorts per Inviolable Rules. 115 remain after the squeeze pre-filter (no outright disqualifications triggered on available short-interest/days-to-cover/earnings-calendar data — the missing-data cap was applied instead of a hard disqualify wherever short-interest/DTC were simply unavailable).

Ranked scores (ticker: score/conviction): AXON 9 MEDIUM(capped), CAVA 8 MEDIUM(capped), SHAK 8 MEDIUM(capped), CARR 7 MEDIUM, GE 7 MEDIUM, SYY 7 MEDIUM, CNA.L 6 MEDIUM, ONTO 6 MEDIUM, ROL 6 MEDIUM, STMMI.MI 6 MEDIUM, DTE.DE 6 MEDIUM, IMB.L 6 MEDIUM, ISRG 6 MEDIUM, UMG.AS 6 MEDIUM, AIR.PA 5 MEDIUM, BARC.L 5 MEDIUM, DLTR 5 MEDIUM, ENR.DE 5 MEDIUM, IR 5 MEDIUM, STJ.L 5 MEDIUM, SU.PA 5 MEDIUM, CPG.L 5 MEDIUM, ETN 5 MEDIUM, MAR 5 MEDIUM, ON 5 MEDIUM, RR.L 5 MEDIUM, SGO.PA 5 MEDIUM, then a long tail of LOW (4/12) and NONE/monitor-only names — see `.scan_scratch/step13_results.json` for the complete machine-readable ranking of all 115.

---

## Pipeline Position / Handoff

Per short-screener.md: these MEDIUM-conviction candidates (led by AXON, CAVA, SHAK, CARR, GE, SYY, and the semiconductor cluster ONTO/STMMI.MI/ON) feed to `strategy-analyst.md` for SHORT-POSITION/SHORT-SWING classification. `risk-manager.md` remains the final gate — must re-validate the squeeze pre-check (per RISK.md) given the system-wide 10-day-price-move data gap flagged above, before any of these are sized against the ~€74,000 account (currently 1 open long, DVN/Energy, no open shorts).
