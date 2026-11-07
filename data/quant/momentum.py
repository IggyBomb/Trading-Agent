"""
momentum.py — the Momentum evaluation: the 4 metrics of the Seeking Alpha Momentum page.

Price change over 3, 6, 9 and 12 months, in % (e.g. 25.0 = +25%).
Price only: dividends are not added back.
"""

import pandas as pd

from quant_parameter_class import QuantParameter
from quant_utils import growth, to_number


class Momentum(QuantParameter):
    # The momentum metrics
    METRICS = [
        "price_performance_three_months",
        "price_performance_six_months",
        "price_performance_nine_months",
        "price_performance_one_year",
    ]
    # table in the DB
    TABLE_NAME = "momentum_history"

    # The constructor of the class
    def __init__(self, ticker, stock=None):
        super().__init__(ticker, stock)

        # No ready-made metric: Yahoo's "52WeekChange" can be stale or wrong
        # (SAP.DE on 2026-11-06: +0.05% vs a real -3.3%), so all 4 are calculated

        # ── Raw numbers: daily closing prices of the last 13 months ──
        history = self.stock.history(period="13mo", auto_adjust=False)
        self.closes = history["Close"] if history is not None and not history.empty else None

        # ── Metrics we calculate ourselves ──
        self.calc_performance()

    def price_months_ago(self, months):
        # Closing price on the last trading day on or before the same date `months` ago
        if self.closes is None:
            return None
        target = self.closes.index[-1] - pd.DateOffset(months=months)
        before = self.closes[self.closes.index <= target]
        return to_number(before.iloc[-1]) if not before.empty else None

    def calc_performance(self):
        # Today's price vs the price N months ago
        self.price_performance_three_months = growth(self.price, self.price_months_ago(3))
        self.price_performance_six_months   = growth(self.price, self.price_months_ago(6))
        self.price_performance_nine_months  = growth(self.price, self.price_months_ago(9))
        self.price_performance_one_year     = growth(self.price, self.price_months_ago(12))

    def get_metrics(self):
        # All 4 metrics as {name: value}
        return {name: getattr(self, name) for name in self.METRICS}
