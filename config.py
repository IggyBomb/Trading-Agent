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
# bubble watch is at an early stage (2 or 3 only) -- possibly catching a
# rally the composite score hasn't fully priced. Stage 4 is excluded,
# confirmed or not (2026-10-29): unconfirmed Stage 4 is already late-stage. Fixed on purpose (independent of the main list's --top), so
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

# -- Earnings rule (watchlist_ranker + position_monitor) -- added 2026-10-30 --
# No ranking penalty before earnings any more (a stock 7 sessions out can
# still run). Instead, for SWING / MOMENTUM only:
#  - held positions are HALVED at the latest EARNINGS_EXIT_SESSIONS before the report
#  - no new entry within EARNINGS_EXIT_SESSIONS of the report (final-analyst -> WAIT)
# POSITION / TURNAROUND / EVENT and the long-term track are NOT affected.
EARNINGS_EXIT_SESSIONS   = 2
EARNINGS_TRIM_STRATEGIES = {"SWING", "MOMENTUM"}
EARNINGS_TRIM_FRACTION   = 0.5

# -- Gap / news-shock detector (fetch_data.detect_gap) -- added 2026-10-30 --
# Price-only detection: an opening gap > GAP_ATR_MULT x ATR14 on volume >
# GAP_VOL_MULT x the 20d average (both measured on the bars BEFORE the gap).
# Only a gap that coincides with an EARNINGS report changes scoring (label
# "earnings_gap": 0 setup points, conviction capped at Medium, gap bar removed
# from ATR / volume average, no measured-move target). News / M&A gaps and
# gaps whose earnings date is unknown are scored normally and only labelled.
GAP_ATR_MULT             = 2.0
GAP_VOL_MULT             = 2.5
GAP_HOLD_SESSIONS        = 10   # = SR_WINDOW: label lasts while the gap bar sits in the S/R window
GAP_EARNINGS_WINDOW_DAYS = 1    # report on the gap day or the session before (after-close reports)

# -- Gold regime (gold_regime.py -> watchlist_ranker.regime_penalty) -- 2026-10-30
# Only for yfinance industries in GOLD_INDUSTRIES. Gold has no cash flow: its
# opportunity cost is the REAL yield, and it is priced in dollars. Rising real
# yields or a strengthening dollar = headwind, but only once gold's own trend
# confirms it (GLD < MA200): in 2022-25 real yields were at 15y highs and gold
# still doubled on central-bank buying. Copper / uranium / everything else and
# the long-term track are not affected.
GOLD_INDUSTRIES           = {"Gold", "Silver", "Other Precious Metals & Mining"}
GOLD_REAL_YIELD_UP_BP     = 50    # 10Y TIPS real yield rise over ~3 months
GOLD_DOLLAR_UP_PCT        = 3.0   # dollar index rise over ~3 months, and still > its MA50
GOLD_2Y_OFF_PEAK_BP       = 50    # 2Y yield this far below its 6M high = market pricing the rate peak
GOLD_HEADWIND_PEN         = -10
GOLD_TAILWIND_BONUS       = 5     # also needs GDX/GLD > its MA50 (miners leading gold)
GOLD_REGIME_MAX_AGE_HOURS = 36    # older file = ignored (neutral)

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
GOLD_REGIME_PATH     = str(DATA_DIR / "gold_regime.json")
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

# ── Leverage scoring (fundamental_agent.score_quality) ──────────────────────
# D/E is scored RELATIVE to the sector median, not on absolute bands: 1.5 is
# normal for a utility and a warning for software. Generated by
# research/sector_de_medians.py from fundamental_data.json (2026-10-30 run,
# 671 validated tickers, min 20 per sector). Refresh quarterly.
# Financial Services is deliberately absent -- D/E and interest coverage are
# not fragility measures for banks/insurers, so both are skipped there.
SECTOR_DE_MEDIAN = {
    "Basic Materials": 0.61,
    "Communication Services": 1.2,
    "Consumer Cyclical": 1.23,
    "Consumer Defensive": 1.18,
    "Energy": 0.51,
    "Healthcare": 0.69,
    "Industrials": 0.8,
    "Real Estate": 0.88,
    "Technology": 0.44,
    "Utilities": 1.82,
}
DE_FALLBACK_MEDIAN     = 0.7    # sector missing from the table: old absolute pivot
DE_NO_SCORE_SECTORS    = {"Financial Services"}

# Interest coverage = EBIT / interest expense (Minsky at company level):
# > HEDGE hedge finance, < 1 Ponzi (EBIT doesn't cover interest).
COVERAGE_HEDGE         = 8.0
COVERAGE_COMFORT       = 3.0
COVERAGE_SPECULATIVE   = 1.5
DEBT_FREE_DE           = 0.1    # no interest line + D/E below this = debt-free
# Yahoo data fixes (2026-11-01):
# A) Some issuers stopped reporting interest expense (AAPL: NaN from FY2024).
#    Use the latest fiscal year that has it, at most this many years back.
INTEREST_LOOKBACK_YEARS = 2
# B) IFRS issuers report gross "finance expense" incl. FX/derivative losses
#    (ENI FY25: 8.17B gross vs 0.97B net). When interest income offsets more
#    than this share of the gross figure, coverage uses NET interest instead.
NET_INTEREST_OFFSET_PCT = 0.5
NET_LENDER_COVERAGE     = 99.0  # interest income >= expense, EBIT > 0: stored as this cap

# ── Minsky fragility score (macro_regime_classifier.minsky_score) ───────────
# FRED public CSV, no key. Each check falls back to its old yfinance proxy if
# the series is unavailable, so the score never silently floors at 0.
MINSKY_HY_OAS_TIGHT    = 3.5    # % -- ICE BofA US HY OAS below this = complacent credit
MINSKY_REAL_YIELD_JUMP = 0.50   # pct points rise in 10Y TIPS yield over ~3M (63 obs)
MINSKY_DEBT_GDP_PCTILE = 0.80   # nonfin. corporate debt/GDP in top 20% of its history

# ── Inflation level guard (macro_regime_classifier.apply_inflation_level_guard)
# The market score reads inflation DIRECTION only. With CPI at 8% and easing
# (Jun/Sep 2022) it said DEFLATION and favoured long bonds while TLT fell
# ~30%. Above this CPI YoY, weak growth + easing inflation = STAGFLATION.
INFLATION_HIGH_CPI_YOY = 3.0    # % -- Fed 2% target + 1pt tolerance
