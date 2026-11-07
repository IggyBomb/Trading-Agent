"""
sector_benchmarks.py — reads Sector_Benchmarks.xlsx once per run and hands the data
to every sector comparison (valuation_compare.py, and later growth / profitability /
momentum).

It is the only file that knows the workbook layout (sheet names, columns). If the
workbook changes, only this file changes.

Usage:
    from sector_benchmarks import load_sector_lookup
    sector_lookup = load_sector_lookup()        # once, before the ticker loop
"""

# ── Imports ──
import os

import pandas as pd


# ── Settings ──
# The workbook sits next to this file
BENCHMARK_FILE = os.path.join(os.path.dirname(__file__), "Sector_Benchmarks.xlsx")

# Valuation metrics, named as in the Constituents sheet header (columns S–AB)
VALUATION_METRICS = [
    "P/E TTM",
    "P/E FWD",
    "PEG (TTM)",
    "P/B",
    "EV/EBITDA",
    "EV/Sales",
    "P/Sales",
    "P/Cash Flow",
    "P/FCF",
    "FCF yield",
]


# ── Loaders ──
def load_sector_lookup(path=BENCHMARK_FILE):
    # {ticker: (model code, region)} from the Constituents sheet. Read ONCE per run, not per ticker
    # header=3 -> the column names are on row 4 of the sheet (pandas counts from 0)
    table = pd.read_excel(path, sheet_name="Constituents", header=3,
                          usecols=["Ticker", "Model code", "Region"])
    table = table.dropna(subset=["Ticker"])          # skip empty rows at the bottom
    return dict(zip(table["Ticker"], zip(table["Model code"], table["Region"])))

#this functions loads all the tickers form the bechmark file + their model code and region + the metrics passed in parameter.
# the idea of this function is to lead all the informations that are going to be used to comapre the tickers to its peers 
# One row per ticker, ticker as the index. Read ONCE per run.
# A blank cell in the sheet = NM (not meaningful) -> NaN, so it's left out of medians and percentiles
def load_peer_values(metrics, path=BENCHMARK_FILE):
    table = pd.read_excel(path, sheet_name="Constituents", header=3,
                          usecols=["Ticker", "Model code", "Region"] + metrics)
    return table.dropna(subset=["Ticker"]).set_index("Ticker")
