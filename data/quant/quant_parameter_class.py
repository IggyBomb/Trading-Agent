"""
quant_parameter_class.py — the base class every evaluation inherits from
(Valuation, Growth, Profitability, ...).

It holds what all evaluations share: the ticker, the yfinance data, and the
row that gets saved to the database. Each subclass only adds its own metrics.

Usage in a subclass:
    from quant_parameter_class import QuantParameter

    class Valuation(QuantParameter):
        METRICS = [...]
        TABLE_NAME = "valuation_history"
        def get_metrics(self): ...
"""

from abc import ABC, abstractmethod

import yfinance


class QuantParameter(ABC):
    # ── Settings every subclass must fill in ──
    ID_COLUMNS = ["ticker", "name", "sector", "price"]
    METRICS = []        # names of the metrics this evaluation calculates
    TABLE_NAME = None   # database table where its results are saved

    def __init__(self, ticker, stock=None):
        # Shared setup for every evaluation
        # `stock` = an already-created yfinance.Ticker, so each parameter object of the quant system can reuse it
        self.ticker = ticker
        self.stock = stock if stock is not None else yfinance.Ticker(ticker)
        self.info = self.stock.info
        self.name   = self.info.get("longName") or self.info.get("shortName")
        self.sector = self.info.get("sector")
        self.price  = self.info.get("currentPrice")

    @classmethod
    def columns(cls):
        # All column names of this evaluation's table: ID columns + metrics
        return cls.ID_COLUMNS + cls.METRICS

    @abstractmethod
    def get_metrics(self):
        # Every subclass MUST write its own version: return {metric name: value}
        pass

    def to_record(self):
        # The row saved to the database: who/what + this evaluation's metrics
        return {name: getattr(self, name) for name in self.columns()}
