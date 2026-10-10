import json

with open('data/market_data.json') as f:
    md = json.load(f)
with open('data/fundamental_data.json') as f:
    fd = json.load(f)['fundamentals']

signals = md['signals']
rows = []
for s in signals:
    conv = s.get('conviction')
    if conv not in ('High', 'Medium'):
        continue
    t = s['ticker']
    fund = fd.get(t)
    f_rating = fund['rating'] if fund else None
    f_score = fund['f_score'] if fund else None
    if fund is None:
        flag = ''
    elif f_rating in ('Undervalued', 'Fair'):
        flag = 'CONFIRMED'
    elif f_rating == 'Overvalued':
        flag = 'CAUTION'
    else:
        flag = ''
    rows.append({
        'ticker': t, 'conviction': conv, 'setup': s.get('setup'),
        'entry': s.get('entry'), 'stop': s.get('stop'), 'target': s.get('target'),
        'rr': s.get('rr'), 'target_atr': s.get('target_atr'),
        'volume_ratio': s.get('volume_ratio'), 'atr_pct': s.get('atr_pct'),
        'trend': s.get('trend'), 'dist_support_pct': s.get('dist_support_pct'),
        'dist_resist_pct': s.get('dist_resist_pct'),
        'f_score': f_score, 'f_rating': f_rating, 'flag': flag,
        'sector': fund.get('sector') if fund else None,
    })

confirmed = [r for r in rows if r['flag'] == 'CONFIRMED']
caution = [r for r in rows if r['flag'] == 'CAUTION']
noflag = [r for r in rows if r['flag'] == '']

confirmed.sort(key=lambda r: (r['f_score'] is None, -(r['f_score'] or 0)))
caution.sort(key=lambda r: (r['volume_ratio'] is None, -(r['volume_ratio'] or 0)))

print(f"Total High/Medium conviction signals: {len(rows)}")
print(f"CONFIRMED: {len(confirmed)}  CAUTION: {len(caution)}  no-fundamental-data: {len(noflag)}")
high_confirmed = [r for r in confirmed if r['conviction'] == 'High']
med_confirmed = [r for r in confirmed if r['conviction'] == 'Medium']
print(f"CONFIRMED High: {len(high_confirmed)}  CONFIRMED Medium: {len(med_confirmed)}")

med_confirmed_sorted = sorted(med_confirmed, key=lambda r: -(r['f_score'] or 0))
quality_pool = high_confirmed + med_confirmed_sorted[:10]
print(f"Quality pool size: {len(quality_pool)}")
print()
print("=== QUALITY POOL ===")
for r in quality_pool:
    print(json.dumps(r))

print()
print("=== ALL CONFIRMED (ranked) ===")
for r in confirmed:
    print(f"{r['ticker']:8s} {r['conviction']:6s} {r['setup']:10s} entry={r['entry']} stop={r['stop']} target={r['target']} rr={r['rr']} target_atr={r['target_atr']} f_score={r['f_score']} f_rating={r['f_rating']}")

print()
print("=== ALL CAUTION (ranked) ===")
for r in caution:
    print(f"{r['ticker']:8s} {r['conviction']:6s} {r['setup']:10s} entry={r['entry']} stop={r['stop']} target={r['target']} rr={r['rr']} vol_ratio={r['volume_ratio']} f_score={r['f_score']} f_rating={r['f_rating']}")

with open('.scan_scratch/step1_4_output.json', 'w') as f:
    json.dump({'confirmed': confirmed, 'caution': caution, 'no_fund_data': noflag, 'quality_pool': quality_pool}, f, indent=2)
