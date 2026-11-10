"""
ticker_card.py — one card per ticker with everything the sector comparison needs:
who it is, which peer group it belongs to, and its metric values per category.

The card only holds data that was already loaded (no downloads, no comparison logic).
Cards are built once per run (see build_cards in sector_benchmarks_loaders.py) and
passed to the comparison functions in peers_compare.py.

Usage:
    card = TickerCard("MU", "Micron Technology, Inc.", "SM", "US",
                      valuation={"price_to_earnings_gaap_trailing": 9.28})
    card.valuation["price_to_earnings_gaap_trailing"]      # 9.28
    card.value("growth", "revenue_growth_year_over_year")  # None if missing
"""

from dataclasses import dataclass, field

# The categories a card holds, same names as the fields below (used to loop over them)
CATEGORIES = ["valuation", "growth", "profitability", "momentum", "revisions"]


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
