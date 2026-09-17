#!/usr/bin/env python3
import json

md = {s['ticker']: s for s in json.load(open('data/market_data.json'))['signals']}
fd = json.load(open('data/fundamental_data.json'))['fundamentals']
ad = json.load(open('data/alt_data.json'))['tickers']

results = []
for tk, s in md.items():
    if s.get('trend') != 'down':
        continue
    if s.get('short_setup') not in ('breakdown', 'distribution', 'dead_cat'):
        continue
    if (s.get('atr_pct') or 0) < 2.0:
        continue
    if (s.get('avg_volume') or 0) < 500000:
        continue

    a = ad.get(tk)
    f = fd.get(tk)

    # Stage 2: squeeze pre-filter (disqualify)
    squeeze_data_missing = a is None
    short_pct = a['short_interest']['short_pct_float'] if a else None
    dtc = a['short_interest']['days_to_cover'] if a else None
    disqualified = False
    dq_reason = []
    if short_pct is not None and short_pct > 20:
        disqualified = True; dq_reason.append(f'short%float {short_pct}>20')
    if dtc is not None and dtc > 5:
        disqualified = True; dq_reason.append(f'DTC {dtc}>5')
    # price up >20% in last 10 days -- approximate via change_pct (1-day) not available as 10d; skip, flag missing
    if disqualified:
        continue

    # Stage 3: fundamental deterioration (max 6, need info we mostly don't have -> use what's available)
    fscore_val = f['f_score'] if f else None
    fund_score = 0
    if f:
        if f.get('earnings_growth') is not None and f['earnings_growth'] < 0:
            fund_score += 1
        if f.get('revenue_growth') is not None and f['revenue_growth'] < 0:
            fund_score += 1
        if fscore_val is not None and fscore_val <= 30:  # proxy for "F-Score <=3" on a 0-100 scale
            fund_score += 1
    analyst_deteriorating = a and a['analyst_trend'].get('trend') == 'DETERIORATING'
    if analyst_deteriorating:
        fund_score += 1

    # Stage 4: institutional distribution (max 4)
    inst_score = 0
    insider_selling_cluster = a and a['insider'].get('cluster_signal') == 'SELLING' and a['insider'].get('sellers_30d', 0) >= 3
    if insider_selling_cluster:
        inst_score += 1
    short_rising = a and a['short_interest'].get('mom_change_pct', 0) and a['short_interest']['mom_change_pct'] > 15
    if short_rising:
        inst_score += 1
    # smart money score / ETF flow not computed this session -> skip those two subcomponents

    # Score
    setup_pts = {'breakdown': 3, 'distribution': 2, 'dead_cat': 2}[s['short_setup']]
    vol_pts = 2 if (s.get('volume_ratio') or 0) > 1.5 else 0
    resist_pts = 2 if (s.get('dist_resist_pct') or 99) < 2 else 0
    fund_pts = 2 if fund_score >= 3 else 0
    inst_pts = 2 if inst_score >= 2 else 0
    # macro sector headwind: only Growth/Tech (high-multiple) and crowded Energy authorised this session
    sector_guess = f.get('sector') if f else None
    macro_pt = 0
    macro_note = 'not authorised'
    if sector_guess == 'Technology' and f and (f.get('pe') or 0) > 30:
        macro_pt = 1; macro_note = 'high-multiple Tech (authorised)'
    elif sector_guess == 'Energy':
        macro_pt = 1; macro_note = 'crowded Energy fade (authorised)'

    total = setup_pts + vol_pts + resist_pts + fund_pts + inst_pts + macro_pt
    if total >= 8:
        conv = 'HIGH'
    elif total >= 5:
        conv = 'MEDIUM'
    elif total >= 3:
        conv = 'LOW'
    else:
        conv = 'NONE'

    results.append({
        'ticker': tk, 'setup': s['short_setup'], 'score': total, 'conviction': conv,
        'atr_pct': s.get('atr_pct'), 'vol_ratio': s.get('volume_ratio'),
        'dist_resist_pct': s.get('dist_resist_pct'), 'short_pct_float': short_pct, 'dtc': dtc,
        'fscore': fscore_val, 'sector': sector_guess, 'macro_note': macro_note,
        'squeeze_data_missing': squeeze_data_missing,
    })

results = [r for r in results if r['conviction'] in ('HIGH', 'MEDIUM')]
results.sort(key=lambda r: -r['score'])

print(f"HIGH+MEDIUM short candidates after full scoring: {len(results)}")
for r in results:
    print(f"{r['ticker']:8s} score={r['score']:2d}/12 {r['conviction']:6s} setup={r['setup']:12s} atr%={r['atr_pct']:5.2f} vol={r['vol_ratio']:5.2f} "
          f"dist_resist={r['dist_resist_pct']:6.2f} short%float={r['short_pct_float']} dtc={r['dtc']} fscore={r['fscore']} sector={r['sector']} macro={r['macro_note']}")

with open('scan_short_screen_output.json', 'w') as f:
    json.dump(results, f, indent=2)
