#!/usr/bin/env python3
import json

with open('data/market_data.json', encoding='utf-8') as f:
    market = json.load(f)
with open('data/fundamental_data.json', encoding='utf-8') as f:
    fund = json.load(f).get('fundamentals', {})

signals = market.get('signals', [])

rows = []
for s in signals:
    conv = s.get('conviction')
    if conv not in ('High', 'Medium'):
        continue
    ticker = s.get('ticker')
    f = fund.get(ticker)
    if f is None:
        flag = ''
        f_score = None
        rating = None
    else:
        f_score = f.get('f_score')
        rating = f.get('rating')
        if rating in ('Undervalued', 'Fair'):
            flag = 'CONFIRMED'
        elif rating == 'Overvalued':
            flag = 'CAUTION'
        else:
            flag = ''
    rows.append({
        'ticker': ticker, 'setup': s.get('setup'), 'entry': s.get('entry'),
        'stop': s.get('stop'), 'target': s.get('target'), 'tech': conv,
        'f_score': f_score, 'rating': rating, 'flag': flag,
        'volume_ratio': s.get('volume_ratio'), 'atr_pct': s.get('atr_pct'),
        'trend': s.get('trend'), 'rr': s.get('rr'),
    })

confirmed = [r for r in rows if r['flag'] == 'CONFIRMED']
caution = [r for r in rows if r['flag'] == 'CAUTION']
nodata = [r for r in rows if r['flag'] == '']

confirmed.sort(key=lambda r: (r['f_score'] or 0), reverse=True)
caution.sort(key=lambda r: (r['volume_ratio'] or 0), reverse=True)

print(f"Total High/Medium technical signals: {len(rows)}")
print(f"CONFIRMED: {len(confirmed)}  CAUTION: {len(caution)}  NO FUND DATA: {len(nodata)}")
print()
print("=== CONFIRMED (sorted by f_score desc) ===")
for r in confirmed:
    print(f"{r['ticker']:<10} {r['setup']:<14} entry={r['entry']:<10} stop={r['stop']:<10} target={r['target']:<10} tech={r['tech']:<7} f_score={r['f_score']:<6} rating={r['rating']:<12} vol_ratio={r['volume_ratio']:<6} atr%={r['atr_pct']:<6} trend={r['trend']:<9} rr={r['rr']}")

print()
print("=== CAUTION (sorted by volume_ratio desc) ===")
for r in caution:
    print(f"{r['ticker']:<10} {r['setup']:<14} entry={r['entry']:<10} stop={r['stop']:<10} target={r['target']:<10} tech={r['tech']:<7} f_score={r['f_score']:<6} rating={r['rating']:<12} vol_ratio={r['volume_ratio']:<6} atr%={r['atr_pct']:<6} trend={r['trend']:<9} rr={r['rr']}")

print()
print(f"=== NO FUNDAMENTAL DATA ({len(nodata)}) — included as-is ===")
for r in nodata:
    print(f"{r['ticker']:<10} {r['setup']:<14} tech={r['tech']:<7} vol_ratio={r['volume_ratio']:<6}")

with open('scan_step1_4_output.json', 'w', encoding='utf-8') as f:
    json.dump({'confirmed': confirmed, 'caution': caution, 'nodata': nodata}, f, indent=2)
