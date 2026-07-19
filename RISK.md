# Risk Rules — Non-Negotiable

## Position Sizing — Dynamic Model

Position size is determined by the full analysis stack: Fear & Greed score, overall sentiment composite, EU composite, and conviction level. `trade_logger.py` reads `data/sentiment_data.json` automatically at entry time and prints the active tier.

| Tier | Max Size | Conditions |
|------|----------|------------|
| HALF | 1% | F&G >75 (extreme greed/euphoria) OR VIX >30 OR VSTOXX >25 |
| NORMAL | 2% | Default — neutral conditions |
| GOOD | 3% | F&G ≤50 AND composite ≥48 (fear/neutral regime, not bearish) |
| STRONG | 4% | F&G ≤45 AND composite ≥55 AND conviction = HIGH |
| MAX | 5% | F&G ≤30 AND composite ≥55 AND EU composite ≥58 AND conviction = HIGH |

**Rules:**
- Never exceed 5% under any circumstances
- Never exceed 3% without at least 2 independent signal confirmations
- Never exceed 4% without HIGH conviction — medium conviction caps at GOOD (3%)
- Never size up after a loss
- Max concurrent open positions: 5

## Drawdown Limits
- Daily max drawdown: 3% of account
- Weekly max drawdown: 6% of account
- If daily limit hit: stop trading, review journal

## Stop-Loss Logic
- Every trade MUST have a stop-loss set before entry
- Never move stop-loss against the trade
- Minimum R:R ratio: 1.5:1

---

## Short Selling Rules

### Position Sizing
- Max short position size: half the dynamic long maximum (e.g., NORMAL long=2% → short max=1%)
- Short size never exceeds 2.5% regardless of conditions — asymmetric downside in squeezes
- Max concurrent short positions: 3 (counted within the 5 max total positions)
- Never short a stock with float < 10 million shares

### Stop-Loss for Shorts
- Stop is a price level ABOVE entry — cover immediately if hit
- Never move stop higher (against the trade)
- Maximum stop distance: 5% above entry for SHORT-SWING, 8% for SHORT-POSITION
- Minimum R:R: 1.5:1 — same as longs

### Short Squeeze Pre-Check — mandatory before every short entry
- Short interest % of float > 20% → DO NOT SHORT
- Days to cover (short ratio) > 5 → reduce size by 50%, flag as squeeze risk
- Price up > 20% in last 10 days → DO NOT SHORT — momentum squeeze in progress
- Earnings, FDA, or M&A within 5 trading days → DO NOT SHORT

### Short Management Rules
- If short moves against you > 50% of initial risk: cover half immediately — no averaging up
- Cover into capitulation (high volume, fast drop) — do not hold through a short squeeze
- No adding to a losing short

### Drawdown Limits
- Same 3% daily / 6% weekly limits apply to the combined long + short book
