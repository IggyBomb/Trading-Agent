"""Gap / news-shock detector (2026-10-30)."""
import numpy as np
import pandas as pd
import fetch_data as fd


def series(n=60, gap_at=None, gap_size=0.0, gap_vol=1.0, base_vol=1e6):
    """Flat-ish price with 1% daily range; optional gap at index `gap_at`."""
    c = np.full(n, 100.0)
    if gap_at is not None:
        c[gap_at:] += gap_size
    o = c.copy()
    if gap_at is not None:
        o[gap_at] = c[gap_at]              # opens at the new level -> gap vs prev close
    h, l = c * 1.005, c * 0.995
    v = np.full(n, base_vol)
    if gap_at is not None:
        v[gap_at] = base_vol * gap_vol
    return o, h, l, c, v


def test_earnings_style_gap_detected():
    o, h, l, c, v = series(gap_at=55, gap_size=8.0, gap_vol=4.0)   # ATR ~1 -> 8 ATR gap
    g = fd.detect_gap(o, h, l, c, v)
    assert g and g["direction"] == "up" and g["days_ago"] == 4 and g["size_atr"] > 2


def test_gap_without_volume_ignored():
    o, h, l, c, v = series(gap_at=55, gap_size=8.0, gap_vol=1.2)
    assert fd.detect_gap(o, h, l, c, v) is None


def test_volume_without_gap_ignored():
    o, h, l, c, v = series(gap_at=55, gap_size=0.0, gap_vol=5.0)
    assert fd.detect_gap(o, h, l, c, v) is None


def test_gap_expires_after_hold_window():
    o, h, l, c, v = series(gap_at=48, gap_size=8.0, gap_vol=4.0)   # 11 sessions ago
    assert fd.detect_gap(o, h, l, c, v) is None


def test_gap_down_detected():
    o, h, l, c, v = series(gap_at=57, gap_size=-8.0, gap_vol=3.0)
    g = fd.detect_gap(o, h, l, c, v)
    assert g and g["direction"] == "down"


def test_earnings_gap_capped_at_medium():
    # breakout-like points (vol>1.5 +2, near resistance +2, bounce +2) would be High
    assert fd.conviction("breakout", 1.6, 1.0, 5.0, "up") == "High"
    assert fd.conviction("earnings_gap", 1.6, 1.0, 1.0, "up", support_bounce=True) == "Medium"
    assert fd.short_conviction("earnings_gap", 1.6, 1.0, "down") in ("Medium", "Low")


def _hist(o, h, l, c, v):
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=len(c))
    return pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c, "Volume": v}, index=idx)


def _run(monkeypatch, earn):
    monkeypatch.setattr(fd, "live_price", lambda t: None)
    monkeypatch.setattr(fd, "backfill_daily", lambda t, h, v=None: h)
    monkeypatch.setattr(fd, "earnings_near", lambda t, d: earn)
    o, h, l, c, v = series(n=260, gap_at=257, gap_size=10.0, gap_vol=4.0)
    h = h * 1.02; l = l * 0.98                       # enough range to pass the ATR% filter
    return fd.process_ticker("FAKE", _hist(o, h, l, c, v))


def test_process_ticker_earnings_vs_news(monkeypatch):
    r_earn = _run(monkeypatch, True)
    r_news = _run(monkeypatch, False)
    r_unk  = _run(monkeypatch, None)
    assert r_earn["gap_event"] == "earnings" and r_earn["setup"] == "earnings_gap"
    assert r_earn["conviction"] != "High"
    assert r_news["gap_event"] == "news" and r_news["setup"] != "earnings_gap"
    assert r_unk["gap_event"] == "unverified" and r_unk["setup"] != "earnings_gap"
    # gap bar removed from ATR for the earnings case -> tighter stop distance
    assert r_earn["atr"] < r_news["atr"]
