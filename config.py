# config.py — single source of truth for all shared constants

import os
from pathlib import Path

# ── .env loader (dependency-free) ─────────────────────────────────────────────
# Load key=value pairs from a local .env into the environment. Keeps personal
# values (account size, API keys) out of committed source. Uses setdefault so it
# never overrides a variable already set in the shell, and is safe to import
# repeatedly. This also gives every script that imports config a consistent way
# to see .env values.
def _load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
_load_env()

# ── Account ───────────────────────────────────────────────────────────────────
# Real account size lives in .env (gitignored) as ACCOUNT_SIZE=...; the neutral
# default keeps committed code free of personal financial data.
ACCOUNT_SIZE = int(os.getenv("ACCOUNT_SIZE", "100000"))   # EUR

# ── Risk / sizing ─────────────────────────────────────────────────────────────
RR_RATIO     = 1.5             # minimum risk/reward ratio (RISK.md)

# ── Fetch / filter thresholds ────────────────────────────────────────────────
MIN_PRICE         = 0.50       # skip penny stocks below this
MIN_AVG_VOLUME    = 500_000    # min 20-day avg volume — US stocks
MIN_ATR_PCT       = 2.0        # min ATR% — US stocks
EU_MIN_AVG_VOLUME = 100_000    # EU stocks trade thinner
EU_MIN_ATR_PCT    = 1.5        # EU stocks less volatile than US
SR_WINDOW         = 10         # days for support/resistance lookback
LOOKBACK_DAYS     = 60         # days of OHLCV history to pull
MAX_TICKERS       = 3200       # safety cap on watchlist size

# ── Batch settings (Yahoo Finance rate-limit avoidance) ───────────────────────
BATCH_SIZE     = 50            # tickers per US batch
BATCH_PAUSE    = 5             # seconds between US batches
EU_BATCH_SIZE  = 20            # tickers per EU batch
EU_BATCH_PAUSE = 4             # seconds between EU batches

# ── European exchange suffixes ────────────────────────────────────────────────
EU_SUFFIXES = {
    ".MI", ".AS", ".PA", ".L", ".DE", ".F", ".ST", ".CO",
    ".OL", ".HE", ".BR", ".LS", ".MC", ".VI", ".SW", ".AT",
}

# ── Japanese exchange suffixes (Tokyo Stock Exchange) ─────────────────────────
JP_SUFFIXES = {".T"}

# ── Japan-specific thresholds ─────────────────────────────────────────────────
JP_MIN_AVG_VOLUME = 500_000    # JPY-denominated stocks trade high share volumes
JP_MIN_ATR_PCT    = 1.5        # similar volatility profile to EU
JP_BATCH_SIZE     = 20
JP_BATCH_PAUSE    = 4

# ── Canadian exchange suffixes (Toronto Stock Exchange) ───────────────────────
CA_SUFFIXES = {".TO", ".V"}

# ── Canada-specific thresholds ────────────────────────────────────────────────
CA_MIN_AVG_VOLUME = 200_000    # TSX trades lower volumes than US
CA_MIN_ATR_PCT    = 2.0        # energy/mining stocks — similar volatility to US
CA_BATCH_SIZE     = 20
CA_BATCH_PAUSE    = 4

# ── Brazilian exchange suffixes (B3 - São Paulo) ──────────────────────────────
BR_SUFFIXES = {".SA"}

# ── Brazil-specific thresholds ────────────────────────────────────────────────
BR_MIN_AVG_VOLUME = 1_000_000  # BRL-denominated stocks trade very high volumes
BR_MIN_ATR_PCT    = 2.0        # volatile market, similar to US threshold
BR_BATCH_SIZE     = 20
BR_BATCH_PAUSE    = 4

# ── Scan / agent filters ──────────────────────────────────────────────────────
CONVICTION_FILTER = {"High", "Medium"}  # tickers passed to fundamental + alt data agents

# ── File paths ────────────────────────────────────────────────────────────────
WATCHLIST_PATH       = "./data/watchlist.txt"
MARKET_DATA_PATH     = "./data/market_data.json"
FUNDAMENTAL_PATH     = "./data/fundamental_data.json"
ALT_DATA_PATH        = "./data/alt_data.json"
SENTIMENT_PATH       = "./data/sentiment_data.json"
EARNINGS_PATH        = "./data/earnings_calendar.json"
MACRO_REGIME_PATH    = "./data/macro_regime.json"
MACRO_FRED_PATH      = "./data/macro_fred.json"
SECTOR_ROTATION_PATH = "./data/sector_rotation.json"
WATCHLIST_RANKED_PATH= "./data/watchlist_ranked.json"
PREMARKET_GAPS_PATH  = "./data/premarket_gaps.json"
TRADES_PATH          = "./logs/trades.jsonl"
BACKTEST_PATH        = "./data/backtest_results.json"
