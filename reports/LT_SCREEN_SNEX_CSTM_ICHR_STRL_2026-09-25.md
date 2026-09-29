# Long-Term Screen: SNEX · CSTM · ICHR · STRL — 2026-09-25

*Long-term analyst, Screening Mode. There are 4 tickers, so this is a screen, not a Deep-Dive.*

**Sources**
- Prices: close 2026-09-24.
- Fundamentals: yfinance (the tickers are not in `fundamental_data.json`), plus Q2/FQ3 2026 releases and earnings calls.

**Macro context** (from `data/daily_macro_report/macro_report_2026-09-24.md`)
- REFLATION, HIGH confidence.
- 10Y UST at **5.14%**, the highest since 2007. Oct hike odds ~73%.
- Late cycle: CYCLE OVERRIDE active. Marks 6/7, Minsky 7/7. Semis/AI-infra at Kindleberger Stage 3.
- Consequence: extra skepticism toward Bull-case DCFs and toward high-TV growth names.

**Currency:** EUR/USD 1.139 (1 USD = €0.878).

**Valuation settings**
- Risk-free rate 5.14% (US 10Y). ERP 4.5%.
- FCFF DCF with Key-Value-Driver terminal value, g = 2–3%, and terminal ROIC fading toward the sector average.
- SNEX is valued with an excess-return (residual income) model. DCF on a futures commission merchant's cash flows is not meaningful because client funds distort them.

## Summary table

| TICKER | Track | Category | F-Score | F-Rating | DCF Bear / Base / Bull ($ → €) | Price | MoS Gate | Compounder | AI Impact | Horizon | Thesis Invalidation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **SNEX** | A-FT (FCM/broker; P/TBV–ROE anchor) | FastGrower | 63 | Undervalued | 39.5 / 80.0 / 113.8 → €34.7 / €70.2 / €99.9 (Re 9.5%) | $69.52 / €61.0 | **BASE** (NONE at Re 10.5%) | **QUALITY** (6/8 scorable) | NEUTRAL | 3–5yr | TTM ROE < 13% for 2 consecutive quarters, OR average client equity down > 20% y/y, OR RJO synergies missing $45M by FYE26 |
| **CSTM** | A-MN (aluminium rolled products/recycling; mid-cycle EV/EBITDA + FCF yield) | Cyclical | 59 | Fair | 14.56 / 26.50 / 36.87 → €12.8 / €23.3 / €32.4 (WACC 9.5%) | $24.63 / €21.6 | **BASE** (thin: 7% below Base; NONE at 10.5%) | **QUALITY** (6/9) | NEUTRAL | 3–5yr | Adj. EBITDA ex-metal-lag run-rate < $850M (the mid-cycle level the price implies), OR 2027 FCF < $200M, OR leverage > 2.5× |
| **ICHR** | B-SM (semi-cap fluid subsystems; GM 14% = contract-manufacturer economics) | Cyclical | 45 | Fair | 13.03 / 26.87 / 43.01 → €11.4 / €23.6 / €37.8 (WACC 11.5%) | $56.47 / €49.6 | **NONE** (price > Bull, priced for perfection) | **TRADE ONLY** (3/9) | TAILWIND | n/a (not a long-term hold) | GM fails to reach ≥ 17% by Q2-27, OR OCF not positive in H1-27 as guided |
| **STRL** | A-ID (E&C; data-centre site development ~77% of Q2 revenue) | FastGrower (cyclical capex exposure) | 60 | Fair | 146.80 / 273.11 / 394.09 → €128.9 / €239.8 / €346.0 (WACC 10.5%) | $513.72 / €451.0 | **NONE** (price > Bull, priced for perfection) | **WATCH** (business 8/9 = COMPOUNDER; price gate fails) | TAILWIND (concentrated) | 5–10yr if re-priced | E-Infrastructure backlog down QoQ for 2 quarters (hyperscaler capex rollover), OR adj. EBITDA margin < 18% |

## DCF sensitivity (per share, USD)

| | Bear | Base | Bull | TV % of EV (Base) |
|---|---|---|---|---|
| SNEX, Re 9.5% / 10.5% | 39.5 / 30.5 | 80.0 / 61.8 | 113.8 / 87.9 | n/a (excess-return) |
| CSTM, WACC 9.5% / 10.5% | 14.56 / 11.57 | 26.50 / 21.72 | 36.87 / 30.51 | 51% |
| ICHR, WACC 11.5% / 13% | 12.05 / 10.55 | 25.88 / 21.59 | 41.99 / 34.31 | 60% |
| STRL, WACC 10.5% / 12% | 145 / 122 | 271 / 220 | 392 / 313 | 59% |

