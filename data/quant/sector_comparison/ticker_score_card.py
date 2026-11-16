"""
This class is used to hold the scores generated for a ticker in each category: "valuation", "growth", "profitability", "momentum", "revisions"

Three levels, nested like the "Compare (quant)" sheet:
    TickerScoreCard   one per ticker: who it is, which peer group was used, one PillarScore per pillar
      PillarScore     one per pillar: average percentile + grade, and the scores of its metrics
        MetricScore   one per metric: value, sector median, % diff, percentile, grade, peers

The score card only holds results: everything is calculated in comparison_engine.py.

Usage:
    score_card.valuation.grade                                                   # pillar grade, e.g. "C-"
    score_card.valuation.metrics["price_to_earnings_non_gaap_trailing"].grade    # one metric, e.g. "C"
    score_card.pillar("growth").percentile                                       # in a loop over PILLARS
"""

from dataclasses import dataclass, field
import logging
from comparison_settings import NO_GRADE_METRIC, NO_GRADE_PILLAR
log = logging.getLogger("ticker_score_card")

PILLARS = ["valuation", "growth", "profitability", "momentum", "revisions"]


@dataclass
class MetricScore:
    # One metric compared with the peer group (one row of Compare (quant))
    metric: str                      # our name, e.g. "price_to_earnings_non_gaap_trailing"
    value: float = None              # the ticker's value after cleaning (None = NM)
    median: float = None             # sector median (None if fewer than MIN_PEERS_FOR_MEDIAN peers have a value)
    pct_diff: float = None           # (value - median) / |median|, e.g. 0.069 = 6.9% above the median
    percentile: float = None         # 0-1: share of peers the ticker beats (ties count half)
    grade: str = NO_GRADE_METRIC     # "F" ... "A+", or "NM" when there is no percentile
    peers: int = 0                   # peers with a value, the ticker itself included


@dataclass
class PillarScore:
    # One pillar: its overall result and the score of each of its metrics
    percentile: float = None         # average of the metrics' percentiles (the ones that have one)
    grade: str = NO_GRADE_PILLAR     # pillar grade from that average, "-" if no metric was scored
    # {metric name: MetricScore}. default_factory: every pillar gets its own empty dict
    metrics: dict = field(default_factory=dict)


@dataclass
class TickerScoreCard:
    ticker: str
    name: str
    code: str              # model sector, e.g. "PH"
    region: str            # "US" or "Europe"
    peer_group: str        # group used: the ticker's region, or "All regions" if it had too few names
    peer_names: int        # names in that peer group (with or without data)
    run_date: str          # quant.db run the values come from, e.g. "2026-11-14"

    # One PillarScore per pillar, same names as PILLARS. default_factory: every score card
    # gets its own empty pillars (a plain PillarScore() would be shared by all score cards)
    valuation:     PillarScore = field(default_factory=PillarScore)
    growth:        PillarScore = field(default_factory=PillarScore)
    profitability: PillarScore = field(default_factory=PillarScore)
    momentum:      PillarScore = field(default_factory=PillarScore)
    revisions:     PillarScore = field(default_factory=PillarScore)

    def pillar(self, name):
        # The PillarScore of one pillar; getattr reads the field with that name (a typo raises an error)
        return getattr(self, name)
