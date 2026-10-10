import json

candidates = [
dict(ticker="ROST", conviction="High", setup="pullback", entry=224.95, stop=209.9923, target=239.73,
     rr_planned=0.99, f_score=49.3, rating="Fair", sector="Consumer Cyclical", strategy_type="SWING",
     alt_data_score=42, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     final_verdict_reason="R:R 0.99 below RISK.md 1.2 floor and f_rating only Fair; bull case (FY26 guidance raised after Q2 beat, low 3.46% short interest) offset by $12.8M net insider selling and live tariff-risk overhang (stockstory/barchart) — timing wrong, not thesis-broken. Wait for entry near 215-218 to restore R:R, or tariff clarity.",
     research_summary="Raised FY26 guidance after a Q2 beat (sgbonline.com); ongoing tariff-risk overhang flagged by sell-side (barchart/stockstory Q1 deep dive). No earnings-date conflict found for near-term hold."),

dict(ticker="SGO.PA", conviction="High", setup="reversal", entry=64.72, stop=58.96, target=71.3,
     rr_planned=1.14, f_score=46.8, rating="Fair", sector="Industrials", strategy_type="SWING",
     alt_data_score=41, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     final_verdict_reason="R:R 1.14 still under the 1.2 floor; primary trend is still down and the reversal has no volume/news confirmation — management reaffirmed (not raised) 2026 targets, which is steady, not a catalyst. EU alt-data is data-thin (no insider/short confirmation), so there is nothing corroborating the bounce. Wait for a confirmed follow-through close with volume.",
     research_summary="Saint-Gobain confirmed its 2026 targets (tradingsat.com) and opened a new furnace in Asturias — steady, not a re-rating catalyst. No negative news found either."),

dict(ticker="SU.PA", conviction="High", setup="pullback", entry=252.0, stop=220.56, target=304.85,
     rr_planned=1.68, f_score=42.6, rating="Fair", sector="Industrials", strategy_type="SWING",
     alt_data_score=41, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="CAUTION", final_verdict="BUY",
     final_verdict_reason="Strongest bull case in the pool: pullback in a confirmed uptrend with a real, multi-source-corroborated catalyst (raised FY guidance on record Q1 revenue, AI/data-center electrification demand — AFP wire via connaissancedesenergies.org, bolsamania, boerse-express), R:R 1.68 and target_atr 5.38 both best-in-pool. Bear case is TIMING-only (Fair not Undervalued, EU data-thin, elevated 10Y yields a sector headwind, stock already re-rated) and doesn't carry a disqualifying fact. GOOD tier 3% sizing (F&G 44.1<=50, composite 51.9>=48; composite not >=55 so STRONG tier not met despite High conviction).",
     research_summary="Schneider Electric raised annual guidance on record Q1 revenue (EUR9.8B), driven by data-center/AI electrification demand (AFP, 2026). Widely corroborated across multiple EU financial outlets."),

dict(ticker="EOG", conviction="Medium", setup="consolidation", entry=144.5, stop=134.5747, target=147.018,
     rr_planned=0.25, f_score=83.4, rating="Undervalued", sector="Energy", strategy_type="SWING",
     alt_data_score=42, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     final_verdict_reason="Best fundamental score in the whole quality pool (83.4, Undervalued) but target_atr 0.81 / R:R 0.25 means there is effectively no real technical trigger at this price — a flat consolidation, not a breakout or pullback. Thesis is fine (oil backdrop stable, OPEC+ holding output per Oct-2026 reporting; Q3 earnings Nov 6 not an immediate risk); this is a mechanical timing problem, not a reason to pass on a 83.4-score Undervalued name.",
     research_summary="OPEC+ held output targets steady for November (Reuters/CNBC/World Oil, early Oct 2026) — no supply shock either direction. EOG Q3 2026 earnings call set for Nov 6 (finviz) — outside near-term risk window."),

dict(ticker="OXY", conviction="Medium", setup="consolidation", entry=58.275, stop=53.6316, target=59.32,
     rr_planned=0.23, f_score=76.7, rating="Undervalued", sector="Energy", strategy_type="SWING",
     alt_data_score=51, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     final_verdict_reason="Same mechanical problem as the rest of the Energy cohort: target_atr 0.72 / R:R 0.23 is not a real setup regardless of the strong 76.7 Undervalued fundamental score. No insider or news red flags. Q3 earnings confirmed for Nov 9 (conference call Nov 10) — outside near-term risk window but worth tracking for a hold-period check if this re-enters later.",
     research_summary="Occidental confirmed Q3 2026 results for Monday Nov 9, 2026, call Nov 10 (GlobeNewswire via telcomagazine.com). No other material news found."),

dict(ticker="SHELL.AS", conviction="Medium", setup="consolidation", entry=43.225, stop=40.6661, target=43.835,
     rr_planned=0.24, f_score=76.6, rating="Undervalued", sector="Energy", strategy_type="SWING",
     alt_data_score=41, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     final_verdict_reason="Target_atr 0.76 / R:R 0.24 — same no-real-trigger problem. Thesis is actually well-supported (active multi-billion buyback programme, shareholder-friendly capital returns), but there's no technical room to trade it at this exact level. EU alt-data is data-thin (expected for this ticker class).",
     research_summary="Shell plc running an active multi-billion-dollar share buyback programme (daily executions through a Goldman Sachs-managed plan, confirmed via multiple Aug-2026 releases; programme ongoing). No negative news found."),

dict(ticker="SM", conviction="Medium", setup="consolidation", entry=35.26, stop=31.0491, target=35.875,
     rr_planned=0.15, f_score=76.5, rating="Undervalued", sector="Energy", strategy_type="SWING",
     alt_data_score=34, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     final_verdict_reason="Mixed and inconclusive: alt-data is BEARISH (score 34, insider selling, moderate 6.6% short interest) but real news is bullish (post-merger quarter, raised H2 production outlook, debt paydown, dividend increase, stock +31% in the 30 days after its last earnings report) — likely insiders taking profit into a real rally, not a thesis break. Combined with target_atr 0.47 / R:R 0.15 giving no real entry trigger either way, this is squarely a TIMING wait, not a PASS.",
     research_summary="SM Energy's post-merger quarter featured synergies, debt reduction, raised H2 production outlook and a dividend increase; stock reportedly +31% in the 30 days after its last earnings print (kavout.com market-lens, paywalled beyond summary). Alt-data shows insider selling + rising-ish short interest concurrently."),

dict(ticker="COP", conviction="Medium", setup="consolidation", entry=130.35, stop=120.9386, target=132.115,
     rr_planned=0.19, f_score=73.3, rating="Undervalued", sector="Energy", strategy_type="SWING",
     alt_data_score=51, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     final_verdict_reason="Target_atr 0.6 / R:R 0.19 — no real trigger. Thesis supportive (Q2 profit beat, plans to return a large share of cash flow to shareholders per Nasdaq coverage). Q3 call confirmed Nov 5 — outside near-term risk window.",
     research_summary="ConocoPhillips beat Q2 profit expectations and reiterated a large shareholder-return plan (Nasdaq); Q3 2026 earnings call confirmed for Thursday Nov 5, 2026 (finviz)."),

dict(ticker="CBOE", conviction="Medium", setup="consolidation", entry=278.45, stop=243.2629, target=283.54,
     rr_planned=0.14, f_score=71.9, rating="Undervalued", sector="Financial Services", strategy_type="SWING",
     alt_data_score=51, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     research_summary="Cboe Global Markets confirmed Q3 2026 earnings release for Oct 30, 2026 (finviz/briefglance) — inside a typical SWING hold window if re-entered soon; flag as WATCH if this setup improves before then.",
     final_verdict_reason="Target_atr 0.46 / R:R 0.14 — no real trigger despite a strong 71.9 Undervalued score. No negative news found. Earnings confirmed Oct 30 — close enough to a future SWING hold period to flag WATCH if revisited."),

dict(ticker="CINF", conviction="Medium", setup="consolidation", entry=162.88, stop=155.3864, target=164.79,
     rr_planned=0.25, f_score=70.2, rating="Undervalued", sector="Financial Services", strategy_type="SWING",
     alt_data_score=51, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     research_summary="Cincinnati Financial scheduled its Q3 2026 results webcast (finviz); one insider (Debbink) bought $171,640 in the last 30 days — alt-data-agent's own framework rates this SINGLE_BUY as negligible relative to this name's size/liquidity.",
     final_verdict_reason="Target_atr 0.82 / R:R 0.25 — no real trigger. Modest insider buy noted but explicitly negligible per alt-data-agent's own sizing rule; not enough to override the mechanical problem."),

dict(ticker="PSX", conviction="Medium", setup="consolidation", entry=273.93, stop=245.178, target=275.8,
     rr_planned=0.07, f_score=68.3, rating="Undervalued", sector="Energy", strategy_type="SWING",
     alt_data_score=39, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     final_verdict_reason="The closest case to a PASS in the pool: alt-data is BEARISH (score 39) with the largest insider-selling figure here ($27.0M net) plus short interest rising +37.3% MoM, layered on top of the worst R:R in the cohort (0.07/target_atr 0.21). Real news shows the stock already ran +17.5% in a month on tightening refining margins — this reads as distribution into strength after a real move, not a broken thesis, so WAIT rather than PASS, but re-underwrite before considering it again.",
     research_summary="Phillips 66 management said product-market outlook looks tighter and refining margins should stay constructive (Newsquawk); stock reported up 17.5% in the prior month (Nasdaq/Zacks) — an older Raymond James $205 target found in search is very likely stale (below the current ~$274 level) and not usable as a live target."),

dict(ticker="VLO", conviction="Medium", setup="consolidation", entry=428.2514, stop=374.8388, target=428.99,
     rr_planned=0.01, f_score=68.3, rating="Undervalued", sector="Energy", strategy_type="SWING",
     alt_data_score=51, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     final_verdict_reason="R:R 0.01 / target_atr 0.04 — essentially zero room to target, the weakest technical trigger in the entire scan. Q3 earnings confirmed Oct 22 (inside a plausible future SWING hold period — flag DANGER if revisited before then) and a real negative operational item (planned Benicia refinery closure by April 2026) gives the bear case more substance than the rest of the Energy cohort, though it's a 2027-dated structural issue, not an immediate one.",
     research_summary="Valero Q3 2026 earnings confirmed for Oct 22, 2026 (finviz). Separately, Valero plans to cease operations at its Benicia, CA refinery by April 2026 (TipRanks/The Fly) — a real structural capacity reduction, not yet a near-term catalyst."),

dict(ticker="AIZ", conviction="Medium", setup="consolidation", entry=268.44, stop=250.072, target=271.28,
     rr_planned=0.15, f_score=67.4, rating="Undervalued", sector="Financial Services", strategy_type="SWING",
     alt_data_score=48, institutional_score=50, institutional_alignment="CAUTIOUS",
     risk_manager_verdict="REJECT", final_verdict="WAIT",
     final_verdict_reason="Target_atr 0.49 / R:R 0.15 — no real trigger. Short interest +14.9% MoM is a mild watch-item (still LOW absolute level at 3.55%), not disqualifying. No earnings date or other news surfaced in research.",
     research_summary="No material news found beyond an SEC Q2 2026 8-K filing; short interest rising +14.9% MoM but still a LOW absolute level (3.55% of float)."),
]

out = {"scan_date": "2026-10-09", "candidates": candidates}
with open("data/scan_test_group.json", "w") as f:
    json.dump(out, f, indent=2)
print("Wrote", len(candidates), "candidates to data/scan_test_group.json")
