#!/bin/bash
# .trading/hooks/PreMarket.sh

OPEN=$(python3 -c "
import json
try:
    trades = [json.loads(l) for l in open('./logs/trades.jsonl')]
    print(len([t for t in trades if t.get('status') == 'open']))
except:
    print('?')
" 2>/dev/null)

SENTIMENT_TS=$(python3 -c "
import json
try:
    s = json.load(open('./data/sentiment_data.json'))
    print(s.get('generated_at', 'unknown')[:10])
except:
    print('no data')
" 2>/dev/null)

echo "[PRE-MARKET] $(date '+%Y-%m-%d %H:%M') | Open positions: $OPEN | Sentiment data: $SENTIMENT_TS"
