# test_fetch_data.py — unit tests for every calculation in fetch_data.py.
#
# Technique: KNOWN-ANSWER TESTING. Every input is simple enough to compute the
# expected result by hand; the hand-math is in the comment next to each assert.
# All tests are OFFLINE (no yfinance, no network) — pure math on synthetic data.
#
# Run from the repo root:  pytest -v

import numpy as np
import pandas as pd
import pytest

from fetch_data import (
    is_european, is_japanese, is_canadian, is_brazilian,
    load_watchlist,
    atr, sma, rsi, week52_high,
    trend_direction, avg_volume, volume_vs_avg,
    support_resistance, distance_from_sr,
    setup_type, short_setup_type,
    conviction, short_conviction,
    process_ticker,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Ticker-suffix routing (which market does a ticker belong to?)
# ═══════════════════════════════════════════════════════════════════════════

def test_market_routing():
    assert is_european("BP.PA")        # London
    assert is_european("AIR.PA")      # Paris
    assert is_european("bp.l")        # suffix check is case-insensitive
    assert not is_european("AAPL")    # no suffix = US

    assert is_japanese("4502.T")
    assert is_canadian("SHOP.TO")
    assert is_canadian("XYZ.V")       # TSX Venture
    assert is_brazilian("PETR4.SA")

    assert not is_japanese("AAPL")
    assert not is_european("BRK-B")   # dash is not a market suffix


# ═══════════════════════════════════════════════════════════════════════════
# 2. Watchlist loading (uses pytest's tmp_path — a throwaway temp folder)
# ═══════════════════════════════════════════════════════════════════════════

def test_load_watchlist_skips_blanks_and_comments(tmp_path):
    f = tmp_path / "watchlist.txt"
    f.write_text("AAPL\n# a comment\n\nMETA\n")
    assert load_watchlist(str(f)) == ["AAPL", "META"]


def test_load_watchlist_missing_file_exits(tmp_path):
    # fetch_data calls sys.exit(1) when the file is absent — assert exactly that.
    with pytest.raises(SystemExit):
        load_watchlist(str(tmp_path / "nope.txt"))


# ═══════════════════════════════════════════════════════════════════════════
# 3. The INDICATORS block — sma, rsi, week52_high 
# ═══════════════════════════════════════════════════════════════════════════

def test_sma_basic():
    closes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert sma(closes, 5) == 8.0          # mean of LAST five: (6+7+8+9+10)/5

def test_sma_exactly_enough_history():
    assert sma([1, 2, 3], 3) == 2.0       # len == period is allowed

def test_sma_not_enough_history():
    assert sma([1, 2], 3) is None         # guard clause


def test_rsi_all_gains_is_100():
    closes = list(range(1, 17))           # 16 closes, every delta +1
    assert rsi(closes, 14) == 100.0       # no losses -> max strength branch

def test_rsi_all_losses_is_0():
    closes = list(range(16, 0, -1))       # every delta -1
    assert rsi(closes, 14) == 0.0         # avg_gain 0 -> rs 0 -> 100-100/1

def test_rsi_balanced_is_50():
    closes = [100, 101] * 8               # deltas alternate +1/-1
    # last 14 deltas = 7 gains of 1, 7 losses of 1 -> rs = 0.5/0.5 = 1 -> 50
    assert rsi(closes, 14) == 50.0

def test_rsi_flat_series_is_50():
    closes = [100] * 16                   # all deltas 0 -> avg_loss == 0,
    assert rsi(closes, 14) == 50.0        # avg_gain == 0 -> neutral branch

def test_rsi_not_enough_history():
    assert rsi([1] * 14, 14) is None      # needs period+1 = 15 closes


def test_week52_high():
    assert week52_high([101.0, 155.5, 103.0]) == 155.5

def test_week52_high_empty():
    assert week52_high([]) is None


# ═══════════════════════════════════════════════════════════════════════════
# 4. ATR — constant-range case, then a gap day to prove True Range matters
# ═══════════════════════════════════════════════════════════════════════════

def test_atr_constant_range():
    closes = [100.0] * 16
    highs  = [101.0] * 16                 # every day: high-low = 2, no gaps
    lows   = [99.0] * 16
    assert atr(highs, lows, closes) == 2.0

def test_atr_gap_day_uses_prev_close():
    # 15 flat days, then close jumps 100 -> 110. On the gap day:
    # TR = max(high-low=2, |111-100|=11, |109-100|=9) = 11  <- prev-close branch
    closes = [100.0] * 15 + [110.0]
    highs  = [c + 1 for c in closes]
    lows   = [c - 1 for c in closes]
    # mean of last 14 TRs = (13 days of 2 + one 11) / 14 = 37/14
    assert atr(highs, lows, closes) == pytest.approx(37 / 14)

def test_atr_not_enough_history():
    assert atr([1] * 14, [1] * 14, [1] * 14) is None


# ═══════════════════════════════════════════════════════════════════════════
# 5. Trend, volume
# ═══════════════════════════════════════════════════════════════════════════

def test_trend_up():
    assert trend_direction(list(range(1, 21))) == "up"        # 20 rising closes

def test_trend_down():
    assert trend_direction(list(range(20, 0, -1))) == "down"

def test_trend_sideways():
    assert trend_direction([5] * 20) == "sideways"            # no higher/lower

def test_trend_unknown_when_short():
    assert trend_direction(list(range(19))) == "unknown"      # < 20 closes


def test_avg_volume():
    # avg_volume averages the 20 days BEFORE today (volumes[-21:-1])
    vols = [100] * 20 + [999]             # today's spike must NOT be included
    assert avg_volume(vols) == 100.0

def test_avg_volume_not_enough():
    assert avg_volume([100] * 20) is None # needs 21

def test_volume_vs_avg_double():
    vols = [100] * 20 + [200]             # today 200 vs 20-day avg 100
    assert volume_vs_avg(vols) == 2.0

def test_volume_vs_avg_flat():
    assert volume_vs_avg([100] * 21) == 1.0


# ═══════════════════════════════════════════════════════════════════════════
# 6. Support / resistance and distances
# ═══════════════════════════════════════════════════════════════════════════

def test_support_resistance_last_window():
    highs = list(range(1, 13))            # 1..12 — window is the LAST 10: 3..12
    lows  = list(range(1, 13))
    support, resistance = support_resistance(highs, lows, window=10)
    assert resistance == 12.0
    assert support == 3.0

def test_support_resistance_short():
    assert support_resistance([1, 2], [1, 2], window=10) == (None, None)

def test_distance_from_sr():
    # price 110, support 100 -> 10% above; resistance 121 -> 10% below it
    dist_sup, dist_res = distance_from_sr(110, 100, 121)
    assert dist_sup == 10.0
    assert dist_res == 10.0

def test_distance_from_sr_none_inputs():
    assert distance_from_sr(110, None, 121) == (None, None)


# ═══════════════════════════════════════════════════════════════════════════
# 7. Setup classification (long and short)
#    These build the exact ingredients each branch needs.
# ═══════════════════════════════════════════════════════════════════════════

def test_setup_breakout():
    closes = list(range(80, 101))         # 21 rising closes, price 100 > prev 99
    vols   = [100] * 20 + [200]           # vol_ratio 2.0 -> strong volume
    # resistance 101 -> (101-100)/100 = 1% away -> near_resistance
    assert setup_type(closes, vols, support=80, resistance=101) == "breakout"

def test_setup_pullback():
    closes = list(range(80, 101))         # uptrend
    vols   = [100] * 21                   # calm volume
    # support 99.5 -> price within 0.5% of support; resistance far away
    assert setup_type(closes, vols, support=99.5, resistance=120) == "pullback"

def test_setup_consolidation():
    closes = list(range(80, 101))
    vols   = [100] * 21                   # weak volume near resistance
    assert setup_type(closes, vols, support=80, resistance=101) == "consolidation"

def test_setup_neutral():
    closes = list(range(80, 101))
    vols   = [100] * 21                   # far from both levels
    assert setup_type(closes, vols, support=50, resistance=200) == "neutral"

def test_setup_unknown_when_no_support():
    assert setup_type(list(range(80, 101)), [100] * 21, None, 101) == "unknown"


def test_short_setup_breakdown():
    closes = list(range(120, 99, -1))     # 21 falling closes: price 100 < prev 101
    vols   = [100] * 20 + [200]           # strong volume
    # support 99 -> price within 1% -> breaking down through support
    assert short_setup_type(closes, vols, support=99, resistance=150) == "breakdown"

def test_short_setup_distribution():
    closes = list(range(120, 99, -1))     # downtrend
    vols   = [100] * 21                   # weak volume stuck near resistance
    assert short_setup_type(closes, vols, support=50, resistance=101) == "distribution"

def test_short_setup_none_in_uptrend():
    closes = list(range(80, 101))         # uptrend -> no short setup
    vols   = [100] * 21
    assert short_setup_type(closes, vols, support=80, resistance=101) == "none"


# ═══════════════════════════════════════════════════════════════════════════
# 8. Conviction point-scoring (the gate that decides who gets analyzed)
# ═══════════════════════════════════════════════════════════════════════════

def test_conviction_high():
    # breakout +3, vol 1.6 +2, dist_res 1% +2, up+breakout +1 = 8 -> High
    assert conviction("breakout", 1.6, 1.0, 5.0, "up") == "High"

def test_conviction_medium():
    # pullback +2, vol 1.25 +1, dist_res 4% +1, up+pullback +1 = 5 -> Medium
    assert conviction("pullback", 1.25, 4.0, 1.0, "up") == "Medium"

def test_conviction_low():
    # consolidation +1, calm volume 0, dist_res 10% 0 = 1 -> Low
    assert conviction("consolidation", 1.0, 10.0, 5.0, "sideways") == "Low"


def test_short_conviction_requires_downtrend():
    assert short_conviction("breakdown", 2.0, 1.0, "up") == "None"

def test_short_conviction_high():
    # breakdown +3, vol 1.6 +2, dist_res 1% +2 = 7 -> High
    assert short_conviction("breakdown", 1.6, 1.0, "down") == "High"

def test_short_conviction_medium():
    # distribution +2, calm vol 0, dist_res 4% +1 = 3 -> Medium
    assert short_conviction("distribution", 1.0, 4.0, "down") == "Medium"


# ═══════════════════════════════════════════════════════════════════════════
# 9. CAPSTONE — process_ticker on a synthetic DataFrame (offline integration)
#    Pins the schema contract that watchlist_ranker depends on (landmine 1).
# ═══════════════════════════════════════════════════════════════════════════

def make_uptrend_df(days=260):
    """A clean rising stock: 100 -> 200 over ~a year, 2M shares/day, 4% daily range."""
    idx = pd.date_range("2025-07-01", periods=days, freq="B")
    close = np.linspace(100, 200, days)
    return pd.DataFrame({
        "Open":   close,
        "High":   close * 1.02,
        "Low":    close * 0.98,
        "Close":  close,
        "Volume": np.full(days, 2_000_000),
    }, index=idx)


def test_process_ticker_schema_contract():
    result = process_ticker("FAKE", make_uptrend_df())

    assert result is not None                      # survives all guard clauses

    # The four landmine-1 fields MUST exist with these exact key names —
    # watchlist_ranker.score_technical reads them.
    for key in ("ma50", "ma200", "52w_high", "rsi"):
        assert key in result, f"missing key: {key}"
        assert result[key] is not None

    assert 0 <= result["rsi"] <= 100
    assert result["rsi"] == 100.0                  # strictly rising -> all gains
    assert result["ma50"] > result["ma200"]        # must hold in a steady uptrend
    assert result["52w_high"] == pytest.approx(200 * 1.02, abs=0.01)  # planted max
    assert result["trend"] == "up"
    assert result["rr"] == 1.5                     # fixed risk/reward by design


def test_process_ticker_rejects_illiquid():
    df = make_uptrend_df()
    df["Volume"] = 100_000                         # below US 500k minimum
    assert process_ticker("FAKE", df) is None      # volume guard drops it

def test_process_ticker_rejects_too_short_history():
    assert process_ticker("FAKE", make_uptrend_df(days=10)) is None
