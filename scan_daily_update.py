#!/usr/bin/env python3
"""
Mamma mia quanto fanno cagare i commenti di Claude. Questi sono tutti da riscrivere.
scan_daily_update.py — daily tracker for the scan test group.

Runs once a day, after market close. Reads every open (outcome IS NULL) row
from data/scan_tracking.db's scan_test_group table and fills in that day's
data for each ticker.

DATA STRUCTURE — today_tickers_data is a dict of dicts (nested dict):
outer key = ticker, inner dict = that ticker's last daily OHLCV row, as
returned by fetch_last_day_ticker_data(). Example with two tickers:

    today_tickers_data = {
        "AAPL": {"date": "2026-09-11", "open": 327.45, "high": 336.22,
                 "low": 326.30, "close": 332.27, "volume": 50659000},
        "MSFT": {"date": "2026-09-11", "open": ..., "high": ..., ...},
    }

Access one value with two keys: today_tickers_data["AAPL"]["high"].
A ticker yfinance returned nothing for is simply absent from the dict.
"""

import os
import sqlite3
import sys
from datetime import datetime, date, timedelta
import logging
log = logging.getLogger("scan_daily_update")

import yfinance as yf
import pandas as pd

DB_PATH = "data/scan_tracking.db"


def fetch_last_day_ticker_data(ticker):
    """Most recent daily OHLCV row for `ticker` as a plain dict, or None."""
    hist = yf.download(ticker, period="1d", progress=False, auto_adjust=True)
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.droplevel(1)  # yfinance nests under ticker name
    if hist.empty:
        return None
    ticker_data = hist.iloc[-1]
    return {
        "date":   hist.index[-1].strftime("%Y-%m-%d"),
        "open":   float(ticker_data["Open"]),
        "high":   float(ticker_data["High"]),
        "low":    float(ticker_data["Low"]),
        "close":  float(ticker_data["Close"]),
        "volume": int(ticker_data["Volume"]),
    }


#this is a helper function that fetches the SP500 close value for a given date, it is used to compare the performance of a  ticker against the benchmark
def sp500_close_fetch(date_str):
    """Fetch the SP500 close on date_str, or on the first trading day after it (weekend/holiday)."""
    try:
        end = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=7)  # yfinance end is exclusive
        hist = yf.download("^GSPC", start=date_str, end=end.strftime("%Y-%m-%d"),
                           progress=False, auto_adjust=True)
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.droplevel(1)  # yfinance nests under ticker name
        if hist.empty:
            return None
        return float(hist.iloc[0]["Close"])
    except Exception as e:
        log.error(f"Error fetching SP500 close value for {date_str}: {e}")
        return None

def update_row(conn, row_id, values):
    """UPDATE one scan_test_group row with the given {column: value} dict."""
    assignments = ", ".join(f"{col} = :{col}" for col in values)
    conn.execute(
        f"UPDATE scan_test_group SET {assignments} WHERE id = :id",
        {**values, "id": row_id},
    )


def calculate_metrics(row, data, price):
    """gain_pct / r_achieved / days_held of this row valued at `price` on today's bar."""
    entry, risk = row["entry"], row["entry"] - row["stop"]
    return {
        "gain_pct":   round((price - entry) / entry * 100, 2),
        "r_achieved": round((price - entry) / risk, 2) if risk else None,
        "days_held":  len(pd.bdate_range(row["scan_date"], data["date"])),
    }


def calculate_outcome(row, data, outcome, exit_price):
    """Return the {column: value} dict that closes this row."""
    return {
        "outcome":    outcome,
        "exit_date":  data["date"],
        "exit_price": exit_price,
        **calculate_metrics(row, data, exit_price),
    }


def update_daily_tracking(conn, row, data):
    """Check for new max/high and min/low. Than update the row's day_close_price and metrics (%gain/loss, day close, etc)."""
    if data["high"] < row["target"] and (row["max_high"] is None or data["high"] > row["max_high"]):
        update_row(conn, row["id"], {"max_high": data["high"], "max_high_date": data["date"]})
    if data["low"] > row["stop"] and (row["min_low"] is None or data["low"] < row["min_low"]):
        update_row(conn, row["id"], {"min_low": data["low"], "min_low_date": data["date"]})
    update_row(conn, row["id"], {"day_close_price": data["close"],
                                 **calculate_metrics(row, data, data["close"])})


