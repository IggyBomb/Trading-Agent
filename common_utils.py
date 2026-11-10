"""
common_utils.py — small helpers shared by many scripts.

Usage from another script:
    from common_utils import load_watchlist, keep_awake
    keep_awake()                 # first thing in a long scheduled script
    tickers = load_watchlist()
"""
import os
import sys
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


# keep_awake tells Windows not to sleep while the calling script runs.
# A PC woken by Task Scheduler goes back to sleep after ~2 minutes unless a
# running program asks it not to. Released automatically when the script ends.
def keep_awake():
    if sys.platform != "win32":
        return
    import ctypes
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


