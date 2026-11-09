"""
main.py — runs the quant evaluations on the watchlist and saves the results.

Run from the repo root:
    python data/quant/main.py              # whole watchlist (the weekly scheduled run)
    python data/quant/main.py MU ICHR      # only these tickers (testing)
"""

import logging
import os
import sys

import yfinance

# common_utils.py and config.py live in the repo root, two levels up from data/quant
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from common_utils import load_watchlist
from DB_logger import DBLogger
from evaluation import Valuation
from growth import Growth
from profitability import Profitability
from momentum import Momentum
from revisions import Revisions

log = logging.getLogger("quant_main")

# Every evaluation run on each ticker (each one saves to its own table)
EVALUATIONS = [Valuation, Growth, Profitability, Momentum, Revisions]

# This many tickers in a row with no answer from Yahoo = network or Yahoo is down:
# stop instead of failing every remaining ticker
MAX_FAILURES_IN_A_ROW = 10

# ═══════════════════════════ TODO — still to write ═══════════════════════════
# 3. peer_comparison: get the sector, build Valuation(peer) for each peer, take
#    the median of each metric. Do it ONCE per sector (keep a dict
#    sector -> medians), not once per ticker. Then per metric: % diff vs sector
#    median, and a grade.
# 4. 5-year average column (optional): needs the annual statements, separate step.
# ═════════════════════════════════════════════════════════════════════════════


def main(tickers=None):
    # No tickers given = the whole watchlist
    tickers = tickers or load_watchlist()
    log.info(f"Run started: {len(tickers)} tickers")

    logger = DBLogger()                                              # once, before the loop
    for evaluation in EVALUATIONS:
        logger.create_table(evaluation.TABLE_NAME, evaluation.columns())   # only built the first time

    saved, skipped, failed = 0, 0, 0                                 # for the summary at the end
    failures_in_a_row = 0
    for ticker in tickers:
        # Downloaded once, shared by every evaluation of this ticker
        stock = yfinance.Ticker(ticker)

        # First ask Yahoo for the basics: if it doesn't answer, skip the 5 evaluations
        try:
            price = (stock.info or {}).get("currentPrice")
        except Exception as e:
            failures_in_a_row += 1
            failed += 1
            log.error(f"{ticker}: no answer from Yahoo ({e})")
            if failures_in_a_row >= MAX_FAILURES_IN_A_ROW:
                log.error(f"{failures_in_a_row} tickers in a row got no answer: network or Yahoo is down, run stopped")
                logger.close()
                sys.exit(1)   # the scheduled task shows as failed
            continue
        failures_in_a_row = 0

        # No price = Yahoo has no data for this ticker (e.g. delisted): don't save empty rows
        if price is None:
            skipped += 1
            log.warning(f"{ticker}: no data from Yahoo, skipped")
            continue

        for evaluation in EVALUATIONS:
            # One failed evaluation must not stop the others
            try:
                logger.log(evaluation(ticker, stock))
            except Exception as e:
                log.error(f"{ticker}: {evaluation.__name__} failed ({e})")
        saved += 1

    logger.close()                                                   # once, after the loop
    log.info(f"Run finished: {saved} tickers saved, {skipped} skipped (no data), {failed} no answer")


def keep_awake():
    # Tell Windows not to sleep while this script runs (a sleeping PC broke the
    # first full run). Released automatically when the script ends.
    if sys.platform == "win32":
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("DB_logger").setLevel(logging.WARNING)    # no line per saved row (817 x 5)
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)    # its own errors are reported by main
    keep_awake()
    main(sys.argv[1:])