**WACC notes**
- **STRL:** CAPM with the reported beta of 1.85 gives a 13.5% cost of equity. That beta is inflated by the AI trade, so 10.5% (β≈1.2) is the base and 12% is the stress case.
- **ICHR:** β 1.81 → 13.3%. The base uses 11.5%.
- **CSTM:** β 1.55 → Re 12.1%. Debt is 35% of value at ~4.9% after tax, giving a WACC of ≈9.5%.
- **SNEX:** CAPM gives 8.0% (β 0.64). The base is floored at 9.5% for a leveraged financial.

## Price-implied expectations (Mauboussin)

**STRL**
- At WACC 10.5% and a steady 14% NOPLAT margin, the price needs a **25% revenue CAGR for 5 years**: $4.1B → $12.5B by 2031.
- At 9.5% it needs 20%; at 12% it needs 33%.
- The base rate for companies growing 20–30% is ~12–15% the following year. The price therefore requires roughly **1.7–2× the base rate**, which is the Mauboussin "priced for perfection" band.

**ICHR**
- At base growth (+15% in 2027, then 8% fading), the price needs a steady **EBIT margin of ~16% at an 11.5% WACC**. That is ~13% at 10% and ~19.5% at 13%.
- Best-ever EBIT margin was ~6.7% (FY22). Management's own target is 20% *gross* margin, which implies ~9–10% EBIT.
- The price therefore needs ~2× peak-cycle profitability.

**CSTM**
- The price implies a steady adj. EBITDA of **~$920M at WACC 9.5%**: ~$835M at 8.5% and ~$1.0B at 10.5%.
- The 2026 guide is $980M–1.02B ex-metal-lag, a record year.
- The market is pricing roughly a 10% fade to mid-cycle EBITDA, not a collapse. This is fair, not cheap, on a through-cycle basis.

**SNEX**
- The price implies a sustained ROE of ~17–18% fading to ~13% at Re 9.5%.
- TTM ROE is 20.8% and quarterly ROE 18.4%.
- The price is at or below what the current earning power supports, *if* the rate environment holds.

## Quality Compounder screen (Framework 8)

| Criterion | SNEX | CSTM | ICHR | STRL |
|---|---|---|---|---|
| ROIC/ROE 5y avg > 15% | ✅ ROE ~17% (FY22 19% → TTM 20.8%) | ❌ ~9% (FY25 ~13%) | ❌ negative FY23–25 | ✅ ~17% (13.5% → 22%) |
| Trend stable/improving | ✅ | ✅ | ✅ (GM 11% → 14%) | ✅ |
| Operating margin > 15% | ✅ ~32% pretax on net op. revenue | ❌ 5.6% FY25 / 8.9% TTM | ❌ 2.8% TTM | ✅ 20% TTM |
| FCF conversion > 80% | n/a (client funds distort OCF) | ❌ 58% FY25 (guide > $300M FY26) | ❌ FCF negative FY25 | ✅ 125% FY25 |
| CapEx/revenue < 10% | ✅ ~3% of net revenue | ✅ 3.4% | ✅ ~3–4% (rising in H2-26) | ✅ 3.1% |
| Self-funded (dilution < 3%/yr) | ❌ ~5%/yr FY22–25 plus RJO equity | ✅ share count 146.6M → 135.4M | ❌ $137M equity raise in 2024 (~15%) | ✅ flat ~30.7M |
| Mgmt ownership | ✅ insiders 9.1% | ✅ ~3% | ❓ 1.4% aggregate, CEO stake unverified | ✅ 2.3% |
| Buyback discipline | ❌ none | ✅ at ~5× EBITDA | ❌ none | ✅ $74M FY25 at lower prices |
| M&A discipline (goodwill < 40% of assets) | ✅ 1.6% (RJO bolt-on, synergies on track) | ✅ 2.5% | ✅ 39.9% (marginal) | ❌ 43% (CEC + Stone Ridge) |
| **Verdict** | **6/8 → QUALITY** | **6/9 → QUALITY** | **3/9 → TRADE ONLY** | **8/9 → COMPOUNDER business, WATCH at this price** |

## Per-ticker notes

### SNEX — StoneX
**What has to be true**
- ROE holds in the high teens as the R.J. O'Brien integration completes. Synergies are at a $37–38M run-rate, heading to $45–46M by FYE26 and $50M by Q1 FY27.
- Client balances hold. They are $16.2B, +108% y/y.

**Moat and advantage period**
- Scale and regulatory-licence moat as the largest non-bank FCM, with clearing and switching costs in commercial hedging relationships.
- Narrow-to-wide moat; estimated competitive advantage period ~7 years.

