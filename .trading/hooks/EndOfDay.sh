#!/bin/bash
# .trading/hooks/EndOfDay.sh

DATE=$(date '+%Y-%m-%d')
SNAPSHOT_DIR="./snapshots/$DATE"
mkdir -p "$SNAPSHOT_DIR"

cp ./logs/trades.jsonl "$SNAPSHOT_DIR/" 2>/dev/null && echo "trades.jsonl saved" || echo "WARNING: trades.jsonl not found"
cp ./data/sentiment_data.json "$SNAPSHOT_DIR/" 2>/dev/null && echo "sentiment_data.json saved" || echo "WARNING: sentiment_data.json not found"

echo "End of day snapshot saved to $SNAPSHOT_DIR"

# Session note reminder
SESSION_FILE="./sessions/$DATE.md"
if [ ! -f "$SESSION_FILE" ]; then
    echo ""
    echo "⚠ No session note saved for today."
    echo "  Save one before closing: sessions/$DATE.md"
    echo "  Include: pipeline run, tickers scanned, entries/exits, key observations."
fi
