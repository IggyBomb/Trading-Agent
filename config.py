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
# RISK.md's stated minimum is 1.2:1 R:R. RR_RATIO below is NOT that number directly --
# it's compared against the live `rr` field, which is target_atr / ATR_STOP_MULT, so
# raising ATR_STOP_MULT shrinks `rr` for every ticker at a fixed target. Changed
# 2026-10-06: widened the stop to 3.2x ATR (more noise protection) and lowered
# RR_RATIO to 0.75 (not 1.2) specifically so the combined gate admits MORE candidates
# than the previous 1.5/2.0 setting, not fewer -- 1.2 @ 3.2x would need
# target_atr >= 3.84 and pass only ~7% of the High/Medium pool (vs ~14% today);
# 0.75 @ 3.2x needs target_atr >= 2.4, passing ~25%. See chat 2026-10-06 for the
# derivation -- do not "simplify" this back to 1.2 without redoing that math.
RR_RATIO     = 0.75            # compared against the live `rr` field (NOT the literal RISK.md ratio -- see above)
ATR_STOP_MULT = 3.2            # stop = entry -/+ ATR_STOP_MULT x ATR14 (was 1.0 until 2026-09-14, then 2.0;
                               # widened again 2026-10-06 for more noise protection)

# ── Fetch / filter thresholds ────────────────────────────────────────────────
MIN_PRICE         = 0.50       # skip penny stocks below this
MIN_AVG_VOLUME    = 300_000    # min 20-day avg volume — US stocks
MIN_ATR_PCT       = 1.0        # min ATR% — US stocks (was 2.5 until 2026-10-06)
EU_MIN_AVG_VOLUME = 67_500    # EU stocks trade thinner
EU_MIN_ATR_PCT    = 0.7        # EU stocks less volatile than US (was 1.8 until 2026-10-06)
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
JP_MIN_AVG_VOLUME = 150_000    # JPY-denominated stocks trade high share volumes
JP_MIN_ATR_PCT    = 1.5        # similar volatility profile to EU
JP_BATCH_SIZE     = 20
JP_BATCH_PAUSE    = 4

# ── Canadian exchange suffixes (Toronto Stock Exchange) ───────────────────────
CA_SUFFIXES = {".TO", ".V"}

# ── Canada-specific thresholds ────────────────────────────────────────────────
CA_MIN_AVG_VOLUME = 100_000    # TSX trades lower volumes than US
CA_MIN_ATR_PCT    = 2.0        # energy/mining stocks — similar volatility to US
CA_BATCH_SIZE     = 20
CA_BATCH_PAUSE    = 4

# ── Brazilian exchange suffixes (B3 - São Paulo) ──────────────────────────────
BR_SUFFIXES = {".SA"}

# ── Brazil-specific thresholds ────────────────────────────────────────────────
BR_MIN_AVG_VOLUME = 750_000  # BRL-denominated stocks trade very high volumes
BR_MIN_ATR_PCT    = 2.0        # volatile market, similar to US threshold
BR_BATCH_SIZE     = 20
BR_BATCH_PAUSE    = 4

# ── Scan / agent filters ──────────────────────────────────────────────────────
CONVICTION_FILTER = {"High", "Medium"}  # tickers passed to fundamental + alt data agents

# -- Fundamental refresh cadence ----------------------------------------------
# Fundamentals (FCF, income, PE, revenue growth) move at earnings pace, not
# daily -- re-scoring the same ticker every scan wastes yfinance calls for no
# fresher signal. fundamental_agent.py now scores the FULL valid universe
# (not just CONVICTION_FILTER tickers), but re-fetches a given ticker only
# once its cached score is older than this many days; everything still-fresh
# is carried over unchanged from the previous run's fundamental_data.json.
FUNDAMENTAL_MAX_AGE_DAYS    = 7
# Safety cap on FRESH fetches per run, so the first run against the full
# universe (previously ~15% of it via CONVICTION_FILTER, now 100%) ramps up
# over several runs instead of bursting ~1,900+ yfinance calls at once.
FUNDAMENTAL_MAX_NEW_PER_RUN = 400

# -- Alt-data refresh cadence -------------------------------------------------
# Same problem as fundamental_agent.py, worse multiplier: alt_data.py makes
# ~4-5 network calls per ticker (2 of them Finnhub, which is both rate-limited
# AND the free-tier source), not 1. alt_data.py now scores the FULL valid
# universe (not just CONVICTION_FILTER tickers), via the same staleness-cache
# pattern. TTL is shorter than fundamentals' because insider/MSPR filings are
# the fastest-moving SCORED signal here (~3d); news sentiment is technically
# daily but gets stale along with everything else in this single-TTL version
# -- true per-signal TTLs would need the 5 fetches decoupled, not done yet
# (see the TODO left in alt_data.py 2026-09-20).
ALT_DATA_MAX_AGE_DAYS    = 3
# Lower cap than FUNDAMENTAL_MAX_NEW_PER_RUN on purpose -- same reasoning,
# more expensive per ticker (4-5 calls vs 1), so fewer new fetches per run.
ALT_DATA_MAX_NEW_PER_RUN = 175