**Macro fit: the only name here with a direct tailwind from the current regime**
- Each +100bp in rates adds ~$46.9M after tax (+$0.38/share).
- Reflation-era commodity volatility drives the Commercial segment (+90% y/y).

**Biggest risk**
- The same lever in reverse. A Fed pivot, or a late-cycle credit event that compresses rates and volumes, cuts the earnings power the price assumes.

**Other points**
- The FQ3 EPS miss ($1.00 vs $1.23) and the sequential decline (net revenue −13% QoQ) explain the −24% over 3 months.
- Book value per share $23.70 (+32% y/y). P/B 2.9×.

### CSTM — Constellium
**Business and recent results**
- Record Q2: segment adj. EBITDA $310M, adj. EPS $1.04 vs $0.71 consensus.
- FY26 guide raised to $980M–1.02B ex-metal-lag; FCF > $300M; leverage 1.8×.
- Management says the 2028 targets are two years early.

**Lynch cyclical warning**
- Trailing P/E is 6.4× against forward 8.9×: consensus expects earnings to *fall*. That is the classic peak-earnings trap.
- Q2 also carried a +$129M non-cash metal-lag benefit.

**What has to be true**
- Mid-cycle EBITDA of ~$900M+ holds. The drivers are tariff-protected North American rolled-products shortages, record aerospace backlogs and recycling economics.
- Scrap spreads, currently locked favourably for H2, must not mean-revert hard.

**Moat and advantage period**
- Cost advantage through recycling and qualified aerospace/auto alloys (switching costs via qualification). Narrow moat, ~3–7 years.

**Biggest risk**
- Tariff and scrap-spread normalisation plus weak European auto, all at once.

**Verdict**
- The price clears Base only narrowly (7% below Base at 9.5%) and fails at 10.5%.
- QUALITY, with thin margin of safety. The stock is −27% over 3 months despite raised guidance.

### ICHR — Ichor Holdings
**Recent results and guidance**
- Q2 revenue $294.8M (+15% QoQ); GM 14.1%.
- Q3 guide $315–345M, GM 14.5–15.5%.
- FY26 revenue ≥ +30%. Operating cash flow positive only from H1-27.

**Why it fails the gate**
- The price needs roughly double the company's best-ever operating margin.
- That is on top of an AI/memory WFE upcycle the macro report classifies as Kindleberger Stage 3 (euphoria, Stage-4 risk).
- Gross margin in the teens is contract-manufacturer economics. Track B's CONFIRMED rule requires GM > 60%, so ICHR is **CAUTION on the Track B rules**.

**Other flags**
- Dilution (2024 raise).
- Goodwill ~40% of assets.
- No buybacks.

**Conclusion**
- No structural floor. It belongs to the short-term agents, not the long-term book.

**Biggest risk**
- A WFE digestion phase. Semi-cap subsystem suppliers historically see revenue fall 30–40% peak-to-trough (FY22 → FY23: −37%).

### STRL — Sterling Infrastructure
**The business is excellent**
- ROIC ~22%, EBITDA margin 22%, FCF conversion > 100%, net cash, flat share count.
- Committed backlog $4.3B (+116%), or $5.6B including unsigned awards.
- FY26 guide: revenue $4.0–4.15B, adj. EPS $19.70–20.30, adj. EBITDA $891–916M.

**The price fails the gate even after the −49% drawdown from $1,006**
- The market still needs ~25% revenue CAGR for 5 years at a 10.5% WACC.
- Revenue mix is increasingly data-centre site work: E-Infrastructure was $905M of $1,168M in Q2 (+192%). Transportation is −20%.
- The Q2 selloff trigger was guidance implying only a ~14% incremental EBITDA margin (Stone Ridge dilution) against 22% current.

**Moat and advantage period**
- Efficient scale and relationships with hyperscalers/GCs in regional site development. Narrow moat, ~3–7 years.
- The moat is not switching costs, so ROIC should fade.

**Biggest risk**
- A hyperscaler capex pause. Q2 revenue is ~77% tied to one end-market inside a Stage-3 AI-infra cycle.

**Verdict and re-underwrite level**
- WATCH. The business passes 8/9, but the price is above the Bull case.
- The Base case (~$271 / €238) is the re-underwrite zone. A materially lower WACC regime would also move it.
- **Update 2026-09-25 (Deep-Dives):** ICHR and STRL values refreshed for Q2 net cash (ICHR $136M after its $195M ATM raise; STRL $181M). ICHR stays 3/9 counted. Full reports: reports/{SNEX,CSTM,ICHR,STRL}_long_term_deep_dive_2026-09-25.docx
