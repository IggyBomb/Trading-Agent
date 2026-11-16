"""
comparison_engine.py — compares each ticker's metrics (its TickerCard, values from quant.db)
against the other cards of its model sector, the same method as the "Compare (quant)" sheet
of Sector_Benchmarks_quant.xlsx.

Inputs:
    - Ticker cards (values + code + region) -> ticker_card.py (download_all_latest_tickers_data + build_cards)
    - Which metrics and how                 -> metric_list.py
    - Thresholds and grades                 -> comparison_settings.py

Output:
    - One TickerScoreCard per ticker (ticker_score_card.py)

Run from the repo root:
    (to be decided)
"""

# ── Imports ──
from sector_benchmarks_loaders import load_sector_lookup
from metric_list import METRICS
from comparison_settings import ALL_REGIONS, MIN_NAMES_FOR_REGION
from ticker_score_card import TickerScoreCard
import logging
log = logging.getLogger("comparison_engine")



# ── Peer groups ──

# This function creates a dictionary of peer groups, where each group is defined by sector and region. Each ticker card is added to a list with his sector peers for region and in the global list of his peers.
def create_peers_groups(all_ticker_card):
    peer_groups = {}
    for card in all_ticker_card.values():
        sector_code = card.code
        region = card.region
        if sector_code not in peer_groups:
            peer_groups[sector_code] = {}
        if region not in peer_groups[sector_code]:
            peer_groups[sector_code][region] = []
        if ALL_REGIONS not in peer_groups[sector_code]:
            peer_groups[sector_code][ALL_REGIONS] = []
        peer_groups[sector_code][ALL_REGIONS].append(card)
        peer_groups[sector_code][region].append(card)
    return peer_groups


# Returns the peer group used for a ticker: (group label, list of peer cards).
# The label is the ticker's region, or ALL_REGIONS when that region has too few names.
def select_group_region(ticker_card, peer_groups):
    sector_code = ticker_card.code
    region = ticker_card.region
    peers = peer_groups[sector_code][region]
    if len(peers) < MIN_NAMES_FOR_REGION:
        log.info(f"Function select_group_region: for {ticker_card.ticker}: Not enough peers in region {region} for sector {sector_code}. Using global peers instead.")
        return ALL_REGIONS, peer_groups[sector_code][ALL_REGIONS]
    return region, peers


# ── Comparison ──

# Scores ONE ticker against its peers and returns its TickerScoreCard.
# run_date = the quant.db run the card values come from (returned by download_all_latest_tickers_data)
def peers_compare(ticker_card, peer_groups, run_date):
    group, peers = select_group_region(ticker_card, peer_groups)
    score_card = TickerScoreCard(
        ticker=ticker_card.ticker,
        name=ticker_card.name,
        code=ticker_card.code,
        region=ticker_card.region,
        peer_group=group,
        peer_names=len(peers),
        run_date=run_date,
    )
    # Compare the ticker value against the peer values, metric by metric (to be implemented):
    # for metric in METRICS: ... score_card.pillar(metric.category).metrics[metric.name] = MetricScore(...)
    # then the pillar percentile and grade for each pillar
    return score_card


# Scores every ticker: builds the peer groups once, then one TickerScoreCard per card.
# Returns {ticker: TickerScoreCard}
def compare_all(all_ticker_card, run_date):
    peer_groups = create_peers_groups(all_ticker_card)
    score_cards = {}
    for card in all_ticker_card.values():
        score_cards[card.ticker] = peers_compare(card, peer_groups, run_date)
    log.info(f"{len(score_cards)} score cards for run {run_date}")
    return score_cards


# ── Main logic ──


if __name__ == "__main__":
    sector_lookup = load_sector_lookup()
    pass
