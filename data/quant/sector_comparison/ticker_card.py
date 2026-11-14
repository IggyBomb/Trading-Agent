"""
ticker_card.py — one card per ticker with everything the sector comparison needs:
who it is, which peer group it belongs to, and its metric values per category.

The card only holds data that was already loaded (no downloads, no comparison logic).
Cards are built once per run (download_all_latest_tickers_data at the bottom of this
file reads quant.db, then the cards are created from that) and passed to the comparison
functions in peers_compare.py.

Usage:
    card = TickerCard("MU", "Micron Technology, Inc.", "SM", "US",
                      valuation={"price_to_earnings_gaap_trailing": 9.28})
    card.valuation["price_to_earnings_gaap_trailing"]      # 9.28
    card.value("growth", "revenue_growth_year_over_year")  # None if missing
"""

from dataclasses import dataclass, field
import logging
import sqlite3
from pathlib import Path
log = logging.getLogger("ticker_card")

# The categories a card holds, same names as the fields below (used to loop over them).
# Each one is also the name of its table in quant.db
CATEGORIES = ["valuation", "growth", "profitability", "momentum", "revisions"]

# Columns every table has that are not metrics (who / when): left out of the card's category dicts
NOT_METRICS = ["date", "ticker", "name", "sector", "price"]

# A run counts as "full" if it has at least this share of the biggest run's tickers.
# Keeps one-ticker test runs (e.g. `main.py MU`) from being taken as the latest data
FULL_RUN_SHARE = 0.8

# function to load the ticker data from the database with the ticker's newest row
def load_ticker_data(ticker, database):
    ticker_data = {}
    try:
        # Read-only: a wrong path gives an error instead of silently creating an empty database file
        connection = sqlite3.connect(Path(database).as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row   # lets a row be turned into a dict (column name -> value)
    except sqlite3.Error as e:
        log.error(f"Error connecting to database {database}: {e}")
        return {}
    try:
        for category in CATEGORIES:
            # Newest row of this ticker. The ticker goes in as a ? parameter, never pasted into the SQL text
            query = f"SELECT * FROM {category} WHERE ticker = ? ORDER BY date DESC LIMIT 1"
            row = connection.execute(query, (ticker,)).fetchone()
            if row:
                ticker_data[category] = {column: value for column, value in dict(row).items()
                                         if column not in NOT_METRICS}
            else:
                ticker_data[category] = {}
                log.warning(f"No {category} data found for ticker {ticker} in database {database}")
    except sqlite3.Error as e:
        log.error(f"Error reading {ticker} from database {database}: {e}")
        return {}
    finally:
        connection.close()   # always closed, even after an error

    return ticker_data


@dataclass
class TickerCard:
    ticker: str
    name: str
    code: str      # model sector from the workbook, e.g. "SM"
    region: str    # "US" or "Europe"

    # Metric values per category: {metric name: value}
    # default_factory: every card gets its own empty dict (a plain {} would be shared by all cards)
    valuation:     dict = field(default_factory=dict)
    growth:        dict = field(default_factory=dict)
    profitability: dict = field(default_factory=dict)
    momentum:      dict = field(default_factory=dict)
    revisions:     dict = field(default_factory=dict)

    def value(self, category, metric):
        # One metric value, or None if it's missing. `category` is one of CATEGORIES:
        # getattr reads the field with that name (a typo raises an error instead of returning None)
        return getattr(self, category).get(metric)


# Download every ticker's data from the newest FULL run in quant.db, in one database pass.
# Returns 3 things:
#   run_date  the date of the run that was read, e.g. "2026-11-14" (None if nothing could be read)
#   names     {ticker: company name}, from the valuation table
#   values    {ticker: {category: {metric: value}}}, everything a card needs, all tickers
def download_all_latest_tickers_data(database):
    values = {}   # filled by the queries below
    names = {}

    try:
        connection = sqlite3.connect(Path(database).as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        log.error(f"Error connecting to database {database}: {e}")
        return None, {}, {}
    try:
        # Newest date with at least FULL_RUN_SHARE of the biggest run's tickers (not just MAX(date),
        # which would pick a one-ticker test run)
        run_date = connection.execute(
            "SELECT date FROM valuation GROUP BY date "
            "HAVING COUNT(*) >= ? * (SELECT MAX(n) FROM (SELECT COUNT(*) AS n FROM valuation GROUP BY date)) "
            "ORDER BY date DESC LIMIT 1", (FULL_RUN_SHARE,)).fetchone()[0]
        log.info(f"Downloading the {run_date} run")

        for category in CATEGORIES:
            query = f"SELECT * FROM {category} WHERE date = ?"
            for row in connection.execute(query, (run_date,)):
                row = dict(row)
                ticker = row["ticker"]
                # we extract the company name only from the valuation table, otherwise it will do it for every table, but we need it only once per ticker.
                if category == "valuation":
                    names[ticker] = row["name"]
                # setdefault: create the ticker's entry the first time, reuse it after
                values.setdefault(ticker, {})[category] = {
                    column: value for column, value in row.items() if column not in NOT_METRICS
                }
    except (sqlite3.Error, TypeError) as e:   # TypeError: empty table, no run date found
        log.error(f"Error reading database {database}: {e}")
        return None, {}, {}
    finally:
        connection.close()   # always closed, even after an error

    log.info(f"{len(values)} tickers downloaded")
    return run_date, names, values

# Builds the card for the tickers in the run, returns a dict {ticker: card}.
# sector_lookup = {ticker: (code, region)} from load_sector_lookup() in sector_benchmarks_loaders.py
def build_cards(run_date, names, values, sector_lookup):
    cards = {}
    not_found = []   # tickers with no model code in the workbook: no card, reported once at the end
    for ticker, ticker_values in values.items():
        if ticker not in sector_lookup:
            not_found.append(ticker)
            continue
        code, region = sector_lookup[ticker]  
        card = TickerCard(
            ticker=ticker,
            name=names.get(ticker),            
            code=code,
            region=region,
            valuation=ticker_values.get("valuation", {}),
            growth=ticker_values.get("growth", {}),
            profitability=ticker_values.get("profitability", {}),
            momentum=ticker_values.get("momentum", {}),
            revisions=ticker_values.get("revisions", {})
        )
        cards[ticker] = card
        log.debug(f"Built card for {ticker}: {card}")

    if not_found:
        log.error(f"{len(not_found)} tickers not in Sector_Benchmarks (no model code), no card: "
                  f"{', '.join(not_found)}")
    log.info(f"{len(cards)} cards built for run {run_date}")
    return cards