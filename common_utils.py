"""
common_utils.py — small helpers shared by many scripts.

Usage from another script:
    from common_utils import load_watchlist
    tickers = load_watchlist()
"""
import os
from config import WATCHLIST_PATH
import logging
log = logging.getLogger("common_utils")

# load_watchlist reads the watchlist file and returns a list of tickers.
def load_watchlist(path=WATCHLIST_PATH):
    # Stop with a clear message if the file isn't there
    if not os.path.exists(path):
        log.error("Watchlist file not found: %s", path)
        raise FileNotFoundError(path)
    tickers = []
    with open(path, encoding="utf-8") as list_file:
        for line in list_file:
            line = line.strip()
            if line:
                tickers.append(line)
    return tickers


