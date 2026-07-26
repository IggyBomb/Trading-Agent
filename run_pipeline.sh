#!/bin/bash
# run_pipeline.sh — Pre-session pipeline orchestrator
# Runs all data scripts in order. Flags failures, never blocks.
# Usage: bash run_pipeline.sh

# Windows/portability fixes: resolve a working python, force UTF-8
# (Windows console default codepage can't encode the arrows/deltas the
# scripts print), and point at a merged CA bundle (certifi + Windows system
# store — this machine has something, likely AV/corporate TLS inspection,
# injecting a root cert that only the Windows store trusts, so certifi
# alone isn't enough for yfinance's curl_cffi backend). See
# .trading_certs/build_bundle.py.
PYTHON=python3
python3 --version >/dev/null 2>&1 || PYTHON=python
export PYTHONUTF8=1
"$PYTHON" "$(dirname "$0")/.trading_certs/build_bundle.py" >/dev/null 2>&1
BUNDLE="$(dirname "$0")/.trading_certs/combined_cacert.pem"
if [ -f "$BUNDLE" ]; then
    export SSL_CERT_FILE="$BUNDLE"
    export CURL_CA_BUNDLE="$BUNDLE"
fi

START=$(date '+%Y-%m-%d %H:%M:%S')
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

run_step() {
    local name="$1"
    local cmd="$2"
    local pillar="$3"

    echo -n "  [$name] "
    if output=$("$PYTHON" $cmd 2>&1); then
        echo -e "${GREEN}OK${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}FAILED${NC} ⚠ [$pillar PILLAR INCOMPLETE]"
        echo "    └─ $(echo "$output" | tail -3)"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo -e "${BOLD}=== PRE-SESSION PIPELINE === $START${NC}"
echo ""

echo "── CATALYST"
run_step "earnings_calendar" "earnings_calendar.py" "CATALYST"

# Check if any open positions have earnings flagged — trigger investor-relations
echo ""
"$PYTHON" - <<'EOF'
import json
from pathlib import Path

try:
    trades = [json.loads(l) for l in open('./logs/trades.jsonl')]
    open_tickers = {t['ticker'].upper() for t in trades if t.get('status') == 'open'}
except:
    open_tickers = set()

try:
    earnings_raw = json.load(open('./data/earnings_calendar.json'))
    earnings = earnings_raw.get('tickers', []) if isinstance(earnings_raw, dict) else earnings_raw
    flagged = [e for e in earnings if e.get('ticker', '').upper() in open_tickers and e.get('days_away', 99) <= 7]
except:
    flagged = []

if flagged:
    print(f"\033[1;33m  ⚠ INVESTOR-RELATIONS TRIGGERED\033[0m")
    for e in flagged:
        print(f"    └─ {e['ticker']} reports in {e.get('days_away','?')} days — run investor-relations.md before /scan")
EOF

echo ""
echo "── SUPPORT (data foundation)"
run_step "fetch_data      " "fetch_data.py" "SUPPORT"

echo ""
echo "── COOLDOWN (3 min — Yahoo Finance rate limit reset)"
for i in 3 2 1; do
    echo -ne "  Waiting ${i}m...\r"
    sleep 60
done
echo -e "  Cooldown complete.    "

echo ""
echo "── FUNDAMENTAL PILLAR"
run_step "fundamental_agent" "fundamental_agent.py" "FUNDAMENTAL"

echo ""
echo "── SENTIMENT PILLAR"
run_step "sentiment_agent " "sentiment_agent.py" "SENTIMENT"

echo ""
echo "── CATALYST PILLAR"
run_step "alt_data        " "alt_data.py" "CATALYST"

echo ""
echo "── SUPPORT"
run_step "macro_regime    " "macro_regime_classifier.py" "SUPPORT"
run_step "macro_fred      " "macro_data_fred.py" "SUPPORT"
run_step "sector_rotation " "sector_rotation.py" "SUPPORT"
run_step "watchlist_ranker" "watchlist_ranker.py" "SUPPORT"

echo ""
echo -e "${BOLD}=== PIPELINE SUMMARY ===${NC}"
echo "  Started : $START"
echo "  Finished: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "  Steps   : ${GREEN}$PASS OK${NC} / ${RED}$FAIL failed${NC}"
echo ""

# Three-pillar status
echo "── Pillar status:"
check_file() {
    local label="$1"
    local file="$2"
    local pillar="$3"
    if [ -f "$file" ]; then
        ts=$("$PYTHON" -c "import os,datetime; t=os.path.getmtime('$file'); print(datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M'))" 2>/dev/null)
        echo -e "  ${GREEN}✓${NC} $label ($pillar) → $ts"
    else
        echo -e "  ${RED}✗ MISSING${NC} $label — ${YELLOW}[$pillar PILLAR INCOMPLETE — flag in scan]${NC}"
    fi
}

check_file "fundamental_data.json" "data/fundamental_data.json" "FUNDAMENTAL"
check_file "sentiment_data.json  " "data/sentiment_data.json"   "SENTIMENT"
check_file "alt_data.json        " "data/alt_data.json"         "CATALYST"
check_file "macro_regime.json    " "data/macro_regime.json"     "SUPPORT"
check_file "macro_fred.json      " "data/macro_fred.json"       "SUPPORT"
check_file "sector_rotation.json " "data/sector_rotation.json"  "SUPPORT"
check_file "watchlist_ranked.json" "data/watchlist_ranked.json" "SUPPORT"

# Weekly journal-analyzer reminder (Fridays)
DAY=$(date '+%u')
if [ "$DAY" = "5" ]; then
    echo ""
    echo -e "${YELLOW}  ⚠ FRIDAY — run journal-analyzer.md for weekly performance review${NC}"
fi

echo ""
echo "Next: macro-analyst.md → /scan"
echo ""
