* score_panel_regressions.do — first-pass tests on data/backtest/score_panel.dta
* Run from the repo root:  stata -b do research/score_panel_regressions.do
* Needs: ssc install reghdfe, ftools, asreg  (once)

use "data/backtest/score_panel.dta", clear
keep if tradable == 1
xtset, clear
encode ticker, gen(tid)
encode setup,  gen(setup_c)
encode trend,  gen(trend_c)
encode region, gen(region_c)

* rows overlap in time (weekly scans, 20/60-day horizons) -> two-way cluster date + ticker
* and absorb date FE so only the cross-sectional ranking is tested

* 1. Does the conviction label predict anything?  (BUG4 question)
reghdfe xret_20_w i.conv_num if insample, absorb(date) vce(cluster date tid)
reghdfe xret_60_w i.conv_num if insample, absorb(date) vce(cluster date tid)

* 2. Which components carry the signal?  (are COMPOSITE_WEIGHTS sensible?)
reghdfe xret_20_w tech_score vol_score if insample, absorb(date) vce(cluster date tid)
reghdfe xret_20_w i.setup_c volume_ratio rsi c.dist_resist_pct support_bounce ///
        if insample, absorb(date) vce(cluster date tid)

* 3. Trade logic: target before stop (3.2x ATR stop, chart-level target)
* logit only allows one-way clustering; ticker is the more conservative choice here
logit target_hit i.conv_num target_atr i.setup_c i.region_c i.year if insample, vce(cluster tid)
reghdfe trade_r i.conv_num target_atr if insample, absorb(date) vce(cluster date tid)

* 4. Out of sample — same specs, never looked at while tuning
reghdfe xret_20_w i.conv_num tech_score vol_score if !insample, absorb(date) vce(cluster date tid)

* 5. Fama-MacBeth version of (2)
asreg xret_20_w tech_score vol_score if insample, fmb newey(4)   // lags = horizon/5 for weekly rows