def check_high_low(conn, row, data):
    """Close the row if today's p hit target or stop. Returns True if closed.
    Target wins if both hit the same day (a daily bar can't tell which came first)."""
    if data["high"] >= row["target"]:
        update_row(conn, row["id"], {"max_high": row["target"], "max_high_date": data["date"],
                                     **calculate_outcome(row, data, "TARGET_HIT", row["target"])})
        return True
    elif data["low"] <= row["stop"]:
        update_row(conn, row["id"], {"min_low": row["stop"], "min_low_date": data["date"],
                                     **calculate_outcome(row, data, "STOP_HIT", row["stop"])})
        return True


def check_close_date(conn, row, data):
    """Close the row at today's close if its expected_close_date has arrived."""
    if data["date"] >= row["expected_close_date"]:
        close = data["close"]
        update_row(conn, row["id"], {
            "day_close_price": close,
            **calculate_outcome(row, data, "CLOSE_DATE_HIT", close),
        })

# this function updates the SP500 benchmark tracking, it compares the performance of the ticker since its scan date against the SP500
def benchmark_daily_tracking(conn, row, sp500_today_value):
    """Store the SP500 close on the scan date (once) and the SP500 % change since then (daily)."""
    sp500_start_value = row["sp500_entry_close"]
    if sp500_start_value is None:
        sp500_start_value = sp500_close_fetch(row["scan_date"])
        if sp500_start_value is None:
            return   # yfinance failed — try again on the next run
        update_row(conn, row["id"], {"sp500_entry_close": sp500_start_value})
    if sp500_today_value is not None:
        sp500_gain_pct = round((sp500_today_value - sp500_start_value) / sp500_start_value * 100, 2)
        update_row(conn, row["id"], {"sp500_gain_pct": sp500_gain_pct})


def main():
    # Logging setup — INFO to console + a fresh logfile each run. Flip to
    # logging.DEBUG to see the per-ticker drop reasons from process_ticker().
    os.makedirs("logs", exist_ok=True)
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # so em-dashes render on any Windows console
    except Exception:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/scan_daily_update.log", mode="w", encoding="utf-8"),
        ],
    )
    print(f"=== scan_daily_update === {datetime.now():%Y-%m-%d %H:%M:%S}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows accessible by column name: row["ticker"]

    open_rows = conn.execute(
        "SELECT * FROM scan_test_group WHERE outcome IS NULL"
    ).fetchall()
    tickers = sorted({row["ticker"] for row in open_rows})  # unique, one yfinance call each

    print(f"  Open rows to update: {len(open_rows)} ({len(tickers)} tickers)")

    today_tickers_data = {}   # ticker -> {"date", "open", "high", "low", "close", "volume"}
    for t in tickers:
        ticker_data = fetch_last_day_ticker_data(t)
        if ticker_data is None:
            print(f"  {t}: no data from yfinance — skipped")
            continue
        today_tickers_data[t] = ticker_data

    print(f"  Fetched {len(today_tickers_data)}/{len(tickers)} tickers")

    sp500_today_data = fetch_last_day_ticker_data("^GSPC")   # once for all rows
    sp500_today_value = sp500_today_data["close"] if sp500_today_data is not None else None
    if sp500_today_value is None:
        print("  ^GSPC: no data from yfinance — sp500_gain_pct not updated today")

    for row in open_rows:
        data = today_tickers_data.get(row["ticker"])
        if data is None:
            continue   # no bar for this ticker today — leave the row untouched
        update_daily_tracking(conn, row, data)
        benchmark_daily_tracking(conn, row, sp500_today_value)
        if not check_high_low(conn, row, data):
            check_close_date(conn, row, data)

    conn.commit()
    still_open = conn.execute(
        "SELECT COUNT(*) FROM scan_test_group WHERE outcome IS NULL"
    ).fetchone()[0]
    conn.close()

    print(f"  Closed today: {len(open_rows) - still_open}   Still open: {still_open}")


if __name__ == "__main__":
    main()
