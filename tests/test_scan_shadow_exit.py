import pandas as pd

from scan_shadow_exit import replay, path_facts


def bars(rows, start="2026-11-05"):
    idx = pd.bdate_range(start, periods=len(rows))
    return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx)


# Adidas 2026-11-04 BUY: entry 176.35, high 181.90 (+3.15%) -> floor 178.85 (keep 45%).
# Day 1 close 179.60 stays above the floor; day 2 close 174.55 is below it.
ADS = bars([
    (177.0, 181.90, 177.15, 179.60),
    (176.0, 176.00, 173.10, 174.55),
])


def test_giveback_exits_on_close_below_floor():
    ex = replay(ADS, 176.35, 161.58, 197.45, "2026-11-13", giveback=True)
    assert ex == {"outcome": "GIVEBACK_EXIT", "date": "2026-11-06", "price": 174.55}


def test_control_ignores_giveback():
    assert replay(ADS, 176.35, 161.58, 197.45, "2026-11-13", giveback=False) is None


def test_not_armed_below_threshold():
    b = bars([(100, 102.9, 99, 100.5)])          # peak +2.9%: rule stays off
    assert replay(b, 100, 90, 120, "2026-12-31", giveback=True) is None


def test_target_wins_same_bar_as_stop():
    b = bars([(100, 121, 89, 100)])
    assert replay(b, 100, 90, 120, "2026-12-31", giveback=True)["outcome"] == "TARGET_HIT"


def test_stop_before_giveback():
    b = bars([(100, 105, 89, 95)])
    ex = replay(b, 100, 90, 120, "2026-12-31", giveback=True)
    assert ex["outcome"] == "STOP_HIT" and ex["price"] == 90


def test_close_date():
    b = bars([(100, 101, 99, 100.5), (100, 101, 99, 100.8)])
    ex = replay(b, 100, 90, 120, "2026-11-06", giveback=True)
    assert ex == {"outcome": "CLOSE_DATE_HIT", "date": "2026-11-06", "price": 100.8}


def test_path_facts_floor():
    peak, peak_date, armed, floor = path_facts(ADS, 176.35)
    assert peak == 181.90 and armed == "2026-11-05"
    assert round(floor, 2) == 178.85
