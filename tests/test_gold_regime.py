"""Gold regime (2026-10-30): gold_regime.classify() and its hook in
watchlist_ranker.regime_penalty()."""
import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

import gold_regime as gr
import watchlist_ranker as wr

N = 300
IDX = pd.bdate_range(end="2026-10-30", periods=N)


def ramp(start, end, tail=N):
    """Flat at `start`, then linear to `end` over the last `tail` points."""
    v = np.r_[np.full(N - tail, start), np.linspace(start, end, tail)]
    return pd.Series(v, index=IDX)


def flat(x):
    return pd.Series(np.full(N, float(x)), index=IDX)


def last_leg(start_series, end, k):
    """Replace the last k points with a line from the series' value to `end`."""
    s = start_series.copy()
    s.iloc[-k:] = np.linspace(s.iloc[-k - 1], end, k)
    return s


GOLD_FALLING = last_leg(ramp(100, 130, tail=N - 63), 95, 63)    # rally, then -27% in 3M -> < MA200
GOLD_RISING  = ramp(100, 160)
# 2Y yield climbs to a 5.0% peak, then falls 70bp to 4.3% over the last 40 sessions
PEAK_THEN_70BP_LOWER = pd.Series(np.r_[np.linspace(4.0, 5.0, N - 40), np.linspace(5.0, 4.3, 40)], index=IDX)


def test_headwind_rates_up_gold_weak():          # Sept-Oct 2026 type
    out = gr.classify(ramp(1.8, 2.5, tail=63), flat(4.5), flat(100), GOLD_FALLING, GOLD_FALLING * 0.3)
    assert out["regime"] == "HEADWIND" and out["adjustment"] == -10


def test_headwind_dollar_only():
    out = gr.classify(flat(2.0), flat(4.5), ramp(100, 106, tail=63), GOLD_FALLING, GOLD_FALLING * 0.3)
    assert out["regime"] == "HEADWIND"


def test_rates_up_but_gold_rising_is_neutral():  # 2023-24 type: price overrides theory
    out = gr.classify(ramp(1.0, 2.0, tail=63), flat(4.5), ramp(100, 106, tail=63),
                      GOLD_RISING, GOLD_RISING * 0.3)
    assert out["regime"] == "NEUTRAL" and out["adjustment"] == 0
    assert any("NOT confirmed" in n for n in out["notes"])


def test_tailwind_peak_priced_and_miners_leading():
    y2 = PEAK_THEN_70BP_LOWER
    gdx = last_leg(flat(30), 36, 40)
    out = gr.classify(flat(2.0), y2, flat(100), flat(100), gdx)
    assert out["regime"] == "TAILWIND" and out["adjustment"] == 5


def test_peak_priced_but_miners_lagging_is_neutral():
    y2 = PEAK_THEN_70BP_LOWER
    gdx = last_leg(flat(30), 25, 40)
    out = gr.classify(flat(2.0), y2, flat(100), flat(100), gdx)
    assert out["regime"] == "NEUTRAL"


def test_missing_data_is_neutral():
    assert gr.classify(None, None, None, None, None)["adjustment"] == 0
    # macro says headwind but no gold price -> still neutral (fail-closed)
    assert gr.classify(ramp(1.8, 2.5, tail=63), flat(4.5), flat(100), None, None)["adjustment"] == 0


def test_regime_penalty_only_hits_precious_metals():
    regime = {"regime": "HEADWIND", "adjustment": -10, "notes": ["test"]}
    pen, notes = wr.regime_penalty("Basic Materials", "Gold", None, None, None, regime)
    assert pen == -10 and any("gold regime" in n for n in notes)
    assert wr.regime_penalty("Basic Materials", "Other Precious Metals & Mining", None, None, None, regime)[0] == -10
    assert wr.regime_penalty("Basic Materials", "Copper", None, None, None, regime)[0] == 0
    assert wr.regime_penalty("Energy", "Uranium", None, None, None, regime)[0] == 0
    assert wr.regime_penalty("Technology", "Semiconductors", None, None, None, regime)[0] == 0
    assert wr.regime_penalty("Basic Materials", "Gold", None, None, None, None)[0] == 0


def test_stale_file_ignored(tmp_path):
    p = tmp_path / "gold_regime.json"
    old = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    p.write_text(json.dumps({"generated_at": old, "adjustment": -10}))
    assert wr.load_gold_regime(str(p), 36) == {}
    p.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "adjustment": -10}))
    assert wr.load_gold_regime(str(p), 36)["adjustment"] == -10
