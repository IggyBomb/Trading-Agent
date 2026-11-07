"""
main.py — runs the quant evaluations on the watchlist and saves the results.

Run from the repo root:
    python data/quant/main.py
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

# While testing, run only these tickers. Set to None to run the whole watchlist.
TEST_TICKERS = ["MU"]

# Every evaluation run on each ticker (each one saves to its own table)
EVALUATIONS = [Valuation, Growth, Profitability, Momentum, Revisions]

# ═══════════════════════════ TODO — still to write ═══════════════════════════
# 3. peer_comparison: get the sector, build Valuation(peer) for each peer, take
#    the median of each metric. Do it ONCE per sector (keep a dict
#    sector -> medians), not once per ticker. Then per metric: % diff vs sector
#    median, and a grade.
# 4. 5-year average column (optional): needs the annual statements, separate step.
# ═════════════════════════════════════════════════════════════════════════════


def main():
    tickers = TEST_TICKERS or load_watchlist()

    logger = DBLogger()                                              # once, before the loop
    for evaluation in EVALUATIONS:
        logger.create_table(evaluation.TABLE_NAME, evaluation.columns())   # only built the first time

    for ticker in tickers:
        # Downloaded once, shared by every evaluation of this ticker
        stock = yfinance.Ticker(ticker)
        for evaluation in EVALUATIONS:
            # One bad ticker (or one failed evaluation) must not stop the run
            try:
                result = evaluation(ticker, stock)
                # No price = Yahoo has no data for this ticker: don't save empty rows
                if result.price is None:
                    log.warning(f"{ticker}: no data from Yahoo, skipped")
                    break
                logger.log(result)
            except Exception as e:
                log.error(f"{ticker}: {evaluation.__name__} failed ({e})")

    logger.close()                                                   # once, after the loop


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    main()