# -- Crowded-sector thresholds (watchlist_ranker.regime_penalty) -------------
# Mechanical, return-only trigger: either one firing is enough. No sector-rank
# requirement -- a sector can be crowded without being today's single #1.
SECTOR_RET_1M_THRESHOLD = 15   # percent, 1-month sector return
SECTOR_RET_3M_THRESHOLD = 40   # percent, 3-month sector return
# Tolerance band: a return within this many percentage points of a threshold
# still counts as a hit (e.g. 36% against a 40% 3M threshold still triggers,
# since 40 - 5 = 35 < 36). Applied to both thresholds the same way.
SECTOR_THRESHOLD_TOLERANCE = 5

# -- Bubble-watch gate (watchlist_ranker.regime_penalty) ---------------------
# The crowded-sector penalty above now only fires when macro-analyst.md has
# written data/bubble_watch.json flagging that sector/industry as Kindleberger
# Stage 4 CONFIRMED this session (see regime_penalty()). Macro reports run
# ~daily, not every pipeline run -- treat the file as stale (= no gate, penalty
# never fires on this basis) once it's older than this.
BUBBLE_WATCH_MAX_AGE_HOURS = 36

# -- Rescued_BW rank (watchlist_ranker.main) ---------------------------------
# A second, smaller rank alongside the main one: tickers whose sector/industry
# bubble watch is at an early, not-yet-confirmed stage (2, 3, or
# 4-not-confirmed) -- possibly catching a rally the composite score hasn't
# fully priced. Confirmed Stage 4 is excluded on purpose, since that's the
# same signal regime_penalty() already treats as "too late", not an
# opportunity. Fixed on purpose (independent of the main list's --top), so
# Rescued_BW always means the same thing regardless of how many rows main()
# prints.
# 2026-10-10: 20 -> 0. The pool now starts at pipeline-1 rank #1 instead of
# #21 -- the main top 20 is no longer excluded, so a bubble-watch name ranked
# highly on composite is eligible too. Ranks RESCUE_BW_TOP_CUTOFF+1 .. POOL_END.
RESCUE_BW_TOP_CUTOFF = 0
# Last pipeline-1 rank eligible for rescue (inclusive): the pool is ranks
# RESCUE_BW_TOP_CUTOFF+1 .. RESCUE_BW_POOL_END on COMPOSITE_WEIGHTS (1-100),
# not the whole tail -- anything below #100 is too far down to rescue.
RESCUE_BW_POOL_END = 100

# -- Composite score weights (watchlist_ranker.composite) --------------------
# Single source of truth: edit here, not inside composite(), and every
# consumer (watchlist_ranker.py's main rank, rescue_bw.py's Rescued_BW, or
# anything else built on build_scored_universe() later) picks it up.
# Must sum to 1.0 -- composite() doesn't re-normalize for you.
COMPOSITE_WEIGHTS = {"tech": 0.45, "fund": 0.25, "alt": 0.20, "volatility": 0.10}

# Rescued_BW uses its own split (rescue_bw.py only, never watchlist_ranker.py's
# main rank): heavier on technical/momentum, lighter on fundamentals, since
# these are specifically the tickers whose composite score DIDN'T make the
# main cut -- for a ticker in an early bubble-watch stage, how it's actually
# trading right now matters more here than it does for the main rank.
# 2026-10-05: tech 0.45->0.50, fund 0.25->0.20, alt/volatility unchanged.
RESCUE_BW_WEIGHTS = {"tech": 0.50, "fund": 0.20, "alt": 0.20, "volatility": 0.10}


# ── File paths ────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"

WATCHLIST_PATH       = str(DATA_DIR / "watchlist.txt")
MARKET_DATA_PATH     = str(DATA_DIR / "market_data.json")
FUNDAMENTAL_PATH     = str(DATA_DIR / "fundamental_data.json")
ALT_DATA_PATH        = str(DATA_DIR / "alt_data.json")
SENTIMENT_PATH       = str(DATA_DIR / "sentiment_data.json")
EARNINGS_PATH        = str(DATA_DIR / "earnings_calendar.json")
MACRO_REGIME_PATH    = str(DATA_DIR / "macro_regime.json")
MACRO_FRED_PATH      = str(DATA_DIR / "macro_fred.json")
SECTOR_ROTATION_PATH = str(DATA_DIR / "sector_rotation.json")
BUBBLE_WATCH_PATH    = str(DATA_DIR / "bubble_watch.json")
RESCUED_BW_PATH      = str(DATA_DIR / "rescued_bw.json")
WATCHLIST_RANKED_PATH= str(DATA_DIR / "watchlist_ranked.json")
PREMARKET_GAPS_PATH  = str(DATA_DIR / "premarket_gaps.json")
TRADES_PATH          = str(LOGS_DIR / "trades.jsonl")
BACKTEST_PATH        = str(DATA_DIR / "backtest_results.json")
SCAN_CANDIDATES_PATH = str(LOGS_DIR / "scan_candidates.jsonl")
SCAN_BACKTEST_PATH   = str(DATA_DIR / "scan_backtest_results.json")

# scan_tracking.db table that scan_logger.py writes and scan_daily_update.py
# tracks. scan_test_group is the frozen pre-bubble-watch table (old tracking
# rules); everything from the bubble-watch rescue onward goes here, with a
# selection_group column (HIGH / MEDIUM_POOL / BUBBLE_RESCUED) to compare groups.
SCAN_TRACKING_TABLE  = "scan_tracking_bubble_watch"
