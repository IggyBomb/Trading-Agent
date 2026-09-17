#!/usr/bin/env python3
"""
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

import sqlite3
from datetime import datetime, date

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


def check_first_day(conn, row, data):
    """First tracked day only (day_close_price still NULL). The scan's entry
    is the previous close, which nobody could actually trade: re-base entry
    to today's open. If the open is already through the stop, the trade was
    never enterable -> close as GAPPED_OUT (entry kept as the scan wrote it,
    so gain_pct shows the gap size). Returns True if closed."""
    if row["day_close_price"] is not None:
        return False
    if data["open"] <= row["stop"]:
        update_row(conn, row["id"], calculate_outcome(row, data, "GAPPED_OUT", data["open"]))
        return True
    row["entry"] = data["open"]
    update_row(conn, row["id"], {"entry": data["open"]})
    return False


def update_daily_tracking(conn, row, data):
    """Daily mark for an open row: running high/low (only while the trade is
    live — a bar beyond the level belongs to the exit), today's close and the
    metrics valued at that close. Stored high/low is NULL until first update."""
    if data["high"] < row["target"] and (row["max_high"] is None or data["high"] > row["max_high"]):
        update_row(conn, row["id"], {"max_high": data["high"], "max_high_date": data["date"]})
    if data["low"] > row["stop"] and (row["min_low"] is None or data["low"] < row["min_low"]):
        update_row(conn, row["id"], {"min_low": data["low"], "min_low_date": data["date"]})
    update_row(conn, row["id"], {"day_close_price": data["close"],
                                 **calculate_metrics(row, data, data["close"])})


def check_high_low(conn, row, data):
    """Close the row if today's bar hit target or stop. Returns True if closed.
    Target wins if both hit the same day (a daily bar can't tell which came first)."""
    if data["high"] >= row["target"]:
        update_row(conn, row["id"], calculate_outcome(row, data, "TARGET_HIT", row["target"]))
        return True
    elif data["low"] <= row["stop"]:
        update_row(conn, row["id"], calculate_outcome(row, data, "STOP_HIT", row["stop"]))
        return True


def check_close_date(conn, row, data):
    """Close the row at today's close if its expected_close_date has arrived."""
    if data["date"] >= row["expected_close_date"]:
        close = data["close"]
        update_row(conn, row["id"], {
            "day_close_price": close,
            **calculate_outcome(row, data, "CLOSE_DATE_HIT", close),
        })


def main():
    print(f"=== scan_daily_update === {datetime.now():%Y-%m-%d %H:%M:%S}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows accessible by column name: row["ticker"]

    open_rows = [dict(r) for r in conn.execute(
        "SELECT * FROM scan_test_group WHERE outcome IS NULL"
    )]
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

    for row in open_rows:
        data = today_tickers_data.get(row["ticker"])
        if data is None:
            continue   # no bar for this ticker today — leave the row untouched
        if check_first_day(conn, row, data):
            continue
        update_daily_tracking(conn, row, data)
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
