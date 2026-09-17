import json

candidates = [
  # === 4 WINNERS: full Steps 10-12 adjudication ===
  {
    "ticker": "VLO", "conviction": "High", "setup": "breakout",
    "entry": 388.95, "stop": 378.3764, "target": 443.36, "rr_planned": 5.15,
    "f_score": 68.3, "rating": "Undervalued", "sector": "Energy",
    "strategy_type": "SWING", "alt_data_score": 57, "institutional_score": 50,
    "institutional_alignment": "CAUTIOUS", "risk_manager_verdict": "APPROVE",
    "final_verdict": "BUY - REDUCED (50%)",
    "final_verdict_reason": "Analyst upgrades (Zacks #1, UBS PT $450) and confirmed Energy sector leadership support entry, but RSI 79.66 (most extreme non-META reading) plus tomorrow's regime-hinge CPI print argue for half size, not full.",
    "research_summary": "Zacks Rank #1 Strong Buy added 3 Sep, UBS PT $355->$450, Piper PT $329->$435, YTD +127.7%; RSI 79.66 extremely overbought; Energy sector cap now 2/2 with existing WMB position."
  },
  {
    "ticker": "SHOP", "conviction": "High", "setup": "reversal",
    "entry": 126.79, "stop": 120.6758, "target": 156.49, "rr_planned": 4.86,
    "f_score": 55.3, "rating": "Fair", "sector": "Technology",
    "strategy_type": "SWING", "alt_data_score": 63, "institutional_score": 50,
    "institutional_alignment": "CAUTIOUS", "risk_manager_verdict": "APPROVE",
    "final_verdict": "BUY - REDUCED (65%)",
    "final_verdict_reason": "STRONG_CLUSTER insider buying ($287M/3 insiders) into a rotation-driven, non-fundamental dip with shorts covering -42.1% MoM is the strongest alt-data signal researched this session; sized below full only for an unconfirmed earnings date and today's session-wide macro event risk, not a thesis flaw.",
    "research_summary": "Decline is valuation/rotation profit-taking (ARK trimming post +25% rally), not fundamental break - Q2 strong, next-Q EPS growth est +29.41%. STRONG_CLUSTER insider buy $287M into the dip."
  },
  {
    "ticker": "ADM", "conviction": "High", "setup": "breakout",
    "entry": 86.55, "stop": 83.5971, "target": 95.94, "rr_planned": 3.18,
    "f_score": 50.7, "rating": "Fair", "sector": "Consumer Defensive",
    "strategy_type": "SWING", "alt_data_score": 77, "institutional_score": 50,
    "institutional_alignment": "CAUTIOUS", "risk_manager_verdict": "APPROVE",
    "final_verdict": "BUY - REDUCED (70%)",
    "final_verdict_reason": "Cleanest, most cross-confirmed setup this session - guidance raise, analyst upgrade, BULLISH alt-data score (77, best of 20 researched), bullish insider MSPR, short covering, all aligned with no contradicting data point found. Bear case was WEAK (macro-timing only) - sized at 70%, the high end, purely per today's session-wide macro sizing note ahead of tomorrow's CPI.",
    "research_summary": "FY26 EPS guidance raised to $5.15-5.60, UBS upgrade, $500-750M cost-savings program on track, Q2 adj EPS +98% YoY. Alt-data score 77 BULLISH, best in the entire 20-ticker research population."
  },
  {
    "ticker": "AON", "conviction": "High", "setup": "reversal",
    "entry": 304.69, "stop": 294.4543, "target": 358.71, "rr_planned": 5.28,
    "f_score": 45.3, "rating": "Fair", "sector": "Financial Services",
    "strategy_type": "SWING", "alt_data_score": 52, "institutional_score": 50,
    "institutional_alignment": "CAUTIOUS", "risk_manager_verdict": "APPROVE",
    "final_verdict": "BUY - REDUCED (50%)",
    "final_verdict_reason": "Overreaction thesis is plausible and evidenced (zero analyst downgrades, director bought $6.55M into the post-deal weakness, short interest low and covering), but the $17B USI deal is all-debt-financed and elevated rates are a direct, mechanism-specific cost-of-capital headwind compounding tomorrow's CPI risk - real enough to size at half rather than full.",
    "research_summary": "Selloff is a clean, dated M&A financing/integration-risk repricing (KKR USI deal, $17B, all-debt), not organic deterioration - zero downgrades, 1 upgrade in the past month. Director bought $6.55M into the post-announcement weakness."
  },
  # === 5 exposure-capped REJECTs: individually cleared risk-manager mechanics, no slot available ===
  {
    "ticker": "PRU", "conviction": "High", "setup": "reversal",
    "entry": 117.59, "stop": 115.0411, "target": 123.57, "rr_planned": 2.35,
    "f_score": 53.8, "rating": "Fair", "sector": "Financial Services",
    "strategy_type": "SWING", "alt_data_score": 59, "institutional_score": 50,
    "institutional_alignment": "CAUTIOUS", "risk_manager_verdict": "REJECT",
    "final_verdict": None, "final_verdict_reason": None,
    "research_summary": "Portfolio exposure - no slots remaining. Individually cleared all mechanical checks (R:R 2.35, stop 3.36% OK) but ranked below AON within the 2-position Financial Services sector cap, and total 4-slot cap was already filled by AON/VLO/SHOP/ADM. Q2 beat +22%, buyback active, but 0% analyst buy-rated is a live divergence worth a future look."
  },
  {
    "ticker": "UBER", "conviction": "Medium", "setup": "pullback",
    "entry": 71.08, "stop": 68.6947, "target": 82.365, "rr_planned": 4.73,
    "f_score": 59.4, "rating": "Fair", "sector": "Technology",
    "strategy_type": "SWING", "alt_data_score": 59, "institutional_score": 50,
    "institutional_alignment": "CAUTIOUS", "risk_manager_verdict": "REJECT",
    "final_verdict": None, "final_verdict_reason": None,
    "research_summary": "Portfolio exposure - no slots remaining. Confirmed COO $5.3M open-market buy 8 Sep - clean setup, individually cleared checks, but 4-slot cap already filled by higher-ranked candidates before Technology's second slot could be considered."
  },
  {
    "ticker": "ROP", "conviction": "Medium", "setup": "pullback",
    "entry": 390.35, "stop": 380.6114, "target": 429.6, "rr_planned": 4.03,
    "f_score": 60.9, "rating": "Fair", "sector": "Technology",
    "strategy_type": "SWING", "alt_data_score": 42, "institutional_score": 50,
    "institutional_alignment": "CAUTIOUS", "risk_manager_verdict": "REJECT",
    "final_verdict": None, "final_verdict_reason": None,
    "research_summary": "Portfolio exposure - no slots remaining. EPS beat, Moderate Buy consensus, no red flags, but ranked below UBER within Technology's capped allocation and total slots already exhausted."
  },
  {
    "ticker": "MSFT", "conviction": "Medium", "setup": "pullback",
    "entry": 491.65, "stop": 481.775, "target": 517.78, "rr_planned": 2.65,
    "f_score": 63.7, "rating": "Undervalued", "sector": "Technology",
    "strategy_type": "SWING", "alt_data_score": 40, "institutional_score": 50,
    "institutional_alignment": "CAUTIOUS", "risk_manager_verdict": "REJECT",
    "final_verdict": None, "final_verdict_reason": None,
    "research_summary": "Portfolio exposure - no slots remaining. Azure disclosure improving, 92.8% Street buy-rated, but lowest R:R (2.65) among the Technology candidates and total slots already exhausted."
  },
  {
    "ticker": "CBOE", "conviction": "Medium", "setup": "pullback",
    "entry": 291.87, "stop": 281.5785, "target": 316.8598, "rr_planned": 2.43,
    "f_score": 68.6, "rating": "Undervalued", "sector": "Financial Services",
    "strategy_type": "SWING", "alt_data_score": 49, "institutional_score": 50,
    "institutional_alignment": "CAUTIOUS", "risk_manager_verdict": "REJECT",
    "final_verdict": None, "final_verdict_reason": None,
    "research_summary": "Portfolio exposure - no slots remaining. 19% dividend hike, record Q2, clean setup, but Financial Services sector cap filled by AON (higher R:R) and total slots exhausted."
  },
  # === CAUTION-flagged in Step 9 (never reached Steps 10-12) ===
  {"ticker":"SYK","conviction":"High","setup":"reversal","entry":275.39,"stop":264.555,"target":333.39,"rr_planned":5.35,"f_score":56.0,"rating":"Fair","sector":"Healthcare","strategy_type":"SWING","alt_data_score":45,"institutional_score":50,"institutional_alignment":"CAUTIOUS","risk_manager_verdict":"CAUTION","final_verdict":None,"final_verdict_reason":None,"research_summary":"Fresh 7.7% drop on ongoing supply-chain issue, PT cut, INSIDER_SELLING $118.2M net (0 buyers), MSPR -95.0 (most negative in batch) - smart money and sell-side both trimming into the reversal zone."},
  {"ticker":"META","conviction":"High","setup":"breakout","entry":653.69,"stop":633.7864,"target":759.62,"rr_planned":5.32,"f_score":53.8,"rating":"Fair","sector":"Communication Services","strategy_type":"SWING","alt_data_score":48,"institutional_score":50,"institutional_alignment":"CAUTIOUS","risk_manager_verdict":"CAUTION","final_verdict":None,"final_verdict_reason":None,"research_summary":"Muse AI launch spike (+6.55% single day) but RSI 89.56 most extreme overbought reading in either batch, INSIDER_SELLING (8 sellers), MSPR -55.8 - chasing a spike, not a clean continuation entry."},
  {"ticker":"HPE","conviction":"High","setup":"breakout","entry":58.9,"stop":55.9382,"target":72.14,"rr_planned":4.47,"f_score":53.2,"rating":"Fair","sector":"Technology","strategy_type":"SWING","alt_data_score":48,"institutional_score":50,"institutional_alignment":"CAUTIOUS","risk_manager_verdict":"CAUTION","final_verdict":None,"final_verdict_reason":None,"research_summary":"Guidance raised, AI/Juniper strong, but stop 5.03% marginally exceeds the 5% swing ceiling - technical structure flaw, not a fundamental one."},
  {"ticker":"LMT","conviction":"High","setup":"reversal","entry":524.46,"stop":511.3894,"target":566.4564,"rr_planned":3.21,"f_score":50.7,"rating":"Fair","sector":"Industrials","strategy_type":"SWING","alt_data_score":48,"institutional_score":50,"institutional_alignment":"CAUTIOUS","risk_manager_verdict":"CAUTION","final_verdict":None,"final_verdict_reason":None,"research_summary":"Q1 EPS miss, FCF -$291M negative, INSIDER_SELLING, MSPR -78.1 - real fundamental headwind cluster underneath a technically clean oversold bounce."},
  {"ticker":"PHM","conviction":"High","setup":"reversal","entry":118.93,"stop":115.8714,"target":131.63,"rr_planned":4.15,"f_score":43.5,"rating":"Fair","sector":"Consumer Cyclical","strategy_type":"SWING","alt_data_score":36,"institutional_score":50,"institutional_alignment":"CAUTIOUS","risk_manager_verdict":"CAUTION","final_verdict":None,"final_verdict_reason":None,"research_summary":"Only BEARISH alt-data score in the High-10 batch (36); revenue -9.6% YoY, earnings -18.2% YoY are real declines two isolated sell-side upgrades don't offset."},
  {"ticker":"APP","conviction":"Medium","setup":"pullback","entry":305.06,"stop":291.9494,"target":335.45,"rr_planned":2.32,"f_score":68.5,"rating":"Undervalued","sector":"Communication Services","strategy_type":"SWING","alt_data_score":33,"institutional_score":50,"institutional_alignment":"CAUTIOUS","risk_manager_verdict":"CAUTION","final_verdict":None,"final_verdict_reason":None,"research_summary":"Still working through a post-Q2-crash analyst downgrade cycle, 3+ weeks on - alt-data BEARISH (33)."},
  {"ticker":"LYFT","conviction":"Medium","setup":"pullback","entry":14.9,"stop":14.1979,"target":17.98,"rr_planned":4.39,"f_score":65.3,"rating":"Undervalued","sector":"Technology","strategy_type":"SWING","alt_data_score":42,"institutional_score":50,"institutional_alignment":"CAUTIOUS","risk_manager_verdict":"CAUTION","final_verdict":None,"final_verdict_reason":None,"research_summary":"New CFO, Waymo Nashville partnership positive, but CLO/CAO insider selling and stop near the 5% ceiling."},
  {"ticker":"GEHC","conviction":"Medium","setup":"reversal","entry":65.17,"stop":63.6026,"target":74.235,"rr_planned":5.78,"f_score":60.7,"rating":"Fair","sector":"Healthcare","strategy_type":"TURNAROUND","alt_data_score":54,"institutional_score":50,"institutional_alignment":"CAUTIOUS","risk_manager_verdict":"CAUTION","final_verdict":None,"final_verdict_reason":None,"research_summary":"RSI 8.0 capitulation-level oversold, order growth/backlog real, but live unresolved DUAL_SIGNAL (simultaneous long+short mechanical setup) plus CFO transition and tariff drag - flagged for a Step 15 live watch, not an entry today."},
  {"ticker":"PATH","conviction":"Medium","setup":"pullback","entry":13.57,"stop":12.5619,"target":18.83,"rr_planned":5.22,"f_score":59.3,"rating":"Fair","sector":"Technology","strategy_type":"SWING","alt_data_score":26,"institutional_score":50,"institutional_alignment":"CAUTIOUS","risk_manager_verdict":"REJECT","final_verdict":None,"final_verdict_reason":None,"research_summary":"Stop 7.43% exceeds the 5% swing maximum; extreme 38% short interest rising, billings still missing - bearish confluence, mechanical R:R gate technically passed but risk-manager rejected on stop-sanity + alt-data grounds."},
  {"ticker":"PODD","conviction":"Medium","setup":"pullback","entry":137.92,"stop":132.6814,"target":151.5,"rr_planned":2.59,"f_score":58.5,"rating":"Fair","sector":"Healthcare","strategy_type":"SWING","alt_data_score":46,"institutional_score":50,"institutional_alignment":"CAUTIOUS","risk_manager_verdict":"CAUTION","final_verdict":None,"final_verdict_reason":None,"research_summary":"Guidance cut, Artisan Partners exited the position, target sits above the reset Street PT (144) - steepest analyst cut in the batch, bounce unconfirmed."},
  {"ticker":"ADBE","conviction":"Medium","setup":"pullback","entry":254.86,"stop":245.1079,"target":294.53,"rr_planned":4.07,"f_score":57.8,"rating":"Fair","sector":"Technology","strategy_type":"EVENT","alt_data_score":48,"institutional_score":50,"institutional_alignment":"CAUTIOUS","risk_manager_verdict":"CAUTION","final_verdict":None,"final_verdict_reason":None,"research_summary":"Reports earnings after today's close - pre-event entry prohibited per strategy-analyst's own rule (never enter an event trade on the event day itself). Re-screen post-print."},
]

out = {"scan_date": "2026-09-10", "candidates": candidates}
with open('data/scan_test_group.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f"Wrote {len(candidates)} candidates to data/scan_test_group.json")
