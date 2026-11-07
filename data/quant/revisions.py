"""
revisions.py — the Revisions evaluation: how analysts' forecasts are changing,
for this fiscal year and the next

Where the numbers come from:
  - yfinance: today's EPS and revenue forecasts, EPS up/down revisions of the
    last 30 days, EPS forecast change over 1 and 3 months
  - our own database: Yahoo keeps no history of revenue forecasts and no EPS
    history beyond 90 days, so those changes are measured against the forecasts
    this class saved on earlier days. They stay empty until enough history exists
    (1 month, 3 months, 6 months after the first daily run).
Revenue up/down revision counts are not available from any free source.
Changes are in % (e.g. 5.0 = the forecast rose 5%).
"""

import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd

from quant_parameter_class import QuantParameter
from quant_utils import estimate, forecast_lags, growth, to_number

# config.py lives in the repo root, two levels up from data/quant
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import QUANT_DB_PATH

# Months back for each trend, and how far an older saved row may be from the exact
# date (weekends, days the script didn't run)
TREND_MONTHS = {"one_month": 1, "three_months": 3, "six_months": 6}
MAX_GAP_DAYS = 7


class Revisions(QuantParameter):
    # The revisions metrics
    METRICS = [
        # Which fiscal years "current" and "next" are (e.g. "2027-08"): needed to compare
        # the same year across days, because "current year" moves when a year closes
        "current_fiscal_year",
        "next_fiscal_year",
        # Today's forecasts: saved every day, they are the history the trends below use
        "earnings_per_share_estimate_current_year",
        "earnings_per_share_estimate_next_year",
        "revenue_estimate_current_year",
        "revenue_estimate_next_year",
        # How many analysts raised / cut their EPS forecast in the last 30 days
        "earnings_per_share_up_revisions_last_30_days_current_year",
        "earnings_per_share_down_revisions_last_30_days_current_year",
        "earnings_per_share_up_revisions_last_30_days_next_year",
        "earnings_per_share_down_revisions_last_30_days_next_year",
        # How much the forecast changed
        "earnings_per_share_estimate_change_one_month_current_year",
        "earnings_per_share_estimate_change_three_months_current_year",
        "earnings_per_share_estimate_change_six_months_current_year",
        "earnings_per_share_estimate_change_one_month_next_year",
        "earnings_per_share_estimate_change_three_months_next_year",
        "earnings_per_share_estimate_change_six_months_next_year",
        "revenue_estimate_change_one_month_current_year",
        "revenue_estimate_change_three_months_current_year",
        "revenue_estimate_change_six_months_current_year",
        "revenue_estimate_change_one_month_next_year",
        "revenue_estimate_change_three_months_next_year",
        "revenue_estimate_change_six_months_next_year",
    ]
    # table in the DB
    TABLE_NAME = "revisions_history"

    # The constructor of the class
    def __init__(self, ticker, stock=None, db_path=QUANT_DB_PATH):
        super().__init__(ticker, stock)
        self.db_path = db_path   # where earlier days' forecasts are read from

        # ── Which Yahoo rows are "current year" and "next year" ──
        # Right after a fiscal year closes Yahoo can lag (see forecast_lags): its "+1y"
        # is then the current year, and there's no row for the next one
        lagging = forecast_lags(self.stock.revenue_estimate, self.stock.income_stmt)
        self.rows = {"current_year": "+1y" if lagging else "0y",
                     "next_year": None if lagging else "+1y"}
        self.calc_fiscal_years()

        # ── Metrics yfinance already gives ready-made ──
        # (same names for both years, so they're set in a loop; a missing row gives None)
        eps_est, revenue_est = self.stock.earnings_estimate, self.stock.revenue_estimate
        eps_trend, eps_revisions = self.stock.eps_trend, self.stock.eps_revisions
        for year, row in self.rows.items():
            setattr(self, f"earnings_per_share_estimate_{year}", estimate(eps_est, row))
            setattr(self, f"revenue_estimate_{year}", estimate(revenue_est, row))
            setattr(self, f"earnings_per_share_up_revisions_last_30_days_{year}",
                    whole(estimate(eps_revisions, row, "upLast30days")))
            setattr(self, f"earnings_per_share_down_revisions_last_30_days_{year}",
                    whole(estimate(eps_revisions, row, "downLast30days")))
            # Yahoo keeps the EPS forecast of 30 and 90 days ago
            today_eps = estimate(eps_trend, row, "current")
            setattr(self, f"earnings_per_share_estimate_change_one_month_{year}",
                    growth(today_eps, estimate(eps_trend, row, "30daysAgo")))
            setattr(self, f"earnings_per_share_estimate_change_three_months_{year}",
                    growth(today_eps, estimate(eps_trend, row, "90daysAgo")))

        # ── Metrics we calculate ourselves, from our own saved history ──
        self.calc_history_trends()

    def calc_fiscal_years(self):
        # Last reported fiscal year end + 1 year = current fiscal year (as "YYYY-MM")
        income = self.stock.income_stmt
        if income is None or income.empty:
            self.current_fiscal_year = self.next_fiscal_year = None
            return
        last_year_end = pd.Timestamp(max(income.columns))
        self.current_fiscal_year = (last_year_end + pd.DateOffset(years=1)).strftime("%Y-%m")
        self.next_fiscal_year = (last_year_end + pd.DateOffset(years=2)).strftime("%Y-%m")

    def calc_history_trends(self):
        # Revenue: 1, 3 and 6 months. EPS: only 6 months (Yahoo already gave 1 and 3)
        fiscal_years = {"current_year": self.current_fiscal_year, "next_year": self.next_fiscal_year}
        for year, fiscal_year in fiscal_years.items():
            revenue_now = getattr(self, f"revenue_estimate_{year}")
            eps_now = getattr(self, f"earnings_per_share_estimate_{year}")
            for period, months in TREND_MONTHS.items():
                revenue_then = self.saved_estimate("revenue_estimate", fiscal_year, months)
                setattr(self, f"revenue_estimate_change_{period}_{year}", growth(revenue_now, revenue_then))
            eps_then = self.saved_estimate("earnings_per_share_estimate", fiscal_year, 6)
            setattr(self, f"earnings_per_share_estimate_change_six_months_{year}", growth(eps_now, eps_then))

    def saved_estimate(self, kind, fiscal_year, months):
        # The forecast for `fiscal_year` that we saved about `months` ago (None if no such day).
        # `kind` = "revenue_estimate" or "earnings_per_share_estimate"
        if fiscal_year is None:
            return None
        target = pd.Timestamp.today().normalize() - pd.DateOffset(months=months)
        oldest = target - pd.Timedelta(days=MAX_GAP_DAYS)
        sql = (f"SELECT current_fiscal_year, next_fiscal_year, {kind}_current_year, {kind}_next_year "
               f"FROM {self.TABLE_NAME} WHERE ticker = ? AND date BETWEEN ? AND ? ORDER BY date DESC LIMIT 1")
        try:
            # Read-only: only looks at the database, never creates or changes it
            connection = sqlite3.connect(Path(self.db_path).as_uri() + "?mode=ro", uri=True)
            try:
                row = connection.execute(sql, (self.ticker, oldest.strftime("%Y-%m-%d"),
                                               target.strftime("%Y-%m-%d"))).fetchone()
            finally:
                connection.close()
        except sqlite3.Error:
            return None   # no database or table yet (first run)
        if row is None:
            return None
        # Back then, the same fiscal year may have been "current" or still "next"
        saved_current_year, saved_next_year, saved_current, saved_next = row
        if saved_current_year == fiscal_year:
            return to_number(saved_current)
        if saved_next_year == fiscal_year:
            return to_number(saved_next)
        return None

    def get_metrics(self):
        # All 22 metrics as {name: value}
        return {name: getattr(self, name) for name in self.METRICS}


def whole(number):
    # Revision counts as whole numbers (Yahoo gives them as decimals)
    return int(number) if number is not None else None
