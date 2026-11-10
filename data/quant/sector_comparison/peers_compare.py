"""
valuation_compare.py — compares the Valuation metrics of each ticker (from
evaluation.py, run by main.py) against the sector values in Sector_Benchmarks.xlsx.

Inputs:
    - Valuation(ticker) results           -> data/quant/evaluation.py
    - Sector benchmarks, "Valuation" sheet -> data/quant/sector_comparison/Sector_Benchmarks.xlsx

Output:
    - (to be decided)

Run from the repo root:
    (to be decided)
"""

# ── Imports ──
import load_sector_lookup, load_peer_values from sector_benchmarks_loaders



# ── Settings ──

def compare_metric(ticker, metric):
    # Compare a ticker's metric to its peers in the same model code + region
    # Returns a dict with the ticker's value, the median of its peers, and the percentile
    # of the ticker's value among its peers (0–100)
    if ticker not in sector_lookup:
        return None
    model_code, region = sector_lookup[ticker]
    peers = peer_values[(peer_values["Model code"] == model_code) &
                        (peer_values["Region"] == region)]
    if metric not in peers.columns or ticker not in peer_values.index:
        return None
    value = peer_values.loc[ticker, metric]
    median = peers[metric].median()
    percentile = 100 * (peers[metric] < value).sum() / len(peers)
    return {"value": value, "median": median, "percentile": percentile}


# ── Main logic ──


if __name__ == "__main__":
    sector_lookup = load_sector_lookup()
    peer_values = load_peer_values(VALUATION_METRICS)
    pass
